// firmware/src/ble_service.h
//
// BLE GATT service definition for the Sign-Language Training Glove.
// Uses ESP32 BLE Arduino library (NimBLE or Bluedroid backend).

#ifndef BLE_SERVICE_H
#define BLE_SERVICE_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

// Callback type for when companion app sends a target sign ID.
typedef void (*ble_target_sign_callback_t)(uint8_t sign_id);

// Initialise BLE GATT server with the Glove Control Service.
// callback: called when TARGET_SIGN characteristic is written.
void ble_service_init(ble_target_sign_callback_t callback);

// Notify the connected client with current sensor state.
// data: 8 bytes [5x flex_angle_uint8, 3x imu_delta_int8]
void ble_service_notify_sensor_state(const uint8_t data[8]);

// Notify the connected client with match result.
// data: 3 bytes [match_flags, rms_error, classifier_result]
void ble_service_notify_match_result(const uint8_t data[3]);

#ifdef __cplusplus
}
#endif

#endif // BLE_SERVICE_H
