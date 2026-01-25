"""
ROTE Coverage Matrix Builder - Phase 3 Implementation

Aggregates guild-wide unit eligibility for Rise of the Empire platoon analysis.
Builds a coverage matrix showing how many players have each unit at each relic threshold.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

from .models import PlayerResponse, Unit, UnitsResponse
from .rote_models import RotePath, SimpleRoteRequirements, UnitRequirement


class RoteConfig:
    """Configuration constants for ROTE platoon analysis."""

    PATHS = [RotePath.DARK_SIDE, RotePath.NEUTRAL, RotePath.LIGHT_SIDE]

    # Minimum relic tier required per layer/territory
    RELIC_BY_LAYER = {
        1: 5,  # R5 (e.g., Mustafar, Corellia, Coruscant)
        2: 6,  # R6
        3: 7,  # R7
        4: 8,  # R8
        5: 9,  # R9
    }

    # Maximum units a single player can deploy per planet
    MAX_UNITS_PER_PLAYER_PER_PLANET = 10

    # Alignment values from SWGOH.GG API
    ALIGNMENT_LIGHT = 1
    ALIGNMENT_DARK = 2
    ALIGNMENT_NEUTRAL = 3  # (Not used in game, but included for completeness)

    # Territory phase mapping (which phase each planet is in)
    # Format: territory_name -> phase_number (use 'b' suffix for bonus planets)
    TERRITORY_PHASE = {
        # Phase 1
        "Coruscant": "1",
        "Mustafar": "1",
        "Corellia": "1",
        # Phase 2
        "Bracca": "2",
        "Geonosis": "2",
        "Felucia": "2",
        # Phase 3
        "Kashyyyk": "3",
        "Dathomir": "3",
        "Tatooine": "3",
        "Zeffo": "3b",  # Bonus planet
        # Phase 4
        "Lothal": "4",
        "Kessel": "4",
        "Haven-class Medical Station": "4",
        "Mandalore": "4b",  # Bonus planet
        # Phase 5
        "Scarif": "5",
        "Malachor": "5",
        "Vandor": "5",
        # Phase 6
        "Ring of Kafrene": "6",
        "Hoth": "6",
        "Death Star": "6",
    }


@dataclass
class PlayerUnitInfo:
    """Information about a player's ownership of a unit."""

    player_name: str
    ally_code: int
    relic_tier: int  # Actual relic (0-9), not API value


@dataclass
class UnitCoverage:
    """Coverage data for a single unit across the guild."""

    unit_id: str
    unit_name: str
    alignment: int  # 1=Light, 2=Dark
    combat_type: int  # 1=Character, 2=Ship
    categories: List[str] = field(default_factory=list)

    # Players at each relic threshold: relic_level -> list of player info
    players_by_relic: Dict[int, List[PlayerUnitInfo]] = field(
        default_factory=lambda: defaultdict(list)
    )

    def count_at_relic(self, min_relic: int) -> int:
        """Count players who have this unit at or above a relic threshold."""
        count = 0
        for relic_level, players in self.players_by_relic.items():
            if relic_level >= min_relic:
                count += len(players)
        return count

    def players_at_relic(self, min_relic: int) -> List[PlayerUnitInfo]:
        """Get list of players who have this unit at or above a relic threshold."""
        result = []
        for relic_level, players in self.players_by_relic.items():
            if relic_level >= min_relic:
                result.extend(players)
        return result


