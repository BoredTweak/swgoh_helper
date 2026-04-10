"""
SWGOH Data Service - Unified facade for all data access operations.

This module provides a single entry point for accessing all SWGOH.gg data
through a cohesive, OOP-compliant interface.
"""

from typing import Dict, List, Optional

from ..cache_manager import CacheManager
from ..progress import ProgressNotifier
from ..models import (
    Ability,
    AbilitiesResponse,
    CharactersResponse,
    GearPiece,
    GuildResponse,
    PlayerResponse,
    ShipsResponse,
    StatDefinition,
    Unit,
    UnitsResponse,
)
from .base import BaseApiClient
from .abilities_repository import AbilitiesRepository
from .gear_repository import GearRepository
from .guilds_repository import GuildsRepository
from .players_repository import PlayersRepository
from .stats_repository import StatDefinitionsRepository
from .units_repository import UnitsRepository


class SwgohDataService:
    """
    Unified data service providing access to all SWGOH.gg API endpoints.

    This service acts as a facade over the individual repositories,
    providing a cohesive interface for data access operations.

    Example usage:
        >>> service = SwgohDataService(api_key="your_key")
        >>> player = service.get_player("123456789")
        >>> units = service.get_all_units()
    """

    def __init__(
        self,
        api_key: str,
        cache_manager: Optional[CacheManager] = None,
        progress: Optional[ProgressNotifier] = None,
    ):
        """
        Initialize the data service.

        Args:
            api_key: API key for SWGOH.gg authentication
            cache_manager: Optional cache manager (creates default if None)
            progress: Optional progress notifier for status updates
        """
        self._client = BaseApiClient(api_key, cache_manager, progress)

        # Initialize repositories
        self._units = UnitsRepository(self._client)
        self._players = PlayersRepository(self._client)
        self._guilds = GuildsRepository(self._client, self._players)
        self._gear = GearRepository(self._client)
        self._abilities = AbilitiesRepository(self._client)
        self._stats = StatDefinitionsRepository(self._client)

    # ==================== Repository Access ====================

    @property
    def units(self) -> UnitsRepository:
        """Access the units repository directly."""
        return self._units

    @property
    def players(self) -> PlayersRepository:
        """Access the players repository directly."""
        return self._players

    @property
    def guilds(self) -> GuildsRepository:
        """Access the guilds repository directly."""
        return self._guilds

    @property
    def gear(self) -> GearRepository:
        """Access the gear repository directly."""
        return self._gear

    @property
    def abilities(self) -> AbilitiesRepository:
        """Access the abilities repository directly."""
        return self._abilities

    @property
    def stats(self) -> StatDefinitionsRepository:
        """Access the stat definitions repository directly."""
        return self._stats

    @property
    def cache(self) -> CacheManager:
        """Access the cache manager."""
        return self._client.cache

    # ==================== Convenience Methods ====================

    # --- Units ---

    def get_all_units(self) -> UnitsResponse:
        """Get all units (characters and ships)."""
        return self._units.get_all_units()

    def get_characters(self) -> CharactersResponse:
        """Get all characters only."""
        return self._units.get_characters()

    def get_ships(self) -> ShipsResponse:
        """Get all ships only."""
        return self._units.get_ships()

    def get_unit_by_id(self, base_id: str) -> Optional[Unit]:
        """Get a specific unit by base_id."""
        return self._units.get_unit_by_id(base_id)

    # --- Players ---

    def get_player(self, ally_code: str, silent: bool = False) -> PlayerResponse:
        """Get player data including roster, mods, and datacrons."""
        return self._players.get_player(ally_code, silent)

    def get_players_batch(
        self, ally_codes: List[int], delay_seconds: float = 1.0
    ) -> List[PlayerResponse]:
        """Get data for multiple players."""
        return self._players.get_players_batch(ally_codes, delay_seconds)

    def invalidate_player_caches(self, ally_codes: List[int]) -> None:
        """Invalidate cache for specified players."""
        self._players.invalidate_player_caches(ally_codes)

    # --- Guilds ---

    def get_guild(self, guild_id: str) -> GuildResponse:
        """Get guild data including member list."""
        return self._guilds.get_guild(guild_id)

    def get_guild_from_ally_code(self, ally_code: str) -> tuple[str, str, List[int]]:
        """Get guild info from a player's ally code."""
        return self._guilds.get_guild_from_ally_code(ally_code)

    def get_guild_rosters(
        self, ally_codes: List[int], delay_seconds: float = 1.0
    ) -> List[PlayerResponse]:
        """Get rosters for all guild members."""
        return self._guilds.get_guild_rosters(ally_codes, delay_seconds)

    # --- Gear ---

    def get_all_gear(self) -> Dict[str, GearPiece]:
        """Get all gear pieces as a lookup dictionary."""
        return self._gear.get_all_gear()

    def get_gear_by_id(self, base_id: str) -> Optional[GearPiece]:
        """Get a specific gear piece by base_id."""
        return self._gear.get_gear_by_id(base_id)

    def get_gear_by_tier(self, tier: int) -> List[GearPiece]:
        """Get all gear of a specific tier."""
        return self._gear.get_gear_by_tier(tier)

    # --- Abilities ---

    def get_all_abilities(self) -> AbilitiesResponse:
        """Get all abilities."""
        return self._abilities.get_all_abilities()

    def get_ability_by_id(self, base_id: str) -> Optional[Ability]:
        """Get a specific ability by base_id."""
        return self._abilities.get_ability_by_id(base_id)

    def get_zeta_abilities(self) -> List[Ability]:
        """Get all zeta abilities."""
        return self._abilities.get_zeta_abilities()

    def get_omicron_abilities(self) -> List[Ability]:
        """Get all omicron abilities."""
        return self._abilities.get_omicron_abilities()

    def get_abilities_for_character(self, character_base_id: str) -> List[Ability]:
        """Get all abilities for a character."""
        return self._abilities.get_abilities_for_character(character_base_id)

    # --- Stats ---

    def get_all_stat_definitions(self) -> List[StatDefinition]:
        """Get all stat type definitions."""
        return self._stats.get_all_stats()

    def get_stat_by_id(self, stat_id: int) -> Optional[StatDefinition]:
        """Get a stat definition by ID."""
        return self._stats.get_stat_by_id(stat_id)

    def get_stat_by_name(self, stat_name: str) -> Optional[StatDefinition]:
        """Get a stat definition by name."""
        return self._stats.get_stat_by_name(stat_name)
