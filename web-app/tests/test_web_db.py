"""Unit tests for web application database operations."""

from datetime import timezone
from unittest.mock import patch
from uuid import UUID

import pytest
from pymongo.errors import ConnectionFailure

from web_db import (
    check_connection,
    get_collection,
    create_round_document,
    store_round,
    get_round,
    list_rounds,
    get_stats,
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


def test_list_rounds_success():
    """Verify retrieval of recent rounds."""
    documents = [
        {"_id": "round-2", "status": "completed"},
        {"_id": "round-1", "status": "pending"},
    ]

    with patch("web_db.get_collection") as mock_get_collection:
        collection = mock_get_collection.return_value
        cursor = collection.find.return_value
        sorted_cursor = cursor.sort.return_value
        sorted_cursor.limit.return_value = documents

        assert list_rounds() == documents

        collection.find.assert_called_once_with({}, {"image": 0})
        cursor.sort.assert_called_once_with("created_at", -1)
        sorted_cursor.limit.assert_called_once_with(20)


def test_list_rounds_empty():
    """Verify retrieval when no rounds exist."""
    with patch("web_db.get_collection") as mock_get_collection:
        collection = mock_get_collection.return_value
        collection.find.return_value.sort.return_value.limit.return_value = []

        assert list_rounds() == []


def test_list_rounds_custom_limit():
    """Verify that a custom retrieval limit is applied."""
    with patch("web_db.get_collection") as mock_get_collection:
        collection = mock_get_collection.return_value
        cursor = collection.find.return_value.sort.return_value
        cursor.limit.return_value = []

        assert list_rounds(limit=5) == []
        cursor.limit.assert_called_once_with(5)


def test_list_rounds_database_failure():
    """Verify that database retrieval errors propagate."""
    with patch("web_db.get_collection") as mock_get_collection:
        collection = mock_get_collection.return_value
        collection.find.side_effect = ConnectionFailure("Database unavailable")

        with pytest.raises(ConnectionFailure):
            list_rounds()


def test_get_stats_success():
    """Verify statistics for completed rounds."""
    results = [
        {"_id": "win", "count": 5},
        {"_id": "loss", "count": 3},
        {"_id": "draw", "count": 2},
    ]

    with patch("web_db.get_collection") as mock_get_collection:
        collection = mock_get_collection.return_value
        collection.aggregate.return_value = results

        assert get_stats() == {
            "wins": 5,
            "losses": 3,
            "draws": 2,
            "total": 10,
        }

        collection.aggregate.assert_called_once_with(
            [
                {"$match": {"status": "completed"}},
                {
                    "$group": {
                        "_id": "$outcome",
                        "count": {"$sum": 1},
                    }
                },
            ]
        )


def test_get_stats_empty():
    """Verify statistics when no completed rounds exist."""
    with patch("web_db.get_collection") as mock_get_collection:
        collection = mock_get_collection.return_value
        collection.aggregate.return_value = []

        assert get_stats() == {
            "wins": 0,
            "losses": 0,
            "draws": 0,
            "total": 0,
        }


def test_get_stats_unexpected_outcome():
    """Verify that unexpected outcomes are ignored."""
    results = [
        {"_id": "win", "count": 4},
        {"_id": "unknown", "count": 2},
    ]

    with patch("web_db.get_collection") as mock_get_collection:
        collection = mock_get_collection.return_value
        collection.aggregate.return_value = results

        assert get_stats() == {
            "wins": 4,
            "losses": 0,
            "draws": 0,
            "total": 4,
        }


def test_get_stats_database_failure():
    """Verify that aggregation errors propagate."""
    with patch("web_db.get_collection") as mock_get_collection:
        collection = mock_get_collection.return_value
        collection.aggregate.side_effect = ConnectionFailure("Database unavailable")

        with pytest.raises(ConnectionFailure):
            get_stats()


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


@pytest.mark.parametrize("limit", [0, -1, -20, 2.5, "20", None, True])
def test_list_rounds_invalid_limit(limit):
    """Verify that invalid history limits are rejected."""
    with patch("web_db.get_collection") as mock_get_collection:
        with pytest.raises(ValueError):
            list_rounds(limit)

        mock_get_collection.assert_not_called()
