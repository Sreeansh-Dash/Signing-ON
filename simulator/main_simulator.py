# simulator/main_simulator.py
#
# Entry point: python simulator/main_simulator.py
# Renders a real-time text UI showing sensor state, match result, and haptic output.
#
# Usage:
#   python simulator/main_simulator.py --sign B --mode noisy --duration 10

import time
import sys
import os
import argparse

# Add project root to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulator.mock_sensor_hal import MockSensorHAL
from core.ema_filter import EMAFilter
from core.sign_matcher import SignMatcher
from core.haptic_engine import HapticEngine


def run_simulation(
    target_sign_label: str = "B",
    duration_seconds: float = 10.0,
    sensor_mode: str = "animated",
):
    """
    Simulates the full glove pipeline without hardware.

    Modes:
    - 'animated': random pose exploration (shows haptic guidance in action)
    - 'noisy': fixed pose with noise (tests EMA filter + dead-band)
    - 'static': perfect pose (should produce all-zero duties immediately)
    """
    print(f"\n{'=' * 65}")
    print(f"  Glove Simulator — Target: ISL {target_sign_label.upper()}")
    print(f"  Mode: {sensor_mode} | Duration: {duration_seconds}s")
    print(f"{'=' * 65}\n")

    # --- Initialise all modules ---
    sensor = MockSensorHAL(mode=sensor_mode)
    ema = EMAFilter(alpha=0.2, num_channels=8)
    matcher = SignMatcher(sign_library_path="data/signs/")
    haptic = HapticEngine(version="1.0")

    sign_id = ord(target_sign_label.upper()) - ord("A")
    matcher.set_target_sign(sign_id)

    # Print target sign info
    sign = matcher.signs[sign_id]
    target_str = " ".join(f"{a:5.1f}°" for a in sign["target_angles"])
    print(f"  Target angles: [{target_str}]")
    print(f"  Tolerance: ±{sign['tolerance_band']}° | IMU tolerance: ±{sign['imu_tolerance']}°")
    print(f"  Notes: {sign.get('notes', 'N/A')}")
    print(f"\n  {'─' * 60}")
    print(f"  {'Finger Angles':^35}  →  {'Haptic Output':^25}")
    print(f"  {'─' * 60}\n")

    start = time.time()
    iteration = 0
    match_count = 0
    total_checks = 0

    try:
        while (time.time() - start) < duration_seconds:
            # --- sensorTask equivalent (1 ms) ---
            raw_flex = sensor.read_flex_angles().tolist()
            raw_imu_dict = sensor.read_imu()
            raw_imu = [raw_imu_dict["roll"], raw_imu_dict["pitch"], raw_imu_dict["yaw"]]
            filtered = ema.update(raw_flex + raw_imu)
            filtered_flex = filtered[:5]
            filtered_imu = {"roll": filtered[5], "pitch": filtered[6], "yaw": filtered[7]}

            # --- signMatchTask equivalent (10 ms — run every 10 iterations) ---
            if iteration % 10 == 0:
                result = matcher.compute_match(filtered_flex, filtered_imu)
                if result:
                    state = haptic.compute_haptic_state(result)
                    haptic_str = haptic.render_to_pwm_string(state)
                    total_checks += 1
                    if result.all_correct:
                        match_count += 1

                    # Real-time display
                    angles_str = " ".join(f"{a:5.1f}°" for a in filtered_flex)
                    rms_str = f"RMS:{result.error_magnitude:5.1f}°"
                    print(
                        f"\r  [{angles_str}]  →  {haptic_str}  {rms_str}   ",
                        end="",
                        flush=True,
                    )

            iteration += 1
            time.sleep(0.001)  # 1 ms

    except KeyboardInterrupt:
        print("\n\n  Simulation interrupted by user.")

    # --- Summary ---
    elapsed = time.time() - start
    print(f"\n\n  {'─' * 60}")
    print(f"  Simulation Summary")
    print(f"  {'─' * 60}")
    print(f"  Total iterations:     {iteration}")
    print(f"  Elapsed time:         {elapsed:.2f}s")
    print(f"  Match checks:         {total_checks}")
    if total_checks > 0:
        print(f"  Correct matches:      {match_count} / {total_checks} ({match_count/total_checks*100:.1f}%)")
    print(f"  Effective loop rate:  {iteration/elapsed:.0f} Hz")
    print(f"  {'─' * 60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Glove Simulator — No Hardware Required")
    parser.add_argument("--sign", default="B", help="Target ISL letter A-Z")
    parser.add_argument(
        "--mode",
        default="animated",
        choices=["static", "noisy", "animated"],
        help="Sensor simulation mode",
    )
    parser.add_argument("--duration", type=float, default=10.0, help="Duration in seconds")
    args = parser.parse_args()

    # Generate sign library if it doesn't exist
    if not os.path.exists("data/signs/isl_a.json"):
        print("  Sign library not found — generating...")
        from tools.generate_sign_library import generate_library
        generate_library()

    run_simulation(args.sign, args.duration, args.mode)
