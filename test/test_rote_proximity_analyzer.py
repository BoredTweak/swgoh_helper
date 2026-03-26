"""Unit tests for ROTE proximity analyzer."""

import pytest

from swgoh_helper.rote_proximity_analyzer import (
    ProximityAnalyzer,
    ProgressStage,
    PlayerProgress,
    GapProximityReport,
)
from swgoh_helper.rote_coverage import (
    CoverageMatrix,
    UnitCoverage,
    PlayerUnitInfo,
    CoverageMatrixBuilder,
)
from swgoh_helper.rote_gap_analyzer import GapAnalyzer, PlatoonGap, GapSeverity
from swgoh_helper.rote_models import (
    RotePath,
    SimpleRoteRequirements,
    UnitRequirement,
)
from swgoh_helper.models import (
    Unit,
    UnitsResponse,
    PlayerResponse,
    PlayerData,
    PlayerUnit,
    UnitData,
    ArenaSquad,
)
from collections import defaultdict


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_units_response():
    """Create mock units for testing."""
    units = [
        Unit(
            name="Darth Vader",
            base_id="VADER",
            url="",
            image="",
            power=100,
            description="",
            combat_type=1,
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
            name="Starkiller",
            base_id="STARKILLER",
            url="",
            image="",
            power=100,
            description="",
            combat_type=1,
            gear_levels=[],
            alignment=2,  # Dark side
            categories=["Unaligned Force User"],
            ability_classes=[],
            role="Attacker",
            activate_shard_count=80,
            is_capital_ship=False,
            is_galactic_legend=False,
            made_available_on="2022-01-01",
            crew_base_ids=[],
            omicron_ability_ids=[],
            zeta_ability_ids=[],
        ),
    ]
    return UnitsResponse(data=units)


@pytest.fixture
def mock_coverage_matrix():
    """Create a coverage matrix with various player progress levels."""
    matrix = CoverageMatrix(
        guild_name="Test Guild",
        guild_id="test_guild_id",
        member_count=5,
    )

    # Vader unit with players at different levels
    vader_coverage = UnitCoverage(
        unit_id="VADER",
        unit_name="Darth Vader",
        alignment=2,
        combat_type=1,
        categories=["Empire", "Sith"],
    )

    # Player 1: R7 - meets R7 requirement
    vader_coverage.players_by_relic[7].append(
        PlayerUnitInfo(
            player_name="Player1_R7",
            ally_code=100000001,
            relic_tier=7,
            gear_level=13,
            rarity=7,
        )
    )

    # Player 2: R5 - needs 2 more relics for R7
    vader_coverage.players_by_relic[5].append(
        PlayerUnitInfo(
            player_name="Player2_R5",
            ally_code=100000002,
            relic_tier=5,
            gear_level=13,
            rarity=7,
        )
    )

    # Player 3: G12 7* - needs G13 then relics
    vader_coverage.players_by_relic[-1].append(
        PlayerUnitInfo(
            player_name="Player3_G12",
            ally_code=100000003,
            relic_tier=-1,
            gear_level=12,
            rarity=7,
        )
    )

    # Player 4: G10 5* - needs gear and stars before R7
    vader_coverage.players_by_relic[-1].append(
        PlayerUnitInfo(
            player_name="Player4_G10_5star",
            ally_code=100000004,
            relic_tier=-1,
            gear_level=10,
            rarity=5,
        )
    )

    matrix.units["VADER"] = vader_coverage

    # Starkiller - nobody has at R7, one person at R3
    starkiller_coverage = UnitCoverage(
        unit_id="STARKILLER",
        unit_name="Starkiller",
        alignment=2,
        combat_type=1,
        categories=["Unaligned Force User"],
    )

    # Player 5: R3 - needs 4 more relics for R7
    starkiller_coverage.players_by_relic[3].append(
        PlayerUnitInfo(
            player_name="Player5_R3",
            ally_code=100000005,
            relic_tier=3,
            gear_level=13,
            rarity=7,
        )
    )

    matrix.units["STARKILLER"] = starkiller_coverage

    return matrix


