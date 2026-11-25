"""Flask backend for the MonkeyMoves application."""

import os
from datetime import datetime, timezone
from io import BytesIO
from uuid import uuid4

from flask import Flask, jsonify, request
from PIL import Image, UnidentifiedImageError
from pymongo import MongoClient
from pymongo.errors import PyMongoError

app = Flask(__name__)

MAX_IMAGE_SIZE = 1024 * 1024

MONGO_URI = os.getenv(
    "MONGO_URI", "mongodb://db:27017/monkeymoves"
)

mongo_client = MongoClient(
    MONGO_URI, serverSelectionTimeoutMS=2000
)


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


@app.route("/health", methods=["GET"])
def health():
    """Check application and database readiness."""
    try:
        mongo_client.admin.command("ping")
        return jsonify({"status": "ok"}), 200
    except PyMongoError:
        return jsonify({"status": "unavailable"}), 503


@app.route("/api/rounds", methods=["POST"])
def submit_round():
    """Receive and validate a webcam image."""
    image = request.files.get("image")

    if image is None or not image.filename:
        return jsonify({"error": "Image is required"}), 400

    image_data = image.read(MAX_IMAGE_SIZE + 1)

    if len(image_data) > MAX_IMAGE_SIZE:
        return jsonify({"error": "Image exceeds 1 MiB limit"}), 413

    if image.mimetype != "image/jpeg":
        return jsonify({"error": "Only JPEG images are accepted"}), 400

    try:
        with Image.open(BytesIO(image_data)) as uploaded_image:
            if uploaded_image.format != "JPEG":
                return jsonify({"error": "Invalid JPEG image"}), 400

            uploaded_image.load()

    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
    ):
        return jsonify({"error": "Invalid JPEG image"}), 400

    return jsonify({"error": "Submission not yet implemented"}), 501


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)