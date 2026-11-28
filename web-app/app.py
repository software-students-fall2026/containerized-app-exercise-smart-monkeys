"""Flask backend for the MonkeyMoves application."""

import os
from io import BytesIO

from flask import Flask, jsonify, render_template, request
from PIL import Image, UnidentifiedImageError
from pymongo.errors import PyMongoError

from web_db import check_connection, create_round_document, store_round

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


@app.route("/", methods=["GET"])
def index():
    """Serve the webcam interface."""
    return render_template("index.html")


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


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
