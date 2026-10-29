# TankGuard — Master Pin Map (ESP8266)

**Board:** ESP8266 NodeMCU v3 (or Wemos D1 mini — pin names differ, GPIO numbers are the same).
**Rule:** all analog sensors go through the **ADS1115** (the ESP8266 has only one ADC).

---

## ESP8266 pin allocation

| Function | NodeMCU label | GPIO | Notes |
|---|---|---|---|
| I²C SDA → ADS1115 | **D2** | GPIO4 | 4.7 kΩ pull-up to 3.3 V recommended |
| I²C SCL → ADS1115 | **D1** | GPIO5 | 4.7 kΩ pull-up to 3.3 V recommended |
| JSN-SR04T **TRIG** | **D7** | GPIO13 | 3.3 V output is fine |
| JSN-SR04T **ECHO** | **D5** | GPIO14 | **5 V output — divide to ~2.5 V** |
| DS18B20 **DQ** | **D6** | GPIO12 | 4.7 kΩ pull-up to 3.3 V |
| Valve **MOSFET gate** | **D8** | GPIO15 | 10 kΩ pull-down to GND; **must be LOW at boot** |
| Deep-sleep wake | **D0** | GPIO16 | jumper to **RST** |
| A0 (built-in ADC) | A0 | ADC | **unused** — all analog via ADS1115 |

### Pins intentionally avoided
| Pin | GPIO | Reason |
|---|---|---|
| D3 | GPIO0 | Boot-mode strap (must be HIGH at boot) — used by some boards for FLASH button |
| D4 | GPIO2 | Boot strap + onboard LED (must be HIGH at boot) |
| D9 / D10 | GPIO3 / GPIO1 | UART RX/TX — reserved for serial debug |
| D8 | GPIO15 | *Used for valve, but only because it must be LOW at boot and a pulldown guarantees the valve is OFF at boot — safe.* |

> **Why D8/GPIO15 is safe for the valve:** GPIO15 must be LOW at boot. The MOSFET gate
> has a 10 kΩ pulldown, so at boot the gate is LOW → MOSFET OFF → normally-closed valve
> stays closed. This satisfies the boot requirement and keeps the valve de-energised.

---

## ADS1115 channel map (I²C address 0x48, ADDR → GND)

| ADS1115 input | Sensor | Signal range | Conditioning |
|---|---|---|---|
| **A0** | SEN0189 turbidity | 0–4.5 V (analog) | **÷2 divider** (10 kΩ / 10 kΩ) → 0–2.25 V |
| **A1** | SEN0244 TDS | 0–2.3 V | direct |
| **A2** | SEN0161-V2 pH | 0–3.0 V | direct (see note) |
| **A3** | spare | — | — |

- ADS1115 **VDD = 3.3 V**, so no input may exceed ~3.3 V.
- Use **gain = 1 (±4.096 V)** for A0 (turbidity) and **gain = 2 (±2.048 V)** for A1/A2 for better resolution. Gain is set per conversion in firmware.
- If your pH board output can approach 3.2–3.3 V, add a light divider (e.g. 10 kΩ/1 kΩ) on A2 to be safe.

---

## Power connections

| Rail | NodeMCU pin | Feeds |
|---|---|---|
| 5 V | `VIN` | JSN-SR04T VCC, SEN0189 VCC, SEN0244 VCC, pH kit VCC |
| 3.3 V | `3V3` | ADS1115 VDD, DS18B20 VDD, I²C pull-ups, divider tops |
| GND | `GND` | all sensor GND + MOSFET source + 12 V supply GND (common) |

---

## Boot-strap check before first power-up

- [ ] GPIO15 (D8) pulled to GND through 10 kΩ (valve off at boot)
- [ ] GPIO0 (D3) NOT held low (no FLASH button pressed)
- [ ] GPIO2 (D4) not forced low
- [ ] Echo line divided to ≤3.3 V
- [ ] Common ground between 12 V and 3.3 V sections
- [ ] 12 V valve line fused (2 A)
