"""Tests for the ROTE Farm Advisor."""

import pytest
from unittest.mock import MagicMock

from swgoh_helper.models.rote import (
    CoverageMatrix,
    GapSeverity,
    PersonalFarmRecommendation,
    PersonalFarmReport,
    PlayerUnitInfo,
    RotePath,
    SimpleRoteRequirements,
    UnitCoverage,
    UnitRequirement,
)
from swgoh_helper.rote_farm_advisor import FarmAdvisor


@pytest.fixture
def sample_requirements():
    """Create sample ROTE requirements."""
    return SimpleRoteRequirements(
        version="1.0",
        last_updated="2026-01-01",
        requirements=[
            UnitRequirement(
                unit_id="DARTHTRAYA",
                unit_name="Darth Traya",
                min_relic=5,
                path=RotePath.DARK_SIDE,
                territory="Mustafar",
                count=7,
            ),
            UnitRequirement(
                unit_id="UGNAUGHT",
                unit_name="Ugnaught",
                min_relic=5,
                path=RotePath.DARK_SIDE,
                territory="Mustafar",
                count=3,
            ),
            UnitRequirement(
                unit_id="DARTHREVAN",
                unit_name="Darth Revan",
                min_relic=5,
                path=RotePath.DARK_SIDE,
                territory="Mustafar",
                count=5,
            ),
        ],
    )


@pytest.fixture
def sample_coverage_matrix():
    """Create sample coverage matrix with some units covered."""
    matrix = CoverageMatrix(
        guild_name="Test Guild",
        guild_id="test123",
        member_count=50,
    )

    # Darth Traya - 5 players qualify (gap: need 7, have 5)
    traya_coverage = UnitCoverage(
        unit_id="DARTHTRAYA",
        unit_name="Darth Traya",
        alignment=2,
        combat_type=1,
    )
    for i in range(5):
        traya_coverage.players_by_relic[5].append(
            PlayerUnitInfo(
                player_name=f"Player{i}",
                ally_code=100000000 + i,
                relic_tier=5,
                gear_level=13,
                rarity=7,
            )
        )
    # Add some players below threshold
    for i in range(3):
        traya_coverage.players_by_relic[3].append(
            PlayerUnitInfo(
                player_name=f"ClosePlayer{i}",
                ally_code=200000000 + i,
                relic_tier=3,
                gear_level=13,
                rarity=7,
            )
        )
    matrix.units["DARTHTRAYA"] = traya_coverage

    # Ugnaught - 1 player qualifies (gap: need 3, have 1)
    ugnaught_coverage = UnitCoverage(
        unit_id="UGNAUGHT",
        unit_name="Ugnaught",
        alignment=1,
        combat_type=1,
    )
    ugnaught_coverage.players_by_relic[5].append(
        PlayerUnitInfo(
            player_name="UgnaughtOwner",
            ally_code=300000001,
            relic_tier=5,
            gear_level=13,
            rarity=7,
        )
    )
    # Add player close to qualifying
    ugnaught_coverage.players_by_relic[4].append(
        PlayerUnitInfo(
            player_name="TestPlayer",
            ally_code=999999999,
            relic_tier=4,
            gear_level=13,
            rarity=7,
        )
    )
    matrix.units["UGNAUGHT"] = ugnaught_coverage

    # Darth Revan - 10 players qualify (no gap: need 5, have 10)
    revan_coverage = UnitCoverage(
        unit_id="DARTHREVAN",
        unit_name="Darth Revan",
        alignment=2,
        combat_type=1,
    )
    for i in range(10):
        revan_coverage.players_by_relic[5].append(
            PlayerUnitInfo(
                player_name=f"RevanPlayer{i}",
                ally_code=400000000 + i,
                relic_tier=5,
                gear_level=13,
                rarity=7,
            )
        )
    matrix.units["DARTHREVAN"] = revan_coverage

    return matrix


