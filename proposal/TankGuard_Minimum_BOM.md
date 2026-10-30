# TankGuard — Absolute Minimum BOM (Lowest Cost Indian Market)

**Target: Working prototype for < ₹6,000 parts**

---

## Core Monitor (M1) — Bare Minimum

| # | Component | Cheapest Indian Option | Qty | Est. Price | Source |
|---|-----------|------------------------|-----|------------|--------|
| 1 | ESP32 Dev Board | ESP32-WROOM-32 (generic, no brand) | 1 | ₹220 | Robu.in / Amazon / Local |
| 2 | ADS1115 ADC | Generic breakout (blue PCB) | 1 | ₹120 | Robu.in / Amazon |
| 3 | pH Sensor | Gravity SEN0161-V2 **OR** generic BNC pH probe + BNC-to-ADC board | 1 | ₹1,800 / ₹650* | Robu.in / Amazon |
| 4 | TDS Sensor | Gravity SEN0244 **OR** generic TDS probe + XKC-Y25 module | 1 | ₹900 / ₹350* | Robu.in / Amazon |
| 5 | Turbidity Sensor | Gravity SEN0189 **OR** generic IR turbidity module (SEN0189 clone) | 1 | ₹450 / ₹180* | Robu.in / Amazon |
| 6 | Temperature | DS18B20 Waterproof (stainless, 1m) | 1 | ₹40 | Robu.in / Amazon |
| 7 | Water Level | JSN-SR04T (waterproof ultrasonic) | 1 | ₹220 | Robu.in / Amazon |
| 8 | Solar Panel | 5W 6V mini panel **OR** 10W 12V poly (if 12V system) | 1 | ₹350 / ₹650 | Robu.in / Local solar shop |
| 9 | Battery | 18650 × 2 (salvaged laptop cells OK) + TP4056 charger | 2+1 | ₹150 | Local / salvage |
| 10 | Charge Controller | CN3791 module **OR** TP4056 + DW01A (for 1S Li-ion) | 1 | ₹60 / ₹15 | Robu.in |
| 11 | Voltage Reg | LM2596 buck (12V→5V) + AMS1117 3.3V | 1+1 | ₹35 | Robu.in |
| 12 | Enclosure | Generic IP65 junction box (100×100×70mm) + cable glands | 1 | ₹180 | Local electrical shop |
| 13 | Heat Protection | Aluminium foil tape + foam sheet (DIY) | 1 | ₹50 | Local hardware |
| 14 | Wiring/Connectors | Dupont, screw terminals, heat shrink, perf board | 1 set | ₹150 | Local / Robu.in |
| 15 | Calibration | pH 4.0/7.0 buffer powder sachets + DI water | 1 set | ₹120 | Amazon / Lab supplier |

**M1 Absolute Minimum: ~₹4,500–5,200** (using *generic/clone sensors)

---

## Grand Total: **~₹4,500–5,200** (parts only, no actuator)

---

## Where to Buy Cheapest in India

| Platform | Best For |
|----------|----------|
| **Robu.in** | ESP32, ADS1115, sensors, solar, batteries — COD, fast |
| **Amazon.in** | Generic sensors, DS18B20, JSN-SR04T, enclosures |
| **Local Electronics Market** (Lamington Rd Mumbai, SP Rd Bangalore, Nehru Place Delhi) | 30–40% cheaper, instant, can bargain |
| **Salvage** | 18650 cells from old laptop batteries (free), TP4056 boards |

---

## Cost-Cutting Substitutions (Trade-offs)

| Original | Cheap Alternative | Trade-off |
|----------|-------------------|-----------|
| Gravity pH (₹2,669) | Generic BNC probe + ADC board (₹650) | Needs manual calibration, shorter life |
| Gravity TDS (₹1,489) | XKC-Y25 TDS module + probe (₹350) | Less accurate, no temp comp |
| Gravity Turbidity (₹600) | Clone SEN0189 module (₹180) | Noisy, needs averaging |
| 4×18650 + CN3791 (₹1,180) | 2× salvaged 18650 + TP4056 (₹150) | 1S only, less capacity, no MPPT |
| IP66 box + heat shield (₹1,520) | Generic junction box + foil tape (₹230) | Less weatherproof, hotter inside |
| 10W panel (₹950) | 5W 6V panel + boost (₹350) | Less power, needs sunny location |

---

## Minimum Viable Firmware Features

1. **Deep sleep** — wake every 3 hrs, measure, sleep (saves 95% power)
2. **Median filter** — 50 samples per sensor, take median (removes noise)
3. **TankScore** — simple threshold: turbidity>5 OR TDS>500 OR pH<6.5/8.5 = CLEAN NOW
4. **Local AP + Web Server** — ESP32 hosts `tankmon.local` (no router needed for demo)
5. **Pump control** — home-side relay drives the pump contactor (mains-safe)

---

## 3-Day Build Plan (Minimum)

| Day | Task |
|-----|------|
| **Day 1** | Breadboard all sensors → serial print raw values → calibrate pH/TDS/turbidity with buffers |
| **Day 2** | Add solar+battery+deep sleep → verify 24h run → build TankScore logic → test with dirty water |
| **Day 3** | Build the home unit (TFT + relay + button) → link it to the tank → install in box → demo |

---

## ⚠️ Risks at This Price

- **Generic pH probe** lasts 3–6 months (vs 1–2 years for Gravity)
- **No MPPT** = panel must face sun directly, larger panel needed
- **No heat shield** = ESP32 may overheat in direct summer sun (add vent holes)
- **No NIST calibration** = readings ±5–10% (good enough for trend detection)

---

## Recommended "Sweet Spot" (₹9,000)

If budget allows ₹3k more, upgrade **only these 3 items**:

| Upgrade | Cost Δ | Why |
|---------|--------|-----|
| Gravity pH SEN0161-V2 | +₹1,150 | Reliable, long life, easy calibration |
| Gravity TDS SEN0244 | +₹550 | Built-in temp comp, stable |
| 10W 12V panel + CN3791 | +₹500 | Reliable charging, smaller panel |

**Result: ₹7,500 — reliable, lasts 1+ years, still very cheap.**