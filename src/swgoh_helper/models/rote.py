"""
Pydantic models for Rise of the Empire (ROTE) Territory Battle.

This module contains all models related to ROTE platoon analysis,
coverage tracking, gap analysis, and farming recommendations.
"""

from collections import defaultdict
from enum import Enum
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, computed_field


# ===== Enums =====


class RotePath(str, Enum):
    """The three paths in ROTE Territory Battle."""

    DARK_SIDE = "dark_side"
    NEUTRAL = "neutral"
    LIGHT_SIDE = "light_side"


class UnitType(str, Enum):
    """Unit type - character or ship."""

    CHARACTER = "character"
    SHIP = "ship"


class GapSeverity(Enum):
    """Severity levels for platoon gaps."""

    CRITICAL = "critical"  # < 3 players available
    WARNING = "warning"  # 3-9 players available
    HEALTHY = "healthy"  # 10+ players available
    OVERFILLED = "overfilled"  # More players than slots needed


class ProgressStage(str, Enum):
    """Stage of progress toward a relic requirement."""

    RELICED = "reliced"  # Has relics, needs more relic levels
    GEAR_13 = "gear_13"  # At G13 but no relic yet
    GEARING = "gearing"  # Below G13, needs gear
    STAR_GATED = "star_gated"  # Needs more stars before can reach required relic


# ===== Requirements Models =====


class UnitRequirement(BaseModel):
    """A unit required at a specific relic level."""

    unit_id: str = Field(description="Unit base_id from SWGOH.GG")
    unit_name: str = Field(description="Display name for readability")
    min_relic: int = Field(ge=0, le=9, description="Minimum relic level required")
    path: RotePath = Field(description="Which path requires this unit")
    territory: str = Field(description="Territory/planet name (e.g., 'Mustafar')")
    count: int = Field(default=1, ge=1, description="How many slots require this unit")
    unit_type: UnitType = Field(
        default=UnitType.CHARACTER, description="Whether this is a character or ship"
    )


class SimpleRoteRequirements(BaseModel):
    """ROTE requirements that list units by relic tier."""

    version: str = Field(default="1.0")
    last_updated: str
    notes: Optional[str] = None
    requirements: List[UnitRequirement] = Field(default_factory=list)


# ===== Coverage Models =====


class PlayerUnitInfo(BaseModel):
    """Information about a player's ownership of a unit."""

    player_name: str
    ally_code: int
    relic_tier: int  # Actual relic (0-9), not API value
    gear_level: int = 13  # Gear level 1-13
    rarity: int = 7  # Star level 1-7


