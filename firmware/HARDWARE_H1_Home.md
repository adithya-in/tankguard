# H1 — Home-Side Module (near the pump motor switch)

The H1 module lives **inside the house, next to the pump motor switch**. It:

1. **Receives** tank data (level, turbidity, TDS, pH, temperature, TankScore) from the tank-side module over Wi-Fi.
2. **Shows** status locally (OLED + LEDs/buzzer) and on a small web page.
3. **Optionally automates the pump motor** — switches it ON/OFF based on tank level, with a manual override.
4. Can send a **flush command** back to the tank-side valve (optional).

> **SAFETY — read first.** The pump runs on **230 V AC mains**. The ESP8266 must never
> touch mains. It drives an **opto-isolated relay**, which in turn drives a **motor-rated
> contactor**. All mains wiring must be done by a **licensed electrician** and must keep
> the low-voltage and mains sides physically separated. Never bypass the pump's existing
> starter, overload/thermal protection, or earth.

---

## 1. Architecture

```
   TANK SIDE (outdoor)                         HOME SIDE (indoor, at motor switch)
 ┌───────────────────────────┐   Wi-Fi     ┌──────────────────────────────────────┐
 │ ESP8266 + ADS1115         │  HTTP/ESP-  │ ESP8266 (H1)                         │
 │  turbidity/TDS/pH/temp    │  NOW/MQTT   │  ├─ OLED status                      │
 │  ultrasonic level         │ ──────────► │  ├─ buzzer / LEDs                    │
 │  12 V flush valve (M2)    │ ◄────────── │  ├─ web dashboard                    │
 └───────────────────────────┘  commands   │  └─ opto-relay ──► contactor ──► PUMP│
                                            │       (5 V)         (230 V coil)     │
                                            └──────────────────────────────────────┘
                                                     │
                                          existing manual switch stays in circuit
```

**Data link options** (pick one):

| Option | Best when | Notes |
|---|---|---|
| **HTTP polling** (tank side runs a tiny web server) | Both on the same home Wi-Fi | Simplest; no broker; home side polls `/data` every 2–5 s |
| **ESP-NOW** | No router / weak Wi-Fi | Direct ESP8266-to-ESP8266, no router; short range through walls |
| **Local MQTT** | You already run a broker (Pi/old phone) | Cleanest for multiple tanks; needs an always-on broker |

This guide assumes **HTTP polling** (default) but the wiring is identical for all three.

---

## 2. Bill of materials

| # | Part | Spec | Qty | Approx. ₹ |
|---|---|---|---|---|
| 1 | ESP8266 NodeMCU | ESP-12E | 1 | 180 |
| 2 | OLED display | 0.96″ I²C SSD1306 (optional) | 1 | 180 |
| 3 | Opto-isolated relay module | 5 V, **10 A / 250 V AC**, 1-channel | 1 | 120–250 |
| 4 | Contactor (motor-rated) | AC-3, coil 230 V AC (or 12 V DC), ≥9 A | 1 | 350–900 |
| 5 | Current sensor (optional) | ACS712-20A or SCT-013 + burden | 1 | 150–350 |
| 6 | Buzzer + LEDs | 5 V buzzer, red/green LEDs, resistors | set | 40 |
| 7 | 5 V PSU | HiLink/HLK-PM01 (230 V→5 V) **or** USB adapter | 1 | 120–250 |
| 8 | Enclosure | DIN-rail or ABS box, 2 compartments (LV / mains) | 1 | 200–500 |
| 9 | Terminals / wire | screw terminals, 1.5 mm² mains wire, ferrules | set | 150 |
| 10 | MCB / fuse | 6 A MCB + 1 A fuse for LV | 1 | 200 |
| 11 | Manual selector | Auto / Off / Manual rotary switch | 1 | 120 |

> **Do not** use a bare 5 V relay coil on a GPIO, and **do not** switch the pump with a
> 10 A relay alone if the pump is larger than ~0.5 HP — use the relay to drive a
> **motor-rated contactor**.

---

## 3. Low-voltage wiring (ESP8266 side)

| Function | NodeMCU pin | GPIO | Notes |
|---|---|---|---|
| OLED SDA | D2 | GPIO4 | I²C |
| OLED SCL | D1 | GPIO5 | I²C |
| Relay IN | D5 | GPIO14 | Active-LOW modules are common — check your module |
| Buzzer | D6 | GPIO12 | via NPN transistor or direct if piezo |
| Green LED (OK) | D7 | GPIO13 | 330 Ω |
| Red LED (alert) | D0 | GPIO16 | 330 Ω |
| Current sensor (optional) | A0 | ADC | ACS712 output (0–3.3 V safe) |
| Mode switch (Auto/Off/Manual) | D3 / D4 | GPIO0/GPIO2 | **avoid** — use a 3-position switch read via an ADC divider on A0, or skip and use the web UI |

