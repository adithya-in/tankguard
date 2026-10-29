/*
 * TankGuard H1 - home-side module firmware (ESP8266)
 *
 * Hardware (NodeMCU):
 *   ST7735 1.8" TFT (128x160, SPI):
 *     SCLK=D5(14)  MOSI=D7(13)  CS=D0(16)  DC=D1(5)  RST=D2(4)
 *   Relay IN  = D6 (GPIO12)
 *   FLUSH btn = D3 (GPIO0)   (10k pull-up, button to GND)
 *   MOTOR btn = D4 (GPIO2)   (10k pull-up, button to GND)
 *
 * Behaviour:
 *   FLUSH short press -> request flush from tank side
 *   FLUSH long press  -> force flush
 *   MOTOR short press -> toggle pump (enters MANUAL)
 *   MOTOR long press  -> toggle AUTO <-> MANUAL
 *
 * If WIFI_SSID is empty the display runs a DEMO simulation so the unit can be
 * bench-tested without a network.
 */

#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>
#include <ArduinoJson.h>
#include <SPI.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ST7735.h>
#include "config.h"

#ifndef TFT_INIT
#define TFT_INIT INITR_BLACKTAB   // try INITR_REDTAB / INITR_GREENTAB if colours look wrong
#endif

Adafruit_ST7735 tft(TFT_CS, TFT_DC, TFT_RST);

struct TankData {
  float score = 0;
  float level = 0;
  float ph    = 7.0;
  float turb  = 0;
  float tds   = 0;
  float temp  = 25.0;
};

enum Mode { MODE_AUTO, MODE_MANUAL };

TankData data;
Mode mode = MODE_AUTO;
bool pumpOn = false;
bool linkOk = false;
bool demo = false;
unsigned long lastFetchMs = 0;
unsigned long lastManualOnMs = 0;
unsigned long lastUiMs = 0;
String flushMsg = "READY";
unsigned long flushMsgMs = 0;

// ------------------------------- buttons ----------------------------------
struct Button {
  uint8_t pin;
  bool stable = true;        // true = released (INPUT_PULLUP)
  bool lastRead = true;
  unsigned long changeMs = 0;
  unsigned long pressMs = 0;
  bool longFired = false;
  bool shortEvt = false;
  bool longEvt = false;
};

Button btnFlush = { BTN_FLUSH };
Button btnMotor = { BTN_MOTOR };

void pollButton(Button &b) {
  bool raw = digitalRead(b.pin);           // HIGH = released
  unsigned long now = millis();
  if (raw != b.lastRead) { b.lastRead = raw; b.changeMs = now; }

  if (raw != b.stable && (now - b.changeMs) > 30) {
    b.stable = raw;
    if (!b.stable) {                       // pressed
      b.pressMs = now;
      b.longFired = false;
    } else {                               // released
      if (!b.longFired && (now - b.pressMs) >= 50) b.shortEvt = true;
    }
  }

  if (!b.stable && !b.longFired && (now - b.pressMs) >= 2000) {
    b.longEvt = true;
    b.longFired = true;
  }
}

// ------------------------------- relay ------------------------------------
void setPump(bool on) {
  pumpOn = on;
#if RELAY_ACTIVE_LOW
  digitalWrite(RELAY_PIN, on ? LOW : HIGH);
#else
  digitalWrite(RELAY_PIN, on ? HIGH : LOW);
#endif
}

void pumpOffSafe() {
  setPump(false);
  mode = MODE_AUTO;
}

// ------------------------------- network ----------------------------------
void wifiBegin() {
  demo = (strlen(WIFI_SSID) == 0);
  if (demo) return;

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 15000) {
    delay(200);
    yield();
  }
}

