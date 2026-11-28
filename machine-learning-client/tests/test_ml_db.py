"""Unit tests for machine learning database operations."""

from unittest.mock import patch

import pytest
from pymongo import ReturnDocument
from pymongo.errors import ConnectionFailure

from ml_db import check_connection, get_collection, claim_next_round


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


def test_claim_next_round_success():
    """Verify that the oldest pending round is claimed atomically."""
    document = {
        "_id": "round-1",
        "status": "processing",
        "image": b"test image",
    }

    with patch("ml_db.get_collection") as mock_get_collection:
        collection = mock_get_collection.return_value
        collection.find_one_and_update.return_value = document

        assert claim_next_round() == document

        collection.find_one_and_update.assert_called_once_with(
            {"status": "pending"},
            {"$set": {"status": "processing"}},
            sort=[("created_at", 1)],
            return_document=ReturnDocument.AFTER,
        )


def test_claim_next_round_empty():
    """Verify behavior when no pending rounds exist."""
    with patch("ml_db.get_collection") as mock_get_collection:
        collection = mock_get_collection.return_value
        collection.find_one_and_update.return_value = None

        assert claim_next_round() is None


def test_claim_next_round_database_failure():
    """Verify that database failures propagate to the worker."""
    with patch("ml_db.get_collection") as mock_get_collection:
        collection = mock_get_collection.return_value
        collection.find_one_and_update.side_effect = ConnectionFailure(
            "MongoDB is unavailable"
        )

        with pytest.raises(ConnectionFailure):
            claim_next_round()
