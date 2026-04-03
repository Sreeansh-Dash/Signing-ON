# tests/test_sign_matcher.py
#
# Unit tests for the sign matching engine.

import json
import pytest
from core.sign_matcher import SignMatcher, MatchResult


@pytest.fixture
def matcher(tmp_path):
    """Creates a matcher with a minimal test sign library."""
    sign_b = {
        "sign_id": 1,
        "label": "ISL_B",
        "target_angles": [90, 0, 0, 0, 0],
        "wrist_orientation": {"roll_deg": 0, "pitch_deg": 0, "yaw_deg": 90},
        "tolerance_band": 8.0,
        "imu_tolerance": 15.0,
        "haptic_pattern": "simultaneous",
        "is_dynamic": False,
    }
    (tmp_path / "isl_b.json").write_text(json.dumps(sign_b))

    m = SignMatcher(str(tmp_path))
    m.set_target_sign(1)
    return m


@pytest.fixture
def multi_sign_matcher(tmp_path):
    """Creates a matcher with multiple signs for broader testing."""
    signs = [
        {
            "sign_id": 0, "label": "ISL_A",
            "target_angles": [60, 90, 90, 90, 90],
            "wrist_orientation": {"roll_deg": 0, "pitch_deg": 0, "yaw_deg": 90},
            "tolerance_band": 8.0, "imu_tolerance": 15.0,
            "haptic_pattern": "simultaneous", "is_dynamic": False,
        },
        {
            "sign_id": 1, "label": "ISL_B",
            "target_angles": [90, 0, 0, 0, 0],
            "wrist_orientation": {"roll_deg": 0, "pitch_deg": 0, "yaw_deg": 90},
            "tolerance_band": 8.0, "imu_tolerance": 15.0,
            "haptic_pattern": "simultaneous", "is_dynamic": False,
        },
    ]
    for s in signs:
        (tmp_path / f"isl_{s['label'][-1].lower()}.json").write_text(json.dumps(s))

    return SignMatcher(str(tmp_path))


class TestSignMatcher:
    """Tests for the core sign matching algorithm."""

    def test_perfect_match_produces_zero_duty(self, matcher):
        """When the user's pose exactly matches the target, all duties should be 0."""
        result = matcher.compute_match(
            [90, 0, 0, 0, 0],
            {"roll": 0, "pitch": 0, "yaw": 90},
        )
        assert result.all_correct is True
        assert all(d == 0 for d in result.motor_duties)

    def test_dead_band_threshold(self, matcher):
        """Error of exactly 8° (tolerance) should silence the motor."""
        result = matcher.compute_match(
            [98, 0, 0, 0, 0],  # thumb 8° off
            {"roll": 0, "pitch": 0, "yaw": 90},
        )
        assert result.motor_duties[0] == 0  # within dead band

    def test_just_outside_dead_band(self, matcher):
        """Error of 9° (just outside 8° dead band) should produce small non-zero duty."""
        result = matcher.compute_match(
            [99, 0, 0, 0, 0],  # thumb 9° off
            {"roll": 0, "pitch": 0, "yaw": 90},
        )
        assert result.motor_duties[0] > 0  # outside dead band

    def test_large_error_produces_max_duty(self, matcher):
        """Error of 40° or more should produce duty=255."""
        result = matcher.compute_match(
            [50, 0, 0, 0, 0],  # thumb 40° off (90 - 50 = 40)
            {"roll": 0, "pitch": 0, "yaw": 90},
        )
        assert result.motor_duties[0] == 255

    def test_very_large_error_clamped(self, matcher):
        """Error beyond 40° should still be clamped to duty=255."""
        result = matcher.compute_match(
            [0, 0, 0, 0, 0],  # thumb 90° off
            {"roll": 0, "pitch": 0, "yaw": 90},
        )
        assert result.motor_duties[0] == 255

    def test_imu_mismatch_flagged(self, matcher):
        """IMU error beyond tolerance should flag wrist correction needed."""
        result = matcher.compute_match(
            [90, 0, 0, 0, 0],
            {"roll": 0, "pitch": 0, "yaw": 50},  # yaw 40° off (> 15° tolerance)
        )
        assert result.is_match is True             # fingers correct
        assert result.wrist_needs_correction is True   # but wrist wrong
        assert result.all_correct is False          # overall not correct

    def test_imu_within_tolerance(self, matcher):
        """IMU error within tolerance should not flag wrist correction."""
        result = matcher.compute_match(
            [90, 0, 0, 0, 0],
            {"roll": 5, "pitch": 5, "yaw": 85},  # all within 15°
        )
        assert result.wrist_needs_correction is False
        assert result.all_correct is True

    def test_partial_correction_linear_duty(self, matcher):
        """At 24° error (between 8° and 40°), duty should be ~50%."""
        result = matcher.compute_match(
            [90 + 24, 0, 0, 0, 0],  # thumb 24° off
            {"roll": 0, "pitch": 0, "yaw": 90},
        )
        expected = int((24 - 8) / (40 - 8) * 255)  # ~127
        assert abs(result.motor_duties[0] - expected) <= 2

    def test_no_target_sign_returns_none(self, multi_sign_matcher):
        """If no target sign is set, compute_match should return None."""
        result = multi_sign_matcher.compute_match(
            [50, 50, 50, 50, 50],
            {"roll": 0, "pitch": 0, "yaw": 0},
        )
        assert result is None

    def test_invalid_sign_id_raises(self, multi_sign_matcher):
        """Setting an invalid sign ID should raise ValueError."""
        with pytest.raises(ValueError):
            multi_sign_matcher.set_target_sign(99)

    def test_error_magnitude_calculation(self, matcher):
        """RMS error magnitude should be computed correctly."""
        result = matcher.compute_match(
            [90, 10, 10, 10, 10],  # all 4 non-thumb fingers 10° off
            {"roll": 0, "pitch": 0, "yaw": 90},
        )
        import numpy as np
        expected_rms = float(np.sqrt(np.mean(np.array([0, 10, 10, 10, 10]) ** 2)))
        assert abs(result.error_magnitude - expected_rms) < 0.01

    def test_multiple_fingers_off(self, matcher):
        """Multiple fingers off should produce duties only for off fingers."""
        result = matcher.compute_match(
            [90, 30, 0, 30, 0],  # index and ring 30° off
            {"roll": 0, "pitch": 0, "yaw": 90},
        )
        assert result.motor_duties[0] == 0    # thumb correct
        assert result.motor_duties[1] > 0     # index off
        assert result.motor_duties[2] == 0    # middle correct
        assert result.motor_duties[3] > 0     # ring off
        assert result.motor_duties[4] == 0    # pinky correct

    def test_get_sign_label(self, multi_sign_matcher):
        """Should return correct label for known signs."""
        assert multi_sign_matcher.get_sign_label(0) == "ISL_A"
        assert multi_sign_matcher.get_sign_label(1) == "ISL_B"
        assert "UNKNOWN" in multi_sign_matcher.get_sign_label(99)
