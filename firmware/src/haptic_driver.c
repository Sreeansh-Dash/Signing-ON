// firmware/src/haptic_driver.c
//
// Haptic motor driver — ledc PWM implementation for ESP32-S3.
// Drives 5 ERM motors via 2N2222 transistor switches.

#include "haptic_driver.h"
#include "driver/ledc.h"

// ─── GPIO Pin Assignments ───────────────────────────────────────────
// Verify against your PCB layout

#define MOTOR_THUMB_GPIO   18
#define MOTOR_INDEX_GPIO   19
#define MOTOR_MIDDLE_GPIO  20
#define MOTOR_RING_GPIO    21
#define MOTOR_PINKY_GPIO   22
#define MOTOR_WRIST_GPIO   23  // V1.1 only — optional buzzer for IMU cue

static const int MOTOR_GPIOS[5] = {
    MOTOR_THUMB_GPIO, MOTOR_INDEX_GPIO, MOTOR_MIDDLE_GPIO,
    MOTOR_RING_GPIO, MOTOR_PINKY_GPIO
};

// ─── Initialisation ─────────────────────────────────────────────────

void haptic_driver_init(void) {
    // Configure ledc timer: 1 kHz, 8-bit resolution (0–255)
    ledc_timer_config_t timer_cfg = {
        .speed_mode       = LEDC_LOW_SPEED_MODE,
        .timer_num        = LEDC_TIMER_0,
        .duty_resolution  = LEDC_TIMER_8_BIT,   // 0–255 range
        .freq_hz          = 1000,                // 1 kHz for ERM motors
        .clk_cfg          = LEDC_AUTO_CLK
    };
    ledc_timer_config(&timer_cfg);

    // Configure one ledc channel per motor
    for (int i = 0; i < 5; i++) {
        ledc_channel_config_t ch_cfg = {
            .speed_mode     = LEDC_LOW_SPEED_MODE,
            .channel        = (ledc_channel_t)i,
            .timer_sel      = LEDC_TIMER_0,
            .intr_type      = LEDC_INTR_DISABLE,
            .gpio_num       = MOTOR_GPIOS[i],
            .duty           = 0,
            .hpoint         = 0
        };
        ledc_channel_config(&ch_cfg);
    }
}

// ─── Duty Cycle Control ─────────────────────────────────────────────

void haptic_driver_set_duties(const uint8_t duties[5]) {
    for (int i = 0; i < 5; i++) {
        ledc_set_duty(LEDC_LOW_SPEED_MODE, (ledc_channel_t)i, duties[i]);
        ledc_update_duty(LEDC_LOW_SPEED_MODE, (ledc_channel_t)i);
    }
}

void haptic_driver_all_off(void) {
    uint8_t zeros[5] = {0, 0, 0, 0, 0};
    haptic_driver_set_duties(zeros);
}
