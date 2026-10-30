# TankGuard

IoT water tank quality monitoring and pump-control system.

## Problem
Water storage tanks in homes and institutions accumulate sludge and degrade silently — by the time water smells or looks bad, it's already unsafe.

## Solution
A self-powered, in-tank sensor unit (turbidity, TDS, pH, temperature, level) that computes a composite quality score (TankScore) and a home-side unit that displays it, controls the pump safely, and alerts before the water becomes unsafe.

## Features
- Multi-parameter continuous monitoring (turbidity, TDS, pH, temp, level)
- Composite TankScore with trend-predictive analysis
- Home-side TFT dashboard + manual pump override
- Mains-safe pump automation via opto-relay + contactor
- Optional long-range nRF24L01+ link (Wi-Fi not required)
- Solar-powered, cloud-free (no subscription, no internet required)

## Hardware
- ESP8266 NodeMCU (tank + home units)
- ADS1115 16-bit ADC (all analog sensors)
- SEN0189 turbidity sensor
- SEN0244 TDS sensor
- pH sensor kit (SEN0161-V2)
- DS18B20 temperature sensor
- JSN-SR04T ultrasonic level sensor
- 1.8" ST7735 TFT, opto-relay + contactor (home unit)
- 5W solar panel + Li-ion battery

## Build Guides
| File | Description |
|------|-------------|
| [`webapp/`](webapp/) | **Web dashboard** (React + Vite) — TankScore, five parameter readings, session-log trends; talks to the tank unit's `/data` endpoint or runs a labelled demo |
| [`firmware/README.md`](firmware/README.md) | Firmware overview, power tree, safety, bring-up order (ESP8266) |
| [`firmware/PINMAP.md`](firmware/PINMAP.md) | Master ESP8266 pin map + ADS1115 channel map |
| [`firmware/HARDWARE_M1_Monitor.md`](firmware/HARDWARE_M1_Monitor.md) | M1 monitor build — BOM, wiring, dividers, assembly, tests |
| [`firmware/HARDWARE_H1_Home.md`](firmware/HARDWARE_H1_Home.md) | H1 home-side build — receives tank data, drives pump via isolated relay + contactor (mains-safe) |

## Web dashboard

The browser twin of the H1 display lives in [`webapp/`](webapp/): TankScore with
the same state bands as the TFT, the five parameters as live readings with
traces, and an honest data-source chip (device · demo · link state). It probes
the tank unit automatically (same-origin, `?api=<ip>`, or the AP gateway
`192.168.4.1`) and keeps a browser-side session log because the device stores
no history. See [`webapp/README.md`](webapp/README.md).


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
