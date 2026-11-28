"""Database connection utilities for the machine learning client."""

import os
from datetime import datetime, timezone

from pymongo import MongoClient, ReturnDocument
from pymongo.errors import PyMongoError

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/monkeymoves")

mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)


def get_collection():
    """Return the MongoDB rounds collection."""
    database = mongo_client.get_default_database()
    return database["rounds"]


def check_connection():
    """Check whether MongoDB is reachable."""
    try:
        mongo_client.admin.command("ping")
        return True
    except PyMongoError:
        return False


def claim_next_round():
    """Atomically claim the oldest pending game round."""
    return get_collection().find_one_and_update(
        {"status": "pending"},
        {"$set": {"status": "processing"}},
        sort=[("created_at", 1)],
        return_document=ReturnDocument.AFTER,
    )


def complete_round(round_id, player_move, computer_move, confidence, outcome):
    """Save the results of a successfully processed game round."""
    result = get_collection().update_one(
        {"_id": round_id, "status": "processing"},
        {
            "$set": {
                "status": "completed",
                "player_move": player_move,
                "computer_move": computer_move,
                "confidence": confidence,
                "outcome": outcome,
                "error": None,
                "finished_at": datetime.now(timezone.utc),
            },
            "$unset": {"image": ""},
        },
    )

    return result.modified_count == 1


def _finish_unsuccessful_round(round_id, status, error):
    """Save an unsuccessful round and remove its image."""
    result = get_collection().update_one(
        {"_id": round_id, "status": "processing"},
        {
            "$set": {
                "status": status,
                "player_move": None,
                "computer_move": None,
                "confidence": None,
                "outcome": None,
                "error": error,
                "finished_at": datetime.now(timezone.utc),
            },
            "$unset": {"image": ""},
        },
    )

    return result.modified_count == 1


def invalidate_round(round_id, error):
    """Mark a round as invalid when no usable gesture is recognized."""
    return _finish_unsuccessful_round(round_id, "invalid", error)


def fail_round(round_id, error):
    """Mark a round as failed due to an unexpected processing error."""
    return _finish_unsuccessful_round(round_id, "failed", error)
