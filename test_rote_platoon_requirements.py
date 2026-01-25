"""Unit tests for ROTE platoon requirements data validation."""

import json
import pytest
from pathlib import Path
from collections import defaultdict


@pytest.fixture
def rote_requirements():
    """Load the ROTE platoon requirements JSON."""
    json_path = Path(__file__).parent / "data" / "rote_platoon_requirements.json"
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
