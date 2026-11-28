"""Background worker for processing pending game rounds."""

import logging
import time

from pymongo.errors import PyMongoError

from ml_db import claim_next_round

LOGGER = logging.getLogger(__name__)

POLL_INTERVAL = 1.0
ERROR_RETRY_INTERVAL = 5.0


def run_worker(process_round):
    """Continuously claim and process pending game rounds."""
    while True:
        try:
            game_round = claim_next_round()

            if game_round is None:
                time.sleep(POLL_INTERVAL)
                continue

            process_round(game_round)

        except PyMongoError:
            LOGGER.exception("Database operation failed")
            time.sleep(ERROR_RETRY_INTERVAL)
