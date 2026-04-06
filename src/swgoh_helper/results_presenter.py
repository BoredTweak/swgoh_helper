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

    def format_results(
        self,
        results: List[Tuple[str, int, Dict[str, int], int]],
        verbose: bool = False,
        total_owned_count: int | None = None,
        total_unowned_count: int = 0,
        total_owned_salvage: int | None = None,
        total_unowned_salvage: int = 0,
    ) -> str:
        """Format owned-only kyrotech results as plain text."""
        if not results:
            return "\nNo characters need kyrotech gear!"

        lines = self._header_lines()
        lines.extend(self._character_lines(self._display_slice(results, verbose)))
        lines.extend(
            self._summary_lines(
                results,
                total_owned_count=total_owned_count,
                total_unowned_count=total_unowned_count,
                total_owned_salvage=total_owned_salvage,
                total_unowned_salvage=total_unowned_salvage,
            )
        )
        return "\n".join(lines)

    def display_results(
        self, results: List[Tuple[str, int, Dict[str, int], int]]
    ) -> None:
        """Display the kyrotech analysis results in a formatted way."""
        print(self.format_results(results))

    def _header_lines(self) -> list[str]:
        return [
            "",
            "=" * 80,
            "CHARACTERS WITH HIGHEST KYROTECH REQUIREMENTS (RAW SALVAGE)",
            "=" * 80,
        ]

    def _character_lines(
        self, results: List[Tuple[str, int, Dict[str, int], int]]
    ) -> list[str]:
        lines: list[str] = []
        for rank, (name, current_gear, kyrotech_needs, total) in enumerate(results, 1):
            lines.extend(
                self._character_block(rank, name, current_gear, kyrotech_needs, total)
            )
        return lines

    def _character_block(
        self,
        rank: int,
        name: str,
        current_gear: int,
        kyrotech_needs: Dict[str, int],
        total: int,
    ) -> list[str]:
        lines = [
            f"\n#{rank}. {name} (Currently G{current_gear})",
            f"   Total Kyrotech Salvage: {total}",
            "   Breakdown:",
        ]
        lines.extend(self._breakdown_lines(kyrotech_needs))
        return lines

    def _breakdown_lines(self, kyrotech_needs: Dict[str, int]) -> list[str]:
        lines: list[str] = []
        sorted_needs = sorted(kyrotech_needs.items(), key=lambda x: x[1], reverse=True)

        for salvage_id, count in sorted_needs:
            salvage_name = self.display_names.get(salvage_id, salvage_id)
            lines.append(f"      - {salvage_name}: {count}")
        return lines

    def _summary_lines(
        self,
        results: List[Tuple[str, int, Dict[str, int], int]],
        total_owned_count: int | None = None,
        total_unowned_count: int = 0,
        total_owned_salvage: int | None = None,
        total_unowned_salvage: int = 0,
    ) -> list[str]:
        owned_count = (
            total_owned_count if total_owned_count is not None else len(results)
        )
        unowned_count = total_unowned_count
        owned_total = (
            total_owned_salvage
            if total_owned_salvage is not None
            else sum(r[3] for r in results)
        )
        unowned_total = total_unowned_salvage
        overall_total = owned_total + unowned_total

        lines = ["\n" + "=" * 80]
        lines.append(f"Total owned characters needing kyros: {owned_count}")
        lines.append(f"Total unowned characters needing kyros: {unowned_count}")
        lines.append(
            f"Total kyrotech salvage needed for owned characters: {owned_total}"
        )
        lines.append(
            f"Total kyrotech salvage needed for unowned characters: {unowned_total}"
        )
        lines.append(f"Total kyrotech salvage needed overall: {overall_total}")
        lines.append("=" * 80)
        return lines

    def format_all_results(
        self, results: List[CharacterKyrotechResult], verbose: bool = False
    ) -> str:
        """Format kyrotech analysis including owned/unowned separation."""
        if not results:
            return "\nNo characters need kyrotech gear!"

        displayed = self._display_slice(results, verbose)
        shown_ids = {r.base_id for r in displayed}

        owned = [r for r in results if r.is_owned]
        unowned = [r for r in results if not r.is_owned]
        displayed_owned = [r for r in owned if r.base_id in shown_ids]
        displayed_unowned = [r for r in unowned if r.base_id in shown_ids]

        lines = self._header_lines()
        if displayed_owned:
            lines.append("\n--- OWNED CHARACTERS ---")
            for rank, result in enumerate(displayed_owned, 1):
                lines.extend(self._character_result_lines(rank, result))

        if displayed_unowned:
            lines.append("\n--- NOT OWNED (Full G1-G13 Requirements) ---")
            for rank, result in enumerate(displayed_unowned, 1):
                lines.extend(
                    self._character_result_lines(rank, result, show_gear=False)
                )

        lines.extend(self._all_summary_lines(results, owned, unowned))
        return "\n".join(lines)

    def display_all_results(self, results: List[CharacterKyrotechResult]) -> None:
        """Display kyrotech analysis results including owned/unowned separation."""
        print(self.format_all_results(results))

    def _character_result_lines(
        self, rank: int, result: CharacterKyrotechResult, show_gear: bool = True
    ) -> list[str]:
        lines: list[str] = []
        if show_gear:
            lines.append(f"\n#{rank}. {result.name} (Currently G{result.gear_level})")
        else:
            lines.append(f"\n#{rank}. {result.name}")
        lines.append(f"   Total Kyrotech Salvage: {result.total_kyrotech}")
        lines.append("   Breakdown:")
        lines.extend(self._breakdown_lines(result.kyrotech_needs))
        return lines

    def _all_summary_lines(
        self,
        results: List[CharacterKyrotechResult],
        owned: List[CharacterKyrotechResult],
        unowned: List[CharacterKyrotechResult],
    ) -> list[str]:
        lines = ["\n" + "=" * 80]
        lines.append(f"Total owned characters needing kyros: {len(owned)}")
        lines.append(f"Total unowned characters needing kyros: {len(unowned)}")
        owned_total = sum(r.total_kyrotech for r in owned)
        unowned_total = sum(r.total_kyrotech for r in unowned)
        overall_total = sum(r.total_kyrotech for r in results)
        lines.append(
            f"Total kyrotech salvage needed for owned characters: {owned_total}"
        )
        lines.append(
            f"Total kyrotech salvage needed for unowned characters: {unowned_total}"
        )
        lines.append(f"Total kyrotech salvage needed overall: {overall_total}")
        lines.append("=" * 80)
        return lines

    def _display_slice(self, results, verbose: bool):
        if verbose:
            return results
        return results[:10]
