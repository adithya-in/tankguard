/*
 * TankGuard C1 — cleaning-arm controller (ESP32, OPEN LOOP)
 *
 * The 2R arm from the CAD: two fixed 20 cm links, one brush at the tip, both
 * joints on generic DC gear motors. There is no position feedback, so this
 * sketch cannot "go to 23.7 degrees" — it drives each joint at a calibrated
 * duty for a computed time and dead-reckons the angle. Everything is built
 * around that limit:
 *
 *   - home switches re-zero both joints at boot and again between rings;
 *   - the planner's arcs (tools/swept_area.html) are the unit of motion: the
 *     elbow holds one angle while the shoulder sweeps it;
 *   - the brush runs only during a sweep, never while repositioning;
 *   - speed is a calibration constant (DPS at MOVE_DUTY), so a cycle drifts with
 *     load, voltage and wear — hence the re-homing, and hence the honesty in
 *     the status JSON ("openLoop": true, angles are estimates).
 *
 * Safety
 *   - e-stop (NC) and lid switch (NC) are fail-safe: a broken wire reads unsafe
 *   - level comes from the M1 tank unit; below MIN_LEVEL_PCT the cycle stops
 *   - brush stall cut-out (optional, BRUSH_IS_ENABLED)
 *   - stop is honoured between moves, never mid-move
 *
 * HTTP
 *   GET /clean                          -> status JSON
 *   GET /clean?mode=start|stop|park|home|reset
 */

#include <WiFi.h>
#include <WebServer.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

#include "config.h"
#include "path.h"

// ---------------------------------------------------------------------------
// joints (open loop)
// ---------------------------------------------------------------------------
struct Joint {
  const char *name;
  uint8_t pwmPin, dirPin, homePin, pwmCh;
  bool invert;
  float degPerBurst; // calibrated advance per full-duty pulse (includes coast)
  float estDeg;      // dead-reckoned angle, 0 = home switch
};

Joint sh = {"shoulder", SH_PWM, SH_DIR, SH_HOME, 0, SH_DIR_INVERT, SH_DEG_PER_BURST, 0};
Joint el = {"elbow", EL_PWM, EL_DIR, EL_HOME, 1, EL_DIR_INVERT, EL_DEG_PER_BURST, 0};

volatile bool stopRequested = false;

// LEDC API differs across cores: 3.x attaches by pin, 2.x by channel.
#if defined(ESP_ARDUINO_VERSION_MAJOR) && ESP_ARDUINO_VERSION_MAJOR >= 3
static inline void pwmAttach(uint8_t pin, uint8_t ch) { (void)ch; ledcAttach(pin, 20000, 8); }
static inline void pwmWrite(uint8_t pin, uint8_t ch, uint8_t duty) { (void)ch; ledcWrite(pin, duty); }
#else
static inline void pwmAttach(uint8_t pin, uint8_t ch) { ledcSetup(ch, 20000, 8); ledcAttachPin(pin, ch); }
static inline void pwmWrite(uint8_t pin, uint8_t ch, uint8_t duty) { (void)pin; ledcWrite(ch, duty); }
#endif

void applyDuty(Joint &j, int duty) {
  duty = constrain(duty, -255, 255);
  const bool forward = (duty >= 0) ^ j.invert;
  digitalWrite(j.dirPin, forward ? HIGH : LOW);
  pwmWrite(j.pwmPin, j.pwmCh, (uint8_t)abs(duty));
}

/** delay that can be cut short by a stop request; false = aborted */
bool hold(uint32_t ms) {
  const uint32_t t0 = millis();
  while (millis() - t0 < ms) {
    if (stopRequested) return false;
    delay(5);
  }
  return true;
}

/** Burst move: full-duty pulses with a dwell between them (no gearbox).
 *  Each pulse advances degPerBurst; the count comes from the requested angle. */
bool moveBy(Joint &j, float deltaDeg) {
  if (isnan(j.estDeg)) return false; // angle unknown — must re-home first
  if (fabsf(deltaDeg) < MOVE_TOL_DEG) return true;

  const float clamped = constrain(j.estDeg + deltaDeg, JOINT_MIN_DEG, JOINT_MAX_DEG);
  const float travel = clamped - j.estDeg;
  const int dir = travel > 0 ? 1 : -1;
  const int bursts = (int)lroundf(fabsf(travel) / j.degPerBurst);
  if (bursts == 0) return true;

  for (int i = 0; i < bursts; i++) {
    applyDuty(j, dir * BURST_DUTY);
    const bool on = hold(BURST_MS);
    applyDuty(j, 0); // coast; the brush dwells here
    const bool off = on && hold(PAUSE_MS);
    if (!on || !off) {
      // stopped mid-move: the angle is unknown, force a re-home before anything else
      stopRequested = false;
      j.estDeg = NAN;
      return false;
    }
  }

  delay(SETTLE_MS);
  j.estDeg = j.estDeg + dir * bursts * j.degPerBurst;
  return true;
}

