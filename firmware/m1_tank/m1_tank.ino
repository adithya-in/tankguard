/*
 * TankGuard tank-side firmware (ESP8266) - M1 monitor
 *
 * Hardware (NodeMCU):
 *   I2C: SDA=D2(4)  SCL=D1(5)   -> ADS1115 (0x48)
 *     A0 = turbidity SEN0189 (via 10k/10k divider)
 *     A1 = TDS SEN0244
 *     A2 = pH SEN0161-V2
 *   DS18B20 DQ = D6(12)   (+4.7k pull-up to 3.3V)
 *   JSN-SR04T TRIG=D7(13) ECHO=D5(14) (echo via 1k/1k divider)
 *
 * Optional nRF24L01+ (USE_NRF24=1) moves DS18B20 to D4, ultrasonic to TX/RX,
 * and adds CE=D0 / CSN=D3. See NRF24_LONG_RANGE.md.
 *
 * Two-arm BTS7960 (USE_ARMS=1, Wi-Fi only): D5/D6/D7/D8 PWM, 1 s left ->
 * 1 s right sweep, browser manual/auto control. Sensors move to D0/D3/D4.
 *
 * Serves JSON for the home module:
 *   GET /data   -> {"score":..,"level":..,"ph":..,"turb":..,"tds":..,"temp":..}
 *   GET /arm?m=A&d=left|right|stop&pwm=180&ms=1000
 *   GET /auto?on=1|0
 *   GET /armstatus
 *
 * NOTE: this build runs continuously because it hosts an HTTP server, so the
 * ESP8266 cannot deep-sleep. Solar sizing must cover continuous Wi-Fi.
 */

#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <Wire.h>
#include <Adafruit_ADS1X15.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <math.h>
#include "config.h"

#if USE_NRF24
#include "nrf_link.h"
RF24 radio(NRF_CE, NRF_CSN);
#define TG_SERIAL_BEGIN()
#define TG_PRINT(...)
#define TG_PRINTLN(...)
#else
#define TG_SERIAL_BEGIN() do { Serial.begin(115200); delay(100); } while (0)
#define TG_PRINT(...) Serial.print(__VA_ARGS__)
#define TG_PRINTLN(...) Serial.println(__VA_ARGS__)
#endif

Adafruit_ADS1115 ads;
OneWire oneWire(DS18B20_PIN);
DallasTemperature ds(&oneWire);
ESP8266WebServer server(80);

struct Readings {
  float score = 0;
  float level = 0;
  float ph = 7.0;
  float turb = 0;
  float tds = 0;
  float temp = 25.0;
};
Readings r;

unsigned long lastSampleMs = 0;
bool adsOk = false;

// ------------------------------ arms --------------------------------------
#if USE_ARMS
enum ArmDir { ARM_STOP = 0, ARM_LEFT = 1, ARM_RIGHT = 2 };

struct Arm {
  uint8_t rpwm;
  uint8_t lpwm;
  ArmDir dir;
  unsigned long stopAt;
};

Arm armA = {ARM_A_RPWM, ARM_A_LPWM, ARM_STOP, 0};
Arm armB = {ARM_B_RPWM, ARM_B_LPWM, ARM_STOP, 0};

int armPwm = ARM_PWM_DEFAULT;
unsigned long armTravelMs = ARM_TRAVEL_MS;
bool autoMode = false;
enum AutoPhase { AUTO_IDLE, AUTO_LEFT, AUTO_PAUSE_L, AUTO_RIGHT, AUTO_PAUSE_R };
AutoPhase autoPhase = AUTO_IDLE;
unsigned long autoAt = 0;

const char* armDirName(ArmDir d) {
  if (d == ARM_LEFT) return "left";
  if (d == ARM_RIGHT) return "right";
  return "stop";
}

void armWrite(Arm &a, ArmDir dir, int pwm) {
  if (dir == ARM_LEFT) {
    analogWrite(a.rpwm, 0);
    analogWrite(a.lpwm, pwm);
  } else if (dir == ARM_RIGHT) {
    analogWrite(a.rpwm, pwm);
    analogWrite(a.lpwm, 0);
  } else {
    analogWrite(a.rpwm, 0);
    analogWrite(a.lpwm, 0);
  }
}

void armStop(Arm &a) {
  armWrite(a, ARM_STOP, 0);
  a.dir = ARM_STOP;
}

