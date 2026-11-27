"""Unit tests for the MonkeyMoves Flask application."""

from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import patch
from uuid import UUID

from PIL import Image
from pymongo.errors import ConnectionFailure

from app import app, MAX_IMAGE_SIZE


def test_health_success():
    """Verify health response when MongoDB is available."""
    with patch("app.check_connection") as mock_check:
        mock_check.return_value = True

        with app.test_client() as client:
            response = client.get("/health")

            assert response.status_code == 200
            assert response.get_json() == {"status": "ok"}

        mock_check.assert_called_once_with()


def test_health_database_unavailable():
    """Verify health response when MongoDB is unavailable."""
    with patch("app.check_connection") as mock_check:
        mock_check.return_value = False

        with app.test_client() as client:
            response = client.get("/health")

            assert response.status_code == 503
            assert response.get_json() == {"status": "unavailable"}

        mock_check.assert_called_once_with()


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
        assert response.get_json() == {"error": "Only JPEG images are accepted"}


def test_submit_round_corrupted_jpeg():
    """Reject invalid JPEG content."""
    with app.test_client() as client:
        response = client.post(
            "/api/rounds",
            data={"image": (BytesIO(b"not a real image"), "photo.jpg")},
            content_type="multipart/form-data",
        )

        assert response.status_code == 400
        assert response.get_json() == {"error": "Invalid JPEG image"}


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
        assert response.get_json() == {"error": "Image exceeds 1 MiB limit"}


def test_submit_round_valid_jpeg():
    """Verify successful submission of a valid JPEG."""
    image = BytesIO()
    Image.new("RGB", (10, 10)).save(image, format="JPEG")
    image_data = image.getvalue()
    image.seek(0)

    with patch("app.store_round") as mock_store:
        with app.test_client() as client:
            response = client.post(
                "/api/rounds",
                data={"image": (image, "photo.jpg")},
                content_type="multipart/form-data",
            )

        assert response.status_code == 202

        result = response.get_json()

        assert result["status"] == "pending"
        assert str(UUID(result["id"])) == result["id"]

        mock_store.assert_called_once()

        document = mock_store.call_args.args[0]

        assert document["_id"] == result["id"]
        assert document["status"] == "pending"
        assert document["image"] == image_data


def test_submit_round_database_failure():
    """Return 503 when round storage fails."""
    image = BytesIO()
    Image.new("RGB", (10, 10)).save(image, format="JPEG")
    image.seek(0)

    with patch("app.store_round") as mock_store:
        mock_store.side_effect = ConnectionFailure()

        with app.test_client() as client:
            response = client.post(
                "/api/rounds",
                data={"image": (image, "photo.jpg")},
                content_type="multipart/form-data",
            )

        assert response.status_code == 503
        assert response.get_json() == {"error": "Database unavailable"}

        mock_store.assert_called_once()


def test_submit_round_oversized_request():
    """Reject requests exceeding the HTTP upload limit."""
    image = BytesIO(b"x" * (app.config["MAX_CONTENT_LENGTH"] + 1))

    with app.test_client() as client:
        response = client.post(
            "/api/rounds",
            data={"image": (image, "large.jpg")},
            content_type="multipart/form-data",
        )

        assert response.status_code == 413
        assert response.get_json() == {"error": "Request exceeds upload limit"}


def test_retrieve_round_completed():
    """Verify retrieval of a completed round."""
    timestamp = datetime(2026, 11, 27, 12, 0, tzinfo=timezone.utc)

    document = {
        "_id": "round-123",
        "status": "completed",
        "player_move": "rock",
        "computer_move": "scissors",
        "confidence": 0.98,
        "outcome": "win",
        "error": None,
        "created_at": timestamp,
        "finished_at": timestamp,
    }

    with patch("app.get_round", return_value=document) as mock_get:
        with app.test_client() as client:
            response = client.get("/api/rounds/round-123")

        assert response.status_code == 200
        assert response.get_json() == {
            "id": "round-123",
            "status": "completed",
            "player_move": "rock",
            "computer_move": "scissors",
            "confidence": 0.98,
            "outcome": "win",
            "error": None,
            "created_at": "2026-11-27T12:00:00+00:00",
            "finished_at": "2026-11-27T12:00:00+00:00",
        }

        mock_get.assert_called_once_with("round-123")


def test_retrieve_round_pending():
    """Verify retrieval of a pending round."""
    document = {
        "_id": "round-456",
        "status": "pending",
        "created_at": datetime(2026, 11, 27, 12, 0),
    }

    with patch("app.get_round", return_value=document):
        with app.test_client() as client:
            response = client.get("/api/rounds/round-456")

        assert response.status_code == 200

        result = response.get_json()

        assert result["id"] == "round-456"
        assert result["status"] == "pending"
        assert result["player_move"] is None
        assert result["computer_move"] is None
        assert result["confidence"] is None
        assert result["outcome"] is None
        assert result["error"] is None
        assert result["finished_at"] is None
        assert result["created_at"] == "2026-11-27T12:00:00+00:00"


def test_retrieve_round_excludes_image():
    """Ensure binary image data is never exposed."""
    document = {
        "_id": "round-789",
        "status": "pending",
        "image": b"private image data",
    }

    with patch("app.get_round", return_value=document):
        with app.test_client() as client:
            response = client.get("/api/rounds/round-789")

        assert response.status_code == 200
        assert "image" not in response.get_json()
        assert "_id" not in response.get_json()


def test_retrieve_round_not_found():
    """Return 404 when the requested round does not exist."""
    with patch("app.get_round", return_value=None) as mock_get:
        with app.test_client() as client:
            response = client.get("/api/rounds/nonexistent-id")

        assert response.status_code == 404
        assert response.get_json() == {"error": "Round not found"}

        mock_get.assert_called_once_with("nonexistent-id")


def test_retrieve_round_database_failure():
    """Return 503 when round retrieval fails."""
    with patch("app.get_round") as mock_get:
        mock_get.side_effect = ConnectionFailure()

        with app.test_client() as client:
            response = client.get("/api/rounds/round-123")

        assert response.status_code == 503
        assert response.get_json() == {"error": "Database unavailable"}

        mock_get.assert_called_once_with("round-123")
