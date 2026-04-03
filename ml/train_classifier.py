# ml/train_classifier.py
#
# TinyML gesture classifier training pipeline.
# Target: TensorFlow Lite for Microcontrollers
# Input:  8 features (5 flex + 3 IMU)
# Output: 26 classes (ISL A–Z)
#
# ESP32-S3 constraints on the model:
#   - Max model size: ~200 KB (fits in PSRAM, not internal SRAM)
#   - Tensor arena: ~96 KB (tune with minimal_arena_checker)
#   - Inference time target: < 5 ms (leaves headroom in 10 ms signMatchTask)
#
# NOTE: This script requires TensorFlow which may not be compatible with
# Python 3.13. If TF is not available, a scikit-learn fallback is provided
# for pipeline validation purposes.
#
# Usage: python ml/train_classifier.py

import os
import sys
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, confusion_matrix

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Feature columns
FEATURE_COLS = ["flex_0", "flex_1", "flex_2", "flex_3", "flex_4",
                "imu_roll", "imu_pitch", "imu_yaw"]


def load_dataset(csv_path: str = "ml/data/synthetic_train.csv"):
    """Load and split dataset into train/test sets."""
    df = pd.read_csv(csv_path)
    X = df[FEATURE_COLS].values.astype(np.float32)
    y = df["label"].values.astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"Dataset: {len(X_train)} train, {len(X_test)} test, {len(np.unique(y))} classes")
    return X_train, X_test, y_train, y_test


def try_tensorflow_pipeline(X_train, X_test, y_train, y_test, num_classes=26):
    """
    TensorFlow/Keras training + TFLite conversion.

    Returns True if successful, False if TF is not available.
    """
    try:
        import tensorflow as tf
        print(f"TensorFlow {tf.__version__} found. Training Keras model...")
    except ImportError:
        print("TensorFlow not available (likely Python 3.13 incompatibility).")
        print("Falling back to scikit-learn pipeline for validation.")
        return False

    # Build dense MLP classifier
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(8,)),
        tf.keras.layers.Dense(64, activation="relu"),
        tf.keras.layers.BatchNormalization(),
        tf.keras.layers.Dropout(0.3),
        tf.keras.layers.Dense(32, activation="relu"),
        tf.keras.layers.Dropout(0.2),
        tf.keras.layers.Dense(num_classes, activation="softmax"),
    ])

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )

    model.summary()

    # Train
    history = model.fit(
        X_train, y_train,
        validation_split=0.15,
        epochs=50,
        batch_size=64,
        verbose=1,
        callbacks=[
            tf.keras.callbacks.EarlyStopping(
                patience=5, restore_best_weights=True, monitor="val_accuracy"
            )
        ],
    )

    # Evaluate
    loss, accuracy = model.evaluate(X_test, y_test, verbose=0)
    print(f"\nTest accuracy: {accuracy * 100:.2f}%")
    print(f"Test loss: {loss:.4f}")

    # Predictions for confusion matrix
    y_pred = np.argmax(model.predict(X_test, verbose=0), axis=1)
    labels = [chr(i + ord("A")) for i in range(num_classes)]
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=labels, zero_division=0))

    # Convert to TFLite with int8 quantisation
    output_path = "ml/model/gesture_classifier.tflite"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]

    # Representative dataset for full integer quantisation
    def representative_data_gen():
        for i in range(min(100, len(X_train))):
            yield [X_train[i : i + 1]]

    converter.representative_dataset = representative_data_gen
    converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    converter.inference_input_type = tf.int8
    converter.inference_output_type = tf.int8

    tflite_model = converter.convert()
    with open(output_path, "wb") as f:
        f.write(tflite_model)

    size_kb = len(tflite_model) / 1024
    print(f"\nTFLite model saved: {output_path} ({size_kb:.1f} KB)")
    if size_kb < 200:
        print(f"✓ Model size ({size_kb:.1f} KB) fits within ESP32-S3 PSRAM limit (200 KB)")
    else:
        print(f"⚠ Model size ({size_kb:.1f} KB) exceeds 200 KB target — consider pruning")

    return True


def sklearn_fallback_pipeline(X_train, X_test, y_train, y_test, num_classes=26):
    """
    Scikit-learn MLP fallback when TensorFlow is not available.

    This validates the data pipeline and feature separability.
    The actual TFLite model will need TF (use Python 3.11/3.12 or Colab).
    """
    from sklearn.neural_network import MLPClassifier
    from sklearn.preprocessing import StandardScaler

    print("\n--- Scikit-learn MLP Fallback Pipeline ---")

    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Train MLP with similar architecture to the Keras model
    clf = MLPClassifier(
        hidden_layer_sizes=(64, 32),
        activation="relu",
        max_iter=200,
        random_state=42,
        early_stopping=True,
        validation_fraction=0.15,
        verbose=True,
    )
    clf.fit(X_train_scaled, y_train)

    # Evaluate
    accuracy = clf.score(X_test_scaled, y_test)
    y_pred = clf.predict(X_test_scaled)
    print(f"\nTest accuracy: {accuracy * 100:.2f}%")

    labels = [chr(i + ord("A")) for i in range(num_classes)]
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=labels, zero_division=0))

    # Confusion matrix for similar pairs
    cm = confusion_matrix(y_test, y_pred)
    similar_pairs = [
        ("M", "N"), ("D", "G"), ("U", "V"), ("R", "H"),
        ("A", "S"), ("G", "Q"), ("L", "P"),
    ]
    print("\nConfusion pairs of interest (for paper):")
    for a, b in similar_pairs:
        i, j = ord(a) - ord("A"), ord(b) - ord("A")
        print(f"  {a} vs {b}: {cm[i][j]} misclassified as {b}, {cm[j][i]} misclassified as {a}")

    print("\n--- Fallback pipeline complete ---")
    print("NOTE: For TFLite conversion, re-run with Python 3.11/3.12 or use Google Colab.")


def main():
    # Check if dataset exists
    csv_path = "ml/data/synthetic_train.csv"
    if not os.path.exists(csv_path):
        print(f"Dataset not found at {csv_path}. Generating...")
        from ml.generate_synthetic_dataset import SyntheticDataGenerator

        if not os.path.exists("data/signs/isl_a.json"):
            from tools.generate_sign_library import generate_library
            generate_library()

        gen = SyntheticDataGenerator("data/signs/", samples_per_sign=500)
        gen.generate(csv_path)

    # Load data
    X_train, X_test, y_train, y_test = load_dataset(csv_path)

    # Try TensorFlow first, fall back to scikit-learn
    if not try_tensorflow_pipeline(X_train, X_test, y_train, y_test):
        sklearn_fallback_pipeline(X_train, X_test, y_train, y_test)


if __name__ == "__main__":
    main()
