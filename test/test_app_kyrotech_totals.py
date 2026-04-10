"""Tests for kyrotech totals behavior in app orchestration."""

from types import SimpleNamespace

from swgoh_helper.app import KyrotechAnalysisApp
from swgoh_helper.models import CharacterKyrotechResult


class _FakeRosterAnalyzer:
    def __init__(self, _kyrotech_analyzer):
        pass

    def build_units_lookup(self, _units_data):
        return {}

    def analyze_all_characters(self, _player_units, _units_by_id, **_kwargs):
        return [
            CharacterKyrotechResult(
                name="Owned A",
                base_id="OWNED_A",
                gear_level=8,
                kyrotech_needs={"172Salvage": 10},
                total_kyrotech=10,
                is_owned=True,
            ),
            CharacterKyrotechResult(
                name="Unowned B",
                base_id="UNOWNED_B",
                gear_level=1,
                kyrotech_needs={"172Salvage": 20},
                total_kyrotech=20,
                is_owned=False,
            ),
        ]


class _FakePresenter:
    def format_results(self, results, **kwargs):
        self.results = results
        self.kwargs = kwargs
        return "ok"

    def format_all_results(self, results, verbose=False):
        return "ok"


class _FakeService:
    def get_all_units(self):
        return SimpleNamespace(data=[])

    def get_all_gear(self):
        return {}

    def get_player(self, _ally_code):
        return SimpleNamespace(units=[])


def test_analyze_player_owned_only_uses_all_character_totals(monkeypatch):
    app = KyrotechAnalysisApp.__new__(KyrotechAnalysisApp)
    app.progress = SimpleNamespace(update=lambda _message: None)
    app.service = _FakeService()
    app.presenter = _FakePresenter()

    monkeypatch.setattr("swgoh_helper.app.KyrotechAnalyzer", lambda gear: object())
    monkeypatch.setattr("swgoh_helper.app.RosterAnalyzer", _FakeRosterAnalyzer)

    output = app.analyze_player("123456789", include_unowned=False, verbose=False)

    assert output == "ok"
    assert len(app.presenter.results) == 1
    assert app.presenter.kwargs["total_owned_count"] == 1
    assert app.presenter.kwargs["total_unowned_count"] == 1
    assert app.presenter.kwargs["total_owned_salvage"] == 10
    assert app.presenter.kwargs["total_unowned_salvage"] == 20
