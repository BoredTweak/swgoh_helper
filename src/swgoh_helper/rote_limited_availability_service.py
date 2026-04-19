"""Shared service for calculating ROTE limited-availability unit targets."""

from collections import defaultdict
from typing import Dict, List, Tuple

from .constants import LIMITED_AVAILABILITY_BASE_THRESHOLD
from .models.rote import CoverageMatrix, SimpleRoteRequirements

LimitedTarget = Tuple[str, str, int, Dict[str, int], int, List[str], int, int]


class LimitedAvailabilityService:
    """Builds consistent limited-availability targets across commands."""

    def __init__(
        self,
        coverage_matrix: CoverageMatrix,
        requirements: SimpleRoteRequirements,
        base_owner_threshold: int = LIMITED_AVAILABILITY_BASE_THRESHOLD,
    ):
        self.matrix = coverage_matrix
        self.requirements = requirements
        self.base_owner_threshold = base_owner_threshold

    @staticmethod
    def effective_threshold(total_slots: int, base_threshold: int) -> int:
        """Return the scarcity threshold for a requirement."""
        return max(base_threshold, total_slots)

    @classmethod
    def is_limited(
        cls,
        owner_count: int,
        total_slots: int,
        base_threshold: int,
    ) -> bool:
        """Return whether ownership is limited for the required slot volume."""
        return owner_count <= cls.effective_threshold(total_slots, base_threshold)

    def get_targets(self, include_zero_owners: bool = True) -> List[LimitedTarget]:
        """Return limited targets as tuples sorted by scarcity and demand."""
        targets: List[LimitedTarget] = []
        for unit_id, min_relic, slots in self._aggregate_requirement_slots():
            owners = self.matrix.get_players_at_relic(unit_id, min_relic)
            owner_count = len(owners)
            total_slots = sum(slots.values())
            threshold = self.effective_threshold(total_slots, self.base_owner_threshold)
            if not self.is_limited(owner_count, total_slots, self.base_owner_threshold):
                continue
            if not include_zero_owners and owner_count <= 0:
                continue
            unit_name = self._resolve_unit_name(unit_id, slots)
            targets.append(
                (
                    unit_id,
                    unit_name,
                    min_relic,
                    slots,
                    total_slots,
                    [player.player_name for player in owners],
                    owner_count,
                    threshold,
                )
            )
        return sorted(targets, key=lambda target: (target[6], -target[4], target[1]))

    def _aggregate_requirement_slots(self) -> List[Tuple[str, int, Dict[str, int]]]:
        slots_by_target: Dict[Tuple[str, int], Dict[str, int]] = defaultdict(dict)
        for requirement in self.requirements.requirements:
            key = (requirement.unit_id, requirement.min_relic)
            territory_slots = slots_by_target[key]
            territory_slots[requirement.territory] = (
                territory_slots.get(requirement.territory, 0) + requirement.count
            )
        return [
            (unit_id, min_relic, slots)
            for (unit_id, min_relic), slots in slots_by_target.items()
        ]

    def _resolve_unit_name(self, unit_id: str, slots: Dict[str, int]) -> str:
        coverage = self.matrix.get_coverage(unit_id)
        if coverage is not None:
            return coverage.unit_name
        for requirement in self.requirements.requirements:
            if requirement.unit_id == unit_id and requirement.territory in slots:
                return requirement.unit_name
        return unit_id
