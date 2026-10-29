#pragma once

// ---------------------------------------------------------------------------
// TankGuard H1 (home-side) configuration
// Edit WIFI_SSID / WIFI_PASS and the tank-side URLs, then re-flash.
// Leave WIFI_SSID empty to run the on-screen DEMO (no network needed).
// ---------------------------------------------------------------------------

#define WIFI_SSID ""
#define WIFI_PASS ""

// Tank-side module endpoints (HTTP polling)
#define TANK_DATA_URL  "http://192.168.1.50/data"
#define TANK_FLUSH_URL "http://192.168.1.50/flush"

// NodeMCU pin labels -> GPIO numbers
#define TFT_CS    16   // D0
#define TFT_DC     5   // D1
#define TFT_RST    4   // D2
#define RELAY_PIN 12   // D6
#define BTN_FLUSH  0   // D3  (boot strap: do not hold at power-up)
#define BTN_MOTOR  2   // D4  (boot strap: do not hold at power-up)

// Relay module: 1 = active-LOW (most common), 0 = active-HIGH
#define RELAY_ACTIVE_LOW 1

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
