"""
Bonus Zone Readiness Analyzer for Rise of the Empire Territory Battle.

Determines if the guild is closer to unlocking Mandalore or Zeffo bonus zones.

Zeffo Requirements:
- Cere Junda AND (Cal Kestis OR Jedi Knight Cal Kestis)
- Unlock threshold: 30/30

Mandalore Requirements:
- Bo-Katan (Mand'alor) AND The Mandalorian (Beskar Armor)
- Unlock threshold: 25/25

Notes:
- Jedi Knight Cal Kestis, Bo-Katan (Mand'alor), and The Mandalorian (Beskar Armor)
  all have pre-requisites that must be unlocked first.

Distance scoring uses the farming recommendations formula:
  distance = (relic_gap × 1.0) + (gear_gap × 0.5) + (star_gap × 2.0)
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Set

from pydantic import BaseModel

from swgoh_helper.constants import (
    ZEFFO_UNITS,
    MANDALORE_UNITS,
    BOKATAN_PREREQS,
    BESKAR_PREREQS,
    ZEFFO_THRESHOLD,
    MANDALORE_THRESHOLD,
    MIN_RELIC_TIER,
    BESKAR_MIN_GEAR,
    BESKAR_MIN_STARS,
    BOKATAN_MIN_RELIC,
    RELIC_WEIGHT,
    GEAR_WEIGHT,
    STAR_WEIGHT,
    RELIC_STAR_REQUIREMENTS,
)
from swgoh_helper.models import PlayerResponse
from swgoh_helper.models.rote import (
    PlayerDistance,
    BonusZoneReadiness,
)


def calculate_unit_distance(
    relic_tier: int,
    gear_level: int,
    rarity: int,
    required_relic: int = MIN_RELIC_TIER,
) -> float:
    """
    Calculate distance score for a single unit using farming recommendations formula.

    distance = (relic_gap × 1.0) + (gear_gap × 0.5) + (star_gap × 2.0)

    Returns 0 if unit qualifies, otherwise positive distance.
    """
    required_stars = RELIC_STAR_REQUIREMENTS.get(required_relic, 7)
    star_gap = max(0, required_stars - rarity)

    if relic_tier >= required_relic:
        # Already qualifies
        return 0.0

    if relic_tier >= 0:
        # Has relics, needs more
        relic_gap = required_relic - relic_tier
        gear_gap = 0
    elif gear_level == 13:
        # At G13, needs relic
        relic_gap = required_relic
        gear_gap = 0
    else:
        # Below G13
        relic_gap = required_relic
        gear_gap = 13 - gear_level

    return (
        (relic_gap * RELIC_WEIGHT) + (gear_gap * GEAR_WEIGHT) + (star_gap * STAR_WEIGHT)
    )


def calculate_gear_distance(
    gear_level: int,
    rarity: int,
    required_gear: int = BESKAR_MIN_GEAR,
    required_stars: int = BESKAR_MIN_STARS,
) -> float:
    """
    Calculate distance score for a unit to reach 7* G12 (Beskar prereq).

    Uses same formula: distance = gear_gap × 0.5 + star_gap × 2.0
    """
    star_gap = max(0, required_stars - rarity)
    gear_gap = max(0, required_gear - gear_level)

    return (gear_gap * GEAR_WEIGHT) + (star_gap * STAR_WEIGHT)


def get_data_dir() -> Path:
    """Get the data directory path."""
    # Try relative to current working directory first
    data_dir = Path("data")
    if data_dir.exists():
        return data_dir

    # Try relative to the module location
    module_dir = Path(__file__).parent.parent.parent
    data_dir = module_dir / "data"
    if data_dir.exists():
        return data_dir

    raise FileNotFoundError("Could not find data directory")


def load_guild_data(guild_id: str) -> dict:
    """Load guild data from cache."""
    data_dir = get_data_dir()
    guild_file = data_dir / f"guild_{guild_id}.json"

    if not guild_file.exists():
        raise FileNotFoundError(f"Guild file not found: {guild_file}")

    with open(guild_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["data"]["data"]


def get_current_member_ally_codes(guild_data: dict) -> Set[int]:
    """Extract ally codes of current guild members."""
    return {member["ally_code"] for member in guild_data["members"]}


def load_player_rosters(member_ally_codes: Set[int]) -> List[PlayerResponse]:
    """Load player rosters for current guild members only."""
    data_dir = get_data_dir()
    rosters = []

    for player_file in data_dir.glob("player_*.json"):
        with open(player_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        roster = PlayerResponse(**data["data"])
        # Only include current guild members
        if roster.data.ally_code in member_ally_codes:
            rosters.append(roster)

    return rosters


def convert_relic_tier(api_relic_tier: int | None) -> int:
    """
    Convert API relic_tier value to actual relic level.
    API encoding: None=not G13, 1=G13 no relic, 2=R0, 3=R1, ..., 11=R9
    Returns -1 for non-reliced units.
    """
    if api_relic_tier is None or api_relic_tier < 3:
        return -1
    return api_relic_tier - 2


class PrereqStatus(BaseModel):
    """Status of unlock prerequisites for a character."""

    can_unlock: bool  # Already has the character unlocked
    prereq_distance: float  # Distance to complete all prereqs (0 if can_unlock)
    missing_prereqs: List[str]  # Names of prereq units not at required level
    detail: str  # Human-readable summary


def calculate_beskar_prereq_status(roster: PlayerResponse) -> PrereqStatus:
    """
    Calculate distance to unlock Beskar Mando.
    Requires: Mando, Greef, Cara, IG-11, Kuiil all at 7* G12.
    """
    # First check if they already have Beskar
    for unit in roster.units:
        if unit.data.base_id == "THEMANDALORIANBESKARARMOR":
            return PrereqStatus(
                can_unlock=True,
                prereq_distance=0.0,
                missing_prereqs=[],
                detail="has Beskar",
            )

    # Calculate distance to complete prereqs
    total_distance = 0.0
    missing = []

    for prereq_id, prereq_name in BESKAR_PREREQS.items():
        found = False
        for unit in roster.units:
            if unit.data.base_id == prereq_id:
                found = True
                gear_level = unit.data.gear_level
                rarity = unit.data.rarity

                if gear_level >= BESKAR_MIN_GEAR and rarity >= BESKAR_MIN_STARS:
                    # Prereq met
                    pass
                else:
                    distance = calculate_gear_distance(gear_level, rarity)
                    total_distance += distance
                    missing.append(f"{prereq_name}({rarity}★G{gear_level})")
                break

        if not found:
            # Don't own the prereq - huge distance
            total_distance += float("inf")
            missing.append(f"no {prereq_name}")

    detail = (
        f"Beskar prereqs: {', '.join(missing)}" if missing else "Beskar prereqs met"
    )

    return PrereqStatus(
        can_unlock=False,
        prereq_distance=total_distance,
        missing_prereqs=missing,
        detail=detail,
    )


def calculate_bokatan_prereq_status(roster: PlayerResponse) -> PrereqStatus:
    """
    Calculate distance to unlock Bo-Katan (Mand'alor).
    Requires: Kelleran, Paz, IG-12, Beskar Mando all at R7.
    """
    # First check if they already have Bo-Katan
    for unit in roster.units:
        if unit.data.base_id == "MANDALORBOKATAN":
            return PrereqStatus(
                can_unlock=True,
                prereq_distance=0.0,
                missing_prereqs=[],
                detail="has Bo-Katan",
            )

    # Calculate distance for Bo-Katan prereqs (all need R7)
    total_distance = 0.0
    missing = []

    for prereq_id, prereq_name in BOKATAN_PREREQS.items():
        # Special case: Beskar Mando needs its own prereqs checked
        if prereq_id == "THEMANDALORIANBESKARARMOR":
            beskar_status = calculate_beskar_prereq_status(roster)
            if not beskar_status.can_unlock:
                # Need to also factor in Beskar prereqs
                total_distance += beskar_status.prereq_distance
                missing.extend(beskar_status.missing_prereqs)
            # Still need to check Beskar's own relic level

        found = False
        for unit in roster.units:
            if unit.data.base_id == prereq_id:
                found = True
                relic_tier = convert_relic_tier(unit.data.relic_tier)
                gear_level = unit.data.gear_level
                rarity = unit.data.rarity

                if relic_tier >= BOKATAN_MIN_RELIC:
                    # Prereq met
                    pass
                else:
                    distance = calculate_unit_distance(
                        relic_tier, gear_level, rarity, BOKATAN_MIN_RELIC
                    )
                    total_distance += distance
                    if relic_tier >= 0:
                        missing.append(f"{prereq_name}(R{relic_tier})")
                    else:
                        missing.append(f"{prereq_name}(G{gear_level})")
                break

        if not found:
            # Don't own the prereq
            if prereq_id == "THEMANDALORIANBESKARARMOR":
                # Beskar prereqs already added above
                pass
            else:
                total_distance += float("inf")
                missing.append(f"no {prereq_name}")

    detail = (
        f"Bo-Katan prereqs: {', '.join(missing)}" if missing else "Bo-Katan prereqs met"
    )

    return PrereqStatus(
        can_unlock=False,
        prereq_distance=total_distance,
        missing_prereqs=missing,
        detail=detail,
    )


class UnitProgress(BaseModel):
    """Progress data for a single unit."""

    has_unit: bool
    relic_tier: int  # -1 if not reliced
    gear_level: int  # 1-13
    rarity: int  # 1-7 stars
    distance: float  # Distance to R7 requirement


def get_player_unit_status(
    roster: PlayerResponse, required_units: Dict[str, str]
) -> Dict[str, UnitProgress]:
    """Check if player has the required units and calculate distance to R7."""
    result = {
        unit_id: UnitProgress(
            has_unit=False,
            relic_tier=-1,
            gear_level=1,
            rarity=0,
            distance=float("inf"),  # Infinite distance if not owned
        )
        for unit_id in required_units
    }

    for player_unit in roster.units:
        unit_id = player_unit.data.base_id
        if unit_id in required_units:
            relic_tier = convert_relic_tier(player_unit.data.relic_tier)
            gear_level = player_unit.data.gear_level
            rarity = player_unit.data.rarity
            distance = calculate_unit_distance(
                relic_tier, gear_level, rarity, MIN_RELIC_TIER
            )
            result[unit_id] = UnitProgress(
                has_unit=True,
                relic_tier=relic_tier,
                gear_level=gear_level,
                rarity=rarity,
                distance=distance,
            )

    return result


def analyze_zeffo_readiness(rosters: List[PlayerResponse]) -> BonusZoneReadiness:
    """
    Analyze guild readiness for Zeffo.
    Requirement: Cere Junda AND (Cal Kestis OR Jedi Knight Cal Kestis)

    Player distance = Cere distance + min(Cal distance, JK Cal distance)
    """
    qualifying_players = []
    near_qualifying = []

    for roster in rosters:
        player_name = roster.data.name
        units_status = get_player_unit_status(roster, ZEFFO_UNITS)

        cere = units_status["CEREJUNDA"]
        cal = units_status["CALKESTIS"]
        jkcal = units_status["JEDIKNIGHTCAL"]

        # Distance is sum of Cere + min(Cal, JK Cal)
        # Use best Cal variant (lowest distance)
        cal_distance = min(cal.distance, jkcal.distance)
        player_distance = cere.distance + cal_distance

        if cere.distance == 0 and cal_distance == 0:
            qualifying_players.append(player_name)
        else:
            # Build status string with distances
            details = []
            if cere.has_unit:
                if cere.distance > 0:
                    details.append(
                        f"Cere R{cere.relic_tier}->R7 (d={cere.distance:.1f})"
                    )
                else:
                    details.append("Cere OK")
            else:
                details.append("no Cere")

            if cal.has_unit or jkcal.has_unit:
                best_cal = cal if cal.distance <= jkcal.distance else jkcal
                best_name = "Cal" if cal.distance <= jkcal.distance else "JKCal"
                if cal_distance > 0:
                    details.append(
                        f"{best_name} R{best_cal.relic_tier}->R7 (d={cal_distance:.1f})"
                    )
                else:
                    details.append(f"{best_name} OK")
            else:
                details.append("no Cal")

            near_qualifying.append(
                PlayerDistance(
                    player_name=player_name,
                    distance=player_distance,
                    details=", ".join(details),
                )
            )

    # Sort near-qualifying by distance (closest first)
    near_qualifying.sort(key=lambda p: (p.distance, p.player_name))

    # Calculate distance to fill the gap (sum of top N closest players needed)
    gap = max(0, ZEFFO_THRESHOLD - len(qualifying_players))
    farmable_players = [p for p in near_qualifying if p.distance < float("inf")]
    distance_to_fill = (
        sum(p.distance for p in farmable_players[:gap]) if gap > 0 else 0.0
    )

    return BonusZoneReadiness(
        zone_name="Zeffo",
        threshold=ZEFFO_THRESHOLD,
        qualifying_players=qualifying_players,
        qualifying_count=len(qualifying_players),
        near_qualifying=near_qualifying,
        distance_to_fill_gap=distance_to_fill,
        farmable_count=len(farmable_players),
        is_unlockable=len(qualifying_players) >= ZEFFO_THRESHOLD,
    )


def analyze_mandalore_readiness(rosters: List[PlayerResponse]) -> BonusZoneReadiness:
    """
    Analyze guild readiness for Mandalore.
    Requirement: Bo-Katan (Mand'alor) AND The Mandalorian (Beskar Armor)

    For players who already have both characters:
        distance = R7 distance for each
    For players missing characters:
        distance = prereq distance to unlock + R7 distance for the unlocked character
    """
    qualifying_players = []
    near_qualifying = []

    for roster in rosters:
        player_name = roster.data.name
        units_status = get_player_unit_status(roster, MANDALORE_UNITS)

        bokatan = units_status["MANDALORBOKATAN"]
        beskar = units_status["THEMANDALORIANBESKARARMOR"]

        # Check prereq status for characters player doesn't have
        bokatan_prereq = (
            calculate_bokatan_prereq_status(roster) if not bokatan.has_unit else None
        )
        beskar_prereq = (
            calculate_beskar_prereq_status(roster) if not beskar.has_unit else None
        )

        # Calculate total distance
        # For each character: if owned, use direct R7 distance; else use prereq distance + unlock R7 distance

        # Beskar Mando distance
        if beskar.has_unit:
            beskar_total = beskar.distance
        elif beskar_prereq and beskar_prereq.prereq_distance < float("inf"):
            # Can unlock Beskar via prereqs, then need to get to R7
            # Beskar unlocks at 7*, so star distance is 0, just need gear/relic
            # Distance = prereq farming + G1->R7 for newly unlocked Beskar
            beskar_unlock_to_r7 = calculate_unit_distance(-1, 1, 7, MIN_RELIC_TIER)
            beskar_total = beskar_prereq.prereq_distance + beskar_unlock_to_r7
        else:
            beskar_total = float("inf")

        # Bo-Katan distance
        if bokatan.has_unit:
            bokatan_total = bokatan.distance
        elif bokatan_prereq and bokatan_prereq.prereq_distance < float("inf"):
            # Can unlock Bo-Katan via prereqs, then need to get to R7
            # Bo-Katan unlocks at 7*, so star distance is 0
            bokatan_unlock_to_r7 = calculate_unit_distance(-1, 1, 7, MIN_RELIC_TIER)
            bokatan_total = bokatan_prereq.prereq_distance + bokatan_unlock_to_r7
        else:
            bokatan_total = float("inf")

        player_distance = bokatan_total + beskar_total

        if bokatan.distance == 0 and beskar.distance == 0:
            qualifying_players.append(player_name)
        else:
            # Build status string with distances
            details = []

            # Bo-Katan status
            if bokatan.has_unit:
                if bokatan.distance > 0:
                    details.append(
                        f"Bo-Katan R{bokatan.relic_tier}->R7 (d={bokatan.distance:.1f})"
                    )
                else:
                    details.append("Bo-Katan OK")
            else:
                # Show prereq details
                if bokatan_prereq and bokatan_prereq.prereq_distance < float("inf"):
                    prereq_summary = ", ".join(bokatan_prereq.missing_prereqs[:3])
                    if len(bokatan_prereq.missing_prereqs) > 3:
                        prereq_summary += "..."
                    details.append(
                        f"no Bo-Katan [{prereq_summary}] (d={bokatan_prereq.prereq_distance:.1f})"
                    )
                else:
                    details.append("no Bo-Katan (blocked)")

            # Beskar status
            if beskar.has_unit:
                if beskar.distance > 0:
                    details.append(
                        f"Beskar R{beskar.relic_tier}->R7 (d={beskar.distance:.1f})"
                    )
                else:
                    details.append("Beskar OK")
            else:
                # Show prereq details
                if beskar_prereq and beskar_prereq.prereq_distance < float("inf"):
                    prereq_summary = ", ".join(beskar_prereq.missing_prereqs[:3])
                    if len(beskar_prereq.missing_prereqs) > 3:
                        prereq_summary += "..."
                    details.append(
                        f"no Beskar [{prereq_summary}] (d={beskar_prereq.prereq_distance:.1f})"
                    )
                else:
                    details.append("no Beskar (blocked)")

            near_qualifying.append(
                PlayerDistance(
                    player_name=player_name,
                    distance=player_distance,
                    details=", ".join(details),
                )
            )

    # Sort near-qualifying by distance (closest first)
    near_qualifying.sort(key=lambda p: (p.distance, p.player_name))

    # Calculate distance to fill the gap (sum of top N closest players needed)
    gap = max(0, MANDALORE_THRESHOLD - len(qualifying_players))
    farmable_players = [p for p in near_qualifying if p.distance < float("inf")]
    distance_to_fill = (
        sum(p.distance for p in farmable_players[:gap]) if gap > 0 else 0.0
    )

    return BonusZoneReadiness(
        zone_name="Mandalore",
        threshold=MANDALORE_THRESHOLD,
        qualifying_players=qualifying_players,
        qualifying_count=len(qualifying_players),
        near_qualifying=near_qualifying,
        distance_to_fill_gap=distance_to_fill,
        farmable_count=len(farmable_players),
        is_unlockable=len(qualifying_players) >= MANDALORE_THRESHOLD,
    )


def print_readiness_report(readiness: BonusZoneReadiness) -> None:
    """Print a formatted readiness report for a bonus zone."""
    status = "[YES] UNLOCKABLE" if readiness.is_unlockable else "[NO] NOT YET"
    progress = f"{readiness.qualifying_count}/{readiness.threshold}"
    gap = max(0, readiness.threshold - readiness.qualifying_count)

    print(f"\n{'='*60}")
    print(f"  {readiness.zone_name.upper()} BONUS ZONE")
    print(f"{'='*60}")
    print(f"  Status: {status}")
    print(f"  Progress: {progress} ({readiness.qualifying_count} qualifying)")
    if gap > 0:
        print(f"  Gap: Need {gap} more players")
        print(
            f"  Farmable Players: {readiness.farmable_count} (own all required units)"
        )
        if readiness.farmable_count < gap:
            print(
                f"  ** WARNING: Only {readiness.farmable_count} can farm to qualify, but need {gap}!"
            )
        actual_farmable = min(gap, readiness.farmable_count)
        print(
            f"  Distance to Fill Gap: {readiness.distance_to_fill_gap:.1f} (top {actual_farmable} closest)"
        )
    print()

    if readiness.qualifying_players:
        print(f"  Qualifying Players ({len(readiness.qualifying_players)}):")
        for name in sorted(readiness.qualifying_players):
            print(f"    - {name}")

    if readiness.near_qualifying:
        print("\n  Near-Qualifying Players (sorted by distance, closest first):")
        # Show top 15 closest
        for player in readiness.near_qualifying[:15]:
            print(
                f"    - [{player.distance:.1f}] {player.player_name}: {player.details}"
            )
        if len(readiness.near_qualifying) > 15:
            print(f"    ... and {len(readiness.near_qualifying) - 15} more players")


def print_officer_writeup(
    zeffo: BonusZoneReadiness,
    mandalore: BonusZoneReadiness,
    rosters: List[PlayerResponse],
) -> None:
    """Generate a detailed writeup for guild officers."""

    zeffo_gap = max(0, zeffo.threshold - zeffo.qualifying_count)
    mandalore_gap = max(0, mandalore.threshold - mandalore.qualifying_count)

    print("\n" + "=" * 70)
    print("  GUILD OFFICER BRIEFING: BONUS ZONE STRATEGY")
    print("  Rise of the Empire Territory Battle")
    print("=" * 70)

    # Executive Summary
    print("\n=== EXECUTIVE SUMMARY ===")
    print("-" * 70)

    if mandalore.distance_to_fill_gap < zeffo.distance_to_fill_gap:
        recommendation = "MANDALORE"
    else:
        recommendation = "ZEFFO"

    print(
        f"""
  Current Status:
  * Zeffo:     {zeffo.qualifying_count}/30 ready ({zeffo.qualifying_count/30*100:.0f}%) - need {zeffo_gap} more
  * Mandalore: {mandalore.qualifying_count}/25 ready ({mandalore.qualifying_count/25*100:.0f}%) - need {mandalore_gap} more

  Recommendation: Focus farming efforts on {recommendation} (lower farming distance)
  
  Key Insight: While Mandalore has more players "ready" (60% vs 30%), the 
  unlock requirements for Bo-Katan (Mand'alor) create a significant farming
  chain that must be considered.
"""
    )

    # Unlock Requirements Explanation
    print("\n=== UNLOCK REQUIREMENTS ===")
    print("-" * 70)
    print(
        """
  ZEFFO Bonus Zone (need 30/30):
    Each player needs: Cere Junda R7 + (Cal Kestis OR JK Cal) R7
      Note: JK Cal unlock requires Cal R7 + 5 Jedi at R5+ (not tracked here)

  MANDALORE Bonus Zone (need 25/25):
    Each player needs: Bo-Katan (Mand'alor) R7 + Beskar Mando R7
     
    Bo-Katan (Mand'alor) unlock requires R7 for ALL of:
      - Kelleran Beq
      - Paz Vizsla
      - IG-12 & Grogu
      - The Mandalorian (Beskar Armor)
     
    Beskar Mando unlock requires 7* G12 for ALL of:
      - The Mandalorian
      - Greef Karga
      - Cara Dune
      - IG-11
      - Kuiil
"""
    )

    # Zeffo Priority List
    print("\n=== ZEFFO FARMING PRIORITIES ===")
    print("-" * 70)
    print(f"  Currently qualifying: {zeffo.qualifying_count}/30")
    print(f"  Gap to fill: {zeffo_gap} players")
    print(f"  Total distance for top {zeffo_gap}: {zeffo.distance_to_fill_gap:.1f}")
    print()
    print("  TOP 15 CLOSEST TO QUALIFYING:")
    print("  " + "-" * 66)
    print(f"  {'Player':<20} {'Distance':>8}  {'What They Need'}")
    print("  " + "-" * 66)
    for player in zeffo.near_qualifying[:15]:
        print(f"  {player.player_name:<20} {player.distance:>8.1f}  {player.details}")

    # Mandalore Priority List
    print("\n\n=== MANDALORE FARMING PRIORITIES ===")
    print("-" * 70)
    print(f"  Currently qualifying: {mandalore.qualifying_count}/25")
    print(f"  Gap to fill: {mandalore_gap} players")
    print(
        f"  Total distance for top {mandalore_gap}: {mandalore.distance_to_fill_gap:.1f}"
    )
    print()
    print("  TOP 15 CLOSEST TO QUALIFYING:")
    print("  " + "-" * 66)
    print(f"  {'Player':<20} {'Distance':>8}  {'What They Need'}")
    print("  " + "-" * 66)
    for player in mandalore.near_qualifying[:15]:
        # Truncate details if too long
        details = player.details
        if len(details) > 55:
            details = details[:52] + "..."
        print(f"  {player.player_name:<20} {player.distance:>8.1f}  {details}")

    # Quick Win Analysis
    print("\n\n=== QUICK WINS (Distance < 5) ===")
    print("-" * 70)

    zeffo_quick = [p for p in zeffo.near_qualifying if p.distance < 5]
    mandalore_quick = [p for p in mandalore.near_qualifying if p.distance < 5]

    print(f"\n  ZEFFO Quick Wins ({len(zeffo_quick)} players):")
    if zeffo_quick:
        for p in zeffo_quick:
            print(f"    - {p.player_name}: {p.details}")
    else:
        print("    (none)")

    print(f"\n  MANDALORE Quick Wins ({len(mandalore_quick)} players):")
    if mandalore_quick:
        for p in mandalore_quick:
            print(f"    - {p.player_name}: {p.details}")
    else:
        print("    (none)")

    # Players who qualify for both
    print("\n\n=== PLAYERS READY FOR BOTH ZONES ===")
    print("-" * 70)
    both_ready = set(zeffo.qualifying_players) & set(mandalore.qualifying_players)
    zeffo_only = set(zeffo.qualifying_players) - set(mandalore.qualifying_players)
    mandalore_only = set(mandalore.qualifying_players) - set(zeffo.qualifying_players)

    print(f"\n  Ready for BOTH ({len(both_ready)}):")
    if both_ready:
        for name in sorted(both_ready):
            print(f"    - {name}")
    else:
        print("    (none)")

    print(f"\n  Ready for ZEFFO only ({len(zeffo_only)}):")
    if zeffo_only:
        for name in sorted(zeffo_only):
            print(f"    - {name}")
    else:
        print("    (none)")

    print(f"\n  Ready for MANDALORE only ({len(mandalore_only)}):")
    if mandalore_only:
        for name in sorted(mandalore_only):
            print(f"    - {name}")
    else:
        print("    (none)")

    # Strategic Recommendation
    print("\n\n=== STRATEGIC ANALYSIS ===")
    print("-" * 70)

    # Calculate average distance per player needed
    zeffo_avg = zeffo.distance_to_fill_gap / zeffo_gap if zeffo_gap > 0 else 0
    mandalore_avg = (
        mandalore.distance_to_fill_gap / mandalore_gap if mandalore_gap > 0 else 0
    )

    print(
        f"""
  ZEFFO Analysis:
  - Need {zeffo_gap} more players to unlock
  - {len(zeffo_quick)} players are within "quick win" range (d<5)
  - Average farming distance per player: {zeffo_avg:.1f}
  - Total guild farming effort: {zeffo.distance_to_fill_gap:.1f}

  MANDALORE Analysis:
  - Need {mandalore_gap} more players to unlock
  - {len(mandalore_quick)} players are within "quick win" range (d<5)
  - Average farming distance per player: {mandalore_avg:.1f}
  - Total guild farming effort: {mandalore.distance_to_fill_gap:.1f}

  RECOMMENDATION:
"""
    )

    if mandalore.distance_to_fill_gap < zeffo.distance_to_fill_gap:
        print(
            f"""  
  >>> FOCUS ON MANDALORE FIRST <<<
  
  Rationale:
  * Lower total farming distance ({mandalore.distance_to_fill_gap:.1f} vs {zeffo.distance_to_fill_gap:.1f})
  * Fewer players needed to reach unlock ({mandalore_gap} vs {zeffo_gap})
  * {len(mandalore_quick)} quick wins available
  
  Priority Players to Contact:
"""
        )
        for i, p in enumerate(mandalore.near_qualifying[:5], 1):
            print(f"    {i}. {p.player_name} (d={p.distance:.1f})")
    else:
        print(
            f"""  
  >>> FOCUS ON ZEFFO FIRST <<<
  
  Rationale:
  * Lower total farming distance ({zeffo.distance_to_fill_gap:.1f} vs {mandalore.distance_to_fill_gap:.1f})
  * {len(zeffo_quick)} quick wins available
  * Mandalore unlock chain is complex (Beskar prereqs -> Beskar -> Bo-Katan prereqs -> Bo-Katan)
  
  Priority Players to Contact:
"""
        )
        for i, p in enumerate(zeffo.near_qualifying[:5], 1):
            print(f"    {i}. {p.player_name} (d={p.distance:.1f})")

    print("\n" + "=" * 70)
    print("  END OF OFFICER BRIEFING")
    print("=" * 70 + "\n")


class BonusReadinessApp:
    """Application for analyzing Rise of the Empire bonus zone readiness."""

    def analyze(self, guild_id: str) -> None:
        """Analyze guild readiness for bonus zones."""
        print("\n" + "=" * 60)
        print("  BONUS ZONE READINESS ANALYSIS")
        print("  Rise of the Empire Territory Battle")
        print("=" * 60)

        # Load guild data and filter to current members only
        guild_data = load_guild_data(guild_id)
        guild_name = guild_data.get("name", "Unknown Guild")
        member_ally_codes = get_current_member_ally_codes(guild_data)
        print(f"\n  Guild: {guild_name}")
        print(f"  Current members: {len(member_ally_codes)}")

        rosters = load_player_rosters(member_ally_codes)
        print(f"  Loaded {len(rosters)} player rosters")

        # Analyze both zones
        zeffo = analyze_zeffo_readiness(rosters)
        mandalore = analyze_mandalore_readiness(rosters)

        # Print reports
        print_readiness_report(zeffo)
        print_readiness_report(mandalore)

        # Comparison summary
        print("\n" + "=" * 60)
        print("  COMPARISON SUMMARY")
        print("=" * 60)

        zeffo_pct = (zeffo.qualifying_count / zeffo.threshold) * 100
        mandalore_pct = (mandalore.qualifying_count / mandalore.threshold) * 100

        zeffo_gap = max(0, zeffo.threshold - zeffo.qualifying_count)
        mandalore_gap = max(0, mandalore.threshold - mandalore.qualifying_count)

        print("\n  By Qualifying Count:")
        print(
            f"    Zeffo:     {zeffo.qualifying_count}/{zeffo.threshold} = {zeffo_pct:.1f}% (need {zeffo_gap} more)"
        )
        print(
            f"    Mandalore: {mandalore.qualifying_count}/{mandalore.threshold} = {mandalore_pct:.1f}% (need {mandalore_gap} more)"
        )

        print("\n  By Farmable Players (own all required units):")
        print(f"    Zeffo:     {zeffo.farmable_count} farmable (need {zeffo_gap})")
        print(
            f"    Mandalore: {mandalore.farmable_count} farmable (need {mandalore_gap})"
        )

        print("\n  By Distance to Fill Gap (farming effort for closest N players):")
        zeffo_actual = min(zeffo_gap, zeffo.farmable_count)
        mandalore_actual = min(mandalore_gap, mandalore.farmable_count)
        print(
            f"    Zeffo:     {zeffo.distance_to_fill_gap:.1f} distance (for {zeffo_actual} players)"
        )
        print(
            f"    Mandalore: {mandalore.distance_to_fill_gap:.1f} distance (for {mandalore_actual} players)"
        )

        # Check if either zone is blocked by lack of farmable players
        zeffo_blocked = zeffo.farmable_count < zeffo_gap
        mandalore_blocked = mandalore.farmable_count < mandalore_gap

        # Determine winner based on distance (lower is better)
        if zeffo_blocked and not mandalore_blocked:
            print("\n  >>> Guild is CLOSER to unlocking MANDALORE <<<")
            print(
                f"      (Zeffo blocked: only {zeffo.farmable_count} farmable but need {zeffo_gap})"
            )
        elif mandalore_blocked and not zeffo_blocked:
            print("\n  >>> Guild is CLOSER to unlocking ZEFFO <<<")
            print(
                f"      (Mandalore blocked: only {mandalore.farmable_count} farmable but need {mandalore_gap})"
            )
        elif zeffo.distance_to_fill_gap < mandalore.distance_to_fill_gap:
            print("\n  >>> Guild is CLOSER to unlocking ZEFFO <<<")
            print(
                f"      (Lower farming distance: {zeffo.distance_to_fill_gap:.1f} vs {mandalore.distance_to_fill_gap:.1f})"
            )
        elif mandalore.distance_to_fill_gap < zeffo.distance_to_fill_gap:
            print("\n  >>> Guild is CLOSER to unlocking MANDALORE <<<")
            print(
                f"      (Lower farming distance: {mandalore.distance_to_fill_gap:.1f} vs {zeffo.distance_to_fill_gap:.1f})"
            )
        else:
            print("\n  >>> Guild is EQUALLY close to both zones <<<")

        print()

        # Generate officer writeup
        print_officer_writeup(zeffo, mandalore, rosters)


def run_rote_bonus_readiness():
    """Entry point for rote-bonus-readiness CLI command."""
    # Parse command line arguments
    if len(sys.argv) < 2 or sys.argv[1] in ("--help", "-h"):
        print("Usage: rote_bonus_readiness <guild_id>")
        print()
        print("Analyze guild readiness for Rise of the Empire bonus zones.")
        print()
        print("Arguments:")
        print("  guild_id  The guild ID to analyze (from cached data)")
        print()
        print("The command reads cached data from the 'data/' directory.")
        print("Run 'rote-platoon <ally_code>' first to populate the cache.")
        if len(sys.argv) < 2:
            sys.exit(1)
        sys.exit(0)

    guild_id = sys.argv[1]

    try:
        app = BonusReadinessApp()
        app.analyze(guild_id)
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
