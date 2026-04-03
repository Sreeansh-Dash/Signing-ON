// firmware/src/sensor_hal.h
//
// Sensor Hardware Abstraction Layer
// Separates business logic from GPIO/ADC/I2C hardware access.
// Implement twice: real (sensor_hal.c) and mock (for desktop sim).

#ifndef SENSOR_HAL_H
#define SENSOR_HAL_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

// Initialise all sensors. Returns true on success.
bool sensor_hal_init(void);

// Read raw 12-bit ADC value for flex sensor [0..4] (thumb=0, pinky=4)
// Returns -1 on read failure.
int16_t sensor_hal_read_flex_raw(uint8_t finger_index);

// Read MPU-6050 over I2C. Fills roll_deg, pitch_deg, yaw_deg.
// Returns false on I2C NACK or timeout.
bool sensor_hal_read_imu(float *roll_deg, float *pitch_deg, float *yaw_deg);

// Read FSR raw ADC (palm sensor). Returns 0–4095.
int16_t sensor_hal_read_fsr_raw(void);

// Convert a raw ADC count for finger [index] to degrees using
// pre-calibrated lookup table stored in LittleFS.
float sensor_hal_adc_to_degrees(uint8_t finger_index, int16_t raw_adc);

#ifdef __cplusplus
}
#endif

#endif // SENSOR_HAL_H
