"""Shared progress and distance scoring utilities."""

from typing import Dict, Optional


class ProgressScorer:
    """Reusable scorer for relic/gear/star progress calculations."""

    def __init__(
        self,
        relic_weight: float,
        gear_weight: float,
        star_weight: float,
        relic_star_requirements: Dict[int, int],
        relic_costs: Optional[Dict[int, float]] = None,
    ):
        self.relic_weight = relic_weight
        self.gear_weight = gear_weight
        self.star_weight = star_weight
        self.relic_star_requirements = relic_star_requirements
        self.relic_costs = relic_costs

    def required_stars_for_relic(self, relic_level: int) -> int:
        """Minimum stars needed to reach a given relic level."""
        return self.relic_star_requirements.get(relic_level, 7)

    def unit_distance(
        self,
        relic_tier: int,
        gear_level: int,
        rarity: int,
        required_relic: int,
    ) -> float:
        """Distance to reach required relic using configured weights."""
        star_gap = max(0, self.required_stars_for_relic(required_relic) - rarity)
        if relic_tier >= required_relic:
            return 0.0
        if relic_tier >= 0:
            relic_gap, gear_gap = required_relic - relic_tier, 0
        elif gear_level == 13:
            relic_gap, gear_gap = required_relic, 0
        else:
            relic_gap, gear_gap = required_relic, 13 - gear_level
        return (
            relic_gap * self.relic_weight
            + gear_gap * self.gear_weight
            + star_gap * self.star_weight
        )

    def gear_distance(
        self,
        gear_level: int,
        rarity: int,
        required_gear: int,
        required_stars: int,
    ) -> float:
        """Distance for a pure gear/star target."""
        return (
            max(0, required_gear - gear_level) * self.gear_weight
            + max(0, required_stars - rarity) * self.star_weight
        )

    def relic_upgrade_cost(self, current_relic: int, target_relic: int) -> float:
        """Cost to upgrade from current relic to target using optional tier costs."""
        if current_relic >= target_relic:
            return 0.0
        if not self.relic_costs:
            return (target_relic - max(current_relic, 0)) * self.relic_weight

        start_tier = max(1, current_relic + 1)
        total_cost = 0.0
        for tier in range(start_tier, target_relic + 1):
            total_cost += self.relic_costs.get(tier, 10.0)
        return total_cost
