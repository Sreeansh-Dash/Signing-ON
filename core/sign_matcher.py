# core/sign_matcher.py
#
# Core sign matching engine — the heart of the glove's feedback logic.
# Fully unit-testable without hardware.

import os
import glob
import json
import numpy as np
from dataclasses import dataclass
from typing import Optional


@dataclass
class MatchResult:
    """Result of comparing current hand pose against a target ISL sign."""

    is_match: bool                  # True if ALL fingers within tolerance
    finger_errors: list             # degrees error per finger [5 floats]
    imu_errors: dict                # {'roll': float, 'pitch': float, 'yaw': float}
    motor_duties: list              # PWM 0–255 per finger [5 ints]
    wrist_needs_correction: bool    # True if IMU error > imu_tolerance
    all_correct: bool               # True if match + IMU correct
    error_magnitude: float          # RMS of finger errors (useful for logging)


class SignMatcher:
    """
    Core sign matching algorithm.

    Error-to-PWM mapping: LINEAR, not logarithmic.

    Why linear? The publication's haptic effectiveness claim requires the
    vibration intensity to be proportional to the angular error. A logarithmic
    map would compress large errors and the gradient would be weak for users
    making coarse corrections. A linear map gives maximum gradient signal
    throughout the correction range.

    Max error for full PWM: 40° (configurable). At 40° error → duty=255.
    Dead band: 8° → duty=0 (configurable per sign).
    Between 8° and 40°: linear interpolation.
    """

    MAX_ERROR_FOR_FULL_PWM_DEG = 40.0

    def __init__(self, sign_library_path: str = "data/signs/"):
        self.signs: dict[int, dict] = {}
        self._load_library(sign_library_path)
        self.active_sign_id: Optional[int] = None

    def _load_library(self, path: str):
        """Load all ISL sign JSON files from the given directory."""
        for filepath in glob.glob(os.path.join(path, "*.json")):
            with open(filepath) as f:
                sign = json.load(f)
                self.signs[sign["sign_id"]] = sign
        print(f"SignMatcher: loaded {len(self.signs)} signs.")

    def set_target_sign(self, sign_id: int):
        """Set the active target sign for matching."""
        if sign_id not in self.signs:
            raise ValueError(f"Sign ID {sign_id} not in library (available: {sorted(self.signs.keys())})")
        self.active_sign_id = sign_id

    def get_sign_label(self, sign_id: int) -> str:
        """Get the human-readable label for a sign ID."""
        if sign_id in self.signs:
            return self.signs[sign_id].get("label", f"SIGN_{sign_id}")
        return f"UNKNOWN_{sign_id}"

    def compute_match(self, current_angles: list, current_imu: dict) -> Optional[MatchResult]:
        """
        Primary matching computation. Call this every 10 ms (signMatchTask period).

        Parameters
        ----------
        current_angles : list of float
            [thumb, index, middle, ring, pinky] in degrees.
        current_imu : dict
            {'roll': float, 'pitch': float, 'yaw': float} in degrees.

        Returns
        -------
        MatchResult or None
            None if no target sign is active.
        """
        if self.active_sign_id is None:
            return None

        sign = self.signs[self.active_sign_id]
        target = np.array(sign["target_angles"])
        current = np.array(current_angles)
        tolerance = sign["tolerance_band"]

        # Per-finger absolute error
        finger_errors = np.abs(current - target).tolist()

        # IMU orientation error
        wrist = sign["wrist_orientation"]
        imu_errors = {
            "roll":  abs(current_imu["roll"]  - wrist["roll_deg"]),
            "pitch": abs(current_imu["pitch"] - wrist["pitch_deg"]),
            "yaw":   abs(current_imu["yaw"]   - wrist["yaw_deg"]),
        }
        imu_tolerance = sign.get("imu_tolerance", 15.0)
        wrist_needs_correction = any(e > imu_tolerance for e in imu_errors.values())

        # Error-to-PWM mapping: linear with dead-band clamping
        motor_duties = []
        for err in finger_errors:
            if err <= tolerance:
                duty = 0  # dead band → silence
            elif err >= self.MAX_ERROR_FOR_FULL_PWM_DEG:
                duty = 255
            else:
                # Linear interpolation: tolerance → 0, MAX_ERROR → 255
                duty = int(
                    (err - tolerance)
                    / (self.MAX_ERROR_FOR_FULL_PWM_DEG - tolerance)
                    * 255
                )
            motor_duties.append(duty)

        is_match = all(e <= tolerance for e in finger_errors)
        all_correct = is_match and not wrist_needs_correction
        error_magnitude = float(np.sqrt(np.mean(np.array(finger_errors) ** 2)))

        return MatchResult(
            is_match=is_match,
            finger_errors=finger_errors,
            imu_errors=imu_errors,
            motor_duties=motor_duties,
            wrist_needs_correction=wrist_needs_correction,
            all_correct=all_correct,
            error_magnitude=error_magnitude,
        )
