"""
Pydantic models for SWGOH Grand Arena Championship (GAC) data.
"""

from typing import List, Optional, Dict
from pydantic import BaseModel, Field

from .enums import GACFormat


class GACSquadUnit(BaseModel):
    """Represents a single unit in a GAC squad."""

    base_id: str
    name: Optional[str] = None
    gear_level: Optional[int] = None
    relic_tier: Optional[int] = None
    rarity: Optional[int] = None
    power: Optional[int] = None
    is_leader: bool = False


class GACSquad(BaseModel):
    """Represents a squad used in GAC (attack or defense)."""

    units: List[GACSquadUnit] = Field(default_factory=list)
    leader_base_id: Optional[str] = None
    banners_earned: Optional[int] = None
    banners_lost: Optional[int] = None
    survived: bool = True

    @property
    def leader(self) -> Optional[GACSquadUnit]:
        """Get the leader unit of the squad."""
        for unit in self.units:
            if unit.is_leader:
                return unit
        return self.units[0] if self.units else None


class GACBattle(BaseModel):
    """Represents a single battle in a GAC match."""

    attack_squad: Optional[GACSquad] = None
    defense_squad: Optional[GACSquad] = None
    banners: int = 0
    attempt_number: int = 1
    was_successful: bool = False
    territory: Optional[str] = None  # e.g., "front", "back", "fleet"


class GACTerritory(BaseModel):
    """Represents a territory in a GAC round."""

    name: str
    zone_id: Optional[str] = None
    squads: List[GACSquad] = Field(default_factory=list)
    is_fleet: bool = False
    is_cleared: bool = False
    banners_available: int = 0
    banners_earned: int = 0


class GACRoundResult(BaseModel):
    """Represents the result of a single GAC round/match against one opponent."""

    opponent_ally_code: Optional[int] = None
    opponent_name: Optional[str] = None
    opponent_galactic_power: Optional[int] = None
    player_score: int = 0
    opponent_score: int = 0
    player_attacks: List[GACBattle] = Field(default_factory=list)
    opponent_attacks: List[GACBattle] = Field(default_factory=list)
    player_defense: List[GACTerritory] = Field(default_factory=list)
    was_victory: Optional[bool] = None

    @property
    def is_win(self) -> bool:
        """Determine if the player won this round."""
        if self.was_victory is not None:
            return self.was_victory
        return self.player_score > self.opponent_score


class GACBracketPlayer(BaseModel):
    """Represents a player in a GAC bracket."""

    ally_code: int
    name: str
    skill_rating: int = 0
    galactic_power: int = 0
    league: Optional[str] = None
    division: Optional[int] = None
    wins: int = 0
    losses: int = 0
    current_round_score: int = 0
    portrait_image: Optional[str] = None
    title: Optional[str] = None
    guild_name: Optional[str] = None


class GACBracket(BaseModel):
    """Represents a GAC bracket containing multiple players."""

    event_id: Optional[str] = None
    bracket_id: Optional[str] = None
    format: GACFormat = GACFormat.FIVE_V_FIVE
    league: Optional[str] = None
    division: Optional[int] = None
    players: List[GACBracketPlayer] = Field(default_factory=list)
    round_number: int = 1
    total_rounds: int = 3
    start_time: Optional[str] = None
    end_time: Optional[str] = None


class GACSeasonEvent(BaseModel):
    """Represents a single GAC event/season."""

    event_id: str
    season_id: Optional[str] = None
    format: GACFormat = GACFormat.FIVE_V_FIVE
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    league: Optional[str] = None
    division: Optional[int] = None
    skill_rating_start: Optional[int] = None
    skill_rating_end: Optional[int] = None
    final_rank: Optional[int] = None
    wins: int = 0
    losses: int = 0
    rounds: List[GACRoundResult] = Field(default_factory=list)


class GACHistory(BaseModel):
    """Represents a player's complete GAC history."""

    ally_code: int
    player_name: Optional[str] = None
    current_skill_rating: int = 0
    current_league: Optional[str] = None
    current_division: Optional[int] = None
    events: List[GACSeasonEvent] = Field(default_factory=list)

    def get_events_by_format(self, format: GACFormat) -> List[GACSeasonEvent]:
        """Filter events by GAC format (3v3 or 5v5)."""
        return [e for e in self.events if e.format == format]

    @property
    def three_v_three_events(self) -> List[GACSeasonEvent]:
        """Get all 3v3 GAC events."""
        return self.get_events_by_format(GACFormat.THREE_V_THREE)

    @property
    def five_v_five_events(self) -> List[GACSeasonEvent]:
        """Get all 5v5 GAC events."""
        return self.get_events_by_format(GACFormat.FIVE_V_FIVE)


class GACMatchAnalysis(BaseModel):
    """Analysis of a GAC match showing likely attackers and defenders."""

    ally_code: int
    opponent_ally_code: Optional[int] = None
    format: GACFormat = GACFormat.FIVE_V_FIVE
    likely_attack_squads: List[GACSquad] = Field(default_factory=list)
    likely_defense_squads: List[GACSquad] = Field(default_factory=list)
    attack_squad_frequency: Dict[str, int] = Field(default_factory=dict)
    defense_squad_frequency: Dict[str, int] = Field(default_factory=dict)


class GACBracketResponse(BaseModel):
    """Response model for GAC bracket API call."""

    data: GACBracket
    message: Optional[str] = None


class GACHistoryResponse(BaseModel):
    """Response model for GAC history API call."""

    data: GACHistory
    message: Optional[str] = None
