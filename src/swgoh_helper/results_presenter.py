"""
Presentation layer for displaying kyrotech analysis results.
"""

from typing import List, Tuple, Dict

from .constants import KYROTECH_SALVAGE_IDS
from .models import CharacterKyrotechResult


class ResultsPresenter:
    """
    Formats and displays kyrotech analysis results.
    """

    def __init__(self, display_names: Dict[str, str] = None):
        self.display_names = display_names or KYROTECH_SALVAGE_IDS

    def display_results(
        self, results: List[Tuple[str, int, Dict[str, int], int]]
    ) -> None:
        """Display the kyrotech analysis results in a formatted way."""
        if not results:
            self._display_no_results()
            return

        self._display_header()
        self._display_characters(results)
        self._display_summary(results)

    def _display_no_results(self) -> None:
        print("\nNo characters need kyrotech gear!")

    def _display_header(self) -> None:
        print("\n" + "=" * 80)
        print("CHARACTERS WITH HIGHEST KYROTECH REQUIREMENTS (RAW SALVAGE)")
        print("=" * 80)

    def _display_characters(
        self, results: List[Tuple[str, int, Dict[str, int], int]]
    ) -> None:
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
        print(f"\n#{rank}. {name} (Currently G{current_gear})")
        print(f"   Total Kyrotech Salvage: {total}")
        print("   Breakdown:")

        self._display_breakdown(kyrotech_needs)

    def _display_breakdown(self, kyrotech_needs: Dict[str, int]) -> None:
        sorted_needs = sorted(kyrotech_needs.items(), key=lambda x: x[1], reverse=True)

        for salvage_id, count in sorted_needs:
            salvage_name = self.display_names.get(salvage_id, salvage_id)
            print(f"      - {salvage_name}: {count}")

    def _display_summary(
        self, results: List[Tuple[str, int, Dict[str, int], int]]
    ) -> None:
        print("\n" + "=" * 80)
        print(f"Total characters needing kyrotech: {len(results)}")

        total_kyrotech_needed = sum(r[3] for r in results)
        print(f"Total kyrotech salvage needed: {total_kyrotech_needed}")
        print("=" * 80)

    def display_all_results(self, results: List[CharacterKyrotechResult]) -> None:
        """Display kyrotech analysis results including owned/unowned separation."""
        if not results:
            self._display_no_results()
            return

        owned = [r for r in results if r.is_owned]
        unowned = [r for r in results if not r.is_owned]

        self._display_header()

        if owned:
            print("\n--- OWNED CHARACTERS ---")
            for rank, result in enumerate(owned, 1):
                self._display_character_result(rank, result)

        if unowned:
            print("\n--- NOT OWNED (Full G1-G13 Requirements) ---")
            for rank, result in enumerate(unowned, 1):
                self._display_character_result(rank, result, show_gear=False)

        self._display_all_summary(results, owned, unowned)

    def _display_character_result(
        self, rank: int, result: CharacterKyrotechResult, show_gear: bool = True
    ) -> None:
        if show_gear:
            print(f"\n#{rank}. {result.name} (Currently G{result.gear_level})")
        else:
            print(f"\n#{rank}. {result.name}")
        print(f"   Total Kyrotech Salvage: {result.total_kyrotech}")
        print("   Breakdown:")
        self._display_breakdown(result.kyrotech_needs)

    def _display_all_summary(
        self,
        results: List[CharacterKyrotechResult],
        owned: List[CharacterKyrotechResult],
        unowned: List[CharacterKyrotechResult],
    ) -> None:
        print("\n" + "=" * 80)
        print(
            f"Total characters: {len(results)} ({len(owned)} owned, {len(unowned)} not owned)"
        )

        owned_total = sum(r.total_kyrotech for r in owned)
        unowned_total = sum(r.total_kyrotech for r in unowned)
        print(f"Kyrotech needed for owned: {owned_total}")
        if unowned:
            print(f"Kyrotech needed for unowned: {unowned_total}")
        print("=" * 80)
