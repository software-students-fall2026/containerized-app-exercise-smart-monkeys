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


def test_no_hand():
    """Verify that images without detected hands are rejected."""
    recognizer = make_recognizer([], hand_count=0)

    result = recognize_gesture(make_image_bytes(), recognizer)

    assert result == {
        "move": None,
        "confidence": None,
    }


def test_multiple_hands():
    """Verify that images with multiple detected hands are rejected."""
    recognizer = make_recognizer(
        [
            [make_category("Closed_Fist", 0.95)],
            [make_category("Victory", 0.92)],
        ],
        hand_count=2,
    )

    result = recognize_gesture(make_image_bytes(), recognizer)

    assert result == {
        "move": None,
        "confidence": None,
    }


def test_missing_gestures():
    """Verify that missing gesture predictions are handled."""
    recognizer = make_recognizer([], hand_count=1)

    result = recognize_gesture(make_image_bytes(), recognizer)

    assert result["move"] is None
    assert result["confidence"] is None


def test_empty_gesture_categories():
    """Verify that empty gesture categories are handled."""
    recognizer = make_recognizer([[]])

    result = recognize_gesture(make_image_bytes(), recognizer)

    assert result["move"] is None
    assert result["confidence"] is None


def test_invalid_image():
    """Verify that corrupted image data is rejected."""
    recognizer = Mock()

    result = recognize_gesture(b"invalid image data", recognizer)

    assert result["move"] is None
    assert result["confidence"] is None

    recognizer.recognize.assert_not_called()


def test_non_jpeg_image():
    """Verify that unsupported image formats are rejected."""
    recognizer = Mock()

    result = recognize_gesture(make_image_bytes("PNG"), recognizer)

    assert result["move"] is None
    assert result["confidence"] is None

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
