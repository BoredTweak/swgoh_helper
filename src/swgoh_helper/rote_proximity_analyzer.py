"""
ROTE Proximity Analyzer

Finds players who are closest to meeting platoon requirements for gaps.
Considers relic level, gear level, and star rarity when calculating proximity.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .constants import MAX_PLAYERS_PER_UNIT, RELIC_STAR_REQUIREMENTS
from .models.rote import (
    SimpleRoteRequirements,
    CoverageMatrix,
    PlayerUnitInfo,
    PlatoonGap,
    ProgressStage,
    PlayerProgress,
    GapProximityReport,
    UnitRecommendation,
    TerritoryRecommendation,
)
from .rote_gap_analyzer import GapAnalyzer
from .progress_scorer import ProgressScorer


def load_relic_costs(data_path: Optional[Path] = None) -> Dict[int, float]:
    """
    Load relic tier costs from the relic_costs.json data file.

    Returns:
        Dict mapping relic tier (1-10) to its relative cost weight.
    """
    if data_path is None:
        # Default to the data folder relative to this module
        data_path = Path(__file__).parent.parent.parent / "data" / "relic_costs.json"

    if data_path.exists():
        with open(data_path, "r") as f:
            data = json.load(f)
            weights = data.get("relative_weights", {})
            # Convert string keys to int, skip non-numeric keys like "description"
            return {int(k): float(v) for k, v in weights.items() if k.isdigit()}

    # Fallback defaults if file not found
    return {
        1: 1.0,
        2: 1.5,
        3: 2.0,
        4: 2.5,
        5: 4.0,
        6: 6.0,
        7: 10.0,
        8: 20.0,
        9: 30.0,
        10: 40.0,
    }


class ProximityAnalyzer:
    """
    Analyzes player proximity to platoon requirements.

    Relic level requirements and star gates:
    - Relic 1-2: Requires 5 stars (effectively no gate at G13)
    - Relic 3: Requires 5 stars
    - Relic 4: Requires 6 stars
    - Relic 5-9: Requires 7 stars
    """

    # Weight factors for non-relic distance calculation
    GEAR_WEIGHT = 2.0  # Each gear level to G13 (roughly equivalent to R1-R2)
    STAR_WEIGHT = 5.0  # Each missing star (significant farming)

    def __init__(
        self,
        coverage_matrix: CoverageMatrix,
        requirements: SimpleRoteRequirements,
        relic_costs: Optional[Dict[int, float]] = None,
    ):
        self.matrix = coverage_matrix
        self.requirements = requirements
        self.gap_analyzer = GapAnalyzer(coverage_matrix, requirements)
        self.relic_costs = (
            relic_costs if relic_costs is not None else load_relic_costs()
        )
        self.progress_scorer = ProgressScorer(
            relic_weight=1.0,
            gear_weight=self.GEAR_WEIGHT,
            star_weight=self.STAR_WEIGHT,
            relic_star_requirements=RELIC_STAR_REQUIREMENTS,
            relic_costs=self.relic_costs,
        )

    def calculate_player_progress(
        self,
        player: PlayerUnitInfo,
        unit_id: str,
        unit_name: str,
        required_relic: int,
    ) -> PlayerProgress:
        """Calculate a player's progress toward a relic requirement."""
        required_stars = self.progress_scorer.required_stars_for_relic(required_relic)

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
        relic_cost = self.progress_scorer.relic_upgrade_cost(
            player.relic_tier if player.relic_tier >= 0 else 0, required_relic
        )
        distance_score = (
            relic_cost + gear_gap * self.GEAR_WEIGHT + star_gap * self.STAR_WEIGHT
        )

        return PlayerProgress(
            player_name=player.player_name,
            ally_code=player.ally_code,
            unit_id=unit_id,
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
            self.calculate_player_progress(
                player, gap.unit_id, unit_name, gap.min_relic
            )
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
        max_players_per_gap: int = MAX_PLAYERS_PER_UNIT,
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
        max_recommendations: int = MAX_PLAYERS_PER_UNIT,
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

    def get_farming_recommendations_by_territory(
        self,
        max_players_per_unit: int = MAX_PLAYERS_PER_UNIT,
    ) -> List[TerritoryRecommendation]:
        """
        Get farming recommendations grouped by territory/planet.

        Each territory shows all units with gaps and the closest players
        who could fill them.

        Args:
            max_players_per_unit: Max closest players to show per unit gap

        Returns:
            List of TerritoryRecommendation, one per territory with gaps
        """
        all_gaps = self.gap_analyzer.get_all_gaps()

        # Group gaps by territory
        territory_gaps: Dict[str, List[PlatoonGap]] = {}
        for gap in all_gaps:
            if gap.slots_unfillable == 0:
                continue
            key = gap.territory
            if key not in territory_gaps:
                territory_gaps[key] = []
            territory_gaps[key].append(gap)

        recommendations = []
        for territory, gaps in territory_gaps.items():
            # Group by unit within territory
            unit_gaps: Dict[str, List[PlatoonGap]] = {}
            for gap in gaps:
                unit_key = f"{gap.unit_id}_{gap.min_relic}"
                if unit_key not in unit_gaps:
                    unit_gaps[unit_key] = []
                unit_gaps[unit_key].append(gap)

            unit_recs = []
            for unit_key, ugaps in unit_gaps.items():
                gap = ugaps[0]
                total_unfillable = sum(g.slots_unfillable for g in ugaps)

                report = self.find_closest_players_for_gap(
                    gap, max_results=max_players_per_unit
                )

                unit_recs.append(
                    UnitRecommendation(
                        unit_id=gap.unit_id,
                        unit_name=gap.unit_name,
                        required_relic=gap.min_relic,
                        slots_unfillable=total_unfillable,
                        closest_players=report.closest_players,
                    )
                )

            # Sort units by minimum distance (easiest to farm first)
            unit_recs.sort(key=lambda u: (u.min_distance, u.unit_name))

            path = gaps[0].path.value if gaps else "unknown"
            recommendations.append(
                TerritoryRecommendation(
                    territory=territory,
                    path=path,
                    total_gaps=len(unit_recs),
                    total_slots_unfillable=sum(u.slots_unfillable for u in unit_recs),
                    unit_recommendations=unit_recs,
                )
            )

        # Sort territories by total unfillable slots (worst first)
        recommendations.sort(key=lambda t: (-t.total_slots_unfillable, t.territory))

        return recommendations


def _format_players_grouped(
    players: List[PlayerProgress], indent: str = "", max_names_per_line: int = 10
) -> List[str]:
    """
    Group players by their progress status and format as condensed lines.

    Players with identical status (e.g., all R5 needing +2R) are combined.
    Lines with more than max_names_per_line names are truncated.
    """
    from collections import defaultdict

    # Group players by (status_string, note)
    groups: Dict[Tuple[str, str], List[str]] = defaultdict(list)

    for p in players:
        if p.stage == ProgressStage.STAR_GATED:
            note = f"needs {p.star_gap}* first"
        elif p.stage == ProgressStage.GEARING:
            note = f"+{p.gear_gap} gear to G13"
        elif p.stage == ProgressStage.GEAR_13:
            note = f"+relic to R{p.required_relic}"
        else:
            note = f"+{p.relic_gap}R to R{p.required_relic}"

        key = (p.status_string, note)
        groups[key].append(p.player_name)

    lines = []
    for (status, note), names in groups.items():
        if len(names) > max_names_per_line:
            names_str = (
                ", ".join(names[:max_names_per_line])
                + f" (+{len(names) - max_names_per_line} more)"
            )
        else:
            names_str = ", ".join(names)
        lines.append(f"{indent}{names_str}: {status} ({note})")

    return lines


def format_proximity_report(report: GapProximityReport) -> str:
    """Format a proximity report as a string for display."""
    lines = [
        f"\n{report.gap.unit_name} R{report.gap.min_relic} "
        f"({report.gap.territory}) - {report.slots_to_fill} slot(s) unfilled"
    ]

    if not report.closest_players:
        lines.append("  No players have this unit")
    else:
        lines.extend(_format_players_grouped(report.closest_players, indent="  "))

    return "\n".join(lines)


def format_territory_recommendations(
    recommendations: List[TerritoryRecommendation],
) -> str:
    """Format territory recommendations as a string for display."""
    if not recommendations:
        return "No farming recommendations - all platoon slots can be filled!"

    lines = []
    for territory_rec in recommendations:
        lines.append(
            f"\n{'='*60}\n"
            f"[{territory_rec.territory.upper()}] ({territory_rec.path})\n"
            f"   {territory_rec.total_gaps} unit(s) with gaps, "
            f"{territory_rec.total_slots_unfillable} total slots unfillable\n"
            f"{'='*60}"
        )

        for unit_rec in territory_rec.unit_recommendations:
            lines.append(
                f"\n  {unit_rec.unit_name} R{unit_rec.required_relic} "
                f"- {unit_rec.slots_unfillable} slot(s) unfilled"
            )

            if not unit_rec.closest_players:
                lines.append("    [!] No players have this unit")
            else:
                lines.extend(
                    _format_players_grouped(unit_rec.closest_players, indent="    ")
                )

    return "\n".join(lines)
