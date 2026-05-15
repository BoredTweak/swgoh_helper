"""
Bonus Zone Readiness Analyzer for Rise of the Empire Territory Battle.

Zeffo:     Cere Junda AND (Cal Kestis OR JK Cal Kestis) at R7 - need 30/30
Mandalore: Bo-Katan (Mand'alor) AND Beskar Mando at R7 - need 25/25

JK Cal Kestis (easy mode), Bo-Katan, and Beskar Mando all require unlock chains.
Distance scoring: (relic_gap x 1.0) + (gear_gap x 0.5) + (star_gap x 2.0)
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set

from swgoh_helper.constants import (
    GEAR_WEIGHT,
    JOURNEY_GUIDE_REQUIREMENTS_FILENAME,
    MANDALORE_THRESHOLD,
    MIN_RELIC_TIER,
    RELIC_STAR_REQUIREMENTS,
    RELIC_WEIGHT,
    STAR_WEIGHT,
    ZEFFO_THRESHOLD,
)
from swgoh_helper.models import (
    AllExprV2,
    AnyExprV2,
    AtLeastExprV2,
    JourneyGuideSchemaV2,
    NoneExprV2,
    PlayerResponse,
    RefExprV2,
    RequirementExprV2,
    UnitData,
    UnitExprV2,
    UnitRuleV2,
)
from swgoh_helper.models.rote import (
    BonusZoneReadiness,
    PlayerDistance,
    PrereqStatus,
    UnitProgressStatus,
)
from swgoh_helper.progress import ProgressNotifier
from swgoh_helper.progress_scorer import ProgressScorer

CLOSE_DISTANCE_THRESHOLD = 8.0
UnitLookup = Dict[str, UnitData]
BONUS_SCORER = ProgressScorer(
    relic_weight=RELIC_WEIGHT,
    gear_weight=GEAR_WEIGHT,
    star_weight=STAR_WEIGHT,
    relic_star_requirements=RELIC_STAR_REQUIREMENTS,
)


# === Data loading ===


class BonusReadinessDataSource:
    """Encapsulates bonus-readiness data loading from local cache files."""

    @staticmethod
    def get_data_dir() -> Path:
        data_dir = Path("data")
        if data_dir.exists():
            return data_dir
        data_dir = Path(__file__).parent.parent.parent / "data"
        if data_dir.exists():
            return data_dir
        raise FileNotFoundError("Could not find data directory")

    @classmethod
    def load_guild_data(cls, guild_id: str) -> dict:
        guild_file = cls.get_data_dir() / f"guild_{guild_id}.json"
        if not guild_file.exists():
            raise FileNotFoundError(f"Guild file not found: {guild_file}")
        with open(guild_file, "r", encoding="utf-8") as f:
            return json.load(f)["data"]["data"]

    @staticmethod
    def get_current_member_ally_codes(guild_data: dict) -> Set[int]:
        return {member["ally_code"] for member in guild_data["members"]}

    @classmethod
    def load_player_rosters(cls, member_ally_codes: Set[int]) -> List[PlayerResponse]:
        rosters = []
        for player_file in cls.get_data_dir().glob("player_*.json"):
            with open(player_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            roster = PlayerResponse(**data["data"])
            if roster.data.ally_code in member_ally_codes:
                rosters.append(roster)
        return rosters


class UnlockRequirementsSource:
    """Loads Bo-Katan and Beskar unlock requirements from journey guide data."""

    TARGET_IDS = {"MANDALORBOKATAN", "THEMANDALORIANBESKARARMOR"}

    def __init__(self, requirements_path: Optional[Path] = None):
        self.requirements_path = requirements_path or self._default_requirements_path()
        self.default_stars = 7
        self.unit_names: dict[str, str] = {}
        self._rules_by_target = self._load_rules_by_target()

    @staticmethod
    def _default_requirements_path() -> Path:
        data_dir = BonusReadinessDataSource.get_data_dir()
        return data_dir / JOURNEY_GUIDE_REQUIREMENTS_FILENAME

    def rules_for(self, target_id: str) -> list[UnitRuleV2]:
        return self._rules_by_target.get(target_id, [])

    def display_name(self, unit_id: str) -> str:
        return self.unit_names.get(unit_id, unit_id)

    def _load_rules_by_target(self) -> dict[str, list[UnitRuleV2]]:
        with self.requirements_path.open("r", encoding="utf-8") as file:
            raw_data = json.load(file)
        schema = JourneyGuideSchemaV2.model_validate(raw_data)
        self.default_stars = schema.defaults.stars
        self.unit_names = {
            unit_id: entry.name for unit_id, entry in schema.catalog.units.items()
        }

        rules_by_target: dict[str, list[UnitRuleV2]] = {}
        for target in schema.targets:
            if target.id not in self.TARGET_IDS:
                continue
            flattened = self._flatten_unit_rules(schema, target.requirement, set())
            rules_by_target[target.id] = self._dedupe_rules(flattened)
        return rules_by_target

    def _flatten_unit_rules(
        self,
        schema: JourneyGuideSchemaV2,
        expression: RequirementExprV2,
        seen_refs: set[str],
    ) -> list[UnitRuleV2]:
        if isinstance(expression, UnitExprV2):
            return [expression.unit]
        if isinstance(expression, RefExprV2):
            return self._flatten_ref(schema, expression.ref, seen_refs)
        if isinstance(expression, AtLeastExprV2):
            return self._flatten_expressions(schema, expression.of, seen_refs)
        if isinstance(expression, (AllExprV2, AnyExprV2, NoneExprV2)):
            return self._flatten_expressions(schema, expression.items, seen_refs)
        return []

    def _flatten_expressions(
        self,
        schema: JourneyGuideSchemaV2,
        expressions: list[RequirementExprV2],
        seen_refs: set[str],
    ) -> list[UnitRuleV2]:
        rules: list[UnitRuleV2] = []
        for expression in expressions:
            rules.extend(self._flatten_unit_rules(schema, expression, seen_refs))
        return rules

    def _flatten_ref(
        self,
        schema: JourneyGuideSchemaV2,
        ref: str,
        seen_refs: set[str],
    ) -> list[UnitRuleV2]:
        if ref in seen_refs:
            return []
        expression = schema.catalog.sets.get(ref)
        if expression is None:
            return []
        next_refs = set(seen_refs)
        next_refs.add(ref)
        return self._flatten_unit_rules(schema, expression, next_refs)

    @staticmethod
    def _dedupe_rules(rules: list[UnitRuleV2]) -> list[UnitRuleV2]:
        unique: dict[str, UnitRuleV2] = {}
        for rule in rules:
            if rule.id not in unique:
                unique[rule.id] = rule
        return list(unique.values())


class BonusReadinessAnalyzer:
    """Class-based analyzer for Zeffo and Mandalore readiness."""

    def __init__(
        self,
        close_distance_threshold: float = CLOSE_DISTANCE_THRESHOLD,
        journey_requirements_path: Optional[Path] = None,
    ):
        self.close_distance_threshold = close_distance_threshold
        self.requirements_source = UnlockRequirementsSource(journey_requirements_path)
        self._bokatan_rules = self.requirements_source.rules_for("MANDALORBOKATAN")
        self._beskar_rules = self.requirements_source.rules_for(
            "THEMANDALORIANBESKARARMOR"
        )

    @staticmethod
    def _unit_lookup(roster: PlayerResponse) -> UnitLookup:
        return {u.data.base_id: u.data for u in roster.units}

    @staticmethod
    def _unit_progress(units: UnitLookup, unit_id: str) -> UnitProgressStatus:
        if unit_id not in units:
            return UnitProgressStatus(
                has_unit=False,
                relic_tier=-1,
                gear_level=1,
                rarity=0,
                distance=float("inf"),
            )
        unit = units[unit_id]
        relic = unit.relic_tier_or_minus_one
        return UnitProgressStatus(
            has_unit=True,
            relic_tier=relic,
            gear_level=unit.gear_level,
            rarity=unit.rarity,
            distance=BONUS_SCORER.unit_distance(
                relic_tier=relic,
                gear_level=unit.gear_level,
                rarity=unit.rarity,
                required_relic=MIN_RELIC_TIER,
            ),
        )

    @staticmethod
    def _finalize_zone(
        zone_name: str,
        threshold: int,
        qualifying: List[str],
        near_qualifying: List[PlayerDistance],
    ) -> BonusZoneReadiness:
        near_qualifying.sort(key=lambda p: (p.distance, p.player_name))
        gap = max(0, threshold - len(qualifying))
        farmable = [p for p in near_qualifying if p.distance < float("inf")]
        distance_to_fill = sum(p.distance for p in farmable[:gap]) if gap > 0 else 0.0
        return BonusZoneReadiness(
            zone_name=zone_name,
            threshold=threshold,
            qualifying_players=qualifying,
            qualifying_count=len(qualifying),
            near_qualifying=near_qualifying,
            distance_to_fill_gap=distance_to_fill,
            farmable_count=len(farmable),
            is_unlockable=len(qualifying) >= threshold,
        )

    def _beskar_prereq_distance(self, units: UnitLookup) -> PrereqStatus:
        total, missing = 0.0, []
        for rule in self._beskar_rules:
            if rule.id not in units:
                total += float("inf")
                missing.append(f"no {self.requirements_source.display_name(rule.id)}")
                continue
            unit = units[rule.id]
            if self._meets_rule(unit, rule):
                continue
            total += self._rule_distance(unit, rule)
            missing.append(
                f"{self.requirements_source.display_name(rule.id)}"
                f"({self._current_progress_label(unit)})"
            )
        return PrereqStatus(prereq_distance=total, missing_prereqs=missing)

    def _bokatan_prereq_distance(self, units: UnitLookup) -> PrereqStatus:
        total, missing = 0.0, []
        if "THEMANDALORIANBESKARARMOR" not in units:
            beskar = self._beskar_prereq_distance(units)
            total += beskar.prereq_distance
            missing.extend(beskar.missing_prereqs)

        for rule in self._bokatan_rules:
            if rule.id not in units:
                if rule.id != "THEMANDALORIANBESKARARMOR":
                    total += float("inf")
                    missing.append(
                        f"no {self.requirements_source.display_name(rule.id)}"
                    )
                continue
            unit = units[rule.id]
            if self._meets_rule(unit, rule):
                continue
            total += self._rule_distance(unit, rule)
            missing.append(
                f"{self.requirements_source.display_name(rule.id)}"
                f"({self._current_progress_label(unit)})"
            )
        return PrereqStatus(prereq_distance=total, missing_prereqs=missing)

    def _required_stars(self, rule: UnitRuleV2) -> int:
        if rule.min.stars is not None:
            return rule.min.stars
        return self.requirements_source.default_stars

    def _meets_rule(self, unit: UnitData, rule: UnitRuleV2) -> bool:
        required_stars = self._required_stars(rule)
        if unit.rarity < required_stars:
            return False
        if rule.min.relic is not None:
            return unit.relic_tier_or_minus_one >= rule.min.relic
        if rule.min.gear is not None:
            return unit.gear_level >= rule.min.gear
        return True

    def _rule_distance(self, unit: UnitData, rule: UnitRuleV2) -> float:
        required_stars = self._required_stars(rule)
        required_relic = rule.min.relic
        if required_relic is not None:
            return BONUS_SCORER.unit_distance(
                relic_tier=unit.relic_tier_or_minus_one,
                gear_level=unit.gear_level,
                rarity=unit.rarity,
                required_relic=required_relic,
            )

        required_gear = rule.min.gear
        if required_gear is not None:
            return BONUS_SCORER.gear_distance(
                gear_level=unit.gear_level,
                rarity=unit.rarity,
                required_gear=required_gear,
                required_stars=required_stars,
            )

        return max(0, required_stars - unit.rarity) * STAR_WEIGHT

    @staticmethod
    def _current_progress_label(unit: UnitData) -> str:
        relic = unit.relic_tier_or_minus_one
        if relic >= 0:
            return f"R{relic}"
        return f"{unit.rarity}*G{unit.gear_level}"

    def _char_detail(
        self,
        unit: UnitProgressStatus,
        prereq: Optional[PrereqStatus],
        label: str,
    ) -> str:
        if unit.has_unit:
            return (
                unit.progress_text(label, MIN_RELIC_TIER)
                if unit.distance > 0
                else f"{label} OK"
            )
        if prereq and prereq.prereq_distance < float("inf"):
            summary = ", ".join(prereq.missing_prereqs[:3])
            if len(prereq.missing_prereqs) > 3:
                summary += "..."
            return f"no {label} [{summary}]"
        return f"no {label} (blocked)"

    @staticmethod
    def _total_character_cost(
        unit: UnitProgressStatus,
        prereq: Optional[PrereqStatus],
        unlock_to_r7: float,
    ) -> float:
        """Total cost to have character at R7 (owned path or unlock path)."""
        if unit.has_unit:
            return unit.distance
        if prereq and prereq.prereq_distance < float("inf"):
            return prereq.prereq_distance + unlock_to_r7
        return float("inf")

    def analyze_zeffo_readiness(
        self, rosters: List[PlayerResponse]
    ) -> BonusZoneReadiness:
        qualifying, near_qualifying = [], []
        for roster in rosters:
            units = self._unit_lookup(roster)
            cere = self._unit_progress(units, "CEREJUNDA")
            cal = self._unit_progress(units, "CALKESTIS")
            jkcal = self._unit_progress(units, "JEDIKNIGHTCAL")

            best_cal = cal if cal.distance <= jkcal.distance else jkcal
            best_name = "Cal" if cal.distance <= jkcal.distance else "JKCal"
            total = cere.distance + best_cal.distance

            if total == 0:
                qualifying.append(roster.data.name)
                continue

            details = []
            if cere.distance > 0:
                details.append(
                    cere.progress_text("Cere", MIN_RELIC_TIER)
                    if cere.has_unit
                    else "no Cere"
                )
            if best_cal.distance > 0:
                details.append(
                    best_cal.progress_text(best_name, MIN_RELIC_TIER)
                    if best_cal.has_unit
                    else f"no {best_name}"
                )
            near_qualifying.append(
                PlayerDistance(
                    player_name=roster.data.name,
                    distance=total,
                    details=", ".join(details),
                )
            )

        return self._finalize_zone(
            "Zeffo", ZEFFO_THRESHOLD, qualifying, near_qualifying
        )

    def analyze_mandalore_readiness(
        self,
        rosters: List[PlayerResponse],
    ) -> BonusZoneReadiness:
        qualifying, near_qualifying = [], []
        unlock_to_r7 = BONUS_SCORER.unit_distance(
            relic_tier=-1,
            gear_level=1,
            rarity=7,
            required_relic=MIN_RELIC_TIER,
        )

        for roster in rosters:
            units = self._unit_lookup(roster)
            bokatan = self._unit_progress(units, "MANDALORBOKATAN")
            beskar = self._unit_progress(units, "THEMANDALORIANBESKARARMOR")
            bokatan_prereq = (
                self._bokatan_prereq_distance(units) if not bokatan.has_unit else None
            )
            beskar_prereq = (
                self._beskar_prereq_distance(units) if not beskar.has_unit else None
            )

            bokatan_cost = self._total_character_cost(
                bokatan,
                bokatan_prereq,
                unlock_to_r7,
            )
            beskar_cost = self._total_character_cost(
                beskar,
                beskar_prereq,
                unlock_to_r7,
            )
            total = bokatan_cost + beskar_cost

            if total == 0:
                qualifying.append(roster.data.name)
                continue

            details = [
                self._char_detail(bokatan, bokatan_prereq, "Bo-Katan"),
                self._char_detail(beskar, beskar_prereq, "Beskar"),
            ]
            near_qualifying.append(
                PlayerDistance(
                    player_name=roster.data.name,
                    distance=total,
                    details=", ".join(details),
                )
            )

        return self._finalize_zone(
            "Mandalore", MANDALORE_THRESHOLD, qualifying, near_qualifying
        )

    def _format_zone(
        self, readiness: BonusZoneReadiness, note: Optional[str] = None
    ) -> list[str]:
        lines = [
            f"\n{readiness.zone_name} ({readiness.qualifying_count}/{readiness.threshold} ready)"
        ]
        if note:
            lines.append(f"  Note: {note}")
        ready = sorted(readiness.qualifying_players)
        lines.append(
            f"  Ready ({len(ready)}): {', '.join(ready)}" if ready else "  Ready: none"
        )

        close = [
            p
            for p in readiness.near_qualifying
            if 0 < p.distance <= self.close_distance_threshold
        ]
        if close:
            lines.append(f"  Close to ready ({len(close)}):")
            for player in close:
                lines.append(f"    {player.player_name}: {player.details}")
        else:
            lines.append("  Close to ready: none")
        return lines

    def format_bonus_readiness_report(
        self,
        zeffo: BonusZoneReadiness,
        mandalore: BonusZoneReadiness,
    ) -> str:
        def zone_status(readiness: BonusZoneReadiness) -> str:
            if readiness.is_unlockable:
                return "UNLOCKABLE NOW"
            return f"not yet ({readiness.qualifying_count}/{readiness.threshold})"

        lines = [
            "",
            "Bonus Zone Status",
            f"  Zeffo:     {zone_status(zeffo)}",
            f"  Mandalore: {zone_status(mandalore)}",
        ]
        lines.extend(
            self._format_zone(
                zeffo,
                note="Jedi Knight Cal Kestis = easy mode; Cal Kestis = hard mode",
            )
        )
        lines.extend(self._format_zone(mandalore))
        lines.append("")
        return "\n".join(lines)


# === App ===


class BonusReadinessApp:
    def __init__(self, progress: Optional[ProgressNotifier] = None):
        self.progress = progress or ProgressNotifier()
        self.analyzer = BonusReadinessAnalyzer()

    def analyze(self, guild_id: str) -> str:
        self.progress.update("Starting bonus zone readiness analysis...")
        guild_data = BonusReadinessDataSource.load_guild_data(guild_id)
        guild_name = guild_data.get("name", "Unknown Guild")
        member_ally_codes = BonusReadinessDataSource.get_current_member_ally_codes(
            guild_data
        )
        self.progress.update(f"Guild: {guild_name} ({len(member_ally_codes)} members)")
        rosters = BonusReadinessDataSource.load_player_rosters(member_ally_codes)
        self.progress.update(f"Loaded {len(rosters)} player rosters")
        self.progress.update("Analyzing Zeffo readiness...")
        zeffo = self.analyzer.analyze_zeffo_readiness(rosters)
        self.progress.update("Analyzing Mandalore readiness...")
        mandalore = self.analyzer.analyze_mandalore_readiness(rosters)
        return self.analyzer.format_bonus_readiness_report(zeffo, mandalore)


def _print_bonus_readiness_usage() -> None:
    print("Usage: rote_bonus_readiness <guild_id>")
    print()
    print("Analyze guild readiness for Rise of the Empire bonus zones.")
    print()
    print("Arguments:")
    print("  guild_id  The guild ID to analyze (from cached data)")
    print()
    print("The command reads cached data from the 'data/' directory.")
    print("Run 'rote-platoon <ally_code>' first to populate the cache.")


def run_rote_bonus_readiness() -> None:
    """Entry point for rote-bonus-readiness CLI command."""
    if len(sys.argv) < 2:
        _print_bonus_readiness_usage()
        sys.exit(1)

    if sys.argv[1] in ("--help", "-h"):
        _print_bonus_readiness_usage()
        sys.exit(0)

    try:
        print(BonusReadinessApp().analyze(sys.argv[1]))
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Make sure you have guild and player data in the 'data/' directory.")
        print("Run 'rote-platoon <ally_code>' first to populate the cache.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run_rote_bonus_readiness()
