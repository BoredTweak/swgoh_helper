"""
Pydantic models for kyrotech analysis results.
"""

from typing import Dict, Optional

from pydantic import BaseModel


class CharacterKyrotechResult(BaseModel):
    """Result of kyrotech analysis for a single character."""

    name: str
    base_id: str
    gear_level: int
    kyrotech_needs: Dict[str, int]
    total_kyrotech: int
    is_owned: bool
    faction: Optional[str] = None
