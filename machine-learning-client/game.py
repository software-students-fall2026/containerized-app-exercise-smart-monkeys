"""Rock, paper and scissors game logic for MonkeyMoves."""

import random

MOVES = ("rock", "paper", "scissors")


def choose_computer_move():
    """Randomly select a valid move for the computer."""
    return random.choice(MOVES)
