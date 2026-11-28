"""Database connection utilities for the machine learning client."""

import os

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
