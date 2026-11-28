"""Unit tests for machine learning database operations."""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from pymongo import ReturnDocument
from pymongo.errors import ConnectionFailure

from ml_db import (
    check_connection,
    get_collection,
    claim_next_round,
    complete_round,
    invalidate_round,
    fail_round,
)


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


def test_complete_round_success():
    """Verify that successful game results are stored correctly."""
    finished_at = datetime(2026, 11, 27, 12, 0, tzinfo=timezone.utc)

    with (
        patch("ml_db.get_collection") as mock_get_collection,
        patch("ml_db.datetime") as mock_datetime,
    ):
        mock_datetime.now.return_value = finished_at

        collection = mock_get_collection.return_value
        collection.update_one.return_value.modified_count = 1

        assert complete_round("round-1", "rock", "scissors", 0.95, "win") is True

        collection.update_one.assert_called_once_with(
            {"_id": "round-1", "status": "processing"},
            {
                "$set": {
                    "status": "completed",
                    "player_move": "rock",
                    "computer_move": "scissors",
                    "confidence": 0.95,
                    "outcome": "win",
                    "error": None,
                    "finished_at": finished_at,
                },
                "$unset": {"image": ""},
            },
        )

        mock_datetime.now.assert_called_once_with(timezone.utc)


def test_complete_round_no_match():
    """Verify behavior when no processing round matches the ID."""
    with patch("ml_db.get_collection") as mock_get_collection:
        collection = mock_get_collection.return_value
        collection.update_one.return_value.modified_count = 0

        assert complete_round("round-1", "rock", "scissors", 0.95, "win") is False


def test_complete_round_database_failure():
    """Verify that database failures propagate to the worker."""
    with patch("ml_db.get_collection") as mock_get_collection:
        collection = mock_get_collection.return_value
        collection.update_one.side_effect = ConnectionFailure("MongoDB is unavailable")

        with pytest.raises(ConnectionFailure):
            complete_round("round-1", "rock", "scissors", 0.95, "win")


@pytest.mark.parametrize(
    "finish_round, status, error",
    [
        (invalidate_round, "invalid", "No valid gesture detected"),
        (fail_round, "failed", "Gesture processing failed"),
    ],
)
def test_unsuccessful_round_update(finish_round, status, error):
    """Verify that unsuccessful rounds are stored correctly."""
    finished_at = datetime(2026, 11, 27, 12, 0, tzinfo=timezone.utc)

    with (
        patch("ml_db.get_collection") as mock_get_collection,
        patch("ml_db.datetime") as mock_datetime,
    ):
        mock_datetime.now.return_value = finished_at
        collection = mock_get_collection.return_value
        collection.update_one.return_value.modified_count = 1

        assert finish_round("round-1", error) is True

        expected_fields = dict.fromkeys(
            ("player_move", "computer_move", "confidence", "outcome")
        )
        expected_fields.update(
            status=status,
            error=error,
            finished_at=finished_at,
        )

        collection.update_one.assert_called_once_with(
            {"_id": "round-1", "status": "processing"},
            {
                "$set": expected_fields,
                "$unset": {"image": ""},
            },
        )

        mock_datetime.now.assert_called_once_with(timezone.utc)


@pytest.mark.parametrize(
    "finish_round",
    [invalidate_round, fail_round],
)
def test_unsuccessful_round_no_match(finish_round):
    """Verify behavior when no processing round matches."""
    with patch("ml_db.get_collection") as mock_get_collection:
        collection = mock_get_collection.return_value
        collection.update_one.return_value.modified_count = 0

        assert finish_round("round-1", "Test error") is False


@pytest.mark.parametrize(
    "finish_round",
    [invalidate_round, fail_round],
)
def test_unsuccessful_round_database_failure(finish_round):
    """Verify that database failures propagate to the worker."""
    with patch("ml_db.get_collection") as mock_get_collection:
        collection = mock_get_collection.return_value
        collection.update_one.side_effect = ConnectionFailure("MongoDB is unavailable")

        with pytest.raises(ConnectionFailure):
            finish_round("round-1", "Test error")
