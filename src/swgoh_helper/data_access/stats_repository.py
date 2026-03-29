"""
Stat definitions repository for accessing stat metadata from SWGOH.gg API.
"""

from typing import Dict, List, Optional

from ..models import StatDefinition
from .base import BaseRepository


class StatDefinitionsRepository(BaseRepository):
    """
    Repository for accessing stat definition data from SWGOH.gg.

    Provides methods to fetch:
    - All stat definitions
    - Stat lookups by ID or name
    """

    def get_cache_key(self) -> str:
        """Generate cache key for stat definitions."""
        return "stat_definitions"

    def get_all_stats(self) -> List[StatDefinition]:
        """
        Fetch all stat definitions from the API.

        Returns:
            List of StatDefinition objects
        """
        data = self._client.fetch_with_cache(
            cache_key=self.get_cache_key(),
            fetch_func=lambda: self._client.get("/stat-definitions/"),
            cache_message="Loading stat definitions from cache...",
            fetch_message="Fetching stat definitions from API...",
        )
        # API returns a list directly
        if isinstance(data, list):
            return [StatDefinition(**stat) for stat in data]
        elif isinstance(data, dict) and "data" in data:
            return [StatDefinition(**stat) for stat in data["data"]]
        return []

    def build_stats_by_id(self) -> Dict[int, StatDefinition]:
        """
        Build a lookup dictionary by stat_id.

        Returns:
            Dictionary mapping stat_id to StatDefinition
        """
        stats = self.get_all_stats()
        return {stat.stat_id: stat for stat in stats}

    def build_stats_by_name(self) -> Dict[str, StatDefinition]:
        """
        Build a lookup dictionary by stat_name.

        Returns:
            Dictionary mapping stat_name to StatDefinition
        """
        stats = self.get_all_stats()
        return {stat.stat_name: stat for stat in stats}

    def get_stat_by_id(self, stat_id: int) -> Optional[StatDefinition]:
        """
        Get a stat definition by its ID.

        Args:
            stat_id: The stat's numeric identifier

        Returns:
            The StatDefinition if found, None otherwise
        """
        lookup = self.build_stats_by_id()
        return lookup.get(stat_id)

    def get_stat_by_name(self, stat_name: str) -> Optional[StatDefinition]:
        """
        Get a stat definition by its internal name.

        Args:
            stat_name: The stat's internal name (e.g., "MAX_HEALTH")

        Returns:
            The StatDefinition if found, None otherwise
        """
        lookup = self.build_stats_by_name()
        return lookup.get(stat_name.upper())

    def get_decimal_stats(self) -> List[StatDefinition]:
        """
        Get all stats that use decimal values.

        Returns:
            List of StatDefinition objects where is_decimal=True
        """
        stats = self.get_all_stats()
        return [s for s in stats if s.is_decimal]

    def get_integer_stats(self) -> List[StatDefinition]:
        """
        Get all stats that use integer values.

        Returns:
            List of StatDefinition objects where is_decimal=False
        """
        stats = self.get_all_stats()
        return [s for s in stats if not s.is_decimal]
