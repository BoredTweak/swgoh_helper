import dotenv
import os
import sys
import traceback
import requests
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
    filter_requirements_by_phase,
    load_requirements,
    CoverageAnalyzer,
    RoteConfig,
)
from .models import VALID_ROTE_OUTPUT_FORMATS
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
        output_format: str = "gaps",
        ignored_players: Optional[list[str]] = None,
    ) -> None:
        """Fetch guild information and analyze platoon coverage."""
        try:
            if output_format not in VALID_ROTE_OUTPUT_FORMATS:
                raise ValueError(
                    "Invalid --output-format. "
                    "Expected one of: all, coverage, gaps, owners, farming, farming-by-territory"
                )

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
                ignored_players=ignored_players,
            )

            print(f"Analyzed {len(coverage_matrix.units)} unique units across roster.")

            print("\nLoading ROTE platoon requirements...")
            requirements = load_requirements()

            if max_phase:
                requirements = filter_requirements_by_phase(requirements, max_phase)
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
                    output_format=output_format,
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


class RoteFarmAdvisorApp:
    """Application for generating personalized ROTE farming recommendations."""

    def __init__(self, api_key: str):
        self.service = SwgohDataService(api_key)

    def recommend_for_player(
        self,
        ally_code: str,
        max_phase: Optional[str] = None,
        max_recommendations: int = 15,
        include_unowned: bool = False,
    ) -> None:
        """Generate personalized farm recommendations for a player."""
        try:
            # Get player's guild info
            guild_id, guild_name, member_ally_codes = (
                self.service.get_guild_from_ally_code(ally_code)
            )

            print(f"\n{'='*60}")
            print(f"Guild: {guild_name}")
            print(f"Guild ID: {guild_id}")
            print(f"Members: {len(member_ally_codes)}")
            print(f"{'='*60}")

            print("\nLoading unit metadata...")
            units_data = self.service.get_all_units()

            print("\nLoading guild rosters...")
            rosters = self.service.get_guild_rosters(
                member_ally_codes, delay_seconds=1.0
            )
            print(f"Loaded data for {len(rosters)} guild members.")

            # Find the target player's roster
            target_roster = None
            ally_code_int = int(ally_code.replace("-", ""))
            for roster in rosters:
                if roster.data.ally_code == ally_code_int:
                    target_roster = roster
                    break

            if target_roster is None:
                print(
                    f"Error: Could not find player with ally code {ally_code} in guild."
                )
                sys.exit(1)

            print(f"\nAnalyzing recommendations for: {target_roster.data.name}")

            print("\nBuilding coverage matrix...")
            coverage_matrix = build_coverage_matrix(
                rosters=rosters,
                units_data=units_data,
                guild_name=guild_name,
                guild_id=guild_id,
            )

            print("\nLoading ROTE platoon requirements...")
            requirements = load_requirements()

            if max_phase:
                requirements = filter_requirements_by_phase(requirements, max_phase)
                print(
                    f"Filtered to phase {max_phase}: {len(requirements.requirements)} requirements."
                )

            print("\nGenerating personalized recommendations...")
            from .rote_farm_advisor import FarmAdvisor

            advisor = FarmAdvisor(coverage_matrix, requirements)
            report = advisor.get_player_recommendations(
                target_roster,
                max_recommendations=max_recommendations,
                include_unowned=include_unowned,
            )
            report.max_phase = max_phase

            presenter = RotePresenter()
            print("\n" + presenter.format_personal_farm_report(report))

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


def print_usage():
    """Print usage information."""
    print("Usage: python app.py <command> [arguments]")
    print()
    print("Commands:")
    print(
        "  kyrotech <ally_code>      Analyze a player's roster for kyrotech requirements"
    )
    print(
        "  rote_platoon <ally_code> [--max-phase N] [--refresh] [--output-format FORMAT] [--ignore-players PLAYER1,PLAYER2,...]"
    )
    print("                            Analyze guild for RotE platoon requirements")
    print("                            --max-phase: Limit analysis to phases up to N")
    print("                                         (e.g., 4, 3b, 5)")
    print(
        "                            --output-format: all|coverage|gaps|owners|farming|farming-by-territory"
    )
    print("                                             (default: gaps)")
    print(
        "                            --refresh:   Force fresh data from API (ignore cache)"
    )
    print(
        "                            --ignore-players: Exclude players by name or ally code"
    )
    print()
    print(
        "  rote_farm <ally_code> [--max-phase N] [--max-recommendations N] [--include-unowned]"
    )
    print(
        "                            Personal farm recommendations based on guild needs"
    )
    print("                            --max-phase: Limit analysis to phases up to N")
    print(
        "                            --max-recommendations: Max units to recommend (default 15)"
    )
    print("                            --include-unowned: Include units you don't own")
    print()
    print("Examples:")
    print("  python app.py kyrotech 123-456-789")
    print("  python app.py rote_platoon 123-456-789")
    print("  python app.py rote_platoon 123-456-789 --max-phase 4")
    print("  python app.py rote_platoon 123-456-789 --refresh")
    print("  python app.py rote_farm 123-456-789 --max-phase 4")


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


