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

// Tank geometry: distance from the ultrasonic sensor face to the tank bottom.
#define TANK_DEPTH_CM 150.0f

#if USE_NRF24
// nRF24L01+ remap (hardware SPI: SCK=D5, MOSI=D7, MISO=D6)
#define NRF_CE    16     // D0
#define NRF_CSN    0     // D3 (10k pull-up to 3V3)
#define DS18B20_PIN 2    // D4 (4.7k pull-up) - moved from D6
#define PIN_TRIG   1     // TX - serial debug disabled
#define PIN_ECHO   3     // RX - via 1k/1k divider
#else
#define DS18B20_PIN 12   // D6
#define PIN_TRIG  13     // D7
#define PIN_ECHO  14     // D5
#endif

// Sensor conditioning
#define TURB_DIV      2.0f      // SEN0189 Ao divided by 2 (10k/10k)
#define PH_SLOPE     -5.70f     // calibrate with pH 4.0 and 7.0 buffers
#define PH_OFFSET    21.34f

// Sampling interval
#define SAMPLE_MS 5000

// Optional hardware
#define HAS_BUZZER 0
