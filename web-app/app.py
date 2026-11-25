"""Flask backend for the MonkeyMoves application."""

import os

from flask import Flask, jsonify
from pymongo import MongoClient
from pymongo.errors import PyMongoError

app = Flask(__name__)

MONGO_URI = os.getenv(
    "MONGO_URI", "mongodb://db:27017/monkeymoves"
)

mongo_client = MongoClient(
    MONGO_URI, serverSelectionTimeoutMS=2000
)


@app.route("/health", methods=["GET"])
def health():
    """Check application and database readiness."""
    try:
        mongo_client.admin.command("ping")
        return jsonify({"status": "ok"}), 200
    except PyMongoError:
        return jsonify({"status": "unavailable"}), 503


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)