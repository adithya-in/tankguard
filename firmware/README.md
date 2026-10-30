# TankGuard — Firmware & Hardware

This folder contains the **hardware build instructions** for TankGuard, built around
**ESP8266** boards. The system has a **tank-side** unit and a **home-side** unit:

| Side | Module | Document | What it does |
|---|---|---|---|
| Tank | **M1 — Monitor** | [`HARDWARE_M1_Monitor.md`](HARDWARE_M1_Monitor.md) | Reads turbidity, TDS, pH, temperature and water level; computes TankScore; sends data over Wi-Fi |
| Home | **H1 — Home** | [`HARDWARE_H1_Home.md`](HARDWARE_H1_Home.md) | Next to the pump motor switch: ESP8266 + relay + 1.8″ ST7735 TFT + MOTOR override button; receives tank data and optionally automates the pump (mains-safe via relay + contactor) |
| — | **Pin map** | [`PINMAP.md`](PINMAP.md) | Master ESP8266 pin allocation for the tank-side module (M1) |
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
                        │        12 V solar/battery   │
                        │      (CN3791 + 18650 pack)  │
                        └───────────────┬─────────────┘
                                        │ 12 V
                                   ┌────▼────┐
                                   │ LM2596  │
                                   │ 12→5V   │
                                   └────┬────┘
                                        │ 5 V
        ┌────────────┬──────────────────┼───────────────┐
        │            │                  │               │
   ┌────▼────┐  ┌────▼────┐        ┌────▼─────┐    ┌────▼─────┐
   │ JSN-    │  │ SEN0189 │        │ SEN0244  │    │ pH kit   │
   │ SR04T   │  │turbidity│        │  TDS     │    │ (5 V)    │
   │(5 V)    │  │  (5 V)  │        │  (5 V)   │    └────┬─────┘
   └────┬────┘  └────┬────┘        └────┬─────┘         │
        │ echo(div)  │ Ao(div)            │ Vo            │ Po
        │            └────────┬───────────┴───────────────┘
        │                     │
   ┌────▼─────────────────────▼──────┐        ┌──────────────┐
   │        ADS1115 (16-bit)         │◄──I2C──┤   ESP8266    │
   │   A0=turbidity A1=TDS A2=pH     │        │  NodeMCU     │
   └─────────────────────────────────┘        │  D0 → RST    │
                     ┌──────────────┐         └──────┬───────┘
                     │  DS18B20     │◄─1-Wire────────┘
                     │ (temp, 3.3V) │
                     └──────────────┘
