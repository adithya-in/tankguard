# TankGuard — Home-Side Module (Hardware)

This folder contains the **hardware build instructions** for TankGuard, built around
**ESP8266** boards. The system has a **tank-side** unit and a **home-side** unit:

| Side | Module | Document | What it does |
|---|---|---|---|
| Tank | **M1 — Monitor** | [`HARDWARE_M1_Monitor.md`](HARDWARE_M1_Monitor.md) | Reads turbidity, TDS, pH, temperature and water level; computes TankScore; sends data over Wi-Fi |
| Tank | **M2 — Sludge Flush** | [`HARDWARE_M2_Flush.md`](HARDWARE_M2_Flush.md) | Drives the 1″ normally-closed solenoid valve at the tank floor |
| Home | **H1 — Home** | [`HARDWARE_H1_Home.md`](HARDWARE_H1_Home.md) | Next to the pump motor switch: ESP8266 + relay + 1.8″ ST7735 TFT + FLUSH/MOTOR override buttons; receives tank data and optionally automates the pump (mains-safe via relay + contactor) |
| — | **Pin map** | [`PINMAP.md`](PINMAP.md) | Master ESP8266 pin allocation for the tank-side modules (M1/M2) |
| Link | **nRF24L01+** | [`NRF24_LONG_RANGE.md`](NRF24_LONG_RANGE.md) | Optional 2.4 GHz long-range link, power rules, pin remap / UART-bridge options |

---

## Why ESP8266 (and the one catch)

The ESP8266 is cheap, Wi-Fi capable and has excellent deep-sleep current — ideal for a
solar-powered tank unit. **Its one limitation is a single ADC input (A0).**

TankGuard needs **three analog sensors** (turbidity, TDS, pH). Therefore **all analog
sensors are read through an ADS1115 16-bit I²C ADC** — the ESP8266's built-in ADC is
left unused. This is the single most important design rule for this build.

---

## System overview

```
                        ┌─────────────────────────────┐
                        │        12 V solar/battery    │
                        │      (CN3791 + 18650 pack)   │
                        └───────────────┬──────────────┘
                                        │ 12 V
                     ┌──────────────────┼──────────────────┐
                     │                  │                  │
                 ┌───▼────┐      ┌──────▼──────┐     ┌─────▼──────┐
                 │ LM2596 │      │   Valve      │     │  (fused)   │
                 │ 12→5V  │      │  solenoid    │     │            │
                 └───┬────┘      └──────────────┘     └────────────┘
                     │ 5 V
        ┌────────────┼───────────────┬───────────────┐
        │            │               │               │
   ┌────▼────┐  ┌────▼────┐     ┌────▼─────┐    ┌────▼─────┐
   │ JSN-    │  │ SEN0189 │     │ SEN0244  │    │ pH kit   │
   │ SR04T   │  │turbidity│     │  TDS     │    │ (5 V)    │
   │(5 V)    │  │  (5 V)  │     │  (5 V)   │    └────┬─────┘
   └────┬────┘  └────┬────┘     └────┬─────┘         │
        │ echo(div)  │ Ao(div)       │ Vo              │ Po
        │            └───────┬───────┴─────────────────┘
        │                    │
   ┌────▼────────────────────▼──────┐        ┌──────────────┐
   │        ADS1115 (16-bit)        │◄──I2C──┤   ESP8266    │
   │   A0=turbidity A1=TDS A2=pH    │        │  NodeMCU     │
   └────────────────────────────────┘        │              │
                                              │  D8 → MOSFET │
                    ┌──────────────┐          │  D0 → RST    │
                    │  DS18B20     │◄─1-Wire──┤              │
                    │ (temp, 3.3V) │          └──────┬───────┘
                    └──────────────┘                 │ gate
                                              ┌───────▼───────┐
                                              │ MOSFET driver │
                                              │  → 12 V valve │
                                              └───────────────┘
```

---

## Power tree