bool moveTo(Joint &j, float deg) { return moveBy(j, deg - j.estDeg); }

// ---------------------------------------------------------------------------
// brush + sensors
// ---------------------------------------------------------------------------
uint8_t brushDuty = 0;
void setBrush(uint8_t duty) {
  brushDuty = duty;
  pwmWrite(BRUSH_PWM, 2, duty);
}

bool estopOk() { return digitalRead(PIN_ESTOP) == LOW; }
bool lidClosed() { return digitalRead(PIN_LID) == LOW; }

volatile float g_levelPct = -1.0f;
volatile uint32_t g_levelAt = 0;
bool levelFresh() { return g_levelAt != 0 && (millis() - g_levelAt) < LEVEL_MAX_AGE_MS; }

// ---------------------------------------------------------------------------
// state
// ---------------------------------------------------------------------------
enum Phase { PH_BOOT, PH_HOMING, PH_PARKED, PH_RUNNING, PH_PARKING, PH_FAULT };
Phase phase = PH_BOOT;
const char *faultReason = nullptr;

bool startRequested = false;
uint8_t curRing = 0;
uint8_t curArc = 0;
uint32_t cycleStartedAt = 0;

const char *phaseName() {
  switch (phase) {
    case PH_HOMING: return "homing";
    case PH_PARKED: return "parked";
    case PH_RUNNING: return "running";
    case PH_PARKING: return "parking";
    case PH_FAULT: return "fault";
    default: return "boot";
  }
}

void enterFault(const char *why) {
  phase = PH_FAULT;
  faultReason = why;
  setBrush(0);
  applyDuty(sh, 0);
  applyDuty(el, 0);
  sh.estDeg = NAN;
  el.estDeg = NAN;
  Serial.printf("FAULT: %s\n", why);
}

// ---------------------------------------------------------------------------
// homing
// ---------------------------------------------------------------------------
bool homeJoint(Joint &j) {
  if (digitalRead(j.homePin) == LOW) { // already on the switch: back off
    applyDuty(j, -HOME_DUTY);
    delay(400);
    applyDuty(j, 0);
    delay(150);
  }
  const uint32_t t0 = millis();
  while (digitalRead(j.homePin) == HIGH) {
    applyDuty(j, HOME_DUTY); // toward negative
    if (millis() - t0 > HOME_TIMEOUT_MS) {
      applyDuty(j, 0);
      return false;
    }
    delay(2);
  }
  applyDuty(j, 0);
  delay(200);
  j.estDeg = 0;
  return true;
}

bool doHoming() {
  setBrush(0);
  Serial.println("homing…");
  if (!homeJoint(sh)) return false;
  if (!homeJoint(el)) return false;
  return true;
}

// ---------------------------------------------------------------------------
// cycle — arcs grouped by ring, re-homing on every ring change
// ---------------------------------------------------------------------------
bool runArc(uint8_t i) {
  const CleanArc a = ARCS[i];
  curArc = i;
  curRing = a.ring;

  const float t1a = a.t1a / 10.0f;
  const float t1b = a.t1b / 10.0f;
  const float t2 = a.t2 / 10.0f;
  Serial.printf("arc %u ring %u: elbow %.1f, shoulder %.1f -> %.1f\n", i, a.ring, t2, t1a, t1b);

  if (!moveTo(el, t2)) return false;   // elbow holds this angle for the sweep
  if (!moveTo(sh, t1a)) return false;

  setBrush(BRUSH_DUTY);
  const bool swept = moveTo(sh, t1b);
  setBrush(0);
  return swept;
}

