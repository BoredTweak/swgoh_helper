import dotenv
import os
import sys
import requests
import click
from pathlib import Path
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
from .rote_bonus_readiness import BonusReadinessAnalyzer, BonusReadinessApp
from .exceptions import AppExecutionError

dotenv.load_dotenv()

SWGOH_API_KEY = os.getenv("SWGOH_API_KEY")

VALID_ROTE_LIMITED_OUTPUT_FORMATS = {"member", "relic"}


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
        limited_buffer: int | None = None,
        limited_output_format: str = "member",
        verbose: bool = False,
        ignored_players: Optional[list[str]] = None,
    ) -> str:
        """Fetch guild information and analyze platoon coverage."""
        try:
            if output_format not in VALID_ROTE_OUTPUT_FORMATS:
                raise ValueError(
                    "Invalid --output-format. "
                    "Expected one of: all, coverage, gaps, owners, mine, limited"
                )

            if (
                output_format == "limited"
                and limited_output_format not in VALID_ROTE_LIMITED_OUTPUT_FORMATS
            ):
                raise ValueError(
                    "Invalid --output-format for rote-limited. "
                    "Expected one of: member, relic"
                )

            if limited_buffer is not None and limited_buffer < 0:
                raise ValueError("Invalid --buffer. Value must be >= 0.")

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

            display_output_format = output_format
            if output_format == "limited":
                display_output_format = f"{output_format}/{limited_output_format}"
            self.progress.update(f"Formatting output: {display_output_format}...")
            presenter = RotePresenter()
            requester_ally_code = int(ally_code.replace("-", ""))
            return presenter.format_results(
                analyzer,
                coverage_matrix,
                gap_analyzer,
                bottleneck_analyzer,
                output_format=output_format,
                limited_buffer=limited_buffer,
                limited_output_format=limited_output_format,
                verbose=verbose,
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
                max_phase=max_phase,
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
        "  rote_platoon <ally_code> [--max-phase N] [--refresh] [--output-format FORMAT] [--buffer N] [--ignore-players PLAYER1,PLAYER2,...]"
    )
    print("                            Analyze guild for RotE platoon requirements")
    print("                            --max-phase: Limit analysis to phases up to N")
    print("                                         (e.g., 4, 3b, 5)")
    print(
        "                            --output-format: all|coverage|gaps|owners|mine|limited"
    )
    print("                                             (default: gaps)")
    print(
        "                            --buffer: include units within N extra owners in Gaps"
    )
    print(
        "                            --refresh:   Force fresh data from API (ignore cache)"
    )
    print(
        "                            --ignore-players: Exclude players by name or ally code"
    )
    print()
    print(
        "  rote_limited <ally_code> [--max-phase N] [--refresh] [--output-format member|relic] [--ignore-players PLAYER1,PLAYER2,...]"
    )
    print("                            member: per-member limited-character counts")
    print(
        "                            relic: all required characters grouped by required relic and owners"
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
    print("  rote-bonus-readiness <guild_id>")
    print("                            Analyze guild readiness for RotE bonus zones")
    print()
    print("Examples:")
    print("  python app.py kyrotech 123-456-789")
    print("  python app.py rote_platoon 123-456-789")
    print("  python app.py rote_platoon 123-456-789 --max-phase 4")
    print("  python app.py rote_platoon 123-456-789 --refresh")
    print("  python app.py rote_farm 123-456-789 --max-phase 4")
    print("  python app.py rote-bonus-readiness guild_abc123")


def run_kyrotech():
    """Entry point for kyrotech CLI command."""
    _run_click_command(_kyrotech_cli, "kyrotech")


def _require_api_key() -> str:
    if not SWGOH_API_KEY:
        raise click.ClickException(
            "SWGOH_API_KEY not found in environment variables. "
            "Please create a .env file with your API key"
        )
    return SWGOH_API_KEY


def _resolve_ally_code(ally_code: str | None, ally_code_option: str | None) -> str:
    resolved = ally_code_option or ally_code
    if not resolved:
        raise click.ClickException(
            "Missing ally code. Provide <ally_code> or --ally-code <ally_code>."
        )
    return resolved


def _parse_ignored_players(values: tuple[str, ...]) -> list[str]:
    ignored_players: list[str] = []
    for value in values:
        for token in value.replace(";", ",").split(","):
            parsed = token.strip()
            if parsed:
                ignored_players.append(parsed)
    return ignored_players


def _retired_output_option(
    _ctx: click.Context, param: click.Option, value: bool
) -> bool:
    if value:
        raise click.BadOptionUsage(
            param.name or "option",
            f"{param.opts[0]} has been retired. Use --output-format instead.",
        )
    return value


def _run_click_command(command: click.Command, prog_name: str) -> None:
    try:
        command.main(args=sys.argv[1:], prog_name=prog_name, standalone_mode=False)
    except click.ClickException as e:
        e.show()
        sys.exit(e.exit_code)
    except click.exceptions.Exit as e:
        sys.exit(e.exit_code)


@click.command()
@click.argument("ally_code", required=False)
@click.option("--ally-code", "ally_code_option", type=str)
@click.option("--faction", type=str)
@click.option("--include-unowned", is_flag=True, default=False)
@click.option("--verbose", is_flag=True, default=False)
def _kyrotech_cli(
    ally_code: str | None,
    ally_code_option: str | None,
    faction: str | None,
    include_unowned: bool,
    verbose: bool,
) -> None:
    resolved_ally_code = _resolve_ally_code(ally_code, ally_code_option)
    api_key = _require_api_key()

    app = KyrotechAnalysisApp(api_key)
    try:
        if faction:
            output = app.find_all_faction_kyrotech(
                resolved_ally_code, faction, include_unowned, verbose
            )
        else:
            output = app.analyze_player(resolved_ally_code, include_unowned, verbose)
        print(output)
    except AppExecutionError as e:
        raise click.ClickException(str(e)) from e


@click.command()
@click.argument("ally_code", required=False)
@click.option("--ally-code", "ally_code_option", type=str)
@click.option("--max-phase", type=str)
@click.option("--refresh", is_flag=True, default=False)
@click.option(
    "--output-format",
    type=click.Choice(sorted(VALID_ROTE_OUTPUT_FORMATS), case_sensitive=False),
    default="gaps",
)
@click.option("--buffer", "limited_buffer", type=int)
@click.option("--verbose", is_flag=True, default=False)
@click.option("--ignore-players", "--ignored-players", "ignored_values", multiple=True)
@click.option(
    "--by-territory",
    is_flag=True,
    expose_value=False,
    callback=_retired_output_option,
)
@click.option(
    "--show-owners",
    is_flag=True,
    expose_value=False,
    callback=_retired_output_option,
)
def _rote_platoon_cli(
    ally_code: str | None,
    ally_code_option: str | None,
    max_phase: str | None,
    refresh: bool,
    output_format: str,
    limited_buffer: int | None,
    verbose: bool,
    ignored_values: tuple[str, ...],
) -> None:
    resolved_ally_code = _resolve_ally_code(ally_code, ally_code_option)
    api_key = _require_api_key()
    ignored_players = _parse_ignored_players(ignored_values)
    if ignored_players:
        print(f"Ignoring players: {', '.join(ignored_players)}")

    app = RotePlatoonApp(api_key)
    try:
        output = app.analyze_guild(
            resolved_ally_code,
            max_phase=max_phase,
            refresh=refresh,
            output_format=output_format.lower(),
            limited_buffer=limited_buffer,
            verbose=verbose,
            ignored_players=ignored_players,
        )
        print(output)
    except AppExecutionError as e:
        raise click.ClickException(str(e)) from e


@click.command()
@click.argument("ally_code", required=False)
@click.option("--ally-code", "ally_code_option", type=str)
@click.option("--max-phase", type=str)
@click.option("--refresh", is_flag=True, default=False)
@click.option(
    "--output-format",
    "limited_output_format",
    type=click.Choice(sorted(VALID_ROTE_LIMITED_OUTPUT_FORMATS), case_sensitive=False),
    default="member",
)
@click.option("--ignore-players", "--ignored-players", "ignored_values", multiple=True)
def _rote_limited_cli(
    ally_code: str | None,
    ally_code_option: str | None,
    max_phase: str | None,
    refresh: bool,
    limited_output_format: str,
    ignored_values: tuple[str, ...],
) -> None:
    resolved_ally_code = _resolve_ally_code(ally_code, ally_code_option)
    api_key = _require_api_key()
    ignored_players = _parse_ignored_players(ignored_values)
    if ignored_players:
        print(f"Ignoring players: {', '.join(ignored_players)}")

    app = RotePlatoonApp(api_key)
    try:
        output = app.analyze_guild(
            resolved_ally_code,
            max_phase=max_phase,
            refresh=refresh,
            output_format="limited",
            limited_output_format=limited_output_format.lower(),
            ignored_players=ignored_players,
        )
        print(output)
    except AppExecutionError as e:
        raise click.ClickException(str(e)) from e


@click.command()
@click.argument("ally_code", required=False)
@click.option("--ally-code", "ally_code_option", type=str)
@click.option("--max-phase", type=str)
@click.option("--max-recommendations", type=int, default=15)
@click.option("--include-unowned", is_flag=True, default=False)
def _rote_farm_cli(
    ally_code: str | None,
    ally_code_option: str | None,
    max_phase: str | None,
    max_recommendations: int,
    include_unowned: bool,
) -> None:
    resolved_ally_code = _resolve_ally_code(ally_code, ally_code_option)
    api_key = _require_api_key()

    app = RoteFarmAdvisorApp(api_key)
    try:
        output = app.recommend_for_player(
            resolved_ally_code,
            max_phase=max_phase,
            max_recommendations=max_recommendations,
            include_unowned=include_unowned,
        )
        print(output)
    except AppExecutionError as e:
        raise click.ClickException(str(e)) from e


@click.command()
@click.argument("guild_id")
def _rote_bonus_readiness_cli(guild_id: str) -> None:
    try:
        print(BonusReadinessApp().analyze(guild_id))
    except FileNotFoundError as e:
        raise click.ClickException(
            f"{e}\nRun 'rote-platoon <ally_code>' first to populate the cache."
        ) from e
    except Exception as e:
        raise click.ClickException(str(e)) from e


def run_rote_platoon():
    """Entry point for rote-platoon CLI command."""
    _run_click_command(_rote_platoon_cli, "rote-platoon")


def run_rote_limited():
    """Entry point for rote-limited CLI command."""
    _run_click_command(_rote_limited_cli, "rote-limited")


def run_rote_farm():
    """Entry point for rote-farm CLI command."""
    _run_click_command(_rote_farm_cli, "rote-farm")


def run_rote_bonus_readiness():
    """Entry point for rote-bonus-readiness CLI command."""
    _run_click_command(_rote_bonus_readiness_cli, "rote-bonus-readiness")


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
        "rote_bonus_readiness": run_rote_bonus_readiness,
        "rote-bonus-readiness": run_rote_bonus_readiness,
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
