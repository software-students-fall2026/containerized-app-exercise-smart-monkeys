"""Rock, paper and scissors game logic for MonkeyMoves."""

import random

MOVES = ("rock", "paper", "scissors")

WINNING_MOVES = {
    "rock": "scissors",
    "paper": "rock",
    "scissors": "paper",
}

def choose_computer_move():
    """Randomly select a valid move for the computer."""
    return random.choice(MOVES)

def determine_winner(player_move, computer_move):
    """Determine the round outcome from the player's perspective."""
    if player_move not in MOVES or computer_move not in MOVES:
        raise ValueError("Invalid game move")

    if player_move == computer_move:
        return "draw"

    if WINNING_MOVES[player_move] == computer_move:
        return "win"

    return "loss"