# Tank cleaning automation — design brief

**Status: design stage — the firmware exists in `firmware/c1_cleaner`; the
hardware is not built.** Source: the Fusion 360 assembly `tank cleaning
automation` (screenshots, 30 Oct 2026). Hardware context comes from **this repo**
(M1 tank unit, H1 home unit, 12 V solar tree), not from the CAD tool's parts
panel. This document records the mechanism, what it can cover, where it collides
with the product as documented today, the drivetrain and control requirements,
and the contract the firmware exposes to the dashboard — so firmware and UI don't
grow around guesses.

---

## 1. What the model shows (mechanical)

- A **vertical pipe** through the tank lid — the arm's spine and the shoulder axis.
- **Two rigid 20 cm links**, fixed length, no telescoping:
  - **link 1 (shoulder)** pivots on the pipe, θ1;
  - **link 2 (elbow)** pivots on the motor at the end of link 1, θ2, and is driven
    independently.
- A **single brush at the tip**. The elbow is a joint — a motor, not a scrubber.
  Tip radius is r = 0–40 cm depending on the elbow angle; the brush adds its 8 cm
  radius to the outer edge.
- Assembly tree: `Rigid 4` (brush mount), `Revolute 3` (the elbow) and
  `Revolute 1` (the shoulder), body `mainarm`.

**Motion implied:** a planar 2R arm with one scrubber at the tip. The tip reaches
any point with r ≤ 40 cm; the brush edge reaches 48 cm. Both joints oscillate
inside their own limits (the hose and wires must not wind up), so the *reachable*
floor depends on those limits — that is the dead-area question, and
`tools/swept_area.html` solves it numerically.

| axis | joint | job |
|---|---|---|
| shoulder | Revolute 1 | swing the whole arm, θ1 |
| elbow | Revolute 3 | fold the second link, θ2, driven independently |
| brush | Rigid 4 | the only scrubber, at the tip |

The pipe is fixed in the CAD; there is no linear axis.

---

## 2. Given constraints and coverage

**Stated rule: the actuator never sinks.** Motor deck above the tank's maximum
water line (i.e. above the lid), driving the brushes down through the pipe on a
shaft. Only the brush head (and the pump) is submerged — no motors, no cables, no
slip ring in the water; the rotary seal lives at the lid. The CAD as drawn puts a
joint motor in the tank, so it does not meet this rule as drawn; that is part of
the conflict in section 3 and the placement question in section 10.

| given | value | derived |
|---|---|---|
| tank radius | 50 cm | floor area 7,854 cm² |
| link 1 (shoulder) | 20 cm fixed | elbow joint at r = 20 cm |
| link 2 (elbow) | 20 cm fixed | tip at r = 0–40 cm depending on θ2 |
| brush | radius 8 cm (⌀16), the build maximum | outer edge reaches **r = 48 cm (40 + 8)** |
| **unreachable wall ring** | **r = 48–50 cm (2.0 cm)** | **7.8 % of the floor** (zero-overlap ladder) |
| pump suction cup | ⌀5 cm | 19.6 cm² footprint (0.25 % of the floor) |

Measured with `tools/swept_area.html` (section 9): with both joints free (±180°)
**91.0 % of the floor is reachable** — 7.8 % is the wall ring and 1.2 % is the
joint-limited centre. The ring, not the joints, is the remaining dead area, and
with the ⌀16 brush it is down to 2.0 cm.

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

**Joint limits set the angular coverage.** The arm cannot rotate continuously
(the hose and wires run down the pipe), so it oscillates between −L and +L and
returns to neutral. Covering the full circle then needs **2·L·N ≥ 360°** for N
arms: one arm needs **±180°**, two arms need only ±90°, three ±60°. Anything less
leaves a dead sector spanning every radius; section 9 measures the cost.

**The pump cup is the collision constraint.** Where the pump sits decides the
motion plan:

- **inside r < 40** → the arm sweeps through the pump: needs a keep-out sector
  (lift/skip) or vertical clearance between the brush plane and the pump top;
- **in the 10 cm ring** → out of the sweep, but its intake sits permanently in
  the uncleaned sludge zone — the worst place for it;
- **docked at the pipe** → cleanest hydraulically, but it blocks the arm's inner
  end.

Which applies depends on the pump's mounting radius and height, still open
(section 10).

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

**This is unresolved.** Either the cleaner is a separate product (recommended —
own enclosure, own power, own safety case, M1 untouched), or the product
statement in `README.md` / `firmware/README.md` / the spec and patent drafts must
be rewritten. Both are legitimate; drifting between them is not.

---

## 4. Drivetrain — TJX28ZRM (RS395 12 V + 21.5:1 planetary)

Datasheet (`tyhemotors.com/tjx28zrm`), 12 V, 21.5:1, two stages:

| spec | value |
|---|---|
| no-load / rated speed (output) | **348.8 / 279 rpm** |
| rated torque | **11.3 N·cm** |
| stall torque (output) | **~34 N·cm** |
| rated / stall current | 0.62 A / 4.5 A at 12 V |
| efficiency | 72 % |
| backlash | ≤ 2° |

**There is no gearbox in the build, and no encoders are fitted.** The motor's
planetary output drives the joint directly; motion is open loop. 279 rpm loaded
is **1,674 °/s**; the sweep needs
45 °/s, i.e. 2.7 % duty — below where a loaded DC motor turns. The controller
therefore pulses: **250 ms at full duty, then 200 ms of coast**, **~10° per
burst** (calibrate).

**Torque is comfortable.** The head is a *ring* of sparse bristles
with an open centre for the pump — water flows through, so there is no seal and
no vacuum downforce. Friction at the head is ~1–2 N, i.e. **~4–8 N·cm at the
shoulder**, plus 4–8 of water drag and 10–20 of inertia:

| load | estimate |
|---|---|
| sparse ring bristles (1–2 N at r = 0.40 m) | ~4–8 N·cm |
| water drag at 25–35 °/s | ~4–8 N·cm |
| inertia per burst | ~10–20 N·cm |
| **total** | **~8–16 N·cm** |

Against **11.3 rated / ~34 stall** that leaves headroom: expect **25–35 °/s** and
a **55–80 s cycle**. The pump relay is sequenced with the brush (on while
scrubbing, off between passes) for power and sludge behaviour, not as a safety
gate.

**The encoder is optional.** The same motor is sold with a 12 PPR magnetic
encoder (A&B, 5–24 V): 12 × 4 × 21.5 = **1,032 counts/rev ≈ 0.35 °/count** —
enough to close the position loop and execute the planner's arcs instead of
dead-reckoning them. No encoder is fitted in this build.

---

## 5. Control requirements (derived from the repo's stack)

The repo already has the pattern this fits: an ESP8266 tank unit, a second unit
near the pump, Wi-Fi as the primary link and nRF24 as the long-range option. The
cleaner needs the same shape plus motor control, on its own ESP32 (the pin count
is why, not the toolchain):

```
M1 tank unit (ESP8266, solar)            cleaner controller (ESP32, own power)
  sensors → GET /data  ──── Wi-Fi ────►  cycle orchestration + interlocks
  no motors, unchanged                    ├─ H-bridge → shoulder (θ1)
                                          ├─ H-bridge → elbow (θ2)
                                          ├─ brush driver → one tip brush
                                          ├─ pump relay
                                          └─ home switches, lid, e-stop, alarm
```

**What the repo does not have yet — and the cleaner needs:**

1. **Motor drivers.** Nothing in the repo drives a motor directly; H1 switches a
   pump through an opto-relay + contactor, which is on/off only. The shoulder and
   elbow need PWM + direction H-bridges, plus a channel for the brush. Brush
   current sensing is optional in this build but is the only way to detect a jam
   rather than infer it.
2. **Power budget.** The 12 V tree (`CN3791 → 18650 → LM2596`) is sized for
   sensors, the ESP8266 and occasional relay switching. Motors are a different
   class: the cleaner should get its own supply (mains at the pump point is the
   natural place) and not share the monitor's battery.
3. **Position feedback.** There are no encoders. Two normally-closed home
   switches give the datum at boot and at every ring; between homes the joint
   angles are dead-reckoned from calibrated speed and flagged as estimates.
   Without the re-home the sweep angle is a guess.
4. **Submersion.** The CAD puts a joint motor in the tank. Two honest options:
   IP68 motors with sealed cables, or motors **above the lid** driving the brushes
   through the pipe with a shaft — no motors in water, no glands to trust. The
   second is strongly preferred for potable water.

---

## 6. Safety rules this mechanism needs

These are in addition to the repo's existing rules.

1. **No continuous rotation — oscillate.** The water hose and the brush wires run
   down the pipe, so the arm must reverse rather than wind up. It sweeps within
   its joint limits and returns to neutral every cycle; the coverage rule is in
   section 2.
2. **Stall detection.** Cut brush power within ~200 ms of a jam — a stalled motor
   in water is a cooked motor and a fire risk. Current sensing is optional in
   this build (`BRUSH_IS_ENABLED 0`).
3. **Water interlock.** Never spin the brushes dry: require `level ≥ 15 %`
   (configurable) and a closed lid (normally-closed switch) before a cycle can
   start. The level comes from the M1 tank unit.
4. **Hard e-stop.** A physical normally-closed switch that cuts the motor rail —
   not a software command.
5. **Cycle caps.** Hard time cap (e.g. 10 min) and per-brush current cap,
   enforced in firmware independent of any UI.

