"""Unit tests for database connection utilities."""

from unittest.mock import patch

from pymongo.errors import ConnectionFailure

from ml_db import check_connection, get_collection


def test_check_connection_success():
    """Verify that a successful database ping returns True."""
    with patch("ml_db.mongo_client") as mock_client:
        mock_client.admin.command.return_value = {"ok": 1}

        assert check_connection() is True

        mock_client.admin.command.assert_called_once_with("ping")


def test_check_connection_failure():
    """Verify that a failed database ping returns False."""
    with patch("ml_db.mongo_client") as mock_client:
        mock_client.admin.command.side_effect = ConnectionFailure(
            "MongoDB is unavailable"
        )

        assert check_connection() is False

        mock_client.admin.command.assert_called_once_with("ping")


def test_get_collection():
    """Verify retrieval of the rounds collection."""
    with patch("ml_db.mongo_client") as mock_client:
        database = mock_client.get_default_database.return_value
        collection = database.__getitem__.return_value

        assert get_collection() is collection
        mock_client.get_default_database.assert_called_once_with()
        database.__getitem__.assert_called_once_with("rounds")