/** returns false on stop/fault — the caller decides which */
bool runCycle() {
  const uint32_t t0 = millis();
  for (uint8_t ring = 1; ring <= ARC_RINGS; ring++) {
    if (stopRequested) return false;
    if (!doHoming()) { enterFault("home"); return false; }

    for (uint8_t i = 0; i < ARC_COUNT; i++) {
      if (ARCS[i].ring != ring) continue;
      if (stopRequested) return false;
      if (!estopOk()) { enterFault("estop"); return false; }
      if (!lidClosed()) { enterFault("lid"); return false; }
      if (levelFresh() && g_levelPct >= 0 && g_levelPct < MIN_LEVEL_PCT) { enterFault("dry"); return false; }
#if BRUSH_IS_ENABLED
      if (brushDuty > 0 && analogRead(BRUSH_IS) > BRUSH_STALL_RAW) { enterFault("stall"); return false; }
#endif
      if (!runArc(i)) {
        if (!estopOk()) enterFault("estop");
        else if (!lidClosed()) enterFault("lid");
        return false;
      }
    }
  }
  Serial.printf("cycle done in %lu s\n", (millis() - t0) / 1000);
  return true;
}

// ---------------------------------------------------------------------------
// HTTP
// ---------------------------------------------------------------------------
WebServer server(80);

String statusJson() {
  String s = "{";
  s += "\"openLoop\":true";
  s += ",\"phase\":\"" + String(phaseName()) + "\"";
  s += ",\"ring\":" + String(curRing);
  s += ",\"arc\":" + String(curArc);
  s += ",\"arcCount\":" + String(ARC_COUNT);
  s += ",\"progress\":" + String(100.0f * curArc / (float)ARC_COUNT, 1);
  s += ",\"t1\":" + (isnan(sh.estDeg) ? String("null") : String(sh.estDeg, 2));
  s += ",\"t2\":" + (isnan(el.estDeg) ? String("null") : String(el.estDeg, 2));
  s += ",\"brush\":" + String(brushDuty);
  s += ",\"level\":" + String(g_levelPct, 1);
  s += ",\"levelAge\":" + String(g_levelAt ? (millis() - g_levelAt) / 1000 : -1);
  s += ",\"lid\":" + String(lidClosed() ? 1 : 0);
  s += ",\"estop\":" + String(estopOk() ? 0 : 1);
  s += ",\"fault\":";
  s += faultReason ? ("\"" + String(faultReason) + "\"") : "null";
  s += ",\"cycleS\":" + String(cycleStartedAt ? (millis() - cycleStartedAt) / 1000 : 0);
  s += ",\"uptime\":" + String(millis() / 1000);
  s += "}";
  return s;
}

void handleClean() {
  const String mode = server.hasArg("mode") ? server.arg("mode") : "";

  if (mode == "start") {
    if (phase == PH_FAULT) { server.send(409, "application/json", "{\"ok\":false,\"reason\":\"fault\"}"); return; }
    if (phase != PH_PARKED) { server.send(409, "application/json", "{\"ok\":false,\"reason\":\"busy\"}"); return; }
    if (!estopOk()) { server.send(409, "application/json", "{\"ok\":false,\"reason\":\"estop\"}"); return; }
    if (!lidClosed()) { server.send(409, "application/json", "{\"ok\":false,\"reason\":\"lid\"}"); return; }
    if (!levelFresh()) { server.send(409, "application/json", "{\"ok\":false,\"reason\":\"level stale\"}"); return; }
    if (g_levelPct >= 0 && g_levelPct < MIN_LEVEL_PCT) {
      server.send(409, "application/json", "{\"ok\":false,\"reason\":\"dry\"}");
      return;
    }
    stopRequested = false;
    startRequested = true;
    phase = PH_BOOT; // loop() homes first, then runs
    server.send(200, "application/json", "{\"ok\":true,\"phase\":\"starting\"}");
    return;
  }

  if (mode == "stop" || mode == "park") {
    stopRequested = true;
    setBrush(0);
    server.send(200, "application/json", "{\"ok\":true,\"phase\":\"stopping\"}");
    return;
  }

  if (mode == "home" || mode == "reset") {
    if (phase == PH_RUNNING) { server.send(409, "application/json", "{\"ok\":false,\"reason\":\"busy\"}"); return; }
    faultReason = nullptr;
    startRequested = false;
    phase = PH_BOOT;
    server.send(200, "application/json", "{\"ok\":true,\"phase\":\"homing\"}");
    return;
  }

  server.send(200, "application/json", statusJson());
}

void handleRoot() {
  String h = "<!doctype html><meta name=viewport content='width=device-width'>";
  h += "<title>TankGuard cleaner</title><body style='font-family:sans-serif;background:#f2f1ed;color:#14171b'>";
  h += "<h2>TankGuard C1</h2><pre id=v>loading…</pre>";
  h += "<script>async function u(){let j=await(await fetch('/clean')).json();";
  h += "v.textContent=JSON.stringify(j,null,1);}u();setInterval(u,2000);</script></body>";
  server.send(200, "text/html", h);
}

