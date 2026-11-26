"""Database connection utilities for the machine learning client."""

import os

from pymongo import MongoClient
from pymongo.errors import PyMongoError

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/monkeymoves")


client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)

db = client["monkeymoves"]

rounds = db["rounds"]


def check_connection():
    """Check whether MongoDB is reachable."""
    try:
        client.admin.command("ping")
        return True
    except PyMongoError:
        return False
