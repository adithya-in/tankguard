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
#include <math.h>
#include "config.h"

#if USE_NRF24
#include "nrf_link.h"
RF24 radio(NRF_CE, NRF_CSN);
#endif

struct Button;

#ifndef TFT_INIT
#define TFT_INIT INITR_BLACKTAB   // try INITR_REDTAB / INITR_GREENTAB if colours look wrong
#endif

// 1 = freeze the ambient wave/impeller, keep state changes
#ifndef REDUCED_MOTION
#define REDUCED_MOTION 0
#endif

// --- palette (RGB565) ------------------------------------------------------
#define C_BG        0x0000
#define C_FRAME     0x528A
#define C_DIM       0x8410
#define C_TRACK     0x2104
#define C_WATER     0x04B6
#define C_WATER_HI  0x2E9F
#define C_FOAM      0xCE79
#define C_ACCENT    0x07FF
#define C_GREEN     0x07E0
#define C_YELLOW    0xFFE0
#define C_RED       0xF800
#define C_ORANGE    0xFD20
#define C_MAGENTA   0xF81F

// --- layout ---------------------------------------------------------------
#define TANK_X   6
#define TANK_Y   18
#define TANK_W   52
#define TANK_H   98
#define TANK_IX  (TANK_X + 3)
#define TANK_IY  (TANK_Y + 4)
#define TANK_IW  (TANK_W - 6)
#define TANK_IH  (TANK_H - 8)
#define TANK_BOT (TANK_IY + TANK_IH)

#define DIAL_CX  112
#define DIAL_CY  42
#define DIAL_RO  24
#define DIAL_RI  20
#define SEGS     18

#define BAR_Y    118

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
unsigned long flushMsgMs = 0;
String flushMsg = "READY";

#if USE_NRF24
unsigned long lastRadioMs = 0;
bool newPacket = false;
#endif

// animation state
float levelShown = 0;
float scoreShown = 0;
float wavePhase = 0;
float impellerAngle = 0;
float flushPhase = 0;
int lastSeg = -1;
int lastScoreInt = -1;
bool lastLinkDraw = false;
bool blinkOn = false;
unsigned long lastBlinkMs = 0;
unsigned long lastAnimMs = 0;
unsigned long lastMetricMs = 0;

// incremental redraw state (prevents flicker)
int16_t prevTop[TANK_IW];
int lastLvlInt = -1;
int lastPumpDrawn = -1;
int lastModeDrawn = -1;
String lastFlushDrawn = "";
bool flushShown = false;
bool chevronsOn = false;

// ------------------------------- buttons ----------------------------------
#if USE_NRF24
// Resistor ladder on A0: idle ~3.3 V, FLUSH ~1.05 V, MOTOR ~0.30 V.
bool rawFlushPressed() {
  int v = analogRead(BTN_ADC);
  return v > 240 && v < 430;
}
bool rawMotorPressed() {
  int v = analogRead(BTN_ADC);
  return v < 160;
}
#else
bool rawFlushPressed() { return digitalRead(BTN_FLUSH) == LOW; }
bool rawMotorPressed() { return digitalRead(BTN_MOTOR) == LOW; }
#endif

struct Button {
  bool (*readFn)();
  bool stable = false;
  bool lastRead = false;
  unsigned long changeMs = 0;
  unsigned long pressMs = 0;
  bool longFired = false;
  bool shortEvt = false;
  bool longEvt = false;
};

Button btnFlush = { rawFlushPressed };
Button btnMotor = { rawMotorPressed };

void pollButton(Button &b) {
  bool pressed = b.readFn();
  unsigned long now = millis();
  if (pressed != b.lastRead) { b.lastRead = pressed; b.changeMs = now; }

  if (pressed != b.stable && (now - b.changeMs) > 30) {
    b.stable = pressed;
    if (b.stable) {
      b.pressMs = now;
      b.longFired = false;
    } else {
      if (!b.longFired && (now - b.pressMs) >= 50) b.shortEvt = true;
    }
  }

  if (b.stable && !b.longFired && (now - b.pressMs) >= 2000) {
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
#if USE_NRF24
  demo = false;
  return;
#else
  demo = (strlen(WIFI_SSID) == 0);
  if (demo) return;

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 15000) {
    delay(200);
    yield();
  }
#endif
}

