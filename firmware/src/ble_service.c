// firmware/src/ble_service.c
//
// BLE GATT service implementation.
// Defines the Glove Control Service with 4 characteristics.
//
// NOTE: This is a scaffolding implementation. Full BLE stack
// integration requires ESP32 hardware. The UUIDs and schema
// are defined and ready for testing with nRF Connect.

#include "ble_service.h"
#include <Arduino.h>

// ─── Service and Characteristic UUIDs ───────────────────────────────
// Custom 128-bit UUIDs for this project.
// Generate your own at https://www.uuidgenerator.net/ for production.

#define GLOVE_SERVICE_UUID     "12345678-1234-1234-1234-123456789000"
#define TARGET_SIGN_UUID       "12345678-1234-1234-1234-123456789001"
#define SENSOR_STATE_UUID      "12345678-1234-1234-1234-123456789002"
#define MATCH_RESULT_UUID      "12345678-1234-1234-1234-123456789003"
#define DEVICE_CONFIG_UUID     "12345678-1234-1234-1234-123456789004"

// ─── Static State ───────────────────────────────────────────────────

static ble_target_sign_callback_t _target_sign_callback = NULL;

// ─── BLE Initialisation ─────────────────────────────────────────────

void ble_service_init(ble_target_sign_callback_t callback) {
    _target_sign_callback = callback;

    // TODO: Full BLE stack initialisation when hardware arrives.
    // This will use:
    //   BLEDevice::init("ISL-Glove");
    //   BLEServer *pServer = BLEDevice::createServer();
    //   BLEService *pService = pServer->createService(GLOVE_SERVICE_UUID);
    //
    //   // Create characteristics:
    //   // TARGET_SIGN  — WRITE | WRITE_NO_RESPONSE
    //   // SENSOR_STATE — NOTIFY (100 ms interval)
    //   // MATCH_RESULT — NOTIFY (50 ms interval)
    //   // DEVICE_CONFIG — READ | WRITE
    //
    //   pService->start();
    //   BLEAdvertising *pAdv = BLEDevice::getAdvertising();
    //   pAdv->addServiceUUID(GLOVE_SERVICE_UUID);
    //   pAdv->start();

    Serial.println("ble_service: init complete (stub mode)");
    Serial.printf("  Service UUID:     %s\n", GLOVE_SERVICE_UUID);
    Serial.printf("  Target Sign UUID: %s\n", TARGET_SIGN_UUID);
    Serial.printf("  Sensor State UUID: %s\n", SENSOR_STATE_UUID);
    Serial.printf("  Match Result UUID: %s\n", MATCH_RESULT_UUID);
}

// ─── BLE Notifications (stubs) ──────────────────────────────────────

void ble_service_notify_sensor_state(const uint8_t data[8]) {
    // TODO: pSensorStateCharacteristic->setValue(data, 8);
    //       pSensorStateCharacteristic->notify();
    (void)data;
}

void ble_service_notify_match_result(const uint8_t data[3]) {
    // TODO: pMatchResultCharacteristic->setValue(data, 3);
    //       pMatchResultCharacteristic->notify();
    (void)data;
}
