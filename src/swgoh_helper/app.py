import dotenv
import os
import sys
import traceback
import requests
from typing import Optional

from .data_access import SwgohDataService
from .progress import ProgressNotifier
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
)
from .models import VALID_ROTE_OUTPUT_FORMATS
from .rote_gap_analyzer import GapAnalyzer
from .rote_bottleneck_analyzer import BottleneckAnalyzer
from .rote_presenter import RotePresenter
from .rote_bonus_readiness import BonusReadinessAnalyzer
from .exceptions import AppExecutionError


dotenv.load_dotenv()

SWGOH_API_KEY = os.getenv("SWGOH_API_KEY")


class KyrotechAnalysisApp:
    """Main application orchestrator for kyrotech analysis."""

    def __init__(self, api_key: str, progress: Optional[ProgressNotifier] = None):
        self.progress = progress or ProgressNotifier()
        self.service = SwgohDataService(api_key, progress=self.progress)
        self.presenter = ResultsPresenter()

    def analyze_player(
        self,
        ally_code: str,
        include_unowned: bool = False,
        verbose: bool = False,
    ) -> str:
        """Analyze a player's roster for kyrotech requirements.

        Args:
            ally_code: Player's ally code
            include_unowned: Whether to include characters the player doesn't own
            verbose: Whether to show all characters instead of top 10
        """
        try:
            self.progress.update(
                f"Starting kyrotech analysis for ally code: {ally_code}..."
            )
            units_data, gear_data, player_data = self._fetch_game_data(ally_code)

            self.progress.update("Preparing kyrotech analyzers...")
            kyrotech_analyzer = KyrotechAnalyzer(gear_data)
            roster_analyzer = RosterAnalyzer(kyrotech_analyzer)

            units_by_id = roster_analyzer.build_units_lookup(units_data.data)
            self.progress.update("Analyzing all characters for totals...")
            all_results = roster_analyzer.analyze_all_characters(
                player_data.units, units_by_id, exclude_era_units=True
            )

            owned_results = [r for r in all_results if r.is_owned]
            unowned_results = [r for r in all_results if not r.is_owned]

            if include_unowned:
                self.progress.update("Formatting kyrotech analysis results...")
                return self.presenter.format_all_results(all_results, verbose=verbose)
            else:
                owned_only = [
                    (
                        result.name,
                        result.gear_level,
                        result.kyrotech_needs,
                        result.total_kyrotech,
                    )
                    for result in owned_results
                ]
                self.progress.update("Formatting kyrotech analysis results...")
                return self.presenter.format_results(
                    owned_only,
                    verbose=verbose,
                    total_owned_count=len(owned_results),
                    total_unowned_count=len(unowned_results),
                    total_owned_salvage=sum(r.total_kyrotech for r in owned_results),
                    total_unowned_salvage=sum(
                        r.total_kyrotech for r in unowned_results
                    ),
                )

        except requests.exceptions.RequestException as e:
            self._handle_request_error(e)
        except Exception as e:
            self._handle_general_error(e)

    def find_all_faction_kyrotech(
        self,
        ally_code: str,
        faction: str,
        include_unowned: bool = True,
        verbose: bool = False,
    ) -> str:
        """Find all characters with kyrotech needs for a faction, including unowned.

        Args:
            ally_code: Player's ally code
            faction: The faction to filter by (e.g., "Empire", "Rebel", "Sith")
            include_unowned: Whether to include characters the player doesn't own
            verbose: Whether to show all characters instead of top 10
        """
        try:
            self.progress.update(
                f"Starting full faction kyrotech scan for {faction} ({ally_code})..."
            )
            units_data, gear_data, player_data = self._fetch_game_data(ally_code)

            self.progress.update("Preparing faction kyrotech analyzer...")
            kyrotech_analyzer = KyrotechAnalyzer(gear_data)
            roster_analyzer = RosterAnalyzer(kyrotech_analyzer)

            units_by_id = roster_analyzer.build_units_lookup(units_data.data)
            self.progress.update(
                f"Analyzing {faction} characters (include_unowned={include_unowned})..."
            )
            results = roster_analyzer.analyze_faction_all_characters(
                player_data.units,
                units_by_id,
                faction,
                include_owned=True,
                include_unowned=True,
                exclude_era_units=True,
            )

            if results:
                self.progress.update("Formatting faction kyrotech report...")
                return self._format_all_faction_kyrotech_results(
                    faction,
                    results,
                    verbose=verbose,
                    show_unowned=include_unowned,
                )
            else:
                self.progress.update("No faction kyrotech needs found.")
                return f"\nNo {faction} characters found that need kyrotech."

        except requests.exceptions.RequestException as e:
            self._handle_request_error(e)
        except Exception as e:
            self._handle_general_error(e)

    def _fetch_game_data(self, ally_code: str):
        self.progress.update("Loading game units data...")
        units_data = self.service.get_all_units()

        self.progress.update("Loading gear recipe data...")
        gear_data = self.service.get_all_gear()

        self.progress.update(f"Fetching player data for ally code: {ally_code}...")
        player_data = self.service.get_player(ally_code)

        return units_data, gear_data, player_data

    def _handle_request_error(
        self, error: requests.exceptions.RequestException
    ) -> None:
        """Handle API request errors."""
        raise AppExecutionError(f"Error fetching data: {error}") from error

    def _handle_general_error(self, error: Exception) -> None:
        """Handle general application errors."""
        raise AppExecutionError(f"Error: {error}") from error

    def _format_kyrotech_needs(self, kyrotech_needs: dict[str, int]) -> list[str]:
        lines: list[str] = []
        for salvage_id, count in kyrotech_needs.items():
            salvage_name = KYROTECH_SALVAGE_IDS.get(salvage_id, salvage_id)
            lines.append(f"  - {salvage_name}: {count}")
        return lines

    def _format_all_faction_kyrotech_results(
        self,
        faction: str,
        results,
        verbose: bool = False,
        show_unowned: bool = True,
    ) -> str:
        owned = [r for r in results if r.is_owned]
        unowned = [r for r in results if not r.is_owned]

        display_source = results if show_unowned else owned
        displayed = display_source if verbose else display_source[:10]
        shown_ids = {r.base_id for r in displayed}
        displayed_owned = [r for r in owned if r.base_id in shown_ids]
        displayed_unowned = (
            [r for r in unowned if r.base_id in shown_ids] if show_unowned else []
        )

        lines = [
            "",
            f"{'='*60}",
            f"{faction} Characters by Kyrotech Needs",
            f"{'='*60}",
        ]

        if displayed_owned:
            lines.append("\n--- OWNED CHARACTERS ---")
            for result in displayed_owned:
                lines.append(
                    f"{result.name} (G{result.gear_level}): {result.total_kyrotech} total"
                )
                lines.extend(self._format_kyrotech_needs(result.kyrotech_needs))

        if displayed_unowned:
            lines.append("\n--- NOT OWNED (Full G1-G13) ---")
            for result in displayed_unowned:
                lines.append(f"{result.name}: {result.total_kyrotech} total")
                lines.extend(self._format_kyrotech_needs(result.kyrotech_needs))

        owned_total = sum(r.total_kyrotech for r in owned)
        unowned_total = sum(r.total_kyrotech for r in unowned)
        overall_total = owned_total + unowned_total

        lines.append(f"\n{'='*60}")
        lines.append(f"Total owned characters needing kyros: {len(owned)}")
        lines.append(f"Total unowned characters needing kyros: {len(unowned)}")
        lines.append(
            f"Total kyrotech salvage needed for owned characters: {owned_total}"
        )
        lines.append(
            f"Total kyrotech salvage needed for unowned characters: {unowned_total}"
        )
        lines.append(f"Total kyrotech salvage needed overall: {overall_total}")
        lines.append(f"{'='*60}")

        return "\n".join(lines).rstrip()


