"""Unit tests for ROTE coverage matrix builder (Phase 3)."""

import pytest

from swgoh_helper.rote_coverage import (
    RoteConfig,
    CoverageMatrixBuilder,
    UnitCoverage,
    PathEligibilityFilter,
    RoteRequirementsLoader,
    CoverageAnalyzer,
)
from swgoh_helper.rote_models import RotePath, UnitRequirement
from swgoh_helper.models import (
    Unit,
    UnitsResponse,
    PlayerResponse,
    PlayerData,
    PlayerUnit,
    UnitData,
    ArenaSquad,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_units_response():
    """Create a mock UnitsResponse with test unit data."""
    units = [
        Unit(
            name="Darth Vader",
            base_id="VADER",
            url="",
            image="",
            power=100,
            description="",
            combat_type=1,  # Character
            gear_levels=[],
            alignment=2,  # Dark side
            categories=["Empire", "Sith"],
            ability_classes=[],
            role="Attacker",
            activate_shard_count=80,
            is_capital_ship=False,
            is_galactic_legend=False,
            made_available_on="2015-11-01",
            crew_base_ids=[],
            omicron_ability_ids=[],
            zeta_ability_ids=[],
        ),
        Unit(
            name="Commander Luke Skywalker",
            base_id="COMMANDERLUKESKYWALKER",
            url="",
            image="",
            power=100,
            description="",
            combat_type=1,  # Character
            gear_levels=[],
            alignment=1,  # Light side
            categories=["Rebel", "Jedi"],
            ability_classes=[],
            role="Attacker",
            activate_shard_count=80,
            is_capital_ship=False,
            is_galactic_legend=False,
            made_available_on="2017-08-01",
            crew_base_ids=[],
            omicron_ability_ids=[],
            zeta_ability_ids=[],
        ),
        Unit(
            name="Chimaera",
            base_id="CAPITALCHIMAERA",
            url="",
            image="",
            power=100,
            description="",
            combat_type=2,  # Ship
            gear_levels=[],
            alignment=2,  # Dark side
            categories=["Empire", "Capital Ship"],
            ability_classes=[],
            role="",
            activate_shard_count=80,
            is_capital_ship=True,
            is_galactic_legend=False,
            made_available_on="2017-11-01",
            crew_base_ids=[],
            omicron_ability_ids=[],
            zeta_ability_ids=[],
        ),
    ]
    return UnitsResponse(data=units)


@pytest.fixture
def mock_player_roster():
    """Create a mock PlayerResponse with test roster data."""

    def make_unit_data(base_id: str, name: str, relic_tier: int | None):
        return PlayerUnit(
            data=UnitData(
                base_id=base_id,
                name=name,
                gear_level=13,
                level=85,
                power=30000,
                rarity=7,
                gear=[],
                url="",
                stats={},
                combat_type=1,
                relic_tier=relic_tier,
                has_ultimate=False,
                is_galactic_legend=False,
            )
        )

    units = [
        make_unit_data("VADER", "Darth Vader", 9),  # R7 (9-2=7)
        make_unit_data("COMMANDERLUKESKYWALKER", "Commander Luke Skywalker", 11),  # R9
        make_unit_data("CAPITALCHIMAERA", "Chimaera", 7),  # R5
    ]

    return PlayerResponse(
        data=PlayerData(
            ally_code=123456789,
            arena_leader_base_id="VADER",
            arena_rank=100,
            level=85,
            name="TestPlayer1",
            last_updated="2026-01-25T00:00:00Z",
            galactic_power=5000000,
            character_galactic_power=4000000,
            ship_galactic_power=1000000,
            ship_battles_won=100,
            pvp_battles_won=100,
            pve_battles_won=100,
            pve_hard_won=100,
            galactic_war_won=100,
            guild_raid_won=100,
            guild_contribution=100,
            guild_exchange_donations=100,
            season_full_clears=0,
            season_successful_defends=0,
            season_league_score=0,
            season_undersized_squad_wins=0,
            season_promotions_earned=0,
            season_banners_earned=0,
            season_offensive_battles_won=0,
            season_territories_defeated=0,
            url="",
            arena=ArenaSquad(),
            fleet_arena=ArenaSquad(),
            skill_rating=0,
            league_name="",
            league_frame_image="",
            league_blank_image="",
            league_image="",
            division_number=0,
            division_image="",
            portrait_image="",
            title="",
            guild_id="test_guild",
            guild_name="Test Guild",
            guild_url="",
        ),
        units=units,
    )


# ============================================================================
# Tests: RoteConfig
# ============================================================================


def test_rote_config_paths():
    """Test that all three paths are defined."""
    assert len(RoteConfig.PATHS) == 3
    assert RotePath.DARK_SIDE in RoteConfig.PATHS
    assert RotePath.NEUTRAL in RoteConfig.PATHS
    assert RotePath.LIGHT_SIDE in RoteConfig.PATHS


def test_rote_config_relic_by_layer():
    """Test relic requirements by layer."""
    assert RoteConfig.RELIC_BY_LAYER[1] == 5
    assert RoteConfig.RELIC_BY_LAYER[5] == 9


# ============================================================================
# Tests: CoverageMatrixBuilder
# ============================================================================


def test_relic_tier_conversion():
    """Test API relic tier to actual relic conversion."""
    builder = CoverageMatrixBuilder(UnitsResponse(data=[]))

    # None = not G13
    assert builder._convert_relic_tier(None) is None

    # 1-2 = G13 but no relic
    assert builder._convert_relic_tier(1) is None
    assert builder._convert_relic_tier(2) is None

    # 3+ = actual relic
    assert builder._convert_relic_tier(3) == 1  # R1
    assert builder._convert_relic_tier(7) == 5  # R5
    assert builder._convert_relic_tier(11) == 9  # R9


def test_build_coverage_matrix(mock_units_response, mock_player_roster):
    """Test building coverage matrix from rosters."""
    builder = CoverageMatrixBuilder(mock_units_response)
    matrix = builder.build_from_rosters(
        rosters=[mock_player_roster],
        guild_name="Test Guild",
        guild_id="test_guild_id",
    )

    assert matrix.guild_name == "Test Guild"
    assert matrix.member_count == 1

    # Check Vader coverage
    vader_coverage = matrix.get_coverage("VADER")
    assert vader_coverage is not None
    assert vader_coverage.count_at_relic(5) == 1
    assert vader_coverage.count_at_relic(7) == 1
    assert vader_coverage.count_at_relic(8) == 0  # Player has R7, not R8

    # Check CLS coverage
    cls_coverage = matrix.get_coverage("COMMANDERLUKESKYWALKER")
    assert cls_coverage is not None
    assert cls_coverage.count_at_relic(9) == 1


def test_coverage_matrix_get_coverage_summary(mock_units_response, mock_player_roster):
    """Test coverage summary generation."""
    builder = CoverageMatrixBuilder(mock_units_response)
    matrix = builder.build_from_rosters(
        rosters=[mock_player_roster],
        guild_name="Test Guild",
        guild_id="test_guild_id",
    )

    summary = matrix.get_coverage_summary("VADER")
    assert summary[5] == 1  # 1 player at R5+
    assert summary[7] == 1  # 1 player at R7+
    assert summary[8] == 0  # 0 players at R8+


# ============================================================================
# Tests: PathEligibilityFilter
# ============================================================================


def test_path_eligibility_dark_side():
    """Test dark side path filtering."""
    dark_unit = UnitCoverage(
        unit_id="VADER",
        unit_name="Darth Vader",
        alignment=RoteConfig.ALIGNMENT_DARK,
        combat_type=1,
    )
    light_unit = UnitCoverage(
        unit_id="LUKE",
        unit_name="Luke Skywalker",
        alignment=RoteConfig.ALIGNMENT_LIGHT,
        combat_type=1,
    )

    assert PathEligibilityFilter.is_eligible_for_path(dark_unit, RotePath.DARK_SIDE)
    assert not PathEligibilityFilter.is_eligible_for_path(
        light_unit, RotePath.DARK_SIDE
    )


def test_path_eligibility_light_side():
    """Test light side path filtering."""
    dark_unit = UnitCoverage(
        unit_id="VADER",
        unit_name="Darth Vader",
        alignment=RoteConfig.ALIGNMENT_DARK,
        combat_type=1,
    )
    light_unit = UnitCoverage(
        unit_id="LUKE",
        unit_name="Luke Skywalker",
        alignment=RoteConfig.ALIGNMENT_LIGHT,
        combat_type=1,
    )

    assert not PathEligibilityFilter.is_eligible_for_path(
        dark_unit, RotePath.LIGHT_SIDE
    )
    assert PathEligibilityFilter.is_eligible_for_path(light_unit, RotePath.LIGHT_SIDE)


def test_path_eligibility_neutral():
    """Test neutral path accepts all alignments."""
    dark_unit = UnitCoverage(
        unit_id="VADER",
        unit_name="Darth Vader",
        alignment=RoteConfig.ALIGNMENT_DARK,
        combat_type=1,
    )
    light_unit = UnitCoverage(
        unit_id="LUKE",
        unit_name="Luke Skywalker",
        alignment=RoteConfig.ALIGNMENT_LIGHT,
        combat_type=1,
    )

    assert PathEligibilityFilter.is_eligible_for_path(dark_unit, RotePath.NEUTRAL)
    assert PathEligibilityFilter.is_eligible_for_path(light_unit, RotePath.NEUTRAL)


def test_filter_characters_only():
    """Test filtering to characters only."""
    units = {
        "VADER": UnitCoverage(
            unit_id="VADER",
            unit_name="Darth Vader",
            alignment=2,
            combat_type=1,  # Character
        ),
        "CHIMAERA": UnitCoverage(
            unit_id="CHIMAERA",
            unit_name="Chimaera",
            alignment=2,
            combat_type=2,  # Ship
        ),
    }

    filtered = PathEligibilityFilter.filter_characters_only(units)
    assert "VADER" in filtered
    assert "CHIMAERA" not in filtered


# ============================================================================
# Tests: RoteRequirementsLoader
# ============================================================================


def test_load_requirements():
    """Test loading requirements from JSON file."""
    requirements = RoteRequirementsLoader.load()

    assert requirements.version == "1.0"
    assert len(requirements.requirements) > 0

    # Check that we have requirements for all paths
    paths_found = {req.path for req in requirements.requirements}
    assert RotePath.DARK_SIDE in paths_found
    assert RotePath.NEUTRAL in paths_found
    assert RotePath.LIGHT_SIDE in paths_found


# ============================================================================
# Tests: CoverageAnalyzer
# ============================================================================


def test_coverage_analyzer_basic(mock_units_response, mock_player_roster):
    """Test basic coverage analysis."""
    builder = CoverageMatrixBuilder(mock_units_response)
    matrix = builder.build_from_rosters(
        rosters=[mock_player_roster],
        guild_name="Test Guild",
        guild_id="test_guild_id",
    )

    # Create a simple requirement
    from swgoh_helper.rote_models import SimpleRoteRequirements

    requirements = SimpleRoteRequirements(
        version="1.0",
        last_updated="2026-01-25",
        requirements=[
            UnitRequirement(
                unit_id="VADER",
                unit_name="Darth Vader",
                min_relic=5,
                path=RotePath.DARK_SIDE,
                territory="Mustafar",
                count=2,
            ),
            UnitRequirement(
                unit_id="VADER",
                unit_name="Darth Vader",
                min_relic=8,
                path=RotePath.DARK_SIDE,
                territory="Malachor",
                count=1,
            ),
        ],
    )

    analyzer = CoverageAnalyzer(matrix, requirements)
    results = analyzer.analyze_all_requirements()

    assert len(results) == 2

    # R5 requirement should be covered (player has R7)
    r5_result = results[0]
    assert r5_result.players_available == 1
    assert "TestPlayer1" in r5_result.player_names

    # R8 requirement should NOT be covered (player only has R7)
    r8_result = results[1]
    assert r8_result.players_available == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
