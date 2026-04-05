"""
Guilds repository for accessing guild data from SWGOH.gg API.
"""

from typing import List, Tuple

from ..models import GuildResponse, PlayerResponse
from .base import BaseApiClient, BaseRepository
from .players_repository import PlayersRepository


class GuildsRepository(BaseRepository):
    """
    Repository for accessing guild data from SWGOH.gg.

    Provides methods to fetch:
    - Guild profile and member information
    - Guild member rosters
    - Guild lookup from player ally code
    """

    def __init__(self, client: BaseApiClient, players_repo: PlayersRepository):
        """
        Initialize the guilds repository.

        Args:
            client: The base API client
            players_repo: Players repository for fetching member rosters
        """
        super().__init__(client)
        self._players_repo = players_repo

    def get_cache_key(self, guild_id: str) -> str:
        """Generate cache key for a guild."""
        return f"guild_{guild_id}"

    def get_guild(self, guild_id: str) -> GuildResponse:
        """
        Fetch guild data including member list.

        Args:
            guild_id: The guild's unique identifier

        Returns:
            GuildResponse containing guild data
        """
        data = self._client.fetch_with_cache(
            cache_key=self.get_cache_key(guild_id),
            fetch_func=lambda: self._client.get(f"/guild-profile/{guild_id}/"),
            cache_message="Loading guild data from cache...",
            fetch_message="Fetching guild data from API...",
        )
        return GuildResponse(**data)

    def get_member_ally_codes(self, guild_id: str) -> List[int]:
        """
        Get all ally codes for members of a guild.

        Args:
            guild_id: The guild's unique identifier

        Returns:
            List of ally codes for all guild members
        """
        guild = self.get_guild(guild_id)
        return [
            member.ally_code
            for member in guild.data.members
            if member.ally_code is not None
        ]

    def get_guild_id_from_player(self, ally_code: str) -> str:
        """
        Get the guild ID for a player.

        Args:
            ally_code: Player's ally code

        Returns:
            Guild ID string

        Raises:
            ValueError: If player is not in a guild
        """
        player = self._players_repo.get_player(ally_code)
        guild_id = player.data.guild_id

        if not guild_id:
            raise ValueError(
                f"Player {player.data.name} is not in a guild or guild data unavailable"
            )

        return guild_id

    def get_guild_from_ally_code(self, ally_code: str) -> Tuple[str, str, List[int]]:
        """
        Get guild info from a player's ally code.

        Args:
            ally_code: Player's ally code

        Returns:
            Tuple of (guild_id, guild_name, member_ally_codes)
        """
        self._client.progress.update(
            f"Fetching guild information for ally code {ally_code}..."
        )

        guild_id = self.get_guild_id_from_player(ally_code)
        guild = self.get_guild(guild_id)

        guild_name = guild.data.name
        member_ally_codes = self.get_member_ally_codes(guild_id)

        self._client.progress.update(f"Found guild: {guild_name} (ID: {guild_id})")
        self._client.progress.update(
            f"Guild has {len(member_ally_codes)} members with ally codes."
        )

        return guild_id, guild_name, member_ally_codes

    def get_guild_rosters(
        self, ally_codes: List[int], delay_seconds: float = 1.0
    ) -> List[PlayerResponse]:
        """
        Fetch rosters for all guild members.

        Args:
            ally_codes: List of guild member ally codes
            delay_seconds: Delay between API calls for uncached data

        Returns:
            List of PlayerResponse objects for all members
        """
        return self._players_repo.get_players_batch(ally_codes, delay_seconds)
