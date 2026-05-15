"""Tests for rote-platoon CLI argument parsing."""

import sys

import pytest

from swgoh_helper.app import _parse_ally_code_arg, _parse_rote_platoon_args


@pytest.mark.parametrize(
    "argv,expected",
    [
        (["app.py", "123-456-789"], ("123-456-789", 2)),
        (["app.py", "--ally-code", "123456789"], ("123456789", 3)),
        (["app.py", "--ally-code=123456789"], ("123456789", 2)),
        (["app.py", "-a", "123456789"], ("123456789", 3)),
    ],
)
def test_parse_ally_code_arg_accepts_supported_forms(
    argv: list[str], expected: tuple[str, int]
):
    """CLI parser should accept positional and ally-code option forms."""
    assert _parse_ally_code_arg(argv) == expected


@pytest.mark.parametrize(
    "argv,error_match",
    [
        (["app.py", "--ally-code"], "requires a value"),
        (["app.py", "--ally-code="], "requires a value"),
        (["app.py", "--max-phase", "4"], "Missing ally code"),
    ],
)
def test_parse_ally_code_arg_rejects_missing_or_invalid_input(
    argv: list[str], error_match: str
):
    """CLI parser should produce a clear error when ally code is absent."""
    with pytest.raises(ValueError, match=error_match):
        _parse_ally_code_arg(argv)


@pytest.mark.parametrize(
    "argv,expected",
    [
        (
            [
                "app.py",
                "123-456-789",
                "--output-format",
                "planets",
                "--planets",
                "DS1,N1,LS1",
            ],
            ["DS1", "N1", "LS1"],
        ),
        (
            ["app.py", "123-456-789", "--planets", "ds1", "n1", "ls1"],
            ["DS1", "N1", "LS1"],
        ),
    ],
)
def test_parse_rote_platoon_args_parses_planet_identifiers(
    monkeypatch: pytest.MonkeyPatch, argv: list[str], expected: list[str]
):
    """CLI parser should normalize and return up to 3 planet IDs."""
    monkeypatch.setattr(sys, "argv", argv)

    parsed = _parse_rote_platoon_args(start_index=2)

    assert parsed["planet_identifiers"] == expected


def test_parse_rote_platoon_args_rejects_more_than_three_planets(
    monkeypatch: pytest.MonkeyPatch,
):
    """CLI parser should reject more than 3 selected planets."""
    monkeypatch.setattr(
        sys,
        "argv",
        ["app.py", "123-456-789", "--planets", "DS1,N1,LS1,DS2"],
    )

    with pytest.raises(ValueError, match="at most 3"):
        _parse_rote_platoon_args(start_index=2)
