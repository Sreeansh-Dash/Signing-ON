# simulator/mock_sensor_hal.py
#
# Generates synthetic flex angle and IMU data for software-only development.
# This mock replaces the real sensor_hal when developing on a laptop.

import numpy as np


class MockSensorHAL:
    """
    Generates synthetic flex angle and IMU data for software-only development.

    Supports three modes:
      - 'static':   holds a fixed pose (used for sign library authoring)
      - 'noisy':    static pose + Gaussian noise (tests EMA filter)
      - 'animated': smoothly transitions between random ISL-like poses
    """

    VALID_MODES = ("static", "noisy", "animated")

    def __init__(self, mode: str = "noisy", seed: int = 42):
        if mode not in self.VALID_MODES:
            raise ValueError(f"Invalid mode '{mode}'. Choose from: {self.VALID_MODES}")
        self.mode = mode
        self.rng = np.random.default_rng(seed)

        # Default starting pose (mid-range for all fingers)
        self._current_pose = np.array([45.0, 90.0, 30.0, 20.0, 60.0])  # degrees
        self._imu_state = np.array([0.0, 0.0, 0.0])  # roll, pitch, yaw
        self._target_pose = self.rng.uniform(0, 120, size=5)

    def read_flex_angles(self) -> np.ndarray:
        """
        Returns shape (5,) array of finger angles in degrees.
        Index: 0=thumb, 1=index, 2=middle, 3=ring, 4=pinky.
        """
        if self.mode == "static":
            return self._current_pose.copy()

        elif self.mode == "noisy":
            # ~±5° noise (realistic for cheap flex sensors + ADC)
            noise = self.rng.normal(0, 2.5, size=5)
            return np.clip(self._current_pose + noise, 0, 120)

        elif self.mode == "animated":
            # Drift pose slowly toward a random target
            diff = self._target_pose - self._current_pose
            self._current_pose += diff * 0.02

            # Pick a new target when close enough
            if np.max(np.abs(diff)) < 5.0:
                self._target_pose = self.rng.uniform(0, 120, size=5)

            return self._current_pose.copy()

        return self._current_pose.copy()

    def read_imu(self) -> dict:
        """Returns roll, pitch, yaw in degrees."""
        # MPU-6050 noise floor ~0.5°
        noise = self.rng.normal(0, 0.5, size=3)
        return {
            "roll":  float(self._imu_state[0] + noise[0]),
            "pitch": float(self._imu_state[1] + noise[1]),
            "yaw":   float(self._imu_state[2] + noise[2]),
        }

    def set_pose(self, flex_angles: list, imu: list | None = None):
        """
        Force a specific pose (useful for sign testing).

        Parameters
        ----------
        flex_angles : list of float
            [thumb, index, middle, ring, pinky] in degrees.
        imu : list of float, optional
            [roll, pitch, yaw] in degrees.
        """
        self._current_pose = np.array(flex_angles, dtype=float)
        if imu is not None:
            self._imu_state = np.array(imu, dtype=float)

    def set_mode(self, mode: str):
        """Switch operating mode at runtime."""
        if mode not in self.VALID_MODES:
            raise ValueError(f"Invalid mode '{mode}'. Choose from: {self.VALID_MODES}")
        self.mode = mode