@pytest.fixture
def mock_requirements():
    """Create mock platoon requirements."""
    return SimpleRoteRequirements(
        version="1.0",
        last_updated="2026-03-08",
        requirements=[
            UnitRequirement(
                unit_id="VADER",
                unit_name="Darth Vader",
                min_relic=7,
                path=RotePath.DARK_SIDE,
                territory="Mustafar",
                count=2,  # Need 2 players at R7
            ),
            UnitRequirement(
                unit_id="STARKILLER",
                unit_name="Starkiller",
                min_relic=7,
                path=RotePath.DARK_SIDE,
                territory="Mustafar",
                count=1,  # Need 1 player at R7
            ),
        ],
    )


# ============================================================================
# Tests: Star Requirements
# ============================================================================


def test_relic_star_requirements():
    """Test that star requirements are correctly defined."""
    matrix = CoverageMatrix(guild_name="Test", guild_id="test", member_count=1)
    requirements = SimpleRoteRequirements(
        version="1.0", last_updated="2026-03-08", requirements=[]
    )
    analyzer = ProximityAnalyzer(matrix, requirements)

    # Relic 1-3 need 5 stars
    assert analyzer.get_required_stars(1) == 5
    assert analyzer.get_required_stars(2) == 5
    assert analyzer.get_required_stars(3) == 5

    # Relic 4 needs 6 stars
    assert analyzer.get_required_stars(4) == 6

    # Relic 5+ needs 7 stars
    assert analyzer.get_required_stars(5) == 7
    assert analyzer.get_required_stars(7) == 7
    assert analyzer.get_required_stars(9) == 7


# ============================================================================
# Tests: Progress Calculation
# ============================================================================


def test_calculate_progress_reliced_player(mock_coverage_matrix, mock_requirements):
    """Test progress calculation for a player with relics."""
    analyzer = ProximityAnalyzer(mock_coverage_matrix, mock_requirements)

    player = PlayerUnitInfo(
        player_name="TestPlayer",
        ally_code=999,
        relic_tier=5,
        gear_level=13,
        rarity=7,
    )

    progress = analyzer.calculate_player_progress(
        player, "VADER", "Vader", required_relic=7
    )

    assert progress.stage == ProgressStage.RELICED
    assert progress.relic_gap == 2  # R5 -> R7 = 2 levels
    assert progress.gear_gap == 0
    assert progress.star_gap == 0


def test_calculate_progress_gearing_player(mock_coverage_matrix, mock_requirements):
    """Test progress calculation for a player still gearing."""
    analyzer = ProximityAnalyzer(mock_coverage_matrix, mock_requirements)

    player = PlayerUnitInfo(
        player_name="TestPlayer",
        ally_code=999,
        relic_tier=-1,
        gear_level=10,
        rarity=7,
    )

    progress = analyzer.calculate_player_progress(
        player, "VADER", "Vader", required_relic=7
    )

    assert progress.stage == ProgressStage.GEARING
    assert progress.gear_gap == 3  # G10 -> G13 = 3 levels
    assert progress.relic_gap == 7  # Need all 7 relic levels


def test_calculate_progress_star_gated_player(mock_coverage_matrix, mock_requirements):
    """Test progress calculation for a player who needs more stars."""
    analyzer = ProximityAnalyzer(mock_coverage_matrix, mock_requirements)

    # Player at G12 but only 5 stars (needs 7 for R5+)
    player = PlayerUnitInfo(
        player_name="TestPlayer",
        ally_code=999,
        relic_tier=-1,
        gear_level=12,
        rarity=5,
    )

    progress = analyzer.calculate_player_progress(
        player, "VADER", "Vader", required_relic=7
    )

    assert progress.stage == ProgressStage.STAR_GATED
    assert progress.star_gap == 2  # 5* -> 7* = 2 stars


def test_calculate_progress_g13_player(mock_coverage_matrix, mock_requirements):
    """Test progress calculation for a G13 non-reliced player."""
    analyzer = ProximityAnalyzer(mock_coverage_matrix, mock_requirements)

    player = PlayerUnitInfo(
        player_name="TestPlayer",
        ally_code=999,
        relic_tier=-1,
        gear_level=13,
        rarity=7,
    )

    progress = analyzer.calculate_player_progress(
        player, "VADER", "Vader", required_relic=7
    )

    assert progress.stage == ProgressStage.GEAR_13
    assert progress.gear_gap == 0
    assert progress.relic_gap == 7