bool fetchTank() {
  if (demo) {
    // animated demo values
    float t = millis() / 1000.0f;
    data.level = 55.0f + 40.0f * sinf(t / 20.0f);
    data.ph    = 7.0f + 0.6f * sinf(t / 45.0f);
    data.turb  = 6.0f + 5.0f * (1.0f + sinf(t / 30.0f));
    data.tds   = 280.0f + 60.0f * sinf(t / 25.0f);
    data.temp  = 27.0f + 2.0f * sinf(t / 60.0f);
    data.score = 85.0f - 20.0f * sinf(t / 35.0f);
    linkOk = true;
    return true;
  }

  if (WiFi.status() != WL_CONNECTED) { linkOk = false; return false; }

  WiFiClient client;
  HTTPClient http;
  http.setTimeout(1500);
  if (!http.begin(client, TANK_DATA_URL)) { linkOk = false; return false; }

  int code = http.GET();
  if (code != 200) { http.end(); linkOk = false; return false; }

  String payload = http.getString();
  http.end();

  StaticJsonDocument<384> doc;
  if (deserializeJson(doc, payload)) { linkOk = false; return false; }

  data.score = doc["score"] | data.score;
  data.level = doc["level"] | data.level;
  data.ph    = doc["ph"]    | data.ph;
  data.turb  = doc["turb"]  | data.turb;
  data.tds   = doc["tds"]   | data.tds;
  data.temp  = doc["temp"]  | data.temp;
  linkOk = true;
  return true;
}

void sendFlush(bool force) {
  if (demo || WiFi.status() != WL_CONNECTED) {
    flushMsg = "NO LINK";
    flushMsgMs = millis();
    return;
  }
  String url = String(TANK_FLUSH_URL) + (force ? "?force=1" : "?force=0");
  WiFiClient client;
  HTTPClient http;
  http.setTimeout(1500);
  if (http.begin(client, url)) {
    int code = http.GET();
    http.end();
    flushMsg = (code == 200) ? (force ? "FORCED" : "SENT") : "ERR " + String(code);
  } else {
    flushMsg = "ERR";
  }
  flushMsgMs = millis();
}

// ------------------------------- display ----------------------------------
void drawStatic() {
  tft.fillScreen(ST77XX_BLACK);
  tft.setTextSize(1);
  tft.setTextColor(ST77XX_CYAN, ST77XX_BLACK);
  tft.setCursor(2, 2);
  tft.print("TANKGUARD H1");
  tft.drawFastHLine(0, 12, 160, ST77XX_CYAN);

  tft.setTextColor(ST77XX_WHITE, ST77XX_BLACK);
  tft.setCursor(2, 16); tft.print("SCORE");

  tft.setTextColor(ST77XX_WHITE, ST77XX_BLACK);
  tft.setCursor(2, 56);  tft.print("LVL");
  tft.setCursor(2, 68);  tft.print("pH");
  tft.setCursor(2, 80);  tft.print("TURB");
  tft.setCursor(2, 92);  tft.print("TDS");
  tft.setCursor(2, 104); tft.print("TEMP");
}

void drawText(int x, int y, int w, const char *s, uint16_t color) {
  tft.fillRect(x, y, w, 9, ST77XX_BLACK);
  tft.setTextSize(1);
  tft.setTextColor(color, ST77XX_BLACK);
  tft.setCursor(x, y);
  tft.print(s);
}

uint16_t scoreColor(float s) {
  if (s >= 70) return ST77XX_GREEN;
  if (s >= 40) return ST77XX_YELLOW;
  return ST77XX_RED;
}

void drawValues() {
  char buf[24];

  tft.fillRect(2, 26, 70, 26, ST77XX_BLACK);
  tft.setTextSize(3);
  tft.setTextColor(scoreColor(data.score), ST77XX_BLACK);
  snprintf(buf, sizeof(buf), "%3d", (int)data.score);
  tft.setCursor(2, 26);
  tft.print(buf);

  snprintf(buf, sizeof(buf), "%3d%%", (int)data.level);
  drawText(34, 56, 46, buf, ST77XX_WHITE);

  snprintf(buf, sizeof(buf), "%.1f", data.ph);
  drawText(34, 68, 46, buf, ST77XX_WHITE);

  snprintf(buf, sizeof(buf), "%4.0f", data.turb);
  drawText(34, 80, 46, buf, ST77XX_WHITE);

  snprintf(buf, sizeof(buf), "%4.0f", data.tds);
  drawText(34, 92, 46, buf, ST77XX_WHITE);

  snprintf(buf, sizeof(buf), "%.1fC", data.temp);
  drawText(34, 104, 46, buf, ST77XX_WHITE);

  snprintf(buf, sizeof(buf), "PUMP %s", pumpOn ? "ON " : "OFF");
  drawText(86, 56, 72, buf, pumpOn ? ST77XX_GREEN : ST77XX_WHITE);

  snprintf(buf, sizeof(buf), "MODE %s", mode == MODE_AUTO ? "AUTO" : "MAN ");
  drawText(86, 68, 72, buf, mode == MODE_AUTO ? ST77XX_CYAN : ST77XX_ORANGE);

  unsigned long age = (millis() - lastFetchMs) / 1000;
  if (millis() - flushMsgMs < 4000) {
    snprintf(buf, sizeof(buf), "FLUSH %s", flushMsg.c_str());
  } else {
    snprintf(buf, sizeof(buf), "UPD %lus", age);
  }
  drawText(86, 80, 72, buf, ST77XX_WHITE);

  if (demo) {
    snprintf(buf, sizeof(buf), "LINK DEMO");
    drawText(86, 92, 72, buf, ST77XX_MAGENTA);
  } else {
    snprintf(buf, sizeof(buf), "LINK %s", linkOk ? "OK" : "--");
    drawText(86, 92, 72, buf, linkOk ? ST77XX_GREEN : ST77XX_RED);
  }

  snprintf(buf, sizeof(buf), "WiFi %s", (demo || WiFi.status() == WL_CONNECTED) ? "UP" : "DOWN");
  drawText(86, 104, 72, buf, (demo || WiFi.status() == WL_CONNECTED) ? ST77XX_GREEN : ST77XX_RED);
}

