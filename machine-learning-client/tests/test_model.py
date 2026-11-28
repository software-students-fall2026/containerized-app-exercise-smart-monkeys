"""Unit tests for the MonkeyMoves gesture recognition module."""

from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from PIL import Image

from model import create_recognizer, recognize_gesture


def make_image_bytes(image_format="JPEG"):
    """Create image bytes for testing without external image files."""
    buffer = BytesIO()

    with Image.new("RGB", (100, 100), color="white") as image:
        image.save(buffer, format=image_format)

    return buffer.getvalue()


def make_recognizer(gestures, hand_count=1):
    """Create a mock recognizer with a predetermined result."""
    recognizer = Mock()

    recognizer.recognize.return_value = SimpleNamespace(
        hand_landmarks=[[] for _ in range(hand_count)],
        gestures=gestures,
    )

    return recognizer


def make_category(name, score):
    """Create a simulated MediaPipe gesture category."""
    return SimpleNamespace(
        category_name=name,
        score=score,
    )


def test_create_recognizer():
    """Verify that the recognizer is initialized correctly."""
    with patch("model.vision.GestureRecognizer.create_from_options") as factory:
        result = create_recognizer()

        factory.assert_called_once()
        assert result is factory.return_value


@pytest.mark.parametrize(
    "category, confidence, expected_move",
    [
        ("Closed_Fist", 0.95, "rock"),
        ("Open_Palm", 0.95, "paper"),
        ("Victory", 0.95, "scissors"),
        ("Thumb_Up", 0.95, None),
        ("Victory", 0.40, None),
        ("Closed_Fist", 0.70, "rock"),
    ],
    ids=[
        "rock",
        "paper",
        "scissors",
        "unsupported",
        "low-confidence",
        "confidence-boundary",
    ],
)
def test_gesture_mapping(category, confidence, expected_move):
    """Verify gesture mapping and confidence filtering."""
    recognizer = make_recognizer([[make_category(category, confidence)]])

    result = recognize_gesture(make_image_bytes(), recognizer)

    assert result == {
        "move": expected_move,
        "confidence": confidence,
    }


@pytest.mark.parametrize(
    "gestures, hand_count",
    [
        ([], 0),
        (
            [
                [make_category("Closed_Fist", 0.95)],
                [make_category("Victory", 0.92)],
            ],
            2,
        ),
        ([], 1),
        ([[]], 1),
    ],
    ids=[
        "no-hand",
        "multiple-hands",
        "missing-gestures",
        "empty-categories",
    ],
)
def test_invalid_hand_detection(gestures, hand_count):
    """Verify that unusable hand detections are rejected."""
    recognizer = make_recognizer(gestures, hand_count)

    assert recognize_gesture(make_image_bytes(), recognizer) == {
        "move": None,
        "confidence": None,
    }


@pytest.mark.parametrize(
    "image_bytes",
    [b"invalid image data", make_image_bytes("PNG")],
    ids=["corrupted-image", "unsupported-format"],
)
def test_invalid_image(image_bytes):
    """Verify that invalid images are rejected before inference."""
    recognizer = Mock()

    assert recognize_gesture(image_bytes, recognizer) == {
        "move": None,
        "confidence": None,
    }

    recognizer.recognize.assert_not_called()


def test_highest_confidence_selected():
    """Verify that the highest-confidence prediction is selected."""
    recognizer = make_recognizer(
        [
            [
                make_category("Closed_Fist", 0.75),
                make_category("Victory", 0.95),
            ]
        ]
    )

    result = recognize_gesture(make_image_bytes(), recognizer)

    assert result["move"] == "scissors"
    assert result["confidence"] == 0.95


def test_recognizer_failure():
    """Verify that unexpected inference failures propagate."""
    recognizer = Mock()
    recognizer.recognize.side_effect = RuntimeError("Inference failed")

    with pytest.raises(RuntimeError, match="Inference failed"):
        recognize_gesture(make_image_bytes(), recognizer)
