"""Rock, paper and scissors game logic for MonkeyMoves."""

import random

MOVES = ("rock", "paper", "scissors")


def choose_computer_move():
    """Randomly select a valid move for the computer."""
    return random.choice(MOVES)


def determine_winner(player_move, computer_move):
    """Return the outcome from the player's perspective."""
    if player_move not in MOVES or computer_move not in MOVES:
        raise ValueError("Moves must be rock, paper or scissors")
    if player_move == computer_move:
        return "draw"
    beats = {"rock": "scissors", "paper": "rock", "scissors": "paper"}
    return "win" if beats[player_move] == computer_move else "loss"
