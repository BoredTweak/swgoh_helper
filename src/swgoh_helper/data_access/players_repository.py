"""
Players repository for accessing player data from SWGOH.gg API.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple

from ..models import PlayerResponse
from .base import BaseRepository


class PlayersRepository(BaseRepository):
    """
    Repository for accessing player data from SWGOH.gg.

    Provides methods to fetch:
    - Individual player data (roster, mods, datacrons)
    - Batch player data for guilds
    - Player roster analysis helpers
    """

    def get_cache_key(self, ally_code: str) -> str:
        """Generate cache key for a player."""
        normalized = str(ally_code).replace("-", "")
        return f"player_{normalized}"

    def get_player(self, ally_code: str, silent: bool = False) -> PlayerResponse:
        """
        Fetch a player's data including units, mods, and datacrons.

        Args:
            ally_code: Player's ally code (with or without dashes)
            silent: Suppress output if True

        Returns:
            PlayerResponse containing player data
        """
        normalized = str(ally_code).replace("-", "")

        data = self._client.fetch_with_cache(
            cache_key=self.get_cache_key(normalized),
            fetch_func=lambda: self._client.get(f"/player/{normalized}/"),
            cache_message=f"Loading {normalized} player data from cache...",
            fetch_message="Fetching player data from API...",
            silent=silent,
        )
        return PlayerResponse(**data)

    def invalidate_player_caches(self, ally_codes: List[int]) -> None:
        """
        Invalidate cache entries for specified ally codes.

        Args:
            ally_codes: List of ally codes to invalidate
        """
        for ally_code in ally_codes:
            self._client.invalidate_cache(self.get_cache_key(str(ally_code)))

    def get_players_batch(
        self, ally_codes: List[int], delay_seconds: float = 1.0
    ) -> List[PlayerResponse]:
        """
        Fetch data for multiple players efficiently.

        Uses parallel fetching for cached data and sequential fetching
        with rate limiting for uncached data.

        Args:
            ally_codes: List of ally codes to fetch
            delay_seconds: Delay between uncached API calls

        Returns:
            List of PlayerResponse objects
        """
        total = len(ally_codes)
        self._client.progress.update(f"Fetching rosters for {total} players...")

        cached_codes, uncached_codes = self._partition_by_cache_status(ally_codes)
        self._client.progress.update(
            f"  Found {len(cached_codes)} cached, {len(uncached_codes)} to fetch from API"
        )

        rosters: List[PlayerResponse] = []

        if cached_codes:
            self._client.progress.update(
                f"Loading {len(cached_codes)} cached rosters in parallel..."
            )
            cached_rosters = self._fetch_players_parallel(cached_codes)
            rosters.extend(cached_rosters)
            self._client.progress.update(
                f"Loaded {len(cached_rosters)} cached rosters."
            )

        if uncached_codes:
            self._client.progress.update(
                f"Fetching {len(uncached_codes)} rosters from API..."
            )
            uncached_rosters = self._fetch_players_sequential(
                uncached_codes, delay_seconds
            )
            rosters.extend(uncached_rosters)

        self._client.progress.update(f"Successfully fetched {len(rosters)} rosters.")
        return rosters

    def _partition_by_cache_status(
        self, ally_codes: List[int]
    ) -> Tuple[List[int], List[int]]:
        """Partition ally codes into cached and uncached groups."""
        cached_codes = []
        uncached_codes = []

        for ally_code in ally_codes:
            cache_key = self.get_cache_key(str(ally_code))
            if self._client.is_cache_valid(cache_key):
                cached_codes.append(ally_code)
            else:
                uncached_codes.append(ally_code)

        return cached_codes, uncached_codes

    def _fetch_players_parallel(
        self, ally_codes: List[int], max_workers: int = 10
    ) -> List[PlayerResponse]:
        """Fetch cached players in parallel."""
        rosters = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_code = {
                executor.submit(self.get_player, str(code), silent=True): code
                for code in ally_codes
            }

            for future in as_completed(future_to_code):
                ally_code = future_to_code[future]
                try:
                    roster = future.result()
                    rosters.append(roster)
                except Exception as e:
                    self._client.progress.update(
                        f"Warning: Failed to load cached {ally_code}: {e}"
                    )

        return rosters

    def _fetch_players_sequential(
        self, ally_codes: List[int], delay_seconds: float
    ) -> List[PlayerResponse]:
        """Fetch uncached players sequentially with rate limiting."""
        rosters = []
        total = len(ally_codes)

        for idx, ally_code in enumerate(ally_codes, 1):
            try:
                self._client.progress.update(f"[{idx}/{total}] Fetching {ally_code}...")
                roster = self.get_player(str(ally_code))
                rosters.append(roster)
                if idx < total and delay_seconds > 0:
                    time.sleep(delay_seconds)
            except Exception as e:
                self._client.progress.update(
                    f"Warning: Failed to fetch {ally_code}: {e}"
                )
                continue

        return rosters
