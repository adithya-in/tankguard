# TankGuard — Project Proposal

**An IoT-Enabled Solar-Powered Water Quality Monitoring System for Household & Institutional Water Storage Tanks**

---

## Page 1: The Problem & Our Impact

### The Silent Crisis in Every Tank

**India's Forgotten Water Tanks: A Public Health Emergency in Waiting**

Every day, millions of households, schools, hospitals, hostels, and apartment complexes across India store water in overhead or underground tanks. The water enters treated—but what comes out is a different story.

| The Reality | The Consequence |
|-------------|-----------------|
| Chlorine residual dissipates within 24–48 hours | Bacteria, algae, and biofilm multiply unchecked |
| Sediment & sludge accumulate on tank floors | Heavy metals, microbes, and particulates re-suspend with every refill |
| Biofilm coats walls & submerged surfaces | Persistent contamination source resistant to casual cleaning |
| Tanks cleaned once every 6–18 months (or never) | Water quality degrades silently—detected only by foul taste, odour, or illness |

**WHO identifies storage as the critical recontamination point**: *"The safe water chain breaks at the point of storage unless tanks are kept clean and covered."* Yet in practice, cleaning is calendar-based guesswork or purely reactive—after the water has already become unusable.

### The Scale in India

- **200+ million** household tanks (urban + rural)
- **1.5+ million** institutional tanks (schools, hospitals, hostels, offices, apartments)
- **Zero** affordable, automatic systems that tell you *when* to clean

### TankGuard's Impact

We convert **guesswork into evidence**. TankGuard is a solar-powered, IoT sensor node that sits *inside* the tank and continuously measures the parameters that actually change during storage:

| Parameter | Why It Matters |
|-----------|----------------|
| **Turbidity** | Primary sludge & biofilm indicator—rises before you can see it |
| **pH** | Drift signals algae, decay, seepage, or corrosion |
| **TDS / EC** | Dissolved solids leach from settled debris and scale |
| **Temperature** | Biological activity clock; enables temp-compensation of other readings |
| **Water Level** | Water age since refill; empty/full detection |

These feed **TankScore**—a single, weighted, trend-aware index that answers one question conclusively:

> **"Is it time to clean this tank?"**

**Status Output:** `GOOD` · `WATCH` · `CLEAN-REQUIRED`

### What Changes

| Before TankGuard | After TankGuard |
|------------------|-----------------|
| Clean every 6 months (wasted effort) or wait for bad smell (too late) | Clean *exactly when needed*—evidence-based, not calendar-based |
| No data, no history, no alert | 90-day local history, trend graphs, instant phone dashboard |
| Manual inspection = climbing tanks, opening lids | Zero physical access needed—data comes to your phone |
| Cloud-dependent, subscription-based, privacy risk | **100% local**—no cloud, no account, no data leaves the home |

**Result:** Healthier water, less wasted cleaning effort, reduced water loss from unnecessary drain-and-refill, and a scalable model for institutions managing hundreds of tanks.

---

## Page 2: Components List with Pricing (Indian Market)

### Bill of Materials — M1 Base Kit (Prototype Scope)

| # | Category | Component | Specification / SKU | Qty | Unit (₹) | Total (₹) |
|---|----------|-----------|---------------------|-----|----------|-----------|
| 1 | Compute | ESP32-WROOM-32 Dev Board | FireBeetle-class (DFR0478) | 1 | 1,237 | 1,237 |
| 2 | Compute | ADS1115 16-bit ADC | 4-channel I²C analogue expansion | 1 | 145 | 145 |
| 3 | Sensing | pH Sensor Kit | Gravity SEN0161-V2 (probe + interface) | 1 | 2,669 | 2,669 |
| 4 | Sensing | TDS/EC Sensor | Gravity SEN0244 (analogue) | 1 | 1,489 | 1,489 |
| 5 | Sensing | Turbidity Sensor | Gravity SEN0189 (analogue optical) | 1 | 600 | 600 |
| 6 | Sensing | Temperature Probe | Waterproof DS18B20, 1 m cable | 1 | 44 | 44 |
| 7 | Sensing | Water Level Sensor | JSN-SR04T waterproof ultrasonic | 1 | 270 | 270 |
| 8 | Power | Buck Converter | 12 V → 5 V DC-DC (LM2596S) | 1 | 78 | 78 |
| 9 | Power | 3.3 V LDO | Low-quiescent HT7333 (ESP32 rail) | 1 | 65 est. | 65 |
| 10 | Power | Sensor-Rail MOSFET Switch | IRF520 high-side enable boards | 2 | 42 | 84 |
| 11 | Power | MPPT Charge Controller | CN3791 solar module | 1 | 420 | 420 |
| 12 | Power | Solar Panel | 10 W / 12 V polycrystalline | 1 | 950 est. | 950 |
| 13 | Power | Battery Cells | 18650 Li-ion ~3000 mAh each | 4 | 190 est. | 760 |
| 14 | Power | Battery Protection | 3S BMS with balance | 1 | 420 est. | 420 |
| 15 | Enclosure | Waterproof Housing | IP66 box, cable glands, mounting plate | 1 | 900 est. | 900 |
| 16 | Enclosure | Heat-Protection Set | Foil-foam liner, reflective shield, desiccant | 1 | 620 est. | 620 |
| 17 | Build | Wiring & Misc | Connectors, divider resistors, fasteners, potting | 1 | 739 est. | 739 |
| 18 | Calibration | pH Buffers | 4.00 / 6.86 / 9.18 buffer solutions (set) | 1 | 580 est. | 580 |
| 19 | Calibration | Turbidity Standards | 0 NTU (DI) + 1000 NTU formazin (set) | 1 | 480 est. | 480 |
| 20 | Spares | Probe Care & Spares Kit | KCl storage, spare caps/seals, backup electrode | 1 | 1,000 est. | 1,000 |

