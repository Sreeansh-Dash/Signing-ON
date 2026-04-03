# Assistive Robotic Sign-Language Training Glove

**An assistive wearable system that teaches Indian Sign Language (ISL) fingerspelling through proportional vibrotactile haptic feedback.**

> **Status:** Software-First Development Track | No Hardware Required  
> **Platform:** ESP32-S3 (Xtensa LX7 Dual-Core, 240 MHz, 8 MB PSRAM)  
> **Framework:** Arduino + FreeRTOS  
> **IP Target:** Indian Provisional Patent (Section 3(k) compliant) + Scopus-indexed publication

---

## Architecture Overview

```
┌─────────────┐  ADC  ┌──────────────────────────────────────┐
│  5x Flex    ├──────►│  sensorTask (Core 0, 1ms)            │
│  Sensors    │       │  EMA Filter → Angle LUT → RingBuffer  │
├─────────────┤       └──────────────┬───────────────────────┘
│  MPU-6050   │  I2C                 │
│  IMU        ├──────►               ▼
├─────────────┤       ┌──────────────────────────────────────┐
│  FSR (palm) ├──────►│  signMatchTask (Core 0, 10ms)        │
└─────────────┘       │  Threshold Compare + TinyML Classify  │
                      └──────────────┬───────────────────────┘
                                     ▼
┌─────────────┐  PWM  ┌──────────────────────────────────────┐
│  5x ERM     │◄──────┤  feedbackTask (Core 1, 5ms)          │
│  Motors     │       │  PWM duty ∝ angular error             │
└─────────────┘       └──────────────────────────────────────┘
```

## Quick Start (No Hardware)

```bash
# 1. Create virtual environment
python -m venv venv
.\venv\Scripts\activate    # Windows
# source venv/bin/activate  # Linux/macOS

# 2. Install dependencies
pip install -r requirements.txt

# 3. Generate ISL sign library (26 letters)
python tools/generate_sign_library.py

# 4. Run unit tests
pytest tests/ -v

# 5. Run the glove simulator
python simulator/main_simulator.py --sign B --mode animated --duration 10

# 6. Generate synthetic training data
python ml/generate_synthetic_dataset.py

# 7. Train the gesture classifier
python ml/train_classifier.py
```

## Project Structure

```
├── core/                    ← Hardware-independent Python logic
│   ├── ema_filter.py        ← Exponential Moving Average filter
│   ├── calibration_lut.py   ← ADC-to-angle lookup table
│   ├── sign_matcher.py      ← Core sign matching engine
│   └── haptic_engine.py     ← Haptic feedback computation
│
├── simulator/               ← Desktop simulation (no hardware needed)
│   ├── main_simulator.py    ← Full pipeline simulator
│   └── mock_sensor_hal.py   ← Synthetic sensor data generator
│
├── data/signs/              ← ISL JSON sign library (26 files)
│
├── ml/                      ← TinyML training pipeline
│   ├── generate_synthetic_dataset.py
│   └── train_classifier.py
│
├── firmware/                ← ESP32-S3 Arduino/FreeRTOS code
│   ├── src/
│   │   ├── main.ino         ← FreeRTOS task entry point
│   │   ├── sensor_hal.h/.c  ← Hardware abstraction layer
│   │   ├── haptic_driver.h/.c
│   │   ├── sign_matcher.h/.c
│   │   └── ble_service.h/.c
│   ├── platformio.ini
│   └── partitions.csv
│
├── validation/              ← Publication metrics framework
│   └── metrics_tracker.py
│
├── tools/                   ← Utility scripts
│   ├── generate_sign_library.py
│   └── data_collector.py
│
└── tests/                   ← Unit tests (pytest)
    ├── test_ema_filter.py
    ├── test_sign_matcher.py
    └── test_haptic_engine.py
```

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Linear error-to-PWM mapping | Maximum gradient throughout correction range |
| Dead band = 8° | Within EMA filter settling error; prevents micro-buzz |
| EMA α = 0.2 | 10 ms settling → 3° lag at 300°/s (within dead band) |
| TFLite dense MLP | <2 ms inference on S3; static signs don't need sequences |
| BLE GATT over WiFi | Lower latency, no router dependency |
| `xQueueOverwrite` | Haptic command is current state, not history |

## License

This project is developed for academic research and patent filing purposes.