@dataclass
class CoverageMatrix:
    """
    Complete coverage matrix for a guild.

    Maps unit_id -> UnitCoverage, providing easy lookup of which players
    have which units at which relic levels.
    """

    guild_name: str
    guild_id: str
    member_count: int
    units: Dict[str, UnitCoverage] = field(default_factory=dict)

    def get_coverage(self, unit_id: str) -> Optional[UnitCoverage]:
        """Get coverage data for a specific unit."""
        return self.units.get(unit_id)

    def get_count_at_relic(self, unit_id: str, min_relic: int) -> int:
        """Get count of players with a unit at a minimum relic level."""
        coverage = self.units.get(unit_id)
        if coverage is None:
            return 0
        return coverage.count_at_relic(min_relic)

    def get_players_at_relic(
        self, unit_id: str, min_relic: int
    ) -> List[PlayerUnitInfo]:
        """Get players who have a unit at a minimum relic level."""
        coverage = self.units.get(unit_id)
        if coverage is None:
            return []
        return coverage.players_at_relic(min_relic)

    def get_coverage_summary(self, unit_id: str) -> Dict[int, int]:
        """
        Get a summary of player counts at each relic threshold.

        Returns dict like: {5: 45, 6: 42, 7: 38, 8: 12, 9: 3}
        where key is min_relic and value is player count at or above that level.
        """
        coverage = self.units.get(unit_id)
        if coverage is None:
            return {r: 0 for r in range(5, 10)}

        return {r: coverage.count_at_relic(r) for r in range(5, 10)}


class CoverageMatrixBuilder:
    """Builds a coverage matrix from guild roster data."""

    def __init__(self, units_data: UnitsResponse):
        self.units_lookup: Dict[str, Unit] = {
            unit.base_id: unit for unit in units_data.data
        }

    def build_from_rosters(
        self,
        rosters: List[PlayerResponse],
        guild_name: str,
        guild_id: str,
    ) -> CoverageMatrix:
        """Build a complete coverage matrix from guild rosters."""
        matrix = CoverageMatrix(
            guild_name=guild_name,
            guild_id=guild_id,
            member_count=len(rosters),
        )

        for roster in rosters:
            self._process_player_roster(roster, matrix)

        return matrix

    def _process_player_roster(
        self, roster: PlayerResponse, matrix: CoverageMatrix
    ) -> None:
        player_name = roster.data.name
        ally_code = roster.data.ally_code

        for player_unit in roster.units:
            unit_data = player_unit.data
            unit_id = unit_data.base_id

            unit_meta = self.units_lookup.get(unit_id)
            if unit_meta is None:
                continue

            # Ships use star level, characters use relic tier
            if unit_meta.combat_type == 2:
                if unit_data.rarity < 7:
                    continue
                effective_tier = unit_data.rarity
            else:
                actual_relic = self._convert_relic_tier(unit_data.relic_tier)
                if actual_relic is None:
                    continue
                effective_tier = actual_relic

            if unit_id not in matrix.units:
                matrix.units[unit_id] = UnitCoverage(
                    unit_id=unit_id,
                    unit_name=unit_meta.name,
                    alignment=unit_meta.alignment,
                    combat_type=unit_meta.combat_type,
                    categories=unit_meta.categories.copy(),
                )

            player_info = PlayerUnitInfo(
                player_name=player_name,
                ally_code=ally_code,
                relic_tier=effective_tier,
            )
            matrix.units[unit_id].players_by_relic[effective_tier].append(player_info)

    def _convert_relic_tier(self, api_relic_tier: Optional[int]) -> Optional[int]:
        """
        Convert API relic_tier value to actual relic level.

        SWGOH.GG API encoding: None=not G13, 1=G13 no relic, 2=R0, 3=R1, ..., 11=R9
        Formula: actual_relic = relic_tier - 2 (when relic_tier >= 3)
        """
        if api_relic_tier is None:
            return None

        if api_relic_tier < 3:
            # G13 but no relic (tier 1 or 2), not eligible for ROTE
            return None

        return api_relic_tier - 2


