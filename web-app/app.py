"""Flask backend for the MonkeyMoves application."""

import os
from datetime import timezone
from io import BytesIO

from flask import Flask, jsonify, request
from PIL import Image, UnidentifiedImageError
from pymongo.errors import PyMongoError

from web_db import (
    check_connection,
    create_round_document,
    get_round,
    get_stats,
    list_rounds,
    store_round,
)

app = Flask(__name__)

MAX_IMAGE_SIZE = 1024 * 1024

app.config["MAX_CONTENT_LENGTH"] = MAX_IMAGE_SIZE + 64 * 1024


def is_valid_jpeg(image_data):
    """Verify that image data contains a valid JPEG image."""
    try:
        with Image.open(BytesIO(image_data)) as uploaded_image:
            if uploaded_image.format != "JPEG":
                return False

            uploaded_image.load()
            return True

    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
    ):
        return False


def serialize_timestamp(timestamp):
    """Convert a MongoDB timestamp to an ISO 8601 UTC string."""
    if timestamp is None:
        return None

    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)

    return timestamp.astimezone(timezone.utc).isoformat()


def serialize_round(document):
    """Convert a round document into a public API response."""
    return {
        "id": str(document["_id"]),
        "status": document["status"],
        "player_move": document.get("player_move"),
        "computer_move": document.get("computer_move"),
        "confidence": document.get("confidence"),
        "outcome": document.get("outcome"),
        "error": document.get("error"),
        "created_at": serialize_timestamp(document.get("created_at")),
        "finished_at": serialize_timestamp(document.get("finished_at")),
    }


@app.errorhandler(413)
def request_too_large(_error):
    """Return a JSON response for oversized requests."""
    return jsonify({"error": "Request exceeds upload limit"}), 413


@app.route("/health", methods=["GET"])
def health():
    """Check application and database readiness."""
    if check_connection():
        return jsonify({"status": "ok"}), 200

    return jsonify({"status": "unavailable"}), 503


@app.route("/api/rounds", methods=["POST"])
def submit_round():
    """Receive, validate, and store a webcam image."""
    image = request.files.get("image")

    if image is None or not image.filename:
        return jsonify({"error": "Image is required"}), 400

    image_data = image.read(MAX_IMAGE_SIZE + 1)

    if len(image_data) > MAX_IMAGE_SIZE:
        return jsonify({"error": "Image exceeds 1 MiB limit"}), 413

    if image.mimetype != "image/jpeg":
        return jsonify({"error": "Only JPEG images are accepted"}), 400

    if not is_valid_jpeg(image_data):
        return jsonify({"error": "Invalid JPEG image"}), 400

    document = create_round_document(image_data)

    try:
        store_round(document)
    except PyMongoError:
        return jsonify({"error": "Database unavailable"}), 503

    return jsonify({"id": document["_id"], "status": document["status"]}), 202


@app.route("/api/rounds/<round_id>", methods=["GET"])
def retrieve_round(round_id):
    """Retrieve the status and results of an individual round."""
    try:
        document = get_round(round_id)
    except PyMongoError:
        return jsonify({"error": "Database unavailable"}), 503

    if document is None:
        return jsonify({"error": "Round not found"}), 404

    return jsonify(serialize_round(document)), 200


@app.route("/api/rounds", methods=["GET"])
def retrieve_round_history():
    """Retrieve the 20 most recent game rounds."""
    try:
        documents = list_rounds(limit=20)
    except PyMongoError:
        return jsonify({"error": "Database unavailable"}), 503

    return (
        jsonify({"rounds": [serialize_round(document) for document in documents]}),
        200,
    )


@app.route("/api/stats", methods=["GET"])
def retrieve_stats():
    """Retrieve statistics for completed game rounds."""
    try:
        stats = get_stats()
    except PyMongoError:
        return jsonify({"error": "Database unavailable"}), 503

    return jsonify(stats), 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