# ============================================================================
# Tests: Distance Score
# ============================================================================


def test_distance_score_ordering(mock_coverage_matrix, mock_requirements):
    """Test that distance scores order players correctly."""
    analyzer = ProximityAnalyzer(mock_coverage_matrix, mock_requirements)

    # R5 player - closest
    r5_player = PlayerUnitInfo(
        player_name="R5", ally_code=1, relic_tier=5, gear_level=13, rarity=7
    )

    # G12 player - needs gear + relics
    g12_player = PlayerUnitInfo(
        player_name="G12", ally_code=2, relic_tier=-1, gear_level=12, rarity=7
    )

    # G10 with star gate - furthest
    g10_5star = PlayerUnitInfo(
        player_name="G10_5star", ally_code=3, relic_tier=-1, gear_level=10, rarity=5
    )

    r5_progress = analyzer.calculate_player_progress(r5_player, "VADER", "Vader", 7)
    g12_progress = analyzer.calculate_player_progress(g12_player, "VADER", "Vader", 7)
    g10_progress = analyzer.calculate_player_progress(g10_5star, "VADER", "Vader", 7)

    # R5 should have lowest distance, then G12, then G10 with star gate
    assert r5_progress.distance_score < g12_progress.distance_score
    assert g12_progress.distance_score < g10_progress.distance_score


# ============================================================================
# Tests: Gap Proximity Analysis
# ============================================================================


def test_find_closest_players_for_gap(mock_coverage_matrix, mock_requirements):
    """Test finding closest players for a platoon gap."""
    analyzer = ProximityAnalyzer(mock_coverage_matrix, mock_requirements)

    gaps = analyzer.gap_analyzer.get_all_gaps()
    vader_gap = next(g for g in gaps if g.unit_id == "VADER")

    report = analyzer.find_closest_players_for_gap(vader_gap, max_results=10)

    # Should find players who don't meet R7 but have the unit
    assert len(report.closest_players) > 0

    # First player should be closest (R5, only needs +2R)
    assert report.closest_players[0].player_name == "Player2_R5"


def test_analyze_all_gaps(mock_coverage_matrix, mock_requirements):
    """Test analyzing all gaps at once."""
    analyzer = ProximityAnalyzer(mock_coverage_matrix, mock_requirements)

    reports = analyzer.analyze_all_gaps(max_players_per_gap=5)

    # Should have reports for both units
    unit_ids = {r.gap.unit_id for r in reports}
    assert len(unit_ids) >= 1  # At least one gap should have candidates


# ============================================================================
# Tests: Farming Recommendations
# ============================================================================


def test_get_farming_recommendations(mock_coverage_matrix, mock_requirements):
    """Test farming recommendations generation."""
    analyzer = ProximityAnalyzer(mock_coverage_matrix, mock_requirements)

    recommendations = analyzer.get_farming_recommendations(max_recommendations=10)

    # Should return recommendations
    assert len(recommendations) >= 1

    # Each recommendation should have unit name, relic req, and players
    for unit_name, relic_req, players in recommendations:
        assert unit_name
        assert relic_req.startswith("R")
        assert len(players) > 0


# ============================================================================
# Tests: Status String
# ============================================================================


def test_player_progress_status_string():
    """Test status string formatting."""
    # Reliced player
    reliced = PlayerProgress(
        player_name="Test",
        ally_code=1,
        unit_id="VADER",
        unit_name="Vader",
        required_relic=7,
        current_relic=5,
        gear_level=13,
        rarity=7,
        stage=ProgressStage.RELICED,
        relic_gap=2,
        gear_gap=0,
        star_gap=0,
        distance_score=2.0,
    )
    assert reliced.status_string == "R5"

    # Non-reliced player
    gearing = PlayerProgress(
        player_name="Test",
        ally_code=1,
        unit_id="VADER",
        unit_name="Vader",
        required_relic=7,
        current_relic=-1,
        gear_level=10,
        rarity=6,
        stage=ProgressStage.GEARING,
        relic_gap=7,
        gear_gap=3,
        star_gap=0,
        distance_score=10.0,
    )
    assert gearing.status_string == "G10 6*"
