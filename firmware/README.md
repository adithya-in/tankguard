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

## Cleaner firmware (C1 — ESP8266, open loop)

[`c1_cleaner/`](c1_cleaner/) drives the 2R cleaning arm: two fixed 20 cm links,
one brush at the tip, both joints on generic DC gear motors. It is a **separate
unit with its own power**, not part of M1 or H1.

### Why ESP8266

The arm needs four PWM outputs, two home switches, one safety loop, a pump relay
and a brush channel. A NodeMCU exposes exactly enough: D5-D8 drive the two
dual-PWM drivers, D1/D2 read the homes, D0 drives the brush, D4 the pump and D3
the safety loop. Serial stays on TX/RX, and the controller page is served from
flash.

The constraint is boot strapping: D3 (GPIO0), D4 (GPIO2) and D8 (GPIO15) must
sit in their boot states, so the safety loop and the relay are wired to match.

### Build

```
arduino-cli compile --fqbn esp8266:esp8266:nodemcuv2 firmware/c1_cleaner
arduino-cli upload  -p COM7 --fqbn esp8266:esp8266:nodemcuv2 firmware/c1_cleaner
```

### No position feedback (what it costs)

There are no encoders on this build, so the firmware cannot servo to an angle.
It drives each joint open-loop — a **calibrated duty for a computed time** — and
dead-reckons the angle from the burst count. Three things make that workable:

- both joints **re-home at every ring** (three per cycle), so drift never spans
  more than one pass;
- the planner's **arcs** are the unit of motion — the elbow holds one angle while
  the shoulder sweeps it, so each move is a single timed segment;
- the status JSON says `"openLoop": true` and its angles are estimates, not
  measurements.

What it costs is accuracy: a few degrees per ring, not the planner's 0.3 cm
overlap. The 16 cm brush tolerates that; a wider overlap (or a compliant brush
skirt) is the mitigation, not a bigger number in the planner. An optional 12 PPR
encoder on the motor shaft would give 0.35 °/count at the joint if fitted later.

### Wiring (ESP8266 NodeMCU)

The arm motors use dual-PWM drivers: each joint has an RPWM and an LPWM input,
not a PWM plus DIR pair.

| signal | pin | notes |
|---|---|---|
| arm A (shoulder) RPWM / LPWM | D5 / D6 (14 / 12) | |
| arm B (elbow) RPWM / LPWM | D7 / D8 (13 / 15) | D8 must be LOW at boot |
| shoulder / elbow home | D2 / D1 (4 / 5) | NC switch to GND, internal pull-up |
| brush PWM | D0 (16) | MOSFET or second bridge channel |
| pump relay | D4 (2) | **active-LOW**; HIGH at boot = off |
| safety loop | D3 (0) | e-stop + lid in series to 3V3, 10 kΩ pull-down; HIGH = safe |
| brush current | A0 | optional, single ADC |
| serial | TX / RX | debug only |

GPIO0, GPIO2 and GPIO15 are strapping pins: 0 and 2 must be HIGH at boot, 15
LOW. The safety loop holds D3 high when closed, and the active-low relay holds
D4 high when off, so both straps are satisfied by the normal wiring.

### Drivetrain (TJX28ZRM — RS395 12 V + 21.5:1, 11.3 N·cm rated)

Datasheet: 348.8 rpm no-load, **279 rpm rated**, **11.3 N·cm rated / ~34 N·cm
stall**, 0.62 A rated / 4.5 A stall, ≤2 ° backlash.

**Why not continuous PWM.** 279 rpm at the joint is 1,674 °/s, so 45 °/s would be
a ~2.7 % duty — below the point where a loaded DC motor turns at all. The
controller therefore runs **full-duty bursts**: 250 ms on, 200 ms coast
(`BURST_MS` / `PAUSE_MS`), ~10 ° of joint travel per burst, tuned per joint (see
Calibration).

**Torque is comfortable.** The head is a sparse ring of bristles on the perimeter
only, with an open centre for the pump intake — water flows through, so there is
no seal and no vacuum downforce. Joint load is ≈ 8–16 N·cm against 11.3 rated /
~34 stall. Expect **25–35 °/s** and a **55–80 s cycle**. The pump is sequenced
with the brush for power and sludge behaviour, not as a safety gate.

### Controller page (standalone hotspot)

With `WIFI_SSID` empty (the default) the cleaner runs as its own access point:

