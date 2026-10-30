# M1 — Water-Quality Monitor (Hardware Build)

The M1 module is the base unit: it senses the water and computes the TankScore. It is
built around an **ESP8266 NodeMCU** and an **ADS1115 16-bit ADC** (required because the
ESP8266 has only one analog input). See [`PINMAP.md`](PINMAP.md) for the shared pin map.

---

## 1. Bill of materials (ESP8266 version)

| # | Part | Spec | Qty | Approx. ₹ |
|---|---|---|---|---|
| 1 | ESP8266 NodeMCU v3 | ESP-12E, micro-USB | 1 | 180 |
| 2 | ADS1115 module | 16-bit, 4-ch, I²C, 0x48 | 1 | 120 |
| 3 | Turbidity sensor | SEN0189 (or clone), 5 V, IP68 | 1 | 180–450 |
| 4 | TDS sensor | SEN0244 / XKC-Y25, 5 V | 1 | 350–900 |
| 5 | pH sensor kit | SEN0161-V2 (5 V, analog Po) | 1 | 650–1800 |
| 6 | Temperature probe | DS18B20 waterproof | 1 | 40 |
| 7 | Ultrasonic level | JSN-SR04T, 5 V, IP67 | 1 | 200 |
| 8 | Resistors | 10 kΩ ×4, 1 kΩ ×2, 4.7 kΩ ×2 | set | 20 |
| 9 | Capacitors | 100 µF / 25 V, 0.1 µF ×2 | set | 20 |
| 10 | Buck converter | LM2596 (12 V → 5 V, ≥2 A) | 1 | 35 |
| 11 | LDO (optional) | AMS1117-3.3 if not using NodeMCU reg | 1 | 12 |
| 12 | Solar panel | 5–10 W, 6 V or 12 V | 1 | 350–950 |
| 13 | Battery + charger | 18650 ×2–4 + TP4056/CN3791 | 1 set | 150–420 |
| 14 | Enclosure | IP65/66 box + IP68 glands + heat shield | 1 | 180–520 |
| 15 | Wiring | Dupont, perf board, heat-shrink, fuse | set | 150 |
| 16 | Calibration | pH 4.0/7.0 buffers + distilled water + KCl | 1 set | 120–250 |
| 17 | nRF24L01+ PA/LNA (optional) | 2.4 GHz, SMA antenna, **3.3 V only**, + 100 µF/10 µF | 1 | 250–450 |

**M1 parts subtotal: ~₹3,000 (minimum) to ~₹5,500 (grade-A).**

---

## 2. Wiring — step by step

### 2.1 Power first (do this with everything OFF)
1. Connect the **12 V** battery/solar rail to the **LM2596 IN+ / IN−**.
2. Set the LM2596 output to **5.0 V** (measure with a multimeter before connecting anything).
3. Connect **LM2596 OUT+ → NodeMCU `VIN`** and **OUT− → NodeMCU `GND`**.
4. Confirm the NodeMCU powers up (onboard LED) and boots.

> Never feed 5 V into `3V3`. `VIN` accepts 5 V (goes through the onboard regulator).

### 2.2 ADS1115 (I²C)
| ADS1115 pin | Connect to |
|---|---|
| VDD | NodeMCU `3V3` |
| GND | NodeMCU `GND` |
| SCL | NodeMCU **D1** (GPIO5) |
| SDA | NodeMCU **D2** (GPIO4) |
| ADDR | **GND** (sets address 0x48) |

Add 4.7 kΩ pull-ups from SDA→3V3 and SCL→3V3 if your module doesn't include them.

### 2.3 Turbidity sensor (SEN0189) → A0 (with ÷2 divider)
SEN0189 outputs up to ~4.5 V — too high for the 3.3 V ADS1115, so divide by 2:

```
SEN0189 Ao ──[ R1 10k ]──┬── ADS1115 A0
                          │
                       [ R2 10k ]
                          │
                         GND
```
- SEN0189 **VCC → 5 V**, **GND → GND**, **Ao → R1** as above.
- Result: 4.5 V becomes 2.25 V. Safe.

### 2.4 TDS sensor (SEN0244 / XKC-Y25) → A1
| Sensor | Connect to |
|---|---|
| VCC | 5 V |
| GND | GND |
| Analog out | ADS1115 **A1** (direct — max ~2.3 V) |