bool fetchTank() {
  if (demo) {
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
#if USE_NRF24
  CmdPacket c;
  c.magic = TG_MAGIC;
  c.cmd = force ? 2 : 1;
  radio.stopListening();
  bool ok = radio.write(&c, sizeof(c));
  radio.startListening();
  flushMsg = ok ? (force ? "FORCED" : "SENT") : "NO LINK";
  flushMsgMs = millis();
#else
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
#endif
}

// ------------------------------- radio ------------------------------------
#if USE_NRF24
void radioBegin() {
  radio.begin();
  nrfConfig(radio);
  radio.setAddressWidth(5);
  radio.openWritingPipe(TG_ADDR);
  radio.openReadingPipe(1, TG_ADDR);
  radio.startListening();
}

void radioPoll() {
  if (!radio.available()) return;
  TankPacket p;
  radio.read(&p, sizeof(p));
  if (p.magic != TG_MAGIC) return;

  data.score = p.score;
  data.level = p.level;
  data.ph    = p.ph;
  data.turb  = p.turb;
  data.tds   = p.tds;
  data.temp  = p.temp;

  linkOk = true;
  lastRadioMs = millis();
  lastFetchMs = lastRadioMs;

  if (p.flush == 1)      flushMsg = "FLUSHING";
  else if (p.flush == 2) flushMsg = "DONE";

  newPacket = true;
}
#endif

// ------------------------------- drawing ----------------------------------
uint16_t scoreColor(float s) {
  if (s >= 70) return C_GREEN;
  if (s >= 40) return C_YELLOW;
  return C_RED;
}

void drawStatic() {
  tft.fillScreen(C_BG);
  tft.setTextSize(1);

  tft.setTextColor(C_ACCENT, C_BG);
  tft.setCursor(4, 2);
  tft.print("TANKGUARD");
  tft.drawFastHLine(0, 12, 160, C_FRAME);

  // tank outline + lid
  tft.drawRoundRect(TANK_X, TANK_Y, TANK_W, TANK_H, 5, C_FRAME);
  tft.drawFastHLine(TANK_X + 16, TANK_Y - 3, 20, C_FRAME);
  tft.drawFastVLine(TANK_X + 16, TANK_Y - 3, 4, C_FRAME);
  tft.drawFastVLine(TANK_X + 35, TANK_Y - 3, 4, C_FRAME);

  // metric labels
  tft.setTextColor(C_DIM, C_BG);
  tft.setCursor(66, 71);  tft.print("pH");
  tft.setCursor(112, 71); tft.print("TURB");
  tft.setCursor(66, 95);  tft.print("TDS");
  tft.setCursor(112, 95); tft.print("TEMP");

  tft.drawFastHLine(0, 117, 160, C_FRAME);
}

void drawImpeller(int cx, int cy, float ang, uint16_t col) {
  for (int i = 0; i < 3; i++) {
    float a = ang + i * 2.0944f;
    int x = cx + (int)(cosf(a) * 3.4f);
    int y = cy + (int)(sinf(a) * 3.4f);
    tft.drawLine(cx, cy, x, y, col);
  }
  tft.drawPixel(cx, cy, col);
}

void drawChevrons() {
  int x = TANK_IX + TANK_IW / 2;
  for (int i = 0; i < 3; i++) {
    int y = 76 + (((int)flushPhase + i * 10) % 30);
    uint16_t c = (i == 0) ? C_ACCENT : C_WATER_HI;
    tft.drawLine(x - 6, y, x, y + 5, c);
    tft.drawLine(x, y + 5, x + 6, y, c);
  }
}

void drawTank() {
  float lv = levelShown;
  if (lv < 0) lv = 0;
  if (lv > 100) lv = 100;
  int wy = TANK_BOT - (int)((lv / 100.0f) * TANK_IH);
  if (wy < TANK_IY) wy = TANK_IY;

  // Repaint only the pixels that changed per column: no full clear, no flicker.
  for (int x = 0; x < TANK_IW; x++) {
    int yy = wy + (int)(1.6f * sinf(x * 0.38f + wavePhase));
    if (yy < TANK_IY) yy = TANK_IY;
    if (yy > TANK_BOT) yy = TANK_BOT;

    int prev = prevTop[x];
    if (yy < prev) {
      tft.drawFastVLine(TANK_IX + x, yy, prev - yy, C_WATER);
    } else if (yy > prev) {
      tft.drawFastVLine(TANK_IX + x, prev, yy - prev, C_BG);
    }

    if (yy != prev) {
      tft.drawPixel(TANK_IX + x, yy, C_WATER_HI);
      if (prev < TANK_BOT)
        tft.drawPixel(TANK_IX + x, prev, (yy > prev) ? C_BG : C_WATER);
    } else {
      tft.drawPixel(TANK_IX + x, yy, C_WATER_HI);
    }
    prevTop[x] = yy;
  }

  // capacity ticks on the right inner edge
  for (int p = 25; p <= 75; p += 25) {
    int ty = TANK_BOT - (int)((p / 100.0f) * TANK_IH);
    tft.drawFastHLine(TANK_IX + TANK_IW - 5, ty, 5, C_FRAME);
  }

  bool flushActive = (millis() - flushMsgMs < 4000);
  if (flushActive) {
    drawChevrons();
    chevronsOn = true;
  } else if (chevronsOn) {
    // flush just ended: one clean repaint removes the chevrons
    chevronsOn = false;
    tft.fillRect(TANK_IX, TANK_IY, TANK_IW, TANK_IH, C_BG);
    for (int i = 0; i < TANK_IW; i++) prevTop[i] = TANK_BOT;
  }

  int li = (int)(lv + 0.5f);
  if (li != lastLvlInt) {
    lastLvlInt = li;
    char b[16];
    snprintf(b, sizeof(b), "LVL %d%%", li);
    tft.fillRect(62, 1, 52, 10, C_BG);
    tft.setTextSize(1);
    tft.setTextColor(C_FOAM, C_BG);
    tft.setCursor(62, 2);
    tft.print(b);
  }
}

void drawDial() {
  int filled = (int)(scoreShown / (100.0f / SEGS) + 0.5f);
  if (filled > SEGS) filled = SEGS;
  uint16_t sc = scoreColor(scoreShown);
  int scoreInt = (int)(scoreShown + 0.5f);

  if (filled == lastSeg && scoreInt == lastScoreInt) return;

  tft.fillRect(DIAL_CX - (DIAL_RO + 2), DIAL_CY - (DIAL_RO + 2),
               (DIAL_RO + 2) * 2, (DIAL_RO + 2) * 2, C_BG);

  for (int i = 0; i < SEGS; i++) {
    float a = 2.35619f + i * (4.71239f / (SEGS - 1));
    int x1 = DIAL_CX + (int)(cosf(a) * DIAL_RI);
    int y1 = DIAL_CY + (int)(sinf(a) * DIAL_RI);
    int x2 = DIAL_CX + (int)(cosf(a) * DIAL_RO);
    int y2 = DIAL_CY + (int)(sinf(a) * DIAL_RO);
    uint16_t c = (i < filled) ? sc : C_TRACK;
    tft.drawLine(x1, y1, x2, y2, c);
    tft.drawLine(x1 + 1, y1, x2 + 1, y2, c);
  }

  char b[4];
  snprintf(b, sizeof(b), "%d", scoreInt);
  tft.setTextSize(2);
  tft.setTextColor(sc, C_BG);
  int w = 12 * strlen(b);
  tft.setCursor(DIAL_CX - w / 2, DIAL_CY - 8);
  tft.print(b);

  lastSeg = filled;
  lastScoreInt = scoreInt;
}

void drawMetrics() {
  char b[10];
  tft.setTextSize(1);

  tft.fillRect(66, 80, 40, 9, C_BG);
  snprintf(b, sizeof(b), "%.1f", data.ph);
  tft.setTextColor(ST77XX_WHITE, C_BG);
  tft.setCursor(66, 80); tft.print(b);

  tft.fillRect(112, 80, 40, 9, C_BG);
  snprintf(b, sizeof(b), "%.0f", data.turb);
  tft.setTextColor(ST77XX_WHITE, C_BG);
  tft.setCursor(112, 80); tft.print(b);

  tft.fillRect(66, 104, 40, 9, C_BG);
  snprintf(b, sizeof(b), "%.0f", data.tds);
  tft.setTextColor(ST77XX_WHITE, C_BG);
  tft.setCursor(66, 104); tft.print(b);

  tft.fillRect(112, 104, 40, 9, C_BG);
  snprintf(b, sizeof(b), "%.0fC", data.temp);
  tft.setTextColor(ST77XX_WHITE, C_BG);
  tft.setCursor(112, 104); tft.print(b);
}

void drawLink() {
  tft.fillRect(140, 0, 20, 11, C_BG);
  bool on;
  uint16_t c;
  if (demo) { on = true; c = C_MAGENTA; }
  else if (linkOk) { on = true; c = C_GREEN; }
  else { on = blinkOn; c = C_RED; }
  if (on) tft.fillCircle(150, 5, 3, c);
  lastLinkDraw = linkOk;
}

void drawBottom() {
  tft.setTextSize(1);

  // impeller is the only thing that changes every frame
  tft.fillRect(1, 118, 15, 10, C_BG);
  drawImpeller(8, 123, impellerAngle, pumpOn ? C_GREEN : C_DIM);

  if ((int)pumpOn != lastPumpDrawn) {
    lastPumpDrawn = (int)pumpOn;
    tft.fillRect(18, BAR_Y + 1, 46, 9, C_BG);
    tft.setTextColor(pumpOn ? C_GREEN : C_DIM, C_BG);
    tft.setCursor(18, BAR_Y + 1);
    tft.print(pumpOn ? "PUMP ON" : "PUMP OFF");
  }

  if ((int)mode != lastModeDrawn) {
    lastModeDrawn = (int)mode;
    tft.fillRect(126, BAR_Y + 1, 32, 9, C_BG);
    tft.setTextColor(mode == MODE_AUTO ? C_ACCENT : C_ORANGE, C_BG);
    tft.setCursor(126, BAR_Y + 1);
    tft.print(mode == MODE_AUTO ? "AUTO" : "MAN");
  }

  bool flushActive = (millis() - flushMsgMs < 4000);
  if (flushActive && (!flushShown || flushMsg != lastFlushDrawn)) {
    flushShown = true;
    lastFlushDrawn = flushMsg;
    tft.fillRect(64, BAR_Y + 1, 62, 9, C_BG);
    tft.setTextColor(C_ACCENT, C_BG);
    tft.setCursor(66, BAR_Y + 1);
    tft.print(flushMsg);
  } else if (!flushActive && flushShown) {
    flushShown = false;
    tft.fillRect(64, BAR_Y + 1, 62, 9, C_BG);
  }
}

void animate() {
#if REDUCED_MOTION
  levelShown = data.level;
  scoreShown = data.score;
#else
  levelShown += (data.level - levelShown) * 0.18f;
  scoreShown += (data.score - scoreShown) * 0.18f;
  wavePhase += 0.28f;
  if (pumpOn) impellerAngle += 0.55f;
  if (millis() - flushMsgMs < 4000) flushPhase += 0.9f;
#endif
  drawTank();
  drawDial();
  drawBottom();
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
  flushPhase = 0;
  sendFlush(force);
  flushMsgMs = millis();
  flushPhase = 0;
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
  mode = (mode == MODE_AUTO) ? MODE_MANUAL : MODE_AUTO;
}

// ------------------------------- setup ------------------------------------
void setup() {
  Serial.begin(115200);
  delay(100);

#if RELAY_ACTIVE_LOW
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, HIGH);   // active-LOW module: HIGH = pump OFF
#else
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW);    // active-HIGH module: LOW = pump OFF
#endif