1. Join the **TankGuard-C1** hotspot, password **tankguard**.
2. Open **http://192.168.4.1**.
3. The page is served from the ESP8266 itself, so there is no router, no internet
   and no app to install. It polls `/clean` once a second and drives the same API
   as `curl`.

The page has a status grid (ring/arc, both angles, level, bursts, last move), a
progress bar, the four interlocks as dots, Run controls (Check, Home, Start with
a ring selector and the bench bypass, Stop, Reset) and a jog panel for
calibration. Start, Home, Reset and Jog are disabled while the arm is moving;
Stop stays live.

`levelFresh` will be false in hotspot mode because M1 is not on that network, so
Start refuses until **Skip level check** is ticked. The e-stop and lid interlocks
are always live.

### Calibration

The advance per burst differs by joint **and by direction**, because the shoulder
works with and against gravity. Four numbers, all in `config.h`:

1. `BURST_DUTY` stays 255; `BURST_MS` / `PAUSE_MS` set the rhythm (250 / 200 ms).
2. Home the arm, then jog one joint a known number of bursts:
   `curl "http://<ip>/jog?joint=sh&bursts=5&dir=1"`, and again with `dir=-1`.
3. Measure the angle the arm actually moved with a protractor and divide by the
   burst count. That is the advance for that direction, coast included.
4. Put it in `SH_DEG_PER_BURST_FWD` / `_BACK` (or the `EL_` pair). Do it **in
   water, brush loaded** — that is the number the cycle will see.
5. Re-check after the first few cycles; speed drifts with voltage and wear, which
   is why the cycle re-homes.

`RAMP_MS` (40 ms) softens the start of every burst, and `DEAD_TIME_MS` (20 ms)
coasts the bridge before a reversal. Both exist to keep the inrush off the supply
and the gearbox, not to change the calibration.

### Demo runbook

1. Power on with the lid switch closed and the e-stop released. Join the
   **TankGuard-C1** hotspot (password `tankguard`) and open `http://192.168.4.1`.
   The arm homes at boot; the serial log prints the two switch states.
2. Pre-flight: `curl "http://<ip>/clean?mode=check"`. Expect `estop:0`, `lid:1`,
   `home1:0`, `home2:0`, `angleValid:1`. `levelFresh:0` is acceptable on a bench
   with no monitor attached.
3. Run one ring: `curl "http://<ip>/clean?mode=start&rings=1"`. Omit `rings` for
   the full three-ring cycle.
4. With no monitor attached, add `force=1` to skip the level gate. The e-stop and
   lid interlocks stay live; only the dry-run check is bypassed.
5. `mode=stop` finishes the current burst, then parks. `mode=reset` clears a
   latched fault and re-homes.
6. If the arm jams, press the e-stop. Without a shunt the firmware cannot see a
   stall, so the e-stop is the only obstruction protection on this build.

### Path

Six arcs — two elbow branches on each of three rings (8.0 / 23.7 / 39.4 cm) —
generated from `tools/swept_area.html`:

```
node tools/export-plan.mjs 9225 file:///.../tools/swept_area.html firmware/c1_cleaner/plan.json
node tools/plan-to-header.mjs firmware/c1_cleaner/plan.json firmware/c1_cleaner/path.h
```

`path.h` holds the result. The tool's "Export path (JSON)" button produces the
same file without a headless browser.

### API

| request | effect |
|---|---|
| `GET /clean` | status: `openLoop`, phase, ring/arc, estimated t1/t2, brush, pump, level, lid, e-stop, fault, bursts, lastMoveMs, home1/2, duty1/2 |
| `GET /clean?mode=start` | home, then run the cycle (409 with a reason if interlocked) |
| `GET /clean?mode=start&rings=1` | run only the first ring (1..3, default 3) |
| `GET /clean?mode=start&force=1` | bench demo: skip the level gate, keep e-stop and lid live |
| `GET /clean?mode=stop` | stop after the current move, then park |
| `GET /clean?mode=home` / `reset` | re-home; clears a latched fault |
| `GET /clean?mode=check` | pre-flight: interlocks, home switches, level freshness, angle validity |
| `GET /jog?joint=sh\|el&bursts=N&dir=1\|-1` | calibration: fire N bursts (max 20), returns the expected angle; 409 if busy or interlocked |
| `GET /` | controller page, served from flash |

Interlocks are enforced on the device: e-stop (NC), lid (NC), level ≥ 15 % (from
M1), and optional brush-stall cut-out. Any fault cuts motor power, stops the
brush and latches until `reset`.
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
