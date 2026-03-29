"""
Abilities repository for accessing ability data from SWGOH.gg API.
"""

from typing import Dict, List, Optional

from ..models import Ability, AbilitiesResponse
from .base import BaseRepository


class AbilitiesRepository(BaseRepository):
    """
    Repository for accessing ability data from SWGOH.gg.

    Provides methods to fetch:
    - All abilities
    - Zeta abilities
    - Omicron abilities
    - Ultimate abilities
    - Abilities by unit
    """

    def get_cache_key(self) -> str:
        """Generate cache key for abilities."""
        return "abilities"

    def get_all_abilities(self) -> AbilitiesResponse:
        """
        Fetch all abilities from the API.

        Returns:
            AbilitiesResponse containing all abilities
        """
        data = self._client.fetch_with_cache(
            cache_key=self.get_cache_key(),
            fetch_func=lambda: self._client.get("/abilities/"),
            cache_message="Loading abilities from cache...",
            fetch_message="Fetching abilities from API...",
        )
        # API returns a list directly, wrap it
        if isinstance(data, list):
            data = {"data": data}
        return AbilitiesResponse(**data)

    def build_abilities_lookup(self) -> Dict[str, Ability]:
        """
        Build a lookup dictionary for abilities by base_id.

        Returns:
            Dictionary mapping base_id to Ability
        """
        abilities = self.get_all_abilities()
        return {ability.base_id: ability for ability in abilities.data}

    def get_ability_by_id(self, base_id: str) -> Optional[Ability]:
        """
        Get a specific ability by its base_id.

        Args:
            base_id: The ability's base identifier

        Returns:
            The Ability if found, None otherwise
        """
        lookup = self.build_abilities_lookup()
        return lookup.get(base_id)

    def get_zeta_abilities(self) -> List[Ability]:
        """
        Get all abilities that have a zeta upgrade.

        Returns:
            List of abilities with is_zeta=True
        """
        abilities = self.get_all_abilities()
        return [a for a in abilities.data if a.is_zeta]

    def get_omicron_abilities(self) -> List[Ability]:
        """
        Get all abilities that have an omicron upgrade.

        Returns:
            List of abilities with is_omicron=True
        """
        abilities = self.get_all_abilities()
        return [a for a in abilities.data if a.is_omicron]

    def get_ultimate_abilities(self) -> List[Ability]:
        """
        Get all ultimate abilities (Galactic Legend abilities).

        Returns:
            List of abilities with is_ultimate=True
        """
        abilities = self.get_all_abilities()
        return [a for a in abilities.data if a.is_ultimate]

    def get_abilities_for_character(self, character_base_id: str) -> List[Ability]:
        """
        Get all abilities for a specific character.

        Args:
            character_base_id: The character's base_id

        Returns:
            List of abilities belonging to the character
        """
        abilities = self.get_all_abilities()
        return [a for a in abilities.data if a.character_base_id == character_base_id]

    def get_abilities_for_ship(self, ship_base_id: str) -> List[Ability]:
        """
        Get all abilities for a specific ship.

        Args:
            ship_base_id: The ship's base_id

        Returns:
            List of abilities belonging to the ship
        """
        abilities = self.get_all_abilities()
        return [a for a in abilities.data if a.ship_base_id == ship_base_id]

    def get_abilities_by_type(self, ability_type: int) -> List[Ability]:
        """
        Get all abilities of a specific type.

        Args:
            ability_type: 1=basic, 2=special, 3=leader, 4=unique, etc.

        Returns:
            List of abilities of the specified type
        """
        abilities = self.get_all_abilities()
        return [a for a in abilities.data if a.type == ability_type]
