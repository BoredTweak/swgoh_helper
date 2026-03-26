import dotenv
import os
import sys
import traceback
import requests
from collections import defaultdict
from typing import Optional

from .swgoh_gg_client import SwgohGGClient
from .kyrotech_analyzer import KyrotechAnalyzer, RosterAnalyzer, KYROTECH_SALVAGE_IDS
from .results_presenter import ResultsPresenter
from .rote_coverage import (
    build_coverage_matrix,
    load_requirements,
    CoverageAnalyzer,
    RoteConfig,
)
from .rote_models import RotePath, SimpleRoteRequirements
from .rote_gap_analyzer import GapAnalyzer
from .rote_bottleneck_analyzer import BottleneckAnalyzer
from .rote_proximity_analyzer import ProximityAnalyzer, ProgressStage


dotenv.load_dotenv()

SWGOH_API_KEY = os.getenv("SWGOH_API_KEY")


class KyrotechAnalysisApp:
    """Main application orchestrator for kyrotech analysis."""

    def __init__(self, api_key: str):
        self.client = SwgohGGClient(api_key)
        self.presenter = ResultsPresenter()

    def analyze_player(self, ally_code: str) -> None:
        """Analyze a player's roster for kyrotech requirements."""
        try:
            units_data, gear_data, player_data = self._fetch_game_data(ally_code)

            kyrotech_analyzer = KyrotechAnalyzer(gear_data)
            roster_analyzer = RosterAnalyzer(kyrotech_analyzer)

            units_by_id = roster_analyzer.build_units_lookup(units_data.data)
            results = roster_analyzer.analyze_roster(player_data.units, units_by_id)

            self.presenter.display_results(results)

        except requests.exceptions.RequestException as e:
            self._handle_request_error(e)
        except Exception as e:
            self._handle_general_error(e)

    def find_top_faction_kyrotech(self, ally_code: str, faction: str) -> None:
        """Find all characters with kyrotech needs for a specific faction.

        Args:
            ally_code: Player's ally code
            faction: The faction to filter by (e.g., "Empire", "Rebel", "Sith")
        """
        try:
            units_data, gear_data, player_data = self._fetch_game_data(ally_code)

            kyrotech_analyzer = KyrotechAnalyzer(gear_data)
            roster_analyzer = RosterAnalyzer(kyrotech_analyzer)

            units_by_id = roster_analyzer.build_units_lookup(units_data.data)
            results = roster_analyzer.analyze_faction_kyrotech(
                player_data.units, units_by_id, faction
            )

            if results:
                print(f"\n{'='*60}")
                print(f"{faction} Characters by Kyrotech Needs")
                print(f"{'='*60}\n")

                for name, gear_level, kyrotech_needs, total_kyrotech in results:
                    print(f"{name} (G{gear_level}): {total_kyrotech} total kyrotech")
                    for salvage_id, count in kyrotech_needs.items():
                        salvage_name = KYROTECH_SALVAGE_IDS.get(salvage_id, salvage_id)
                        print(f"  - {salvage_name}: {count}")
                    print()
            else:
                print(f"\nNo {faction} characters found that need kyrotech.")

        except requests.exceptions.RequestException as e:
            self._handle_request_error(e)
        except Exception as e:
            self._handle_general_error(e)

    def _fetch_game_data(self, ally_code: str):
        print("Loading game units data...")
        units_data = self.client.get_units()

        print("Loading gear recipe data...")
        gear_data = self.client.get_gear_recipes()

        print(f"Fetching player data for ally code: {ally_code}...")
        player_data = self.client.get_player_units(ally_code)

        return units_data, gear_data, player_data

    def _handle_request_error(
        self, error: requests.exceptions.RequestException
    ) -> None:
        """Handle API request errors."""
        print(f"Error fetching data: {error}")
        sys.exit(1)

    def _handle_general_error(self, error: Exception) -> None:
        """Handle general application errors."""
        print(f"Error: {error}")
        traceback.print_exc()
        sys.exit(1)


