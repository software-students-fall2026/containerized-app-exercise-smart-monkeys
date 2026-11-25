"""Unit tests for the MonkeyMoves Flask application."""

from io import BytesIO
from unittest.mock import patch

from pymongo.errors import ConnectionFailure

from app import app


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