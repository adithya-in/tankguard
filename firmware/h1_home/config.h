#pragma once

// ---------------------------------------------------------------------------
// TankGuard H1 (home-side) configuration
// Edit WIFI_SSID / WIFI_PASS and the tank-side URLs, then re-flash.
// Leave WIFI_SSID empty to run the on-screen DEMO (no network needed).
// ---------------------------------------------------------------------------

#define WIFI_SSID ""
#define WIFI_PASS ""

// Radio link: 1 = nRF24L01+ direct link (see NRF24_LONG_RANGE.md, pin remap).
// 0 = Wi-Fi/HTTP polling (default).
#ifndef USE_NRF24
#define USE_NRF24 0
#endif

// Tank-side module endpoint (HTTP polling)
#define TANK_DATA_URL  "http://192.168.1.50/data"

// NodeMCU pin labels -> GPIO numbers
#define TFT_CS    16   // D0
#define TFT_DC     5   // D1
#define TFT_RST    4   // D2

#if USE_NRF24
// nRF24L01+ shares SPI with the TFT (SCK=D5, MOSI=D7, MISO=D6)
#define NRF_CE     2   // D4 (10k pull-up to 3V3)
#define NRF_CSN    0   // D3 (10k pull-up to 3V3)
#define RELAY_PIN 15   // D8, must be active-HIGH (LOW at boot = pump OFF)
#define RELAY_ACTIVE_LOW 0
#define BTN_ADC   A0   // MOTOR button via 1k to GND
#else
#define RELAY_PIN 12   // D6
#define BTN_MOTOR  2   // D4  (boot strap: do not hold at power-up)
// Relay module: 1 = active-LOW (most common), 0 = active-HIGH
#define RELAY_ACTIVE_LOW 1
#endif

// Pump automation setpoints (% level)
#define LEVEL_LOW   20.0f
#define LEVEL_HIGH  95.0f

// Manual pump override auto-releases after this long
#define MANUAL_TIMEOUT_MS (10UL * 60UL * 1000UL)

// Sensor poll interval
#define FETCH_MS 3000

// Optional hardware (not in the current build)
#define HAS_BUZZER 0
#if HAS_BUZZER
#define BUZZER_PIN 15  // D8
#endif
