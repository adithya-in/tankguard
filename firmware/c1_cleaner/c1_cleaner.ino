/*
 * TankGuard C1 — cleaning-arm controller (ESP8266, OPEN LOOP)
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
 *   - e-stop and lid are in series on one fail-safe loop (PIN_SAFETY)
 *   - level comes from the M1 tank unit; below MIN_LEVEL_PCT the cycle stops
 *   - brush stall cut-out (optional, BRUSH_IS_ENABLED)
 *   - stop is honoured between moves, never mid-move
 *
 * HTTP
 *   GET /                               -> controller page (ui.h)
 *   GET /clean                          -> status JSON
 *   GET /clean?mode=start|stop|park|home|reset|check
 *   GET /jog?joint=sh|el&bursts=N&dir=1|-1
 */

#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <ESP8266HTTPClient.h>
#include <ArduinoJson.h>

#include "config.h"
#include "path.h"
#include "ui.h"

// ---------------------------------------------------------------------------
// joints (open loop)
// ---------------------------------------------------------------------------
struct Joint {
  const char *name;
  uint8_t rpwmPin, lpwmPin, homePin;
  uint8_t rpwmCh, lpwmCh;
  bool invert;
  float degFwd, degBack; // calibrated advance per burst, per direction
  float estDeg;          // dead-reckoned angle, 0 = home switch
  int duty;              // last commanded duty
  int lastDir;           // last non-zero direction
  uint32_t bursts;       // bursts fired since the last home
};

Joint sh = {"shoulder", ARM_A_RPWM, ARM_A_LPWM, SH_HOME, 0, 1, SH_DIR_INVERT,
            SH_DEG_PER_BURST_FWD, SH_DEG_PER_BURST_BACK, 0, 0, 0, 0};
Joint el = {"elbow", ARM_B_RPWM, ARM_B_LPWM, EL_HOME, 2, 3, EL_DIR_INVERT,
            EL_DEG_PER_BURST_FWD, EL_DEG_PER_BURST_BACK, 0, 0, 0, 0};

volatile bool stopRequested = false;
uint32_t lastMoveMs = 0;

// ESP8266: analogWrite, 20 kHz and 8-bit range set in setup().
static inline void pwmAttach(uint8_t pin, uint8_t ch) {
  (void)ch;
  pinMode(pin, OUTPUT);
  analogWrite(pin, 0);
}
static inline void pwmWrite(uint8_t pin, uint8_t ch, uint8_t duty) {
  (void)ch;
  analogWrite(pin, duty);
}

/** Drive one joint through a dual-PWM driver: RPWM forward, LPWM reverse.
 *  A reversal coasts first, so the bridge never changes direction under load. */
