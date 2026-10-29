#pragma once

// ---------------------------------------------------------------------------
// TankGuard M1/M2 (tank-side) configuration
// Edit Wi-Fi + calibration values, then flash.
// Leave WIFI_SSID empty to start a setup AP "TankGuard-Tank".
// ---------------------------------------------------------------------------

#define WIFI_SSID ""
#define WIFI_PASS ""

// Tank geometry: distance from the ultrasonic sensor face to the tank bottom.
#define TANK_DEPTH_CM 150.0f

// DS18B20 data pin (D6 = GPIO12)
#define DS18B20_PIN 12

// Sensor conditioning
#define TURB_DIV      2.0f      // SEN0189 Ao divided by 2 (10k/10k)
#define PH_SLOPE     -5.70f     // calibrate with pH 4.0 and 7.0 buffers
#define PH_OFFSET    21.34f

// Flush valve
#define VALVE_PIN        15     // D8 (GPIO15) - must be LOW at boot
#define VALVE_ACTIVE_HIGH 1     // 1 = MOSFET/active-HIGH, 0 = active-LOW relay module
#define FLUSH_SECONDS    20     // valve open time per flush

// Automatic flushing
#define AUTO_FLUSH 1
#define AUTO_FLUSH_SCORE 45.0f
#define AUTO_FLUSH_MIN_INTERVAL_MS (6UL * 3600UL * 1000UL)
#define AUTO_FLUSH_MIN_LEVEL 10.0f

// Sampling interval
#define SAMPLE_MS 5000

// Optional hardware
#define HAS_BUZZER 0
