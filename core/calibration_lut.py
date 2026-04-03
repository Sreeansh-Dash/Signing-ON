# core/calibration_lut.py
#
# ADC-to-angle lookup table (LUT) system.
# Piecewise linear interpolation between 5 calibration points per finger.
#
# Calibration workflow (hardware required for population, but schema is defined now):
#   Physical calibration points: 0°, 30°, 60°, 90°, 120° per finger
#   (use 3D-printed jig as specified in Validation Test #1)
#
# Each finger has its own LUT due to unit-to-unit variation in flex sensors.
# Reference document notes: "Buy 7–8 sensors and characterise them individually."

import json
import os
import numpy as np


CALIBRATION_SCHEMA = {
    "finger_0": {  # Thumb
        "calibration_points": [
            {"angle_deg": 0,   "adc_raw": None},
            {"angle_deg": 30,  "adc_raw": None},
            {"angle_deg": 60,  "adc_raw": None},
            {"angle_deg": 90,  "adc_raw": None},
            {"angle_deg": 120, "adc_raw": None},
        ],
        "sensor_serial": "FLEX-001",   # track unit identity for variance analysis
        "calibrated_at": None,         # ISO timestamp
    },
    # repeat for finger_1 through finger_4
}


class CalibrationLUT:
    """
    Piecewise linear interpolation between 5 known calibration points.

    Extrapolation beyond [0°, 120°] is clamped — flex sensors saturate
    and become non-linear outside this range for most cheap resistive units.
    """

    def __init__(self, calibration_file: str | None = None):
        self.luts: dict[int, tuple[np.ndarray, np.ndarray]] = {}
        if calibration_file and os.path.exists(calibration_file):
            self._load_from_file(calibration_file)
        else:
            self._load_defaults()

    def _load_defaults(self):
        """
        Placeholder LUT for simulation only.

        Based on typical Spectra Symbol flex sensor voltage divider (10kΩ pull-down,
        3.3V supply). At 0° bend, R_flex ≈ 10kΩ → Vout ≈ 1.65V → ADC ≈ 2048.
        At 90° bend, R_flex ≈ 30kΩ → Vout ≈ 2.47V → ADC ≈ 3072.
        These are estimates. Replace with measured values during hardware calibration.
        """
        for i in range(5):
            adc_vals = np.array([1800, 2200, 2600, 3100, 3600])
            angle_vals = np.array([0.0, 30.0, 60.0, 90.0, 120.0])
            self.luts[i] = (adc_vals, angle_vals)

    def _load_from_file(self, path: str):
        """Load calibration data from a JSON file."""
        with open(path) as f:
            data = json.load(f)
        for key, finger_data in data.items():
            idx = int(key.split("_")[1])
            points = finger_data["calibration_points"]
            adc_vals = np.array([p["adc_raw"] for p in points], dtype=float)
            angle_vals = np.array([p["angle_deg"] for p in points], dtype=float)
            self.luts[idx] = (adc_vals, angle_vals)

    def adc_to_degrees(self, finger_index: int, adc_raw: int) -> float:
        """
        Convert a raw 12-bit ADC count to degrees for the given finger.

        Uses piecewise linear interpolation. Values outside the calibrated
        range are clamped to [0°, 120°].
        """
        adc_vals, angle_vals = self.luts[finger_index]
        return float(np.interp(adc_raw, adc_vals, angle_vals))

    def save_calibration(self, path: str):
        """Export current LUT data to a JSON file."""
        data = {}
        for idx, (adc_vals, angle_vals) in self.luts.items():
            data[f"finger_{idx}"] = {
                "calibration_points": [
                    {"angle_deg": float(a), "adc_raw": int(r)}
                    for a, r in zip(angle_vals, adc_vals)
                ],
                "sensor_serial": f"FLEX-{idx:03d}",
                "calibrated_at": None,
            }
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