class RotePlatoonApp:
    """Application for analyzing Rise of the Empire Territory Battle platoon requirements."""

    def __init__(self, api_key: str, progress: Optional[ProgressNotifier] = None):
        self.progress = progress or ProgressNotifier()
        self.service = SwgohDataService(api_key, progress=self.progress)

    def analyze_guild(
        self,
        ally_code: str,
        max_phase: Optional[str] = None,
        refresh: bool = False,
        output_format: str = "gaps",
        ignored_players: Optional[list[str]] = None,
    ) -> str:
        """Fetch guild information and analyze platoon coverage."""
        try:
            if output_format not in VALID_ROTE_OUTPUT_FORMATS:
                raise ValueError(
                    "Invalid --output-format. "
                    "Expected one of: all, coverage, gaps, owners, mine"
                )

            guild_id, guild_name, member_ally_codes = (
                self.service.get_guild_from_ally_code(ally_code)
            )

            self.progress.update(f"Guild: {guild_name}")
            self.progress.update(f"Guild ID: {guild_id}")
            self.progress.update(f"Members: {len(member_ally_codes)}")

            if refresh:
                self.progress.update(
                    "Invalidating player caches (--refresh specified)..."
                )
                self.service.invalidate_player_caches(member_ally_codes)

            self.progress.update("Loading unit metadata...")
            units_data = self.service.get_all_units()

            rosters = self.service.get_guild_rosters(
                member_ally_codes, delay_seconds=1.0
            )

            self.progress.update(
                f"Successfully loaded data for {len(rosters)} guild members."
            )

            self.progress.update("Building coverage matrix...")
            coverage_matrix = build_coverage_matrix(
                rosters=rosters,
                units_data=units_data,
                guild_name=guild_name,
                guild_id=guild_id,
                ignored_players=ignored_players,
            )

            self.progress.update(
                f"Analyzed {len(coverage_matrix.units)} unique units across roster."
            )

            self.progress.update("Loading ROTE platoon requirements...")
            requirements = load_requirements()

            if max_phase:
                requirements = filter_requirements_by_phase(requirements, max_phase)
                self.progress.update(
                    f"Filtered to phase {max_phase}: {len(requirements.requirements)} requirements."
                )
            else:
                self.progress.update(
                    f"Loaded {len(requirements.requirements)} platoon requirements."
                )

            self.progress.update("Analyzing platoon coverage...")
            analyzer = CoverageAnalyzer(coverage_matrix, requirements)

            self.progress.update("Analyzing gaps and bottlenecks...")
            gap_analyzer = GapAnalyzer(coverage_matrix, requirements)
            bottleneck_analyzer = BottleneckAnalyzer(coverage_matrix, requirements)

            self.progress.update("Checking bonus zone unlock status...")
            bonus_analyzer = BonusReadinessAnalyzer()
            bonus_readiness = {
                "Zeffo": bonus_analyzer.analyze_zeffo_readiness(rosters),
                "Mandalore": bonus_analyzer.analyze_mandalore_readiness(rosters),
            }

            self.progress.update(f"Formatting output: {output_format}...")
            presenter = RotePresenter()
            requester_ally_code = int(ally_code.replace("-", ""))
            return presenter.format_results(
                analyzer,
                coverage_matrix,
                gap_analyzer,
                bottleneck_analyzer,
                output_format=output_format,
                requester_ally_code=requester_ally_code,
                bonus_readiness=bonus_readiness,
            )

        except ValueError as e:
            raise AppExecutionError(f"Error: {e}") from e
        except requests.exceptions.RequestException as e:
            raise AppExecutionError(f"Error fetching data: {e}") from e
        except Exception as e:
            raise AppExecutionError(f"Error: {e}") from e


