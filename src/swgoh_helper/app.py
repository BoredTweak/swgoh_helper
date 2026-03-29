import dotenv
import os
import sys
import traceback
import requests
from collections import defaultdict
from typing import Optional

from .data_access import SwgohDataService
from .kyrotech_analyzer import (
    KyrotechAnalyzer,
    RosterAnalyzer,
    KYROTECH_SALVAGE_IDS,
)
from .results_presenter import ResultsPresenter
from .rote_coverage import (
    build_coverage_matrix,
    load_requirements,
    CoverageAnalyzer,
    RoteConfig,
)
from .rote_models import SimpleRoteRequirements
from .rote_gap_analyzer import GapAnalyzer
from .rote_bottleneck_analyzer import BottleneckAnalyzer
from .rote_proximity_analyzer import ProximityAnalyzer
from .rote_presenter import RotePresenter


dotenv.load_dotenv()

SWGOH_API_KEY = os.getenv("SWGOH_API_KEY")


class KyrotechAnalysisApp:
    """Main application orchestrator for kyrotech analysis."""

    def __init__(self, api_key: str):
        self.service = SwgohDataService(api_key)
        self.presenter = ResultsPresenter()

    def analyze_player(self, ally_code: str, include_unowned: bool = False) -> None:
        """Analyze a player's roster for kyrotech requirements.

        Args:
            ally_code: Player's ally code
            include_unowned: Whether to include characters the player doesn't own
        """
        try:
            units_data, gear_data, player_data = self._fetch_game_data(ally_code)

            kyrotech_analyzer = KyrotechAnalyzer(gear_data)
            roster_analyzer = RosterAnalyzer(kyrotech_analyzer)

            units_by_id = roster_analyzer.build_units_lookup(units_data.data)

            if include_unowned:
                results = roster_analyzer.analyze_all_characters(
                    player_data.units, units_by_id
                )
                self.presenter.display_all_results(results)
            else:
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

    def find_all_faction_kyrotech(
        self,
        ally_code: str,
        faction: str,
        include_unowned: bool = True,
    ) -> None:
        """Find all characters with kyrotech needs for a faction, including unowned.

        Args:
            ally_code: Player's ally code
            faction: The faction to filter by (e.g., "Empire", "Rebel", "Sith")
            include_unowned: Whether to include characters the player doesn't own
        """
        try:
            units_data, gear_data, player_data = self._fetch_game_data(ally_code)

            kyrotech_analyzer = KyrotechAnalyzer(gear_data)
            roster_analyzer = RosterAnalyzer(kyrotech_analyzer)

            units_by_id = roster_analyzer.build_units_lookup(units_data.data)
            results = roster_analyzer.analyze_faction_all_characters(
                player_data.units,
                units_by_id,
                faction,
                include_owned=True,
                include_unowned=include_unowned,
            )

            if results:
                owned = [r for r in results if r.is_owned]
                unowned = [r for r in results if not r.is_owned]

                print(f"\n{'='*60}")
                print(f"{faction} Characters by Kyrotech Needs")
                print(f"{'='*60}")

                if owned:
                    print("\n--- OWNED CHARACTERS ---")
                    for result in owned:
                        gear_str = f"G{result.gear_level}"
                        print(
                            f"{result.name} ({gear_str}): {result.total_kyrotech} total"
                        )
                        for salvage_id, count in result.kyrotech_needs.items():
                            salvage_name = KYROTECH_SALVAGE_IDS.get(
                                salvage_id, salvage_id
                            )
                            print(f"  - {salvage_name}: {count}")

                if unowned:
                    print("\n--- NOT OWNED (Full G1-G13) ---")
                    for result in unowned:
                        print(f"{result.name}: {result.total_kyrotech} total")
                        for salvage_id, count in result.kyrotech_needs.items():
                            salvage_name = KYROTECH_SALVAGE_IDS.get(
                                salvage_id, salvage_id
                            )
                            print(f"  - {salvage_name}: {count}")
            else:
                print(f"\nNo {faction} characters found that need kyrotech.")

        except requests.exceptions.RequestException as e:
            self._handle_request_error(e)
        except Exception as e:
            self._handle_general_error(e)

    def _fetch_game_data(self, ally_code: str):
        print("Loading game units data...")
        units_data = self.service.get_all_units()

        print("Loading gear recipe data...")
        gear_data = self.service.get_all_gear()

        print(f"Fetching player data for ally code: {ally_code}...")
        player_data = self.service.get_player(ally_code)

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
        self.service = SwgohDataService(api_key)

    def analyze_guild(
        self,
        ally_code: str,
        max_phase: Optional[str] = None,
        refresh: bool = False,
        by_territory: bool = False,
    ) -> None:
        """Fetch guild information and analyze platoon coverage."""
        try:
            guild_id, guild_name, member_ally_codes = (
                self.service.get_guild_from_ally_code(ally_code)
            )

            print(f"\n{'='*60}")
            print(f"Guild: {guild_name}")
            print(f"Guild ID: {guild_id}")
            print(f"Members: {len(member_ally_codes)}")
            print(f"{'='*60}")

            if refresh:
                print("\nInvalidating player caches (--refresh specified)...")
                self.service.invalidate_player_caches(member_ally_codes)

            print("\nLoading unit metadata...")
            units_data = self.service.get_all_units()

            rosters = self.service.get_guild_rosters(
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

            presenter = RotePresenter()
            print(
                "\n"
                + presenter.format_results(
                    analyzer,
                    coverage_matrix,
                    gap_analyzer,
                    bottleneck_analyzer,
                    proximity_analyzer,
                    by_territory=by_territory,
                )
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


def print_usage():
    """Print usage information."""
    print("Usage: python app.py <command> [arguments]")
    print()
    print("Commands:")
    print(
        "  kyrotech <ally_code>      Analyze a player's roster for kyrotech requirements"
    )
    print("  rote_platoon <ally_code> [--max-phase N] [--refresh] [--by-territory]")
    print("                            Analyze guild for RotE platoon requirements")
    print("                            --max-phase: Limit analysis to phases up to N")
    print("                                         (e.g., 4, 3b, 5)")
    print(
        "                            --refresh:   Force fresh data from API (ignore cache)"
    )
    print(
        "                            --by-territory: Group farming recommendations by planet"
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
        print(
            "Usage: kyrotech <ally_code> [--faction FACTION_NAME] [--include-unowned]"
        )
        print("Example: kyrotech 123-456-789")
        print("         kyrotech 123-456-789 --faction Empire")
        print("         kyrotech 123-456-789 --include-unowned")
        sys.exit(1)

    if not SWGOH_API_KEY:
        print("Error: SWGOH_API_KEY not found in environment variables")
        print("Please create a .env file with your API key")
        sys.exit(1)

    ally_code = sys.argv[1]
    faction = None
    include_unowned = "--include-unowned" in sys.argv

    for i, arg in enumerate(sys.argv[2:], start=2):
        if arg == "--faction" and i + 1 < len(sys.argv):
            faction = sys.argv[i + 1]
            break

    app = KyrotechAnalysisApp(SWGOH_API_KEY)
    if faction:
        app.find_all_faction_kyrotech(ally_code, faction, include_unowned)
    else:
        app.analyze_player(ally_code, include_unowned)


def run_rote_platoon():
    """Entry point for rote-platoon CLI command."""
    if len(sys.argv) < 2:
        print(
            "Usage: rote-platoon <ally_code> [--max-phase N] [--refresh] [--by-territory]"
        )
        sys.exit(1)

    if not SWGOH_API_KEY:
        print("Error: SWGOH_API_KEY not found in environment variables")
        print("Please create a .env file with your API key")
        sys.exit(1)

    ally_code = sys.argv[1]
    max_phase = None
    refresh = False
    by_territory = False
    for i, arg in enumerate(sys.argv[2:], start=2):
        if arg == "--max-phase" and i + 1 < len(sys.argv):
            max_phase = sys.argv[i + 1]
        elif arg == "--refresh":
            refresh = True
        elif arg == "--by-territory":
            by_territory = True

    app = RotePlatoonApp(SWGOH_API_KEY)
    app.analyze_guild(
        ally_code, max_phase=max_phase, refresh=refresh, by_territory=by_territory
    )


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
