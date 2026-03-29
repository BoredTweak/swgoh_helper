"""
Pydantic models for SWGOH characters data.
"""

from typing import List, Optional
from pydantic import BaseModel, Field

from .units import GearTier


class Character(BaseModel):
    """Represents a character in Star Wars Galaxy of Heroes."""

    name: str
    base_id: str
    url: str
    image: str
    power: int
    description: str
    combat_type: int  # Always 1 for characters
    gear_levels: List[GearTier] = Field(default_factory=list)
    alignment: str  # "Light Side", "Dark Side", "Neutral"
    categories: List[str] = Field(default_factory=list)
    ability_classes: List[str] = Field(default_factory=list)
    role: str
    ship: Optional[str] = None  # Base ID of piloted ship, if any
    ship_slot: Optional[int] = None
    activate_shard_count: int


class CharactersResponse(BaseModel):
    """Root response model containing the list of characters."""

    data: List[Character]
