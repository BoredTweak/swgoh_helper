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
        output_format: str = "all",
    ) -> str:
        """Generate complete formatted output."""
        lines = [f"**{matrix.guild_name}** ({matrix.member_count} members)"]

        if output_format in {"all", "coverage"}:
            lines.extend(["", "**Coverage**"])
            lines.extend(self._format_coverage(analyzer))

        if output_format in {"all", "gaps"}:
            lines.extend(self._format_gaps(gap_analyzer, bottleneck_analyzer))

        if output_format == "owners":
            lines.extend(self._format_requirement_owners(analyzer))

        if proximity_analyzer:
            if output_format == "farming-by-territory":
                lines.extend(self._format_farming_by_territory(proximity_analyzer))
            elif output_format == "farming":
                lines.extend(self._format_farming(proximity_analyzer))
            elif output_format == "all":
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
                territories = self._format_slots_per_territory(u.slots_per_territory)
                lines.append(
                    f"- {u.unit_name} R{u.min_relic}: {territories} → {owners}"
                )

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

    def _format_requirement_owners(self, analyzer: CoverageAnalyzer) -> list[str]:
        """Format platoon requirement owners grouped by territory."""
        lines = ["", "**Requirement Owners**"]
        territories = self._group_requirements_by_territory(analyzer)

        for (path, territory), requirements in territories:
            phase = RoteConfig.TERRITORY_PHASE.get(territory, "?")
            lines.append(f"P{phase} {territory}:")
            for requirement in requirements:
                lines.append(self._format_requirement_owner_line(requirement, analyzer))
            lines.append("")

        return lines

    def _group_requirements_by_territory(
        self, analyzer: CoverageAnalyzer
    ) -> list[tuple[tuple[RotePath, str], list]]:
        """Group requirements by path and territory in report order."""
        grouped = defaultdict(list)
        for requirement in analyzer.requirements.requirements:
            grouped[(requirement.path, requirement.territory)].append(requirement)

        return sorted(
            grouped.items(),
            key=lambda item: (
                item[0][0].value,
                RoteConfig.TERRITORY_PHASE.get(item[0][1], "99"),
                item[0][1],
            ),
        )

    def _format_requirement_owner_line(
        self, requirement, analyzer: CoverageAnalyzer
    ) -> str:
        """Format a single requirement line with all qualifying owners."""
        players = analyzer.matrix.get_players_at_relic(
            requirement.unit_id, requirement.min_relic
        )
        owner_names = sorted(player.player_name for player in players)
        owners = ", ".join(owner_names) if owner_names else "(none)"
        count_suffix = f" x{requirement.count}" if requirement.count > 1 else ""
        return (
            f"- {requirement.unit_name} R{requirement.min_relic}{count_suffix}: "
            f"{owners}"
        )

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

    def _format_slots_per_territory(self, slots_per_territory: dict[str, int]) -> str:
        """Format slots per territory with phase prefixes for compact display."""
        formatted = []
        for territory, slots in slots_per_territory.items():
            phase = RoteConfig.TERRITORY_PHASE.get(territory, "?")
            formatted.append(f"P{phase} {territory} ×{slots}")
        return ", ".join(formatted)

    def format_personal_farm_report(self, report) -> str:
        """Format personalized farming recommendations for a player."""
        lines = [
            f"**Farm Recommendations for {report.player_name}**",
            f"Guild: {report.guild_name} ({report.guild_member_count} members)",
            "",
        ]

        if report.max_phase:
            lines.append(f"Phases: 1-{report.max_phase}")
            lines.append("")

        # Summary
        lines.append(f"**Summary**")
        lines.append(f"- Total platoon gaps: {report.total_gaps}")
        lines.append(f"- Units you can help with: {report.units_player_can_help}")
        lines.append(
            f"- Units you already qualify for: {report.units_player_already_qualifies}"
        )
        lines.append("")

        if not report.recommendations:
            lines.append(
                "✅ No farming recommendations - you already cover all guild needs!"
            )
            return "\n".join(lines)

        # Priority recommendations
        lines.append("**Priority Farming Targets**")
        lines.append("_Sorted by guild need + your progress (best targets first)_")
        lines.append("")

        for rec in report.recommendations:
            # Priority indicator
            if rec.priority_rank <= 3:
                priority = "🔴"  # Top 3 = highest priority
            elif rec.priority_rank <= 7:
                priority = "🟡"  # 4-7 = medium priority
            else:
                priority = "⚪"  # 8+ = lower priority

            # Guild need indicator
            if rec.slots_unfillable > 0:
                need_str = f"❌ {rec.guild_owners}/{rec.slots_needed} ({rec.slots_unfillable} unfilled)"
            elif rec.guild_density < 0.5:
                need_str = f"⚠️ {rec.guild_owners}/{rec.slots_needed}"
            else:
                need_str = f"✅ {rec.guild_owners}/{rec.slots_needed}"

            lines.append(f"{priority} **{rec.unit_name}** → R{rec.required_relic}")
            lines.append(
                f"   Your status: {rec.status_string} | Need: {rec.progress_summary}"
            )
            lines.append(f"   Guild coverage: {need_str}")
            lines.append(f"   Territories: {', '.join(rec.territories)}")
            lines.append("")

        # Already qualified section (collapsed)
        if report.already_qualified:
            lines.append("")
            lines.append("**Already Qualified**")
            # Group by first letter for readability
            qualified_str = ", ".join(sorted(report.already_qualified)[:10])
            if len(report.already_qualified) > 10:
                qualified_str += f" (+{len(report.already_qualified) - 10} more)"
            lines.append(qualified_str)

        return "\n".join(lines)
