"""
Pydantic models for SWGOH data schemas (units and player data).
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


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
