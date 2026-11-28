"""Check the live Flask upload and health endpoints with a real test database."""

import argparse
from io import BytesIO
import json
import os
from pathlib import Path
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

from PIL import Image
from pymongo import MongoClient


def request_json(url, data=None, headers=None):
    """Return the status and JSON body, including expected HTTP error responses."""
    request = Request(url, data=data, headers=headers or {})
    try:
        response = urlopen(request, timeout=10)
    except HTTPError as error:
        response = error
    with response:
        return response.status, json.load(response)


def check_upload(base_url, mongo_uri, image_bytes=None, expected="pending"):
    """Verify JPEG storage or real processing, then remove only our test round."""
    if image_bytes is None:
        image = BytesIO()
        Image.new("RGB", (16, 16), "blue").save(image, format="JPEG")
        image_bytes = image.getvalue()
    boundary = uuid4().hex
    body = (
        (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="image"; filename="smoke.jpg"\r\n'
            "Content-Type: image/jpeg\r\n\r\n"
        ).encode()
        + image_bytes
        + f"\r\n--{boundary}--\r\n".encode()
    )
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    status, result = request_json(f"{base_url}/api/rounds", body, headers)
    assert status == 202, (status, result)
    assert result["status"] == "pending", result
    round_id = result["id"]

    with MongoClient(mongo_uri, serverSelectionTimeoutMS=5000) as client:
        rounds = client.get_default_database()["rounds"]
        try:
            if expected != "pending":
                deadline = time.monotonic() + 60
                while time.monotonic() < deadline:
                    status, result = request_json(f"{base_url}/api/rounds/{round_id}")
                    assert status == 200, result
                    if result["status"] not in ("pending", "processing"):
                        break
                    time.sleep(1)
                assert result["status"] == expected, result
                if expected == "completed":
                    assert result["player_move"] == "scissors", result
                    assert 0.70 <= result["confidence"] <= 1, result
                    assert (
                        result["outcome"]
                        == {"rock": "loss", "paper": "win", "scissors": "draw"}[
                            result["computer_move"]
                        ]
                    ), result
                else:
                    assert result["error"] and result["outcome"] is None, result
            document = rounds.find_one({"_id": round_id})
            assert document is not None, "Accepted round was not stored"
            assert document["status"] == expected, document["status"]
            if expected == "pending":
                assert document["image"] == image_bytes, "Stored JPEG differs"
            else:
                assert "image" not in document and document["finished_at"] is not None
            assert document["created_at"] is not None
        finally:
            rounds.delete_one({"_id": round_id})


def main():
    """Check ready/upload behavior, or the health response during a DB outage."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expect-unavailable", action="store_true")
    parser.add_argument(
        "--gesture", type=Path, help="Known scissors JPEG for the full stack"
    )
    args = parser.parse_args()
    base_url = os.environ.get("BASE_URL", "http://127.0.0.1:5000").rstrip("/")
    status, result = request_json(f"{base_url}/health")
    if args.expect_unavailable:
        assert status == 503, (status, result)
        assert result == {"status": "unavailable"}, result
        print("PASS: database outage returns 503")
        return

    assert status == 200, (status, result)
    assert result == {"status": "ok"}, result
    status, result = request_json(f"{base_url}/api/rounds", data=b"")
    assert status == 400, (status, result)
    if args.gesture:
        check_upload(
            base_url, os.environ["MONGO_URI"], args.gesture.read_bytes(), "completed"
        )
        check_upload(base_url, os.environ["MONGO_URI"], expected="invalid")
    else:
        check_upload(base_url, os.environ["MONGO_URI"])
    print("PASS: health, upload and expected database result")


if __name__ == "__main__":
    main()
