"""Unit tests for web application database operations."""

from datetime import timezone
from unittest.mock import patch
from uuid import UUID

from pymongo.errors import ConnectionFailure
import pytest

from web_db import (
    check_connection,
    get_collection,
    create_round_document,
    store_round,
    get_round,
)


def test_check_connection_success():
    """Verify successful MongoDB connectivity."""
    with patch("web_db.mongo_client") as mock_client:
        mock_client.admin.command.return_value = {"ok": 1}

        assert check_connection() is True
        mock_client.admin.command.assert_called_once_with("ping")


def test_check_connection_failure():
    """Verify handling of MongoDB connection failures."""
    with patch("web_db.mongo_client") as mock_client:
        mock_client.admin.command.side_effect = ConnectionFailure()

        assert check_connection() is False
        mock_client.admin.command.assert_called_once_with("ping")


def test_get_collection():
    """Verify retrieval of the rounds collection."""
    with patch("web_db.mongo_client") as mock_client:
        database = mock_client.get_default_database.return_value
        collection = database.__getitem__.return_value

        assert get_collection() is collection

        mock_client.get_default_database.assert_called_once_with()
        database.__getitem__.assert_called_once_with("rounds")


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

    with patch("web_db.mongo_client") as mock_client:
        database = mock_client.get_default_database.return_value
        collection = database.__getitem__.return_value

        store_round(document)

        mock_client.get_default_database.assert_called_once_with()
        database.__getitem__.assert_called_once_with("rounds")
        collection.insert_one.assert_called_once_with(document)


def test_get_round_success():
    """Verify retrieval of an existing round without image data."""
    document = {
        "_id": "round-123",
        "status": "completed",
        "player_move": "rock",
        "computer_move": "scissors",
        "outcome": "win",
    }

    with patch("web_db.get_collection") as mock_get_collection:
        collection = mock_get_collection.return_value
        collection.find_one.return_value = document

        assert get_round("round-123") == document

        collection.find_one.assert_called_once_with(
            {"_id": "round-123"},
            {"image": 0},
        )


def test_get_round_not_found():
    """Verify that a nonexistent round returns None."""
    with patch("web_db.get_collection") as mock_get_collection:
        collection = mock_get_collection.return_value
        collection.find_one.return_value = None

        assert get_round("nonexistent-id") is None

        collection.find_one.assert_called_once_with(
            {"_id": "nonexistent-id"},
            {"image": 0},
        )


def test_get_round_database_failure():
    """Verify that database retrieval errors propagate."""
    with patch("web_db.get_collection") as mock_get_collection:
        collection = mock_get_collection.return_value
        collection.find_one.side_effect = ConnectionFailure("Database unavailable")

        with pytest.raises(ConnectionFailure):
            get_round("round-123")