---

## 7. Control contract (v1 — implemented by `firmware/c1_cleaner`)

Only what the cleaner can actually measure — and it can measure very little:
there are **no encoders**, so joint angles are dead-reckoned and flagged as
estimates. Home switches re-zero both joints at boot and at each ring. The
dashboard reflects interlocks; it never bypasses them.

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
  "pump": 1,                 // relay state, sequenced with the brush
  "level": 63.0,             // from M1 /data
  "levelAge": 4,             // seconds since the last successful read
  "lid": 1,
  "estop": 0,
  "fault": null,             // "home" | "estop" | "lid" | "dry" | "stall"
  "cycleS": 42,              // elapsed this cycle, s
  "uptime": 812
}

// GET /clean?mode=start|stop|park|home|reset
```

`start` returns `409` with a reason when the unit is not parked, the e-stop is
open, the lid is open, the level is stale or below 15 %, or a fault is latched.

**Accuracy budget.** With timed moves the position error grows with load, supply
sag and wear; the firmware bounds it by re-homing at every ring. Expect a few
degrees per pass, not the 0.3 cm the planner talks about — the 16 cm brush
absorbs that, which is why the overlap margin is not the thing to tune here.
Fitting the optional encoder (section 4) would turn this into the closed-loop
controller the planner was written for; the firmware keeps the joint interface
small so that swap is contained.

---

## 8. Firmware state machine (implemented)

```
BOOT ──► HOMING ──► PARKED ──start──► RUNNING ──► PARKING ──► PARKED
           │                            │
           │                            ├─ ring 1: arcs → re-home
           │                            ├─ ring 2: arcs → re-home
           │                            └─ ring 3: arcs
           └─ fail ─► FAULT ◄───────────┘ (e-stop, lid, dry, stall)
