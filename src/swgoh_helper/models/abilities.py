"""
Pydantic models for SWGOH abilities data.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class Ability(BaseModel):
    """Represents a single ability in Star Wars Galaxy of Heroes."""

    base_id: str
    ability_id: str
    name: str
    image: str
    url: str
    tier_max: int
    is_zeta: bool
    is_omega: bool
    is_omicron: bool
    is_ultimate: bool
    description: str
    combat_type: int  # 1 = character, 2 = ship
    omicron_mode: int
    type: int  # 1 = basic, 2 = special, 3 = leader, 4 = unique, etc.
    character_base_id: Optional[str] = None
    ship_base_id: Optional[str] = None
    omicron_battle_types: List[str] = Field(default_factory=list)


class AbilitiesResponse(BaseModel):
    """Root response model containing the list of abilities."""

    data: List[Ability]