**M1 Subtotal (Base Kit — Prototype): ₹13,550**

---

### Optional Add-On Modules (Future Expansion)

| Module | Components | Subtotal |
|--------|------------|----------|
| **M2 — Auto Pump Control** | 12 V relay/contactor kit, mains wiring, CT dry-run clamp | ₹1,000 |

**Full 2-Module Product Line: ₹14,550** (under ₹15,346 budget cap)

> **Note:** Prices marked "est." are typical Indian street estimates; verified retailer prices used where available. Parts-only cost—excludes labour, GST, freight, duties. ~10% contingency (≈₹1,455) brings delivered full-family unit to ~₹16,005.

---

## Page 3: 2-Week Execution Timeline

### Compressed Delivery Plan — 14 Days

| Week | Days | Activity | Deliverable / Milestone |
|------|------|----------|-------------------------|
| **Week 1** | **Day 1–2** | **Parts Procurement & Bring-Up**<br>• Order all M1 components (same-day local vendors + quick-ship)<br>• Breadboard each sensor independently: pH, TDS, turbidity, DS18B20, JSN-SR04T<br>• Validate raw readings against handheld reference meters | All 5 sensors reporting plausible values on serial monitor |
| | **Day 3–4** | **Calibration & ADC Integration**<br>• Two/three-point pH calibration (4.0 / 6.86 / 9.18)<br>• TDS calibration with standard conductivity solution<br>• Turbidity calibration: 0 NTU (DI) + 1000 NTU formazin<br>• Wire ADS1115 for all 3 analogue channels; implement median-filtered sampling | Calibration files persisted; each sensor ±2% of reference |
| | **Day 5** | **Power Train & Deep Sleep**<br>• Assemble solar → CN3791 → 4×18650 pack → 12 V bus → buck → 5 V rail → HT7333 → 3.3 V<br>• Implement MOSFET-switched sensor rail + deep-sleep timer wake (3 h)<br>• Measure real current: sleep, measure, WiFi publish | Sustained solar-only operation >48 h confirmed |
| **Week 2** | **Day 6–7** | **Firmware Core: TankScore Engine**<br>• Implement weighted scoring per Table 2 thresholds<br>• Add 14-day trend detection (turbidity/TDS/pH slope)<br>• Interval counter: days since last confirmed cleaning (default 90 d)<br>• Output: GOOD / WATCH / CLEAN-REQUIRED + persistent alert flag | TankScore logic unit-tested with synthetic data vectors |
| | **Day 8–9** | **Local Web Dashboard**<br>• ESP32 captive-portal WiFi provisioning (first boot)<br>• mDNS hostname `tankmon.local`<br>• LittleFS: static SPA (gauges, Chart.js history, battery/solar, TankScore banner)<br>• "Tank cleaned ✓" button → resets interval counter & logs event | Phone opens `http://tankmon.local` → live dashboard, zero cloud |
| | **Day 10** | **Enclosure & On-Tank Install**<br>• Mount probes in IP66 box with cable glands, heat shield, desiccant<br>• Route probe cables through sealed entry; secure to tank lid/wall<br>• Position solar panel for optimal daily insolation | Fully sealed, weather-ready node installed on real tank |
| | **Day 11–13** | **Soak Test & Validation**<br>• Continuous 3-hour sampling cycle logging to flash ring buffer<br>• Daily dashboard review: verify readings, TankScore transitions, battery health<br>• Simulate "cleaning event" → confirm counter reset & status returns to GOOD | 72+ hours field data; drift <5%; TankScore correlates with visual inspection |
| | **Day 14** | **Documentation & Demo**<br>• Final calibration records, drift analysis, power budget actuals<br>• User guide: WiFi setup, calibration rerun, probe care, "Tank cleaned" workflow<br>• 10-min live demo + slide deck for submission | **Complete, documented, demonstrable prototype** |

---

### Risk Buffer (Built-In)

| Risk | Mitigation in Timeline |
|------|------------------------|
| Delayed component delivery | Day 1–2 uses local vendors (Robu, Semicon, Amazon.in same-day); fallbacks identified |
| Sensor calibration drift | Day 3–4 builds calibrated baseline; Day 11–13 monitors drift in real conditions |
| Solar underperformance | Battery sized for 3-week zero-sun autonomy; deep-sleep verified Day 5 |
| WiFi range at tank | Captive-portal AP fallback; local flash logging never loses data |
| Firmware integration bugs | Modular bring-up (Days 1–5) isolates each subsystem before integration |

---

### Summary

| Metric | Target |
|--------|--------|
| **Total Calendar Time** | 14 days |
| **Hardware Cost (M1)** | ₹13,550 |
| **Sensors Operational** | 5 (pH, TDS, Turbidity, Temp, Level) |
| **Dashboard** | Local, phone-accessible, no cloud |
| **Autonomy** | Solar + battery, 3-week zero-sun reserve |
| **Decision Engine** | TankScore: GOOD / WATCH / CLEAN-REQUIRED |
| **Validation** | 72+ hour soak test on real tank |

**TankGuard delivers a working, evidence-based tank cleaning indicator in two weeks—ready to protect the water millions of Indians drink every day.**

---

*Prepared: October 2026 · For academic/project submission · Prices indicative, subject to vendor confirmation*