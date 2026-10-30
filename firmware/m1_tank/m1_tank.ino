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
 * Serves the web dashboard from LittleFS and JSON for clients:
 *   GET /data   -> {"score":..,"level":..,"ph":..,"turb":..,"tds":..,"temp":..}
 *   GET /...    -> webapp bundle (LittleFS, pre-gzipped — see webapp/tools/build-device-bundle.mjs)
 *
 * The webapp bundle is flashed to the FS area (4M1M layout: 1 MB at 0x300000):
 *   node webapp/tools/build-device-bundle.mjs      -> device-littlefs.bin
 *   esptool.py --port <PORT> write_flash 0x300000 device-littlefs.bin
 * If LittleFS is empty the old inline status page is served instead.
 *
 * NOTE: this build runs continuously because it hosts an HTTP server, so the
 * ESP8266 cannot deep-sleep. Solar sizing must cover continuous Wi-Fi.
 */

#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <ESP8266mDNS.h>
#include <LittleFS.h>
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
bool fsOk = false;

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

// ------------------------------ web ---------------------------------------

// ---- static bundle from LittleFS (the webapp is pre-gzipped on the PC) ----
static const char* mimeFor(const String& path) {
  if (path.endsWith(".html")) return "text/html";
  if (path.endsWith(".js"))   return "application/javascript";
  if (path.endsWith(".css"))  return "text/css";
  if (path.endsWith(".json")) return "application/json";
  if (path.endsWith(".svg"))  return "image/svg+xml";
  if (path.endsWith(".ico"))  return "image/x-icon";
  if (path.endsWith(".woff2")) return "font/woff2";
  if (path.endsWith(".png"))  return "image/png";
  return "application/octet-stream";
}

// Serve a file from LittleFS, preferring the pre-gzipped variant. Content is
// streamed from flash in chunks — a 76 KB bundle never lands in RAM.
bool serveFromFS(String path) {
  if (!fsOk) return false;
  if (path == "/") path = "/index.html";
  if (path.endsWith("/")) path += "index.html";
  if (path.indexOf("..") >= 0) return false;   // no traversal

  const char* cache = path.startsWith("/assets/") ? "public, max-age=86400" : "no-cache";

  String gz = path + ".gz";
  if (LittleFS.exists(gz)) {
    File f = LittleFS.open(gz, "r");
    if (f) {
      server.sendHeader("Content-Encoding", "gzip");
      server.sendHeader("Cache-Control", cache);
      server.streamFile(f, mimeFor(path));
      f.close();
      return true;
    }
  }
  if (LittleFS.exists(path)) {
    File f = LittleFS.open(path, "r");
    if (f) {
      server.sendHeader("Cache-Control", cache);
      server.streamFile(f, mimeFor(path));
      f.close();
      return true;
    }
  }
  return false;
}

void handleNotFound() {
  if (serveFromFS(server.uri())) return;
  server.send(404, "text/plain", "not found");
}

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

void handleRoot() {
  // the real dashboard from flash when the bundle is installed
  if (serveFromFS("/")) return;

  String h = "<!doctype html><meta name=viewport content='width=device-width'>";
  h += "<title>TankGuard tank</title><body style='font-family:sans-serif;background:#071018;color:#cfe'>";
  h += "<h2>TankGuard</h2><pre id=v>loading...</pre>";
  h += "<p>No webapp bundle in flash (see webapp/tools/build-device-bundle.mjs). <a href='/data'>JSON</a></p>";
  h += "<script>async function u(){let j=await(await fetch('/data')).json();";
  h += "v.textContent='Score '+j.score+'\\nLevel '+j.level+'%\\npH '+j.ph+'\\nTurbidity '+j.turb+' NTU\\nTDS '+j.tds+' ppm\\nTemp '+j.temp+' C';}";
  h += "u();setInterval(u,3000);</script></body></html>";
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

  fsOk = LittleFS.begin();
  if (!fsOk) TG_PRINTLN("WARN: LittleFS mount failed — serving inline page only");

  if (MDNS.begin("tankguard")) {
    MDNS.addService("http", "tcp", 80);
    TG_PRINTLN("mDNS: http://tankguard.local");
  }

  server.on("/", handleRoot);
  server.on("/data", handleData);
  server.onNotFound(handleNotFound);
  server.begin();
#endif

  TG_PRINTLN("TankGuard tank-side ready");
}

// ------------------------------ loop --------------------------------------
void loop() {
#if !USE_NRF24
  server.handleClient();
#endif

  if (millis() - lastSampleMs >= SAMPLE_MS) {
    lastSampleMs = millis();
    sample();
#if USE_NRF24
    radioSend();
#endif
  }

  delay(2);
}
