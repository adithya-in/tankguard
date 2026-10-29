# M2 — Sludge Flush Module (Hardware Build)

The M2 module electrically drives the **1″ normally-closed (NC) brass solenoid valve**
mounted at the tank floor. It is an add-on to the M1 controller: it shares the same
ESP8266, 12 V rail and ground. See [`PINMAP.md`](PINMAP.md) for the pin map.

> **Normally-closed** is a safety requirement: with no power (or a dead battery, or a
> crashed ESP8266) the valve stays **closed** and the tank cannot drain itself.

---

## 1. Bill of materials (ESP8266 version)

| # | Part | Spec | Qty | Approx. ₹ |
|---|---|---|---|---|
| 1 | Solenoid valve | 1″ brass, **NC**, 12 V DC, EPDM seal | 1 | 1,000–2,500 |
| 2 | MOSFET | IRLZ44N (logic-level) or IRL540N | 1 | 25 |
| 3 | Gate resistor | 220 Ω | 1 | 2 |
| 4 | Gate pulldown | 10 kΩ | 1 | 2 |
| 5 | Flyback diode | 1N5819 (Schottky) or 1N4007 | 1 | 5 |
| 6 | Bulk capacitor | 100 µF / 25 V (across 12 V near valve) | 1 | 8 |
| 7 | Fuse | 2 A blade fuse + holder | 1 | 20 |
| 8 | Manual bypass | 1″ ball valve (for servicing) | 1 | 250–500 |
| 9 | Cable | 2-core, 0.75 mm², UV-rated | ~5 m | 100 |
| 10 | Connectors | screw terminal / DC jack | set | 40 |

**M2 parts subtotal: ~₹1,500–3,200** (valve dominates the cost; street price is often
₹1,000–1,300 for a 1″ brass NC 12 V valve).

> **Why 1″ and not ½″?** Sludge and debris clog small orifices. The 1″ valve passes
> solids and flushes the bottom layer quickly (~5–15 % of tank volume in a short burst).

---

## 2. Driver circuit (low-side MOSFET switch)

The ESP8266 GPIO can supply only ~12 mA — not enough to drive a solenoid (≈0.5–1.5 A).
A logic-level N-channel MOSFET switches the valve's ground path:

```
                       +12 V (fused, 2 A)
                          │
                          ├──────────────┬──────────────┐
                          │              │              │
                       [100 µF]       Valve +        (diode cathode)
                          │              │              │
                         GND          Valve − ──────┬───┘
                                            (drain) │
                                                    │
                                     ┌──────────────┴─────────┐
   GPIO15 (D8) ──[220 Ω]──┬──────────┤  Gate                  │
                          │          │   IRLZ44N              │
                       [10 kΩ]       │  Drain ── to valve −   │
                          │          │  Source ── GND         │
                         GND         └────────────────────────┘

   Flyback diode: cathode → +12 V, anode → drain (valve −)
```

### Key points
- **Source → GND**, **Drain → valve (−)**, **valve (+) → +12 V**.
- **Gate → GPIO15 (D8)** through **220 Ω**, with **10 kΩ gate→GND** pulldown.
- **Flyback diode across the coil** is mandatory — without it the collapsing coil
  produces a voltage spike that kills the MOSFET.
- **100 µF** across the 12 V rail near the valve smooths the inrush spike.
- **GPIO15 must be LOW at boot** — the 10 kΩ pulldown guarantees this and keeps the
  valve **OFF (closed)** during boot. This is exactly the boot-strap behaviour GPIO15
  requires, so it is safe to use for the gate.

---

## 3. Will 3.3 V drive IRLZ44N reliably?

IRLZ44N is a logic-level MOSFET: it begins to conduct around Vgs ≈ 1–2 V, but its
**lowest specified Rds(on) is at Vgs = 5 V**. At **3.3 V** it still switches the
solenoid's ~1 A comfortably, but it runs a little warmer. Two safe options:

- **Option A (simplest):** IRLZ44N driven directly from GPIO15 at 3.3 V — acceptable for a valve that is ON only in short bursts.
- **Option B (cooler):** add a small gate driver (e.g. 74HCT1G125 buffer or a 2N7000 + 10 kΩ pull-up to 5 V) so the gate sees ~5 V.
- **Option C (no MOSFET):** use a **5 V relay module with an opto-isolator**; drive the relay input from GPIO15. Clicks audibly but is simple and isolated.

> Do **not** use a bare 5 V relay coil directly on a GPIO — it will damage the ESP8266.

---

## 4. Wiring steps

1. **Fuse the 12 V feed** to the valve (2 A) — do this first.
2. Wire **valve (+) → +12 V (after fuse)**.
3. Wire **valve (−) → MOSFET drain**.
4. Wire **MOSFET source → GND**.
5. Wire **MOSFET gate → 220 Ω → NodeMCU D8 (GPIO15)**.
6. Add **10 kΩ from gate → GND** (pulldown).
7. Solder the **flyback diode** across the valve coil: **cathode (band) → +12 V**, **anode → drain**.
8. Add **100 µF** across +12 V and GND near the valve.
9. Connect the **12 V supply GND** to the **NodeMCU GND** (common ground).
10. Install the **manual bypass ball valve** in parallel so the line can be opened by hand during service.
11. Run the **2-core cable** to the valve through an IP68 gland; keep polarity marked.

---

## 5. Connection summary

| From | To |
|---|---|
| 12 V+ (fused) | Valve +, 100 µF +, diode cathode |
| Valve − | MOSFET drain, diode anode |
| MOSFET source | GND (common) |
| NodeMCU D8 (GPIO15) | 220 Ω → MOSFET gate |
| MOSFET gate | 10 kΩ → GND |
| 12 V− | GND (common with ESP8266) |
| Manual bypass valve | parallel to solenoid valve |

---

## 6. Installation at the tank

1. Mount the solenoid valve at the **lowest point** of the tank floor (sludge collects there).
2. Fit the **manual bypass** in parallel and leave it closed in normal operation.
3. Slope the outlet pipe downward so sludge does not sit in the line.
4. Terminate the outlet to a drain / soak pit — never dump sludge onto walkways.
5. Keep the valve body accessible for cleaning; brass + EPDM is preferred for potable water.
6. Seal all cable entries; the valve area is wet by definition.

---

## 7. Bring-up tests

| Test | How | Pass criteria |
|---|---|---|
| Valve closed at boot | Power up, listen/feel | No click, no flow (NC valve) |
| Valve opens | Drive GPIO15 HIGH | Audible click, water flows |
| Valve closes | Drive GPIO15 LOW | Click, flow stops |
| Flyback present | Inspect | Diode across coil, correct polarity |
| Current | Inline ammeter | Within valve rating (~0.5–1.5 A) |
| Fuse | Short-test on bench only | Fuse blows before wiring overheats |
| Leak | Pressurise line | No drips at fittings |

---

## 8. Safety notes

- The valve is **12 V DC low-voltage**, but the **inrush current** and **inductive spike** are the real hazards — never omit the flyback diode.
- **Never** drive the valve from the 3.3 V or 5 V rail.
- Keep the **manual bypass** so the tank can be serviced if electronics fail.
- If the tank supplies **drinking water**, use a **food-grade** valve and flush the line after installation.
- Add a **2 A fuse** and, ideally, a **TVS diode** (e.g. SMBJ15A) across the 12 V rail for extra spike protection.

> Full firmware is separate; this document covers only the physical hardware.
