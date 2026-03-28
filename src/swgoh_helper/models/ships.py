"""
Pydantic models for SWGOH ships data.
"""

from typing import List
from pydantic import BaseModel, Field


class Ship(BaseModel):
    """Represents a ship in Star Wars Galaxy of Heroes."""

    name: str
    base_id: str
    url: str
    image: str
    power: int
    description: str
    combat_type: int  # Always 2 for ships
    alignment: str  # "Light Side", "Dark Side", "Neutral"
    categories: List[str] = Field(default_factory=list)
    ability_classes: List[str] = Field(default_factory=list)
    role: str
    capital_ship: bool
    activate_shard_count: int


class ShipsResponse(BaseModel):
    """Root response model containing the list of ships."""

    data: List[Ship]
