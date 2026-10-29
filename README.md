# TankGuard

IoT water tank quality monitoring system with automated sediment-flush valve.

## Problem
Water storage tanks in homes and institutions accumulate sludge and degrade silently — by the time water smells or looks bad, it's already unsafe.

## Solution
A self-powered, in-tank sensor unit (turbidity, TDS, pH, temperature, level) that computes a composite quality score (TankScore) and automatically flushes the sediment layer at the tank bottom when contamination thresholds are crossed — without draining the tank.

## Features
- Multi-parameter continuous monitoring (turbidity, TDS, pH, temp, level)
- Composite TankScore with trend-predictive analysis
- Automated sludge-flush valve (selective bottom-layer flush, not full drain)
- Closed-loop flush verification (re-measure after flush, compute effectiveness)
- Solar-powered, cloud-free local dashboard (ESP32 + mDNS)
- No subscription, no internet required

## Hardware
- ESP32 DevKit
- ADS1115 ADC (for pH)
- SEN0189 turbidity sensor
- XKC-Y25-NPN TDS sensor
- DS18B20 temperature sensor
- JSN-SR04T ultrasonic level sensor
- 1" Brass NC solenoid valve (flush valve)
- 5W solar panel + Li-ion battery

## Build Guides
| File | Description |
|------|-------------|
| [`firmware/README.md`](firmware/README.md) | Home-side module overview, power tree, safety, bring-up order (ESP8266) |
| [`firmware/PINMAP.md`](firmware/PINMAP.md) | Master ESP8266 pin map + ADS1115 channel map |
| [`firmware/HARDWARE_M1_Monitor.md`](firmware/HARDWARE_M1_Monitor.md) | M1 monitor build — BOM, wiring, dividers, assembly, tests |
| [`firmware/HARDWARE_M2_Flush.md`](firmware/HARDWARE_M2_Flush.md) | M2 flush driver build — MOSFET, flyback, valve wiring, tests |

## Documents
| File | Description |
|------|-------------|
| `TankGuard_Specification.pdf` | **Technical specification** — title, abstract, components, features, uniqueness, cost, HW/SW specs, drawings |
| `TankGuard_Patentability_Disclosure.pdf` | Patent disclosure draft — prior art, claims, novelty |
| `TankGuard_3Page_Proposal.pdf` | 3-page project proposal with BOM and timeline |
| `TankGuard_Minimum_BOM.md` | Minimum-cost bill of materials (~₹6,500) |
| `TankGuard_Proposal.pdf` | Full detailed proposal |

## License
MIT
