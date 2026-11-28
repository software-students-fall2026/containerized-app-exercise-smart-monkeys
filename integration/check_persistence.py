"""Verify a test record survives container recreation with the same volume."""

import argparse
import os

from pymongo import MongoClient


def check_persistence(action, marker_id):
    """Write a marker, or verify and remove it after restarting the database."""
    with MongoClient(os.environ["MONGO_URI"], serverSelectionTimeoutMS=5000) as client:
        collection = client.get_default_database()["_infrastructure_checks"]
        marker = {"_id": marker_id, "purpose": "compose-persistence"}
        if action == "write":
            collection.insert_one(marker)
            print("Persistence marker saved")
        else:
            assert (
                collection.find_one({"_id": marker_id}) == marker
            ), "Persistence marker missing or changed after restart"
            collection.delete_one({"_id": marker_id})
            print("PASS: data survived restart; test marker removed")


def main():
    """Run against the disposable test database supplied through MONGO_URI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["write", "verify"])
    parser.add_argument("marker_id")
    args = parser.parse_args()
    check_persistence(args.action, args.marker_id)


if __name__ == "__main__":
    main()
