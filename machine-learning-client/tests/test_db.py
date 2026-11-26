"""Unit tests for database connection utilities."""

from unittest.mock import patch

from pymongo.errors import ConnectionFailure

from db import check_connection


def test_check_connection_success():
    """Verify that a successful database ping returns True."""
    with patch("db.client") as mock_client:
        mock_client.admin.command.return_value = {"ok": 1}

        assert check_connection() is True

        mock_client.admin.command.assert_called_once_with("ping")


def test_check_connection_failure():
    """Verify that a failed database ping returns False."""
    with patch("db.client") as mock_client:
        mock_client.admin.command.side_effect = ConnectionFailure(
            "MongoDB is unavailable"
        )

        assert check_connection() is False

        mock_client.admin.command.assert_called_once_with("ping")
