import dotenv
import os
import sys
import requests

from swgoh_gg_client import SwgohGGClient
from kyrotech_analyzer import KyrotechAnalyzer, RosterAnalyzer
from results_presenter import ResultsPresenter


dotenv.load_dotenv()

SWGOH_API_KEY = os.getenv("SWGOH_API_KEY")


class KyrotechAnalysisApp:
    """
    Main application orchestrator for kyrotech analysis.

    Coordinates between data fetching, analysis, and presentation layers
    while keeping each responsibility separate.
    """

    def __init__(self, api_key: str):
        """
        Initialize the application with required dependencies.

        Args:
            api_key: SWGOH.GG API key
        """
        self.client = SwgohGGClient(api_key)
        self.presenter = ResultsPresenter()

    def analyze_player(self, ally_code: str) -> None:
        """
        Analyze a player's roster for kyrotech requirements.

        Args:
            ally_code: Player's ally code
        """
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
        """
        Fetch all required game data.

        Extracted method to reduce complexity in analyze_player.

        Args:
            ally_code: Player's ally code

        Returns:
            Tuple of (units_data, gear_data, player_data)
        """
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


def main():
    """Main entry point for the application."""
    if len(sys.argv) < 2:
        print("Usage: python app.py <ally_code>")
        print("Example: python app.py 123-456-789")
        sys.exit(1)

    if not SWGOH_API_KEY:
        print("Error: SWGOH_API_KEY not found in environment variables")
        print("Please create a .env file with your API key")
        sys.exit(1)

    ally_code = sys.argv[1]
    app = KyrotechAnalysisApp(SWGOH_API_KEY)
    app.analyze_player(ally_code)


if __name__ == "__main__":
    main()
