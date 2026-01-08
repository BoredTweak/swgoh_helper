"""
Service layer for analyzing kyrotech gear requirements in SWGOH.
"""

from typing import Dict, List, Tuple
from collections import defaultdict

from models import GearTier, GearPiece, Unit, PlayerUnit


# Constants for kyrotech salvage IDs
KYROTECH_SALVAGE_IDS = {
    "172Salvage": "Mk 7 Kyrotech Shock Prod Prototype Salvage",
    "173Salvage": "Mk 9 Kyrotech Battle Computer Prototype Salvage",
    "174Salvage": "Mk 5 Kyrotech Power Cell Prototype Salvage",
}

MAX_GEAR_TIER = 13


class KyrotechAnalyzer:
    """
    Analyzes gear requirements to calculate kyrotech needs.
    """

    def __init__(self, gear_lookup: Dict[str, GearPiece]):
        """
        Initialize the analyzer with gear recipe data.

        Args:
            gear_lookup: Dictionary mapping gear base_id to GearPiece
        """
        self.gear_lookup = gear_lookup
        self.kyrotech_salvage_ids = set(KYROTECH_SALVAGE_IDS.keys())

    def calculate_salvage_requirements(
        self, gear_id: str, kyrotech_salvage_ids: set = None
    ) -> Dict[str, int]:
        """
        Recursively calculate raw salvage requirements for a gear piece.

        Args:
            gear_id: The base_id of the gear piece
            kyrotech_salvage_ids: Set of kyrotech salvage base_ids to track

        Returns:
            Dictionary mapping salvage base_id to total amount needed
        """
        if kyrotech_salvage_ids is None:
            kyrotech_salvage_ids = self.kyrotech_salvage_ids

        salvage_counts = defaultdict(int)
        if gear_id not in self.gear_lookup:
            return dict(salvage_counts)

        gear_piece = self.gear_lookup[gear_id]
        if self._is_salvage_piece(gear_piece):
            if gear_id in kyrotech_salvage_ids:
                salvage_counts[gear_id] += 1
            return dict(salvage_counts)

        self._process_ingredients(gear_piece, salvage_counts, kyrotech_salvage_ids)

        return dict(salvage_counts)

    def calculate_character_requirements(
        self, gear_levels: List[GearTier], current_tier: int
    ) -> Dict[str, int]:
        """
        Count kyrotech salvage requirements from current gear tier to max.

        Args:
            gear_levels: List of gear tier requirements
            current_tier: Player's current gear tier for this character

        Returns:
            Dictionary mapping kyrotech salvage base_id to total amount needed
        """
        total_salvage = defaultdict(int)

        for gear_tier in gear_levels:
            if not self._should_count_tier(gear_tier.tier, current_tier):
                continue

            for gear_id in gear_tier.gear:
                salvage_reqs = self.calculate_salvage_requirements(gear_id)
                self._accumulate_salvage(total_salvage, salvage_reqs)

        return dict(total_salvage)

    def _is_salvage_piece(self, gear_piece: GearPiece) -> bool:
        """Check if a gear piece is a base salvage (no ingredients)."""
        return not gear_piece.ingredients or len(gear_piece.ingredients) == 0

    def _should_count_tier(self, tier: int, current_tier: int) -> bool:
        """Check if a gear tier should be counted in requirements."""
        return current_tier < tier <= MAX_GEAR_TIER

    def _process_ingredients(
        self,
        gear_piece: GearPiece,
        salvage_counts: defaultdict,
        kyrotech_salvage_ids: set,
    ) -> None:
        """
        Process all ingredients of a gear piece recursively.

        Reduces cyclomatic complexity by extracting ingredient processing logic.
        """
        for ingredient in gear_piece.ingredients:
            ing_gear_id = ingredient.gear
            ing_amount = ingredient.amount
            if ing_gear_id == "GRIND":
                continue

            if ing_gear_id in kyrotech_salvage_ids:
                salvage_counts[ing_gear_id] += ing_amount
            else:
                sub_salvage = self.calculate_salvage_requirements(
                    ing_gear_id, kyrotech_salvage_ids
                )
                for salvage_id, count in sub_salvage.items():
                    salvage_counts[salvage_id] += count * ing_amount

    def _accumulate_salvage(
        self, total_salvage: defaultdict, salvage_reqs: Dict[str, int]
    ) -> None:
        """Accumulate salvage requirements into total."""
        for salvage_id, amount in salvage_reqs.items():
            total_salvage[salvage_id] += amount


class RosterAnalyzer:
    """
    Analyzes a player's roster to identify kyrotech requirements.

    Separates roster analysis logic from data fetching and presentation.
    """

    def __init__(self, kyrotech_analyzer: KyrotechAnalyzer):
        """
        Initialize the roster analyzer.

        Args:
            kyrotech_analyzer: KyrotechAnalyzer instance for calculations
        """
        self.kyrotech_analyzer = kyrotech_analyzer

    def analyze_roster(
        self, player_units: List[PlayerUnit], units_by_id: Dict[str, Unit]
    ) -> List[Tuple[str, int, Dict[str, int], int]]:
        """
        Analyze player's roster for kyrotech needs.

        Args:
            player_units: List of player's units
            units_by_id: Dictionary mapping unit base_id to Unit data

        Returns:
            List of tuples: (name, current_gear, kyrotech_needs, total)
            Sorted by total kyrotech count descending
        """
        results = []

        for player_unit in player_units:
            character_result = self._analyze_character(player_unit, units_by_id)
            if character_result:
                results.append(character_result)

        return sorted(results, key=lambda x: x[3], reverse=True)

    def _analyze_character(
        self, player_unit: PlayerUnit, units_by_id: Dict[str, Unit]
    ) -> Tuple[str, int, Dict[str, int], int] | None:
        """
        Analyze a single character for kyrotech requirements.

        Extracted method to reduce complexity in analyze_roster.

        Args:
            player_unit: Player's unit data
            units_by_id: Dictionary of all unit definitions

        Returns:
            Tuple of (name, gear_level, kyrotech_needs, total) or None if no needs
        """
        base_id = player_unit.data.base_id
        current_gear = player_unit.data.gear_level

        if current_gear >= MAX_GEAR_TIER or base_id not in units_by_id:
            return None

        unit_info = units_by_id[base_id]
        kyrotech_needs = self.kyrotech_analyzer.calculate_character_requirements(
            unit_info.gear_levels, current_gear
        )

        if not kyrotech_needs:
            return None

        total_kyrotech = sum(kyrotech_needs.values())
        return (unit_info.name, current_gear, kyrotech_needs, total_kyrotech)

    def build_units_lookup(self, units: List[Unit]) -> Dict[str, Unit]:
        """
        Create a lookup dictionary for units by base_id.

        Args:
            units: List of Unit objects

        Returns:
            Dictionary mapping base_id to Unit
        """
        return {unit.base_id: unit for unit in units}
