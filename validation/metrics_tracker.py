# validation/metrics_tracker.py
#
# All metrics required for the paper results section.
# Fields map 1:1 to Module 3 of the Technical Reference.
# Implements the measurement scaffolding for 7 stress tests.

import csv
import os
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class PublicationMetrics:
    """
    All metrics required for the paper results section.
    Fields map 1:1 to Module 3 of the Technical Reference.
    """

    # Test 1 — Flex sensor linearity
    flex_linearity_error_deg: List[float] = field(default_factory=list)  # ±° per sensor

    # Test 2 — Sign discrimination accuracy
    confusion_matrix: Optional[object] = None  # numpy 26×26 array

    # Test 3 — Haptic guidance effectiveness
    correction_attempts_per_sign: List[List[int]] = field(default_factory=list)
    # shape: [num_signs][num_trials] → learning curve extractable

    # Test 4 — BLE round-trip latency
    ble_roundtrip_latency_ms: List[float] = field(default_factory=list)
    # target < 300 ms; measure from STT trigger to first motor PWM change

    # Test 5 — Battery life
    idle_current_ma: Optional[float] = None
    active_current_ma: Optional[float] = None
    measured_battery_life_hours: Optional[float] = None

    # Test 6 — Sensor drift at rest
    drift_std_dev_deg: List[float] = field(default_factory=list)  # per finger, 30 min

    # Test 7 — TinyML accuracy
    tflite_top1_accuracy: Optional[float] = None
    inference_time_us: Optional[float] = None

    # Publication extras
    adc_noise_floor_counts_std: Optional[float] = None
    haptic_latency_ms: Optional[float] = None  # cmd write → motor start
    ble_reconnect_events_per_hour: Optional[float] = None

    def to_summary_string(self) -> str:
        """Human-readable summary of measured metrics."""
        lines = [
            (
                f"BLE Round-trip: {sum(self.ble_roundtrip_latency_ms)/len(self.ble_roundtrip_latency_ms):.1f} ms avg"
                if self.ble_roundtrip_latency_ms
                else "BLE: not measured"
            ),
            (
                f"TFLite Top-1: {self.tflite_top1_accuracy * 100:.1f}%"
                if self.tflite_top1_accuracy
                else "TFLite: not measured"
            ),
            (
                f"Inference time: {self.inference_time_us:.0f} µs"
                if self.inference_time_us
                else "Inference: not measured"
            ),
            (
                f"Battery life: {self.measured_battery_life_hours:.1f} h"
                if self.measured_battery_life_hours
                else "Battery: not measured"
            ),
        ]
        return "\n".join(lines)

    def export_csv(self, path: str = "validation/results/metrics.csv"):
        """Exports scalar metrics to CSV for paper results table."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["metric", "value", "unit", "target"])
            writer.writerow([
                "ble_latency_mean_ms",
                f"{sum(self.ble_roundtrip_latency_ms) / max(1, len(self.ble_roundtrip_latency_ms)):.1f}",
                "ms",
                "<300",
            ])
            writer.writerow([
                "tflite_accuracy",
                f"{(self.tflite_top1_accuracy or 0) * 100:.1f}",
                "%",
                ">85",
            ])
            writer.writerow([
                "inference_time_us",
                str(self.inference_time_us or ""),
                "µs",
                "<5000",
            ])
            writer.writerow([
                "sensor_drift_std",
                str(self.drift_std_dev_deg or ""),
                "deg",
                "<2",
            ])
        print(f"Metrics exported to {path}")
