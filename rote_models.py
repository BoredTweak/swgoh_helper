"""
Pydantic models for Rise of the Empire (ROTE) Territory Battle platoon requirements.

These models support manual configuration of platoon data since no API is available.
"""

from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from enum import Enum


class RotePath(str, Enum):
    """The three paths in ROTE Territory Battle."""

    DARK_SIDE = "dark_side"
    NEUTRAL = "neutral"
    LIGHT_SIDE = "light_side"


class UnitType(str, Enum):
    """Unit type - character or ship."""

    CHARACTER = "character"
    SHIP = "ship"


class UnitRequirement(BaseModel):
    """A unit required at a specific relic level."""

    unit_id: str = Field(description="Unit base_id from SWGOH.GG")
    unit_name: str = Field(description="Display name for readability")
    min_relic: int = Field(ge=0, le=9, description="Minimum relic level required")
    path: RotePath = Field(description="Which path requires this unit")
    territory: str = Field(description="Territory/planet name (e.g., 'Mustafar')")
    count: int = Field(default=1, ge=1, description="How many slots require this unit")
    unit_type: UnitType = Field(
        default=UnitType.CHARACTER, description="Whether this is a character or ship"
    )


class SimpleRoteRequirements(BaseModel):
    """
    ROTE requirements that list units by relic tier.
    """

    version: str = Field(default="1.0")
    last_updated: str
    notes: Optional[str] = None
    requirements: List[UnitRequirement] = Field(default_factory=list)
