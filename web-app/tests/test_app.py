"""Unit tests for the MonkeyMoves Flask application."""

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


def test_homepage_and_assets():
    """Serve the camera page and its assets even when the database is offline."""
    with patch("app.check_connection", return_value=False):
        with app.test_client() as client:
            response = client.get("/")
            assert response.status_code == 200
            assert response.mimetype == "text/html"
            assert b'id="webcam"' in response.data
            for path in ("/static/camera.js", "/static/style.css"):
                assert path.encode() in response.data
                assert client.get(path).status_code == 200