@pytest.fixture
def sample_player_roster():
    """Create a mock player roster."""
    roster = MagicMock()
    roster.data.name = "TestPlayer"
    roster.data.ally_code = 999999999

    # Create unit mocks
    traya_unit = MagicMock()
    traya_unit.data.base_id = "DARTHTRAYA"
    traya_unit.data.relic_tier = 5  # API value (means R3)
    traya_unit.data.gear_level = 13
    traya_unit.data.rarity = 7

    ugnaught_unit = MagicMock()
    ugnaught_unit.data.base_id = "UGNAUGHT"
    ugnaught_unit.data.relic_tier = 6  # API value (means R4)
    ugnaught_unit.data.gear_level = 13
    ugnaught_unit.data.rarity = 7

    revan_unit = MagicMock()
    revan_unit.data.base_id = "DARTHREVAN"
    revan_unit.data.relic_tier = 7  # API value (means R5)
    revan_unit.data.gear_level = 13
    revan_unit.data.rarity = 7

    roster.units = [traya_unit, ugnaught_unit, revan_unit]
    return roster


class TestFarmAdvisor:
    """Tests for the FarmAdvisor class."""

    def test_get_player_recommendations_returns_report(
        self, sample_coverage_matrix, sample_requirements, sample_player_roster
    ):
        """Test that recommendations return a valid report."""
        advisor = FarmAdvisor(sample_coverage_matrix, sample_requirements)
        report = advisor.get_player_recommendations(sample_player_roster)

        assert isinstance(report, PersonalFarmReport)
        assert report.player_name == "TestPlayer"
        assert report.ally_code == 999999999
        assert report.guild_name == "Test Guild"

    def test_already_qualified_units_excluded(
        self, sample_coverage_matrix, sample_requirements, sample_player_roster
    ):
        """Test that units where player already qualifies are not recommended."""
        advisor = FarmAdvisor(sample_coverage_matrix, sample_requirements)
        report = advisor.get_player_recommendations(sample_player_roster)

        # Darth Revan should be in already_qualified (player has R5, needs R5)
        # Note: based on our mock, player has R5 for Revan
        recommended_unit_ids = [r.unit_id for r in report.recommendations]
        assert "DARTHREVAN" not in recommended_unit_ids

    def test_gap_units_included_in_recommendations(
        self, sample_coverage_matrix, sample_requirements, sample_player_roster
    ):
        """Test that units with gaps are recommended."""
        advisor = FarmAdvisor(sample_coverage_matrix, sample_requirements)
        report = advisor.get_player_recommendations(sample_player_roster)

        # Ugnaught has a critical gap (1/3), player has R4 -> should be recommended
        ugnaught_rec = next(
            (r for r in report.recommendations if r.unit_id == "UGNAUGHT"), None
        )
        assert ugnaught_rec is not None
        assert ugnaught_rec.slots_unfillable > 0

    def test_priority_scoring_favors_high_need_close_progress(
        self, sample_coverage_matrix, sample_requirements, sample_player_roster
    ):
        """Test that higher need + closer progress = higher priority."""
        advisor = FarmAdvisor(sample_coverage_matrix, sample_requirements)
        report = advisor.get_player_recommendations(sample_player_roster)

        # Ugnaught has 1/3 coverage (critical) and player is at R4 (needs +1R)
        # Traya has 5/7 coverage (warning) and player is at R3 (needs +2R)
        # Ugnaught should be higher priority
        if len(report.recommendations) >= 2:
            ugnaught_idx = next(
                (
                    i
                    for i, r in enumerate(report.recommendations)
                    if r.unit_id == "UGNAUGHT"
                ),
                None,
            )
            traya_idx = next(
                (
                    i
                    for i, r in enumerate(report.recommendations)
                    if r.unit_id == "DARTHTRAYA"
                ),
                None,
            )
            if ugnaught_idx is not None and traya_idx is not None:
                # Lower index = higher priority
                assert ugnaught_idx < traya_idx

    def test_need_score_calculation(self, sample_coverage_matrix, sample_requirements):
        """Test need score is higher for more critical gaps."""
        advisor = FarmAdvisor(sample_coverage_matrix, sample_requirements)

        # Ugnaught: 1/3 coverage, CRITICAL severity
        ugnaught_need = advisor._calculate_need_score(
            guild_owners=1,
            total_slots=3,
            total_unfillable=2,
            severity=GapSeverity.CRITICAL,
        )

        # Traya: 5/7 coverage, WARNING severity
        traya_need = advisor._calculate_need_score(
            guild_owners=5,
            total_slots=7,
            total_unfillable=2,
            severity=GapSeverity.WARNING,
        )

        # Ugnaught should have higher need score
        assert ugnaught_need > traya_need

    def test_unowned_units_excluded_by_default(
        self, sample_coverage_matrix, sample_requirements
    ):
        """Test that unowned units are excluded when include_unowned=False."""
        # Create player who doesn't own Ugnaught
        roster = MagicMock()
        roster.data.name = "NewPlayer"
        roster.data.ally_code = 888888888

        traya_unit = MagicMock()
        traya_unit.data.base_id = "DARTHTRAYA"
        traya_unit.data.relic_tier = 5
        traya_unit.data.gear_level = 13
        traya_unit.data.rarity = 7

        roster.units = [traya_unit]  # No Ugnaught

        advisor = FarmAdvisor(sample_coverage_matrix, sample_requirements)
        report = advisor.get_player_recommendations(roster, include_unowned=False)

        # Ugnaught should not be in recommendations
        ugnaught_rec = next(
            (r for r in report.recommendations if r.unit_id == "UGNAUGHT"), None
        )
        assert ugnaught_rec is None

    def test_unowned_units_included_when_requested(
        self, sample_coverage_matrix, sample_requirements
    ):
        """Test that unowned units are included when include_unowned=True."""
        # Create player who doesn't own Ugnaught
        roster = MagicMock()
        roster.data.name = "NewPlayer"
        roster.data.ally_code = 888888888

        traya_unit = MagicMock()
        traya_unit.data.base_id = "DARTHTRAYA"
        traya_unit.data.relic_tier = 5
        traya_unit.data.gear_level = 13
        traya_unit.data.rarity = 7

        roster.units = [traya_unit]  # No Ugnaught

        advisor = FarmAdvisor(sample_coverage_matrix, sample_requirements)
        report = advisor.get_player_recommendations(roster, include_unowned=True)

        # Ugnaught should now appear in recommendations
        ugnaught_rec = next(
            (r for r in report.recommendations if r.unit_id == "UGNAUGHT"), None
        )
        assert ugnaught_rec is not None
        assert ugnaught_rec.has_unit is False


