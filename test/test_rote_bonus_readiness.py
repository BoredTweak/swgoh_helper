"""Tests for journey-guide-backed bonus readiness prerequisites."""

import json

import pytest

from swgoh_helper.rote_bonus_readiness import (
    BonusReadinessAnalyzer,
    UnlockRequirementsSource,
)


class DummyUnit:
    """Minimal unit stub used by bonus readiness prerequisite scoring."""

    def __init__(self, rarity: int, gear_level: int, relic_tier_or_minus_one: int):
        self.rarity = rarity
        self.gear_level = gear_level
        self.relic_tier_or_minus_one = relic_tier_or_minus_one


def _write_requirements(tmp_path):
    data = {
        "schema_version": "2.0.0",
        "updated_at": "2026-05-15",
        "defaults": {"stars": 7},
        "catalog": {
            "units": {
                "REQ1": {"id": "REQ1", "name": "Req One"},
                "REQ2": {"id": "REQ2", "name": "Req Two"},
                "THEMANDALORIANBESKARARMOR": {
                    "id": "THEMANDALORIANBESKARARMOR",
                    "name": "The Mandalorian (Beskar Armor)",
                },
            },
            "tags": {},
            "sets": {},
        },
        "targets": [
            {
                "id": "THEMANDALORIANBESKARARMOR",
                "name": "The Mandalorian (Beskar Armor)",
                "kind": "journey_character",
                "requirement": {
                    "type": "all",
                    "items": [
                        {
                            "type": "unit",
                            "unit": {"id": "REQ1", "min": {"stars": 7, "gear": 12}},
                        }
                    ],
                },
            },
            {
                "id": "MANDALORBOKATAN",
                "name": "Bo-Katan (Mand'alor)",
                "kind": "journey_character",
                "requirement": {
                    "type": "all",
                    "items": [
                        {
                            "type": "unit",
                            "unit": {"id": "REQ2", "min": {"stars": 7, "relic": 7}},
                        },
                        {
                            "type": "unit",
                            "unit": {
                                "id": "THEMANDALORIANBESKARARMOR",
                                "min": {"stars": 7, "relic": 7},
                            },
                        },
                    ],
                },
            },
        ],
    }
    requirements_path = tmp_path / "journey_guide_requirements.json"
    requirements_path.write_text(json.dumps(data), encoding="utf-8")
    return requirements_path


def test_unlock_requirements_source_parses_target_rules(tmp_path):
    requirements_path = _write_requirements(tmp_path)

    source = UnlockRequirementsSource(requirements_path=requirements_path)

    assert [rule.id for rule in source.rules_for("THEMANDALORIANBESKARARMOR")] == [
        "REQ1"
    ]
    assert [rule.id for rule in source.rules_for("MANDALORBOKATAN")] == [
        "REQ2",
        "THEMANDALORIANBESKARARMOR",
    ]


def test_beskar_prereq_distance_uses_json_min_gear_and_stars(tmp_path):
    requirements_path = _write_requirements(tmp_path)
    analyzer = BonusReadinessAnalyzer(journey_requirements_path=requirements_path)
    units = {"REQ1": DummyUnit(rarity=6, gear_level=10, relic_tier_or_minus_one=-1)}

    status = analyzer._beskar_prereq_distance(units)

    assert status.prereq_distance == pytest.approx(3.0)
    assert status.missing_prereqs == ["Req One(6*G10)"]


def test_bokatan_prereq_distance_uses_beskar_unlock_chain_from_json(tmp_path):
    requirements_path = _write_requirements(tmp_path)
    analyzer = BonusReadinessAnalyzer(journey_requirements_path=requirements_path)
    units = {
        "REQ1": DummyUnit(rarity=7, gear_level=12, relic_tier_or_minus_one=-1),
        "REQ2": DummyUnit(rarity=7, gear_level=13, relic_tier_or_minus_one=6),
    }

    status = analyzer._bokatan_prereq_distance(units)

    assert status.prereq_distance == pytest.approx(1.0)
    assert status.missing_prereqs == ["Req Two(R6)"]