```

---

## Power tree

| Rail | Source | Feeds |
|---|---|---|
| 12 V | Solar panel → CN3791 MPPT → 18650 pack | LM2596 input |
| 5 V | LM2596 buck (12 V → 5 V) | JSN-SR04T, SEN0189, SEN0244, pH kit, NodeMCU `VIN` |
| 3.3 V | NodeMCU onboard regulator + AMS1117 | ESP8266 core, ADS1115, DS18B20, dividers |

> **Common ground is mandatory** across the 12 V, 5 V and 3.3 V sections, otherwise the
> sensor readings will float.

---

## Safety rules (read before wiring)

1. **Fuse the 12 V feed** (2 A blade fuse) — a shorted wire can otherwise overheat the harness.
2. **Never connect 5 V sensor outputs directly to ESP8266 GPIOs** — always divide down to ≤3.3 V (see each module doc).
3. **Keep the ESP8266 inside the sealed enclosure**; probe cables exit only through IP68 glands.
4. **Potable water:** use food-safe probe materials if the tank supplies drinking water.
5. **No actuator in the tank:** TankGuard monitors water quality and controls the pump only. Draining/flushing the tank is manual.

---

## H1 firmware

The home-side firmware lives in [`h1_home/`](h1_home/) (Arduino sketch, ESP8266).

1. Edit [`h1_home/config.h`](h1_home/config.h): set `WIFI_SSID`, `WIFI_PASS`, `TANK_DATA_URL`.
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

## Cleaner firmware (C1 — ESP32, open loop)

[`c1_cleaner/`](c1_cleaner/) drives the 2R cleaning arm: two fixed 20 cm links,
one brush at the tip, both joints on generic DC gear motors. It is a **separate
unit with its own power**, not part of M1 or H1.

**Why ESP32:** 2 PWM + 2 DIR, two home switches, brush PWM, e-stop, lid and the
level link — more I/O than a NodeMCU exposes.

**No position feedback.** There are no encoders on this build, so the firmware
cannot servo to an angle. It drives each joint at a **calibrated duty for a
computed time** and dead-reckons the angle. The design absorbs that:

- both joints **re-home at every ring** (three per cycle), so drift never spans
  more than one pass;
- the planner's **arcs** are the unit of motion — the elbow holds one angle while
  the shoulder sweeps it, so each move is a single timed segment;
- the status JSON says `"openLoop": true` and its angles are estimates, not
  measurements.

Expected accuracy: a few degrees per ring, not the planner's 0.3 cm overlap. The
16 cm brush tolerates that; a wider overlap (or a compliant brush skirt) is the
mitigation, not a bigger number in the planner.

### Wiring (ESP32 DevKit)

| signal | pin | notes |
|---|---|---|
| shoulder PWM / DIR | 25 / 26 | H-bridge, 20 kHz LEDC |
| elbow PWM / DIR | 27 / 14 | H-bridge |
| shoulder / elbow home | 39 / 18 | NC switch to GND, trips at θ = 0 |
| brush PWM | 13 | MOSFET or second bridge channel |
| brush current | 36 | optional, ADC |
| e-stop | 19 | NC loop, HIGH = unsafe (fail-safe) |
| lid switch | 21 | NC to GND, HIGH = open |

### Drivetrain (12 V, 350 rpm, **no gearbox**)

350 rpm is **2,100 °/s** direct drive; the sweep needs 45 °/s, and a loaded DC
motor stalls below ~15 % duty, so continuous PWM cannot do it. The controller
modulates **in time**: a 15 ms full-duty burst, then 200 ms of coast. Each burst
advances ~10°, so the average is ~46 °/s — the planner's speed — with every
pulse at full torque, and the dwell helps the brush.

**Torque is the gate.** The joint needs ~40–70 kg·cm (≈20 kg·cm to hold a 1 kg
arm at 20 cm, plus brush drag). A small 350 rpm motor makes 2–5 kg·cm — check
the stall torque before building; if it is short, no PWM scheme fixes it.

### Calibration

1. `BURST_DUTY` stays 255; `BURST_MS` / `PAUSE_MS` set the rhythm (15 / 200 ms).
2. Measure the **advance per burst**: command a long move (e.g. 180°), count the
   pulses the firmware prints, and divide by the angle the arm actually covered
   — the coast is included in that number.
3. Put it in `SH_DEG_PER_BURST` / `EL_DEG_PER_BURST`. Do it **in water, brush
   loaded** — that is the number the cycle will see.
4. Re-check after the first few cycles; speed drifts with voltage and wear,
   which is why the cycle re-homes.

### Path

```
node tools/export-plan.mjs 9225 file:///.../tools/swept_area.html firmware/c1_cleaner/plan.json
node tools/plan-to-header.mjs firmware/c1_cleaner/plan.json firmware/c1_cleaner/path.h
```

`path.h` holds six arcs (three rings × two elbow branches). The tool's
"Export path (JSON)" button produces the same file without a headless browser.

### API

| request | effect |
|---|---|
| `GET /clean` | status: phase, ring/arc, estimates t1/t2, brush, level, lid, e-stop, fault |
| `GET /clean?mode=start` | home, then run the cycle (409 with a reason if interlocked) |
| `GET /clean?mode=stop` | stop after the current move, then park |
| `GET /clean?mode=home` / `reset` | re-home; clears a latched fault |
| `GET /` | tiny status page |

Interlocks are enforced on the device: e-stop, lid, level ≥ 15 % (from M1), and
optional brush-stall cut-out. Any fault cuts motor power, stops the brush and
latches until `reset`.
## Tank-side firmware

The tank-side firmware lives in [`m1_tank/`](m1_tank/) (Arduino sketch, ESP8266).

1. Edit [`m1_tank/config.h`](m1_tank/config.h): Wi-Fi, `TANK_DEPTH_CM`, pH calibration.
2. Libraries: `Adafruit ADS1X15`, `OneWire`, `DallasTemperature` (LittleFS and mDNS ship with the core).
3. Compile + flash (**4M1M layout** — the web dashboard lives in the 1 MB FS area):
   ```
   arduino-cli compile --fqbn "esp8266:esp8266:nodemcuv2:eesz=4M1M,xtal=80" firmware/m1_tank
   arduino-cli upload -p /dev/cu.usbserial-XXXX --fqbn "esp8266:esp8266:nodemcuv2:eesz=4M1M,xtal=80" firmware/m1_tank
   ```
4. With Wi-Fi set it serves:
   - `GET /data` → `{"score","level","ph","turb","tds","temp"}`
   - `GET /` → **the web dashboard from LittleFS** (see below), or a small
     inline status page when no bundle is flashed
   - mDNS: `http://tankguard.local`
5. With `WIFI_SSID` empty it starts AP **TankGuard-Tank** (open) and serves the same pages at `192.168.4.1`.

Point the home module at `http://<tank-ip>/data`.

### Flashing the web dashboard

The webapp (see [`../webapp/`](../webapp/)) is served by this sketch from
LittleFS, pre-gzipped (~150 KB). Build and flash the filesystem image:

```
cd ../webapp
npm run build && node tools/build-device-bundle.mjs
esptool.py --port /dev/cu.usbserial-XXXX write_flash 0x300000 device-littlefs.bin
```

Desk-test the whole serving scheme with no hardware:
`node tools/device-server.mjs` → http://127.0.0.1:4311/

### Optional nRF24L01+ direct link

Instead of Wi-Fi, the two boards can talk over a 2.4 GHz nRF24L01+ (≈1 km LOS at
250 kbps). This needs the pin remap in [`NRF24_LONG_RANGE.md`](NRF24_LONG_RANGE.md).
Then build **both** sketches with `USE_NRF24=1`:

```
arduino-cli compile --fqbn esp8266:esp8266:nodemcuv2 \
  --build-property "compiler.cpp.extra_flags=-DUSE_NRF24=1" firmware/m1_tank
arduino-cli compile --fqbn esp8266:esp8266:nodemcuv2 \
  --build-property "compiler.cpp.extra_flags=-DUSE_NRF24=1" firmware/h1_home
```

Library needed: `RF24`. With nRF enabled the tank drops serial debug and the home
unit drops Wi-Fi; the protocol is described in `NRF24_LONG_RANGE.md`.

## Bring-up order (recommended)

1. Power the NodeMCU alone from USB → confirm it boots and joins Wi-Fi.
2. Add the ADS1115 → scan I²C, confirm address `0x48`.
3. Add one sensor at a time, confirm plausible raw values.
4. Add the DS18B20 and JSN-SR04T → confirm readings.
5. Mount the enclosure and run the probe cables through the glands.
6. Enable deep sleep last (D0→RST jumper) once everything else is stable.

See `PINMAP.md` for the exact pin allocation and the module docs for step-by-step wiring.
