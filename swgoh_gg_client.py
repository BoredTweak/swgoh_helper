import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Callable, TypeVar, Any, List, Tuple

from models import PlayerResponse, UnitsResponse, GearPiece, GuildResponse
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
        """Fetch all units from SWGOH.GG API."""

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
        gear_by_id: Dict[str, GearPiece] = {}
        for gear_json in gear_data:
            gear_piece = GearPiece(**gear_json)
            gear_by_id[gear_piece.base_id] = gear_piece
        return gear_by_id

    def get_player_units(self, ally_code: str) -> PlayerResponse:
        """Fetch player's units/roster from SWGOH.GG API."""
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

    def get_guild(self, guild_id: str) -> GuildResponse:
        """Fetch guild data from SWGOH.GG API."""

        def fetch_from_api():
            url = f"{self.base_url}/guild-profile/{guild_id}/"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()

        data = self._fetch_with_cache(
            cache_key=f"guild_{guild_id}",
            fetch_func=fetch_from_api,
            cache_message="Loading guild data from cache...",
            fetch_message="Fetching guild data from API...",
        )

        return GuildResponse(**data)

    def get_guild_player_ids(self, guild_id: str) -> List[int]:
        """Fetch all player ally codes in a guild."""
        guild = self.get_guild(guild_id)
        return [
            member.ally_code
            for member in guild.data.members
            if member.ally_code is not None
        ]

    def get_guild_id_from_player(self, ally_code: str) -> str:
        """Get the guild ID from a player's ally code. Raises ValueError if not in a guild."""
        player = self.get_player_units(ally_code)
        guild_id = player.data.guild_id

        if not guild_id:
            raise ValueError(
                f"Player {player.data.name} is not in a guild or guild data is not available"
            )

        return guild_id

    def get_guild_from_ally_code(self, ally_code: str) -> tuple[str, str, List[int]]:
        """Get guild info (id, name, member ally codes) from a player's ally code."""
        print(f"\nFetching guild information for ally code {ally_code}...")

        guild_id = self.get_guild_id_from_player(ally_code)
        guild = self.get_guild(guild_id)

        guild_name = guild.data.name
        member_ally_codes = self.get_guild_player_ids(guild_id)

        print(f"Found guild: {guild_name} (ID: {guild_id})")
        print(f"Guild has {len(member_ally_codes)} members with ally codes.")

        return guild_id, guild_name, member_ally_codes

    def get_guild_rosters(
        self, ally_codes: List[int], delay_seconds: float = 1.0
    ) -> List[PlayerResponse]:
        """Fetch rosters for all guild members. Fetches cached in parallel, uncached sequentially."""
        total = len(ally_codes)
        print(f"\nFetching rosters for {total} guild members...")

        cached_codes, uncached_codes = self._partition_by_cache_status(ally_codes)
        print(
            f"  Found {len(cached_codes)} cached, {len(uncached_codes)} to fetch from API"
        )

        rosters: List[PlayerResponse] = []
        if cached_codes:
            print(f"\n  Loading {len(cached_codes)} cached rosters in parallel...")
            cached_rosters = self._fetch_players_parallel(cached_codes)
            rosters.extend(cached_rosters)
            print(f"  Loaded {len(cached_rosters)} cached rosters.")

        if uncached_codes:
            print(f"\n  Fetching {len(uncached_codes)} rosters from API...")
            uncached_rosters = self._fetch_players_sequential(
                uncached_codes, delay_seconds
            )
            rosters.extend(uncached_rosters)

        print(f"\nSuccessfully fetched {len(rosters)} rosters.\n")
        return rosters

    def _partition_by_cache_status(
        self, ally_codes: List[int]
    ) -> Tuple[List[int], List[int]]:
        cached_codes = []
        uncached_codes = []

        for ally_code in ally_codes:
            normalized_code = str(ally_code).replace("-", "")
            cache_key = f"player_{normalized_code}"

            if self.cache.is_valid(cache_key):
                cached_codes.append(ally_code)
            else:
                uncached_codes.append(ally_code)

        return cached_codes, uncached_codes

    def _fetch_players_parallel(
        self, ally_codes: List[int], max_workers: int = 10
    ) -> List[PlayerResponse]:
        rosters = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_code = {
                executor.submit(self.get_player_units, str(code)): code
                for code in ally_codes
            }

            for future in as_completed(future_to_code):
                ally_code = future_to_code[future]
                try:
                    roster = future.result()
                    rosters.append(roster)
                except Exception as e:
                    print(f"    Warning: Failed to load cached {ally_code}: {e}")

        return rosters

    def _fetch_players_sequential(
        self, ally_codes: List[int], delay_seconds: float
    ) -> List[PlayerResponse]:
        rosters = []
        total = len(ally_codes)

        for idx, ally_code in enumerate(ally_codes, 1):
            try:
                print(f"    [{idx}/{total}] Fetching {ally_code}...")
                roster = self.get_player_units(str(ally_code))
                rosters.append(roster)
                if idx < total and delay_seconds > 0:
                    time.sleep(delay_seconds)
            except Exception as e:
                print(f"    Warning: Failed to fetch {ally_code}: {e}")
                continue

        return rosters
