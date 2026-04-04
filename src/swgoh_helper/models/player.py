"""
Pydantic models for SWGOH player data.
"""

from typing import List, Optional, Dict
from pydantic import BaseModel, Field


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

    @staticmethod
    def api_to_ui_relic_tier(api_relic_tier: Optional[int]) -> Optional[int]:
        """Convert SWGOH API relic_tier encoding to UI relic level (R1-R9)."""
        if api_relic_tier is None or api_relic_tier < 3:
            return None
        return api_relic_tier - 2

    @property
    def relic_tier_ui(self) -> Optional[int]:
        """UI relic level (R1-R9), or None for non-reliced characters."""
        return self.api_to_ui_relic_tier(self.relic_tier)

    @property
    def relic_tier_or_minus_one(self) -> int:
        """UI relic level or -1 sentinel for non-reliced characters."""
        ui_relic = self.relic_tier_ui
        return ui_relic if ui_relic is not None else -1


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


class PlayerResponse(BaseModel):
    """Root response model containing player data, units, mods, and datacrons."""

    data: PlayerData
    units: List[PlayerUnit] = Field(default_factory=list)
    mods: List[Mod] = Field(default_factory=list)
    datacrons: List[Datacron] = Field(default_factory=list)