#if !USE_NRF24
  pinMode(BTN_FLUSH, INPUT_PULLUP);
  pinMode(BTN_MOTOR, INPUT_PULLUP);
#endif

#if HAS_BUZZER
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);
#endif

  tft.initR(TFT_INIT);
  tft.setRotation(1);
  for (int i = 0; i < TANK_IW; i++) prevTop[i] = TANK_BOT;
  drawStatic();

#if USE_NRF24
  radioBegin();
#else
  wifiBegin();
  fetchTank();
#endif
  lastFetchMs = millis();
  drawMetrics();
  animate();

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

#if USE_NRF24
  radioPoll();
  if (newPacket) {
    newPacket = false;
    applyAutoLogic();
    drawMetrics();
  }
  if (linkOk && now - lastRadioMs > 15000) linkOk = false;
#else
  if (now - lastFetchMs >= FETCH_MS) {
    lastFetchMs = now;
    fetchTank();
    applyAutoLogic();
    drawMetrics();
  }
#endif

  if (mode == MODE_MANUAL && pumpOn && now - lastManualOnMs >= MANUAL_TIMEOUT_MS) {
    mode = MODE_AUTO;
    applyAutoLogic();
    if (pumpOn && data.level >= LEVEL_HIGH) setPump(false);
  }

  if (!linkOk && pumpOn && now - lastFetchMs > 60000) {
    pumpOffSafe();
  }

  if (now - lastAnimMs >= 70) {
    lastAnimMs = now;
    animate();
  }

  if (now - lastBlinkMs >= 500) {
    lastBlinkMs = now;
    blinkOn = !blinkOn;
    drawLink();
  }

  delay(5);
}
