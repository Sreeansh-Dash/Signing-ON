# ml/generate_synthetic_dataset.py
#
# Generate synthetic training data for the TFLite classifier.
# This data is for pipeline validation only — replace with real
# sensor recordings before training the production model.
#
# Output format: CSV with columns
# [flex_0, flex_1, flex_2, flex_3, flex_4, imu_roll, imu_pitch, imu_yaw, label]
#
# Usage: python ml/generate_synthetic_dataset.py

import os
import sys
import glob
import json

import numpy as np
import pandas as pd

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class SyntheticDataGenerator:
    """
    Generates plausible-looking sensor data for each ISL sign by
    adding controlled noise around the ground-truth target angles.

    This is valid for testing the ML pipeline architecture.
    For a publication-grade model, collect real data from 5+ users
    per the user study protocol in Module 3.
    """

    def __init__(self, sign_library_path: str, samples_per_sign: int = 500):
        self.signs = self._load_signs(sign_library_path)
        self.samples_per_sign = samples_per_sign
        self.rng = np.random.default_rng(42)

    def _load_signs(self, path: str) -> dict:
        signs = {}
        for fp in glob.glob(os.path.join(path, "*.json")):
            with open(fp) as f:
                s = json.load(f)
                signs[s["sign_id"]] = s
        return signs

    def generate(self, output_csv: str = "ml/data/synthetic_train.csv") -> pd.DataFrame:
        """
        Generate synthetic training dataset.

        Returns
        -------
        pd.DataFrame
            DataFrame with 8 feature columns + label column.
        """
        records = []
        for sign_id, sign in self.signs.items():
            target = np.array(sign["target_angles"])
            imu_target = np.array([
                sign["wrist_orientation"]["roll_deg"],
                sign["wrist_orientation"]["pitch_deg"],
                sign["wrist_orientation"]["yaw_deg"],
            ])

            for _ in range(self.samples_per_sign):
                # User variation: ±15° per finger (realistic for novice)
                flex_noise = self.rng.normal(0, 8, size=5)
                imu_noise = self.rng.normal(0, 5, size=3)
                sample_flex = np.clip(target + flex_noise, 0, 120)
                sample_imu = imu_target + imu_noise

                records.append({
                    "flex_0": sample_flex[0],
                    "flex_1": sample_flex[1],
                    "flex_2": sample_flex[2],
                    "flex_3": sample_flex[3],
                    "flex_4": sample_flex[4],
                    "imu_roll": sample_imu[0],
                    "imu_pitch": sample_imu[1],
                    "imu_yaw": sample_imu[2],
                    "label": sign_id,
                })

        df = pd.DataFrame(records).sample(frac=1, random_state=42).reset_index(drop=True)
        os.makedirs(os.path.dirname(output_csv), exist_ok=True)
        df.to_csv(output_csv, index=False)
        print(f"Generated {len(df)} samples across {len(self.signs)} signs → {output_csv}")
        return df


if __name__ == "__main__":
    # Generate sign library if needed
    if not os.path.exists("data/signs/isl_a.json"):
        print("Sign library not found — generating first...")
        from tools.generate_sign_library import generate_library
        generate_library()

    gen = SyntheticDataGenerator("data/signs/", samples_per_sign=500)
    gen.generate()
