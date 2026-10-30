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
- A **main arm** in 2020 aluminium extrusion carrying **two planetary-motor
  units** beneath it, each ending in a coupling/hub — the brush mounts.
- A **second arm segment** (`arm1` / `arm2`) hinged at the end of the main arm.
- Assembly tree: `Rigid 4` (brush mounts), `Revolute 3` and `Revolute 1` (two
  rotational axes), body `mainarm`.

**Motion implied:** the arm rotates about the pipe axis and sweeps a radius over
the tank floor while the two brush heads spin on their own axes; the second
segment gives reach adjustment or a fold for insertion through the lid.

| axis | joint | job |
|---|---|---|
| sweep | Revolute 1 | rotate the arm across the floor |
| fold / reach | Revolute 3 | fold for insertion, or set the sweep radius |
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
| arm reach, fully extended (centre → outer brush-motor axis, top view) | 40 cm | swept disc 5,027 cm² |
| **unreachable ring** | **10 cm wide** | **2,827 cm² = 36 % of the floor** |
| pump suction cup | ⌀ 5 cm | 19.6 cm² footprint (0.25 % of the floor) |
| 2020 extrusion stock | 500 mm | 100 mm of beam already sits beyond the outer motor |

**The ring is the real constraint.** It is exactly the wall base, where sludge
settles hardest. Options, cheapest first:

| option | change | result |
|---|---|---|
| **A — use the beam** | move the outer brush motor to the beam tip (stock is already 500 mm) | brush edge reaches past 50 cm → ring closed, no new parts |
| **B — accept it** | add a fixed wall-base brush/skirt at the tip | ring still 36 % but the fillet gets scrubbed |
| **C — extend** | telescoping arm beyond 500 mm | new stock, more mass, more torque on the sweep axis |

**Off-centre pivot is not a fix.** A 40 cm arm pivoted *d* from the centre
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

1. **Cable twist.** Continuous rotation winds the brush cables. Either a slip
   ring through the pipe, or constrain the sweep to **±170°** with a cable loop.
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

## 7. Open questions (blocking firmware)

1. **Motors** — what are the planetary units, and what drives the sweep axis:
   brushed DC with gearbox, or a stepper? (Voltage/current/gearing decide the
   driver, and the driver decides the board.)
2. **Controller** — ESP32-class (more PWM/timers, same toolchain as the repo) or
   keep ESP8266? Either way the cleaner gets its own unit.
3. **Motors in water** — IP68 inside the tank, or above the lid driving through
   the pipe?
4. **Sweep** — continuous rotation (slip ring) or ±170°?
5. **Power** — mains at the pump point, or the monitor's 12 V rail?