**Relay module wiring:**
| Relay module | Connect to |
|---|---|
| VCC | 5 V |
| GND | GND |
| IN | NodeMCU **D5** (GPIO14) |
| COM / NO | in series with the **contactor coil** circuit (low-voltage coil side only) |

> Keep the relay module's **opto-isolation**: power its VCC from the 5 V rail and its GND
> to the ESP8266 GND, but the **contact side is a separate circuit**. Never common the
> mains side with the ESP8266 ground.

---

## 4. Mains side (electrician only)

The relay's contact does **not** switch the pump directly. It switches the **coil** of a
motor-rated contactor; the contactor's power contacts switch the pump.

```
 230 V L ──[ MCB 6 A ]──┬───────────────────────────────┐
                        │                               │
                        │        ┌──────────────┐       │
                        ├────────┤ Contactor    │       │
                        │        │  coil (A1)   │       │
                        │        │              │       │
                        │        │  A2 ─────────┼──┐    │
                        │        └──────────────┘  │    │
                        │                          │    │
                        │     Relay COM ───────────┘    │
                        │     Relay NO ── N ────────────┘  (coil return)
                        │
                        ├── Contactor L1 ──► PUMP L
                        └── Contactor T1 ──► PUMP N
 230 V N ──────────────────────────────────────► PUMP N (via contactor)
 EARTH ────────────────────────────────────────► PUMP earth + enclosure earth
```

**Electrician checklist:**
- [ ] Pump rating (HP/kW, FLA) known; contactor rated **AC-3** for that motor.
- [ ] Contactor coil voltage matches the control supply (230 V AC or 12 V DC).
- [ ] MCB/fuse sized to the pump; existing overload/thermal protection retained.
- [ ] Earth bonded to pump body and metal enclosure.
- [ ] Low-voltage and mains compartments **physically separated** (≥6 mm creepage; use a partition).
- [ ] Cable glands, strain relief, and labels on every conductor.
- [ ] **Manual selector** (Auto/Off/Manual) installed so the pump can always be run by hand.
- [ ] Test with the pump **disconnected** first; then with a lamp; then the pump.

---

## 5. Automation logic (optional)

Only enable auto mode if the tank sensor is reliable. Default logic:

| Condition | Action |
|---|---|
| Level < **LOW** setpoint (e.g. 20 %) and pump idle | Pump **ON** |
| Level > **HIGH** setpoint (e.g. 95 %) | Pump **OFF** |
| Level not rising after 60 s of running (optional current/level check) | Pump **OFF** + red LED + buzzer (dry-run / no-flow) |
| TankScore poor and flush due | Send **flush** command to tank side (optional) |
| Selector = **Off** or **Manual** | Automation disabled; existing switch controls pump |
| Comms lost > 60 s | Pump **OFF** (fail-safe) + alert |

> **Fail-safe rule:** if the ESP8266 loses contact with the tank, or reboots, the relay
> de-energises and the pump stops. Never design it so a crash leaves the pump running.

---

## 6. Local display / dashboard

- **OLED:** TankScore, level %, pH, turbidity, pump state, link status.
- **Web page:** served by the H1 ESP8266 at `http://tankguard-h1.local/` with:
  - live values + last-update age
  - Auto / Off / Manual buttons
  - Setpoints (LOW/HIGH %) editable
  - "Flush now" button (sends command to tank side)

---

## 7. Bring-up tests

| Test | How | Pass criteria |
|---|---|---|
| PSU | Measure 5 V rail | 5.0 V ±0.1 V |
| Boot | Serial @ 115200 | boots, joins Wi-Fi |
| OLED | Power on | shows status page |
| Relay (LV only) | Toggle from web UI | relay clicks; LED matches |
| Contactor (no pump) | Relay on | contactor pulls in, releases |
| Pump (electrician) | Auto mode, low level | pump starts; stops at HIGH |
| Fail-safe | Unplug tank side | pump stops within 60 s, red alert |
| Manual override | Selector to Manual | existing switch controls pump |
| Current sensor (optional) | Pump running | A0/RMS shows expected current |

---

## 8. Placement & enclosure

1. Mount the H1 box **next to the existing motor switch**, on DIN rail if possible.
2. Keep the **mains compartment** separate and earthed; route mains at the bottom, low voltage at the top.
3. Use a **5 V PSU** (HLK-PM01 or USB adapter) for the ESP8266; do not steal power from the pump circuit.
4. Label the box: **"Auto pump controller — isolate before opening."**
5. Leave the original switch functional at all times.

> Full firmware is separate; this document covers only the physical hardware.
