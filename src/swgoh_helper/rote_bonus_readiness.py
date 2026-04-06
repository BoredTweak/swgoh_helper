"""
Bonus Zone Readiness Analyzer for Rise of the Empire Territory Battle.

Zeffo:     Cere Junda AND (Cal Kestis OR JK Cal Kestis) at R7 — need 30/30
Mandalore: Bo-Katan (Mand'alor) AND Beskar Mando at R7 — need 25/25

JK Cal Kestis (easy mode), Bo-Katan, and Beskar Mando all require unlock chains.
Distance scoring: (relic_gap x 1.0) + (gear_gap x 0.5) + (star_gap x 2.0)
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set

from swgoh_helper.constants import (
    BESKAR_MIN_GEAR,
    BESKAR_MIN_STARS,
    BESKAR_PREREQS,
    BOKATAN_MIN_RELIC,
    BOKATAN_PREREQS,
    GEAR_WEIGHT,
    MANDALORE_THRESHOLD,
    MIN_RELIC_TIER,
    RELIC_STAR_REQUIREMENTS,
    RELIC_WEIGHT,
    STAR_WEIGHT,
    ZEFFO_THRESHOLD,
)
from swgoh_helper.models import PlayerResponse, UnitData
from swgoh_helper.models.rote import (
    BonusZoneReadiness,
    PlayerDistance,
    PrereqStatus,
    UnitProgressStatus,
)
from swgoh_helper.progress_scorer import ProgressScorer
from swgoh_helper.progress import ProgressNotifier

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


class BonusReadinessAnalyzer:
    """Class-based analyzer for Zeffo and Mandalore readiness."""

    def __init__(self, close_distance_threshold: float = CLOSE_DISTANCE_THRESHOLD):
        self.close_distance_threshold = close_distance_threshold

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
        for prereq_id, prereq_name in BESKAR_PREREQS.items():
            if prereq_id not in units:
                total += float("inf")
                missing.append(f"no {prereq_name}")
                continue
            unit = units[prereq_id]
            if unit.gear_level >= BESKAR_MIN_GEAR and unit.rarity >= BESKAR_MIN_STARS:
                continue
            total += BONUS_SCORER.gear_distance(
                gear_level=unit.gear_level,
                rarity=unit.rarity,
                required_gear=BESKAR_MIN_GEAR,
                required_stars=BESKAR_MIN_STARS,
            )
            missing.append(f"{prereq_name}({unit.rarity}*G{unit.gear_level})")
        return PrereqStatus(prereq_distance=total, missing_prereqs=missing)

    def _bokatan_prereq_distance(self, units: UnitLookup) -> PrereqStatus:
        total, missing = 0.0, []
        if "THEMANDALORIANBESKARARMOR" not in units:
            beskar = self._beskar_prereq_distance(units)
            total += beskar.prereq_distance
            missing.extend(beskar.missing_prereqs)

        for prereq_id, prereq_name in BOKATAN_PREREQS.items():
            if prereq_id not in units:
                if prereq_id != "THEMANDALORIANBESKARARMOR":
                    total += float("inf")
                    missing.append(f"no {prereq_name}")
                continue
            unit = units[prereq_id]
            relic = unit.relic_tier_or_minus_one
            if relic >= BOKATAN_MIN_RELIC:
                continue
            total += BONUS_SCORER.unit_distance(
                relic_tier=relic,
                gear_level=unit.gear_level,
                rarity=unit.rarity,
                required_relic=BOKATAN_MIN_RELIC,
            )
            label = f"R{relic}" if relic >= 0 else f"G{unit.gear_level}"
            missing.append(f"{prereq_name}({label})")
        return PrereqStatus(prereq_distance=total, missing_prereqs=missing)

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