// ---------------------------------------------------------------------------
// level link (own task so HTTP never blocks a timed move)
// ---------------------------------------------------------------------------
void levelTask(void *) {
  for (;;) {
    if (WiFi.status() == WL_CONNECTED) {
      WiFiClient client;
      HTTPClient http;
      http.setTimeout(1200);
      if (http.begin(client, M1_DATA_URL)) {
        if (http.GET() == 200) {
          StaticJsonDocument<256> doc;
          if (!deserializeJson(doc, http.getString()) && doc.containsKey("level")) {
            g_levelPct = doc["level"].as<float>();
            g_levelAt = millis();
          }
        }
        http.end();
      }
    }
    vTaskDelay(pdMS_TO_TICKS(10000));
  }
}

// ---------------------------------------------------------------------------
// setup / loop
// ---------------------------------------------------------------------------
void setup() {
  Serial.begin(SERIAL_BAUD);
  delay(150);
  Serial.println("\nTankGuard C1 cleaner (open loop)");

  pinMode(SH_DIR, OUTPUT);
  pinMode(EL_DIR, OUTPUT);
  pinMode(SH_HOME, INPUT_PULLUP);
  pinMode(EL_HOME, INPUT_PULLUP);
  pinMode(PIN_ESTOP, INPUT_PULLUP);
  pinMode(PIN_LID, INPUT_PULLUP);
  pinMode(STATUS_LED, OUTPUT);

  pwmAttach(SH_PWM, 0);
  pwmAttach(EL_PWM, 1);
  pwmAttach(BRUSH_PWM, 2);
  pwmWrite(SH_PWM, 0, 0);
  pwmWrite(EL_PWM, 1, 0);
  pwmWrite(BRUSH_PWM, 2, 0);

  if (strlen(WIFI_SSID) == 0) {
    WiFi.mode(WIFI_AP);
    WiFi.softAP("TankGuard-Cleaner");
    Serial.print("AP mode, IP: ");
    Serial.println(WiFi.softAPIP());
  } else {
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    const uint32_t t0 = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - t0 < 15000) delay(200);
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());
  }

  server.on("/", handleRoot);
  server.on("/clean", handleClean);
  server.begin();

  xTaskCreatePinnedToCore(levelTask, "level", 4096, nullptr, 1, nullptr, 0);

  if (!doHoming()) enterFault("home");
  else phase = PH_PARKED;
}

void loop() {
  server.handleClient();

  static uint32_t lastTelemetry = 0;

  switch (phase) {
    case PH_BOOT:
      phase = PH_HOMING;
      if (!doHoming()) {
        enterFault("home");
      } else if (startRequested) {
        startRequested = false;
        curArc = 0;
        curRing = 0;
        cycleStartedAt = millis();
        phase = PH_RUNNING;
      } else {
        phase = PH_PARKED;
      }
      break;

    case PH_RUNNING: {
      const bool ok = runCycle();
      if (phase == PH_FAULT) break;              // interlock tripped
      if (!ok || stopRequested) {
        stopRequested = false;
        phase = PH_PARKING;
        break;
      }
      moveTo(sh, PARK_T1 / 10.0f);
      moveTo(el, PARK_T2 / 10.0f);
      cycleStartedAt = 0;
      phase = PH_PARKED;
      break;
    }

    case PH_PARKING:
      // after a stop the angle estimate is invalid; re-home before parking
      if (isnan(sh.estDeg) || isnan(el.estDeg)) {
        phase = PH_BOOT;
        break;
      }
      moveTo(sh, PARK_T1 / 10.0f);
      moveTo(el, PARK_T2 / 10.0f);
      curArc = 0;
      curRing = 0;
      cycleStartedAt = 0;
      phase = PH_PARKED;
      break;

    default:
      break;
  }

  digitalWrite(STATUS_LED, phase == PH_FAULT ? (millis() / 250) % 2 : (phase == PH_RUNNING ? HIGH : LOW));

  if (millis() - lastTelemetry > 5000) {
    lastTelemetry = millis();
    Serial.printf("phase=%s ring=%u arc=%u t1=%.1f t2=%.1f level=%.0f\n", phaseName(), curRing, curArc,
                  sh.estDeg, el.estDeg, g_levelPct);
  }

  delay(5);
}