class PathEligibilityFilter:
    """
    Filters units based on path eligibility.
    Dark Side path = alignment 2, Light Side = alignment 1, Neutral = all.
    """

    @staticmethod
    def filter_by_path(
        matrix: CoverageMatrix, path: RotePath
    ) -> Dict[str, UnitCoverage]:
        """Filter coverage matrix units by path eligibility."""
        filtered = {}

        for unit_id, coverage in matrix.units.items():
            if PathEligibilityFilter.is_eligible_for_path(coverage, path):
                filtered[unit_id] = coverage

        return filtered

    @staticmethod
    def is_eligible_for_path(coverage: UnitCoverage, path: RotePath) -> bool:
        """Check if a unit is eligible for a specific path."""
        if path == RotePath.DARK_SIDE:
            return coverage.alignment == RoteConfig.ALIGNMENT_DARK
        elif path == RotePath.LIGHT_SIDE:
            return coverage.alignment == RoteConfig.ALIGNMENT_LIGHT
        else:  # NEUTRAL
            return True

    @staticmethod
    def filter_characters_only(
        units: Dict[str, UnitCoverage],
    ) -> Dict[str, UnitCoverage]:
        """Filter to only include characters (combat_type=1), excluding ships."""
        return {
            unit_id: coverage
            for unit_id, coverage in units.items()
            if coverage.combat_type == 1
        }


class RoteRequirementsLoader:
    """Loads ROTE platoon requirements from JSON configuration file."""

    DEFAULT_PATH = Path("data") / "rote_platoon_requirements.json"

    @classmethod
    def load(cls, path: Optional[Path] = None) -> SimpleRoteRequirements:
        """Load ROTE requirements from JSON file."""
        file_path = path or cls.DEFAULT_PATH

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return SimpleRoteRequirements(**data)


@dataclass
class RequirementCoverage:
    """Coverage analysis for a single platoon requirement."""

    requirement: UnitRequirement
    players_available: int
    player_names: List[str]
    coverage_ratio: float  # players_available / guild_size


class CoverageAnalyzer:
    """Analyzes coverage matrix against platoon requirements."""

    def __init__(
        self,
        coverage_matrix: CoverageMatrix,
        requirements: SimpleRoteRequirements,
    ):
        self.matrix = coverage_matrix
        self.requirements = requirements

    def analyze_requirement(self, requirement: UnitRequirement) -> RequirementCoverage:
        """Analyze coverage for a single requirement."""
        players = self.matrix.get_players_at_relic(
            requirement.unit_id, requirement.min_relic
        )

        player_names = [p.player_name for p in players]

        return RequirementCoverage(
            requirement=requirement,
            players_available=len(players),
            player_names=player_names,
            coverage_ratio=(
                len(players) / self.matrix.member_count
                if self.matrix.member_count > 0
                else 0.0
            ),
        )

    def analyze_all_requirements(self) -> List[RequirementCoverage]:
        """Analyze coverage for all requirements."""
        results = []
        for req in self.requirements.requirements:
            results.append(self.analyze_requirement(req))
        return results

    def get_coverage_summary_by_territory(
        self,
    ) -> Dict[Tuple[RotePath, str], Dict[str, int]]:
        """Get coverage summary by territory. Returns (path, territory) -> {total_slots, covered_slots}."""
        summary: Dict[Tuple[RotePath, str], Dict[str, int]] = {}

        for req in self.requirements.requirements:
            key = (req.path, req.territory)
            if key not in summary:
                summary[key] = {"total_slots": 0, "covered_slots": 0}

            summary[key]["total_slots"] += req.count

            players_available = self.matrix.get_count_at_relic(
                req.unit_id, req.min_relic
            )
            summary[key]["covered_slots"] += min(players_available, req.count)

        return summary


def build_coverage_matrix(
    rosters: List[PlayerResponse],
    units_data: UnitsResponse,
    guild_name: str,
    guild_id: str,
) -> CoverageMatrix:
    """Build a coverage matrix from guild rosters."""
    builder = CoverageMatrixBuilder(units_data)
    return builder.build_from_rosters(rosters, guild_name, guild_id)


def load_requirements(path: Optional[Path] = None) -> SimpleRoteRequirements:
    """Load ROTE platoon requirements from JSON."""
    return RoteRequirementsLoader.load(path)
