/*
 * TankGuard tank-side firmware (ESP8266) - M1 monitor + M2 flush
 *
 * Hardware (NodeMCU):
 *   I2C: SDA=D2(4)  SCL=D1(5)   -> ADS1115 (0x48)
 *     A0 = turbidity SEN0189 (via 10k/10k divider)
 *     A1 = TDS SEN0244
 *     A2 = pH SEN0161-V2
 *   DS18B20 DQ = D6(12)   (+4.7k pull-up to 3.3V)
 *   JSN-SR04T TRIG=D7(13) ECHO=D5(14) (echo via 1k/1k divider)
 *   Flush valve gate = D8(15) (10k pull-down)
 *
 * Optional nRF24L01+ (USE_NRF24=1) moves DS18B20 to D4, ultrasonic to TX/RX,
 * and adds CE=D0 / CSN=D3. See NRF24_LONG_RANGE.md.
 *
 * Serves JSON for the home module:
 *   GET /data   -> {"score":..,"level":..,"ph":..,"turb":..,"tds":..,"temp":..,
 *                   "flush":"idle|running|done","valve":0|1}
 *   GET /flush?force=0|1
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

enum FlushState { FLUSH_IDLE, FLUSH_RUNNING };
FlushState flushState = FLUSH_IDLE;
unsigned long flushStartMs = 0;
unsigned long lastFlushMs = 0;
float turbBeforeFlush = 0;
String flushResult = "idle";

unsigned long lastSampleMs = 0;
bool adsOk = false;

// ------------------------------ valve -------------------------------------
void valveWrite(bool open) {
#if VALVE_ACTIVE_HIGH
  digitalWrite(VALVE_PIN, open ? HIGH : LOW);
#else
  digitalWrite(VALVE_PIN, open ? LOW : HIGH);
#endif
}

void valveInit() {
#if VALVE_ACTIVE_HIGH
  pinMode(VALVE_PIN, OUTPUT);
  digitalWrite(VALVE_PIN, LOW);      // closed at boot
#else
  pinMode(VALVE_PIN, OUTPUT);
  digitalWrite(VALVE_PIN, HIGH);     // closed at boot
#endif
}

// ------------------------------ sensors -----------------------------------
float readVolts(uint8_t ch) {
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
  float vTurb = readVolts(0);
  float vTds  = readVolts(1);
  float vPh   = readVolts(2);

  ds.requestTemperatures();
  float t = ds.getTempCByIndex(0);
  if (t != DEVICE_DISCONNECTED_C && t > -20 && t < 90) r.temp = t;

  r.turb = turbidityNTU(vTurb);
  r.tds  = tdsPPM(vTds, r.temp);
  r.ph   = phValue(vPh);

  float lvl = readLevel();
  if (lvl >= 0) r.level = lvl;

  r.score = scoreFrom(r.turb, r.tds, r.ph, r.temp);
}

// ------------------------------ flush -------------------------------------
bool startFlush(bool force) {
  if (flushState == FLUSH_RUNNING) return false;
  if (!force && r.level < 5.0f) {
    flushResult = "low level";
    return false;
  }
  turbBeforeFlush = r.turb;
  valveWrite(true);
  flushState = FLUSH_RUNNING;
  flushStartMs = millis();
  flushResult = "running";
  TG_PRINTLN("Flush started");
  return true;
}

void serviceFlush() {
  if (flushState != FLUSH_RUNNING) return;
  if (millis() - flushStartMs < (unsigned long)FLUSH_SECONDS * 1000UL) return;

  valveWrite(false);
  flushState = FLUSH_IDLE;
  lastFlushMs = millis();
  flushResult = "done";

  sample();
  if (turbBeforeFlush > 1.0f) {
    float eff = (turbBeforeFlush - r.turb) / turbBeforeFlush * 100.0f;
    TG_PRINT("Flush done, turbidity reduction %: ");
    TG_PRINTLN(eff, 1);
  }
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
  s += ",\"flush\":\"" + flushResult + "\"";
  s += ",\"valve\":" + String(flushState == FLUSH_RUNNING ? 1 : 0);
  s += "}";
  return s;
}

void handleData() {
  server.send(200, "application/json", jsonData());
}

void handleFlush() {
  bool force = false;
  if (server.hasArg("force")) force = server.arg("force").toInt() != 0;
  bool ok = startFlush(force);
  String s = "{\"ok\":";
  s += ok ? "true" : "false";
  s += ",\"flush\":\"" + flushResult + "\"}";
  server.send(ok ? 200 : 409, "application/json", s);
}

void handleRoot() {
  String h = "<!doctype html><meta name=viewport content='width=device-width'>";
  h += "<title>TankGuard tank</title><body style='font-family:sans-serif;background:#071018;color:#cfe'>";
  h += "<h2>TankGuard</h2><pre id=v>loading...</pre>";
  h += "<p><a href='/flush?force=0'>Flush</a> | <a href='/flush?force=1'>Force flush</a> | <a href='/data'>JSON</a></p>";
  h += "<script>async function u(){let j=await(await fetch('/data')).json();";
  h += "v.textContent='Score '+j.score+'\\nLevel '+j.level+'%\\npH '+j.ph+'\\nTurbidity '+j.turb+' NTU\\nTDS '+j.tds+' ppm\\nTemp '+j.temp+' C\\nFlush '+j.flush;}";
  h += "u();setInterval(u,3000);</script></body>";
  server.send(200, "text/html", h);
}

// ------------------------------ radio -------------------------------------
#if USE_NRF24
void radioBegin() {
  radio.begin();
  nrfConfig(radio);
  radio.setAddressWidth(5);
  radio.openWritingPipe(TG_ADDR);
  radio.openReadingPipe(1, TG_ADDR);
  radio.startListening();
}

uint8_t flushCode() {
  if (flushState == FLUSH_RUNNING) return 1;
  if (flushResult == "done") return 2;
  return 0;
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
  p.flush = flushCode();
  p.valve = (flushState == FLUSH_RUNNING) ? 1 : 0;
  radio.stopListening();
  radio.write(&p, sizeof(p));
  radio.startListening();
}

void radioPoll() {
  if (!radio.available()) return;
  CmdPacket c;
  radio.read(&c, sizeof(c));
  if (c.magic == TG_MAGIC && (c.cmd == 1 || c.cmd == 2)) {
    startFlush(c.cmd == 2);
  }
}
#endif

// ------------------------------ setup -------------------------------------
void setup() {
  TG_SERIAL_BEGIN();

  valveInit();

  pinMode(PIN_TRIG, OUTPUT);
  pinMode(PIN_ECHO, INPUT);

  Wire.begin(4, 5);          // SDA=D2(4), SCL=D1(5)
  adsOk = ads.begin();
  if (!adsOk) TG_PRINTLN("WARN: ADS1115 not found at 0x48");
  ads.setGain(GAIN_ONE);

  ds.begin();

  sample();
  lastSampleMs = millis();

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
  server.on("/flush", handleFlush);
  server.begin();
#endif

  TG_PRINTLN("TankGuard tank-side ready");
}

// ------------------------------ loop --------------------------------------
void loop() {
#if USE_NRF24
  radioPoll();
#else
  server.handleClient();
#endif

  if (millis() - lastSampleMs >= SAMPLE_MS) {
    lastSampleMs = millis();
    sample();
#if USE_NRF24
    radioSend();
#endif
  }

  serviceFlush();

#if AUTO_FLUSH
  if (flushState == FLUSH_IDLE &&
      millis() - lastFlushMs > AUTO_FLUSH_MIN_INTERVAL_MS &&
      r.level > AUTO_FLUSH_MIN_LEVEL &&
      r.score < AUTO_FLUSH_SCORE) {
    startFlush(false);
  }
#endif

  delay(2);
}
