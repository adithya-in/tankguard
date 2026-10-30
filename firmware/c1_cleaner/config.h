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

// ---- brush ----------------------------------------------------------------
#define BRUSH_PWM     13
#define BRUSH_IS      36
#define BRUSH_IS_ENABLED 0 // 1 once a current-sense resistor is fitted

// ---- safety chain ---------------------------------------------------------
// Both normally-closed to GND with a pull-up: a broken wire reads HIGH, which
// is treated as unsafe (fail-safe).
#define PIN_ESTOP     19   // LOW = loop intact, HIGH = pressed / broken
#define PIN_LID       21   // LOW = lid closed, HIGH = open / broken

// ---- speed calibration ----------------------------------------------------
// Drive a joint at MOVE_DUTY from its home switch for a known time, measure the
// angle it actually covered, and set DPS = degrees / seconds. Start with the
// motor's no-load rating and correct on the bench, in water, with the brush
// loaded — that is the number that matters.
#define SH_MOVE_DUTY  170
#define SH_DPS        42.0f   // deg/s at SH_MOVE_DUTY, loaded
#define EL_MOVE_DUTY  170
#define EL_DPS        42.0f

// A short full-duty kick breaks stiction; its distance is folded into the
// calibration above by keeping KICK_MS small relative to normal moves.
#define KICK_MS       90
#define KICK_DUTY     255

// ---- motion limits --------------------------------------------------------
#define JOINT_MIN_DEG -185.0f
#define JOINT_MAX_DEG  185.0f
#define MOVE_TOL_DEG    0.5f
#define HOME_DUTY       90
#define HOME_TIMEOUT_MS 25000UL
#define SETTLE_MS       180UL   // let the arm stop before the next move

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