// ------------------------------- logic ------------------------------------
void applyAutoLogic() {
  if (mode != MODE_AUTO || !linkOk) return;
  if (!pumpOn && data.level <= LEVEL_LOW) {
    setPump(true);
    lastManualOnMs = millis();
  } else if (pumpOn && data.level >= LEVEL_HIGH) {
    setPump(false);
  }
}

void handleFlush(bool force) {
  flushMsg = "SENDING";
  flushMsgMs = millis();
  drawValues();
  sendFlush(force);
  flushMsgMs = millis();
}

void handleMotorShort() {
  if (mode != MODE_MANUAL) {
    mode = MODE_MANUAL;
    setPump(true);
    lastManualOnMs = millis();
  } else {
    setPump(!pumpOn);
    if (pumpOn) lastManualOnMs = millis();
  }
}

void handleMotorLong() {
  if (mode == MODE_AUTO) {
    mode = MODE_MANUAL;
  } else {
    mode = MODE_AUTO;
  }
}

// ------------------------------- setup ------------------------------------
void setup() {
  Serial.begin(115200);
  delay(100);

  // relay OFF immediately (before anything else)
#if RELAY_ACTIVE_LOW
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, HIGH);
#else
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW);
#endif

  pinMode(BTN_FLUSH, INPUT_PULLUP);
  pinMode(BTN_MOTOR, INPUT_PULLUP);

#if HAS_BUZZER
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);
#endif

  tft.initR(TFT_INIT);
  tft.setRotation(1);       // landscape 160x128
  drawStatic();

  wifiBegin();
  fetchTank();
  lastFetchMs = millis();
  drawValues();

  Serial.println();
  Serial.println("TankGuard H1 ready");
}

// ------------------------------- loop -------------------------------------
void loop() {
  unsigned long now = millis();

  pollButton(btnFlush);
  pollButton(btnMotor);

  if (btnFlush.shortEvt) { btnFlush.shortEvt = false; handleFlush(false); }
  if (btnFlush.longEvt)  { btnFlush.longEvt  = false; handleFlush(true);  }
  if (btnMotor.shortEvt) { btnMotor.shortEvt = false; handleMotorShort(); }
  if (btnMotor.longEvt)  { btnMotor.longEvt  = false; handleMotorLong();  }

  if (now - lastFetchMs >= FETCH_MS) {
    lastFetchMs = now;
    fetchTank();
    applyAutoLogic();
  }

  // manual override timeout
  if (mode == MODE_MANUAL && pumpOn && now - lastManualOnMs >= MANUAL_TIMEOUT_MS) {
    mode = MODE_AUTO;
    applyAutoLogic();
    if (pumpOn && data.level >= LEVEL_HIGH) setPump(false);
  }

  // safety: lost link -> stop pump
  if (!linkOk && pumpOn && now - lastFetchMs > 60000) {
    pumpOffSafe();
  }

  if (now - lastUiMs >= 500) {
    lastUiMs = now;
    drawValues();
  }

  delay(5);
}
