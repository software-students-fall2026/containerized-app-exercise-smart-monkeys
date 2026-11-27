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
