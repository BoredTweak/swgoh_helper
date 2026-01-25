"""
ROTE Bottleneck Analyzer - Phase 5 Implementation

Identifies bottleneck players who are sole/rare owners of required units,
and detects cross-planet deployment conflicts.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple

from .rote_models import SimpleRoteRequirements
from .rote_coverage import CoverageMatrix


@dataclass
class UnicornUnit:
    """A unit that only a few players have at the required relic level."""

    unit_id: str
    unit_name: str
    min_relic: int
    owner_names: List[str]
    owner_count: int
    territories_needed: List[str]  # Which territories need this unit
    total_slots_needed: int  # Total slots across all territories

    @property
    def is_sole_owner(self) -> bool:
        """Returns True if only one player has this unit."""
        return self.owner_count == 1

    @property
    def is_critical(self) -> bool:
        """Returns True if fewer than 3 players have this unit."""
        return self.owner_count < 3


class BottleneckAnalyzer:
    """Identifies bottleneck players and unicorn units."""

    UNICORN_THRESHOLD = 3

    def __init__(
        self,
        coverage_matrix: CoverageMatrix,
        requirements: SimpleRoteRequirements,
    ):
        self.matrix = coverage_matrix
        self.requirements = requirements

    def identify_unicorn_units(self) -> List[UnicornUnit]:
        """Identify units with few owners at required relic. Sorted by owner count."""
        unit_requirements: Dict[Tuple[str, int], Dict] = {}

        for req in self.requirements.requirements:
            key = (req.unit_id, req.min_relic)

            if key not in unit_requirements:
                unit_requirements[key] = {
                    "territories": [],
                    "total_slots": 0,
                }

            unit_requirements[key]["territories"].append(req.territory)
            unit_requirements[key]["total_slots"] += req.count

        # Check each unique (unit_id, min_relic) combination
        unicorns = []

        for (unit_id, min_relic), data in unit_requirements.items():
            players = self.matrix.get_players_at_relic(unit_id, min_relic)
            owner_count = len(players)

            if owner_count <= self.UNICORN_THRESHOLD:
                coverage = self.matrix.get_coverage(unit_id)
                unit_name = coverage.unit_name if coverage else unit_id

                unicorns.append(
                    UnicornUnit(
                        unit_id=unit_id,
                        unit_name=unit_name,
                        min_relic=min_relic,
                        owner_names=[p.player_name for p in players],
                        owner_count=owner_count,
                        territories_needed=data["territories"],
                        total_slots_needed=data["total_slots"],
                    )
                )

        # Sort by owner count (sole owners first), then by total slots needed
        return sorted(unicorns, key=lambda u: (u.owner_count, -u.total_slots_needed))