class RoteFarmAdvisorApp:
    """Application for generating personalized ROTE farming recommendations."""

    def __init__(self, api_key: str, progress: Optional[ProgressNotifier] = None):
        self.progress = progress or ProgressNotifier()
        self.service = SwgohDataService(api_key, progress=self.progress)

    def recommend_for_player(
        self,
        ally_code: str,
        max_phase: Optional[str] = None,
        max_recommendations: int = 15,
        include_unowned: bool = False,
    ) -> str:
        """Generate personalized farm recommendations for a player."""
        try:
            # Get player's guild info
            guild_id, guild_name, member_ally_codes = (
                self.service.get_guild_from_ally_code(ally_code)
            )

            self.progress.update(f"Guild: {guild_name}")
            self.progress.update(f"Guild ID: {guild_id}")
            self.progress.update(f"Members: {len(member_ally_codes)}")

            self.progress.update("Loading unit metadata...")
            units_data = self.service.get_all_units()

            self.progress.update("Loading guild rosters...")
            rosters = self.service.get_guild_rosters(
                member_ally_codes, delay_seconds=1.0
            )
            self.progress.update(f"Loaded data for {len(rosters)} guild members.")

            # Find the target player's roster
            self.progress.update("Locating target player roster in guild data...")
            target_roster = None
            ally_code_int = int(ally_code.replace("-", ""))
            for roster in rosters:
                if roster.data.ally_code == ally_code_int:
                    target_roster = roster
                    break

            if target_roster is None:
                raise AppExecutionError(
                    f"Error: Could not find player with ally code {ally_code} in guild."
                )

            self.progress.update(
                f"Analyzing recommendations for: {target_roster.data.name}"
            )

            self.progress.update("Building coverage matrix...")
            coverage_matrix = build_coverage_matrix(
                rosters=rosters,
                units_data=units_data,
                guild_name=guild_name,
                guild_id=guild_id,
            )

            self.progress.update("Loading ROTE platoon requirements...")
            requirements = load_requirements()

            if max_phase:
                requirements = filter_requirements_by_phase(requirements, max_phase)
                self.progress.update(
                    f"Filtered to phase {max_phase}: {len(requirements.requirements)} requirements."
                )

            self.progress.update("Generating personalized recommendations...")
            from .rote_farm_advisor import FarmAdvisor

            self.progress.update("Building advisor model...")
            advisor = FarmAdvisor(coverage_matrix, requirements)
            report = advisor.get_player_recommendations(
                target_roster,
                max_recommendations=max_recommendations,
                include_unowned=include_unowned,
            )
            report.max_phase = max_phase

            self.progress.update("Formatting farm recommendation report...")
            presenter = RotePresenter()
            return presenter.format_personal_farm_report(report)

        except ValueError as e:
            raise AppExecutionError(f"Error: {e}") from e
        except requests.exceptions.RequestException as e:
            raise AppExecutionError(f"Error fetching data: {e}") from e
        except Exception as e:
            raise AppExecutionError(f"Error: {e}") from e