class RotePlatoonApp:
    """Application for analyzing Rise of the Empire Territory Battle platoon requirements."""

    def __init__(self, api_key: str):
        self.client = SwgohGGClient(api_key)

    def analyze_guild(
        self, ally_code: str, max_phase: Optional[str] = None, refresh: bool = False
    ) -> None:
        """Fetch guild information and analyze platoon coverage."""
        try:
            guild_id, guild_name, member_ally_codes = (
                self.client.get_guild_from_ally_code(ally_code)
            )

            print(f"\n{'='*60}")
            print(f"Guild: {guild_name}")
            print(f"Guild ID: {guild_id}")
            print(f"Members: {len(member_ally_codes)}")
            print(f"{'='*60}")

            if refresh:
                print("\nInvalidating player caches (--refresh specified)...")
                self.client.invalidate_player_caches(member_ally_codes)

            print("\nLoading unit metadata...")
            units_data = self.client.get_units()

            rosters = self.client.get_guild_rosters(
                member_ally_codes, delay_seconds=1.0
            )

            print(f"\nSuccessfully loaded data for {len(rosters)} guild members.")

            print("\nBuilding coverage matrix...")
            coverage_matrix = build_coverage_matrix(
                rosters=rosters,
                units_data=units_data,
                guild_name=guild_name,
                guild_id=guild_id,
            )

            print(f"Analyzed {len(coverage_matrix.units)} unique units across roster.")

            print("\nLoading ROTE platoon requirements...")
            requirements = load_requirements()

            if max_phase:
                requirements = self._filter_requirements_by_phase(
                    requirements, max_phase
                )
                print(
                    f"Filtered to phase {max_phase}: {len(requirements.requirements)} requirements."
                )
            else:
                print(f"Loaded {len(requirements.requirements)} platoon requirements.")

            print("\nAnalyzing platoon coverage...")
            analyzer = CoverageAnalyzer(coverage_matrix, requirements)

            gap_analyzer = GapAnalyzer(coverage_matrix, requirements)
            bottleneck_analyzer = BottleneckAnalyzer(coverage_matrix, requirements)
            proximity_analyzer = ProximityAnalyzer(coverage_matrix, requirements)

            self._display_rote_results(
                analyzer,
                coverage_matrix,
                gap_analyzer,
                bottleneck_analyzer,
                proximity_analyzer,
            )

        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"Error: {e}")
            traceback.print_exc()
            sys.exit(1)

    def _filter_requirements_by_phase(self, requirements, max_phase: str):
        """Filter requirements to only include territories up to max_phase."""
        base_phases = ["1", "2", "3", "4", "5", "6"]

        try:
            max_phase_idx = base_phases.index(max_phase)
        except ValueError:
            print(f"Warning: Unknown phase '{max_phase}', using all phases.")
            return requirements

        included_phases = set()
        for i in range(max_phase_idx + 1):
            phase = base_phases[i]
            included_phases.add(phase)
            included_phases.add(f"{phase}b")  # Include bonus planet for this phase

        filtered_reqs = []
        for req in requirements.requirements:
            territory_phase = RoteConfig.TERRITORY_PHASE.get(req.territory, "99")
            if territory_phase in included_phases:
                filtered_reqs.append(req)

        return SimpleRoteRequirements(
            version=requirements.version,
            last_updated=requirements.last_updated,
            requirements=filtered_reqs,
        )

    def _display_rote_results(
        self,
        analyzer: CoverageAnalyzer,
        matrix,
        gap_analyzer,
        bottleneck_analyzer,
        proximity_analyzer=None,
    ) -> None:
        """Display complete ROTE platoon analysis results."""
        summary = analyzer.get_coverage_summary_by_territory()

        print(f"\n{'='*60}")
        print(f"Guild: {matrix.guild_name} | Members: {matrix.member_count}")
        print(f"\nROTE PLATOON COVERAGE SUMMARY")
        print(f"{'='*60}")

        # Coverage by path
        for path in [RotePath.DARK_SIDE, RotePath.NEUTRAL, RotePath.LIGHT_SIDE]:
            path_label = path.value.replace("_", " ").title()
            print(f"\n{path_label}:")
            print("-" * 40)

            path_territories = [
                (key, data) for key, data in summary.items() if key[0] == path
            ]

            if not path_territories:
                print("  No requirements found.")
                continue

            for (_, territory), data in sorted(
                path_territories,
                key=lambda x: RoteConfig.TERRITORY_PHASE.get(x[0][1], "99"),
            ):
                total = data["total_slots"]
                covered = data["covered_slots"]
                pct = (covered / total * 100) if total > 0 else 0
                phase = RoteConfig.TERRITORY_PHASE.get(territory, "?")

                if pct == 100:
                    status = "✅"
                elif pct >= 80:
                    status = "⚠️"
                else:
                    status = "❌"

                print(
                    f"  {status} P{phase} {territory}: {covered}/{total} slots ({pct:.0f}%)"
                )

        all_gaps = gap_analyzer.get_all_gaps()
        unfilled_by_tier: dict[int, dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )
        for gap in all_gaps:
            if gap.slots_unfillable > 0:
                unfilled_by_tier[gap.min_relic][gap.unit_name] += gap.slots_unfillable

        if unfilled_by_tier:
            print(f"\nUnfillable platoon slots")
            print("-" * 40)

            for relic in sorted(unfilled_by_tier.keys()):
                units = unfilled_by_tier[relic]
                if relic <= 5:
                    phase_label = "Tier 1 Planets"
                elif relic == 6:
                    phase_label = "Tier 2 Planets"
                else:
                    phase_label = "Tier 3 Planets"

                print(f"\n{phase_label} – R{relic}:")
                for unit_name in sorted(units.keys()):
                    count = units[unit_name]
                    print(f"  {unit_name} – R{relic} x{count}")

        # Analysis section
        print(f"\n{'='*60}")
        print("ANALYSIS")
        print(f"{'='*60}")

        # Critical gaps
        critical_gaps = gap_analyzer.get_critical_gaps()
        print(f"\nCritical gaps")
        print("-" * 40)

        if not critical_gaps:
            print("\n✅ No critical gaps detected!")
        else:
            gaps_by_territory = {}
            for gap in critical_gaps:
                key = (gap.path, gap.territory)
                if key not in gaps_by_territory:
                    gaps_by_territory[key] = []
                gaps_by_territory[key].append(gap)

            for (path, territory), gaps in sorted(
                gaps_by_territory.items(),
                key=lambda x: (
                    x[0][0].value,
                    RoteConfig.TERRITORY_PHASE.get(x[0][1], "99"),
                ),
            ):
                phase = RoteConfig.TERRITORY_PHASE.get(territory, "?")
                path_label = path.value.replace("_", " ").title()
                print(f"\n{path_label} - P{phase} {territory}:")

                for gap in sorted(
                    gaps, key=lambda g: (g.players_available, g.unit_name)
                ):
                    owners = ", ".join(gap.player_names) if gap.player_names else ""
                    owners_suffix = f" ({owners})" if owners else ""
                    print(
                        f"  - {gap.unit_name} R{gap.min_relic}: "
                        f"{gap.players_available}/{gap.slots_needed} players{owners_suffix}"
                    )

        # Limited availability units
        rare_units = bottleneck_analyzer.identify_unicorn_units()
        available_rare = [u for u in rare_units if u.owner_count > 0]

        print(f"\n\nLimited availability units")
        print("-" * 40)

        if not available_rare:
            print("\n✅ No limited availability units!")
        else:
            sole_owner = [u for u in available_rare if u.owner_count == 1]
            two_owners = [u for u in available_rare if u.owner_count == 2]
            three_owners = [u for u in available_rare if u.owner_count == 3]

            if sole_owner:
                units_str = "\n  ".join(
                    f"{u.unit_name} R{u.min_relic}→{u.owner_names[0]}"
                    for u in sole_owner
                )
                print(f"\n1 owner ({len(sole_owner)}):\n  {units_str}")

            if two_owners:
                units_str = "\n  ".join(
                    f"{u.unit_name} R{u.min_relic}→{', '.join(u.owner_names[:2])}"
                    for u in two_owners
                )
                print(f"\n2 owners ({len(two_owners)}):\n  {units_str}")

            if three_owners:
                units_str = "\n  ".join(
                    f"{u.unit_name} R{u.min_relic}→{', '.join(u.owner_names[:3])}"
                    for u in three_owners
                )
                print(f"\n3 owners ({len(three_owners)}):\n  {units_str}")

        # Farming recommendations (closest players to gaps)
        if proximity_analyzer:
            self._display_farming_recommendations(proximity_analyzer)

        print()

    def _display_farming_recommendations(self, proximity_analyzer) -> None:
        """Display farming recommendations for platoon gaps."""
        recommendations = proximity_analyzer.get_farming_recommendations(
            max_recommendations=15
        )

        print(f"\n\nFarming recommendations (closest to gaps)")
        print("-" * 40)

        if not recommendations:
            print("\n✅ No actionable farming recommendations!")
            return

        for unit_name, relic_req, closest_players in recommendations:
            print(f"\n{unit_name} {relic_req}:")

            # Group players by distance score to handle ties
            # Show up to 3 distinct distance levels, but include ALL tied players at each level
            distance_groups: list[list] = []
            current_group: list = []
            current_score: float | None = None

            for p in closest_players:
                if current_score is None or p.distance_score == current_score:
                    current_group.append(p)
                    current_score = p.distance_score
                else:
                    if current_group:
                        distance_groups.append(current_group)
                    current_group = [p]
                    current_score = p.distance_score

            if current_group:
                distance_groups.append(current_group)

            # Display up to 3 distance groups
            groups_to_show = distance_groups[:3]

            for group in groups_to_show:
                # All players in a group have the same distance, so use first to get label
                first = group[0]

                if first.stage == ProgressStage.STAR_GATED:
                    label = f"needs {first.star_gap}★ first"
                elif first.stage == ProgressStage.GEARING:
                    label = f"needs G13 (+{first.gear_gap} gear)"
                elif first.stage == ProgressStage.GEAR_13:
                    label = "at G13, needs relic"
                else:  # RELICED
                    label = f"+{first.relic_gap}R needed"

                # Collect player names
                names = [p.player_name for p in group]
                names_str = ", ".join(names)
                count = len(names)

                print(f"  - {label} ({count}): {names_str}")


