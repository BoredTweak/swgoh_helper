import requests
from typing import Dict, Callable, TypeVar, Any

from models import PlayerResponse, UnitsResponse, GearPiece
from cache_manager import CacheManager


T = TypeVar("T")


class SwgohGGClient:
    """
    Client for interacting with the SWGOH.GG API with intelligent caching.
    """

    def __init__(self, api_key: str, cache_manager: CacheManager = None):
        """
        Initialize the SWGOH.GG API client.

        Args:
            api_key: API key for SWGOH.GG authentication
            cache_manager: Optional cache manager instance (creates default if None)
        """
        self.api_key = api_key
        self.base_url = "https://swgoh.gg/api"
        self.headers = {"x-gg-bot-access": self.api_key}
        self.cache = cache_manager or CacheManager()

    def _fetch_with_cache(
        self,
        cache_key: str,
        fetch_func: Callable[[], Any],
        cache_message: str,
        fetch_message: str,
    ) -> Any:
        """
        Generic method to fetch data with caching support.

        Reduces code duplication by providing a template for cached API calls.

        Args:
            cache_key: Unique identifier for caching
            fetch_func: Function that fetches data from API
            cache_message: Message to display when loading from cache
            fetch_message: Message to display when fetching from API

        Returns:
            Data from cache or freshly fetched from API
        """
        # Try to get from cache first
        cached_data = self.cache.get(cache_key)
        if cached_data is not None:
            print(cache_message)
            return cached_data

        # Fetch from API if cache miss
        print(fetch_message)
        data = fetch_func()
        self.cache.set(cache_key, data)
        return data

    def get_units(self) -> UnitsResponse:
        """
        Fetch all units from SWGOH.GG API.

        Returns:
            UnitsResponse object containing all game units
        """

        def fetch_from_api():
            response = requests.get(f"{self.base_url}/units/", headers=self.headers)
            response.raise_for_status()
            return response.json()

        data = self._fetch_with_cache(
            cache_key="units",
            fetch_func=fetch_from_api,
            cache_message="Loading units from cache...",
            fetch_message="Fetching units from API...",
        )

        return UnitsResponse(**data)

    def get_gear_recipes(self) -> Dict[str, GearPiece]:
        """
        Fetch all gear/equipment data from SWGOH.GG API including crafting recipes.

        Returns:
            Dictionary mapping gear base_id to GearPiece object
        """

        def fetch_from_api():
            response = requests.get(f"{self.base_url}/gear/", headers=self.headers)
            response.raise_for_status()
            return response.json()

        gear_data = self._fetch_with_cache(
            cache_key="gear",
            fetch_func=fetch_from_api,
            cache_message="Loading gear recipes from cache...",
            fetch_message="Fetching gear recipes from API...",
        )

        return self._build_gear_lookup(gear_data)

    def _build_gear_lookup(self, gear_data: list) -> Dict[str, GearPiece]:
        """
        Convert gear data list to a lookup dictionary.

        Extracted method to reduce complexity in get_gear_recipes.

        Args:
            gear_data: List of gear piece dictionaries

        Returns:
            Dictionary mapping gear base_id to GearPiece object
        """
        gear_by_id: Dict[str, GearPiece] = {}
        for gear_json in gear_data:
            gear_piece = GearPiece(**gear_json)
            gear_by_id[gear_piece.base_id] = gear_piece
        return gear_by_id

    def get_player_units(self, ally_code: str) -> PlayerResponse:
        """
        Fetch player's units/roster from SWGOH.GG API.

        Args:
            ally_code: Player's ally code (9 digits, can include dashes)

        Returns:
            PlayerResponse object containing player's unit collection data
        """
        normalized_ally_code = ally_code.replace("-", "")

        def fetch_from_api():
            url = f"{self.base_url}/player/{normalized_ally_code}/"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()

        data = self._fetch_with_cache(
            cache_key=f"player_{normalized_ally_code}",
            fetch_func=fetch_from_api,
            cache_message="Loading player data from cache...",
            fetch_message="Fetching player data from API...",
        )

        return PlayerResponse(**data)
