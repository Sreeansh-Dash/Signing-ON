// firmware/src/main.ino
//
// Assistive Robotic Sign-Language Training Glove
// ESP32-S3 Main Entry Point
//
// FreeRTOS tasks:
//   sensorTask   — Core 0, Priority 3, 1 ms period
//   signMatchTask — Core 0, Priority 2, 10 ms period
//   feedbackTask — Core 1, Priority 2, 5 ms period

#include <Arduino.h>
#include "sensor_hal.h"
#include "haptic_driver.h"
#include "sign_matcher.h"
#include "ble_service.h"

// ─── Shared Data Structures ─────────────────────────────────────────

typedef struct {
    float flex_angles[5];     // degrees; index=0 (thumb) to index=4 (pinky)
    float imu_roll;           // degrees; MPU-6050 roll axis
    float imu_pitch;          // degrees; MPU-6050 pitch axis
    float imu_yaw;            // degrees; MPU-6050 yaw axis
    uint32_t timestamp_ms;    // millis()
} AngleVector_t;

typedef struct {
    uint8_t motor_duty[5];    // 0–255; index matches flex_angles
    uint8_t wrist_pattern;    // 0=none, 1=single, 2=double buzz (V1.1)
    bool all_correct;         // true if all errors < dead_band
    uint8_t classifier_result; // V1.1: predicted sign index (0=unknown)
} HapticCommand_t;

// ─── Ring Buffer (lock-free SPSC) ───────────────────────────────────

#define RING_BUFFER_SIZE 50
static AngleVector_t ring_buffer[RING_BUFFER_SIZE];
static volatile uint32_t ring_write_idx = 0;

// ─── Haptic Command Queue ───────────────────────────────────────────

static QueueHandle_t hapticCmdQueue;

// ─── EMA Filter State ───────────────────────────────────────────────

#define EMA_ALPHA 0.2f
#define NUM_SENSORS 8  // 5 flex + 3 IMU

static float ema_state[NUM_SENSORS];
static bool ema_initialized = false;

static void ema_update(float raw[NUM_SENSORS], float filtered[NUM_SENSORS]) {
    if (!ema_initialized) {
        for (int i = 0; i < NUM_SENSORS; i++) {
            ema_state[i] = raw[i];
            filtered[i] = raw[i];
        }
        ema_initialized = true;
        return;
    }
    for (int i = 0; i < NUM_SENSORS; i++) {
        ema_state[i] = EMA_ALPHA * raw[i] + (1.0f - EMA_ALPHA) * ema_state[i];
        filtered[i] = ema_state[i];
    }
}

// ─── Active Target Sign ─────────────────────────────────────────────

static volatile int8_t active_sign_id = -1;  // -1 = no target

// ─── sensorTask ─────────────────────────────────────────────────────
// Core: 0 | Priority: 3 (highest) | Stack: 4096 bytes | Period: 1 ms

void sensorTask(void *pvParameters) {
    TickType_t xLastWakeTime = xTaskGetTickCount();
    const TickType_t xPeriod = pdMS_TO_TICKS(1);

    while (1) {
        // 1. Read 5 ADC flex channels
        float raw[NUM_SENSORS];
        for (int i = 0; i < 5; i++) {
            int16_t adc_raw = sensor_hal_read_flex_raw(i);
            raw[i] = sensor_hal_adc_to_degrees(i, adc_raw);
        }

        // 2. Read MPU-6050 over I2C
        float roll, pitch, yaw;
        sensor_hal_read_imu(&roll, &pitch, &yaw);
        raw[5] = roll;
        raw[6] = pitch;
        raw[7] = yaw;

        // 3. Apply EMA filter
        float filtered[NUM_SENSORS];
        ema_update(raw, filtered);

        // 4. Write to ring buffer (lock-free single-producer)
        uint32_t idx = ring_write_idx % RING_BUFFER_SIZE;
        ring_buffer[idx].flex_angles[0] = filtered[0];
        ring_buffer[idx].flex_angles[1] = filtered[1];
        ring_buffer[idx].flex_angles[2] = filtered[2];
        ring_buffer[idx].flex_angles[3] = filtered[3];
        ring_buffer[idx].flex_angles[4] = filtered[4];
        ring_buffer[idx].imu_roll  = filtered[5];
        ring_buffer[idx].imu_pitch = filtered[6];
        ring_buffer[idx].imu_yaw   = filtered[7];
        ring_buffer[idx].timestamp_ms = millis();
        ring_write_idx++;

        vTaskDelayUntil(&xLastWakeTime, xPeriod);
    }
}

