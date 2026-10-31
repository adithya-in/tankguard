# TankGuard C1 — TRL 7 evidence note

**Document:** TG-TRL-2026-001
**Date:** 31 October 2026
**Subject:** Technology readiness of the C1 cleaning arm after the 500 L tank test
**Prepared for:** TIH IoT Technology Development Program 2026 (TDP 11)
**Prepared by:** Dr. Vishnu Vasudev (PI), with Nuke Labs

---

## 1. Claim

The C1 cleaning arm has reached **TRL 7** on the drive, structure and manual
control axis. On 31 October 2026 the arm was assembled, lowered into a real
500 L water tank, powered from its own supply, and driven in both directions on
both joints by the operator through the controller's own web page.

The claim is deliberately narrow. It covers the arm as a machine in its real
operating environment. It does not claim the autonomous cleaning cycle, the
brush and pump under sludge, or coverage, which the project delivers.

## 2. The scale used

The definitions below are the ones in the TDP application form.

| Level | Definition | Where TankGuard stands |
|---|---|---|
| TRL 6 | The technology works in near-real or simulated conditions | The arm was previously exercised on the bench, out of the tank |
| **TRL 7** | **The technology works in a real place** | **The arm ran in a 500 L tank, in water, under its own power** |
| TRL 8 | The product is finished and ready | Target of this project |
| TRL 9 | People use it every day for real work | After first sales |

## 3. What was demonstrated

**Test article.** The C1 arm: two rigid 20 cm links, one joint at the shoulder
and one at the elbow, a ring brush head at the tip, driven by two 12 V planetary
gearmotors through dual-PWM drivers. Controller: ESP8266 NodeMCU running
`firmware/c1_cleaner`, powered from its own 12 V supply, with the tank unit not
connected.

**Environment.** A 500 L water storage tank, filled, with the arm mounted at the
lid opening and the links immersed. This is the environment the product is sold
for, not a bench mock-up.

**Procedure.**

1. Power the controller and join its hotspot.
2. Open the controller page at 192.168.4.1.
3. In manual mode, jog the shoulder forward and back in bursts, then the elbow
   forward and back, watching the links in the tank.
4. Confirm direction, response and freedom from binding.

**Result.** Both joints moved in both directions, in the tank, under load. The
arm responded to each jog command, reversed on command, and did not bind or
stall. Manual control worked end to end: browser, controller, drivers, motors,
mechanism, in water.

## 4. What this proves, and what it does not

**Proved.**

- The arm's structure and joints survive and operate in a real tank.
- The drivetrain has enough torque to move the links in water.
- The controller, drivers and wiring work in the real installation.
- Direction and speed control respond as commanded, in both directions.

**Not yet proved, and not claimed.**

- The autonomous arc cycle in the tank (the path planner has run in simulation
  and on the bench).
- Brush and pump behaviour against settled sludge.
- Floor coverage measured in the tank.
- Repeatability across a full three-ring cycle.
- Certification and field reliability.

These are the deliverables of the funded project, and they are what separate
TRL 7 from TRL 8.

## 5. Why this is TRL 7 and not TRL 6

TRL 6 is a demonstration in a near-real or simulated environment: a bench rig, a
dry test stand, a model tank. That is what the arm had before this test.

TRL 7 is a demonstration in the real place. The arm was not on a bench; it was
in a 500 L tank, in water, doing the job it is designed to do, with the hardware
that will be installed. The distinction is the environment, and the environment
is exactly what changed.

## 6. Path from TRL 7 to TRL 8

| Milestone | What closes the gap |
|---|---|
| M1, T0 + 3 months | Line installed, design frozen, certification scope agreed |
| M2, T0 + 6 months | Twenty-five pilot sets built in-house; IP68 and EMC passed; unit cost confirmed |
| M3, T0 + 9 months | Twelve installations in three cities; sixty days of operation |
| M4, T0 + 12 months | Certification filed, three paying pilots, channel agreement, TRL 8 evidence pack |

## 7. Evidence held

- Photographs and video of the arm running in the 500 L tank, uploaded separately
  with the application.
- Serial log from the controller covering the manual jog commands.
- This note.