void applyDuty(Joint &j, int duty) {
  duty = constrain(duty, -255, 255);
  const int dir = (duty > 0) - (duty < 0);
  const uint8_t mag = (uint8_t)abs(duty);
  if (dir != 0 && j.lastDir != 0 && dir != j.lastDir) {
    pwmWrite(j.rpwmPin, j.rpwmCh, 0);
    pwmWrite(j.lpwmPin, j.lpwmCh, 0);
    delay(DEAD_TIME_MS);
  }
  if (dir == 0) {
    pwmWrite(j.rpwmPin, j.rpwmCh, 0);
    pwmWrite(j.lpwmPin, j.lpwmCh, 0);
  } else {
    const bool forward = (dir > 0) ^ j.invert;
    pwmWrite(j.rpwmPin, j.rpwmCh, forward ? mag : 0);
    pwmWrite(j.lpwmPin, j.lpwmCh, forward ? 0 : mag);
    j.lastDir = dir;
  }
  j.duty = duty;
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

/** One burst: ramp up, hold, coast. The ramp keeps the inrush off the supply. */
bool burst(Joint &j, int dir) {
  const int target = dir * BURST_DUTY;
  const int steps = 8;
  for (int i = 1; i <= steps; i++) {
    applyDuty(j, target * i / steps);
    if (!hold(RAMP_MS / steps)) {
      applyDuty(j, 0);
      return false;
    }
  }
  const bool ok = hold(BURST_MS - RAMP_MS);
  applyDuty(j, 0);
  return ok;
}

/** Burst move: pulses with a dwell between them (no gearbox).
 *  Each pulse advances degFwd or degBack; the count comes from the angle. */
bool moveBy(Joint &j, float deltaDeg) {
  if (isnan(j.estDeg)) return false; // angle unknown — must re-home first
  if (fabsf(deltaDeg) < MOVE_TOL_DEG) return true;

  const float clamped = constrain(j.estDeg + deltaDeg, JOINT_MIN_DEG, JOINT_MAX_DEG);
  const float travel = clamped - j.estDeg;
  const int dir = travel > 0 ? 1 : -1;
  const float perBurst = dir > 0 ? j.degFwd : j.degBack;
  const int bursts = (int)lroundf(fabsf(travel) / perBurst);
  if (bursts == 0) return true;

  const uint32_t t0 = millis();
  for (int i = 0; i < bursts; i++) {
    const bool on = burst(j, dir);
    const bool off = on && hold(PAUSE_MS);
    if (!on || !off) {
      // stopped mid-move: the angle is unknown, force a re-home before anything else
      stopRequested = false;
      j.estDeg = NAN;
      return false;
    }
  }

  if (!hold(SETTLE_MS)) {
    j.estDeg = NAN;
    return false;
  }
  j.estDeg = j.estDeg + dir * bursts * perBurst;
  j.bursts += bursts;
  lastMoveMs = millis() - t0;
  return true;
}

bool moveTo(Joint &j, float deg) { return moveBy(j, deg - j.estDeg); }

// ---------------------------------------------------------------------------
// brush + sensors
// ---------------------------------------------------------------------------
uint8_t brushDuty = 0;
void setPump(bool on) {
  digitalWrite(PUMP_PIN, (on == (PUMP_ACTIVE_HIGH != 0)) ? HIGH : LOW);
}

void setBrush(uint8_t duty) {
  brushDuty = duty;
  pwmWrite(BRUSH_PWM, 4, duty);
  // the pump follows the brush: suction only while scrubbing, so the head never
  // sits sealed against the floor between passes
  setPump(duty > 0);
}

bool safetyClosed() { return digitalRead(PIN_SAFETY) == HIGH; }
bool estopOk() { return safetyClosed(); }
bool lidClosed() { return safetyClosed(); }

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
uint8_t runRings = ARC_RINGS;   // demo can stop after ring 1 or 2
uint8_t arcsDone = 0;
uint32_t cycleStartedAt = 0;

uint8_t arcCountFor(uint8_t rings) {
  uint8_t n = 0;
  for (uint8_t i = 0; i < ARC_COUNT; i++) {
    if (ARCS[i].ring <= rings) n++;
  }
  return n;
}

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
/** Run toward the switch until it reads LOW for HOME_DEBOUNCE_MS. */
bool seekHome(Joint &j, uint8_t duty, uint32_t timeoutMs) {
  const uint32_t t0 = millis();
  uint32_t lowSince = 0;
  applyDuty(j, duty); // positive duty moves toward home
  while (millis() - t0 < timeoutMs) {
    if (stopRequested) {
      applyDuty(j, 0);
      return false;
    }
    if (digitalRead(j.homePin) == LOW) {
      if (lowSince == 0) lowSince = millis();
      if (millis() - lowSince >= HOME_DEBOUNCE_MS) {
        applyDuty(j, 0);
        return true;
      }
    } else {
      lowSince = 0;
    }
    delay(2);
  }
  applyDuty(j, 0);
  Serial.printf("%s: no switch after %lu ms (pin reads %d)\n", j.name, (unsigned long)timeoutMs,
                digitalRead(j.homePin));
  return false;
}

bool homeJoint(Joint &j) {
  if (digitalRead(j.homePin) == LOW) { // already on the switch: back off
    applyDuty(j, -HOME_DUTY);
    hold(HOME_BACKOFF_MS);
    applyDuty(j, 0);
    hold(150);
  }

  // fast approach
  if (!seekHome(j, HOME_DUTY, HOME_TIMEOUT_MS)) return false;

  // back off at full duty, then re-seek slowly: the second contact is the
  // repeatable zero, and a slow approach keeps the overshoot small
  applyDuty(j, -HOME_DUTY);
  hold(HOME_BACKOFF_MS);
  applyDuty(j, 0);
  hold(120);
  if (!seekHome(j, HOME_SLOW_DUTY, HOME_TIMEOUT_MS / 2)) return false;

  applyDuty(j, 0);
  hold(150);
  j.estDeg = 0;
  j.bursts = 0;
  return true;
}

bool doHoming() {
  setBrush(0);
#if HOME_BYPASS
  Serial.println("home bypass: current pose is zero");
  sh.estDeg = 0;
  el.estDeg = 0;
  sh.bursts = 0;
  el.bursts = 0;
  return true;
#else
  Serial.printf("homing: sh pin=%d el pin=%d\n", digitalRead(SH_HOME), digitalRead(EL_HOME));
  if (!homeJoint(sh)) {
    Serial.println("home failed: shoulder");
    return false;
  }
  Serial.println("shoulder home ok");
  if (!homeJoint(el)) {
    Serial.println("home failed: elbow");
    return false;
  }
  Serial.println("elbow home ok");
  return true;
#endif
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
  for (uint8_t ring = 1; ring <= runRings; ring++) {
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
      arcsDone++;
    }
  }
  Serial.printf("cycle done in %lu s\n", (millis() - t0) / 1000);
  return true;
}

