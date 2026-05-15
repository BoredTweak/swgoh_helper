"""Pydantic models for Journey Guide path planning and schema v2."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, Field


class JourneyRequirement(BaseModel):
    """A single prerequisite for unlocking a journey guide character."""

    unit_id: Optional[str] = None
    unit_name: str
    required_relic: Optional[int] = None
    required_gear: Optional[int] = None
    required_stars: int = 7


class JourneyPathDefinition(BaseModel):
    """Requirement set for one journey guide character."""

    unit_id: Optional[str] = None
    name: str
    requirements: list[JourneyRequirement] = Field(default_factory=list)


class JourneyRequirementProgress(BaseModel):
    """Current player progress for one requirement."""

    unit_name: str
    required_relic: Optional[int] = None
    required_gear: Optional[int] = None
    required_stars: int = 7
    owned: bool
    complete: bool
    current_relic: int = -1
    current_gear: int = 0
    current_stars: int = 0
    distance: float


class JourneyPathScore(BaseModel):
    """Aggregated score for one Journey Guide unlock path."""

    gl_name: str
    total_requirements: int
    completed_requirements: int
    total_distance: float
    all_requirements: list[JourneyRequirementProgress] = Field(default_factory=list)
    missing_requirements: list[JourneyRequirementProgress] = Field(default_factory=list)


class JourneyPathReport(BaseModel):
    """Top-ranked Journey Guide paths for one player."""

    player_name: str
    ally_code: int
    ranked_paths: list[JourneyPathScore] = Field(default_factory=list)


class JourneyGuideDefaultsV2(BaseModel):
    """Default requirement values used when a target omits a field."""

    stars: int = Field(default=7, ge=1, le=7)


class MinSpecV2(BaseModel):
    """Minimum progression requirements for a unit."""

    stars: int | None = Field(default=None, ge=1, le=7)
    gear: int | None = Field(default=None, ge=1, le=13)
    relic: int | None = Field(default=None, ge=0, le=15)
    level: int | None = Field(default=None, ge=1, le=90)
    power: int | None = Field(default=None, ge=0)
    gp: int | None = Field(default=None, ge=0)
    zetas: int | None = Field(default=None, ge=0)
    omicrons: int | None = Field(default=None, ge=0)
    mods_6dot_count: int | None = Field(default=None, ge=0)
    ability_tiers: dict[str, int] = Field(default_factory=dict)
    custom: dict[str, int | float | str | bool] = Field(default_factory=dict)


class UnitFilterV2(BaseModel):
    """Filter criteria used by pooled selector requirements."""

    include_ids: list[str] = Field(default_factory=list)
    exclude_ids: list[str] = Field(default_factory=list)
    tags_any: list[str] = Field(default_factory=list)
    tags_all: list[str] = Field(default_factory=list)
    unit_type: Literal["character", "ship", "capital_ship"] | None = None


class UnitRuleV2(BaseModel):
    """Requirement rule for one specific unit id."""

    id: str
    min: MinSpecV2 = Field(default_factory=MinSpecV2)


class SelectorRuleV2(BaseModel):
    """Requirement rule for matching a count of units in a filter."""

    filter: UnitFilterV2
    count: int = Field(ge=1)
    min_each: MinSpecV2 = Field(default_factory=MinSpecV2)


class AllExprV2(BaseModel):
    """All child expressions must pass."""

    type: Literal["all"]
    items: list[RequirementExprV2]


class AnyExprV2(BaseModel):
    """At least one child expression must pass."""

    type: Literal["any"]
    items: list[RequirementExprV2]


class AtLeastExprV2(BaseModel):
    """A minimum count of child expressions must pass."""

    type: Literal["at_least"]
    count: int = Field(ge=1)
    of: list[RequirementExprV2]


class NoneExprV2(BaseModel):
    """No child expression may pass."""

    type: Literal["none"]
    items: list[RequirementExprV2]


class RefExprV2(BaseModel):
    """Reference a reusable requirement set by id."""

    type: Literal["ref"]
    ref: str


class UnitExprV2(BaseModel):
    """Leaf expression for a single unit requirement."""

    type: Literal["unit"]
    unit: UnitRuleV2


class SelectorExprV2(BaseModel):
    """Leaf expression for a pooled selector requirement."""

    type: Literal["selector"]
    selector: SelectorRuleV2


RequirementExprV2 = Annotated[
    AllExprV2
    | AnyExprV2
    | AtLeastExprV2
    | NoneExprV2
    | RefExprV2
    | UnitExprV2
    | SelectorExprV2,
    Field(discriminator="type"),
]


class UnitCatalogEntryV2(BaseModel):
    """Optional catalog metadata for a known game unit."""

    id: str
    name: str
    unit_type: Literal["character", "ship", "capital_ship"] | None = None
    tags: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)


class TagCatalogEntryV2(BaseModel):
    """Optional tag metadata to document intent and maintenance."""

    id: str
    name: str
    notes: str | None = None


class JourneyGuideCatalogV2(BaseModel):
    """Reusable schema catalog for units, tags, and requirement sets."""

    units: dict[str, UnitCatalogEntryV2] = Field(default_factory=dict)
    tags: dict[str, TagCatalogEntryV2] = Field(default_factory=dict)
    sets: dict[str, RequirementExprV2] = Field(default_factory=dict)


class ScoreWeightsV2(BaseModel):
    """Optional scoring weights for path distance calculations."""

    stars: float = Field(default=1.0, ge=0.0)
    gear: float = Field(default=2.0, ge=0.0)
    relic: float = Field(default=3.0, ge=0.0)
    unowned_penalty: float = Field(default=15.0, ge=0.0)


class ScorePriorityOverrideV2(BaseModel):
    """Optional per-unit scoring priority adjustment."""

    unit_id: str
    priority: float = Field(default=1.0, ge=0.0)


class ScoringHintsV2(BaseModel):
    """Optional scoring hints consumed by a path-ranking engine."""

    weights: ScoreWeightsV2 = Field(default_factory=ScoreWeightsV2)
    priority_overrides: list[ScorePriorityOverrideV2] = Field(default_factory=list)


class JourneyTargetUiV2(BaseModel):
    """Optional UI metadata for display and grouping."""

    icon: str | None = None
    short_name: str | None = None
    labels: list[str] = Field(default_factory=list)


class JourneyTargetV2(BaseModel):
    """A Journey Guide unlock target with an expression-based requirement."""

    id: str
    name: str
    kind: str
    requirement: RequirementExprV2
    scoring: ScoringHintsV2 | None = None
    ui: JourneyTargetUiV2 | None = None
    release_order: int | None = Field(default=None, ge=1)
    is_time_limited: bool | None = None
    source_urls: list[str] = Field(default_factory=list)
    notes: str | None = None
    aliases: list[str] = Field(default_factory=list)


class JourneyGuideSchemaV2(BaseModel):
    """Top-level schema for flexible Journey Guide requirements data."""

    schema_version: str
    updated_at: date
    defaults: JourneyGuideDefaultsV2 = Field(default_factory=JourneyGuideDefaultsV2)
    catalog: JourneyGuideCatalogV2 = Field(default_factory=JourneyGuideCatalogV2)
    targets: list[JourneyTargetV2] = Field(default_factory=list)


AllExprV2.model_rebuild()
AnyExprV2.model_rebuild()
AtLeastExprV2.model_rebuild()
NoneExprV2.model_rebuild()
