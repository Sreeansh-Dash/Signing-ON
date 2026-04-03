// firmware/src/sign_matcher.h
//
// C port of the Python sign matching engine.
// Used by signMatchTask in main.ino.

#ifndef SIGN_MATCHER_H
#define SIGN_MATCHER_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

// Maximum number of signs in the library
#define MAX_SIGNS 26

// Initialise sign matcher and load sign library from LittleFS.
void sign_matcher_init(void);

// Compute match between current sensor state and target sign.
// Outputs: motor_duty[5], all_correct flag, wrist_pattern.
void sign_matcher_compute(
    int8_t sign_id,
    const float flex_angles[5],
    float imu_roll,
    float imu_pitch,
    float imu_yaw,
    uint8_t motor_duty[5],
    bool *all_correct,
    uint8_t *wrist_pattern
);

#ifdef __cplusplus
}
#endif

#endif // SIGN_MATCHER_H
