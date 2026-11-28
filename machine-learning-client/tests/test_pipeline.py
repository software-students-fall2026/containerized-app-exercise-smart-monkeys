"""Check recognition results are saved with the correct terminal state."""

from unittest.mock import DEFAULT, patch

import pytest

from pipeline import process_round


@pytest.mark.parametrize(
    "result,terminal",
    [
        ({"move": "scissors", "confidence": 0.9}, "complete_round"),
        ({"move": None}, "invalidate_round"),
        (RuntimeError("private details"), "fail_round"),
    ],
)
def test_terminal_result(result, terminal):
    """Save exactly one terminal state, without exposing internal errors."""
    with patch.multiple(
        "pipeline",
        recognize_gesture=DEFAULT,
        choose_computer_move=DEFAULT,
        complete_round=DEFAULT,
        invalidate_round=DEFAULT,
        fail_round=DEFAULT,
    ) as mocks:
        mocks["recognize_gesture"].side_effect = [result]
        mocks["choose_computer_move"].return_value = "paper"
        recognizer = object()
        process_round({"_id": "test", "image": b"jpeg"}, recognizer)
        mocks["recognize_gesture"].assert_called_once_with(b"jpeg", recognizer)
        for name in ("complete_round", "invalidate_round", "fail_round"):
            assert mocks[name].call_count == (name == terminal)
        if terminal == "complete_round":
            mocks[terminal].assert_called_once_with(
                "test", "scissors", "paper", 0.9, "win"
            )
        else:
            round_id, error = mocks[terminal].call_args.args
            assert round_id == "test" and error and "private details" not in error
