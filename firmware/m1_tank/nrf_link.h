#pragma once

// Shared nRF24L01+ link definitions for TankGuard (tank <-> home).
// Keep this file identical in m1_tank/ and h1_home/.

#include <RF24.h>

#define TG_MAGIC   0x5447      // 'TG'
#define NRF_CHANNEL 76         // 2.476 GHz, above Wi-Fi 1-13

static const uint8_t TG_ADDR[5] = { 'T', 'A', 'N', 'K', '1' };

// Fixed payload so both ends always agree on layout.
struct __attribute__((packed)) TankPacket {
  uint16_t magic;
  float score;
  float level;
  float ph;
  float turb;
  float tds;
  float temp;
};

// Common radio settings. Power the module from 3.3 V only (100 uF + 10 uF).
inline void nrfConfig(RF24 &r) {
  r.setChannel(NRF_CHANNEL);
  r.setDataRate(RF24_250KBPS);
  r.setPALevel(RF24_PA_MAX);
  r.setAutoAck(true);
  r.setCRCLength(RF24_CRC_16);
}
