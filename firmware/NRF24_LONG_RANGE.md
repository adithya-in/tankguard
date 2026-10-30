# nRF24L01+ Long-Range Link

Adds a **2.4 GHz nRF24L01+ PA/LNA** radio link between the tank and the home unit,
as an alternative (or backup) to Wi-Fi. At **250 kbps** the PA/LNA modules reach
roughly **1 km line-of-sight** and hold up better through walls than high-rate Wi-Fi.

> **Status:** implemented in both firmwares behind `USE_NRF24` (default `0` = Wi-Fi).
> Enabling it requires the **Option A pin remap** below (hardware rewire).
>
> Enable with either:
> - set `#define USE_NRF24 1` in `m1_tank/config.h` **and** `h1_home/config.h`, or
> - build with `--build-property "compiler.cpp.extra_flags=-DUSE_NRF24=1"`.
>
> The two ends must use the same setting. With `USE_NRF24=1` the tank disables
> serial debug (TX/RX are the ultrasonic pins) and the home unit stops using Wi-Fi.

---

## 1. Power (the usual failure point)

| Rule | Why |
|---|---|
| **3.3 V ONLY** | 5 V destroys the nRF24L01 instantly |
| **100 µF electrolytic + 10 µF ceramic** across VCC/GND, at the module | current spikes during TX (~115 mA) |
| **Separate AMS1117-3.3** (or the module's adapter board) | the NodeMCU 3V3 rail is already loaded and sags |
| Wires **< 10 cm**, twisted VCC/GND | reduces drop and noise |
| Antenna clear of metal/water, upright | water absorbs 2.4 GHz |

Module pins: `GND VCC CE CSN SCK MOSI MISO IRQ` (IRQ not used).

Recommended radio settings:
- Channel **76** (2.476 GHz, above Wi-Fi 1–13)
- Data rate **250 kbps** (`RF24_250KBPS`)
- PA **MAX** (`RF24_PA_MAX`)
- Auto-ack on, CRC 2 bytes, pipe address `"TANK1"`

---

## 2. Why a remap is needed

The nRF24 uses **hardware SPI** on the ESP8266: `SCK=D5(14)`, `MOSI=D7(13)`,
`MISO=D6(12)`. Both boards currently use those pins for sensors/display, so enabling
nRF means moving a few signals. Two options:

- **Option A — direct remap** (cheapest, needs rewiring).
- **Option B — UART bridge** (no sensor remap, two extra ESP-01 + nRF boards).

---

## 3. Option A — direct remap

### 3.1 Tank side

| Signal | NodeMCU | GPIO | Change |
|---|---|---|---|
| nRF SCK | D5 | 14 | new |
| nRF MOSI | D7 | 13 | new |
| nRF MISO | D6 | 12 | new |
| nRF CE | D0 | 16 | new |
| nRF CSN | D3 | 0 | new, **10 kΩ pull-up to 3V3** |
| ADS1115 SDA | D2 | 4 | unchanged |
| ADS1115 SCL | D1 | 5 | unchanged |
| DS18B20 DQ | **D4** | 2 | **moved from D6**, 4.7 kΩ pull-up |
| JSN-SR04T TRIG | **TX** | 1 | **moved from D7** |
| JSN-SR04T ECHO | **RX** | 3 | **moved from D5**, 1k/1k divider |

Consequences:
- **Serial debug is lost** (TX/RX now drive the ultrasonic).
- GPIO0 (CSN) must be HIGH at boot → the 10 kΩ pull-up satisfies it.
- GPIO2 (DS18B20) must be HIGH at boot → the 4.7 kΩ pull-up satisfies it.

### 3.2 Home side

| Signal | NodeMCU | GPIO | Change |
|---|---|---|---|
| nRF SCK | D5 | 14 | shared with TFT |
| nRF MOSI | D7 | 13 | shared with TFT |
| nRF MISO | D6 | 12 | **was relay** |
| nRF CE | D4 | 2 | new, **10 kΩ pull-up to 3V3** |
| nRF CSN | D3 | 0 | new, **10 kΩ pull-up to 3V3** |
| TFT CS / DC / RST | D0 / D1 / D2 | 16 / 5 / 4 | unchanged |
| Relay IN | **D8** | 15 | **moved from D6**; use an **active-HIGH** relay module |
| MOTOR button | **A0** | ADC | **moved from D4** (single button on A0) |

Consequences:
- The relay moves to GPIO15, so it **must be active-HIGH with a pulldown**
  (GPIO15 is low at boot → pump OFF). An active-LOW module needs an inverter.
- The MOTOR button moves to A0; firmware reads the pressed voltage band.

### 3.3 Button wiring (home, A0)

```
3V3 ──[10k]──┬── A0
             │
      MOTOR ──┴─[1.0k]── GND     (pressed: ~0.30 V)
```
Idle ≈ 3.3 V, pressed <0.55 V. Firmware treats `<0.52 V` as pressed
(adjust the threshold after measuring).

---

## 4. Option B — UART bridge (no sensor remap)

Keep every sensor where it is. Use two tiny bridge boards:

- **Tank bridge:** ESP-01 + nRF24, UART RX ← tank `TX` (JSON lines).
- **Home bridge:** ESP-01 + nRF24, UART TX → home `RX` (JSON lines).

The tank ESP keeps its current pinout and prints a JSON line per sample; the bridge
transmits it. The home bridge receives and feeds the H1 over UART. Cost ≈ ₹400 extra,
no rewiring of the sensor or display boards, and serial debug can be kept on the tank
(shared TX).

---

## 5. Packet format

```c
struct __attribute__((packed)) TankPacket {
  uint16_t magic;   // 0x5447
  float score, level, ph, turb, tds, temp;
};
```

- Tank writes `TankPacket` every sample (5 s).
- One-way link: the home unit only receives; there is no command channel.
- Use a fixed payload, auto-ack, and CRC 2 bytes.

---

## 6. Firmware behaviour with `USE_NRF24=1`

| Tank side (`m1_tank`) | Home side (`h1_home`) |
|---|---|
| Sends a `TankPacket` every `SAMPLE_MS` (5 s) | Listens for packets, updates the TFT on each one |
| Serial debug off, Wi-Fi/HTTP server off | Wi-Fi/HTTP off; DEMO off |
| — | Link loss: no packets for 15 s → `linkOk=false`; pump forced OFF after 60 s |

The link is one-way (tank → home). The home unit still controls its own pump relay
locally; nothing is sent back to the tank.

---

## 7. Recommendation

| If | Choose |
|---|---|
| You can rewire both boards | **Option A** — cheapest, one radio per board |
| You want to keep the sensor wiring untouched | **Option B** — UART bridges |
| Range through thick walls is the main problem | Use **LoRa SX1278 (433 MHz)** instead; it is SPI too but reaches much farther |

The default build is Wi-Fi; enable nRF by setting `USE_NRF24=1` in both configs.
