"""ROTE bottleneck analysis based on shared limited-availability calculations."""

from typing import List

from .constants import LIMITED_AVAILABILITY_BASE_THRESHOLD
from .models.rote import (
    SimpleRoteRequirements,
    CoverageMatrix,
    UnicornUnit,
)
from .rote_limited_availability_service import LimitedAvailabilityService


class BottleneckAnalyzer:
    """Identifies bottleneck players and unicorn units."""

    def __init__(
        self,
        coverage_matrix: CoverageMatrix,
        requirements: SimpleRoteRequirements,
    ):
        self.matrix = coverage_matrix
        self.requirements = requirements

    def identify_unicorn_units(self) -> List[UnicornUnit]:
        """Identify limited units using owner count relative to required slots."""
        service = LimitedAvailabilityService(
            self.matrix,
            self.requirements,
            base_owner_threshold=LIMITED_AVAILABILITY_BASE_THRESHOLD,
        )
        unicorns = []
        for (
            unit_id,
            unit_name,
            min_relic,
            slots,
            _,
            owner_names,
            owner_count,
            _,
        ) in service.get_targets():
            unicorns.append(
                UnicornUnit(
                    unit_id=unit_id,
                    unit_name=unit_name,
                    min_relic=min_relic,
                    owner_names=owner_names,
                    owner_count=owner_count,
                    slots_per_territory=slots,
                )
            )

        # Sort by owner count (sole owners first), then by total slots needed
        return sorted(unicorns, key=lambda u: (u.owner_count, -u.total_slots_needed))
