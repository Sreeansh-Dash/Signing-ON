// firmware/src/sensor_hal.c
//
// Sensor HAL — Mock implementation for development without hardware.
// Replace with real ADC/I2C reads when hardware arrives.

#include "sensor_hal.h"
#include <Arduino.h>
#include <math.h>

// ─── GPIO Pin Assignments ───────────────────────────────────────────
// Verify against your PCB layout and update as needed.

#define FLEX_ADC_PIN_0  1   // Thumb  (GPIO 1  → ADC1_CH0)
#define FLEX_ADC_PIN_1  2   // Index  (GPIO 2  → ADC1_CH1)
#define FLEX_ADC_PIN_2  3   // Middle (GPIO 3  → ADC1_CH2)
#define FLEX_ADC_PIN_3  4   // Ring   (GPIO 4  → ADC1_CH3)
#define FLEX_ADC_PIN_4  5   // Pinky  (GPIO 5  → ADC1_CH4)
#define FSR_ADC_PIN     6   // Palm   (GPIO 6  → ADC1_CH5)

#define MPU6050_I2C_ADDR  0x68
#define SDA_PIN           8
#define SCL_PIN           9

static const int FLEX_PINS[5] = {
    FLEX_ADC_PIN_0, FLEX_ADC_PIN_1, FLEX_ADC_PIN_2,
    FLEX_ADC_PIN_3, FLEX_ADC_PIN_4
};

// ─── Default Calibration LUT (simulation) ───────────────────────────
// Based on Spectra Symbol flex sensor voltage divider (10kΩ pull-down, 3.3V)

static const int16_t cal_adc[5] = {1800, 2200, 2600, 3100, 3600};
static const float   cal_deg[5] = {0.0f, 30.0f, 60.0f, 90.0f, 120.0f};

// ─── Initialisation ─────────────────────────────────────────────────

bool sensor_hal_init(void) {
    // Configure ADC resolution (ESP32-S3 supports up to 12-bit)
    analogReadResolution(12);

    // TODO: Initialise I2C for MPU-6050 when hardware arrives
    // Wire.begin(SDA_PIN, SCL_PIN);
    // Wire.setClock(400000);  // 400 kHz Fast mode

    Serial.println("sensor_hal: init complete (mock mode)");
    return true;
}

// ─── Flex Sensor Read ───────────────────────────────────────────────

int16_t sensor_hal_read_flex_raw(uint8_t finger_index) {
    if (finger_index > 4) return -1;

    // When hardware is connected, uncomment:
    // return (int16_t)analogRead(FLEX_PINS[finger_index]);

    // Mock: return mid-range value with slight variation
    return 2500 + (finger_index * 100);
}

// ─── IMU Read ───────────────────────────────────────────────────────

bool sensor_hal_read_imu(float *roll_deg, float *pitch_deg, float *yaw_deg) {
    if (!roll_deg || !pitch_deg || !yaw_deg) return false;

    // TODO: Replace with actual MPU-6050 I2C read when hardware arrives
    // Wire.beginTransmission(MPU6050_I2C_ADDR);
    // Wire.write(0x3B);  // ACCEL_XOUT_H
    // Wire.endTransmission(false);
    // Wire.requestFrom(MPU6050_I2C_ADDR, 14, true);
    // ... process accelerometer + gyro data ...

    // Mock: return near-zero values (hand at rest)
    *roll_deg  = 0.0f;
    *pitch_deg = 0.0f;
    *yaw_deg   = 90.0f;  // Default upright position

    return true;
}

// ─── FSR Read ───────────────────────────────────────────────────────

int16_t sensor_hal_read_fsr_raw(void) {
    // When hardware is connected:
    // return (int16_t)analogRead(FSR_ADC_PIN);

    return 0;  // Mock: no palm pressure
}

// ─── ADC to Degrees Conversion ──────────────────────────────────────

float sensor_hal_adc_to_degrees(uint8_t finger_index, int16_t raw_adc) {
    if (finger_index > 4) return 0.0f;

    // Piecewise linear interpolation (same logic as Python CalibrationLUT)
    if (raw_adc <= cal_adc[0]) return cal_deg[0];
    if (raw_adc >= cal_adc[4]) return cal_deg[4];

    for (int i = 0; i < 4; i++) {
        if (raw_adc >= cal_adc[i] && raw_adc <= cal_adc[i + 1]) {
            float t = (float)(raw_adc - cal_adc[i]) / (float)(cal_adc[i + 1] - cal_adc[i]);
            return cal_deg[i] + t * (cal_deg[i + 1] - cal_deg[i]);
        }
    }

    return 0.0f;
}
