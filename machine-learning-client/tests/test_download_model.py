"""Verify model download setup without network access."""

import hashlib
from io import BytesIO
from unittest.mock import patch

import pytest

import download_model


def test_verified_download(tmp_path):
    """Create the model directory and save verified bytes."""
    data = b"test model"
    target = tmp_path / "models" / "gesture_recognizer.task"
    with (
        patch.object(download_model, "MODEL_PATH", target),
        patch.object(download_model, "MODEL_SHA256", hashlib.sha256(data).hexdigest()),
        patch.object(download_model, "urlopen", return_value=BytesIO(data)),
    ):
        assert download_model.download_model() == target
    assert target.read_bytes() == data


def test_bad_download_preserves_existing_model(tmp_path):
    """A corrupt download must not replace an existing model."""
    target = tmp_path / "gesture_recognizer.task"
    target.write_bytes(b"existing model")
    with (
        patch.object(download_model, "MODEL_PATH", target),
        patch.object(download_model, "urlopen", return_value=BytesIO(b"bad download")),
        pytest.raises(ValueError, match="checksum mismatch"),
    ):
        download_model.download_model()
    assert target.read_bytes() == b"existing model"
