"""Unit tests for the MonkeyMoves Flask application."""

from datetime import timezone
from io import BytesIO
from unittest.mock import patch
from uuid import UUID

from PIL import Image
from pymongo.errors import ConnectionFailure

from app import app, MAX_IMAGE_SIZE, create_round_document, store_round


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


def test_create_round_document():
    """Verify the initial pending round document."""
    image_data = b"sample image data"
    document = create_round_document(image_data)

    assert document["status"] == "pending"
    assert document["image"] == image_data
    assert document["created_at"].tzinfo == timezone.utc
    assert str(UUID(document["_id"])) == document["_id"]

    assert document["player_move"] is None
    assert document["computer_move"] is None
    assert document["confidence"] is None
    assert document["outcome"] is None
    assert document["error"] is None
    assert document["finished_at"] is None


def test_create_round_unique_ids():
    """Verify that every round receives a unique ID."""
    first_round = create_round_document(b"image one")
    second_round = create_round_document(b"image two")

    assert first_round["_id"] != second_round["_id"]


def test_store_round():
    """Verify that a round is inserted into MongoDB."""
    document = create_round_document(b"sample image")

    with patch("app.mongo_client") as mock_client:
        database = mock_client.get_default_database.return_value
        collection = database.__getitem__.return_value

        store_round(document)

        mock_client.get_default_database.assert_called_once_with()
        database.__getitem__.assert_called_once_with("rounds")
        collection.insert_one.assert_called_once_with(document)


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
        assert response.get_json() == {
            "error": "Database unavailable"
        }

        mock_store.assert_called_once()