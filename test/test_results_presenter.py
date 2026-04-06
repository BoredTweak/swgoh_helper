"""Tests for kyrotech result presentation behavior."""

from swgoh_helper.models import CharacterKyrotechResult
from swgoh_helper.results_presenter import ResultsPresenter


def _owned_results(count: int):
    return [(f"Character {i}", 8, {"172Salvage": i}, i) for i in range(count, 0, -1)]


def _mixed_results(count: int):
    return [
        CharacterKyrotechResult(
            name=f"Character {i}",
            base_id=f"UNIT_{i}",
            gear_level=8,
            kyrotech_needs={"172Salvage": i},
            total_kyrotech=i,
            is_owned=i % 2 == 0,
        )
        for i in range(count, 0, -1)
    ]


def test_format_results_defaults_to_top_10_and_keeps_totals():
    presenter = ResultsPresenter()
    output = presenter.format_results(_owned_results(12))

    assert "#10. Character 3" in output
    assert "#11." not in output
    assert "Total owned characters needing kyros: 12" in output
    assert "Total unowned characters needing kyros: 0" in output
    assert "Total kyrotech salvage needed for owned characters: 78" in output
    assert "Total kyrotech salvage needed for unowned characters: 0" in output
    assert "Total kyrotech salvage needed overall: 78" in output


def test_format_results_can_include_unowned_totals_from_full_analysis():
    presenter = ResultsPresenter()
    output = presenter.format_results(
        _owned_results(12),
        total_owned_count=12,
        total_unowned_count=6,
        total_owned_salvage=78,
        total_unowned_salvage=36,
    )

    assert "Total owned characters needing kyros: 12" in output
    assert "Total unowned characters needing kyros: 6" in output
    assert "Total kyrotech salvage needed for owned characters: 78" in output
    assert "Total kyrotech salvage needed for unowned characters: 36" in output
    assert "Total kyrotech salvage needed overall: 114" in output


def test_format_results_verbose_shows_every_character():
    presenter = ResultsPresenter()
    output = presenter.format_results(_owned_results(12), verbose=True)

    assert "#12. Character 1" in output


def test_format_all_results_defaults_to_top_10_and_keeps_totals():
    presenter = ResultsPresenter()
    output = presenter.format_all_results(_mixed_results(12))

    assert output.count("Total Kyrotech Salvage:") == 10
    assert "Total owned characters needing kyros: 6" in output
    assert "Total unowned characters needing kyros: 6" in output
    assert "Total kyrotech salvage needed for owned characters: 42" in output
    assert "Total kyrotech salvage needed for unowned characters: 36" in output
    assert "Total kyrotech salvage needed overall: 78" in output


def test_format_all_results_verbose_shows_every_character():
    presenter = ResultsPresenter()
    output = presenter.format_all_results(_mixed_results(12), verbose=True)

    assert output.count("Total Kyrotech Salvage:") == 12
