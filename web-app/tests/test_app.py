"""Unit tests for the MonkeyMoves Flask application."""

from io import BytesIO
from unittest.mock import patch

from PIL import Image
from pymongo.errors import ConnectionFailure

from app import app, MAX_IMAGE_SIZE


def test_health_success():
    """Verify health response when MongoDB is available."""
    with patch("app.mongo_client") as mock_client:
        mock_client.admin.command.return_value = {"ok": 1}

        with app.test_client() as client:
            response = client.get("/health")

            assert response.status_code == 200
            assert response.get_json() == {"status": "ok"}

        mock_client.admin.command.assert_called_once_with("ping")


def test_health_database_unavailable():
    """Verify health response when MongoDB is unavailable."""
    with patch("app.mongo_client") as mock_client:
        mock_client.admin.command.side_effect = ConnectionFailure()

        with app.test_client() as client:
            response = client.get("/health")

            assert response.status_code == 503
            assert response.get_json() == {"status": "unavailable"}


def test_submit_round_missing_image():
    """Reject requests without an image."""
    with app.test_client() as client:
        response = client.post("/api/rounds")

        assert response.status_code == 400
        assert response.get_json() == {"error": "Image is required"}


def test_submit_round_empty_filename():
    """Reject uploads without a filename."""
    with app.test_client() as client:
        response = client.post(
            "/api/rounds",
            data={"image": (BytesIO(b""), "")},
            content_type="multipart/form-data",
        )

        assert response.status_code == 400


def test_submit_round_non_jpeg():
    """Reject images that are not JPEG files."""
    image = BytesIO()
    Image.new("RGB", (10, 10)).save(image, format="PNG")
    image.seek(0)

    with app.test_client() as client:
        response = client.post(
            "/api/rounds",
            data={"image": (image, "photo.png")},
            content_type="multipart/form-data",
        )

        assert response.status_code == 400
        assert response.get_json() == {
            "error": "Only JPEG images are accepted"
        }


def test_submit_round_corrupted_jpeg():
    """Reject invalid JPEG content."""
    with app.test_client() as client:
        response = client.post(
            "/api/rounds",
            data={
                "image": (BytesIO(b"not a real image"), "photo.jpg")
            },
            content_type="multipart/form-data",
        )

        assert response.status_code == 400
        assert response.get_json() == {
            "error": "Invalid JPEG image"
        }


def test_submit_round_oversized_image():
    """Reject images exceeding the maximum upload size."""
    image = BytesIO(b"x" * (MAX_IMAGE_SIZE + 1))

    with app.test_client() as client:
        response = client.post(
            "/api/rounds",
            data={"image": (image, "large.jpg")},
            content_type="multipart/form-data",
        )

        assert response.status_code == 413
        assert response.get_json() == {
            "error": "Image exceeds 1 MiB limit"
        }


def test_submit_round_valid_jpeg():
    """Verify that a valid JPEG passes image validation."""
    image = BytesIO()
    Image.new("RGB", (10, 10)).save(image, format="JPEG")
    image.seek(0)

    with app.test_client() as client:
        response = client.post(
            "/api/rounds",
            data={"image": (image, "photo.jpg")},
            content_type="multipart/form-data",
        )

        assert response.status_code == 501
        assert response.get_json() == {
            "error": "Submission not yet implemented"
        }