def _parse_rote_platoon_args(start_index: int) -> dict[str, object]:
    """Parse rote-platoon options."""
    max_phase = None
    refresh = False
    output_format_arg = None
    ignored_players: list[str] = []

    i = start_index
    while i < len(sys.argv):
        arg = sys.argv[i]

        if arg == "--max-phase" and i + 1 < len(sys.argv):
            max_phase = sys.argv[i + 1]
            i += 2
            continue

        if arg == "--refresh":
            refresh = True
            i += 1
            continue

        if arg == "--output-format" and i + 1 < len(sys.argv):
            output_format_arg = sys.argv[i + 1].lower()
            i += 2
            continue

        if arg in {"--by-territory", "--show-owners"}:
            raise ValueError(f"{arg} has been retired. Use --output-format instead.")

        if arg in {"--ignore-players", "--ignored-players"}:
            i += 1
            ignored_chunks: list[str] = []
            while i < len(sys.argv) and not sys.argv[i].startswith("--"):
                ignored_chunks.append(sys.argv[i])
                i += 1

            ignored_text = " ".join(ignored_chunks)
            ignored_players = [
                p.strip()
                for p in ignored_text.replace(";", ",").split(",")
                if p.strip()
            ]
            if ignored_players:
                print(f"Ignoring players: {', '.join(ignored_players)}")
            continue

        i += 1

    output_format = output_format_arg or "gaps"

    return {
        "max_phase": max_phase,
        "refresh": refresh,
        "output_format": output_format,
        "ignored_players": ignored_players,
    }


def run_rote_platoon():
    """Entry point for rote-platoon CLI command."""
    if len(sys.argv) < 2:
        print(
            "Usage: rote-platoon <ally_code> [--max-phase N] [--refresh] [--output-format FORMAT] [--ignore-players PLAYER1,PLAYER2,...]"
        )
        sys.exit(1)

    if not SWGOH_API_KEY:
        print("Error: SWGOH_API_KEY not found in environment variables")
        print("Please create a .env file with your API key")
        sys.exit(1)

    ally_code = sys.argv[1]
    try:
        options = _parse_rote_platoon_args(start_index=2)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    app = RotePlatoonApp(SWGOH_API_KEY)
    app.analyze_guild(
        ally_code,
        max_phase=options["max_phase"],
        refresh=options["refresh"],
        output_format=options["output_format"],
        ignored_players=options["ignored_players"],
    )


def run_rote_farm():
    """Entry point for rote-farm CLI command."""
    if len(sys.argv) < 2:
        print(
            "Usage: rote-farm <ally_code> [--max-phase N] [--max-recommendations N] [--include-unowned]"
        )
        print()
        print("Options:")
        print("  --max-phase N         Limit to phases 1-N (default: all)")
        print(
            "  --max-recommendations N  Maximum recommendations to show (default: 15)"
        )
        print("  --include-unowned     Include units you don't own yet")
        sys.exit(1)

    if not SWGOH_API_KEY:
        print("Error: SWGOH_API_KEY not found in environment variables")
        print("Please create a .env file with your API key")
        sys.exit(1)

    ally_code = sys.argv[1]
    max_phase = None
    max_recommendations = 15
    include_unowned = False

    for i, arg in enumerate(sys.argv[2:], start=2):
        if arg == "--max-phase" and i + 1 < len(sys.argv):
            max_phase = sys.argv[i + 1]
        elif arg == "--max-recommendations" and i + 1 < len(sys.argv):
            max_recommendations = int(sys.argv[i + 1])
        elif arg == "--include-unowned":
            include_unowned = True

    app = RoteFarmAdvisorApp(SWGOH_API_KEY)
    app.recommend_for_player(
        ally_code,
        max_phase=max_phase,
        max_recommendations=max_recommendations,
        include_unowned=include_unowned,
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
                "Usage: python app.py rote_platoon <ally_code> [--max-phase N] [--refresh] [--output-format FORMAT] [--ignore-players PLAYER1,PLAYER2,...]"
            )
            sys.exit(1)

        if not SWGOH_API_KEY:
            print("Error: SWGOH_API_KEY not found in environment variables")
            print("Please create a .env file with your API key")
            sys.exit(1)

        ally_code = sys.argv[2]
        try:
            options = _parse_rote_platoon_args(start_index=3)
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)

        app = RotePlatoonApp(SWGOH_API_KEY)
        app.analyze_guild(
            ally_code,
            max_phase=options["max_phase"],
            refresh=options["refresh"],
            output_format=options["output_format"],
            ignored_players=options["ignored_players"],
        )
    else:
        print(f"Unknown command: {command}")
        print()
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