| Rail | Source | Feeds |
|---|---|---|
| 12 V | Solar panel → CN3791 MPPT → 18650 pack | Valve solenoid (fused), LM2596 input |
| 5 V | LM2596 buck (12 V → 5 V) | JSN-SR04T, SEN0189, SEN0244, pH kit, NodeMCU `VIN` |
| 3.3 V | NodeMCU onboard regulator + AMS1117 | ESP8266 core, ADS1115, DS18B20, dividers |

> **Common ground is mandatory** across the 12 V, 5 V and 3.3 V sections, otherwise the
> MOSFET gate and sensor readings will float.

---

## Safety rules (read before wiring)

1. **Fuse the 12 V line** to the valve (2 A blade fuse) — a shorted solenoid coil can otherwise overheat wiring.
2. **Never connect 5 V sensor outputs directly to ESP8266 GPIOs** — always divide down to ≤3.3 V (see each module doc).
3. **Keep the ESP8266 inside the sealed enclosure**; probes and the valve cable exit only through IP68 glands.
4. **Potable water:** use a food-grade valve (brass + EPDM) and food-safe probe materials if the tank supplies drinking water.
5. **Bench-test the valve on a low-pressure line first** before installing on a full tank.
6. **Do not power the valve from the 3.3 V or 5 V rail** — it needs the 12 V rail and its own switching path.

---

## H1 firmware

The home-side firmware lives in [`h1_home/`](h1_home/) (Arduino sketch, ESP8266).

1. Edit [`h1_home/config.h`](h1_home/config.h): set `WIFI_SSID`, `WIFI_PASS`, `TANK_DATA_URL`, `TANK_FLUSH_URL`.
   Leave `WIFI_SSID` empty to boot into an on-screen **DEMO** (no network).
2. Install libraries: `Adafruit GFX Library`, `Adafruit ST7735 and ST7789 Library`, `ArduinoJson`.
3. Compile + flash (NodeMCU):
   ```
   arduino-cli compile --fqbn esp8266:esp8266:nodemcuv2 firmware/h1_home
   arduino-cli upload -p /dev/cu.usbserial-XXXX --fqbn esp8266:esp8266:nodemcuv2 firmware/h1_home
   ```
4. Open serial at 115200 — expect `TankGuard H1 ready`.

Tank-side JSON expected by `fetchTank()`:
```json
{"score":82,"level":64,"ph":7.2,"turb":12,"tds":310,"temp":27.5}
```

## Tank-side firmware

The tank-side firmware lives in [`m1_tank/`](m1_tank/) (Arduino sketch, ESP8266).

1. Edit [`m1_tank/config.h`](m1_tank/config.h): Wi-Fi, `TANK_DEPTH_CM`, pH calibration, flush timing.
2. Libraries: `Adafruit ADS1X15`, `OneWire`, `DallasTemperature`, `ArduinoJson`.
3. Compile + flash:
   ```
   arduino-cli compile --fqbn esp8266:esp8266:nodemcuv2 firmware/m1_tank
   arduino-cli upload -p /dev/cu.usbserial-XXXX --fqbn esp8266:esp8266:nodemcuv2 firmware/m1_tank
   ```
4. With Wi-Fi set it serves:
   - `GET /data` → `{"score","level","ph","turb","tds","temp","flush","valve"}`
   - `GET /flush?force=0|1`
   - `GET /` → small status page
5. With `WIFI_SSID` empty it starts AP **TankGuard-Tank** (open) and serves the same pages.

Point the home module at `http://<tank-ip>/data` and `http://<tank-ip>/flush`.

## Bring-up order (recommended)

1. Power the NodeMCU alone from USB → confirm it boots and joins Wi-Fi.
2. Add the ADS1115 → scan I²C, confirm address `0x48`.
3. Add one sensor at a time, confirm plausible raw values.
4. Add the DS18B20 and JSN-SR04T → confirm readings.
5. Only then wire the M2 MOSFET + valve, and test with the tank empty/low.
6. Enable deep sleep last (D0→RST jumper) once everything else is stable.

See `PINMAP.md` for the exact pin allocation and the two module docs for step-by-step wiring.