def print_usage():
    """Print usage information."""
    print("Usage: python app.py <command> [arguments]")
    print()
    print("Commands:")
    print(
        "  kyrotech <ally_code>      Analyze a player's roster for kyrotech requirements"
    )
    print("  rote_platoon <ally_code> [--max-phase N] [--refresh]")
    print("                            Analyze guild for RotE platoon requirements")
    print("                            --max-phase: Limit analysis to phases up to N")
    print("                                         (e.g., 4, 3b, 5)")
    print(
        "                            --refresh:   Force fresh data from API (ignore cache)"
    )
    print()
    print("Examples:")
    print("  python app.py kyrotech 123-456-789")
    print("  python app.py rote_platoon 123-456-789")
    print("  python app.py rote_platoon 123-456-789 --max-phase 4")
    print("  python app.py rote_platoon 123-456-789 --refresh")


def run_kyrotech():
    """Entry point for kyrotech CLI command."""
    if len(sys.argv) < 2:
        print("Usage: kyrotech <ally_code> [--faction FACTION_NAME]")
        print("Example: kyrotech 123-456-789")
        print("         kyrotech 123-456-789 --faction Empire")
        sys.exit(1)

    if not SWGOH_API_KEY:
        print("Error: SWGOH_API_KEY not found in environment variables")
        print("Please create a .env file with your API key")
        sys.exit(1)

    ally_code = sys.argv[1]
    faction = None

    for i, arg in enumerate(sys.argv[2:], start=2):
        if arg == "--faction" and i + 1 < len(sys.argv):
            faction = sys.argv[i + 1]
            break

    app = KyrotechAnalysisApp(SWGOH_API_KEY)
    if faction:
        app.find_top_faction_kyrotech(ally_code, faction)
    else:
        app.analyze_player(ally_code)


