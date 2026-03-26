"""
Pydantic models for SWGOH gear/equipment data.
"""

from typing import List, Dict, Any
from pydantic import BaseModel, Field


class GearIngredient(BaseModel):
    """Represents an ingredient needed to craft a gear piece."""

    amount: int
    gear: str  # Can be a gear base_id or "GRIND" for credits


class GearRecipe(BaseModel):
    """Represents a recipe for crafting a gear piece."""

    base_id: str
    result_id: str
    cost: int
    ingredients: List[GearIngredient] = Field(default_factory=list)


class GearPiece(BaseModel):
    """Represents a gear piece/equipment in Star Wars Galaxy of Heroes."""

    base_id: str
    name: str
    tier: int
    mark: str
    required_level: int
    cost: int
    image: str
    url: str
    recipes: List[GearRecipe] = Field(default_factory=list)
    ingredients: List[GearIngredient] = Field(default_factory=list)
    stats: Dict[str, Any] = Field(default_factory=dict)


class GearResponse(BaseModel):
    """Root response model containing the list of gear pieces."""

    data: List[GearPiece] = Field(default_factory=list)
