"""
Units repository for accessing unit/character/ship data from SWGOH.gg API.
"""

from typing import Dict, List, Optional

from ..models import (
    Unit,
    UnitsResponse,
    CharactersResponse,
    ShipsResponse,
)
from .base import BaseRepository


class UnitsRepository(BaseRepository):
    """
    Repository for accessing unit data from SWGOH.gg.

    Provides methods to fetch:
    - All units (characters + ships combined)
    - Characters only
    - Ships only
    - Unit lookups by base_id
    """

    def get_cache_key(self, endpoint: str = "units") -> str:
        """Generate cache key for units endpoints."""
        return endpoint

    def get_all_units(self) -> UnitsResponse:
        """
        Fetch all units (characters and ships) from the API.

        Returns:
            UnitsResponse containing all units with gear_levels
        """
        data = self._client.fetch_with_cache(
            cache_key=self.get_cache_key("units"),
            fetch_func=lambda: self._client.get("/units/"),
            cache_message="Loading units from cache...",
            fetch_message="Fetching units from API...",
        )
        return UnitsResponse(**data)

    def get_characters(self) -> CharactersResponse:
        """
        Fetch all characters (no ships) from the API.

        Returns:
            CharactersResponse containing all characters
        """
        data = self._client.fetch_with_cache(
            cache_key=self.get_cache_key("characters"),
            fetch_func=lambda: self._client.get("/characters/"),
            cache_message="Loading characters from cache...",
            fetch_message="Fetching characters from API...",
        )
        # API returns a list directly, wrap it
        if isinstance(data, list):
            data = {"data": data}
        return CharactersResponse(**data)

    def get_ships(self) -> ShipsResponse:
        """
        Fetch all ships from the API.

        Returns:
            ShipsResponse containing all ships
        """
        data = self._client.fetch_with_cache(
            cache_key=self.get_cache_key("ships"),
            fetch_func=lambda: self._client.get("/ships/"),
            cache_message="Loading ships from cache...",
            fetch_message="Fetching ships from API...",
        )
        # API returns a list directly, wrap it
        if isinstance(data, list):
            data = {"data": data}
        return ShipsResponse(**data)

    def build_units_lookup(self, units: List[Unit]) -> Dict[str, Unit]:
        """
        Build a lookup dictionary from a list of units.

        Args:
            units: List of Unit objects

        Returns:
            Dictionary mapping base_id to Unit
        """
        return {unit.base_id: unit for unit in units}

    def get_unit_by_id(self, base_id: str) -> Optional[Unit]:
        """
        Get a specific unit by its base_id.

        Args:
            base_id: The unit's base identifier

        Returns:
            The Unit if found, None otherwise
        """
        units = self.get_all_units()
        lookup = self.build_units_lookup(units.data)
        return lookup.get(base_id)

    def get_units_by_category(
        self, category: str, combat_type: Optional[int] = None
    ) -> List[Unit]:
        """
        Get all units belonging to a specific category.

        Args:
            category: The category name (e.g., "Rebel", "Empire", "Sith")
            combat_type: Optional filter (1 = characters, 2 = ships)

        Returns:
            List of units matching the criteria
        """
        units = self.get_all_units()
        result = []
        for unit in units.data:
            if category.lower() in [c.lower() for c in unit.categories]:
                if combat_type is None or unit.combat_type == combat_type:
                    result.append(unit)
        return result
