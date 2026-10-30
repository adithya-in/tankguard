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

- A **vertical pipe** through the tank lid — the arm's spine and the shoulder axis.
- **Two rigid 20 cm links**, no telescoping:
  - **link 1 (shoulder)** pivots on the pipe, θ1;
  - **link 2 (elbow)** pivots on the motor at the end of link 1, θ2, and is driven
    independently.
- A **single brush at the tip** (r = 0–40 cm depending on the elbow angle). The
  elbow is a joint — a motor, not a scrubber.
- Assembly tree: `Rigid 4` (brush mount), `Revolute 3` (the elbow) and
  `Revolute 1` (the shoulder), body `mainarm`.

**Motion implied:** a planar 2R arm with one scrubber at the tip. The tip reaches
any point with r ≤ 40 cm; both joints oscillate inside their own limits (the hose
and wires must not wind up), so the *reachable* floor depends on those limits —
that is the dead-area question, and `tools/swept_area.html` solves it numerically.

| axis | joint | job |
|---|---|---|
| shoulder | Revolute 1 | swing the whole arm; ±L1 |
| elbow | Revolute 3 | fold the second link; ±L2 |
| brush | Rigid 4 | the only scrubber, at the tip |

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
| link 1 (shoulder) | 20 cm fixed | elbow joint at r = 20 cm |
| link 2 (elbow) | 20 cm fixed | tip at r = 0–40 cm depending on θ2 |
| brush heads | ⌀ 16 cm (radius 8, the build maximum) | outer edge reaches **r = 48 cm** |
| **unreachable ring** | **r = 48–50 cm (2 cm)** | **616 cm² = 7.8 % of the floor** |
| pump suction cup | ⌀ 5 cm | 19.6 cm² footprint (0.25 % of the floor) |

Measured with `tools/swept_area.html` (section 7): with both joints free
(±180°) **91.0 % of the floor is reachable** — 7.8 % is the wall ring and 1.2 %
is the joint-limited centre. The ring, not the joints, is the remaining dead
area, and with ⌀16 brushes it is down to 2 cm.

**The ring is the real constraint.** It is exactly the wall base, where sludge
settles hardest. Options, cheapest first:

| option | change | result |
|---|---|---|
| **A — accept it** | add a fixed wall-base brush/skirt at the tip | ring stays 7.8 %, but the fillet gets scrubbed |
| **B — longer second link** | 20 → 22 cm | brush edge reaches 50 cm → ring closed |
| **C — bigger head** | brush radius 10 cm (⌀20) | ring closed, heavy and high torque |

Brush diameter alone cannot close it without becoming the whole design: a ⌀20 cm
head is a floor polisher, not a tank brush.

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

## 7. Workspace explorer (`tools/swept_area.html`)

A self-contained page (no build, no dependencies) that solves the real question:
**given joint limits, which parts of the floor can this arm reach at all?** It
computes the reachable workspace analytically — inverse kinematics on a 0.25 cm
grid, then dilates by the brush radius — so the dead area is exact, not the
result of one guessed path.

Open it directly: `start tools/swept_area.html` (or drag it into a browser).

| control | what it changes |
|---|---|
| Shoulder ±L1, Elbow ±L2 | joint limits = hose/wire twist |
| Brush radius | head size; also sets the outer edge (40 + b) |
| Brush at the elbow | the r = 20 brush on/off |
| θ1 / θ2 sliders | move the arm by hand |
| Trace duration (2–40 s) | how slowly the path runs — adjustable mid-trace |
| Trace a path | walks the reachable area the way a cycle would (paints what it actually scrubs) |

### Measured trade-off (⌀16 brushes, tank r 50, links 20 + 20)

| shoulder ± | coverage | | elbow ± | coverage |
|---|---|---|---|---|
| 180° | **91.0 %** | | 180° | **91.0 %** |
| 150° | 90.1 % | | 150° | 90.7 % |
| 120° | 84.4 % | | 120° | 85.1 % |
| 90° | 73.6 % | | 90° | 74.2 % |
| 60° | 59.9 % | | 60° | 62.1 % |

Three things this settles:

1. **The ring, not the joints, is the main dead area.** Even with both joints
   free, 7.8 % (the 2 cm wall ring) is unreachable. Loosening joints cannot fix
   it; only reach can.
2. **Shoulder ±150° is nearly free** — 0.9 points. If ±180° of hose twist is
   unacceptable, ±150° buys almost the same coverage; below ±120° it collapses
   (84.4 % → 73.6 % at ±90°).
3. **The elbow tolerates ±150° well** (90.7 %) but falls off faster below that:
   ±120° costs 6 points, ±90° costs 17.

The "Trace a path" run reaches 80.9 % against the 80.4 % workspace — i.e. a
concentric cycle over the reachable set actually scrubs what the analysis says
it can, so the model is consistent.

Screenshot: [`workspace-2r.png`](workspace-2r.png)

### Coverage planner — minimal passes, zero duplication

The brush is a disc of radius *b*, so one full circular pass at radius *r*
scrubs the annulus **[r − b, r + b] exactly**. Tiling the reachable disc with
concentric passes spaced **2b** therefore covers everything with **no overlap**:
it is the minimum number of passes, and any tighter spacing re-cleans floor.

With **b = 8 cm** the whole floor is three rings:

| ring | band scrubbed | note |
|---|---|---|
| r = 8 cm | 0 – 16 cm | tip folded (elbow ≈ ±157°) |
| r = 24 cm | 16 – 32 cm | elbow ≈ ±106° |
| r = 40 cm | 32 – 48 cm | fully extended (elbow 0°) |

Planner output (both joints ±180°, elbow brush off):

| metric | value |
|---|---|
| coverage | **91.0 %** of the floor (the rest is the 2 cm ring + 1.2 % centre) |
| duplicate area | **0 %** |
| arcs | 5 (inner and middle rings split once by the elbow branch flip; outer ring 1) |
| joint travel | **1,704°** — 1,076° scrubbing + **628° repositioning** |
| cycle time | **38 s** at 45 °/s joint speed |

Two findings the planner makes obvious:

1. **The tip brush alone closes the tiling.** Rings at 8 / 24 / 40 scrub
   0–48 cm with no gaps and no overlap — a second brush at the elbow would
   scrub 12–28 cm again (25.6 % of the floor twice) for nothing. One brush is
   both simpler and faster.
2. **Overlap margin is expensive.** A 2 cm margin pushes the plan to four rings
   (8 / 19 / 29 / 40 cm), +6 % joint travel and **10.2 % duplicate area** — for
   no coverage gain. Keep the margin at 0 and rely on the brush's compliance.

The planner also splits each ring into arcs wherever a joint limit or an elbow
branch flip forces a reconfiguration, orders those arcs **exactly** (Held-Karp
over the arcs and their two directions — greedy was leaving ~200° on the table),
and interpolates the moves between arcs so the animation shows the real
movement instead of teleporting. Repositioning is 37 % of the cycle and is
dominated by one unavoidable elbow flip: the inner ring needs both branches
(±157°) to keep the shoulder inside ±180°.

The tool draws the whole plan before running it — grey for scrubbing passes,
dashed amber for repositioning moves — so the cycle can be read at a glance.

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
