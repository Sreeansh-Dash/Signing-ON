# core/haptic_engine.py
#
# Translates MatchResult into HapticState (PWM duties + wrist pattern).
# V1.0: finger motors only. V1.1: adds TFLite-informed wrist buzz.

from dataclasses import dataclass
from typing import List

from core.sign_matcher import MatchResult


@dataclass
class HapticState:
    """Output state for the haptic feedback subsystem."""

    duties: List[int]       # 0–255 per finger [thumb, index, middle, ring, pinky]
    wrist_pattern: int      # 0=none, 1=single buzz, 2=double buzz
    all_correct: bool       # True if user's pose is fully correct


class HapticEngine:
    """
    Translates MatchResult into HapticState.

    The 'wrist_pattern' field supports the V1.1 IMU correction signal.

    V1.0: wrist_pattern is always 0 (no IMU feedback)
    V1.1: wrist_pattern = 1 if wrist needs single correction cue
                        = 2 if TFLite classifier confirms wrong sign type
    """

    def __init__(self, version: str = "1.0"):
        if version not in ("1.0", "1.1"):
            raise ValueError(f"Unsupported version: {version}. Use '1.0' or '1.1'.")
        self.version = version
        self._wrist_buzz_state = 0        # tracks double-buzz phase
        self._wrist_buzz_counter = 0

    def compute_haptic_state(
        self, match_result: MatchResult, tflite_prediction: int = 0
    ) -> HapticState:
        """
        Compute haptic output from a match result.

        Parameters
        ----------
        match_result : MatchResult
            Output from SignMatcher.compute_match().
        tflite_prediction : int
            V1.1 only. Predicted sign index from TFLite classifier.
            0 = unknown/idle.

        Returns
        -------
        HapticState
        """
        duties = match_result.motor_duties.copy()

        wrist_pattern = 0
        if self.version == "1.1":
            if match_result.wrist_needs_correction:
                # Single buzz on wrist cue
                wrist_pattern = 1
            if tflite_prediction != 0 and not match_result.all_correct:
                # TFLite says user is forming a different sign entirely
                wrist_pattern = 2

        return HapticState(
            duties=duties,
            wrist_pattern=wrist_pattern,
            all_correct=match_result.all_correct,
        )

    def render_to_pwm_string(self, state: HapticState) -> str:
        """Debug-friendly serialisation of haptic state."""
        fingers = ["T", "I", "M", "R", "P"]
        parts = [f"{f}:{d:3d}" for f, d in zip(fingers, state.duties)]
        wrist_str = f"W:{state.wrist_pattern}" if state.wrist_pattern > 0 else "W:0"
        correct_str = " ✓ ALL CORRECT" if state.all_correct else ""
        return f"[{' | '.join(parts)} | {wrist_str}]{correct_str}"