// ---------------------------------------------------------------------------
// HTTP
// ---------------------------------------------------------------------------
ESP8266WebServer server(80);

String statusJson() {
  const uint8_t total = arcCountFor(runRings);
  String s = "{";
  s += "\"openLoop\":true";
  s += ",\"phase\":\"" + String(phaseName()) + "\"";
  s += ",\"ring\":" + String(curRing);
  s += ",\"arc\":" + String(curArc);
  s += ",\"rings\":" + String(runRings);
  s += ",\"arcCount\":" + String(total);
  s += ",\"arcsDone\":" + String(arcsDone);
  s += ",\"progress\":" + String(100.0f * arcsDone / (float)(total ? total : 1), 1);
  s += ",\"t1\":" + (isnan(sh.estDeg) ? String("null") : String(sh.estDeg, 2));
  s += ",\"t2\":" + (isnan(el.estDeg) ? String("null") : String(el.estDeg, 2));
  s += ",\"brush\":" + String(brushDuty);
  s += ",\"pump\":" + String(brushDuty > 0 ? 1 : 0);
  s += ",\"level\":" + String(g_levelPct, 1);
  s += ",\"levelAge\":" + String(g_levelAt ? (millis() - g_levelAt) / 1000 : -1);
  s += ",\"lid\":" + String(lidClosed() ? 1 : 0);
  s += ",\"estop\":" + String(estopOk() ? 0 : 1);
  s += ",\"fault\":";
  s += faultReason ? ("\"" + String(faultReason) + "\"") : "null";
  s += ",\"cycleS\":" + String(cycleStartedAt ? (millis() - cycleStartedAt) / 1000 : 0);
  s += ",\"uptime\":" + String(millis() / 1000);
  s += ",\"bursts\":" + String(sh.bursts + el.bursts);
  s += ",\"lastMoveMs\":" + String(lastMoveMs);
  s += ",\"home1\":" + String(digitalRead(SH_HOME) == LOW ? 1 : 0);
  s += ",\"home2\":" + String(digitalRead(EL_HOME) == LOW ? 1 : 0);
  s += ",\"duty1\":" + String(sh.duty);
  s += ",\"duty2\":" + String(el.duty);
  s += ",\"mode\":\"";
  s += (strlen(WIFI_SSID) == 0) ? "ap" : "sta";
  s += "\"";
  s += "}";
  return s;
}

void handleClean() {
  const String mode = server.hasArg("mode") ? server.arg("mode") : "";
  const bool force = server.hasArg("force") && server.arg("force") == "1";

  if (mode == "start") {
    if (phase == PH_FAULT) { server.send(409, "application/json", "{\"ok\":false,\"reason\":\"fault\"}"); return; }
    if (phase != PH_PARKED) { server.send(409, "application/json", "{\"ok\":false,\"reason\":\"busy\"}"); return; }
    if (!estopOk()) { server.send(409, "application/json", "{\"ok\":false,\"reason\":\"estop\"}"); return; }
    if (!lidClosed()) { server.send(409, "application/json", "{\"ok\":false,\"reason\":\"lid\"}"); return; }
    if (!force && !levelFresh()) { server.send(409, "application/json", "{\"ok\":false,\"reason\":\"level stale\"}"); return; }
    if (!force && g_levelPct >= 0 && g_levelPct < MIN_LEVEL_PCT) {
      server.send(409, "application/json", "{\"ok\":false,\"reason\":\"dry\"}");
      return;
    }
    const int rings = server.arg("rings").toInt();
    runRings = (rings >= 1 && rings <= ARC_RINGS) ? (uint8_t)rings : ARC_RINGS;
    arcsDone = 0;
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
    arcsDone = 0;
    phase = PH_BOOT;
    server.send(200, "application/json", "{\"ok\":true,\"phase\":\"homing\"}");
    return;
  }

  if (mode == "check") {
    String s = "{\"ok\":true";
    s += ",\"estop\":" + String(estopOk() ? 1 : 0);
    s += ",\"lid\":" + String(lidClosed() ? 1 : 0);
    s += ",\"level\":" + String(g_levelPct, 1);
    s += ",\"levelAge\":" + String(g_levelAt ? (millis() - g_levelAt) / 1000 : -1);
    s += ",\"levelFresh\":" + String(levelFresh() ? 1 : 0);
    s += ",\"home1\":" + String(digitalRead(SH_HOME) == LOW ? 1 : 0);
    s += ",\"home2\":" + String(digitalRead(EL_HOME) == LOW ? 1 : 0);
    s += ",\"angleValid\":" + String((!isnan(sh.estDeg) && !isnan(el.estDeg)) ? 1 : 0);
    s += ",\"phase\":\"" + String(phaseName()) + "\"";
    s += ",\"rings\":" + String(runRings);
    s += "}";
    server.send(200, "application/json", s);
    return;
  }

  server.send(200, "application/json", statusJson());
}

