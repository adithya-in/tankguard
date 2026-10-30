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

### Drivetrain — TJX28ZRM (RS395 12 V + 21.5:1 planetary)

Datasheet (`tyhemotors.com/tjx28zrm`), 12 V, 21.5:1, two stages, 72 % efficiency:

| spec | value |
|---|---|
| no-load / rated speed (output) | **348.8 / 279 rpm** |
| rated torque | **11.3 N·cm** |
| stall torque (output) | **~34 N·cm** |
| rated / stall current | 0.62 A / 4.5 A at 12 V |

279 rpm loaded is **1,674 °/s**; the sweep needs 45 °/s, i.e. 2.7 % duty — below
where a loaded DC motor turns. The controller therefore pulses: **250 ms at full
duty, then 200 ms of coast**, ~8° per burst (calibrate).

**Torque verdict: marginal.** The arm sweeps horizontally, so gravity is a
bearing load, not drive torque. The joint fights:

| load | estimate |
|---|---|
| brush friction (0.2 kg pressure, μ 0.3, r 0.40 m) | ~24 N·cm |
| water drag | ~5–10 N·cm |
| inertia per burst | ~10–20 N·cm |
| **total** | **~30 N·cm** |

Against **11.3 rated / ~34 stall** that is between the two limits: the motor will
move the arm, but loaded and warm. Consequences:

- **brush head ≤ 0.2 kg** — at 0.5 kg the friction alone (~60 N·cm) exceeds stall;
- expect **15–25 °/s loaded**, so the cycle is **90–130 s**, not the planner's 44 s;
- bursts keep it out of continuous stall (4.5 A would cook a 28 mm motor).

**Order the encoder option.** The same motor is sold with a 12 PPR magnetic
encoder (A&B, 5–24 V): 12 × 4 × 21.5 = **1,032 counts/rev ≈ 0.35 °/count** — enough
to close the position loop and execute the planner's arcs instead of
dead-reckoning them.

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

## 5. Control contract (v1 — implemented by `firmware/c1_cleaner`)

Only what the cleaner can actually measure — and it can measure very little: there
are **no encoders**, so joint angles are dead-reckoned from calibrated speed and
flagged as estimates. The dashboard reflects interlocks; it never bypasses them.

```jsonc
// GET /clean
{
  "openLoop": true,          // angles are estimates, not measurements
  "phase": "boot|homing|parked|running|parking|fault",
  "ring": 2,                 // current ring (1..3)
  "arc": 3,                  // current arc (0..5)
  "arcCount": 6,
  "progress": 50.0,          // arcs completed, %
  "t1": 23.50,               // shoulder estimate, deg (null after a fault)
  "t2": -156.90,             // elbow estimate, deg
  "brush": 200,              // PWM duty, 0 = off
  "level": 63.0,             // from M1 /data
  "levelAge": 4,             // seconds since the last successful read
  "lid": 1,
  "estop": 0,
  "fault": null,             // "home" | "estop" | "lid" | "dry" | "stall"
  "cycleS": 42,
  "uptime": 812
}

// GET /clean?mode=start|stop|home|reset
```

`start` returns `409` with a reason when the e-stop is open, the lid is open, the
level is stale or below 15 %, or a fault is latched.

**Accuracy budget.** With timed moves the position error grows with load, supply
sag and wear; the firmware bounds it by re-homing at every ring. Expect a few
degrees per pass, not the 0.3 cm the planner talks about — the 16 cm brush
absorbs that, which is why the overlap margin is not the thing to tune here.
Adding an AS5600 magnetic encoder (~₹300) per joint would turn this into the
closed-loop controller the planner was written for; the firmware keeps the joint
interface small so that swap is contained.

---

## 6. Firmware state machine (implemented)

```
BOOT ──► HOMING ──► PARKED ──start──► RUNNING ──► PARKING ──► PARKED
           │                            │
           │                            ├─ ring 1: arcs → re-home
           │                            ├─ ring 2: arcs → re-home
           │                            └─ ring 3: arcs
           └─ fail ─► FAULT ◄───────────┘ (e-stop, lid, dry, stall)
```

Per arc: `elbow → t2`, `shoulder → t1a`, brush on, `shoulder → t1b`, brush off.
Moves are timed (no feedback): `duty` fixed, `duration = angle / calibrated_dps`.
Stop is honoured between moves, never mid-move — a move cut short invalidates the
angle estimate, so the next action is always a re-home.

**Re-homing is the accuracy mechanism**, not an overhead: three homes per cycle
bound the drift to a single pass. Any change to `SH_DPS` / `EL_DPS` changes the
cycle time proportionally, so calibrate in water with the brush loaded.

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

### Coverage planner — minimal passes, no wasted floor

The brush is a disc of radius *b*, so one full circular pass at radius *r* scrubs
the annulus **[r − b, r + b] exactly**. Tiling the reachable disc with
concentric passes spaced **2b − overlap** covers everything with only the
overlap you ask for — the minimum number of passes, and no other duplication.

**Final configuration: b = 8 cm, 0.3 cm band overlap, single tip brush, both
joints ±180°, cycle starts and ends parked.**

| ring | band scrubbed | note |
|---|---|---|
| r = 8.0 cm | 0 – 16 cm | tip folded (elbow ≈ ±157°) |
| r = 23.7 cm | 15.7 – 31.7 cm | elbow ≈ ±106° |
| r = 39.4 cm | 31.4 – 47.4 cm | nearly extended (elbow ≈ ±20°) |

| metric | value |
|---|---|
| coverage | **90.0 %** of the floor |
| duplicate area | **1.13 %** — exactly the 0.3 cm overlap, nothing else |
| arcs | 6 — each ring splits once at its elbow branch flip |
| reposition moves | 7 — park → ring 1, five ring/branch transitions, ring 3 → park |
| joint travel | **1,991°** — 1,074° scrubbing + **917° repositioning** |
| cycle time | **44 s** at 45 °/s joint speed |

**Park pose.** Every cycle starts and ends in the same rest form: both links
folded back on themselves, θ1 = 0°, θ2 = ±180°, tip at the tank centre. That is
the most compact shape the arm can take (one 20 cm line), loads both joints the
least, and never rests against the wall. The tool draws it as a ghost so the
resting position is part of the picture, and the planner prices the two park legs
into the ordering — it solves for a *cycle*, not an open path.

**Why 0.3 cm costs 2.4 points of floor.** The rings must fit inside the 40 cm
reach, so a tighter ladder trades wall band for overlap: at 0.3 cm the outermost
ring sits at 39.4 and the wall ring grows from 2.0 to 2.6 cm. Forcing a fourth
ring to hold the wall at 40 would stack 5.3 cm of overlap on every boundary and
duplicate **20 %** of the floor. Three rings at 15.7 cm is the right call.

**Where the repositioning goes.** 917° is 46 % of the cycle, and almost all of it
is three elbow flips (one per ring, ≈300° each). A ring below r = 40 cannot be
swept by one elbow branch inside a ±180° shoulder limit — the branch must flip at
some angle. Only a wider shoulder limit removes that, not a better algorithm.

The planner splits rings into arcs where a limit or branch flip forces a
reconfiguration, orders those arcs **exactly** (Held-Karp over arcs × directions,
priced as a cycle back to park), and interpolates every move so the animation
shows the real motion. The whole plan is drawn before it runs — grey for
scrubbing passes, dashed amber for repositioning.

**One brush.** A second brush at the elbow would scrub 12–28 cm, which the r = 8
and r = 23.7 passes already cover — 25.6 % of the floor twice, for nothing.

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
