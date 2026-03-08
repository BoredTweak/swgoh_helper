"""
Pydantic models for SWGOH data schemas (units and player data).
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ===== Enums =====


class GACFormat(str, Enum):
    """Grand Arena Championship format types."""

    THREE_V_THREE = "3v3"
    FIVE_V_FIVE = "5v5"


class GACLeague(str, Enum):
    """Grand Arena Championship league tiers."""

    CARBONITE = "Carbonite"
    BRONZIUM = "Bronzium"
    CHROMIUM = "Chromium"
    AURODIUM = "Aurodium"
    KYBER = "Kyber"


# ===== Units API Models =====


class GearTier(BaseModel):
    """Represents a single gear tier with its required gear items."""

    tier: int
    gear: List[str]


class Unit(BaseModel):
    """Represents a single unit/character in Star Wars Galaxy of Heroes."""

    name: str
    base_id: str
    url: str
    image: str
    power: int
    description: str
    combat_type: int
    gear_levels: List[GearTier]
    alignment: int
    categories: List[str]
    ability_classes: List[str]
    role: str
    ship_base_id: Optional[str] = None
    ship_slot: Optional[int] = None
    activate_shard_count: int
    is_capital_ship: bool
    is_galactic_legend: bool
    made_available_on: str
    crew_base_ids: List[str]
    omicron_ability_ids: List[str]
    zeta_ability_ids: List[str]


class UnitsResponse(BaseModel):
    """Root response model containing the list of units."""

    data: List[Unit]
    message: Optional[str] = None
    total_count: Optional[int] = None


# ===== Player Data Models =====


class ArenaSquad(BaseModel):
    """Represents an arena squad composition."""

    rank: Optional[int] = None
    leader: Optional[str] = None
    members: List[str] = Field(default_factory=list)
    reinforcements: Optional[List[str]] = None


class GearSlot(BaseModel):
    """Represents a single gear slot for a unit."""

    slot: int
    is_obtained: bool
    base_id: str


class AbilityData(BaseModel):
    """Represents ability data for a unit."""

    id: str
    ability_tier: int
    is_omega: bool
    is_zeta: bool
    is_omicron: bool
    has_omicron_learned: bool
    has_zeta_learned: bool
    name: str
    tier_max: int


class UnitData(BaseModel):
    """Represents detailed unit data for a player's roster."""

    base_id: str
    name: str
    gear_level: int
    level: int
    power: int
    rarity: int
    gear: List[GearSlot]
    url: str
    stats: Dict[str, Optional[float]]
    stat_diffs: Optional[Dict[str, float]] = None
    zeta_abilities: List[str] = Field(default_factory=list)
    omicron_abilities: List[str] = Field(default_factory=list)
    ability_data: List[AbilityData] = Field(default_factory=list)
    mod_set_ids: List[str] = Field(default_factory=list)
    combat_type: int
    relic_tier: Optional[int] = Field(default=None)
    has_ultimate: bool
    is_galactic_legend: bool


class PlayerUnit(BaseModel):
    """Wrapper for player unit data."""

    data: UnitData


class ModSecondaryStat(BaseModel):
    """Represents a secondary stat on a mod."""

    name: str
    stat_id: int
    value: float
    display_value: str
    roll: int
    unscaled_roll_values: List[int]
    stat_max: int
    stat_min: int
    stat_rolls: List[float]


class ModPrimaryStat(BaseModel):
    """Represents the primary stat on a mod."""

    name: str
    stat_id: int
    value: float
    display_value: str


class Mod(BaseModel):
    """Represents a mod equipped on a character."""

    id: str
    level: int
    tier: int
    rarity: int
    set: str
    slot: int
    primary_stat: ModPrimaryStat
    character: Optional[str] = None
    secondary_stats: List[ModSecondaryStat] = Field(default_factory=list)
    reroll_count: int


class DatacronTier(BaseModel):
    """Represents a single tier/affix on a datacron."""

    scope_identifier: int
    scope_icon: str
    scope_target_name: str
    target_rule_id: Optional[str] = None
    ability_id: Optional[str] = None
    stat_type: int
    stat_value: float
    required_unit_tier: int
    required_relic_tier: int
    ability_description: Optional[str] = None


class Datacron(BaseModel):
    """Represents a datacron."""

    id: str
    set_id: int
    template_base_id: str
    reroll_count: int
    reroll_index: int
    locked: bool
    tier: int
    tiers: List[DatacronTier]


class PlayerData(BaseModel):
    """Represents the main player data."""

    ally_code: int
    arena_leader_base_id: str
    arena_rank: int
    level: int
    name: str
    last_updated: str
    galactic_power: int
    character_galactic_power: int
    ship_galactic_power: int
    ship_battles_won: int
    pvp_battles_won: int
    pve_battles_won: int
    pve_hard_won: int
    galactic_war_won: int
    guild_raid_won: int
    guild_contribution: int
    guild_exchange_donations: int
    season_full_clears: int
    season_successful_defends: int
    season_league_score: int
    season_undersized_squad_wins: int
    season_promotions_earned: int
    season_banners_earned: int
    season_offensive_battles_won: int
    season_territories_defeated: int
    url: str
    arena: ArenaSquad
    fleet_arena: ArenaSquad
    skill_rating: int
    league_name: str
    league_frame_image: str
    league_blank_image: str
    league_image: str
    division_number: int
    division_image: str
    portrait_image: str
    title: str
    guild_id: str
    guild_name: str
    guild_url: str
    mods: List[Any] = Field(default_factory=list)


class PlayerResponse(BaseModel):
    """Root response model containing player data, units, mods, and datacrons."""

    data: PlayerData
    units: List[PlayerUnit] = Field(default_factory=list)
    mods: List[Mod] = Field(default_factory=list)
    datacrons: List[Datacron] = Field(default_factory=list)


# ===== Gear/Equipment API Models =====


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


# ===== Guild Data Models =====


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


# ===== Grand Arena Championship (GAC) Models =====


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


# ===== GAC API Response Models =====


class GACBracketResponse(BaseModel):
    """Response model for GAC bracket API call."""

    data: GACBracket
    message: Optional[str] = None


class GACHistoryResponse(BaseModel):
    """Response model for GAC history API call."""

    data: GACHistory
    message: Optional[str] = None