### 2.5 pH sensor (SEN0161-V2) → A2
| pH board pin | Connect to |
|---|---|
| VCC | 5 V (or per board spec) |
| GND | GND |
| Po (analog) | ADS1115 **A2** (direct; 0–3.0 V) |
| BNC probe | screw terminal on board |

> Keep the pH probe **wet** (KCl storage solution or pH 4.0 buffer) when not in use.

### 2.6 DS18B20 temperature → D6
| DS18B20 wire | Connect to |
|---|---|
| VDD (red) | 3.3 V |
| GND (black) | GND |
| DQ (yellow) | NodeMCU **D6** (GPIO12) |

Add a **4.7 kΩ resistor from DQ → 3.3 V**.

### 2.7 JSN-SR04T ultrasonic level → D7 / D5 (with divider on Echo)
| JSN-SR04T pin | Connect to |
|---|---|
| VCC | 5 V |
| GND | GND |
| TRIG | NodeMCU **D7** (GPIO13) |
| ECHO | divider → NodeMCU **D5** (GPIO14) |

Echo is a **5 V** signal — divide it down:
```
ECHO ──[ R1 1k ]──┬── NodeMCU D5 (GPIO14)
                   │
                [ R2 1k ]
                   │
                  GND
```
(5 V → 2.5 V, safely within 3.3 V.)

### 2.8 Deep-sleep wake
Jumper **D0 (GPIO16) → RST**. This lets the ESP8266 wake itself from deep sleep on a
timer. Add last, after everything else works.

---

## 3. Complete connection summary

| From | To |
|---|---|
| LM2596 OUT+ (5 V) | NodeMCU VIN; all 5 V sensors' VCC |
| LM2596 OUT− | NodeMCU GND; all sensor GND |
| NodeMCU 3V3 | ADS1115 VDD, DS18B20 VDD, I²C pull-ups, divider tops |
| NodeMCU D1 | ADS1115 SCL |
| NodeMCU D2 | ADS1115 SDA |
| ADS1115 ADDR | GND |
| ADS1115 A0 | turbidity divider node |
| ADS1115 A1 | TDS analog out |
| ADS1115 A2 | pH Po |
| NodeMCU D6 | DS18B20 DQ (+4.7 kΩ to 3V3) |
| NodeMCU D7 | JSN-SR04T TRIG |
| NodeMCU D5 | JSN-SR04T ECHO **via 1k/1k divider** |
| NodeMCU D0 | RST (deep-sleep wake) |

---

## 4. Assembly into the enclosure

1. Mount the NodeMCU, ADS1115 and LM2596 on perf board or a small carrier.
2. Drill the enclosure lid and fit **IP68 cable glands** for: sensor cable bundle, solar cable, valve cable (M2).
3. Seal the buck converter and battery in the box; add a **heat shield** if the box sits in direct sun.
4. Pot or heat-shrink exposed solder joints.
5. Label every cable at both ends.
6. Angle the solar panel toward the sun; keep the enclosure shaded if possible.

---

## 5. Bring-up tests (expected values)

| Test | How | Pass criteria |
|---|---|---|
| Power | Multimeter on LM2596 out | 5.0 V ±0.1 V |
| Boot | USB serial @ 115200 | boot log, Wi-Fi AP appears |
| I²C | `i2cdetect`-style scan / serial | device at **0x48** |
| Turbidity | probe in clear then muddy water | clear ≈ high V, muddy ≈ low V (A0 changes) |
| TDS | probe in distilled then salt water | A1 rises with dissolved solids |
| pH | probe in 7.0 then 4.0 buffer | A2 changes by the expected slope |
| Temperature | compare with thermometer | ±1 °C |
| Level | move probe 10 cm | reading changes ~10 cm |
| Deep sleep | enable wake, watch | current drops to <1 mA between cycles |

---

## 6. Calibration notes

- **pH:** two-point calibration — record ADC value in pH 7.0 and pH 4.0; firmware fits slope + offset.
- **TDS:** calibrate against a known ppm standard (or a TDS reference meter).
- **Turbidity:** calibrate with a known standard; note it is a relative indicator for TankScore, not a compliance meter.

> Full firmware is separate; this document covers only the physical hardware.
