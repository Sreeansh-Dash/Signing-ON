# tools/generate_sign_library.py
#
# Generates placeholder JSON files for all 26 ISL fingerspelling letters.
# Target angles are estimates based on ISL handshape descriptions.
# MUST be validated against certified ISL reference material and
# updated during Week 3 of the hardware timeline.
#
# ISL Reference: Vasishta, M., Suresh, M., & Laxmi Narayana, K. (1998).
# "Instant ISL" — the standard reference for ISL fingerspelling shapes.

import json
import os


# [thumb, index, middle, ring, pinky] in degrees
# 0 = fully extended, 120 = fully curled
# These are structured estimates — verify against ISL reference material

ISL_FINGERSPELLING_ANGLES = {
    "A": ([60, 90, 90, 90, 90],   {"roll": 0, "pitch": 0,   "yaw": 90}),
    "B": ([90, 0, 0, 0, 0],       {"roll": 0, "pitch": 0,   "yaw": 90}),
    "C": ([30, 30, 30, 30, 30],   {"roll": 0, "pitch": 10,  "yaw": 90}),
    "D": ([90, 0, 90, 90, 90],    {"roll": 0, "pitch": 0,   "yaw": 90}),
    "E": ([60, 60, 60, 60, 60],   {"roll": 0, "pitch": 0,   "yaw": 90}),
    "F": ([0, 90, 0, 0, 0],       {"roll": 0, "pitch": 0,   "yaw": 90}),
    "G": ([0, 0, 90, 90, 90],     {"roll": 0, "pitch": 90,  "yaw": 0}),
    "H": ([90, 0, 0, 90, 90],     {"roll": 0, "pitch": 90,  "yaw": 0}),
    "I": ([90, 90, 90, 90, 0],    {"roll": 0, "pitch": 0,   "yaw": 90}),
    "J": ([90, 90, 90, 90, 0],    {"roll": 0, "pitch": 0,   "yaw": 90}),   # J is dynamic
    "K": ([0, 0, 0, 90, 90],      {"roll": 0, "pitch": 0,   "yaw": 90}),
    "L": ([0, 0, 90, 90, 90],     {"roll": 0, "pitch": 0,   "yaw": 90}),
    "M": ([90, 90, 90, 90, 90],   {"roll": 0, "pitch": -20, "yaw": 90}),
    "N": ([90, 90, 90, 90, 90],   {"roll": 0, "pitch": 20,  "yaw": 90}),
    "O": ([20, 20, 20, 20, 20],   {"roll": 0, "pitch": 0,   "yaw": 90}),
    "P": ([0, 0, 90, 90, 90],     {"roll": 0, "pitch": -90, "yaw": 0}),
    "Q": ([0, 0, 90, 90, 90],     {"roll": 0, "pitch": 90,  "yaw": 0}),
    "R": ([90, 0, 0, 90, 90],     {"roll": 0, "pitch": 0,   "yaw": 90}),   # crossed fingers
    "S": ([90, 90, 90, 90, 90],   {"roll": 0, "pitch": 0,   "yaw": 90}),   # thumb over fist
    "T": ([30, 90, 90, 90, 90],   {"roll": 0, "pitch": 0,   "yaw": 90}),
    "U": ([90, 0, 0, 90, 90],     {"roll": 0, "pitch": 0,   "yaw": 90}),
    "V": ([90, 0, 0, 90, 90],     {"roll": 0, "pitch": 0,   "yaw": 90}),   # similar to U
    "W": ([90, 0, 0, 0, 90],      {"roll": 0, "pitch": 0,   "yaw": 90}),
    "X": ([90, 45, 90, 90, 90],   {"roll": 0, "pitch": 0,   "yaw": 90}),
    "Y": ([0, 90, 90, 90, 0],     {"roll": 0, "pitch": 0,   "yaw": 90}),
    "Z": ([90, 0, 90, 90, 90],    {"roll": 0, "pitch": 0,   "yaw": 90}),   # dynamic stroke
}

DYNAMIC_SIGNS = {"J", "Z"}

# Notes for specific signs (from ISL reference descriptions)
SIGN_NOTES = {
    "A": "Fist with thumb resting on side. Wrist vertical (yaw ~90°). Distinguished from S by thumb position.",
    "B": "Four fingers extended straight, thumb folded across palm. Wrist upright.",
    "C": "Curved hand, all fingers partially bent ~30°. Slight pitch forward.",
    "D": "Index finger extended, remaining fingers curled. Thumb touches middle finger.",
    "E": "All fingers partially curled ~60°, forming a loose fist.",
    "F": "Index finger curled to touch thumb, remaining three extended.",
    "G": "Thumb and index extended, pointing sideways. Wrist rotated pitch=90°.",
    "H": "Index and middle finger extended, pointing sideways. Thumb curled.",
    "I": "Pinky extended, all other fingers curled.",
    "J": "Like I but with wrist motion (J-stroke). Dynamic sign.",
    "K": "Thumb, index, middle extended. Ring and pinky curled.",
    "L": "Thumb and index extended at right angle. L-shape.",
    "M": "Fist, fingers over thumb. Slight downward pitch.",
    "N": "Fist, fingers over thumb. Slight upward pitch. Distinguished from M by pitch.",
    "O": "All fingers slightly curled to form O shape ~20°.",
    "P": "Like G but hand points down (pitch=-90°).",
    "Q": "Like G but hand points up (pitch=90°).",
    "R": "Index and middle crossed. Thumb curled.",
    "S": "Fist with thumb over fingers. Distinguished from A by thumb position.",
    "T": "Thumb partially extended (~30°), inserted between index and middle.",
    "U": "Index and middle extended together. Thumb curled.",
    "V": "Index and middle extended apart (V-shape). Similar to U but spread.",
    "W": "Index, middle, ring extended. Thumb and pinky curled.",
    "X": "Index finger hooked (~45° bend). All others curled.",
    "Y": "Thumb and pinky extended. Other fingers curled. (Hang loose gesture.)",
    "Z": "Index finger traces Z in air. Dynamic sign with stroke.",
}


def generate_library(output_dir: str = "data/signs/"):
    """Generate 26 ISL sign definition JSON files."""
    os.makedirs(output_dir, exist_ok=True)

    for letter, (angles, imu) in ISL_FINGERSPELLING_ANGLES.items():
        sign = {
            "sign_id": ord(letter) - ord("A"),
            "label": f"ISL_{letter}",
            "target_angles": angles,
            "wrist_orientation": {
                "roll_deg": imu["roll"],
                "pitch_deg": imu["pitch"],
                "yaw_deg": imu["yaw"],
            },
            "tolerance_band": 8.0,
            "imu_tolerance": 15.0,
            "haptic_pattern": "simultaneous",
            "is_dynamic": letter in DYNAMIC_SIGNS,
            "notes": SIGN_NOTES.get(
                letter,
                "PLACEHOLDER — verify against certified ISL reference material before use",
            ),
        }
        path = os.path.join(output_dir, f"isl_{letter.lower()}.json")
        with open(path, "w") as f:
            json.dump(sign, f, indent=2)

    print(f"Generated {len(ISL_FINGERSPELLING_ANGLES)} sign definitions in {output_dir}")


if __name__ == "__main__":
    generate_library()
