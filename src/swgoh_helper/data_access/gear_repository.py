"""
Gear repository for accessing gear/equipment data from SWGOH.gg API.
"""

from typing import Dict, List, Optional

from ..models import GearPiece
from .base import BaseRepository


class GearRepository(BaseRepository):
    """
    Repository for accessing gear data from SWGOH.gg.

    Provides methods to fetch:
    - All gear pieces with crafting recipes
    - Gear lookup by base_id
    - Gear filtering by tier/mark
    """

    def get_cache_key(self) -> str:
        """Generate cache key for gear."""
        return "gear"

    def get_all_gear(self) -> Dict[str, GearPiece]:
        """
        Fetch all gear pieces and return as a lookup dictionary.

        Returns:
            Dictionary mapping gear base_id to GearPiece
        """
        data = self._client.fetch_with_cache(
            cache_key=self.get_cache_key(),
            fetch_func=lambda: self._client.get("/gear/"),
            cache_message="Loading gear recipes from cache...",
            fetch_message="Fetching gear recipes from API...",
        )
        return self._build_gear_lookup(data)

    def _build_gear_lookup(self, gear_data: list) -> Dict[str, GearPiece]:
        """Build a lookup dictionary from gear data."""
        gear_by_id: Dict[str, GearPiece] = {}
        for gear_json in gear_data:
            gear_piece = GearPiece(**gear_json)
            gear_by_id[gear_piece.base_id] = gear_piece
        return gear_by_id

    def get_gear_by_id(self, base_id: str) -> Optional[GearPiece]:
        """
        Get a specific gear piece by its base_id.

        Args:
            base_id: The gear's base identifier

        Returns:
            The GearPiece if found, None otherwise
        """
        gear = self.get_all_gear()
        return gear.get(base_id)

    def get_gear_by_tier(self, tier: int) -> List[GearPiece]:
        """
        Get all gear pieces of a specific tier.

        Args:
            tier: The gear tier to filter by

        Returns:
            List of GearPiece objects matching the tier
        """
        gear = self.get_all_gear()
        return [g for g in gear.values() if g.tier == tier]

    def get_gear_with_ingredients(self, ingredient_id: str) -> List[GearPiece]:
        """
        Find all gear that uses a specific ingredient.

        Args:
            ingredient_id: The base_id of the ingredient gear

        Returns:
            List of GearPiece objects that use this ingredient
        """
        gear = self.get_all_gear()
        result = []
        for gear_piece in gear.values():
            for ingredient in gear_piece.ingredients:
                if ingredient.gear == ingredient_id:
                    result.append(gear_piece)
                    break
        return result
