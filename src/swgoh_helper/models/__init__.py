"""
Pydantic models for SWGOH data schemas.

This module re-exports all models for backward compatibility.
Models are organized into submodules:
- enums: GACFormat, GACLeague
- units: Unit, GearTier, UnitsResponse
- player: PlayerResponse, PlayerData, PlayerUnit, UnitData, etc.
- gear: GearPiece, GearIngredient, GearRecipe, GearResponse
- guild: GuildResponse, GuildData, GuildMember
- gac: GAC-related models
- rote: ROTE Territory Battle models
"""

# Enums
from .enums import CombatType, GACFormat, GACLeague

# Units
from .units import GearTier, Unit, UnitsResponse

# Player
from .player import (
    ArenaSquad,
    GearSlot,
    AbilityData,
    UnitData,
    PlayerUnit,
    ModSecondaryStat,
    ModPrimaryStat,
    Mod,
    DatacronTier,
    Datacron,
    PlayerData,
    PlayerResponse,
)

# Gear
from .gear import GearIngredient, GearRecipe, GearPiece, GearResponse

# Guild
from .guild import GuildMember, GuildData, GuildResponse

# GAC
from .gac import (
    GACSquadUnit,
    GACSquad,
    GACBattle,
    GACTerritory,
    GACRoundResult,
    GACBracketPlayer,
    GACBracket,
    GACSeasonEvent,
    GACHistory,
    GACMatchAnalysis,
    GACBracketResponse,
    GACHistoryResponse,
)

# ROTE
from .rote import (
    RotePath,
    UnitType,
    GapSeverity,
    ProgressStage,
    UnitRequirement,
    SimpleRoteRequirements,
    PlayerUnitInfo,
    UnitCoverage,
    CoverageMatrix,
    RequirementCoverage,
    PlatoonGap,
    UnicornUnit,
    PlayerProgress,
    GapProximityReport,
    UnitRecommendation,
    TerritoryRecommendation,
    PlayerUnitStatus,
    PlayerDistance,
    BonusZoneReadiness,
    PrereqStatus,
    UnitProgressStatus,
)

# Abilities
from .abilities import Ability, AbilitiesResponse

# Ships
from .ships import Ship, ShipsResponse

# Characters
from .characters import Character, CharactersResponse

# Stat Definitions
from .stats import StatDefinition

# Kyrotech
from .kyrotech import CharacterKyrotechResult

__all__ = [
    # Enums
    "CombatType",
    "GACFormat",
    "GACLeague",
    # Units
    "GearTier",
    "Unit",
    "UnitsResponse",
    # Player
    "ArenaSquad",
    "GearSlot",
    "AbilityData",
    "UnitData",
    "PlayerUnit",
    "ModSecondaryStat",
    "ModPrimaryStat",
    "Mod",
    "DatacronTier",
    "Datacron",
    "PlayerData",
    "PlayerResponse",
    # Gear
    "GearIngredient",
    "GearRecipe",
    "GearPiece",
    "GearResponse",
    # Guild
    "GuildMember",
    "GuildData",
    "GuildResponse",
    # GAC
    "GACSquadUnit",
    "GACSquad",
    "GACBattle",
    "GACTerritory",
    "GACRoundResult",
    "GACBracketPlayer",
    "GACBracket",
    "GACSeasonEvent",
    "GACHistory",
    "GACMatchAnalysis",
    "GACBracketResponse",
    "GACHistoryResponse",
    # ROTE
    "RotePath",
    "UnitType",
    "GapSeverity",
    "ProgressStage",
    "UnitRequirement",
    "SimpleRoteRequirements",
    "PlayerUnitInfo",
    "UnitCoverage",
    "CoverageMatrix",
    "RequirementCoverage",
    "PlatoonGap",
    "UnicornUnit",
    "PlayerProgress",
    "GapProximityReport",
    "UnitRecommendation",
    "TerritoryRecommendation",
    "PlayerUnitStatus",
    "PlayerDistance",
    "BonusZoneReadiness",
    "PrereqStatus",
    "UnitProgressStatus",
    # Abilities
    "Ability",
    "AbilitiesResponse",
    # Ships
    "Ship",
    "ShipsResponse",
    # Characters
    "Character",
    "CharactersResponse",
    # Stat Definitions
    "StatDefinition",
    # Kyrotech
    "CharacterKyrotechResult",
]
