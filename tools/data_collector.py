# tools/data_collector.py
#
# Run on laptop connected to ESP32-S3 via Serial (115200 baud) to stream
# sensor data to a CSV file for TFLite training.
#
# Serial output format (one line per 10 ms):
# DATA:FLEX0,FLEX1,FLEX2,FLEX3,FLEX4,ROLL,PITCH,YAW,TIMESTAMP_MS
#
# Usage: python tools/data_collector.py --port COM3 --sign A --duration 30

import csv
import time
import os
import argparse


def collect(port: str, sign_label: str, duration_s: int, output_dir: str = "ml/data/real/"):
    """
    Collect sensor data from ESP32-S3 over serial.

    Requires pyserial and a connected ESP32-S3 with the data-streaming
    firmware loaded. Saves output as CSV for ML training.
    """
    import serial

    os.makedirs(output_dir, exist_ok=True)
    sign_id = ord(sign_label.upper()) - ord("A")
    out_path = os.path.join(output_dir, f"sign_{sign_label}_{int(time.time())}.csv")

    with serial.Serial(port, 115200, timeout=1) as ser, open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "sign_id", "flex_0", "flex_1", "flex_2", "flex_3", "flex_4",
            "imu_roll", "imu_pitch", "imu_yaw", "timestamp_ms",
        ])
        print(f"Collecting sign '{sign_label}' (ID={sign_id}) for {duration_s}s → {out_path}")
        print("Waiting for DATA: lines from ESP32...")

        start = time.time()
        count = 0
        while (time.time() - start) < duration_s:
            line = ser.readline().decode("utf-8", errors="ignore").strip()
            if line.startswith("DATA:"):
                parts = line[5:].split(",")
                if len(parts) == 9:
                    writer.writerow([sign_id] + parts)
                    count += 1
                    if count % 100 == 0:
                        elapsed = time.time() - start
                        print(f"  {count} samples collected ({elapsed:.1f}s / {duration_s}s)")

    print(f"Collection complete: {count} samples → {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Collect sensor data from ESP32-S3")
    parser.add_argument("--port", required=True, help="Serial port (e.g., COM3 or /dev/ttyUSB0)")
    parser.add_argument("--sign", required=True, help="ISL letter A-Z")
    parser.add_argument("--duration", type=int, default=30, help="Collection duration in seconds")
    parser.add_argument("--output", default="ml/data/real/", help="Output directory")
    args = parser.parse_args()

    collect(args.port, args.sign, args.duration, args.output)
