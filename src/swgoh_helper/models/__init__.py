"""
Pydantic models for SWGOH data schemas.

This module re-exports all models for backward compatibility.
Models are organized into submodules:
- enums: CombatType, GACFormat, GACLeague, RoteOutputFormat
- units: Unit, GearTier, UnitsResponse
- player: PlayerResponse, PlayerData, PlayerUnit, UnitData, etc.
- gear: GearPiece, GearIngredient, GearRecipe, GearResponse
- guild: GuildResponse, GuildData, GuildMember
- gac: GAC-related models
- rote: ROTE Territory Battle models
"""

# Enums
from .enums import (
    CombatType,
    GACFormat,
    GACLeague,
    RoteOutputFormat,
    VALID_ROTE_OUTPUT_FORMATS,
)

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

# Journey Guide Pathing
from .journey_guide import (
    AllExprV2,
    AnyExprV2,
    AtLeastExprV2,
    JourneyGuideCatalogV2,
    JourneyGuideDefaultsV2,
    JourneyGuideSchemaV2,
    JourneyRequirement,
    JourneyPathDefinition,
    JourneyRequirementProgress,
    JourneyPathScore,
    JourneyPathReport,
    JourneyTargetV2,
    MinSpecV2,
    NoneExprV2,
    RefExprV2,
    RequirementExprV2,
    ScoringHintsV2,
    SelectorExprV2,
    SelectorRuleV2,
    UnitExprV2,
    UnitFilterV2,
    UnitRuleV2,
)

__all__ = [
    # Enums
    "CombatType",
    "GACFormat",
    "GACLeague",
    "RoteOutputFormat",
    "VALID_ROTE_OUTPUT_FORMATS",
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
    # Journey Guide Pathing
    "JourneyRequirement",
    "JourneyPathDefinition",
    "JourneyRequirementProgress",
    "JourneyPathScore",
    "JourneyPathReport",
    # Journey Guide Requirements Schema V2
    "AllExprV2",
    "AnyExprV2",
    "AtLeastExprV2",
    "JourneyGuideCatalogV2",
    "JourneyGuideDefaultsV2",
    "JourneyGuideSchemaV2",
    "JourneyTargetV2",
    "MinSpecV2",
    "NoneExprV2",
    "RefExprV2",
    "RequirementExprV2",
    "ScoringHintsV2",
    "SelectorExprV2",
    "SelectorRuleV2",
    "UnitExprV2",
    "UnitFilterV2",
    "UnitRuleV2",
]
