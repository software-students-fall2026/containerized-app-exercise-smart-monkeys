"""Unit tests for the MonkeyMoves game logic."""

from unittest.mock import patch

import pytest

from game import MOVES, choose_computer_move, determine_winner


def test_valid_moves():
    """Verify that the game defines exactly three valid moves."""
    assert MOVES == ("rock", "paper", "scissors")


@pytest.mark.parametrize("move", ["rock", "paper", "scissors"])
def test_choose_computer_move(move):
    """Verify that the computer can select each valid move."""
    with patch("game.random.choice", return_value=move) as mock_choice:
        assert choose_computer_move() == move
        mock_choice.assert_called_once_with(MOVES)


def test_generated_moves_are_valid():
    """Verify that randomly generated moves are always valid."""
    for _ in range(100):
        assert choose_computer_move() in MOVES


@pytest.mark.parametrize(
    "player_move, computer_move, expected_outcome",
    [
        ("rock", "rock", "draw"),
        ("rock", "paper", "loss"),
        ("rock", "scissors", "win"),
        ("paper", "rock", "win"),
        ("paper", "paper", "draw"),
        ("paper", "scissors", "loss"),
        ("scissors", "rock", "loss"),
        ("scissors", "paper", "win"),
        ("scissors", "scissors", "draw"),
    ],
)
def test_determine_winner(player_move, computer_move, expected_outcome):
    """Verify all nine possible game outcomes."""
    assert determine_winner(player_move, computer_move) == expected_outcome


@pytest.mark.parametrize(
    "player_move, computer_move",
    [
        ("banana", "rock"),
        ("rock", "banana"),
        ("", "paper"),
        ("scissors", ""),
        (None, "rock"),
        ("paper", None),
        ("ROCK", "paper"),
        ("invalid", "invalid"),
    ],
)
def test_invalid_game_moves(player_move, computer_move):
    """Verify that invalid game moves are rejected."""
    with pytest.raises(ValueError, match="Invalid game move"):
        determine_winner(player_move, computer_move)
