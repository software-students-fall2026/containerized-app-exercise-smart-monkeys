"""Exercise the downloaded model with real CPU inference, without a webcam."""

from io import BytesIO

from PIL import Image

from model import create_recognizer, recognize_gesture


def test_real_model_rejects_blank_image():
    """A blank JPEG should not be classified as a player's move."""
    image = BytesIO()
    Image.new("RGB", (128, 128), "white").save(image, format="JPEG")
    with create_recognizer() as recognizer:
        result = recognize_gesture(image.getvalue(), recognizer)
    assert result == {"move": None, "confidence": None}