```

Per arc: `elbow → t2`, `shoulder → t1a`, brush on, `shoulder → t1b`, brush off.
Moves are timed (no feedback): a fixed full-duty burst, a fixed coast, and
`bursts = angle / deg_per_burst`. Stop is honoured between bursts; a move cut
short invalidates the angle estimate, so the next action is always a re-home.

**Re-homing is the accuracy mechanism**, not an overhead: three homes per cycle
bound the drift to a single pass. Any change to `SH_DEG_PER_BURST` /
`EL_DEG_PER_BURST` changes the cycle time proportionally, so calibrate in water
with the brush loaded. The planner's 44 s assumes 45 °/s; the expected 25–35 °/s
gives the 55–80 s cycle in section 4.

---

## 9. Workspace explorer (`tools/swept_area.html`)

A self-contained page (no build, no dependencies) that solves the real question:
**given joint limits, which parts of the floor can this arm reach at all?** It
computes the reachable workspace analytically — inverse kinematics on a 0.25 cm
grid, then dilates by the brush radius — so the dead area is exact, not the
result of one guessed path.

Open it directly: `start tools/swept_area.html` (or drag it into a browser).

| control | what it changes |
|---|---|
| Shoulder ± / Elbow ± | joint limits = hose/wire twist |
| Brush radius | head size; also sets the outer edge (40 + b) |
| θ1 / θ2 sliders | move the arm by hand |
| Trace duration (2–40 s) | how slowly the path runs — adjustable mid-trace |
| Trace a path | walks the reachable area the way a cycle would (paints what it actually scrubs) |

### Measured trade-off (⌀16 brush, tank r 50, links 20 + 20)

| shoulder ± | coverage | | elbow ± | coverage |
|---|---|---|---|---|
| 180° | **91.0 %** | | 180° | **91.0 %** |
| 150° | 90.1 % | | 150° | 90.7 % |
| 120° | 84.4 % | | 120° | 85.1 % |
| 90° | 73.6 % | | 90° | 74.2 % |
| 60° | 59.9 % | | 60° | 62.1 % |

Three things this settles:

1. **The wall ring is a reach limit, not a joint limit.** Loosening the joints
   cannot close the 2.0 cm ring (section 2); only more reach can.
2. **Shoulder ±150° is nearly free** — 0.9 points. If ±180° of hose twist is
   unacceptable, ±150° buys almost the same coverage; below ±120° it collapses
   (84.4 % → 73.6 % at ±90°).
3. **The elbow tolerates ±150° well** (90.7 %) but falls off faster below that:
   ±120° costs 6 points, ±90° costs 17.

Screenshot: [`workspace-2r.png`](workspace-2r.png)

### Coverage planner — minimal passes, no wasted floor

The brush is a disc of radius *b*, so one full circular pass at radius *r* scrubs
the annulus **[r − b, r + b] exactly**. Tiling the reachable disc with concentric
passes spaced **2b − overlap** covers everything with only the overlap you ask
for — the minimum number of passes, and no other duplication.

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

The 91.0 % above is the reachable workspace; the planner's 90.0 % is what the
three-ring cycle actually scrubs, after the 1.13 % overlap.

**Park pose.** Every cycle starts and ends in the same rest form: both links
folded back on themselves, θ1 = 0°, θ2 = ±180°, tip at the tank centre. That is
the most compact shape the arm can take (one 20 cm line), loads both joints the
least, and never rests against the wall. The tool draws it as a ghost so the
resting position is part of the picture, and the planner prices the two park legs
into the ordering — it solves for a *cycle*, not an open path.

**Why three rings.** The ladder must fit inside the 40 cm reach, so a tighter
ladder trades wall band for overlap. Forcing a fourth ring to hold the outer edge
at 40 cm would stack 5.3 cm of overlap on every boundary and duplicate **20 %** of
the floor. Three rings at 15.7 cm spacing is the right call.

**Where the repositioning goes.** Repositioning is almost all three elbow flips
(one per ring, ≈300° each). A ring below r = 40 cannot be swept by one elbow
branch inside a ±180° shoulder limit — the branch must flip at some angle. Only a
wider shoulder limit removes that, not a better algorithm.

The planner splits rings into arcs where a limit or branch flip forces a
reconfiguration, orders those arcs **exactly** (Held-Karp over arcs × directions,
priced as a cycle back to park), and interpolates every move so the animation
shows the real motion. The whole plan is drawn before it runs — grey for
scrubbing passes, dashed amber for repositioning.

---

## 10. Verification metrics — four separate quantities

A review of the specification caught a real defect: the flush-era formula

```
E = (Pre − Post) / Pre × 100
```

was written against **TankScore**, which is a *higher-is-better* index. The ratio
form only means "reduction" for a lower-is-better quantity, so on TankScore it
inverts the sign: a cycle that improves the score from 40 to 75 returns
**−87.5 %**, i.e. "worse than doing nothing" for water that got better.

The product no longer flushes, and the cleaning cycle must report four distinct
quantities. They are not interchangeable and must never be printed under one
label such as "effectiveness".

| # | metric | symbol | formula | unit | better when |
|---|---|---|---|---|---|
| 1 | turbidity reduction | `R_T` | `(T_pre − T_post) / T_pre × 100`, `T_pre > 0` | % | higher |
| 2 | estimated sediment reduction | `R_S` | `(S_pre − S_post) / S_pre × 100`, `S = k·(T − T₀)` | % | higher |
| 3 | TankScore change | `ΔQ` | `Q_post − Q_pre` | points | higher |
| 4 | estimated sediment mass removed | `m` | `(S_pre − S_post) × V` | g | higher |

`T` = turbidity (NTU), `S` = suspended-solids estimate (mg/L), `k` and `T₀` from
the NTU→mg/L calibration, `V` = tank volume (L), `Q` = TankScore (0–100).

Rules:

1. **The ratio form is only valid on a reduction quantity.** Turbidity and the
   sediment estimate qualify; TankScore does not. Report TankScore as a point
   change (`ΔQ`, positive = better), never as a percentage of its own baseline.
2. **Percentages need a baseline.** `R_T` and `R_S` are undefined at `T_pre = 0`
   and are clamped to `[−100, +100]`; below the detection limit the cycle reports
   "no measurable change" instead of a number.
3. **`R_S` and `m` are estimates.** Both depend on the NTU→mg/L calibration, so
   they are labelled "estimated" wherever shown and are never presented as
   measured mass.
4. **A pass/fail threshold must name its metric.** The old "≥ 40 % effectiveness"
   becomes e.g. `R_T ≥ 40 %` — attached to turbidity, with `ΔQ` reported
   alongside it for the composite score.
5. **Worked example.** Pre: turbidity 18 NTU, score 40. Post: turbidity 6 NTU,
   score 75. Then `R_T = 66.7 %`, `ΔQ = +35 points`, and `R_S`/`m` follow from the
   calibration and tank volume. The score improved and every number says so.

Where these appear: the spec's storage row (now names the four metrics), the
design record here, and the dashboard's session log (it keeps turbidity and score
series separately, so all four are derivable client-side).

---

## 11. Open questions (blocking firmware)

1. **Product narrative** — is the cleaner a separate product, or do the spec and
   patent drafts get rewritten to include an actuator in the tank? (section 3)
2. **Motors in water** — IP68 inside the tank, or above the lid driving through
   the pipe? (section 5)
3. **Pump mounting** — radius and height, which decide whether the arm needs a
   keep-out sector, a dock, or vertical clearance. (section 2)
4. **Power** — mains at the pump point, or the monitor's 12 V rail?
5. **Encoders** — fit the optional 12 PPR units and close the loop, or stay open
   loop with re-homing? (section 4)
