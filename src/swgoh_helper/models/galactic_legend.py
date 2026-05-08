"""Pydantic models for Galactic Legend path planning."""

from typing import Optional

from pydantic import BaseModel, Field


class GLRequirement(BaseModel):
    """A single prerequisite for unlocking a Galactic Legend."""

    unit_name: str
    required_relic: Optional[int] = None
    required_gear: Optional[int] = None
    required_stars: int = 7


class GLPathDefinition(BaseModel):
    """Requirement set for one Galactic Legend."""

    gl_name: str
    requirements: list[GLRequirement] = Field(default_factory=list)


class GLRequirementProgress(BaseModel):
    """Current player progress for one requirement."""

    unit_name: str
    required_relic: Optional[int] = None
    required_gear: Optional[int] = None
    required_stars: int = 7
    owned: bool
    complete: bool
    current_relic: int = -1
    current_gear: int = 0
    current_stars: int = 0
    distance: float


class GLPathScore(BaseModel):
    """Aggregated score for one Galactic Legend path."""

    gl_name: str
    total_requirements: int
    completed_requirements: int
    total_distance: float
    all_requirements: list[GLRequirementProgress] = Field(default_factory=list)
    missing_requirements: list[GLRequirementProgress] = Field(default_factory=list)


class GLPathReport(BaseModel):
    """Top-ranked Galactic Legend paths for one player."""

    player_name: str
    ally_code: int
    ranked_paths: list[GLPathScore] = Field(default_factory=list)