void armStopBoth() {
  armStop(armA);
  armStop(armB);
}

void armStart(Arm &a, ArmDir dir, int pwm, unsigned long ms) {
  TG_PRINT("arm start RPWM=GPIO"); TG_PRINT(a.rpwm);
  TG_PRINT(" LPWM=GPIO"); TG_PRINT(a.lpwm);
  TG_PRINT(" dir="); TG_PRINT((int)dir);
  TG_PRINT(" pwm="); TG_PRINTLN(pwm);
  if (a.dir != ARM_STOP && a.dir != dir) {
    armWrite(a, ARM_STOP, 0);
    delay(ARM_DEAD_MS);
  }
  armWrite(a, dir, pwm);
  a.dir = dir;
  a.stopAt = millis() + ms;
}

void armStartBoth(ArmDir dir, int pwm, unsigned long ms) {
  armWrite(armA, ARM_STOP, 0);
  armWrite(armB, ARM_STOP, 0);
  delay(ARM_DEAD_MS);
  unsigned long stop = millis() + ms;
  armWrite(armA, dir, pwm);
  armWrite(armB, dir, pwm);
  armA.dir = dir;
  armA.stopAt = stop;
  armB.dir = dir;
  armB.stopAt = stop;
}

void armUpdate(Arm &a) {
  if (a.dir != ARM_STOP && (long)(millis() - a.stopAt) >= 0) armStop(a);
}

void autoStop() {
  autoMode = false;
  autoPhase = AUTO_IDLE;
  armStopBoth();
}

void autoStart() {
  autoMode = true;
  autoPhase = AUTO_LEFT;
  armStartBoth(ARM_LEFT, armPwm, armTravelMs);
  autoAt = millis();
}

void autoUpdate() {
  if (!autoMode) return;
  unsigned long now = millis();
  switch (autoPhase) {
    case AUTO_LEFT:
      if ((long)(now - autoAt) >= (long)armTravelMs) {
        armStopBoth();
        autoPhase = AUTO_PAUSE_L;
        autoAt = now;
      }
      break;
    case AUTO_PAUSE_L:
      if ((long)(now - autoAt) >= (long)ARM_AUTO_PAUSE_MS) {
        autoPhase = AUTO_RIGHT;
        armStartBoth(ARM_RIGHT, armPwm, armTravelMs);
        autoAt = millis();
      }
      break;
    case AUTO_RIGHT:
      if ((long)(now - autoAt) >= (long)armTravelMs) {
        armStopBoth();
        autoPhase = AUTO_PAUSE_R;
        autoAt = now;
      }
      break;
    case AUTO_PAUSE_R:
      if ((long)(now - autoAt) >= (long)ARM_AUTO_PAUSE_MS) {
        autoPhase = AUTO_LEFT;
        armStartBoth(ARM_LEFT, armPwm, armTravelMs);
        autoAt = millis();
      }
      break;
    default:
      break;
  }
}

void armInit() {
  digitalWrite(ARM_A_RPWM, LOW);
  digitalWrite(ARM_A_LPWM, LOW);
  digitalWrite(ARM_B_RPWM, LOW);
  digitalWrite(ARM_B_LPWM, LOW);
  pinMode(ARM_A_RPWM, OUTPUT);
  pinMode(ARM_A_LPWM, OUTPUT);
  pinMode(ARM_B_RPWM, OUTPUT);
  pinMode(ARM_B_LPWM, OUTPUT);
  analogWriteFreq(20000);
  analogWriteRange(1023);
  armStopBoth();
}

String armStatusJson() {
  String s = "{";
  s += "\"auto\":";
  s += autoMode ? "1" : "0";
  s += ",\"a\":\"";
  s += armDirName(armA.dir);
  s += "\",\"b\":\"";
  s += armDirName(armB.dir);
  s += "\",\"pwm\":";
  s += String(armPwm);
  s += ",\"travel\":";
  s += String(armTravelMs);
  s += "}";
  return s;
}
#endif

// ------------------------------ sensors -----------------------------------
float readVolts(uint8_t ch) {
  if (!adsOk) return 0.0f;
  ads.setGain(GAIN_ONE);             // +/-4.096 V
  int16_t raw = ads.readADC_SingleEnded(ch);
  return ads.computeVolts(raw);
}

