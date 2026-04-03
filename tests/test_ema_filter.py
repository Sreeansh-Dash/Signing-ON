# tests/test_ema_filter.py
#
# Unit tests for the EMA filter module.

import pytest
import numpy as np
from core.ema_filter import EMAFilter


class TestEMAFilter:
    """Tests for the Exponential Moving Average filter."""

    def test_init_valid_alpha(self):
        """Alpha must be strictly between 0 and 1."""
        f = EMAFilter(alpha=0.2, num_channels=8)
        assert f.alpha == 0.2
        assert f.num_channels == 8

    def test_init_invalid_alpha_zero(self):
        with pytest.raises(AssertionError):
            EMAFilter(alpha=0)

    def test_init_invalid_alpha_one(self):
        with pytest.raises(AssertionError):
            EMAFilter(alpha=1)

    def test_init_invalid_alpha_negative(self):
        with pytest.raises(AssertionError):
            EMAFilter(alpha=-0.1)

    def test_first_update_returns_raw(self):
        """First call to update() should return the raw input (no smoothing)."""
        f = EMAFilter(alpha=0.2, num_channels=3)
        raw = [10.0, 20.0, 30.0]
        result = f.update(raw)
        assert result == pytest.approx(raw)

    def test_second_update_applies_smoothing(self):
        """Second call should apply EMA formula: α * raw + (1-α) * prev."""
        f = EMAFilter(alpha=0.5, num_channels=1)
        f.update([100.0])
        result = f.update([200.0])
        # EMA: 0.5 * 200 + 0.5 * 100 = 150
        assert result == pytest.approx([150.0])

    def test_step_response_settling(self):
        """
        After a step input, the filter should settle to within ~10% of the
        target after ~10 updates at α=0.2 (90% settling time).
        """
        f = EMAFilter(alpha=0.2, num_channels=1)
        f.update([0.0])  # initialise at 0

        # Step to 100
        for _ in range(20):
            result = f.update([100.0])

        # After 20 iterations at α=0.2, should be very close to 100
        assert abs(result[0] - 100.0) < 2.0

    def test_multi_channel(self):
        """Filter should handle multiple channels independently."""
        f = EMAFilter(alpha=0.5, num_channels=3)
        f.update([0.0, 0.0, 0.0])
        result = f.update([100.0, 200.0, 300.0])
        assert result == pytest.approx([50.0, 100.0, 150.0])

    def test_reset_clears_state(self):
        """After reset, filter should re-initialise from next raw input."""
        f = EMAFilter(alpha=0.2, num_channels=2)
        f.update([100.0, 200.0])
        f.update([100.0, 200.0])

        f.reset()
        assert f.current_state is None

        result = f.update([50.0, 50.0])
        assert result == pytest.approx([50.0, 50.0])

    def test_current_state_property(self):
        """current_state should return the last filtered values."""
        f = EMAFilter(alpha=0.3, num_channels=2)
        assert f.current_state is None

        f.update([10.0, 20.0])
        state = f.current_state
        assert state == pytest.approx([10.0, 20.0])

    def test_noise_reduction(self):
        """
        Filter should reduce noise variance when applied to a noisy signal
        around a constant value.
        """
        rng = np.random.default_rng(42)
        f = EMAFilter(alpha=0.2, num_channels=1)

        # Generate noisy signal around 50.0 with std=10
        raw_values = 50.0 + rng.normal(0, 10, size=100)
        filtered_values = []

        for raw in raw_values:
            result = f.update([float(raw)])
            filtered_values.append(result[0])

        # Filtered signal should have lower variance than raw
        raw_std = np.std(raw_values)
        filtered_std = np.std(filtered_values[20:])  # skip transient
        assert filtered_std < raw_std, (
            f"Filtered std ({filtered_std:.2f}) should be less than raw std ({raw_std:.2f})"
        )
