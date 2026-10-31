#pragma once

// ---------------------------------------------------------------------------
// TankGuard M1 (tank-side) configuration
// Edit Wi-Fi + calibration values, then flash.
// Leave WIFI_SSID empty to start a setup AP "TankGuard-Tank".
// ---------------------------------------------------------------------------

#define WIFI_SSID ""
#define WIFI_PASS ""

// Radio link: 1 = nRF24L01+ direct link (see NRF24_LONG_RANGE.md, pin remap).
// 0 = Wi-Fi/HTTP (default). When 1, serial debug is disabled (TX/RX are used
// by the ultrasonic sensor).
#ifndef USE_NRF24
#define USE_NRF24 0
#endif

// Two-arm BTS7960 option (Wi-Fi/browser build only).
// 1 = D5/D6/D7/D8 PWM + sensors remapped to D0/D3/D4.
// 0 = original single-purpose sensor pin map.
#ifndef USE_ARMS
#define USE_ARMS 1
#endif

// Motors-only test build: 1 = skip ADS1115/DS18B20/ultrasonic setup and move
// Arm B LPWM from D8/GPIO15 to D1/GPIO5 so the ESP boots reliably with the
// BTS7960 connected. Set back to 0 when the sensors are wired.
#ifndef USE_MOTORS_ONLY
#define USE_MOTORS_ONLY 0
#endif

// Arms use D5/D6/D7 for SPI in the nRF build, so nRF forces arms off.
#if USE_NRF24
#undef USE_ARMS
#define USE_ARMS 0
#endif

// Tank geometry: distance from the ultrasonic sensor face to the tank bottom.
#define TANK_DEPTH_CM 150.0f

#if USE_NRF24
// nRF24L01+ remap (hardware SPI: SCK=D5, MOSI=D7, MISO=D6)
#define NRF_CE    16     // D0
#define NRF_CSN    0     // D3 (10k pull-up to 3V3)
#define DS18B20_PIN 2    // D4 (4.7k pull-up) - moved from D6
#define PIN_TRIG   1     // TX - serial debug disabled
#define PIN_ECHO   3     // RX - via 1k/1k divider
#elif USE_ARMS
// Two BTS7960 modules. D8/GPIO15 needs 10k pull-down; D3/D4 need pull-ups.
#define ARM_A_RPWM 14    // D5
#define ARM_A_LPWM 12    // D6
#define ARM_B_RPWM 13    // D7
#if USE_MOTORS_ONLY
#define ARM_B_LPWM  5    // D1/GPIO5 (no I2C in motors-only build)
#else
#define ARM_B_LPWM 15    // D8/GPIO15 (needs 10k pull-down)
#endif
// Sensor remap to free D5/D6/D7 for PWM.
#define DS18B20_PIN 2    // D4 (4.7k pull-up)
#define PIN_TRIG    0    // D3 (10k pull-up)
#define PIN_ECHO   16    // D0 via 1k/1k divider; remove D0-RST jumper
#else
#define DS18B20_PIN 12   // D6
#define PIN_TRIG  13     // D7
#define PIN_ECHO  14     // D5
#endif

#if USE_ARMS
// PWM is 0..1023 after analogWriteRange(1023).
#define ARM_PWM_DEFAULT  180   // start low; raise until the arm reliably moves
#define ARM_PWM_FLOOR     60   // web UI cannot go below this
#define ARM_PWM_MAX     1023
#define ARM_TRAVEL_MS   1000UL // open-loop: 1 s per 180-degree travel
#define ARM_AUTO_PAUSE_MS  500UL // stop at each end before reversing
#define ARM_DEAD_MS       40   // stop before reversing
#endif

// Sensor conditioning
#define TURB_DIV      2.0f      // SEN0189 Ao divided by 2 (10k/10k)
#define PH_SLOPE     -5.70f     // calibrate with pH 4.0 and 7.0 buffers
#define PH_OFFSET    21.34f

// Sampling interval
#define SAMPLE_MS 5000

// Optional hardware
#define HAS_BUZZER 0