float turbidityNTU(float volts) {
  float v = volts * TURB_DIV;
  if (v >= 4.2f) return 0.0f;
  if (v <= 2.5f) return 3000.0f;
  float ntu = -1120.4f * v * v + 5742.3f * v - 4352.9f;
  if (ntu < 0) ntu = 0;
  if (ntu > 3000) ntu = 3000;
  return ntu;
}

float tdsPPM(float volts, float tempC) {
  float v = volts;
  if (v < 0) v = 0;
  float comp = 1.0f + 0.02f * (tempC - 25.0f);
  float ppm = (133.42f * v * v * v - 255.86f * v * v + 857.39f * v) * 0.5f / comp;
  if (ppm < 0) ppm = 0;
  if (ppm > 5000) ppm = 5000;
  return ppm;
}

float phValue(float volts) {
  float p = PH_SLOPE * volts + PH_OFFSET;
  if (p < 0) p = 0;
  if (p > 14) p = 14;
  return p;
}

float readLevel() {
  digitalWrite(PIN_TRIG, LOW);
  delayMicroseconds(4);
  digitalWrite(PIN_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(PIN_TRIG, LOW);
  unsigned long dur = pulseIn(PIN_ECHO, HIGH, 30000UL);
  if (dur == 0) return -1.0f;
  float distance = dur / 58.0f;
  if (distance < 2.0f || distance > TANK_DEPTH_CM + 30.0f) return -1.0f;
  float lvl = (TANK_DEPTH_CM - distance) / TANK_DEPTH_CM * 100.0f;
  if (lvl < 0) lvl = 0;
  if (lvl > 100) lvl = 100;
  return lvl;
}

float scoreFrom(float turb, float tds, float ph, float temp) {
  float sTurb = 100.0f - (turb - 5.0f) * (100.0f / 45.0f);
  if (sTurb < 0) sTurb = 0; if (sTurb > 100) sTurb = 100;

  float sTds = 100.0f - (tds - 300.0f) * (100.0f / 700.0f);
  if (sTds < 0) sTds = 0; if (sTds > 100) sTds = 100;

  float dev = fabsf(ph - 7.0f);
  float sPh = 100.0f - dev * 40.0f;
  if (sPh < 0) sPh = 0;

  float tdev = fabsf(temp - 25.0f) - 5.0f;
  if (tdev < 0) tdev = 0;
  float sTemp = 100.0f - tdev * 4.0f;
  if (sTemp < 0) sTemp = 0;

  return 0.40f * sTurb + 0.25f * sTds + 0.25f * sPh + 0.10f * sTemp;
}

void sample() {
  ds.requestTemperatures();
  float t = ds.getTempCByIndex(0);
  if (t != DEVICE_DISCONNECTED_C && t > -20 && t < 90) r.temp = t;

  if (adsOk) {
    r.turb = turbidityNTU(readVolts(0));
    r.tds  = tdsPPM(readVolts(1), r.temp);
    r.ph   = phValue(readVolts(2));
  }

  float lvl = readLevel();
  if (lvl >= 0) r.level = lvl;

  r.score = adsOk ? scoreFrom(r.turb, r.tds, r.ph, r.temp) : 0.0f;
}

// ------------------------------ web ---------------------------------------
String jsonData() {
  String s = "{";
  s += "\"score\":" + String(r.score, 1);
  s += ",\"level\":" + String(r.level, 1);
  s += ",\"ph\":" + String(r.ph, 2);
  s += ",\"turb\":" + String(r.turb, 1);
  s += ",\"tds\":" + String(r.tds, 0);
  s += ",\"temp\":" + String(r.temp, 1);
  s += "}";
  return s;
}

void handleData() {
  server.send(200, "application/json", jsonData());
}

#if USE_ARMS
void handleArm() {
  if (!server.hasArg("m") || !server.hasArg("d")) {
    server.send(400, "application/json", "{\"error\":\"m,d required\"}");
    return;
  }

  String m = server.arg("m");
  String d = server.arg("d");
  m.toUpperCase();
  d.toLowerCase();

  int pwm = server.hasArg("pwm") ? server.arg("pwm").toInt() : armPwm;
  if (pwm < ARM_PWM_FLOOR) pwm = ARM_PWM_FLOOR;
  if (pwm > ARM_PWM_MAX) pwm = ARM_PWM_MAX;

  unsigned long ms = server.hasArg("ms") ? (unsigned long)server.arg("ms").toInt() : ARM_TRAVEL_MS;
  if (ms < 50) ms = 50;
  if (ms > 10000) ms = 10000;

  armPwm = pwm;
  armTravelMs = ms;
  autoStop();

  Arm *a = nullptr;
  if (m == "A") a = &armA;
  else if (m == "B") a = &armB;

  if (!a) {
    server.send(400, "application/json", "{\"error\":\"m must be A or B\"}");
    return;
  }

  if (d == "left") armStart(*a, ARM_LEFT, pwm, ms);
  else if (d == "right") armStart(*a, ARM_RIGHT, pwm, ms);
  else if (d == "stop") armStop(*a);
  else {
    server.send(400, "application/json", "{\"error\":\"d must be left, right or stop\"}");
    return;
  }

  server.send(200, "application/json", armStatusJson());
}

void handleAuto() {
  if (server.hasArg("pwm")) {
    int pwm = server.arg("pwm").toInt();
    if (pwm < ARM_PWM_FLOOR) pwm = ARM_PWM_FLOOR;
    if (pwm > ARM_PWM_MAX) pwm = ARM_PWM_MAX;
    armPwm = pwm;
  }
  if (server.hasArg("ms")) {
    unsigned long ms = (unsigned long)server.arg("ms").toInt();
    if (ms < 50) ms = 50;
    if (ms > 10000) ms = 10000;
    armTravelMs = ms;
  }

  bool on = server.hasArg("on") && server.arg("on").toInt() != 0;
  if (on) autoStart();
  else autoStop();
  server.send(200, "application/json", armStatusJson());
}

void handleArmStatus() {
  server.send(200, "application/json", armStatusJson());
}
#endif

void handleRoot() {
#if USE_ARMS
  String h = R"HTML(
<!doctype html><html><head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>TankGuard tank</title>
<style>
body{font-family:system-ui,sans-serif;background:#071018;color:#cfe;margin:16px}
.card{background:#0d1b26;border:1px solid #1e3445;border-radius:12px;padding:12px;margin:10px 0}
button{font-size:16px;padding:10px 14px;margin:4px;border:0;border-radius:8px;background:#1d4ed8;color:#fff}
button.stop{background:#b91c1c}
button.auto{background:#047857}
input{width:82px;font-size:16px;padding:6px;margin:4px;background:#071018;color:#cfe;border:1px solid #1e3445;border-radius:6px}
pre{white-space:pre-wrap;margin:0}
.hint{color:#8aa;font-size:13px;margin-top:8px}
</style></head><body>
<h2>TankGuard tank</h2>
<div class="card"><b>Mode:</b> <span id="mode">...</span><br>
<button class="auto" onclick="setAuto(1)">Auto sweep</button>
<button class="stop" onclick="setAuto(0)">Stop auto</button></div>
<div class="card"><b>Arm A</b><br>
<button onclick="cmd('A','left')">Left</button>
<button class="stop" onclick="cmd('A','stop')">Stop</button>
<button onclick="cmd('A','right')">Right</button></div>
<div class="card"><b>Arm B</b><br>
<button onclick="cmd('B','left')">Left</button>
<button class="stop" onclick="cmd('B','stop')">Stop</button>
<button onclick="cmd('B','right')">Right</button></div>
<div class="card"><label>PWM <input id="pwm" type="number" min="60" max="1023" value="180"></label>
<label>Travel ms <input id="ms" type="number" min="100" max="5000" value="1000"></label>
<div class="hint">180 = 1000 ms. Raise PWM until the arm moves reliably; it always stops at the end of the travel.</div></div>
<div class="card"><pre id="v">loading...</pre></div>
<script>
const $=id=>document.getElementById(id);
async function cmd(m,d){
  await fetch('/arm?m='+m+'&d='+d+'&pwm='+$('pwm').value+'&ms='+$('ms').value);
  refresh();
}
async function setAuto(on){ await fetch('/auto?on='+on+'&pwm='+$('pwm').value+'&ms='+$('ms').value); refresh(); }
async function refresh(){
  try{
    let j=await(await fetch('/data')).json();
    let a=await(await fetch('/armstatus')).json();
    $('mode').textContent=a.auto?'AUTO':'MANUAL';
    $('v').textContent='Score '+j.score+'\nLevel '+j.level+'%\npH '+j.ph+'\nTurbidity '+j.turb+' NTU\nTDS '+j.tds+' ppm\nTemp '+j.temp+' C\nArm A '+a.a+'\nArm B '+a.b;
    if(document.activeElement!==$('pwm')) $('pwm').value=a.pwm;
    if(document.activeElement!==$('ms')) $('ms').value=a.travel;
  }catch(e){ $('v').textContent='offline'; }
}
refresh(); setInterval(refresh,1000);
</script></body></html>
)HTML";
#else
  String h = "<!doctype html><meta name=viewport content='width=device-width'>";
  h += "<title>TankGuard tank</title><body style='font-family:sans-serif;background:#071018;color:#cfe'>";
  h += "<h2>TankGuard</h2><pre id=v>loading...</pre>";
  h += "<p><a href='/data'>JSON</a></p>";
  h += "<script>async function u(){let j=await(await fetch('/data')).json();";
  h += "v.textContent='Score '+j.score+'\\nLevel '+j.level+'%\\npH '+j.ph+'\\nTurbidity '+j.turb+' NTU\\nTDS '+j.tds+' ppm\\nTemp '+j.temp+' C';}";
  h += "u();setInterval(u,3000);</script></body>";
#endif
  server.send(200, "text/html", h);
}

// ------------------------------ radio -------------------------------------
#if USE_NRF24
void radioBegin() {
  radio.begin();
  nrfConfig(radio);
  radio.setAddressWidth(5);
  radio.openWritingPipe(TG_ADDR);
  radio.stopListening();
}

void radioSend() {
  TankPacket p;
  p.magic = TG_MAGIC;
  p.score = r.score;
  p.level = r.level;
  p.ph    = r.ph;
  p.turb  = r.turb;
  p.tds   = r.tds;
  p.temp  = r.temp;
  radio.write(&p, sizeof(p));
}
#endif

// ------------------------------ setup -------------------------------------
void setup() {
  TG_SERIAL_BEGIN();

#if !USE_MOTORS_ONLY
  pinMode(PIN_TRIG, OUTPUT);
  pinMode(PIN_ECHO, INPUT);
#endif

#if USE_ARMS
  armInit();
#if USE_MOTORS_ONLY
  TG_PRINTLN("Arms: A RPWM=D5/14 LPWM=D6/12 | B RPWM=D7/13 LPWM=D1/5");
  TG_PRINTLN("Motors-only: sensors/I2C disabled, D8 free");
#else
  TG_PRINTLN("Arms: A RPWM=D5/14 LPWM=D6/12 | B RPWM=D7/13 LPWM=D8/15");
  TG_PRINTLN("Sensors: DS18B20=D4 TRIG=D3 ECHO=D0; D8 needs 10k pulldown");
#endif
#endif

#if !USE_MOTORS_ONLY
  Wire.begin(4, 5);          // SDA=D2(4), SCL=D1(5)
  adsOk = ads.begin();
  if (!adsOk) TG_PRINTLN("WARN: ADS1115 not found at 0x48");
  ads.setGain(GAIN_ONE);

  ds.begin();

  sample();
  lastSampleMs = millis();
#else
  adsOk = false;
  lastSampleMs = millis();
#endif

#if USE_NRF24
  radioBegin();
  radioSend();
#else
  if (strlen(WIFI_SSID) == 0) {
    WiFi.mode(WIFI_AP);
    WiFi.softAP("TankGuard-Tank");
    TG_PRINT("AP mode, IP: ");
    TG_PRINTLN(WiFi.softAPIP());
  } else {
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    unsigned long t0 = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - t0 < 15000) {
      delay(200);
      yield();
    }
    TG_PRINT("IP: ");
    TG_PRINTLN(WiFi.localIP());
  }

  server.on("/", handleRoot);
  server.on("/data", handleData);
#if USE_ARMS
  server.on("/arm", handleArm);
  server.on("/auto", handleAuto);
  server.on("/armstatus", handleArmStatus);
#endif
  server.begin();
#endif

  TG_PRINTLN("TankGuard tank-side ready");
}

// ------------------------------ loop --------------------------------------
void loop() {
#if !USE_NRF24
  server.handleClient();
#endif

#if USE_ARMS
  if (autoMode) autoUpdate();
  else {
    armUpdate(armA);
    armUpdate(armB);
  }
#endif

#if !USE_MOTORS_ONLY
  if (millis() - lastSampleMs >= SAMPLE_MS) {
    lastSampleMs = millis();
    sample();
#if USE_NRF24
    radioSend();
#endif
  }
#endif

  delay(2);
}
