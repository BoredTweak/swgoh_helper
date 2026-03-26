"""
Pydantic models for SWGOH units/characters.
"""

from typing import List, Optional
from pydantic import BaseModel


class GearTier(BaseModel):
    """Represents a single gear tier with its required gear items."""

    tier: int
    gear: List[str]


class Unit(BaseModel):
    """Represents a single unit/character in Star Wars Galaxy of Heroes."""

    name: str
    base_id: str
    url: str
    image: str
    power: int
    description: str
    combat_type: int
    gear_levels: List[GearTier]
    alignment: int
    categories: List[str]
    ability_classes: List[str]
    role: str
    ship_base_id: Optional[str] = None
    ship_slot: Optional[int] = None
    activate_shard_count: int
    is_capital_ship: bool
    is_galactic_legend: bool
    made_available_on: str
    crew_base_ids: List[str]
    omicron_ability_ids: List[str]
    zeta_ability_ids: List[str]


class UnitsResponse(BaseModel):
    """Root response model containing the list of units."""

    data: List[Unit]
    message: Optional[str] = None
    total_count: Optional[int] = None