class UnitCoverage(BaseModel):
    """Coverage data for a single unit across the guild."""

    unit_id: str
    unit_name: str
    alignment: int  # 1=Light, 2=Dark
    combat_type: int  # 1=Character, 2=Ship
    categories: List[str] = Field(default_factory=list)

    # Players at each relic threshold: relic_level -> list of player info
    players_by_relic: Dict[int, List[PlayerUnitInfo]] = Field(
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

    def all_players(self) -> List[PlayerUnitInfo]:
        """Get all players who have this unit at any level."""
        result = []
        for players in self.players_by_relic.values():
            result.extend(players)
        return result

    def players_below_relic(self, required_relic: int) -> List[PlayerUnitInfo]:
        """Get players who have this unit but below the required relic threshold."""
        result = []
        for relic_level, players in self.players_by_relic.items():
            if relic_level < required_relic:
                result.extend(players)
        return result


class CoverageMatrix(BaseModel):
    """
    Complete coverage matrix for a guild.

    Maps unit_id -> UnitCoverage, providing easy lookup of which players
    have which units at which relic levels.
    """

    guild_name: str
    guild_id: str
    member_count: int
    units: Dict[str, UnitCoverage] = Field(default_factory=dict)

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

    def get_players_below_relic(
        self, unit_id: str, required_relic: int
    ) -> List[PlayerUnitInfo]:
        """Get players who have a unit but below the required relic level."""
        coverage = self.units.get(unit_id)
        if coverage is None:
            return []
        return coverage.players_below_relic(required_relic)

    def get_all_players(self, unit_id: str) -> List[PlayerUnitInfo]:
        """Get all players who have a unit at any level."""
        coverage = self.units.get(unit_id)
        if coverage is None:
            return []
        return coverage.all_players()

    def get_coverage_summary(self, unit_id: str) -> Dict[int, int]:
        """Get summary of player counts at each relic threshold for a unit.

        Args:
            unit_id: The unit ID to get coverage summary for.

        Returns:
            Dict mapping relic level (0-9) to count of players at that level or above.
        """
        coverage = self.units.get(unit_id)
        if coverage is None:
            return {i: 0 for i in range(10)}

        result = {}
        for relic_level in range(10):
            result[relic_level] = coverage.count_at_relic(relic_level)
        return result


class RequirementCoverage(BaseModel):
    """Coverage analysis for a single platoon requirement."""

    requirement: UnitRequirement
    players_available: int
    player_names: List[str]
    coverage_ratio: float  # players_available / guild_size


# ===== Gap Analysis Models =====


class PlatoonGap(BaseModel):
    """Represents a gap in platoon coverage for a specific unit requirement."""

    unit_id: str
    unit_name: str
    path: RotePath
    territory: str
    min_relic: int
    slots_needed: int
    players_available: int
    player_names: List[str]
    coverage_ratio: float  # players_available / guild_size
    severity: GapSeverity
    slots_unfillable: int  # How many slots can't be filled

    @computed_field
    @property
    def is_gap(self) -> bool:
        """Returns True if this represents an actual gap (not enough players)."""
        return self.players_available < self.slots_needed


# ===== Bottleneck Models =====


class UnicornUnit(BaseModel):
    """A unit that only a few players have at the required relic level."""

    unit_id: str
    unit_name: str
    min_relic: int
    owner_names: List[str]
    owner_count: int
    slots_per_territory: Dict[str, int]  # Territory -> slots needed

    @computed_field
    @property
    def territories_needed(self) -> List[str]:
        """List of territories that need this unit."""
        return list(self.slots_per_territory.keys())

    @computed_field
    @property
    def total_slots_needed(self) -> int:
        """Total slots needed across all territories."""
        return sum(self.slots_per_territory.values())

    @computed_field
    @property
    def is_sole_owner(self) -> bool:
        """Returns True if only one player has this unit."""
        return self.owner_count == 1

    @computed_field
    @property
    def is_critical(self) -> bool:
        """Returns True if fewer than 3 players have this unit."""
        return self.owner_count < 3


# ===== Proximity/Progress Models =====


class PlayerProgress(BaseModel):
    """A player's progress toward a specific unit requirement."""

    player_name: str
    ally_code: int
    unit_id: str
    unit_name: str
    required_relic: int

    # Current state
    current_relic: int  # -1 if not reliced
    gear_level: int
    rarity: int  # Star level

    # Progress metrics
    stage: ProgressStage
    relic_gap: int  # How many relic levels needed (0 if not reliced yet)
    gear_gap: int  # Gear levels to G13 (0 if at G13)
    star_gap: int  # Stars needed to unlock required relic level

    # Total "distance" score (lower = closer to requirement)
    distance_score: float

    @computed_field
    @property
    def status_string(self) -> str:
        """Human-readable status string."""
        if self.current_relic >= 0:
            return f"R{self.current_relic}"
        else:
            return f"G{self.gear_level} {self.rarity}*"


class GapProximityReport(BaseModel):
    """Report of players closest to filling a specific gap."""

    gap: PlatoonGap
    closest_players: List[PlayerProgress]
    slots_to_fill: int  # How many more slots need filling


class UnitRecommendation(BaseModel):
    """Farming recommendation for a single unit."""

    unit_id: str
    unit_name: str
    required_relic: int
    slots_unfillable: int
    closest_players: List[PlayerProgress]

    @computed_field
    @property
    def min_distance(self) -> float:
        """Minimum distance score among closest players."""
        if not self.closest_players:
            return float("inf")
        return min(p.distance_score for p in self.closest_players)


class TerritoryRecommendation(BaseModel):
    """Farming recommendations grouped by territory/planet."""

    territory: str
    path: str
    total_gaps: int
    total_slots_unfillable: int
    unit_recommendations: List[UnitRecommendation]


# ===== Bonus Zone Models =====


class PlayerUnitStatus(BaseModel):
    """Track which units a player has for a bonus zone."""

    player_name: str
    ally_code: int
    has_units: Dict[str, Tuple[bool, int]]  # unit_id -> (has_it, relic_tier)


class PlayerDistance(BaseModel):
    """A player's distance from qualifying for a bonus zone."""

    player_name: str
    distance: float  # Total distance (lower = closer to qualifying)
    details: str  # Human-readable status


class BonusZoneReadiness(BaseModel):
    """Readiness analysis for a bonus zone."""

    zone_name: str
    threshold: int
    qualifying_players: List[str]
    qualifying_count: int
    near_qualifying: List[PlayerDistance]  # Players sorted by distance
    distance_to_fill_gap: float  # Sum of distances for top N players needed to fill gap
    farmable_count: int  # How many players own all required units (can farm to qualify)
    is_unlockable: bool


class PrereqStatus(BaseModel):
    """Status of unlock prerequisites for a character."""

    can_unlock: bool  # Already has the character unlocked
    prereq_distance: float  # Distance to complete all prereqs (0 if can_unlock)
    missing_prereqs: List[str]  # Names of prereq units not at required level
    detail: str  # Human-readable summary


class UnitProgressStatus(BaseModel):
    """Progress data for a single unit (used in bonus zone analysis)."""

    has_unit: bool
    relic_tier: int  # -1 if not reliced
    gear_level: int  # 1-13
    rarity: int  # 1-7 stars
    distance: float  # Distance to R7 requirement


# ===== Personal Farm Recommendation Models =====


class PersonalFarmRecommendation(BaseModel):
    """A personalized farm recommendation for a specific player."""

    unit_id: str
    unit_name: str
    required_relic: int
    territories: List[str]  # Which territories need this unit

    # Player's current state
    current_relic: int  # -1 if not reliced
    gear_level: int
    rarity: int
    has_unit: bool

    # Progress metrics
    relic_gap: int
    gear_gap: int
    star_gap: int
    distance_score: float

    # Guild context
    guild_owners: int  # How many guild members already qualify
    slots_needed: int  # Total slots needed across all territories
    slots_unfillable: int  # How many slots can't be filled
    guild_density: float  # guild_owners / slots_needed (lower = more needed)

    # Priority scoring
    need_score: float  # Higher = guild needs this more
    priority_score: float  # Combined score (need + closeness)
    priority_rank: int = 0  # Rank among all recommendations

    @computed_field
    @property
    def status_string(self) -> str:
        """Human-readable status string."""
        if not self.has_unit:
            return "Not owned"
        elif self.current_relic >= 0:
            return f"R{self.current_relic}"
        else:
            return f"G{self.gear_level} {self.rarity}*"

    @computed_field
    @property
    def progress_summary(self) -> str:
        """Summary of what's needed to qualify."""
        if self.current_relic >= self.required_relic:
            return "Already qualifies!"

        parts = []
        if self.star_gap > 0:
            parts.append(f"+{self.star_gap}★")
        if self.gear_gap > 0:
            parts.append(f"+{self.gear_gap} gear")
        if self.relic_gap > 0:
            parts.append(f"+{self.relic_gap}R")

        return " ".join(parts) if parts else "Ready"


class PersonalFarmReport(BaseModel):
    """Complete farm recommendation report for a player."""

    player_name: str
    ally_code: int
    guild_name: str
    guild_member_count: int
    max_phase: Optional[str] = None

    # Summary stats
    total_gaps: int
    units_player_can_help: int
    units_player_already_qualifies: int

    # Recommendations sorted by priority
    recommendations: List[PersonalFarmRecommendation]

    # Units where player already qualifies (for reference)
    already_qualified: List[str] = Field(default_factory=list)
