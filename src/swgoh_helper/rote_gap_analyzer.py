"""
ROTE Gap Analyzer - Phase 4 Implementation

Analyzes platoon coverage to identify gaps where the guild lacks sufficient
player coverage for specific unit requirements.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List

from .rote_models import RotePath, SimpleRoteRequirements, UnitRequirement
from .rote_coverage import CoverageMatrix, RoteConfig


class GapSeverity(Enum):
    """Severity levels for platoon gaps."""

    CRITICAL = "critical"  # < 3 players available
    WARNING = "warning"  # 3-9 players available
    HEALTHY = "healthy"  # 10+ players available
    OVERFILLED = "overfilled"  # More players than slots needed


@dataclass
class PlatoonGap:
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

    @property
    def is_gap(self) -> bool:
        """Returns True if this represents an actual gap (not enough players)."""
        return self.players_available < self.slots_needed


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
        if players_available >= slots_needed + 10:
            return GapSeverity.OVERFILLED
        elif players_available >= slots_needed:
            buffer = players_available - slots_needed
            if buffer >= self.WARNING_THRESHOLD:
                return GapSeverity.HEALTHY
            elif buffer >= self.CRITICAL_THRESHOLD:
                return GapSeverity.WARNING
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

    def get_critical_gaps(self) -> List[PlatoonGap]:
        """Get all critical gaps across all paths."""
        critical = []
        for req in self.requirements.requirements:
            gap = self.analyze_requirement(req)
            if gap.severity == GapSeverity.CRITICAL and gap.is_gap:
                critical.append(gap)
        return critical

    def get_all_gaps(self) -> List[PlatoonGap]:
        """Get all gaps where we can't fill all slots."""
        gaps = []
        for req in self.requirements.requirements:
            gap = self.analyze_requirement(req)
            if gap.is_gap:
                gaps.append(gap)
        return gaps
