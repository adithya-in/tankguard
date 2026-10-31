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
| Spare | **D8** | GPIO15 | free; must be **LOW at boot** (10 kΩ pull-down if used) |
| Deep-sleep wake | **D0** | GPIO16 | jumper to **RST** |
| A0 (built-in ADC) | A0 | ADC | **unused** — all analog via ADS1115 |

### Pins intentionally avoided
| Pin | GPIO | Reason |
|---|---|---|
| D3 | GPIO0 | Boot-mode strap (must be HIGH at boot) — used by some boards for FLASH button |
| D4 | GPIO2 | Boot strap + onboard LED (must be HIGH at boot) |
| D9 / D10 | GPIO3 / GPIO1 | UART RX/TX — reserved for serial debug |
| D8 | GPIO15 | Must be LOW at boot — usable only with a pull-down |

> **D8/GPIO15 note:** GPIO15 must be LOW at boot. It is free in the current build; if
> you connect anything there, add a 10 kΩ pull-down so the board still boots.

### nRF24L01+ variant (`USE_NRF24=1`)

Hardware SPI uses **D5/D7/D6**, so these signals move:

| Function | Normal | With nRF |
|---|---|---|
| DS18B20 DQ | D6 (12) | **D4 (2)** + 4.7 kΩ pull-up |
| JSN-SR04T TRIG | D7 (13) | **TX (1)** — serial debug lost |
| JSN-SR04T ECHO | D5 (14) | **RX (3)** via 1k/1k |
| nRF CE | — | **D0 (16)** |
| nRF CSN | — | **D3 (0)** + 10 kΩ pull-up |
| I²C | — | unchanged |

Full tables and home-side remap: [`NRF24_LONG_RANGE.md`](NRF24_LONG_RANGE.md).

### Optional 2-arm BTS7960 PWM remap

Use this only when driving **two DC arms/linear actuators** through two BTS7960
modules and you need PWM speed control on both. It frees **D5/D6/D7/D8** for PWM
by moving the three digital sensors. This is **not** the default wiring, and it
does **not** work with `USE_NRF24=1` (the nRF variant uses D5/D6/D7 for SPI).

| BTS7960 signal | Arm A | Arm B | GPIO | Notes |
|---|---|---|---|---|
| **RPWM** | **D5** | **D7** | 14 / 13 | PWM |
| **LPWM** | **D6** | **D8** | 12 / 15 | PWM; D8 needs 10 kΩ pull-down |
| R_EN | 3V3 via 10 kΩ | 3V3 via 10 kΩ | — | E-stop can pull low |
| L_EN | 3V3 via 10 kΩ | 3V3 via 10 kΩ | — | E-stop can pull low |
| VCC | 5 V | 5 V | — | logic supply **input** |
| GND | GND | GND | — | common ground |
| B+ | 12/24 V+ | 12/24 V+ | — | fused |
| B− | GND | GND | — | |
| M+ / M− | Arm A motor | Arm B motor | — | |

Sensor remap:

| Sensor | Default pin | Arm remap |
|---|---|---|
| DS18B20 DQ | D6 (12) | **D4 (2)** + 4.7 kΩ pull-up |
| JSN-SR04T TRIG | D7 (13) | **D3 (0)** + 10 kΩ pull-up |
| JSN-SR04T ECHO | D5 (14) | **D0 (16)** via 1 kΩ/1 kΩ divider |
| ADS1115 I²C | D1/D2 | unchanged |

Boot-strap requirements:

- **D3/GPIO0** must be HIGH at boot — TRIG pull-up holds it high.
- **D4/GPIO2** must be HIGH at boot — DS18B20 pull-up holds it high.
- **D8/GPIO15** must be LOW at boot — add 10 kΩ pull-down.
- **D0/GPIO16** is digital-only (no PWM); remove the D0→RST deep-sleep jumper.
- Add **10 kΩ pull-downs on all four BTS7960 PWM inputs** to prevent arm twitch at boot.

Firmware defines:

```cpp
#define DS18B20_PIN   2   // D4
#define PIN_TRIG      0   // D3
#define PIN_ECHO     16   // D0

#define ARM_A_RPWM   14   // D5
#define ARM_A_LPWM   12   // D6
#define ARM_B_RPWM   13   // D7
#define ARM_B_LPWM   15   // D8
```

Drive logic:

```cpp
analogWriteFreq(20000);   // 20 kHz
analogWriteRange(1023);

// forward A
analogWrite(ARM_A_RPWM, 700);
analogWrite(ARM_A_LPWM, 0);

// reverse A
analogWrite(ARM_A_RPWM, 0);
analogWrite(ARM_A_LPWM, 700);

// stop
analogWrite(ARM_A_RPWM, 0);
analogWrite(ARM_A_LPWM, 0);
```

Add 20–50 ms dead time before reversing direction. The current M1 firmware does
not implement arm control yet; this is the wiring/config target for the next
firmware revision.

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
| GND | `GND` | all sensor GND + 12 V supply GND (common) |

---

## Boot-strap check before first power-up

- [ ] GPIO15 (D8) pulled to GND through 10 kΩ if anything is connected there
- [ ] GPIO0 (D3) NOT held low (no FLASH button pressed)
- [ ] GPIO2 (D4) not forced low
- [ ] Echo line divided to ≤3.3 V
- [ ] Common ground between 12 V and 3.3 V sections
- [ ] 12 V feed fused (2 A)
