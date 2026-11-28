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
    "player,outcomes",
    [
        ("rock", ("draw", "loss", "win")),
        ("paper", ("win", "draw", "loss")),
        ("scissors", ("loss", "win", "draw")),
    ],
)
def test_winner(player, outcomes):
    """Cover all nine pairings in MOVES order, from the player's perspective."""
    assert tuple(determine_winner(player, computer) for computer in MOVES) == outcomes


@pytest.mark.parametrize("player,computer", [("invalid", "rock"), ("rock", None)])
def test_invalid_moves(player, computer):
    """Reject invalid moves on either side."""
    with pytest.raises(ValueError):
        determine_winner(player, computer)
