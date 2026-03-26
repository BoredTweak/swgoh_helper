"""
Pydantic models for SWGOH guild data.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class GuildMember(BaseModel):
    """Represents a single guild member."""

    player_name: str
    player_level: int
    galactic_power: int
    ally_code: Optional[int] = None


class GuildData(BaseModel):
    """Represents the inner guild data with members."""

    guild_id: str
    name: str
    member_count: int
    galactic_power: int
    members: List[GuildMember] = Field(default_factory=list)


class GuildResponse(BaseModel):
    """Root response model containing guild data."""

    data: GuildData
