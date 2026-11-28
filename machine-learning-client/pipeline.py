"""Connect the queue worker to recognition, game rules and result storage."""

import logging

from game import choose_computer_move, determine_winner
from ml_db import complete_round, fail_round, invalidate_round
from model import create_recognizer, recognize_gesture
from worker import run_worker


def process_round(game_round, recognizer):
    """Process one claimed round using the shared recognizer."""
    round_id = game_round["_id"]
    try:
        result = recognize_gesture(game_round["image"], recognizer)
    except (OSError, RuntimeError, ValueError):
        logging.exception("Recognition failed for round %s", round_id)
        fail_round(round_id, "Unable to process this image. Please try again.")
        return
    if result["move"] is None:
        invalidate_round(round_id, "Show one clear rock, paper or scissors gesture.")
        return
    computer_move = choose_computer_move()
    complete_round(
        round_id,
        result["move"],
        computer_move,
        result["confidence"],
        determine_winner(result["move"], computer_move),
    )


if __name__ == "__main__":
    with create_recognizer() as active_recognizer:
        run_worker(lambda item: process_round(item, active_recognizer))