def print_usage():
    """Print usage information."""
    print("Usage: python app.py <command> [arguments]")
    print()
    print("Commands:")
    print(
        "  kyrotech <ally_code>      Analyze a player's roster for kyrotech requirements"
    )
    print(
        "                            --verbose: Show all matching characters (default top 10)"
    )
    print(
        "  rote_platoon <ally_code> [--max-phase N] [--refresh] [--output-format FORMAT] [--ignore-players PLAYER1,PLAYER2,...]"
    )
    print("                            Analyze guild for RotE platoon requirements")
    print("                            --max-phase: Limit analysis to phases up to N")
    print("                                         (e.g., 4, 3b, 5)")
    print(
        "                            --output-format: all|coverage|gaps|owners|mine|limited"
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
        "  rote_limited <ally_code> [--max-phase N] [--refresh] [--ignore-players PLAYER1,PLAYER2,...]"
    )
    print(
        "                            List members with count of limited-availability character requirements"
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
            "Usage: kyrotech <ally_code> [--faction FACTION_NAME] [--include-unowned] [--verbose]"
        )
        print("Example: kyrotech 123-456-789")
        print("         kyrotech 123-456-789 --faction Empire")
        print("         kyrotech 123-456-789 --include-unowned")
        print("         kyrotech 123-456-789 --verbose")
        sys.exit(1)

    if not SWGOH_API_KEY:
        print("Error: SWGOH_API_KEY not found in environment variables")
        print("Please create a .env file with your API key")
        sys.exit(1)

    ally_code = sys.argv[1]
    faction = None
    include_unowned = "--include-unowned" in sys.argv
    verbose = "--verbose" in sys.argv

    for i, arg in enumerate(sys.argv[2:], start=2):
        if arg == "--faction" and i + 1 < len(sys.argv):
            faction = sys.argv[i + 1]
            break

    app = KyrotechAnalysisApp(SWGOH_API_KEY)
    try:
        if faction:
            output = app.find_all_faction_kyrotech(
                ally_code, faction, include_unowned, verbose
            )
        else:
            output = app.analyze_player(ally_code, include_unowned, verbose)
        print(output)
    except AppExecutionError as e:
        print(str(e))
        traceback.print_exc()
        sys.exit(1)


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
    try:
        output = app.analyze_guild(
            ally_code,
            max_phase=options["max_phase"],
            refresh=options["refresh"],
            output_format=options["output_format"],
            ignored_players=options["ignored_players"],
        )
        print(output)
    except AppExecutionError as e:
        print(str(e))
        traceback.print_exc()
        sys.exit(1)


def run_rote_limited():
    """Entry point for rote-limited CLI command."""
    if len(sys.argv) < 2:
        print(
            "Usage: rote-limited <ally_code> [--max-phase N] [--refresh] [--ignore-players PLAYER1,PLAYER2,...]"
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
    try:
        output = app.analyze_guild(
            ally_code,
            max_phase=options["max_phase"],
            refresh=options["refresh"],
            output_format="limited",
            ignored_players=options["ignored_players"],
        )
        print(output)
    except AppExecutionError as e:
        print(str(e))
        traceback.print_exc()
        sys.exit(1)


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
    try:
        output = app.recommend_for_player(
            ally_code,
            max_phase=max_phase,
            max_recommendations=max_recommendations,
            include_unowned=include_unowned,
        )
        print(output)
    except AppExecutionError as e:
        print(str(e))
        traceback.print_exc()
        sys.exit(1)


def main():
    """Main entry point for the application."""
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    command = sys.argv[1].lower()

    handlers = {
        "kyrotech": run_kyrotech,
        "rote_platoon": run_rote_platoon,
        "rote-platoon": run_rote_platoon,
        "rote_limited": run_rote_limited,
        "rote-limited": run_rote_limited,
        "rote_farm": run_rote_farm,
        "rote-farm": run_rote_farm,
    }

    handler = handlers.get(command)
    if handler is None:
        print(f"Unknown command: {command}")
        print()
        print_usage()
        sys.exit(1)

    # Preserve support for `python app.py <command> ...` by stripping the command
    # token so dedicated entry points can parse argv consistently.
    sys.argv = [sys.argv[0], *sys.argv[2:]]
    handler()


if __name__ == "__main__":
    main()
