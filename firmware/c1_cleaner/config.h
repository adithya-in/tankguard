#pragma once

// ---------------------------------------------------------------------------
// TankGuard C1 — cleaning-arm controller configuration (OPEN LOOP)
//
// Hardware: ESP32 DevKit + two generic DC gear motors on H-bridges (PWM + DIR),
// one brush motor, home switches and the safety chain.
//
// There is NO position feedback on this build. Motion is timed: each joint is
// driven at a fixed duty whose speed you calibrate, and the angle is dead
// reckoned from that. Two consequences, by design:
//   - the arm re-homes between rings, so drift never spans a whole cycle;
//   - the brush is 16 cm wide, so a few degrees of error is tolerable, but the
//     planner's 0.3 cm overlap is far below the real repeatability.
// ---------------------------------------------------------------------------

// ---- shoulder joint -------------------------------------------------------
#define SH_PWM        25
#define SH_DIR        26
#define SH_HOME       39   // NC switch to GND, internal pull-up, trips at theta = 0
#define SH_DIR_INVERT 0

// ---- elbow joint ----------------------------------------------------------
#define EL_PWM        27
#define EL_DIR        14
#define EL_HOME       18
#define EL_DIR_INVERT 0

// ---- brush head + suction ------------------------------------------------
// The head is a ring brush: bristles on the perimeter only, the centre is the
// pump intake. Scrubbing only loosens the sludge — the pump carries it away —
// so the bristles run light.
#define BRUSH_PWM     13
#define BRUSH_IS      36
#define BRUSH_IS_ENABLED 0 // 1 once a current-sense resistor is fitted

// Suction pump relay/MOSFET. The bristle field is sparse, so the head cannot
// seal — there is no vacuum downforce to worry about. The pump is still
// sequenced with the brush (on while scrubbing, off between passes) to save
// power and to avoid stirring sludge during repositioning, not as a safety gate.
#define PUMP_PIN          23
#define PUMP_ACTIVE_HIGH  1

// ---- safety chain ---------------------------------------------------------
// Both normally-closed to GND with a pull-up: a broken wire reads HIGH, which
// is treated as unsafe (fail-safe).
#define PIN_ESTOP     19   // LOW = loop intact, HIGH = pressed / broken
#define PIN_LID       21   // LOW = lid closed, HIGH = open / broken

// ---- drivetrain (TJX28ZRM / ZX6091 — RS395 12 V + 21.5:1 planetary) --------
// Datasheet (tyhemotors.com/tjx28zrm), 12 V, ratio 21.5, 2 stages, 72 % eff:
//   no-load 348.8 rpm · rated 279 rpm · rated torque 11.3 N.cm
//   motor stall 21.9 mN.m -> ~34 N.cm at the output · rated 0.62 A · stall 4.5 A
//
// 279 rpm loaded is still 1674 deg/s, and a loaded DC motor stalls below ~15 %
// duty, so the sweep is PWM in TIME: a full-duty burst, then a coast.
//
// Torque reality: the arm sweeps horizontally, so gravity is a bearing load.
// The joint fights a light ring of bristles (sparse: ~4-8 N.cm), water drag
// (~4-8) and inertia (~10-20). That lands at ~8-16 N.cm against 11.3 rated /
// ~34 stall — MARGINAL. Keep the brush head light (<= 0.2 kg) and expect
// there is no suction downforce; expect 25-35 deg/s and a 55-80 s cycle.
//
// The same motor is available with an optional 12 PPR magnetic encoder (A&B):
// 12 * 4 * 21.5 = 1032 counts/rev = 0.35 deg/count. Order it if you can — it
// turns this dead-reckoned controller into a closed-loop one.
#define MOTOR_RPM_RATED  279.0f
#define MOTOR_RPM_NOLOAD 348.8f
#define MOTOR_TORQUE_NCM 11.3f
#define MOTOR_STALL_NCM  34.0f
#define BURST_DUTY       255
#define BURST_MS         250
#define PAUSE_MS         200
#define SH_DEG_PER_BURST 10.0f
#define EL_DEG_PER_BURST 10.0f
// Belt/pulley or friction transmission would be a reduction too — out of scope
// here: the build is direct drive with no gearbox.


// ---- motion limits --------------------------------------------------------
#define JOINT_MIN_DEG -185.0f
#define JOINT_MAX_DEG  185.0f
#define MOVE_TOL_DEG    0.5f
#define HOME_DUTY       90
#define HOME_TIMEOUT_MS 25000UL
#define SETTLE_MS       180UL   // settle after the last burst of a move

// ---- brush ----------------------------------------------------------------
#define BRUSH_DUTY       200
#define BRUSH_STALL_RAW  3600   // ADC threshold; 0 disables stall detection

// ---- tank interlocks ------------------------------------------------------
#define MIN_LEVEL_PCT    15.0f
#define LEVEL_MAX_AGE_MS 60000UL
#define WIFI_SSID ""
#define WIFI_PASS ""
#define M1_DATA_URL "http://192.168.1.50/data"

// ---- telemetry ------------------------------------------------------------
#define SERIAL_BAUD 115200
#define STATUS_LED   2
