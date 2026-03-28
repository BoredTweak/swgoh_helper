"""
Pydantic models for SWGOH stat definitions data.
"""

from pydantic import BaseModel


class StatDefinition(BaseModel):
    """Represents a stat type definition in Star Wars Galaxy of Heroes."""

    stat_id: int
    stat_name: str  # e.g., "MAX_HEALTH", "STRENGTH"
    name: str  # e.g., "Health", "Strength (STR)"
    detailed_name: str
    is_decimal: bool
