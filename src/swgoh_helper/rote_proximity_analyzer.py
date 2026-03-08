"""
ROTE Proximity Analyzer

Finds players who are closest to meeting platoon requirements for gaps.
Considers relic level, gear level, and star rarity when calculating proximity.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Tuple

from .rote_models import SimpleRoteRequirements
from .rote_coverage import CoverageMatrix, PlayerUnitInfo
from .rote_gap_analyzer import GapAnalyzer, PlatoonGap


class ProgressStage(str, Enum):
    """Stage of progress toward a relic requirement."""

    RELICED = "reliced"  # Has relics, needs more relic levels
    GEAR_13 = "gear_13"  # At G13 but no relic yet
    GEARING = "gearing"  # Below G13, needs gear
    STAR_GATED = "star_gated"  # Needs more stars before can reach required relic


@dataclass
class PlayerProgress:
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

    @property
    def status_string(self) -> str:
        """Human-readable status string."""
        if self.current_relic >= 0:
            return f"R{self.current_relic}"
        else:
            return f"G{self.gear_level} {self.rarity}*"


@dataclass
class GapProximityReport:
    """Report of players closest to filling a specific gap."""

    gap: PlatoonGap
    closest_players: List[PlayerProgress]
    slots_to_fill: int  # How many more slots need filling


class ProximityAnalyzer:
    """
    Analyzes player proximity to platoon requirements.

    Relic level requirements and star gates:
    - Relic 1-2: Requires 5 stars (effectively no gate at G13)
    - Relic 3: Requires 5 stars
    - Relic 4: Requires 6 stars
    - Relic 5-9: Requires 7 stars
    """

    # Star requirements for each relic level
    RELIC_STAR_REQUIREMENTS = {
        0: 0,  # G13 no relic
        1: 5,
        2: 5,
        3: 5,
        4: 6,
        5: 7,
        6: 7,
        7: 7,
        8: 7,
        9: 7,
    }

    # Weight factors for distance calculation
    RELIC_WEIGHT = 1.0  # Each relic level
    GEAR_WEIGHT = 0.5  # Each gear level to G13
    STAR_WEIGHT = 2.0  # Each missing star

    def __init__(
        self,
        coverage_matrix: CoverageMatrix,
        requirements: SimpleRoteRequirements,
    ):
        self.matrix = coverage_matrix
        self.requirements = requirements
        self.gap_analyzer = GapAnalyzer(coverage_matrix, requirements)

    def get_required_stars(self, relic_level: int) -> int:
        """Get the minimum star level required for a relic level."""
        return self.RELIC_STAR_REQUIREMENTS.get(relic_level, 7)

    def calculate_player_progress(
        self,
        player: PlayerUnitInfo,
        unit_name: str,
        required_relic: int,
    ) -> PlayerProgress:
        """Calculate a player's progress toward a relic requirement."""
        required_stars = self.get_required_stars(required_relic)

        # Calculate gaps
        star_gap = max(0, required_stars - player.rarity)

        if player.relic_tier >= 0:
            # Player has relics
            relic_gap = max(0, required_relic - player.relic_tier)
            gear_gap = 0

            if star_gap > 0:
                stage = ProgressStage.STAR_GATED
            else:
                stage = ProgressStage.RELICED
        elif player.gear_level == 13:
            # At G13 but not reliced yet
            relic_gap = required_relic
            gear_gap = 0

            if star_gap > 0:
                stage = ProgressStage.STAR_GATED
            else:
                stage = ProgressStage.GEAR_13
        else:
            # Below G13
            relic_gap = required_relic
            gear_gap = 13 - player.gear_level

            if star_gap > 0:
                stage = ProgressStage.STAR_GATED
            else:
                stage = ProgressStage.GEARING

        # Calculate distance score
        distance_score = (
            relic_gap * self.RELIC_WEIGHT
            + gear_gap * self.GEAR_WEIGHT
            + star_gap * self.STAR_WEIGHT
        )

        return PlayerProgress(
            player_name=player.player_name,
            ally_code=player.ally_code,
            unit_id=player.relic_tier,  # Store for reference
            unit_name=unit_name,
            required_relic=required_relic,
            current_relic=player.relic_tier,
            gear_level=player.gear_level,
            rarity=player.rarity,
            stage=stage,
            relic_gap=relic_gap,
            gear_gap=gear_gap,
            star_gap=star_gap,
            distance_score=distance_score,
        )

    def find_closest_players_for_gap(
        self,
        gap: PlatoonGap,
        max_results: int = 10,
        exclude_qualified: bool = True,
    ) -> GapProximityReport:
        """
        Find players closest to meeting a gap requirement.

        Args:
            gap: The platoon gap to analyze
            max_results: Maximum number of closest players to return
            exclude_qualified: If True, exclude players who already qualify

        Returns:
            GapProximityReport with the closest players
        """
        coverage = self.matrix.get_coverage(gap.unit_id)
        unit_name = coverage.unit_name if coverage else gap.unit_id

        if exclude_qualified:
            candidates = self.matrix.get_players_below_relic(gap.unit_id, gap.min_relic)
        else:
            candidates = self.matrix.get_all_players(gap.unit_id)

        progress_list = [
            self.calculate_player_progress(player, unit_name, gap.min_relic)
            for player in candidates
        ]
        progress_list.sort(key=lambda p: (p.distance_score, p.player_name))
        closest = progress_list[:max_results]

        return GapProximityReport(
            gap=gap,
            closest_players=closest,
            slots_to_fill=gap.slots_unfillable,
        )

    def analyze_all_gaps(
        self,
        max_players_per_gap: int = 5,
        min_severity: str = "warning",
    ) -> List[GapProximityReport]:
        """
        Analyze all gaps and find closest players for each.

        Args:
            max_players_per_gap: Max closest players to show per gap
            min_severity: Minimum severity to include ("critical", "warning")

        Returns:
            List of GapProximityReport for each gap
        """
        all_gaps = self.gap_analyzer.get_all_gaps()

        reports = []
        for gap in all_gaps:
            if min_severity == "critical" and gap.severity.value != "critical":
                continue

            report = self.find_closest_players_for_gap(
                gap, max_results=max_players_per_gap
            )

            if report.closest_players:
                reports.append(report)

        severity_order = {"critical": 0, "warning": 1, "healthy": 2, "overfilled": 3}
        reports.sort(
            key=lambda r: (
                severity_order.get(r.gap.severity.value, 99),
                -r.slots_to_fill,
                r.gap.unit_name,
            )
        )

        return reports

    def get_farming_recommendations(
        self,
        max_recommendations: int = 20,
    ) -> List[Tuple[str, str, List[PlayerProgress]]]:
        """
        Get farming recommendations grouped by unit.

        Returns tuples of (unit_name, required_relic, closest_players)
        """
        all_gaps = self.gap_analyzer.get_all_gaps()
        unit_gaps: Dict[str, List[PlatoonGap]] = {}
        for gap in all_gaps:
            key = f"{gap.unit_id}_{gap.min_relic}"
            if key not in unit_gaps:
                unit_gaps[key] = []
            unit_gaps[key].append(gap)

        recommendations = []
        for key, gaps in unit_gaps.items():
            gap = gaps[0]
            total_unfillable = sum(g.slots_unfillable for g in gaps)

            if total_unfillable == 0:
                continue

            report = self.find_closest_players_for_gap(gap, max_results=15)
            if report.closest_players:
                recommendations.append(
                    (
                        gap.unit_name,
                        f"R{gap.min_relic}",
                        report.closest_players,
                    )
                )

        recommendations.sort(
            key=lambda r: (
                min(p.distance_score for p in r[2]) if r[2] else float("inf"),
                r[0],  # unit name
            )
        )

        return recommendations[:max_recommendations]


def format_proximity_report(report: GapProximityReport) -> str:
    """Format a proximity report as a string for display."""
    lines = [
        f"\n{report.gap.unit_name} R{report.gap.min_relic} "
        f"({report.gap.territory}) - {report.slots_to_fill} slot(s) unfilled"
    ]

    if not report.closest_players:
        lines.append("  No players have this unit")
    else:
        lines.append("  Closest players:")
        for p in report.closest_players:
            status = p.status_string

            if p.stage == ProgressStage.STAR_GATED:
                note = f"needs {p.star_gap}★ first"
            elif p.stage == ProgressStage.GEARING:
                note = f"needs G13 (+{p.gear_gap} gear)"
            elif p.stage == ProgressStage.GEAR_13:
                note = f"needs relic (+{p.relic_gap}R)"
            else:
                note = f"+{p.relic_gap}R to reach R{p.required_relic}"

            lines.append(f"    • {p.player_name}: {status} ({note})")

    return "\n".join(lines)
