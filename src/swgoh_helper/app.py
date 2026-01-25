import dotenv
import os
import sys
import requests
from typing import Optional

from .swgoh_gg_client import SwgohGGClient
from .kyrotech_analyzer import KyrotechAnalyzer, RosterAnalyzer
from .results_presenter import ResultsPresenter
from .rote_coverage import (
    build_coverage_matrix,
    load_requirements,
    CoverageAnalyzer,
)
from .rote_models import RotePath


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
        import traceback

        traceback.print_exc()
        sys.exit(1)


class RotePlatoonApp:
    """Application for analyzing Rise of the Empire Territory Battle platoon requirements."""

    def __init__(self, api_key: str):
        self.client = SwgohGGClient(api_key)

    def analyze_guild(self, ally_code: str, max_phase: Optional[str] = None) -> None:
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

            from .rote_gap_analyzer import GapAnalyzer
            from .rote_bottleneck_analyzer import BottleneckAnalyzer

            gap_analyzer = GapAnalyzer(coverage_matrix, requirements)
            bottleneck_analyzer = BottleneckAnalyzer(coverage_matrix, requirements)

            self._display_rote_results(
                analyzer, coverage_matrix, gap_analyzer, bottleneck_analyzer
            )

        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"Error: {e}")
            import traceback

            traceback.print_exc()
            sys.exit(1)

    def _filter_requirements_by_phase(self, requirements, max_phase: str):
        """Filter requirements to only include territories up to max_phase."""
        from .rote_coverage import RoteConfig
        from .rote_models import SimpleRoteRequirements

        phase_order = ["1", "2", "3", "3b", "4", "4b", "5", "5b", "6"]

        try:
            max_phase_idx = phase_order.index(max_phase)
        except ValueError:
            print(f"Warning: Unknown phase '{max_phase}', using all phases.")
            return requirements

        included_phases = set(phase_order[: max_phase_idx + 1])

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
        self, analyzer: CoverageAnalyzer, matrix, gap_analyzer, bottleneck_analyzer
    ) -> None:
        """Display complete ROTE platoon analysis results."""
        from .rote_coverage import RoteConfig
        from collections import defaultdict

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
                    owners = (
                        ", ".join(gap.player_names) if gap.player_names else "NO ONE"
                    )
                    print(
                        f"  - {gap.unit_name} R{gap.min_relic}: "
                        f"{gap.players_available}/{gap.slots_needed} players ({owners})"
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
                print(f"\nOnly 1 player has ({len(sole_owner)} units):")
                for unit in sole_owner:
                    territories = ", ".join(unit.territories_needed[:2])
                    if len(unit.territories_needed) > 2:
                        territories += f" +{len(unit.territories_needed) - 2}"
                    print(
                        f"   - {unit.unit_name} R{unit.min_relic} → {unit.owner_names[0]} "
                        f"[{territories}]"
                    )

            if two_owners:
                print(f"\nOnly 2 players have ({len(two_owners)} units):")
                for unit in two_owners:
                    owners = ", ".join(unit.owner_names[:2])
                    territories = ", ".join(unit.territories_needed[:2])
                    if len(unit.territories_needed) > 2:
                        territories += f" +{len(unit.territories_needed) - 2}"
                    print(
                        f"   - {unit.unit_name} R{unit.min_relic} → {owners} "
                        f"[{territories}]"
                    )

            if three_owners:
                print(f"\nOnly 3 players have ({len(three_owners)} units):")
                for unit in three_owners:
                    owners = ", ".join(unit.owner_names[:3])
                    territories = ", ".join(unit.territories_needed[:2])
                    if len(unit.territories_needed) > 2:
                        territories += f" +{len(unit.territories_needed) - 2}"
                    print(
                        f"   - {unit.unit_name} R{unit.min_relic} → {owners} "
                        f"[{territories}]"
                    )

        print()


def print_usage():
    """Print usage information."""
    print("Usage: python app.py <command> [arguments]")
    print()
    print("Commands:")
    print(
        "  kyrotech <ally_code>      Analyze a player's roster for kyrotech requirements"
    )
    print("  rote_platoon <ally_code> [--max-phase N]")
    print("                            Analyze guild for RotE platoon requirements")
    print("                            --max-phase: Limit analysis to phases up to N")
    print("                                         (e.g., 4, 3b, 5)")
    print()
    print("Examples:")
    print("  python app.py kyrotech 123-456-789")
    print("  python app.py rote_platoon 123-456-789")
    print("  python app.py rote_platoon 123-456-789 --max-phase 4")


def run_kyrotech():
    """Entry point for kyrotech CLI command."""
    if len(sys.argv) < 2:
        print("Usage: kyrotech <ally_code>")
        sys.exit(1)

    if not SWGOH_API_KEY:
        print("Error: SWGOH_API_KEY not found in environment variables")
        print("Please create a .env file with your API key")
        sys.exit(1)

    ally_code = sys.argv[1]
    app = KyrotechAnalysisApp(SWGOH_API_KEY)
    app.analyze_player(ally_code)


def run_rote_platoon():
    """Entry point for rote-platoon CLI command."""
    if len(sys.argv) < 2:
        print("Usage: rote-platoon <ally_code> [--max-phase N]")
        sys.exit(1)

    if not SWGOH_API_KEY:
        print("Error: SWGOH_API_KEY not found in environment variables")
        print("Please create a .env file with your API key")
        sys.exit(1)

    ally_code = sys.argv[1]
    max_phase = None
    for i, arg in enumerate(sys.argv[2:], start=2):
        if arg == "--max-phase" and i + 1 < len(sys.argv):
            max_phase = sys.argv[i + 1]
            break

    app = RotePlatoonApp(SWGOH_API_KEY)
    app.analyze_guild(ally_code, max_phase=max_phase)


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
            print("Usage: python app.py rote_platoon <ally_code> [--max-phase N]")
            sys.exit(1)

        if not SWGOH_API_KEY:
            print("Error: SWGOH_API_KEY not found in environment variables")
            print("Please create a .env file with your API key")
            sys.exit(1)

        ally_code = sys.argv[2]
        max_phase = None
        for i, arg in enumerate(sys.argv[3:], start=3):
            if arg == "--max-phase" and i + 1 < len(sys.argv):
                max_phase = sys.argv[i + 1]
                break

        app = RotePlatoonApp(SWGOH_API_KEY)
        app.analyze_guild(ally_code, max_phase=max_phase)
    else:
        print(f"Unknown command: {command}")
        print()
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
