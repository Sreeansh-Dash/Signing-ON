// firmware/src/haptic_driver.h
//
// Haptic motor driver interface using ESP32-S3 ledc PWM peripheral.

#ifndef HAPTIC_DRIVER_H
#define HAPTIC_DRIVER_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

// Initialise ledc PWM channels for 5 finger motors.
void haptic_driver_init(void);

// Set PWM duty cycles for all 5 motors.
// duties[0]=thumb, duties[4]=pinky. Range: 0–255.
void haptic_driver_set_duties(const uint8_t duties[5]);

// Turn off all motors immediately.
void haptic_driver_all_off(void);

#ifdef __cplusplus
}
#endif

#endif // HAPTIC_DRIVER_H
