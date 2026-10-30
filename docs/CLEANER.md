# Tank cleaning automation — design brief (v0, from the CAD)

**Status: design stage — nothing here is built.** Source: the Fusion 360
assembly `tank cleaning automation` (screenshots, 30 Oct 2026). Hardware
context comes from **this repo** (M1 tank unit, H1 home unit, 12 V solar tree),
not from the CAD tool's parts panel. This document records the mechanism, where
it collides with the product as documented today, the control requirements, and
the contract the dashboard would consume — so firmware and UI don't grow around
guesses.

---

## 1. What the model shows (mechanical)

- A **vertical pipe** through the tank lid — the arm's spine.
- A **main arm** in 2020 aluminium extrusion: **pipe → outer motor at r = 20 cm**.
- **Two planetary-motor units** beneath the arm: one near the pipe driving a
  direct brush (covers roughly r = 0–12 cm), one at **r = 20 cm** driving the
  **secondary arm** (`arm1` / `arm2`), which extends to **r = 40 cm** fully
  extended, with its brush at the end.
- Assembly tree: `Rigid 4` (brush mounts), `Revolute 3` (the secondary arm's
  hinge at the outer motor) and `Revolute 1` (the main arm's rotation about the
  pipe), body `mainarm`.

**Motion implied:** the whole arm rotates about the pipe axis; the outer motor
extends/retracts the secondary arm to follow the annulus; both brush heads spin
on their own axes.

| axis | joint | job |
|---|---|---|
| sweep | Revolute 1 | rotate the arm across the floor |
| reach | Revolute 3 | extend the secondary arm 20 → 40 cm |
| brush 1 / brush 2 | Rigid 4 | scrub, independently |

Open: which revolute is the sweep vs the fold, and whether the pipe is also a
linear axis (the CAD shows it fixed).

---

## 2. Given constraints (30 Oct 2026) and what they cost

**Rule the design must satisfy: the actuator never sinks.** Motor deck above the
tank's maximum water line (i.e. above the lid), driving the brushes down through
the pipe on a shaft. Only the brush heads (and the pump) are submerged — no
motors, no cables, no slip ring in the water; the rotary seal lives at the lid.

| given | value | derived |
|---|---|---|
| tank radius | 50 cm | floor area 7,854 cm² |
| main arm: pipe → outer motor | 20 cm | inner brush covers ≈ r = 0–12 cm |
| secondary arm: outer motor → brush | 20 cm (fully extended) | outer brush axis at **r = 40 cm** |
| brush heads | ⌀ 10 cm assumed (radius 5) | outer edge reaches **r = 45 cm** |
| **unreachable ring** | **r = 45–50 cm (5 cm)** | **1,492 cm² = 19 % of the floor** |
| pump suction cup | ⌀ 5 cm | 19.6 cm² footprint (0.25 % of the floor) |
| 2020 extrusion stock | 500 mm | **fully used**: 200 + 200 mm + joints — no idle beam |

Measured with `tools/swept_area.py` (section 7): **78.9 % of the floor covered**,
the missing 21 % being the 5 cm ring plus the pipe footprint at the centre. With
a point-sized brush the ring would be 10 cm / 36 % — the ⌀10 head is doing real
work here.

**The ring is the real constraint.** It is exactly the wall base, where sludge
settles hardest. Options, cheapest first:

| option | change | result |
|---|---|---|
| **A — accept it** | add a fixed wall-base brush/skirt at the tip | ring stays 19 %, but the fillet gets scrubbed |
| **B — longer second stage** | secondary arm 20 → 25 cm (1 m extrusion cut down) | brush edge reaches 50 cm → ring closed |
| **C — third stage** | telescoping stage beyond r = 40 | ring closed, most mass and torque at the tip |

Brush diameter alone cannot close it: touching the wall from r = 40 needs a
⌀20 cm brush — heavy, high torque, and it scrubs at a different surface speed.

**Off-centre pivot is not a fix.** A 40 cm reach pivoted *d* from the centre
sweeps a disc of radius 40 around the pivot; at d = 40 it trades the 10 cm inner
ring for a far-side crescent reaching 90 cm — worse, and it includes the far
wall. Only a centred pivot with ≥ 50 cm effective reach covers the floor.

**The pump cup is the collision constraint.** Where the pump sits decides the
motion plan:

- **inside r < 40** → the arm sweeps through the pump: needs a keep-out sector
  (lift/skip) or vertical clearance between the brush plane and the pump top;
- **in the 10 cm ring** → out of the sweep, but its intake sits permanently in
  the uncleaned sludge zone — the worst place for it;
