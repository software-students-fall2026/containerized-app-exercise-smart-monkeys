"""Database operations for the MonkeyMoves web application."""

import os
from datetime import datetime, timezone
from uuid import uuid4

from pymongo import MongoClient
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


def create_round_document(image_data):
    """Construct a pending round document."""
    return {
        "_id": str(uuid4()),
        "status": "pending",
        "created_at": datetime.now(timezone.utc),
        "image": image_data,
        "player_move": None,
        "computer_move": None,
        "confidence": None,
        "outcome": None,
        "error": None,
        "finished_at": None,
    }


def store_round(document):
    """Insert a pending round into MongoDB."""
    get_collection().insert_one(document)


def list_rounds(limit=20):
    """Retrieve recent game rounds without image data."""
    return list(
        get_collection().find({}, {"image": 0}).sort("created_at", -1).limit(limit)
    )


def get_stats():
    """Calculate statistics for completed game rounds."""
    pipeline = [
        {"$match": {"status": "completed"}},
        {
            "$group": {
                "_id": "$outcome",
                "count": {"$sum": 1},
            }
        },
    ]

    stats = {
        "wins": 0,
        "losses": 0,
        "draws": 0,
        "total": 0,
    }

    outcome_keys = {
        "win": "wins",
        "loss": "losses",
        "draw": "draws",
    }

    for result in get_collection().aggregate(pipeline):
        key = outcome_keys.get(result["_id"])

        if key is not None:
            stats[key] = result["count"]
            stats["total"] += result["count"]

    return stats


def get_round(round_id):
    """Retrieve an individual round without its image data."""
    return get_collection().find_one(
        {"_id": round_id},
        {"image": 0},
    )
