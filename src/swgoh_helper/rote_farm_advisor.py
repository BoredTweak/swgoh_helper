"""
ROTE Farm Advisor

Provides personalized farming recommendations for a specific player based on:
1. Guild gaps - units the guild can't fill enough slots for
2. Guild density - units with fewer qualified owners are higher priority
3. Player progress - how close the player is to qualifying for each unit
"""

from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from .constants import MANDALORE_THRESHOLD, MIN_RELIC_TIER, ZEFFO_THRESHOLD
from .models import PlayerResponse, UnitData
from .models.rote import (
    CoverageMatrix,
    GapSeverity,
    PersonalFarmRecommendation,
    PersonalFarmReport,
    PlatoonGap,
    SimpleRoteRequirements,
)
from .rote_gap_analyzer import AggregatedGap, GapAnalyzer, UnitGapKey
from .rote_proximity_analyzer import ProximityAnalyzer

BonusUnlockContext = Dict[str, Tuple[bool, int, int]]
RequiredTarget = Tuple[str, List[str], int]
RequiredTargetMap = Dict[UnitGapKey, RequiredTarget]


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

    BONUS_ZONE_TERRITORIES = {"Zeffo", "Mandalore"}
    BONUS_ZONE_DISABLED_MULTIPLIER = 0.35
    LIMITED_AVAILABILITY_OWNER_THRESHOLD = 3
    LIMITED_AVAILABILITY_NEED_SCALE = 0.55
    BONUS_UNLOCK_TARGETS = {
        "Zeffo": [
            ("CEREJUNDA", "Cere Junda"),
            ("CALKESTIS", "Cal Kestis"),
            ("JEDIKNIGHTCAL", "Jedi Knight Cal Kestis"),
        ],
        "Mandalore": [
            ("MANDALORBOKATAN", "Bo-Katan (Mand'alor)"),
            ("THEMANDALORIANBESKARARMOR", "The Mandalorian (Beskar Armor)"),
        ],
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
        player_units = self._build_player_unit_lookup(player_roster)
        required_targets = self._required_target_details()
        unit_gaps = self.gap_analyzer.get_gaps_by_unit()
        bonus_unlock = self._build_bonus_unlock_context()

        recommendations = []
        already_qualified = self._collect_already_qualified(
            required_targets, player_units
        )

        for unit_key, aggregated_gap in unit_gaps.items():
            recommendation = self._build_recommendation(
                unit_key=unit_key,
                aggregated_gap=aggregated_gap,
                player_unit=player_units.get(unit_key[0]),
                include_unowned=include_unowned,
                bonus_unlock=bonus_unlock,
            )
            if recommendation is not None:
                recommendations.append(recommendation)

        recommendations.extend(
            self._build_bonus_unlock_recommendations(
                player_units=player_units,
                include_unowned=include_unowned,
                bonus_unlock=bonus_unlock,
            )
        )
        recommendations.extend(
            self._build_limited_availability_recommendations(
                required_targets=required_targets,
                player_units=player_units,
                include_unowned=include_unowned,
            )
        )
        recommendations = self._dedupe_recommendations(recommendations)

        recommendations = self._rank_recommendations(
            recommendations, max_recommendations
        )

        return PersonalFarmReport(
            player_name=player_roster.data.name,
            ally_code=player_roster.data.ally_code,
            guild_name=self.matrix.guild_name,
            guild_member_count=self.matrix.member_count,
            total_gaps=len(unit_gaps),
            units_player_can_help=len(recommendations),
            units_player_already_qualifies=len(already_qualified),
            recommendations=recommendations,
            already_qualified=already_qualified,
        )

    def _build_bonus_unlock_context(self) -> BonusUnlockContext:
        zeffo_ready = self._players_ready_zeffo()
        mandalore_ready = self._players_ready_mandalore()
        return {
            "Zeffo": (zeffo_ready >= ZEFFO_THRESHOLD, zeffo_ready, ZEFFO_THRESHOLD),
            "Mandalore": (
                mandalore_ready >= MANDALORE_THRESHOLD,
                mandalore_ready,
                MANDALORE_THRESHOLD,
            ),
        }

    def _players_ready_zeffo(self) -> int:
        cere = self._players_with_unit_at_relic("CEREJUNDA", MIN_RELIC_TIER)
        cal = self._players_with_unit_at_relic("CALKESTIS", MIN_RELIC_TIER)
        jkcal = self._players_with_unit_at_relic("JEDIKNIGHTCAL", MIN_RELIC_TIER)
        return len(cere & (cal | jkcal))

    def _players_ready_mandalore(self) -> int:
        bokatan = self._players_with_unit_at_relic("MANDALORBOKATAN", MIN_RELIC_TIER)
        beskar = self._players_with_unit_at_relic(
            "THEMANDALORIANBESKARARMOR", MIN_RELIC_TIER
        )
        return len(bokatan & beskar)

    def _players_with_unit_at_relic(self, unit_id: str, min_relic: int) -> set[int]:
        return {
            player.ally_code
            for player in self.matrix.get_players_at_relic(unit_id, min_relic)
        }

    def _required_target_details(self) -> RequiredTargetMap:
        target_names: Dict[UnitGapKey, str] = {}
        target_territories: Dict[UnitGapKey, set[str]] = defaultdict(set)
        target_slots: Dict[UnitGapKey, int] = defaultdict(int)
        for requirement in self.requirements.requirements:
            key = (requirement.unit_id, requirement.min_relic)
            if key not in target_names:
                target_names[key] = requirement.unit_name
            target_territories[key].add(requirement.territory)
            target_slots[key] += requirement.count

        details: RequiredTargetMap = {}
        for key, unit_name in target_names.items():
            details[key] = (
                unit_name,
                sorted(target_territories[key]),
                target_slots[key],
            )
        return details

    def _collect_already_qualified(
        self,
        required_targets: RequiredTargetMap,
        player_units: Dict[str, UnitData],
    ) -> List[str]:
        qualified = []
        for (unit_id, min_relic), (unit_name, _, _) in required_targets.items():
            has_unit, current_relic, _, _ = self._player_unit_state(
                player_units.get(unit_id)
            )
            if has_unit and current_relic >= min_relic:
                qualified.append(f"{unit_name} R{min_relic}")
        return sorted(qualified)

    def _build_limited_availability_recommendations(
        self,
        required_targets: RequiredTargetMap,
        player_units: Dict[str, UnitData],
        include_unowned: bool,
    ) -> List[PersonalFarmRecommendation]:
        recommendations = []
        for (unit_id, min_relic), (
            unit_name,
            territories,
            total_slots,
        ) in required_targets.items():
            guild_owners = self.matrix.get_count_at_relic(unit_id, min_relic)
            if (
                guild_owners <= 0
                or guild_owners > self.LIMITED_AVAILABILITY_OWNER_THRESHOLD
            ):
                continue
            recommendation = self._build_limited_target_recommendation(
                unit_id=unit_id,
                unit_name=unit_name,
                min_relic=min_relic,
                territories=territories,
                total_slots=total_slots,
                guild_owners=guild_owners,
                player_unit=player_units.get(unit_id),
                include_unowned=include_unowned,
            )
            if recommendation is not None:
                recommendations.append(recommendation)
        return recommendations

    def _build_limited_target_recommendation(
        self,
        unit_id: str,
        unit_name: str,
        min_relic: int,
        territories: List[str],
        total_slots: int,
        guild_owners: int,
        player_unit: Optional[UnitData],
        include_unowned: bool,
    ) -> Optional[PersonalFarmRecommendation]:
        has_unit, current_relic, gear_level, rarity = self._player_unit_state(
            player_unit
        )
        if (not has_unit and not include_unowned) or current_relic >= min_relic:
            return None

        progress = self._calculate_progress(
            current_relic,
            gear_level,
            rarity,
            min_relic,
            has_unit,
        )
        base_need = (self.LIMITED_AVAILABILITY_OWNER_THRESHOLD + 1 - guild_owners) / (
            self.LIMITED_AVAILABILITY_OWNER_THRESHOLD + 1
        )
        need_score = min(1.0, base_need * self.LIMITED_AVAILABILITY_NEED_SCALE)
        return PersonalFarmRecommendation(
            unit_id=unit_id,
            unit_name=unit_name,
            required_relic=min_relic,
            territories=territories,
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
            slots_unfillable=max(0, total_slots - guild_owners),
            guild_density=guild_owners / total_slots if total_slots > 0 else 1.0,
            need_score=need_score,
            priority_score=self._calculate_priority_score(
                progress["distance_score"], need_score
            ),
        )

    def _build_player_unit_lookup(
        self, player_roster: PlayerResponse
    ) -> Dict[str, UnitData]:
        """Build a lookup of player's units by base_id."""
        return {
            player_unit.data.base_id: player_unit.data
            for player_unit in player_roster.units
        }

    def _build_recommendation(
        self,
        unit_key: UnitGapKey,
        aggregated_gap: AggregatedGap,
        player_unit: Optional[UnitData],
        include_unowned: bool,
        bonus_unlock: BonusUnlockContext,
    ) -> Optional[PersonalFarmRecommendation]:
        unit_id, min_relic = unit_key
        has_unit, current_relic, gear_level, rarity = self._player_unit_state(
            player_unit
        )
        if not has_unit and not include_unowned:
            return None

        gaps, total_slots, total_unfillable = aggregated_gap
        gap = gaps[0]
        if current_relic >= min_relic:
            return None

        progress = self._calculate_progress(
            current_relic, gear_level, rarity, min_relic, has_unit
        )
        guild_owners = gap.players_available
        guild_density = guild_owners / total_slots if total_slots > 0 else 1.0
        need_score = self._calculate_need_score(
            guild_owners, total_slots, total_unfillable, gap.severity
        )
        need_score = self._apply_bonus_zone_weighting(need_score, gaps, bonus_unlock)
        return PersonalFarmRecommendation(
            unit_id=unit_id,
            unit_name=gap.unit_name,
            required_relic=min_relic,
            territories=sorted({current_gap.territory for current_gap in gaps}),
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
            priority_score=self._calculate_priority_score(
                progress["distance_score"], need_score
            ),
        )

    def _apply_bonus_zone_weighting(
        self,
        need_score: float,
        gaps: List[PlatoonGap],
        bonus_unlock: BonusUnlockContext,
    ) -> float:
        territories = {gap.territory for gap in gaps}
        for zone_name in self.BONUS_ZONE_TERRITORIES:
            unlockable, _, _ = bonus_unlock[zone_name]
            if zone_name in territories and not unlockable:
                return need_score * self.BONUS_ZONE_DISABLED_MULTIPLIER
        return need_score

    def _build_bonus_unlock_recommendations(
        self,
        player_units: Dict[str, UnitData],
        include_unowned: bool,
        bonus_unlock: BonusUnlockContext,
    ) -> List[PersonalFarmRecommendation]:
        recommendations = []
        for zone_name, targets in self.BONUS_UNLOCK_TARGETS.items():
            unlockable, qualifying_count, threshold = bonus_unlock[zone_name]
            if unlockable:
                continue
            for unit_id, unit_name in targets:
                recommendation = self._build_bonus_target_recommendation(
                    zone_name=zone_name,
                    unit_id=unit_id,
                    unit_name=unit_name,
                    player_unit=player_units.get(unit_id),
                    qualifying_count=qualifying_count,
                    threshold=threshold,
                    include_unowned=include_unowned,
                )
                if recommendation is not None:
                    recommendations.append(recommendation)
        return recommendations

    def _build_bonus_target_recommendation(
        self,
        zone_name: str,
        unit_id: str,
        unit_name: str,
        player_unit: Optional[UnitData],
        qualifying_count: int,
        threshold: int,
        include_unowned: bool,
    ) -> Optional[PersonalFarmRecommendation]:
        has_unit, current_relic, gear_level, rarity = self._player_unit_state(
            player_unit
        )
        if (not has_unit and not include_unowned) or current_relic >= MIN_RELIC_TIER:
            return None

        progress = self._calculate_progress(
            current_relic,
            gear_level,
            rarity,
            MIN_RELIC_TIER,
            has_unit,
        )
        guild_owners = self.matrix.get_count_at_relic(unit_id, MIN_RELIC_TIER)
        need_score = min(1.0, (threshold - qualifying_count) / threshold + 0.35)
        return PersonalFarmRecommendation(
            unit_id=unit_id,
            unit_name=unit_name,
            required_relic=MIN_RELIC_TIER,
            territories=[f"{zone_name} Bonus Unlock"],
            current_relic=current_relic,
            gear_level=gear_level,
            rarity=rarity,
            has_unit=has_unit,
            relic_gap=progress["relic_gap"],
            gear_gap=progress["gear_gap"],
            star_gap=progress["star_gap"],
            distance_score=progress["distance_score"],
            guild_owners=guild_owners,
            slots_needed=threshold,
            slots_unfillable=max(0, threshold - qualifying_count),
            guild_density=guild_owners / threshold,
            need_score=need_score,
            priority_score=self._calculate_priority_score(
                progress["distance_score"],
                need_score,
            ),
        )

    @staticmethod
    def _dedupe_recommendations(
        recommendations: List[PersonalFarmRecommendation],
    ) -> List[PersonalFarmRecommendation]:
        deduped: Dict[Tuple[str, int], PersonalFarmRecommendation] = {}
        for recommendation in recommendations:
            key = (recommendation.unit_id, recommendation.required_relic)
            existing = deduped.get(key)
            if (
                existing is None
                or recommendation.priority_score < existing.priority_score
            ):
                deduped[key] = recommendation
        return list(deduped.values())

    @staticmethod
    def _player_unit_state(
        player_unit: Optional[UnitData],
    ) -> Tuple[bool, int, int, int]:
        if player_unit is None:
            return False, -1, 0, 0
        relic_tier = getattr(player_unit, "relic_tier_or_minus_one", None)
        if not isinstance(relic_tier, int):
            relic_tier = UnitData.api_to_ui_relic_tier(
                getattr(player_unit, "relic_tier", None)
            )
            relic_tier = relic_tier if relic_tier is not None else -1
        return (
            True,
            relic_tier,
            getattr(player_unit, "gear_level", 0),
            getattr(player_unit, "rarity", 0),
        )

    def _rank_recommendations(
        self,
        recommendations: List[PersonalFarmRecommendation],
        max_recommendations: int,
    ) -> List[PersonalFarmRecommendation]:
        recommendations.sort(
            key=lambda recommendation: (
                recommendation.priority_score,
                -recommendation.need_score,
                recommendation.unit_name,
            )
        )
        for index, recommendation in enumerate(
            recommendations[:max_recommendations], start=1
        ):
            recommendation.priority_rank = index
        return recommendations[:max_recommendations]

    def _calculate_priority_score(
        self, distance_score: float, need_score: float
    ) -> float:
        normalized_distance = min(distance_score, 100) / 100
        return self.DISTANCE_WEIGHT * normalized_distance + self.NEED_WEIGHT * (
            1 - need_score
        )

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
        required_stars = (
            self.proximity_analyzer.progress_scorer.required_stars_for_relic(
                required_relic
            )
        )

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
            distance = self.proximity_analyzer.progress_scorer.relic_upgrade_cost(
                current_relic, required_relic
            )
        elif gear_level == 13:
            # At G13 but not reliced
            relic_gap = required_relic
            gear_gap = 0
            distance = self.proximity_analyzer.progress_scorer.relic_upgrade_cost(
                0, required_relic
            )
        else:
            # Below G13
            relic_gap = required_relic
            gear_gap = 13 - gear_level
            distance = (
                gear_gap * self.proximity_analyzer.GEAR_WEIGHT
                + self.proximity_analyzer.progress_scorer.relic_upgrade_cost(
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