- **docked at the pipe** → cleanest hydraulically, but it blocks the arm's inner
  end.

> **Open:** the team's "main constraint" sentence was left unfinished — the
> pump's mounting radius and height are still needed before the motion plan can
> be fixed.

---

## 3. Where this collides with the product as it stands
The repo's current position, written into `firmware/README.md`, is explicit:

> **No actuator in the tank:** TankGuard monitors water quality and controls the
> pump only. Draining/flushing the tank is manual.

A motorised arm **inside** the tank is the opposite of that. This is not a
detail — it changes the product's safety case and its documentation:

| area | today (repo) | with the cleaner |
|---|---|---|
| actuation | pump only, outside the tank, via isolated relay + contactor (H1) | motors and cables inside potable water |
| power | 12 V solar/battery sized for sensors + Wi-Fi | motor class load — a different budget entirely |
| safety | fuse 12 V, link-loss failsafe, no wet electronics | submersion, cable glands, slip ring, e-stop, stall detection |
| spec / patent | "monitors + controls the pump", flush removed in `022e3b2` | a third mechanism to describe, claim and cost |

**Decide this before building:** either the cleaner is a separate product
(recommended — own enclosure, own power, own safety case, M1 untouched), or the
product statement in `README.md` / `firmware/README.md` / the spec and patent
drafts must be rewritten. Both are legitimate; drifting between them is not.

---

## 4. Control requirements (derived from the repo's stack)

The repo already has the pattern this fits: an ESP8266-class controller on the
tank, a second unit near the pump, Wi-Fi as the primary link and nRF24 as the
long-range option. The cleaner needs the same shape plus motor control:

```
M1 tank unit (ESP8266, solar)            cleaner controller (ESP-class, own power)
  sensors → GET /data  ──── Wi-Fi ────►  cycle orchestration + interlocks
  no motors, unchanged                    ├─ motor driver → sweep axis
                                          ├─ motor driver → brush 1 / brush 2
                                          └─ home switch, lid switch, e-stop, alarm
```

**What the repo does not have yet — and the cleaner needs:**

1. **Motor drivers.** Nothing in the repo drives a motor directly; H1 switches a
   pump through an opto-relay + contactor, which is on/off only. The sweep axis
   and brushes need real drivers (stepper or brushed DC — see open questions),
   with current sensing so a jam can be detected rather than inferred.
2. **Power budget.** The 12 V tree (`CN3791 → 18650 → LM2596`) is sized for
   sensors, the ESP8266 and occasional relay switching. Motors are a different
   class: the cleaner should get its own supply (mains at the pump point is the
   natural place) and not share the monitor's battery.
3. **Position feedback.** No limit switch or encoder exists in the design or the
   repo. A hall/optical home flag on the pipe collar is the cheapest reliable
   datum; without it the sweep angle is a guess.
4. **Submersion.** The CAD hangs the motors inside the tank. Two honest options:
   IP68 motors with sealed cables, or motors **above the lid** driving the
   brushes through the pipe with a shaft — no motors in water, no glands to
   trust. The second is strongly preferred for potable water.

### Safety rules this mechanism needs (in addition to the repo's existing ones)

1. **No continuous rotation — oscillate.** The water hose and the brush wires
   run down the pipe, so the arm must reverse rather than wind up. It sweeps
   between **−L and +L** and returns to neutral every cycle. Coverage of the full
   circle then requires **2·L·N ≥ 360°** (N arms): one arm needs **±180°**, two
   arms need only ±90° (half the twist), three ±60°. Anything less leaves a
   dead sector spanning every radius — measured in section 7.
2. **Stall detection.** Cut brush power within ~200 ms of a jam — a stalled
   motor in water is a cooked motor and a fire risk.
3. **Water interlock.** Never spin the brushes dry: require `level ≥ 15 %`
   (configurable) and a closed lid before a cycle can start.
4. **Hard e-stop.** A physical switch that cuts the motor rail — not a software
   command.
5. **Cycle caps.** Hard time cap (e.g. 10 min) and per-brush current cap,
   enforced in firmware independent of any UI.

---

## 5. Proposed control contract (v1 — for the dashboard)

Only what the cleaner can actually measure. The dashboard reflects interlocks;
it never bypasses them.

