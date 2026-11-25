"""Unit tests for the MonkeyMoves Flask application."""

from app import app


def test_health():
    """Verify that the health endpoint responds successfully."""
    with app.test_client() as client:
        response = client.get("/health")

        assert response.status_code == 200
        assert response.get_json() == {"status": "ok"}
    