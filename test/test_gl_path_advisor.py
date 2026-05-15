"""Tests for Galactic Legend path advisor."""

import json
from types import SimpleNamespace

from swgoh_helper.gl_path_advisor import GLPathAdvisor


def _fake_player_unit(base_id: str, relic: int, gear: int, stars: int):
    data = SimpleNamespace(
        base_id=base_id,
        relic_tier_or_minus_one=relic,
        gear_level=gear,
        rarity=stars,
    )
    return SimpleNamespace(data=data)


def _fake_player(name: str, ally_code: int, units: list[SimpleNamespace]):
    data = SimpleNamespace(name=name, ally_code=ally_code)
    return SimpleNamespace(data=data, units=units)


def _fake_units_response(units: list[tuple[str, str]]):
    unit_objects = [SimpleNamespace(name=name, base_id=base_id) for name, base_id in units]
    return SimpleNamespace(data=unit_objects)


def test_analyze_ranks_closest_path_first(tmp_path):
    requirements = [
        {
            "gl_name": "Closer GL",
            "requirements": [{"unit_name": "Unit One", "required_relic": 5}],
        },
        {
            "gl_name": "Farther GL",
            "requirements": [{"unit_name": "Unit Two", "required_relic": 7}],
        },
    ]
    requirements_path = tmp_path / "gl_requirements.json"
    requirements_path.write_text(json.dumps(requirements), encoding="utf-8")

    advisor = GLPathAdvisor(requirements_path=requirements_path)
    units_data = _fake_units_response([("Unit One", "UNIT1"), ("Unit Two", "UNIT2")])
    player = _fake_player(
        "Test Player",
        123456789,
        [
            _fake_player_unit("UNIT1", relic=4, gear=13, stars=7),
            _fake_player_unit("UNIT2", relic=1, gear=13, stars=7),
        ],
    )

    report = advisor.analyze(player, units_data, top_n=2)

    assert len(report.ranked_paths) == 2
    assert report.ranked_paths[0].gl_name == "Closer GL"
    assert report.ranked_paths[1].gl_name == "Farther GL"


def test_analyze_filters_by_target_gl(tmp_path):
    requirements = [
        {
            "gl_name": "Jedi Master Test",
            "requirements": [{"unit_name": "Unit One", "required_relic": 5}],
        },
        {
            "gl_name": "Sith Eternal Test",
            "requirements": [{"unit_name": "Unit Two", "required_relic": 5}],
        },
    ]
    requirements_path = tmp_path / "gl_requirements.json"
    requirements_path.write_text(json.dumps(requirements), encoding="utf-8")

    advisor = GLPathAdvisor(requirements_path=requirements_path)
    units_data = _fake_units_response([("Unit One", "UNIT1"), ("Unit Two", "UNIT2")])
    player = _fake_player("Test Player", 123456789, [_fake_player_unit("UNIT1", 5, 13, 7)])

    report = advisor.analyze(player, units_data, target_gl="jedi master", top_n=3)

    assert len(report.ranked_paths) == 1
    assert report.ranked_paths[0].gl_name == "Jedi Master Test"


def test_owned_only_applies_higher_unowned_penalty(tmp_path):
    requirements = [
        {
            "gl_name": "Penalty Test",
            "requirements": [{"unit_name": "Missing Unit", "required_relic": 5}],
        }
    ]
    requirements_path = tmp_path / "gl_requirements.json"
    requirements_path.write_text(json.dumps(requirements), encoding="utf-8")

    advisor = GLPathAdvisor(requirements_path=requirements_path)
    units_data = _fake_units_response([("Missing Unit", "MISSING1")])
    player = _fake_player("Test Player", 123456789, [])

    default_report = advisor.analyze(player, units_data, include_unowned=True)
    owned_only_report = advisor.analyze(player, units_data, include_unowned=False)

    assert len(default_report.ranked_paths) == 1
    assert len(owned_only_report.ranked_paths) == 1
    assert owned_only_report.ranked_paths[0].total_distance > default_report.ranked_paths[0].total_distance


def test_format_report_orders_unlock_path_by_lowest_weight(tmp_path):
    requirements = [
        {
            "gl_name": "Ordered GL",
            "requirements": [
                {"unit_name": "Hard Unit", "required_relic": 7},
                {"unit_name": "Done Unit", "required_relic": 3},
                {"unit_name": "Easy Unit", "required_relic": 3},
            ],
        }
    ]
    requirements_path = tmp_path / "gl_requirements.json"
    requirements_path.write_text(json.dumps(requirements), encoding="utf-8")

    advisor = GLPathAdvisor(requirements_path=requirements_path)
    units_data = _fake_units_response(
        [("Hard Unit", "HARD1"), ("Done Unit", "DONE1"), ("Easy Unit", "EASY1")]
    )
    player = _fake_player(
        "Test Player",
        123456789,
        [
            _fake_player_unit("HARD1", relic=1, gear=13, stars=7),
            _fake_player_unit("DONE1", relic=3, gear=13, stars=7),
            _fake_player_unit("EASY1", relic=2, gear=13, stars=7),
        ],
    )

    report = advisor.analyze(player, units_data)
    output = advisor.format_report(report)

    assert "Already have:" in output
    assert "Done Unit: R3 (7*) meets R3" in output
    assert "Unlock path (lowest weight first):" in output
    assert "weight" in output
    assert output.index("1. Easy Unit") < output.index("2. Hard Unit")


def test_relic_requirement_still_costs_when_stars_are_short(tmp_path):
    requirements = [
        {
            "gl_name": "Star Gate GL",
            "requirements": [{"unit_name": "Star Short Unit", "required_relic": 5}],
        }
    ]
    requirements_path = tmp_path / "gl_requirements.json"
    requirements_path.write_text(json.dumps(requirements), encoding="utf-8")

    advisor = GLPathAdvisor(requirements_path=requirements_path)
    units_data = _fake_units_response([("Star Short Unit", "STAR1")])
    player = _fake_player(
        "Test Player",
        123456789,
        [_fake_player_unit("STAR1", relic=5, gear=13, stars=6)],
    )

    report = advisor.analyze(player, units_data)

    assert report.ranked_paths[0].completed_requirements == 0
    assert report.ranked_paths[0].missing_requirements[0].distance == 2.0