```jsonc
// GET /clean
{
  "phase": "idle | homing | sweeping | retracting | fault",
  "progress": 0,            // 0-100 across the cycle
  "angleDeg": 0,            // current sweep angle, -180..180
  "brushes": [ { "amps": 0.0 }, { "amps": 0.0 } ],
  "levelPct": 0,            // from M1, for the interlock display
  "lidClosed": true,
  "startedAt": null,
  "fault": null             // "stall" | "dry" | "estop" | "timeout" | "home"
}

// POST /clean  {"mode": "start" | "stop" | "home"}
```

Interlocks live on the device: `start` returns `409` with a reason when
`levelPct < 15`, `lidClosed == false`, or a fault is latched.

---

## 6. Firmware state machine (sketch)

```
IDLE ──start──► HOME ──► SWEEP ⇄ (n passes) ──► RETRACT ──► IDLE
                  │        │ brush on, watch amps
                  │        └─ pass: set angle → dwell → next
                  └─ fail ─► FAULT (motors off, alarm, latch until reset)
```

Per pass: `angle = -sweep + 2·sweep·k/(n-1)`; n = ceil(2·sweep / step); step
default 30°; dwell 6 s; brush current over cap for 300 ms → `FAULT:stall`.

---

## 7. Swept-area model (`tools/swept_area.py`)

A small matplotlib model that stamps the actual brush discs as the arm moves, so
coverage is measured rather than assumed. It models the **no-continuous-rotation
constraint**: the arm oscillates between −L and +L (the hose and wires unwind on
the way back), and the tool reports the resulting twist and any dead sector.

```
python tools/swept_area.py                          # 1 arm, +/-180, concentric
python tools/swept_area.py --arms 2 --limit 90      # two arms, half the twist
python tools/swept_area.py --limit 170              # shows the dead sector
python tools/swept_area.py --mode spiral --osc 3
python tools/swept_area.py --brush 4                # dia-8 heads: shows the gap
python tools/swept_area.py --pump 25                # draw the dia-5 cup at r = 25
python tools/swept_area.py --save sweep.gif --still sweep-final.png
```

### Coverage needs 2·L·N ≥ 360°

| arms | sweep | hose twist each way | coverage |
|---|---|---|---|
| 1 | ±180° | ±180° | **78.9 %** — full circle |
| 2 | ±90° | ±90° | **78.9 %** — full circle |
| 3 | ±60° | ±60° | full circle |
| 1 | ±170° | ±170° | 77.7 % — **20° dead sector** |

A single arm at ±180° is the only one-arm option that reaches every angle. Any
less leaves a wedge that spans all radii, so no number of radial passes fixes
it — measured loss 1.2 points (the brush radius softens the wedge edges). If
±180° of hose twist is too much, **add arms, not sweep**: two opposite arms halve
the twist and keep full coverage.

### Pattern under oscillation

| pattern | coverage | note |
|---|---|---|
| concentric, passes at r = 20 / 28 / 36 / 40 | **78.9 %** | one oscillation per radius — the recommended cycle |
| spiral, 3 oscillations + dwell at each end | 77.0 % | works, but no better than concentric |
| spiral, 2 oscillations | 73.1 % | pitch 10 cm = band width → gaps |
| either, with dia-8 brushes | 72.3 % | **2 cm gap** between the two brush tracks (r 14–16) |

Three rules fall out of the model:

1. **Brush radius ≥ 5 cm (dia 10)** — the inner track covers r 5–15 and the outer
   starts at 15; a smaller head leaves an unscrubbed ring between them
   (`10 − 2·brush_radius` cm wide).
2. **Overlap the tracks.** Passes spaced at exactly the band width (2 × brush
   radius) touch tangentially and leave scalloped rings. Spacing 1.6 × brush
   radius removes them.
3. **Dwell at both extreme radii.** A monotonic spiral visits each extreme at a
   single angle, costing ~6 points (measured: 64.3 % before the dwells, 78.9 %
   after).

Renders: [`sweep-1arm.png`](sweep-1arm.png) · [`sweep-2arms.png`](sweep-2arms.png) ·
[`sweep-dead-sector.png`](sweep-dead-sector.png)

---

## 8. Open questions (blocking firmware)

1. **Motors** — what are the planetary units, and what drives the sweep axis:
   brushed DC with gearbox, or a stepper? (Voltage/current/gearing decide the
   driver, and the driver decides the board.)
2. **Controller** — ESP32-class (more PWM/timers, same toolchain as the repo) or
   keep ESP8266? Either way the cleaner gets its own unit.
3. **Motors in water** — IP68 inside the tank, or above the lid driving through
   the pipe?
4. **Sweep** — continuous rotation (slip ring) or ±170°?
5. **Power** — mains at the pump point, or the monitor's 12 V rail?
