"""
SWGOH.gg Data Access Layer

This package provides a cohesive, OOP-compliant interface for accessing
the SWGOH.gg API. It is organized as follows:

- **SwgohDataService**: Main entry point - a unified facade over all repositories
- **BaseApiClient**: Low-level HTTP client with caching
- **Repositories**: Domain-specific data access classes

Usage:
    >>> from swgoh_helper.data_access import SwgohDataService
    >>>
    >>> service = SwgohDataService(api_key="your_key")
    >>> player = service.get_player("123456789")
    >>> units = service.get_all_units()
    >>>
    >>> # Or access repositories directly:
    >>> zeta_abilities = service.abilities.get_zeta_abilities()
    >>> gear = service.gear.get_gear_by_tier(12)

Available Endpoints:
    - /units/ - All units (characters + ships) with gear levels
    - /characters/ - Characters only with gear levels
    - /ships/ - Ships only (no gear levels)
    - /gear/ - Gear pieces with crafting recipes
    - /abilities/ - All abilities with zeta/omicron info
    - /stat-definitions/ - Stat type metadata
    - /player/{ally_code}/ - Player data (roster, mods, datacrons)
    - /guild-profile/{guild_id}/ - Guild data with members
"""

from .base import BaseApiClient, BaseRepository
from .service import SwgohDataService
from .abilities_repository import AbilitiesRepository
from .gear_repository import GearRepository
from .guilds_repository import GuildsRepository
from .players_repository import PlayersRepository
from .stats_repository import StatDefinitionsRepository
from .units_repository import UnitsRepository


__all__ = [
    # Main service
    "SwgohDataService",
    # Base classes
    "BaseApiClient",
    "BaseRepository",
    # Repositories
    "AbilitiesRepository",
    "GearRepository",
    "GuildsRepository",
    "PlayersRepository",
    "StatDefinitionsRepository",
    "UnitsRepository",
]
