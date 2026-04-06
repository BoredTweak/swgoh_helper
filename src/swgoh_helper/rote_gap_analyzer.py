"""
ROTE Gap Analyzer - Phase 4 Implementation

Analyzes platoon coverage to identify gaps where the guild lacks sufficient
player coverage for specific unit requirements.
"""

from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from .models.rote import (
    SimpleRoteRequirements,
    UnitRequirement,
    CoverageMatrix,
    GapSeverity,
    PlatoonGap,
)

UnitGapKey = Tuple[str, int]
AggregatedGap = Tuple[List[PlatoonGap], int, int]


class GapAnalyzer:
    """Analyzes platoon coverage to identify and classify gaps."""

    CRITICAL_THRESHOLD = 3
    WARNING_THRESHOLD = 10

    def __init__(
        self,
        coverage_matrix: CoverageMatrix,
        requirements: SimpleRoteRequirements,
    ):
        self.matrix = coverage_matrix
        self.requirements = requirements

    def classify_severity(
        self, players_available: int, slots_needed: int
    ) -> GapSeverity:
        """Classify the severity of a gap based on player availability."""
        if players_available >= slots_needed + self.WARNING_THRESHOLD:
            return GapSeverity.OVERFILLED
        elif players_available >= slots_needed:
            buffer = players_available - slots_needed
            if buffer >= self.CRITICAL_THRESHOLD:
                return GapSeverity.HEALTHY
            else:
                return GapSeverity.WARNING
        else:
            if players_available < self.CRITICAL_THRESHOLD:
                return GapSeverity.CRITICAL
            else:
                return GapSeverity.WARNING

    def analyze_requirement(self, req: UnitRequirement) -> PlatoonGap:
        """Analyze a single platoon requirement for gaps."""
        players = self.matrix.get_players_at_relic(req.unit_id, req.min_relic)
        player_names = [p.player_name for p in players]
        players_available = len(players)

        severity = self.classify_severity(players_available, req.count)
        slots_unfillable = max(0, req.count - players_available)

        # Get unit name from matrix or use ID
        coverage = self.matrix.get_coverage(req.unit_id)
        unit_name = coverage.unit_name if coverage else req.unit_id

        return PlatoonGap(
            unit_id=req.unit_id,
            unit_name=unit_name,
            path=req.path,
            territory=req.territory,
            min_relic=req.min_relic,
            slots_needed=req.count,
            players_available=players_available,
            player_names=player_names,
            coverage_ratio=(
                players_available / self.matrix.member_count
                if self.matrix.member_count > 0
                else 0.0
            ),
            severity=severity,
            slots_unfillable=slots_unfillable,
        )

    def analyze_all_requirements(self) -> List[PlatoonGap]:
        """Analyze every requirement and return full coverage snapshots."""
        return [
            self.analyze_requirement(requirement)
            for requirement in self.requirements.requirements
        ]

    def get_gaps_by_unit(
        self, gaps: Optional[List[PlatoonGap]] = None
    ) -> Dict[UnitGapKey, AggregatedGap]:
        """Aggregate gaps by (unit_id, relic) for cross-consumer consistency."""
        gaps_to_aggregate = gaps if gaps is not None else self.get_all_gaps()
        grouped: Dict[UnitGapKey, List[PlatoonGap]] = defaultdict(list)
        for gap in gaps_to_aggregate:
            grouped[(gap.unit_id, gap.min_relic)].append(gap)

        aggregated: Dict[UnitGapKey, AggregatedGap] = {}
        for unit_key, unit_gaps in grouped.items():
            total_slots = sum(gap.slots_needed for gap in unit_gaps)
            total_unfillable = sum(gap.slots_unfillable for gap in unit_gaps)
            aggregated[unit_key] = (unit_gaps, total_slots, total_unfillable)
        return aggregated

    def get_critical_gaps(self) -> List[PlatoonGap]:
        """Get all critical gaps across all paths."""
        return [
            gap
            for gap in self.analyze_all_requirements()
            if gap.severity == GapSeverity.CRITICAL and gap.is_gap
        ]

    def get_all_gaps(self) -> List[PlatoonGap]:
        """Get all gaps where we can't fill all slots."""
        return [gap for gap in self.analyze_all_requirements() if gap.is_gap]
