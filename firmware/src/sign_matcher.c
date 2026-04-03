// firmware/src/sign_matcher.c
//
// C port of core/sign_matcher.py — the core sign matching algorithm.
// Linear error-to-PWM mapping with dead-band clamping.

#include "sign_matcher.h"
#include <math.h>
#include <string.h>

// ─── Constants ──────────────────────────────────────────────────────

#define MAX_ERROR_FOR_FULL_PWM_DEG 40.0f
#define DEFAULT_TOLERANCE_DEG       8.0f
#define DEFAULT_IMU_TOLERANCE_DEG  15.0f

// ─── Sign Definition ────────────────────────────────────────────────

typedef struct {
    int8_t  sign_id;
    float   target_angles[5];    // degrees
    float   roll_deg;
    float   pitch_deg;
    float   yaw_deg;
    float   tolerance_band;
    float   imu_tolerance;
    bool    is_loaded;
} SignDef_t;

static SignDef_t sign_library[MAX_SIGNS];

// ─── ISL Fingerspelling Angles (hardcoded for now) ──────────────────
// In production, load from LittleFS JSON files.
// This matches the Python ISL_FINGERSPELLING_ANGLES dictionary.

static const float ISL_ANGLES[26][5] = {
    {60, 90, 90, 90, 90},   // A
    {90,  0,  0,  0,  0},   // B
    {30, 30, 30, 30, 30},   // C
    {90,  0, 90, 90, 90},   // D
    {60, 60, 60, 60, 60},   // E
    { 0, 90,  0,  0,  0},   // F
    { 0,  0, 90, 90, 90},   // G
    {90,  0,  0, 90, 90},   // H
    {90, 90, 90, 90,  0},   // I
    {90, 90, 90, 90,  0},   // J
    { 0,  0,  0, 90, 90},   // K
    { 0,  0, 90, 90, 90},   // L
    {90, 90, 90, 90, 90},   // M
    {90, 90, 90, 90, 90},   // N
    {20, 20, 20, 20, 20},   // O
    { 0,  0, 90, 90, 90},   // P
    { 0,  0, 90, 90, 90},   // Q
    {90,  0,  0, 90, 90},   // R
    {90, 90, 90, 90, 90},   // S
    {30, 90, 90, 90, 90},   // T
    {90,  0,  0, 90, 90},   // U
    {90,  0,  0, 90, 90},   // V
    {90,  0,  0,  0, 90},   // W
    {90, 45, 90, 90, 90},   // X
    { 0, 90, 90, 90,  0},   // Y
    {90,  0, 90, 90, 90},   // Z
};

static const float ISL_IMU[26][3] = {
    // {roll, pitch, yaw}
    {0,   0,  90},  // A
    {0,   0,  90},  // B
    {0,  10,  90},  // C
    {0,   0,  90},  // D
    {0,   0,  90},  // E
    {0,   0,  90},  // F
    {0,  90,   0},  // G
    {0,  90,   0},  // H
    {0,   0,  90},  // I
    {0,   0,  90},  // J
    {0,   0,  90},  // K
    {0,   0,  90},  // L
    {0, -20,  90},  // M
    {0,  20,  90},  // N
    {0,   0,  90},  // O
    {0, -90,   0},  // P
    {0,  90,   0},  // Q
    {0,   0,  90},  // R
    {0,   0,  90},  // S
    {0,   0,  90},  // T
    {0,   0,  90},  // U
    {0,   0,  90},  // V
    {0,   0,  90},  // W
    {0,   0,  90},  // X
    {0,   0,  90},  // Y
    {0,   0,  90},  // Z
};

// ─── Initialisation ─────────────────────────────────────────────────

void sign_matcher_init(void) {
    memset(sign_library, 0, sizeof(sign_library));

    for (int i = 0; i < MAX_SIGNS; i++) {
        sign_library[i].sign_id = (int8_t)i;
        memcpy(sign_library[i].target_angles, ISL_ANGLES[i], sizeof(float) * 5);
        sign_library[i].roll_deg  = ISL_IMU[i][0];
        sign_library[i].pitch_deg = ISL_IMU[i][1];
        sign_library[i].yaw_deg   = ISL_IMU[i][2];
        sign_library[i].tolerance_band = DEFAULT_TOLERANCE_DEG;
        sign_library[i].imu_tolerance  = DEFAULT_IMU_TOLERANCE_DEG;
        sign_library[i].is_loaded = true;
    }
}

// ─── Match Computation ──────────────────────────────────────────────

void sign_matcher_compute(
    int8_t sign_id,
    const float flex_angles[5],
    float imu_roll,
    float imu_pitch,
    float imu_yaw,
    uint8_t motor_duty[5],
    bool *all_correct,
    uint8_t *wrist_pattern
) {
    if (sign_id < 0 || sign_id >= MAX_SIGNS || !sign_library[sign_id].is_loaded) {
        memset(motor_duty, 0, 5);
        *all_correct = false;
        *wrist_pattern = 0;
        return;
    }

    SignDef_t *sign = &sign_library[sign_id];
    float tolerance = sign->tolerance_band;
    bool fingers_correct = true;

    // Per-finger error → PWM duty (linear with dead-band)
    for (int i = 0; i < 5; i++) {
        float err = fabsf(flex_angles[i] - sign->target_angles[i]);

        if (err <= tolerance) {
            motor_duty[i] = 0;  // dead band
        } else if (err >= MAX_ERROR_FOR_FULL_PWM_DEG) {
            motor_duty[i] = 255;
            fingers_correct = false;
        } else {
            motor_duty[i] = (uint8_t)(
                (err - tolerance) / (MAX_ERROR_FOR_FULL_PWM_DEG - tolerance) * 255.0f
            );
            fingers_correct = false;
        }
    }

    // IMU orientation error
    float imu_err_roll  = fabsf(imu_roll  - sign->roll_deg);
    float imu_err_pitch = fabsf(imu_pitch - sign->pitch_deg);
    float imu_err_yaw   = fabsf(imu_yaw   - sign->yaw_deg);
    bool wrist_ok = (imu_err_roll  <= sign->imu_tolerance) &&
                    (imu_err_pitch <= sign->imu_tolerance) &&
                    (imu_err_yaw   <= sign->imu_tolerance);

    *all_correct = fingers_correct && wrist_ok;
    *wrist_pattern = wrist_ok ? 0 : 1;
}