class TestPersonalFarmRecommendation:
    """Tests for the PersonalFarmRecommendation model."""

    def test_status_string_shows_relic(self):
        """Test status string for reliced characters."""
        rec = PersonalFarmRecommendation(
            unit_id="TEST",
            unit_name="Test Unit",
            required_relic=5,
            territories=["Mustafar"],
            current_relic=3,
            gear_level=13,
            rarity=7,
            has_unit=True,
            relic_gap=2,
            gear_gap=0,
            star_gap=0,
            distance_score=10.0,
            guild_owners=5,
            slots_needed=7,
            slots_unfillable=2,
            guild_density=0.71,
            need_score=0.5,
            priority_score=0.3,
        )
        assert rec.status_string == "R3"

    def test_status_string_shows_gear_and_stars(self):
        """Test status string for non-reliced characters."""
        rec = PersonalFarmRecommendation(
            unit_id="TEST",
            unit_name="Test Unit",
            required_relic=5,
            territories=["Mustafar"],
            current_relic=-1,
            gear_level=11,
            rarity=6,
            has_unit=True,
            relic_gap=5,
            gear_gap=2,
            star_gap=1,
            distance_score=50.0,
            guild_owners=1,
            slots_needed=3,
            slots_unfillable=2,
            guild_density=0.33,
            need_score=0.8,
            priority_score=0.5,
        )
        assert rec.status_string == "G11 6*"

    def test_progress_summary_shows_requirements(self):
        """Test progress summary with multiple requirements."""
        rec = PersonalFarmRecommendation(
            unit_id="TEST",
            unit_name="Test Unit",
            required_relic=5,
            territories=["Mustafar"],
            current_relic=-1,
            gear_level=11,
            rarity=6,
            has_unit=True,
            relic_gap=5,
            gear_gap=2,
            star_gap=1,
            distance_score=50.0,
            guild_owners=1,
            slots_needed=3,
            slots_unfillable=2,
            guild_density=0.33,
            need_score=0.8,
            priority_score=0.5,
        )
        assert "+1★" in rec.progress_summary
        assert "+2 gear" in rec.progress_summary
        assert "+5R" in rec.progress_summary
