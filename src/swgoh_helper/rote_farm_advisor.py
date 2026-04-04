"""
ROTE Farm Advisor

Provides personalized farming recommendations for a specific player based on:
1. Guild gaps - units the guild can't fill enough slots for
2. Guild density - units with fewer qualified owners are higher priority
3. Player progress - how close the player is to qualifying for each unit
"""

from collections import defaultdict
from typing import Dict, List, Optional

from .models import PlayerResponse
from .models.rote import (
    CoverageMatrix,
    GapSeverity,
    PersonalFarmRecommendation,
    PersonalFarmReport,
    PlatoonGap,
    SimpleRoteRequirements,
)
from .rote_gap_analyzer import GapAnalyzer
from .rote_proximity_analyzer import ProximityAnalyzer


class FarmAdvisor:
    """
    Generates personalized farming recommendations based on guild needs.

    Scoring System:
    - Need Score: Based on how critically the guild needs the unit
      - Higher when fewer people have the unit vs slots needed
      - Scaled by severity (CRITICAL > WARNING)
    - Distance Score: How close the player is to qualifying
    - Priority Score: Combines need and distance to rank recommendations
    """

    # Weights for priority scoring
    NEED_WEIGHT = 0.6  # Weight for guild need
    DISTANCE_WEIGHT = 0.4  # Weight for player closeness

    # Need score multipliers by severity
    SEVERITY_MULTIPLIER = {
        GapSeverity.CRITICAL: 2.0,
        GapSeverity.WARNING: 1.0,
        GapSeverity.HEALTHY: 0.5,
        GapSeverity.OVERFILLED: 0.1,
    }

    def __init__(
        self,
        coverage_matrix: CoverageMatrix,
        requirements: SimpleRoteRequirements,
        proximity_analyzer: Optional[ProximityAnalyzer] = None,
    ):
        self.matrix = coverage_matrix
        self.requirements = requirements
        self.gap_analyzer = GapAnalyzer(coverage_matrix, requirements)
        self.proximity_analyzer = proximity_analyzer or ProximityAnalyzer(
            coverage_matrix, requirements
        )

    def get_player_recommendations(
        self,
        player_roster: PlayerResponse,
        max_recommendations: int = 20,
        include_unowned: bool = True,
    ) -> PersonalFarmReport:
        """
        Generate personalized farm recommendations for a player.

        Args:
            player_roster: The player's roster data
            max_recommendations: Maximum recommendations to return
            include_unowned: Whether to include units the player doesn't own

        Returns:
            PersonalFarmReport with prioritized recommendations
        """
        player_name = player_roster.data.name
        ally_code = player_roster.data.ally_code

        # Build player's unit lookup
        player_units = self._build_player_unit_lookup(player_roster)

        # Get all gaps and aggregate by unit
        all_gaps = self.gap_analyzer.get_all_gaps()
        unit_gaps = self._aggregate_gaps_by_unit(all_gaps)

        recommendations = []
        already_qualified = []

        for unit_key, (gaps, total_slots, total_unfillable) in unit_gaps.items():
            unit_id, min_relic = unit_key.rsplit("_", 1)
            min_relic = int(min_relic)

            # Get player's status for this unit
            player_unit = player_units.get(unit_id)
            has_unit = player_unit is not None

            if not has_unit and not include_unowned:
                continue

            # Get unit metadata
            gap = gaps[0]
            unit_name = gap.unit_name
            territories = list({g.territory for g in gaps})

            # Calculate player's progress
            if has_unit:
                current_relic = player_unit["relic_tier"]
                gear_level = player_unit["gear_level"]
                rarity = player_unit["rarity"]
            else:
                current_relic = -1
                gear_level = 0
                rarity = 0

            # Check if player already qualifies
            if current_relic >= min_relic:
                already_qualified.append(f"{unit_name} R{min_relic}")
                continue

            # Calculate progress metrics
            progress = self._calculate_progress(
                current_relic, gear_level, rarity, min_relic, has_unit
            )

            # Calculate guild density and need score
            guild_owners = gap.players_available
            guild_density = guild_owners / total_slots if total_slots > 0 else 1.0
            need_score = self._calculate_need_score(
                guild_owners, total_slots, total_unfillable, gap.severity
            )

            # Calculate priority score (lower = higher priority)
            # Normalize distance to 0-100 range for comparison
            normalized_distance = min(progress["distance_score"], 100) / 100
            # Invert need_score since higher need = higher priority
            priority_score = (
                self.DISTANCE_WEIGHT * normalized_distance
                + self.NEED_WEIGHT * (1 - need_score)
            )

            recommendations.append(
                PersonalFarmRecommendation(
                    unit_id=unit_id,
                    unit_name=unit_name,
                    required_relic=min_relic,
                    territories=sorted(territories),
                    current_relic=current_relic,
                    gear_level=gear_level,
                    rarity=rarity,
                    has_unit=has_unit,
                    relic_gap=progress["relic_gap"],
                    gear_gap=progress["gear_gap"],
                    star_gap=progress["star_gap"],
                    distance_score=progress["distance_score"],
                    guild_owners=guild_owners,
                    slots_needed=total_slots,
                    slots_unfillable=total_unfillable,
                    guild_density=guild_density,
                    need_score=need_score,
                    priority_score=priority_score,
                )
            )

        # Sort by priority (lower score = higher priority)
        recommendations.sort(
            key=lambda r: (r.priority_score, -r.need_score, r.unit_name)
        )

        # Assign ranks
        for i, rec in enumerate(recommendations):
            rec.priority_rank = i + 1

        # Truncate to max
        recommendations = recommendations[:max_recommendations]

        return PersonalFarmReport(
            player_name=player_name,
            ally_code=ally_code,
            guild_name=self.matrix.guild_name,
            guild_member_count=self.matrix.member_count,
            total_gaps=len(unit_gaps),
            units_player_can_help=len(recommendations),
            units_player_already_qualifies=len(already_qualified),
            recommendations=recommendations,
            already_qualified=already_qualified,
        )

    def _build_player_unit_lookup(
        self, player_roster: PlayerResponse
    ) -> Dict[str, Dict]:
        """Build a lookup of player's units by base_id."""
        lookup = {}
        for player_unit in player_roster.units:
            unit_data = player_unit.data
            relic_tier = self._convert_relic_tier(unit_data.relic_tier)
            lookup[unit_data.base_id] = {
                "relic_tier": relic_tier if relic_tier is not None else -1,
                "gear_level": unit_data.gear_level,
                "rarity": unit_data.rarity,
            }
        return lookup

    def _convert_relic_tier(self, api_relic_tier: Optional[int]) -> Optional[int]:
        """Convert API relic tier (2-11) to display tier (1-9)."""
        if api_relic_tier is None or api_relic_tier < 2:
            return None
        return api_relic_tier - 1

    def _aggregate_gaps_by_unit(
        self, gaps: List[PlatoonGap]
    ) -> Dict[str, tuple[List[PlatoonGap], int, int]]:
        """
        Aggregate gaps by unit_id and relic level.

        Returns dict of unit_key -> (gaps, total_slots, total_unfillable)
        """
        unit_gaps: Dict[str, List[PlatoonGap]] = defaultdict(list)
        for gap in gaps:
            key = f"{gap.unit_id}_{gap.min_relic}"
            unit_gaps[key].append(gap)

        result = {}
        for key, gap_list in unit_gaps.items():
            total_slots = sum(g.slots_needed for g in gap_list)
            total_unfillable = sum(g.slots_unfillable for g in gap_list)
            result[key] = (gap_list, total_slots, total_unfillable)

        return result

    def _calculate_progress(
        self,
        current_relic: int,
        gear_level: int,
        rarity: int,
        required_relic: int,
        has_unit: bool,
    ) -> Dict[str, float]:
        """Calculate progress metrics toward a relic requirement."""
        # Star requirements per relic level
        required_stars = self.proximity_analyzer.get_required_stars(required_relic)

        star_gap = max(0, required_stars - rarity) if has_unit else required_stars

        if not has_unit:
            # Estimate full farm distance
            gear_gap = 13
            relic_gap = required_relic
            distance = 100 + required_relic * 10  # Large penalty for not owning
        elif current_relic >= 0:
            # Already reliced
            relic_gap = max(0, required_relic - current_relic)
            gear_gap = 0
            distance = self.proximity_analyzer.calculate_relic_upgrade_cost(
                current_relic, required_relic
            )
        elif gear_level == 13:
            # At G13 but not reliced
            relic_gap = required_relic
            gear_gap = 0
            distance = self.proximity_analyzer.calculate_relic_upgrade_cost(
                0, required_relic
            )
        else:
            # Below G13
            relic_gap = required_relic
            gear_gap = 13 - gear_level
            distance = (
                gear_gap * self.proximity_analyzer.GEAR_WEIGHT
                + self.proximity_analyzer.calculate_relic_upgrade_cost(
                    0, required_relic
                )
            )

        # Add star gap penalty
        if star_gap > 0:
            distance += star_gap * self.proximity_analyzer.STAR_WEIGHT

        return {
            "relic_gap": relic_gap,
            "gear_gap": gear_gap,
            "star_gap": star_gap,
            "distance_score": distance,
        }

    def _calculate_need_score(
        self,
        guild_owners: int,
        total_slots: int,
        total_unfillable: int,
        severity: GapSeverity,
    ) -> float:
        """
        Calculate how much the guild needs this unit.

        Returns value from 0-1 where higher = more needed.
        """
        if total_slots == 0:
            return 0.0

        # Base need from coverage ratio
        coverage_ratio = guild_owners / total_slots
        base_need = 1 - min(coverage_ratio, 1.0)

        # Boost by severity
        severity_mult = self.SEVERITY_MULTIPLIER.get(severity, 1.0)

        # Extra boost if slots are actually unfillable
        if total_unfillable > 0:
            unfillable_boost = min(total_unfillable / total_slots, 1.0) * 0.5
        else:
            unfillable_boost = 0

        need_score = min(base_need * severity_mult + unfillable_boost, 1.0)
        return need_score
