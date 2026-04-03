# tests/test_haptic_engine.py
#
# Unit tests for the haptic feedback engine.

import pytest
from core.sign_matcher import MatchResult
from core.haptic_engine import HapticEngine, HapticState


def _make_match_result(
    motor_duties=None,
    all_correct=False,
    wrist_needs_correction=False,
    is_match=False,
):
    """Helper to build a MatchResult for testing."""
    return MatchResult(
        is_match=is_match,
        finger_errors=[0.0] * 5,
        imu_errors={"roll": 0.0, "pitch": 0.0, "yaw": 0.0},
        motor_duties=motor_duties or [0] * 5,
        wrist_needs_correction=wrist_needs_correction,
        all_correct=all_correct,
        error_magnitude=0.0,
    )


class TestHapticEngine:
    """Tests for the HapticEngine module."""

    def test_v10_mode_no_wrist_pattern(self):
        """V1.0 mode should always produce wrist_pattern=0."""
        engine = HapticEngine(version="1.0")
        result = _make_match_result(
            motor_duties=[100, 200, 0, 0, 50],
            wrist_needs_correction=True,
        )
        state = engine.compute_haptic_state(result)
        assert state.wrist_pattern == 0
        assert state.duties == [100, 200, 0, 0, 50]

    def test_v11_wrist_correction_single_buzz(self):
        """V1.1: wrist_needs_correction → wrist_pattern=1."""
        engine = HapticEngine(version="1.1")
        result = _make_match_result(wrist_needs_correction=True)
        state = engine.compute_haptic_state(result)
        assert state.wrist_pattern == 1

    def test_v11_tflite_wrong_sign_double_buzz(self):
        """V1.1: TFLite predicts wrong sign → wrist_pattern=2."""
        engine = HapticEngine(version="1.1")
        result = _make_match_result(
            wrist_needs_correction=False,
            all_correct=False,
        )
        state = engine.compute_haptic_state(result, tflite_prediction=5)
        assert state.wrist_pattern == 2

    def test_v11_all_correct_no_wrist_buzz(self):
        """V1.1: if all correct, wrist_pattern should be 0."""
        engine = HapticEngine(version="1.1")
        result = _make_match_result(
            wrist_needs_correction=False,
            all_correct=True,
        )
        state = engine.compute_haptic_state(result, tflite_prediction=5)
        assert state.wrist_pattern == 0

    def test_all_correct_flag_passed_through(self):
        """HapticState should reflect the all_correct flag from MatchResult."""
        engine = HapticEngine(version="1.0")

        result_correct = _make_match_result(all_correct=True)
        state = engine.compute_haptic_state(result_correct)
        assert state.all_correct is True

        result_wrong = _make_match_result(all_correct=False)
        state = engine.compute_haptic_state(result_wrong)
        assert state.all_correct is False

    def test_duties_are_copied_not_referenced(self):
        """Ensure duties in state are a copy, not a reference to the original."""
        engine = HapticEngine(version="1.0")
        original_duties = [10, 20, 30, 40, 50]
        result = _make_match_result(motor_duties=original_duties)
        state = engine.compute_haptic_state(result)

        # Mutate the state and verify original is unaffected
        state.duties[0] = 999
        assert original_duties[0] == 10

    def test_render_to_pwm_string_format(self):
        """PWM string should have correct format."""
        engine = HapticEngine(version="1.0")
        state = HapticState(duties=[0, 128, 255, 0, 64], wrist_pattern=0, all_correct=False)
        s = engine.render_to_pwm_string(state)
        assert "T:  0" in s
        assert "I:128" in s
        assert "M:255" in s
        assert "P: 64" in s
        assert "W:0" in s

    def test_render_all_correct_marker(self):
        """All-correct state should show the ✓ marker."""
        engine = HapticEngine(version="1.0")
        state = HapticState(duties=[0, 0, 0, 0, 0], wrist_pattern=0, all_correct=True)
        s = engine.render_to_pwm_string(state)
        assert "✓ ALL CORRECT" in s

    def test_render_not_correct_no_marker(self):
        """Non-correct state should not show the ✓ marker."""
        engine = HapticEngine(version="1.0")
        state = HapticState(duties=[100, 0, 0, 0, 0], wrist_pattern=0, all_correct=False)
        s = engine.render_to_pwm_string(state)
        assert "✓" not in s

    def test_invalid_version_raises(self):
        """Invalid version string should raise ValueError."""
        with pytest.raises(ValueError):
            HapticEngine(version="2.0")
