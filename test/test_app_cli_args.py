"""Tests for rote-platoon CLI argument parsing."""

import pytest

from swgoh_helper.app import _parse_rote_platoon_args


@pytest.fixture
def original_argv():
    """Snapshot argv and restore after each test."""
    import sys

    saved = sys.argv[:]
    yield
    sys.argv = saved


def test_parse_rote_platoon_args_rejects_retired_show_owners_flag(original_argv):
    """Retired legacy owner flag should fail fast."""
    import sys

    sys.argv = [
        "rote-platoon",
        "123-456-789",
        "--show-owners",
    ]

    with pytest.raises(ValueError, match="--show-owners has been retired"):
        _parse_rote_platoon_args(start_index=2)


def test_parse_rote_platoon_args_rejects_retired_by_territory_flag(original_argv):
    """Retired legacy territory flag should fail fast."""
    import sys

    sys.argv = ["rote-platoon", "123-456-789", "--by-territory"]

    with pytest.raises(ValueError, match="--by-territory has been retired"):
        _parse_rote_platoon_args(start_index=2)


def test_parse_rote_platoon_args_sanitizes_ignored_players(original_argv):
    """Ignored players should be trimmed and empty entries dropped."""
    import sys

    sys.argv = [
        "rote-platoon",
        "123-456-789",
        "--ignore-players",
        " Alpha , , Beta  ",
    ]

    options = _parse_rote_platoon_args(start_index=2)

    assert options["ignored_players"] == ["Alpha", "Beta"]
