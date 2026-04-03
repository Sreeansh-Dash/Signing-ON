# core/ema_filter.py
#
# Exponential Moving Average (EMA) filter for sensor noise reduction.
# Hardware-independent — develop and unit-test on laptop.

import numpy as np


class EMAFilter:
    """
    Exponential Moving Average for sensor noise reduction.

    α = 0.2 is the project default (from reference document).

    Rationale for α = 0.2:
    - Lower α (e.g., 0.05) → smoother but 50+ ms lag on fast gestures
    - Higher α (e.g., 0.5) → responsive but noise bleeds through to sign match
    - At 1 ms poll rate with α=0.2, step response 90% settling time ≈ 10 ms
    - Human finger velocity peaks at ~300°/s for fast signs
    - At 300°/s, 10 ms lag = 3° error — within the 8° dead band. Acceptable.

    Any proposal to set α > 0.4 will cause noise-induced micro-buzzing.
    Any proposal to set α < 0.1 will produce visible lag in haptic response.
    """

    def __init__(self, alpha: float = 0.2, num_channels: int = 8):
        assert 0 < alpha < 1, "Alpha must be strictly between 0 and 1"
        self.alpha = alpha
        self.num_channels = num_channels
        self._state: np.ndarray | None = None  # initialised on first update

    def update(self, raw: list) -> list:
        """
        Apply one EMA step to the raw sensor values.

        Parameters
        ----------
        raw : list of float
            Sensor values, length == num_channels.

        Returns
        -------
        list of float
            Filtered values, same length as input.
        """
        raw_arr = np.array(raw, dtype=float)

        if self._state is None:
            self._state = raw_arr.copy()
            return self._state.tolist()

        self._state = self.alpha * raw_arr + (1 - self.alpha) * self._state
        return self._state.tolist()

    def reset(self):
        """Reset the filter state. Next update() re-initialises from raw."""
        self._state = None

    @property
    def current_state(self) -> list | None:
        """Return the current filtered state, or None if not yet initialised."""
        if self._state is None:
            return None
        return self._state.tolist()
