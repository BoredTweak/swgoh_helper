"""Presentation layer for ROTE platoon analysis results."""

from collections import defaultdict

from .rote_coverage import CoverageAnalyzer, RoteConfig
from .rote_gap_analyzer import GapAnalyzer
from .rote_bottleneck_analyzer import BottleneckAnalyzer
from .rote_models import RotePath
from .rote_proximity_analyzer import ProximityAnalyzer, ProgressStage


class RotePresenter:
    """Formats ROTE platoon analysis as markdown for Discord sharing."""

    def format_results(
        self,
        analyzer: CoverageAnalyzer,
        matrix,
        gap_analyzer: GapAnalyzer,
        bottleneck_analyzer: BottleneckAnalyzer,
        proximity_analyzer: ProximityAnalyzer | None = None,
        by_territory: bool = False,
    ) -> str:
        """Generate complete formatted output."""
        lines = [
            f"**{matrix.guild_name}** ({matrix.member_count} members)",
            "",
            "**Coverage**",
        ]

        lines.extend(self._format_coverage(analyzer))
        lines.extend(self._format_gaps(gap_analyzer, bottleneck_analyzer))

        if proximity_analyzer:
            if by_territory:
                lines.extend(self._format_farming_by_territory(proximity_analyzer))
            else:
                lines.extend(self._format_farming(proximity_analyzer))

        return "\n".join(lines)

    def _format_coverage(self, analyzer: CoverageAnalyzer) -> list[str]:
        """Format coverage summary with emoji status."""
        summary = analyzer.get_coverage_summary_by_territory()
        lines = []
        paths = [RotePath.DARK_SIDE, RotePath.NEUTRAL, RotePath.LIGHT_SIDE]

        for i, path in enumerate(paths):
            path_territories = [
                (key, data) for key, data in summary.items() if key[0] == path
            ]
            if not path_territories:
                continue

            for (_, territory), data in sorted(
                path_territories,
                key=lambda x: RoteConfig.TERRITORY_PHASE.get(x[0][1], "99"),
            ):
                total = data["total_slots"]
                covered = data["covered_slots"]
                pct = (covered / total * 100) if total > 0 else 0
                phase = RoteConfig.TERRITORY_PHASE.get(territory, "?")

                status = "✅" if pct == 100 else ("⚠️" if pct >= 80 else "❌")
                lines.append(f"{status} P{phase} {territory}: {covered}/{total}")

            if i < len(paths) - 1:
                lines.append("")

        return lines

    def _format_gaps(
        self, gap_analyzer: GapAnalyzer, bottleneck_analyzer: BottleneckAnalyzer
    ) -> list[str]:
        """Format critical gaps and limited availability units."""
        lines = ["", "**Gaps**"]

        critical_gaps = gap_analyzer.get_critical_gaps()
        if not critical_gaps:
            lines.append("✅ No critical gaps")
        else:
            gaps_by_territory = defaultdict(list)
            for gap in critical_gaps:
                gaps_by_territory[(gap.path, gap.territory)].append(gap)

            for (path, territory), gaps in sorted(
                gaps_by_territory.items(),
                key=lambda x: (
                    x[0][0].value,
                    RoteConfig.TERRITORY_PHASE.get(x[0][1], "99"),
                ),
            ):
                phase = RoteConfig.TERRITORY_PHASE.get(territory, "?")
                lines.append(f"P{phase} {territory}:")
                for gap in sorted(
                    gaps, key=lambda g: (g.players_available, g.unit_name)
                ):
                    owners = (
                        f" ({', '.join(gap.player_names)})" if gap.player_names else ""
                    )
                    lines.append(
                        f"- {gap.unit_name} R{gap.min_relic}: "
                        f"{gap.players_available}/{gap.slots_needed}{owners}"
                    )
                lines.append("")

        # Limited availability (unicorn) units
        rare_units = [
            u for u in bottleneck_analyzer.identify_unicorn_units() if u.owner_count > 0
        ]
        if rare_units:
            lines.extend(["", "**Limited Availability**"])
            for u in sorted(rare_units, key=lambda x: x.owner_count):
                owners = ", ".join(u.owner_names[:3])
                lines.append(f"- {u.unit_name} R{u.min_relic} → {owners}")

        return lines

    def _format_farming(self, proximity_analyzer: ProximityAnalyzer) -> list[str]:
        """Format farming recommendations."""
        recommendations = proximity_analyzer.get_farming_recommendations(
            max_recommendations=15
        )
        if not recommendations:
            return []

        lines = ["", "**Farming Recommendations**"]
        for unit_name, relic_req, closest_players in recommendations:
            lines.append(f"- {unit_name} {relic_req}:")
            lines.extend(self._format_player_groups(closest_players, max_groups=3))
            lines.append("")

        return lines

    def _format_farming_by_territory(
        self, proximity_analyzer: ProximityAnalyzer
    ) -> list[str]:
        """Format farming recommendations grouped by territory."""
        from .constants import MAX_PLAYERS_PER_UNIT

        recommendations = proximity_analyzer.get_farming_recommendations_by_territory(
            max_players_per_unit=MAX_PLAYERS_PER_UNIT
        )
        if not recommendations:
            return []

        lines = ["", "**Farming Recommendations**"]
        for territory_rec in recommendations:
            phase = RoteConfig.TERRITORY_PHASE.get(territory_rec.territory, "?")
            lines.append(f"P{phase} {territory_rec.territory}:")

            for unit_rec in territory_rec.unit_recommendations:
                lines.append(
                    f"- {unit_rec.unit_name} R{unit_rec.required_relic} "
                    f"({unit_rec.slots_unfillable} unfilled)"
                )
                lines.extend(
                    self._format_player_groups(unit_rec.closest_players, max_groups=2)
                )
                lines.append("")

        return lines

    def _format_player_groups(self, players, max_groups: int) -> list[str]:
        """Group players by progress stage and format."""
        if not players:
            return ["  - (no players have this unit)"]

        groups = []
        current_group = []
        current_score = None

        for p in players:
            if current_score is None or p.distance_score == current_score:
                current_group.append(p)
                current_score = p.distance_score
            else:
                if current_group:
                    groups.append(current_group)
                current_group = [p]
                current_score = p.distance_score
        if current_group:
            groups.append(current_group)

        lines = []
        for group in groups[:max_groups]:
            first = group[0]
            if first.stage == ProgressStage.STAR_GATED:
                label = f"needs {first.star_gap}★"
            elif first.stage == ProgressStage.GEARING:
                label = f"needs G13 (+{first.gear_gap}g)"
            elif first.stage == ProgressStage.GEAR_13:
                label = "at G13"
            else:
                label = f"+{first.relic_gap}R"

            names = ", ".join(p.player_name for p in group)
            lines.append(f"  - {label}: {names}")

        return lines
