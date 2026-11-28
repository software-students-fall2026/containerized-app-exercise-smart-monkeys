"""Unit tests for the background game round worker."""

from unittest.mock import Mock, patch

import pytest
from pymongo.errors import ConnectionFailure

from worker import (
    run_worker,
    POLL_INTERVAL,
    ERROR_RETRY_INTERVAL,
)


def test_worker_processes_pending_round():
    """Verify that a claimed round is passed to the processor."""
    game_round = {"_id": "round-1", "status": "processing"}
    processor = Mock()

    with patch("worker.claim_next_round") as mock_claim:
        mock_claim.side_effect = [
            game_round,
            KeyboardInterrupt(),
        ]

        with pytest.raises(KeyboardInterrupt):
            run_worker(processor)

        processor.assert_called_once_with(game_round)
        assert mock_claim.call_count == 2


def test_worker_waits_when_queue_is_empty():
    """Verify that the worker waits when no rounds are pending."""
    processor = Mock()

    with (
        patch("worker.claim_next_round") as mock_claim,
        patch("worker.time.sleep") as mock_sleep,
    ):
        mock_claim.side_effect = [None, KeyboardInterrupt()]

        with pytest.raises(KeyboardInterrupt):
            run_worker(processor)

        mock_sleep.assert_called_once_with(POLL_INTERVAL)
        processor.assert_not_called()


def test_worker_recovers_from_database_failure():
    """Verify that the worker retries after a database failure."""
    game_round = {"_id": "round-1", "status": "processing"}
    processor = Mock()

    with (
        patch("worker.claim_next_round") as mock_claim,
        patch("worker.time.sleep") as mock_sleep,
        patch("worker.LOGGER") as mock_logger,
    ):
        mock_claim.side_effect = [
            ConnectionFailure("Database unavailable"),
            game_round,
            KeyboardInterrupt(),
        ]

        with pytest.raises(KeyboardInterrupt):
            run_worker(processor)

        mock_sleep.assert_called_once_with(ERROR_RETRY_INTERVAL)
        mock_logger.exception.assert_called_once()
        processor.assert_called_once_with(game_round)
        assert mock_claim.call_count == 3


def test_worker_handles_database_failure_during_processing():
    """Verify retry behavior when processing raises a database error."""
    game_round = {"_id": "round-1", "status": "processing"}
    processor = Mock(side_effect=ConnectionFailure("Update failed"))

    with (
        patch("worker.claim_next_round") as mock_claim,
        patch("worker.time.sleep") as mock_sleep,
        patch("worker.LOGGER") as mock_logger,
    ):
        mock_claim.side_effect = [
            game_round,
            KeyboardInterrupt(),
        ]

        with pytest.raises(KeyboardInterrupt):
            run_worker(processor)

        processor.assert_called_once_with(game_round)
        mock_sleep.assert_called_once_with(ERROR_RETRY_INTERVAL)
        mock_logger.exception.assert_called_once()
