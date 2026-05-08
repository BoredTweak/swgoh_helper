"""Presentation layer for ROTE platoon analysis results."""

from collections import defaultdict
from typing import Dict, Optional

from .constants import LIMITED_AVAILABILITY_CALLOUT_THRESHOLD
from .models import CombatType, UnitType
from .models.rote import BonusZoneReadiness
from .rote_limited_availability_service import LimitedAvailabilityService
from .rote_coverage import CoverageAnalyzer, RoteConfig
from .rote_gap_analyzer import GapAnalyzer
from .rote_bottleneck_analyzer import BottleneckAnalyzer
from .rote_models import RotePath


class RotePresenter:
    """Formats ROTE platoon analysis as markdown for Discord sharing."""

    LOCKED_BONUS_REQUIREMENTS = {
        "Mandalore": "Requires BKM R7",
        "Zeffo": "Requires R7 Cere and R7 Cal (your choice, easier with JKCS)",
    }

    def format_results(
        self,
        analyzer: CoverageAnalyzer,
        matrix,
        gap_analyzer: GapAnalyzer,
        bottleneck_analyzer: BottleneckAnalyzer,
        output_format: str = "all",
        limited_output_format: str = "member",
        limited_buffer: int | None = None,
        verbose: bool = False,
        requester_ally_code: int | None = None,
        bonus_readiness: Optional[Dict[str, BonusZoneReadiness]] = None,
    ) -> str:
        """Generate complete formatted output."""
        lines = [f"**{matrix.guild_name}** ({matrix.member_count} members)"]

        if output_format in {"all", "coverage"}:
            lines.extend(["", "**Coverage**"])
            lines.extend(self._format_coverage(analyzer, bonus_readiness))

        if output_format in {"all", "gaps"}:
            lines.extend(
                self._format_gaps(
                    gap_analyzer,
                    bottleneck_analyzer,
                    bonus_readiness,
                    limited_buffer,
                )
            )

        if output_format == "owners":
            lines.extend(self._format_requirement_owners(analyzer, verbose=verbose))

        if output_format == "mine":
            lines.extend(
                self._format_only_mine_requirements(analyzer, requester_ally_code)
            )

        if output_format == "limited":
            lines.extend(
                self._format_limited_availability(
                    analyzer,
                    bottleneck_analyzer,
                    limited_output_format,
                )
            )

        return "\n".join(lines)

    def _format_limited_availability(
        self,
        analyzer: CoverageAnalyzer,
        bottleneck_analyzer: BottleneckAnalyzer,
        limited_output_format: str,
    ) -> list[str]:
        """Format the limited view using either member or relic ownership grouping."""
        if limited_output_format == "relic":
            return self._format_limited_availability_by_relic(analyzer)
        return self._format_limited_availability_by_member(
            analyzer,
            bottleneck_analyzer,
        )

    def _format_limited_availability_by_member(
        self,
        analyzer: CoverageAnalyzer,
        bottleneck_analyzer: BottleneckAnalyzer,
    ) -> list[str]:
        """Format per-member ownership count for limited-availability character requirements."""
        lines = ["", "**Limited Availability by Member**"]
        rare_character_units = [
            unit
            for unit in bottleneck_analyzer.identify_unicorn_units()
            if unit.owner_count > 0 and self._is_character_unit(analyzer, unit.unit_id)
        ]
        if not rare_character_units:
            lines.append("No limited availability character requirements found.")
            return lines

        member_names = self._collect_member_names(analyzer)
        counts_by_member = {name: 0 for name in member_names}

        for unit in rare_character_units:
            for owner_name in set(unit.owner_names):
                if owner_name in counts_by_member:
                    counts_by_member[owner_name] += 1

        sorted_counts = sorted(
            counts_by_member.items(),
            key=lambda item: (-item[1], item[0].casefold()),
        )
        for member_name, count in sorted_counts:
            character_word = "character" if count == 1 else "characters"
            lines.append(
                f"- {member_name}: {count} limited availability {character_word}"
            )

        return lines

    def _format_limited_availability_by_relic(
        self,
        analyzer: CoverageAnalyzer,
    ) -> list[str]:
        """Format all required characters grouped by required relic with owner counts."""
        lines = ["", "**ROTE Character Ownership by Required Relic**"]
        grouped = self._group_character_requirements_by_relic(analyzer)
        if not grouped:
            lines.append("No character requirements found.")
            return lines

        for relic_tier in sorted(grouped):
            lines.append(f"R{relic_tier}:")
            rows = sorted(
                grouped[relic_tier], key=lambda row: (row[1], -row[2], row[0])
            )
            for unit_name, owner_count, slots_needed in rows:
                owner_word = "owner" if owner_count == 1 else "owners"
                lines.append(
                    f"- {unit_name}: {owner_count} {owner_word} (need {slots_needed})"
                )
            lines.append("")

        return lines[:-1]

    def _group_character_requirements_by_relic(
        self,
        analyzer: CoverageAnalyzer,
    ) -> dict[int, list[tuple[str, int, int]]]:
        """Return relic -> [(unit_name, owner_count, slots_needed)] for all character requirements."""
        aggregated: dict[tuple[str, int], tuple[str, int]] = {}
        for requirement in analyzer.requirements.requirements:
            if self._is_ship_requirement(requirement, analyzer):
                continue
            key = (requirement.unit_id, requirement.min_relic)
            unit_name, slots_needed = aggregated.get(key, (requirement.unit_name, 0))
            aggregated[key] = (unit_name, slots_needed + requirement.count)

        grouped: dict[int, list[tuple[str, int, int]]] = defaultdict(list)
        for (unit_id, min_relic), (unit_name, slots_needed) in aggregated.items():
            owner_count = len(analyzer.matrix.get_players_at_relic(unit_id, min_relic))
            grouped[min_relic].append((unit_name, owner_count, slots_needed))
        return grouped

    def _is_character_unit(self, analyzer: CoverageAnalyzer, unit_id: str) -> bool:
        """Check whether a unit is a character in guild coverage data."""
        coverage = analyzer.matrix.get_coverage(unit_id)
        return bool(coverage and coverage.combat_type == CombatType.CHARACTER)

    def _collect_member_names(self, analyzer: CoverageAnalyzer) -> list[str]:
        """Collect all unique member names represented in the coverage matrix."""
        names: set[str] = set()
        for coverage in analyzer.matrix.units.values():
            for player in coverage.all_players():
                names.add(player.player_name)
        return sorted(names, key=str.casefold)

    def _format_only_mine_requirements(
        self, analyzer: CoverageAnalyzer, requester_ally_code: int | None
    ) -> list[str]:
        """List requirements the requester can cover, grouped by territory."""
        lines = ["", "**Your Planet Coverage**"]
        if requester_ally_code is None:
            lines.append("(requester ally code unavailable)")
            return lines

        territories = self._group_requirements_by_territory(analyzer)
        territory_lines: list[str] = []

        for (_, territory), requirements in territories:
            unique_character_requirement_ids: set[str] = set()
            unique_ship_requirement_ids: set[str] = set()
            for requirement in requirements:
                if self._is_ship_requirement(requirement, analyzer):
                    unique_ship_requirement_ids.add(requirement.unit_id)
                else:
                    unique_character_requirement_ids.add(requirement.unit_id)

            matched_character_unit_ids: set[str] = set()
            matched_ship_unit_ids: set[str] = set()
            matched_requirements: list[tuple[int, int, str, str]] = []
            for requirement in requirements:
                owners = analyzer.matrix.get_players_at_relic(
                    requirement.unit_id, requirement.min_relic
                )
                if not any(owner.ally_code == requester_ally_code for owner in owners):
                    continue

                if self._is_ship_requirement(requirement, analyzer):
                    matched_ship_unit_ids.add(requirement.unit_id)
                else:
                    matched_character_unit_ids.add(requirement.unit_id)

                requester_status = self._format_requester_owned_status(
                    analyzer, requirement.unit_id, requester_ally_code
                )
                line = f"- {requirement.unit_name} {requester_status}"
                owner_count = len(owners)
                callout = self._format_limited_availability_callout(
                    owner_count, requirement.count
                )
                matched_requirements.append(
                    (
                        owner_count,
                        -requirement.count,
                        requirement.unit_name,
                        f"{line}{callout}",
                    )
                )

            matched_requirements.sort(key=lambda row: (row[0], row[1], row[2]))
            matched_lines = [row[3] for row in matched_requirements]

            if not matched_lines:
                continue

            phase = RoteConfig.TERRITORY_PHASE.get(territory, "?")
            territory_lines.append(f"P{phase} {territory}:")
            if unique_character_requirement_ids and unique_ship_requirement_ids:
                territory_lines.append(
                    "You own "
                    f"**{len(matched_character_unit_ids)}/{len(unique_character_requirement_ids)}** characters "
                    "and "
                    f"**{len(matched_ship_unit_ids)}/{len(unique_ship_requirement_ids)}** ships "
                    "at the required levels."
                )
            elif unique_character_requirement_ids:
                territory_lines.append(
                    "You own "
                    f"**{len(matched_character_unit_ids)}/{len(unique_character_requirement_ids)}** "
                    "at the required levels."
                )
            elif unique_ship_requirement_ids:
                territory_lines.append(
                    "You own "
                    f"**{len(matched_ship_unit_ids)}/{len(unique_ship_requirement_ids)}** ships "
                    "at the required levels."
                )
            else:
                territory_lines.append("No character requirements on this planet.")
            territory_lines.extend(matched_lines)
            territory_lines.append("")

        if not territory_lines:
            lines.append("You do not currently qualify for any platoon requirements.")
            return lines

        lines.extend(territory_lines)
        return lines

    def _is_ship_requirement(self, requirement, analyzer: CoverageAnalyzer) -> bool:
        """Infer whether a requirement is a ship requirement."""
        if requirement.unit_type == UnitType.SHIP:
            return True

        coverage = analyzer.matrix.get_coverage(requirement.unit_id)
        return bool(coverage and coverage.combat_type == CombatType.SHIP)

    def _format_requester_owned_status(
        self, analyzer: CoverageAnalyzer, unit_id: str, requester_ally_code: int
    ) -> str:
        """Format the requester's current ownership status for the unit."""
        coverage = analyzer.matrix.get_coverage(unit_id)
        if coverage and coverage.combat_type == CombatType.SHIP:
            return "7*"

        for player in analyzer.matrix.get_all_players(unit_id):
            if player.ally_code != requester_ally_code:
                continue

            if player.relic_tier >= 0:
                return f"R{player.relic_tier}"
            return f"G{player.gear_level} {player.rarity}*"

        return "(owned)"

    def _format_limited_availability_callout(
        self, owner_count: int, slots_needed: int
    ) -> str:
        """Return callout text when owner coverage is limited."""
        if not LimitedAvailabilityService.is_limited(
            owner_count,
            slots_needed,
            LIMITED_AVAILABILITY_CALLOUT_THRESHOLD,
        ):
            return ""

        if owner_count == 1:
            return " **PRIORITY DEPLOY: You are the only player that owns this unit at the required level**"

        player_word = "players"
        verb = "own"
        return (
            " "
            f"**You are one of only {owner_count} {player_word} "
            f"that {verb} this unit at the required level**"
        )

    def _format_coverage(
        self,
        analyzer: CoverageAnalyzer,
        bonus_readiness: Optional[Dict[str, BonusZoneReadiness]] = None,
    ) -> list[str]:
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

                if bonus_readiness and territory in bonus_readiness:
                    lines.extend(
                        self._format_bonus_zone_status(bonus_readiness[territory])
                    )

            if i < len(paths) - 1:
                lines.append("")

        return lines

    def _format_gaps(
        self,
        gap_analyzer: GapAnalyzer,
        bottleneck_analyzer: BottleneckAnalyzer,
        bonus_readiness: Optional[Dict[str, BonusZoneReadiness]] = None,
        limited_buffer: int | None = None,
    ) -> list[str]:
        """Format all unfillable gaps and limited availability units."""
        lines = ["", "**Gaps**"]

        all_requirements = gap_analyzer.analyze_all_requirements()
        gap_rows = self._select_gap_rows(all_requirements, limited_buffer)
        territories = self._territories_for_gap_rows(
            gap_analyzer,
            gap_rows,
            bonus_readiness,
            limited_buffer,
        )

        if not gap_rows and not territories:
            lines.append("✅ No gaps")
        else:
            gaps_by_territory = defaultdict(list)
            for gap in gap_rows:
                gaps_by_territory[(gap.path, gap.territory)].append(gap)

            for path, territory in sorted(
                territories,
                key=lambda x: (
                    x[0].value,
                    RoteConfig.TERRITORY_PHASE.get(x[1], "99"),
                    x[1],
                ),
            ):
                gaps = gaps_by_territory.get((path, territory), [])
                readiness = (
                    bonus_readiness.get(territory)
                    if bonus_readiness and territory in bonus_readiness
                    else None
                )
                if (
                    limited_buffer is not None
                    and readiness
                    and not readiness.is_unlockable
                ):
                    lines.append(
                        self._format_locked_bonus_gap_line(territory, readiness)
                    )
                    lines.append("")
                    continue

                phase = RoteConfig.TERRITORY_PHASE.get(territory, "?")
                lines.append(f"P{phase} {territory}:")

                if readiness:
                    lines.extend(self._format_bonus_zone_status(readiness))

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

        if limited_buffer is not None:
            return lines

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

    def _format_locked_bonus_gap_line(
        self,
        territory: str,
        readiness: BonusZoneReadiness,
    ) -> str:
        """Format locked bonus territory line for compact Gaps output."""
        phase = RoteConfig.TERRITORY_PHASE.get(territory, "?")
        requirement_text = self.LOCKED_BONUS_REQUIREMENTS.get(territory)
        suffix = f" - {requirement_text}" if requirement_text else ""
        return (
            f"P{phase} {territory} 🔒 "
            f"({readiness.qualifying_count}/{readiness.threshold} ready){suffix}"
        )

    def _select_gap_rows(self, all_rows: list, buffer: int | None) -> list:
        """Select rows for the Gaps section using optional limited-availability buffer."""
        if buffer is None:
            return [row for row in all_rows if row.is_gap]
        return [
            row
            for row in all_rows
            if row.players_available <= (row.slots_needed + buffer)
        ]

    def _territories_for_gap_rows(
        self,
        gap_analyzer: GapAnalyzer,
        gap_rows: list,
        bonus_readiness: Optional[Dict[str, BonusZoneReadiness]],
        limited_buffer: int | None,
    ) -> list[tuple[RotePath, str]]:
        """Get territories to render, including locked bonus territories in buffered mode."""
        territory_keys: set[tuple[RotePath, str]] = {
            (row.path, row.territory) for row in gap_rows
        }

        if limited_buffer is None or not bonus_readiness:
            return list(territory_keys)

        path_by_territory = {
            requirement.territory: requirement.path
            for requirement in gap_analyzer.requirements.requirements
        }
        for territory, readiness in bonus_readiness.items():
            if readiness.is_unlockable:
                continue
            path = path_by_territory.get(territory)
            if path is None:
                continue
            territory_keys.add((path, territory))

        return list(territory_keys)

    def _format_bonus_zone_status(self, readiness: BonusZoneReadiness) -> list[str]:
        """Format bonus zone unlock status as indented lines."""
        if readiness.is_unlockable:
            return [
                f"  🔓 Bonus zone unlocked ({readiness.qualifying_count}/{readiness.threshold} ready)"
            ]

        lines = [
            f"  🔒 Bonus zone locked ({readiness.qualifying_count}/{readiness.threshold} ready)"
        ]
        return lines

    def _format_requirement_owners(
        self, analyzer: CoverageAnalyzer, verbose: bool = False
    ) -> list[str]:
        """Format platoon requirement owners grouped by territory."""
        lines = ["", "**Requirement Owners**"]
        territories = self._group_requirements_by_territory(analyzer)

        for (path, territory), requirements in territories:
            phase = RoteConfig.TERRITORY_PHASE.get(territory, "?")
            lines.append(f"P{phase} {territory}:")
            for requirement in requirements:
                lines.append(
                    self._format_requirement_owner_line(
                        requirement,
                        analyzer,
                        verbose=verbose,
                    )
                )
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
        self, requirement, analyzer: CoverageAnalyzer, verbose: bool = False
    ) -> str:
        """Format a single requirement line with qualifying owners."""
        players = analyzer.matrix.get_players_at_relic(
            requirement.unit_id, requirement.min_relic
        )
        owner_names = sorted(player.player_name for player in players)
        owners = self._format_requirement_owners_list(
            owner_names,
            requirement_count=requirement.count,
            verbose=verbose,
        )
        count_suffix = f" x{requirement.count}" if requirement.count > 1 else ""
        return (
            f"- {requirement.unit_name} R{requirement.min_relic}{count_suffix}: "
            f"{owners}"
        )

    def _format_requirement_owners_list(
        self,
        owner_names: list[str],
        requirement_count: int,
        verbose: bool,
    ) -> str:
        """Format owner names compactly unless requirement has limited availability."""
        if not owner_names:
            return "(none)"

        if verbose or self._is_limited_availability(
            len(owner_names), requirement_count
        ):
            return ", ".join(owner_names)

        shown = owner_names[: max(0, requirement_count)]
        shown_text = ", ".join(shown)
        hidden_count = len(owner_names) - len(shown)
        if hidden_count <= 0:
            return shown_text

        if shown_text:
            return f"{shown_text} and {hidden_count} more"
        return f"and {hidden_count} more"

    def _is_limited_availability(self, owner_count: int, slots_needed: int) -> bool:
        """A unit is limited unless it has at least LIMITED_AVAILABILITY_CALLOUT_THRESHOLD extra owners beyond required slots."""
        return owner_count < (slots_needed + LIMITED_AVAILABILITY_CALLOUT_THRESHOLD)

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
        lines.append("**Summary**")
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
