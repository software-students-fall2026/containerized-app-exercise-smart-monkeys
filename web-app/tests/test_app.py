"""Unit tests for the MonkeyMoves Flask application."""

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