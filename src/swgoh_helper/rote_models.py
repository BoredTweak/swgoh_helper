"""
Pydantic models for Rise of the Empire (ROTE) Territory Battle platoon requirements.

These models support manual configuration of platoon data since no API is available.

NOTE: Models have been moved to swgoh_helper.models.rote
This module re-exports them for backward compatibility.
"""

from .models.rote import (
    RotePath,
    UnitType,
    UnitRequirement,
    SimpleRoteRequirements,
)

__all__ = [
    "RotePath",
    "UnitType",
    "UnitRequirement",
    "SimpleRoteRequirements",
]
