"""Unit tests for ROTE platoon requirements data validation."""

import json
import pytest
from pathlib import Path
from collections import defaultdict


@pytest.fixture
def rote_requirements():
    """Load the ROTE platoon requirements JSON."""
    json_path = Path("data") / "rote_platoon_requirements.json"
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_each_planet_has_90_total_units(rote_requirements):
    """Verify that each planet has exactly 90 total units/ships in platoon requirements."""
    requirements = rote_requirements["requirements"]

    # Group by path and territory, summing counts
    planet_counts: dict[tuple[str, str], int] = defaultdict(int)

    for req in requirements:
        key = (req["path"], req["territory"])
        planet_counts[key] += req["count"]

    # Check each planet has exactly 90
    errors = []
    for (path, territory), total_count in sorted(planet_counts.items()):
        if total_count != 90:
            errors.append(f"{path}/{territory}: {total_count} units (expected 90)")

    if errors:
        error_msg = "Planets with incorrect unit counts:\n" + "\n".join(errors)
        pytest.fail(error_msg)


def test_all_expected_planets_present(rote_requirements):
    """Verify all expected planets are present in the requirements."""
    requirements = rote_requirements["requirements"]

    # Extract unique path/territory combinations
    planets = {(req["path"], req["territory"]) for req in requirements}

    expected_planets = {
        # Dark Side (6 planets)
        ("dark_side", "Mustafar"),
        ("dark_side", "Geonosis"),
        ("dark_side", "Dathomir"),
        ("dark_side", "Haven-class Medical Station"),
        ("dark_side", "Malachor"),
        ("dark_side", "Death Star"),
        # Neutral (7 planets including bonus)
        ("neutral", "Corellia"),
        ("neutral", "Felucia"),
        ("neutral", "Tatooine"),
        ("neutral", "Mandalore"),
        ("neutral", "Kessel"),
        ("neutral", "Vandor"),
        ("neutral", "Hoth"),
        # Light Side (7 planets including bonus)
        ("light_side", "Coruscant"),
        ("light_side", "Bracca"),
        ("light_side", "Zeffo"),
        ("light_side", "Kashyyyk"),
        ("light_side", "Lothal"),
        ("light_side", "Ring of Kafrene"),
        ("light_side", "Scarif"),
    }

    missing = expected_planets - planets
    extra = planets - expected_planets

    errors = []
    if missing:
        errors.append(f"Missing planets: {missing}")
    if extra:
        errors.append(f"Unexpected planets: {extra}")

    if errors:
        pytest.fail("\n".join(errors))


def test_planet_count_breakdown(rote_requirements):
    """Display breakdown of unit counts per planet (informational test)."""
    requirements = rote_requirements["requirements"]

    # Group by path and territory
    planet_counts: dict[tuple[str, str], int] = defaultdict(int)

    for req in requirements:
        key = (req["path"], req["territory"])
        planet_counts[key] += req["count"]

    # Print breakdown for debugging
    print("\n\nPlanet Unit Count Breakdown:")
    print("-" * 50)

    for path in ["dark_side", "neutral", "light_side"]:
        print(f"\n{path.upper().replace('_', ' ')}:")
        path_planets = [(t, c) for (p, t), c in planet_counts.items() if p == path]
        for territory, count in sorted(path_planets):
            status = "✓" if count == 90 else f"✗ (off by {count - 90})"
            print(f"  {territory}: {count} {status}")


def test_territory_metadata_matches_operation_rules(rote_requirements):
    """Verify each territory exposes consistent platoon scoring metadata."""
    platoon_rules = rote_requirements["platoon_rules"]
    territories = rote_requirements["territories"]

    expected_gp_per_operation = {
        "Mustafar": 10_000_000,
        "Corellia": 10_000_000,
        "Coruscant": 10_000_000,
        "Geonosis": 11_000_000,
        "Felucia": 11_000_000,
        "Bracca": 11_000_000,
        "Dathomir": 13_200_000,
        "Tatooine": 13_200_000,
        "Kashyyyk": 13_200_000,
        "Zeffo": 13_200_000,
        "Haven-class Medical Station": 18_480_000,
        "Kessel": 18_480_000,
        "Lothal": 18_480_000,
        "Mandalore": 18_480_000,
        "Malachor": 33_264_000,
        "Vandor": 33_264_000,
        "Ring of Kafrene": 33_264_000,
        "Death Star": 86_486_400,
        "Hoth": 86_486_400,
        "Scarif": 86_486_400,
    }

    assert platoon_rules["operations_per_planet"] == 6
    assert platoon_rules["slots_per_operation"] == 15
    assert "total_slots_per_planet" not in platoon_rules
    assert len(territories) == 20

    for territory in territories:
        assert "operations_per_planet" not in territory
        assert "slots_per_operation" not in territory
        assert "total_slots" not in territory
        assert "total_platoon_gp" not in territory
        assert "operations" not in territory
        assert (
            territory["gp_per_operation"]
            == expected_gp_per_operation[territory["territory"]]
        )


def test_territory_metadata_matches_flat_requirements(rote_requirements):
    """Verify territory metadata stays aligned with the legacy flat requirement list."""
    requirements = rote_requirements["requirements"]
    territories = rote_requirements["territories"]

    requirement_counts: dict[str, int] = defaultdict(int)
    requirement_paths: dict[str, str] = {}

    for req in requirements:
        territory = req["territory"]
        requirement_counts[territory] += req["count"]
        requirement_paths[territory] = req["path"]

    for territory in territories:
        name = territory["territory"]
        total_slots = 90  # 6 operations * 15 slots per operation
        assert requirement_counts[name] == total_slots
        assert requirement_paths[name] == territory["path"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
