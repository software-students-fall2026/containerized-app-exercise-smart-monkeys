"""Download the versioned MediaPipe model used by model.py."""

import hashlib
from pathlib import Path
from urllib.request import urlopen

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/gesture_recognizer/"
    "gesture_recognizer/float16/1/gesture_recognizer.task"
)
MODEL_SHA256 = "97952348cf6a6a4915c2ea1496b4b37ebabc50cbbf80571435643c455f2b0482"
MODEL_PATH = Path(__file__).resolve().parent / "models" / "gesture_recognizer.task"


def download_model():
    """Verify the downloaded bytes before replacing the local model file."""
    with urlopen(MODEL_URL, timeout=30) as response:
        data = response.read()
    if hashlib.sha256(data).hexdigest() != MODEL_SHA256:
        raise ValueError("Model checksum mismatch; existing model was not changed")
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    MODEL_PATH.write_bytes(data)
    return MODEL_PATH


if __name__ == "__main__":
    print(f"Model ready: {download_model()}")
