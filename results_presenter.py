"""
Presentation layer for displaying kyrotech analysis results.
"""

from typing import List, Tuple, Dict


SALVAGE_DISPLAY_NAMES = {
    "172Salvage": "Mk 7 Kyrotech Shock Prod Prototype Salvage",
    "173Salvage": "Mk 9 Kyrotech Battle Computer Prototype Salvage",
    "174Salvage": "Mk 5 Kyrotech Power Cell Prototype Salvage",
}


class ResultsPresenter:
    """
    Formats and displays kyrotech analysis results.
    """

    def __init__(self, display_names: Dict[str, str] = None):
        """
        Initialize the results presenter.

        Args:
            display_names: Optional dictionary mapping salvage IDs to display names
        """
        self.display_names = display_names or SALVAGE_DISPLAY_NAMES

    def display_results(
        self, results: List[Tuple[str, int, Dict[str, int], int]]
    ) -> None:
        """
        Display the kyrotech analysis results in a formatted way.

        Args:
            results: List of tuples containing (name, gear_level, kyrotech_needs, total)
        """
        if not results:
            self._display_no_results()
            return

        self._display_header()
        self._display_characters(results)
        self._display_summary(results)

    def _display_no_results(self) -> None:
        """Display message when no characters need kyrotech."""
        print("\nNo characters need kyrotech gear!")

    def _display_header(self) -> None:
        """Display the results header."""
        print("\n" + "=" * 80)
        print("CHARACTERS WITH HIGHEST KYROTECH REQUIREMENTS (RAW SALVAGE)")
        print("=" * 80)

    def _display_characters(
        self, results: List[Tuple[str, int, Dict[str, int], int]]
    ) -> None:
        """
        Display individual character requirements.

        Args:
            results: List of character analysis results
        """
        for rank, (name, current_gear, kyrotech_needs, total) in enumerate(results, 1):
            self._display_character(rank, name, current_gear, kyrotech_needs, total)

    def _display_character(
        self,
        rank: int,
        name: str,
        current_gear: int,
        kyrotech_needs: Dict[str, int],
        total: int,
    ) -> None:
        """
        Display a single character's kyrotech requirements.

        Args:
            rank: Character's rank in the list
            name: Character name
            current_gear: Current gear level
            kyrotech_needs: Dictionary of kyrotech salvage requirements
            total: Total kyrotech salvage needed
        """
        print(f"\n#{rank}. {name} (Currently G{current_gear})")
        print(f"   Total Kyrotech Salvage: {total}")
        print("   Breakdown:")

        self._display_breakdown(kyrotech_needs)

    def _display_breakdown(self, kyrotech_needs: Dict[str, int]) -> None:
        """
        Display the breakdown of kyrotech requirements.

        Args:
            kyrotech_needs: Dictionary of salvage requirements
        """
        sorted_needs = sorted(kyrotech_needs.items(), key=lambda x: x[1], reverse=True)

        for salvage_id, count in sorted_needs:
            salvage_name = self.display_names.get(salvage_id, salvage_id)
            print(f"      - {salvage_name}: {count}")

    def _display_summary(
        self, results: List[Tuple[str, int, Dict[str, int], int]]
    ) -> None:
        """
        Display summary statistics.

        Args:
            results: List of all analysis results
        """
        print("\n" + "=" * 80)
        print(f"Total characters needing kyrotech: {len(results)}")

        total_kyrotech_needed = sum(r[3] for r in results)
        print(f"Total kyrotech salvage needed: {total_kyrotech_needed}")
        print("=" * 80)
