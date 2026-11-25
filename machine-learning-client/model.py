"""Hand gesture recognition for the MonkeyMoves application."""

from io import BytesIO
from pathlib import Path

import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import vision
from PIL import Image, UnidentifiedImageError

MODEL_PATH = Path(__file__).resolve().parent / "models" / "gesture_recognizer.task"

CONFIDENCE_THRESHOLD = 0.70

GESTURE_MAP = {
    "Closed_Fist": "rock",
    "Open_Palm": "paper",
    "Victory": "scissors",
}


def create_recognizer():
    """Initialize and return the MediaPipe gesture recognizer."""
    options = vision.GestureRecognizerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(MODEL_PATH)),
        running_mode=vision.RunningMode.IMAGE,
        num_hands=2,
        min_hand_detection_confidence=0.3,
        min_hand_presence_confidence=0.3,
    )

    return vision.GestureRecognizer.create_from_options(options)


def recognize_gesture(image_bytes, recognizer):
    """Recognize a valid rock, paper or scissors gesture from JPEG bytes."""
    try:
        with Image.open(BytesIO(image_bytes)) as image:
            if image.format != "JPEG":
                return {"move": None, "confidence": None}

            rgb_image = image.convert("RGB")
            image_array = np.array(rgb_image)

    except (
        UnidentifiedImageError,
        OSError,
        Image.DecompressionBombError,
    ):
        return {"move": None, "confidence": None}

    mp_image = mp.Image(
        image_format=mp.ImageFormat.SRGB,
        data=image_array,
    )

    result = recognizer.recognize(mp_image)

    if len(result.hand_landmarks) != 1 or not result.gestures:
        return {"move": None, "confidence": None}

    if not result.gestures[0]:
        return {"move": None, "confidence": None}

    gesture = max(
        result.gestures[0],
        key=lambda category: category.score,
    )

    confidence = float(gesture.score)
    move = GESTURE_MAP.get(gesture.category_name)

    if confidence < CONFIDENCE_THRESHOLD:
        move = None

    return {
        "move": move,
        "confidence": confidence,
    }