#if ENABLE_JOG
/** /jog?joint=sh|el&bursts=5&dir=1 — fire a known number of bursts so the
 *  advance per burst can be measured with a protractor and put in config.h. */
void handleJog() {
  if (phase == PH_RUNNING || phase == PH_HOMING || phase == PH_PARKING) {
    server.send(409, "application/json", "{\"ok\":false,\"reason\":\"busy\"}");
    return;
  }
  if (!estopOk() || !lidClosed()) {
    server.send(409, "application/json", "{\"ok\":false,\"reason\":\"interlock\"}");
    return;
  }

  Joint &j = (server.arg("joint") == "el") ? el : sh;
  const int dir = server.arg("dir").toInt() < 0 ? -1 : 1;
  const int n = constrain(server.arg("bursts").toInt(), 1, JOG_MAX_BURSTS);

  setBrush(0);
  for (int i = 0; i < n; i++) {
    if (!burst(j, dir) || !hold(PAUSE_MS)) {
      j.estDeg = NAN;
      server.send(500, "application/json", "{\"ok\":false,\"reason\":\"stopped\"}");
      return;
    }
  }

  const float perBurst = dir > 0 ? j.degFwd : j.degBack;
  if (!isnan(j.estDeg)) j.estDeg += dir * n * perBurst;
  j.bursts += n;

  String s = "{\"ok\":true,\"joint\":\"" + String(j.name) + "\"";
  s += ",\"bursts\":" + String(n);
  s += ",\"dir\":" + String(dir);
  s += ",\"angle\":" + (isnan(j.estDeg) ? String("null") : String(j.estDeg, 2));
  s += ",\"expectedDeg\":" + String(dir * n * perBurst, 2);
  s += "}";
  server.send(200, "application/json", s);
}
#endif

void handleRoot() {
  server.sendHeader("Cache-Control", "no-store");
  server.send_P(200, "text/html", UI_HTML);
}

// ---------------------------------------------------------------------------
// level link (own task so HTTP never blocks a timed move)
// ---------------------------------------------------------------------------
void pollLevel() {
  static uint32_t last = 0;
  if (millis() - last < 10000) return;
  last = millis();
  if (WiFi.status() != WL_CONNECTED) return;
  WiFiClient client;
  HTTPClient http;
  http.setTimeout(800);
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

// ---------------------------------------------------------------------------
// setup / loop
// ---------------------------------------------------------------------------
void setup() {
  Serial.begin(SERIAL_BAUD);
  delay(150);
  Serial.println("\nTankGuard C1 cleaner (open loop)");

  pinMode(SH_HOME, INPUT_PULLUP);
  pinMode(EL_HOME, INPUT_PULLUP);
  pinMode(PIN_SAFETY, INPUT); // external 10k pull-down; HIGH = safe
  if (STATUS_LED >= 0) pinMode(STATUS_LED, OUTPUT);
  pinMode(PUMP_PIN, OUTPUT);
  setPump(false);

  analogWriteFreq(20000);
  analogWriteRange(255);
  pwmAttach(ARM_A_RPWM, 0);
  pwmAttach(ARM_A_LPWM, 1);
  pwmAttach(ARM_B_RPWM, 2);
  pwmAttach(ARM_B_LPWM, 3);
  pwmAttach(BRUSH_PWM, 4);
  pwmWrite(ARM_A_RPWM, 0, 0);
  pwmWrite(ARM_A_LPWM, 1, 0);
  pwmWrite(ARM_B_RPWM, 2, 0);
  pwmWrite(ARM_B_LPWM, 3, 0);
  pwmWrite(BRUSH_PWM, 4, 0);

  if (strlen(WIFI_SSID) == 0) {
    WiFi.mode(WIFI_AP);
    WiFi.softAP(AP_SSID, AP_PASS);
    Serial.printf("hotspot: %s (password %s)\n", AP_SSID, AP_PASS);
    Serial.print("open http://");
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
#if ENABLE_JOG
  server.on("/jog", handleJog);
#endif
  server.begin();

  if (!doHoming()) enterFault("home");
  else phase = PH_PARKED;
}

void loop() {
  server.handleClient();
  if (phase == PH_PARKED) pollLevel();

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

  if (STATUS_LED >= 0) {
    digitalWrite(STATUS_LED, phase == PH_FAULT ? (millis() / 250) % 2 : (phase == PH_RUNNING ? HIGH : LOW));
  }

  if (millis() - lastTelemetry > 5000) {
    lastTelemetry = millis();
    Serial.printf("phase=%s ring=%u arc=%u t1=%.1f t2=%.1f level=%.0f\n", phaseName(), curRing, curArc,
                  sh.estDeg, el.estDeg, g_levelPct);
  }

  delay(5);
}
