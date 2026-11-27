"""Check the live Flask upload and health endpoints with a real test database."""

import argparse
from io import BytesIO
import json
import os
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


def check_upload(base_url, mongo_uri):
    """Submit a synthetic JPEG, verify its stored bytes, then remove our record."""
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

    with MongoClient(mongo_uri, serverSelectionTimeoutMS=5000) as client:
        rounds = client.get_default_database()["rounds"]
        try:
            document = rounds.find_one({"_id": result["id"]})
            assert document is not None, "Accepted round was not stored"
            assert document["status"] == "pending", document["status"]
            assert document["image"] == image_bytes, "Stored JPEG differs"
            assert document["created_at"] is not None
        finally:
            rounds.delete_one({"_id": result["id"]})


def main():
    """Check ready/upload behavior, or the health response during a DB outage."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expect-unavailable", action="store_true")
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
    check_upload(base_url, os.environ["MONGO_URI"])
    print("PASS: health, missing-image rejection and JPEG storage")


if __name__ == "__main__":
    main()
