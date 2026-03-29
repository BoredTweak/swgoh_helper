# SWGOH Helper package

from .models import (
    # Enums
    GACFormat,
    GACLeague,
    # GAC Models
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

from .data_access import (
    SwgohDataService,
    BaseApiClient,
    BaseRepository,
    AbilitiesRepository,
    GearRepository,
    GuildsRepository,
    PlayersRepository,
    StatDefinitionsRepository,
    UnitsRepository,
)

from .rote_proximity_analyzer import (
    ProximityAnalyzer,
    ProgressStage,
    PlayerProgress,
    GapProximityReport,
)

__all__ = [
    # Data Access Layer
    "SwgohDataService",
    "BaseApiClient",
    "BaseRepository",
    "AbilitiesRepository",
    "GearRepository",
    "GuildsRepository",
    "PlayersRepository",
    "StatDefinitionsRepository",
    "UnitsRepository",
    # Enums
    "GACFormat",
    "GACLeague",
    # GAC Models
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
    # ROTE Proximity Analyzer
    "ProximityAnalyzer",
    "ProgressStage",
    "PlayerProgress",
    "GapProximityReport",
]