def run_rote_platoon():
    """Entry point for rote-platoon CLI command."""
    if len(sys.argv) < 2:
        print("Usage: rote-platoon <ally_code> [--max-phase N] [--refresh]")
        sys.exit(1)

    if not SWGOH_API_KEY:
        print("Error: SWGOH_API_KEY not found in environment variables")
        print("Please create a .env file with your API key")
        sys.exit(1)

    ally_code = sys.argv[1]
    max_phase = None
    refresh = False
    for i, arg in enumerate(sys.argv[2:], start=2):
        if arg == "--max-phase" and i + 1 < len(sys.argv):
            max_phase = sys.argv[i + 1]
        elif arg == "--refresh":
            refresh = True

    app = RotePlatoonApp(SWGOH_API_KEY)
    app.analyze_guild(ally_code, max_phase=max_phase, refresh=refresh)


def main():
    """Main entry point for the application."""
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "kyrotech":
        if len(sys.argv) < 3:
            print("Error: ally_code is required for kyrotech command")
            print("Usage: python app.py kyrotech <ally_code>")
            sys.exit(1)

        if not SWGOH_API_KEY:
            print("Error: SWGOH_API_KEY not found in environment variables")
            print("Please create a .env file with your API key")
            sys.exit(1)

        ally_code = sys.argv[2]
        app = KyrotechAnalysisApp(SWGOH_API_KEY)
        app.analyze_player(ally_code)
    elif command == "rote_platoon":
        if len(sys.argv) < 3:
            print("Error: ally_code is required for rote_platoon command")
            print(
                "Usage: python app.py rote_platoon <ally_code> [--max-phase N] [--refresh]"
            )
            sys.exit(1)

        if not SWGOH_API_KEY:
            print("Error: SWGOH_API_KEY not found in environment variables")
            print("Please create a .env file with your API key")
            sys.exit(1)

        ally_code = sys.argv[2]
        max_phase = None
        refresh = False
        for i, arg in enumerate(sys.argv[3:], start=3):
            if arg == "--max-phase" and i + 1 < len(sys.argv):
                max_phase = sys.argv[i + 1]
            elif arg == "--refresh":
                refresh = True

        app = RotePlatoonApp(SWGOH_API_KEY)
        app.analyze_guild(ally_code, max_phase=max_phase, refresh=refresh)
    else:
        print(f"Unknown command: {command}")
        print()
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
