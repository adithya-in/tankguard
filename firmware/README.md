# TankGuard — Home-Side Module (Hardware)

This folder contains the **hardware build instructions** for the TankGuard home-side
unit, built around an **ESP8266** (NodeMCU / Wemos D1 mini). The system is split into
two modules that share one controller:

| Module | Document | What it does |
|---|---|---|
| **M1 — Monitor** | [`HARDWARE_M1_Monitor.md`](HARDWARE_M1_Monitor.md) | Reads turbidity, TDS, pH, temperature and water level; computes TankScore; hosts the local dashboard |
| **M2 — Sludge Flush** | [`HARDWARE_M2_Flush.md`](HARDWARE_M2_Flush.md) | Drives the 1″ normally-closed solenoid valve at the tank floor |
| **Pin map** | [`PINMAP.md`](PINMAP.md) | Master ESP8266 pin allocation (shared by both modules) |

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

## Bring-up order (recommended)

1. Power the NodeMCU alone from USB → confirm it boots and joins Wi-Fi.
2. Add the ADS1115 → scan I²C, confirm address `0x48`.
3. Add one sensor at a time, confirm plausible raw values.
4. Add the DS18B20 and JSN-SR04T → confirm readings.
5. Only then wire the M2 MOSFET + valve, and test with the tank empty/low.
6. Enable deep sleep last (D0→RST jumper) once everything else is stable.

See `PINMAP.md` for the exact pin allocation and the two module docs for step-by-step wiring.