// ─── signMatchTask ──────────────────────────────────────────────────
// Core: 0 | Priority: 2 | Stack: 8192 bytes | Period: 10 ms

void signMatchTask(void *pvParameters) {
    TickType_t xLastWakeTime = xTaskGetTickCount();
    const TickType_t xPeriod = pdMS_TO_TICKS(10);

    while (1) {
        // 1. Read latest AngleVector from ring buffer
        uint32_t latest_idx = (ring_write_idx - 1) % RING_BUFFER_SIZE;
        AngleVector_t current = ring_buffer[latest_idx];

        // 2. If no target sign active → skip
        if (active_sign_id < 0) {
            vTaskDelayUntil(&xLastWakeTime, xPeriod);
            continue;
        }

        // 3. Compute match (delegated to sign_matcher module)
        HapticCommand_t cmd;
        sign_matcher_compute(
            active_sign_id,
            current.flex_angles,
            current.imu_roll,
            current.imu_pitch,
            current.imu_yaw,
            cmd.motor_duty,
            &cmd.all_correct,
            &cmd.wrist_pattern
        );
        cmd.classifier_result = 0;  // V1.1: TFLite inference here

        // 4. Send to feedbackTask (overwrite — always latest)
        xQueueOverwrite(hapticCmdQueue, &cmd);

        vTaskDelayUntil(&xLastWakeTime, xPeriod);
    }
}

// ─── feedbackTask ───────────────────────────────────────────────────
// Core: 1 | Priority: 2 | Stack: 2048 bytes | Period: 5 ms

void feedbackTask(void *pvParameters) {
    TickType_t xLastWakeTime = xTaskGetTickCount();
    const TickType_t xPeriod = pdMS_TO_TICKS(5);

    while (1) {
        HapticCommand_t cmd;
        // Non-blocking read (timeout = 0)
        if (xQueueReceive(hapticCmdQueue, &cmd, 0) == pdTRUE) {
            haptic_driver_set_duties(cmd.motor_duty);

            // V1.1: handle wrist buzz pattern
            // (Implementation deferred until hardware arrives)
        }

        vTaskDelayUntil(&xLastWakeTime, xPeriod);
    }
}

// ─── BLE Target Sign Callback ───────────────────────────────────────

void on_target_sign_received(uint8_t sign_id) {
    if (sign_id == 0xFF) {
        active_sign_id = -1;  // stop/idle
        haptic_driver_all_off();
        Serial.println("Target sign cleared (idle mode)");
    } else if (sign_id <= 25) {
        active_sign_id = (int8_t)sign_id;
        Serial.printf("Target sign set: %c (ID=%d)\n", 'A' + sign_id, sign_id);
    }
}

// ─── Arduino setup() ────────────────────────────────────────────────

void setup() {
    Serial.begin(115200);
    Serial.println("\n=== Assistive Sign-Language Training Glove ===");
    Serial.println("Firmware version: 1.0-alpha");

    // Initialise hardware abstraction layer
    if (!sensor_hal_init()) {
        Serial.println("ERROR: Sensor HAL init failed!");
    }

    // Initialise haptic motor driver
    haptic_driver_init();

    // Initialise sign library (from LittleFS on flash)
    sign_matcher_init();

    // Initialise BLE GATT service
    ble_service_init(on_target_sign_received);

    // Create haptic command queue (depth=1, overwrite semantics)
    hapticCmdQueue = xQueueCreate(1, sizeof(HapticCommand_t));
    if (hapticCmdQueue == NULL) {
        Serial.println("ERROR: Failed to create haptic command queue!");
    }

    // Create FreeRTOS tasks pinned to specific cores
    xTaskCreatePinnedToCore(sensorTask,   "sensorTask",   4096, NULL, 3, NULL, 0);
    xTaskCreatePinnedToCore(signMatchTask, "signMatchTask", 8192, NULL, 2, NULL, 0);
    xTaskCreatePinnedToCore(feedbackTask, "feedbackTask", 2048, NULL, 2, NULL, 1);

    Serial.println("All tasks started. Waiting for BLE target sign...");
}

// ─── Arduino loop() (unused — FreeRTOS tasks handle everything) ─────

void loop() {
    // FreeRTOS tasks handle all real-time work.
    // loop() can be used for low-priority housekeeping.
    delay(1000);
}
