"""Journey Guide path analysis for individual player rosters."""

import json
import re
from pathlib import Path
from typing import Any

from .constants import (
    GEAR_WEIGHT,
    JOURNEY_GUIDE_REQUIREMENTS_FILENAME,
    RELIC_STAR_REQUIREMENTS,
    RELIC_WEIGHT,
    STAR_WEIGHT,
    UNOWNED_UNIT_PENALTY,
)
from .models import (
    AllExprV2,
    AnyExprV2,
    AtLeastExprV2,
    JourneyGuideSchemaV2,
    JourneyPathDefinition,
    JourneyPathReport,
    JourneyPathScore,
    JourneyRequirement,
    JourneyRequirementProgress,
    NoneExprV2,
    PlayerResponse,
    RefExprV2,
    RequirementExprV2,
    SelectorExprV2,
    SelectorRuleV2,
    Unit,
    UnitExprV2,
    UnitRuleV2,
    UnitsResponse,
)
from .progress_scorer import ProgressScorer
from .rote_proximity_analyzer import load_relic_costs


def _normalize_name(name: str) -> str:
    """Normalize names for resilient matching between data sources."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


class JourneyGuideAdvisor:
    """Ranks Journey Guide unlock paths by roster distance."""

    def __init__(self, requirements_path: Path | None = None):
        self.requirements_path = requirements_path or self._default_requirements_path()
        self.paths = self._load_requirements(self.requirements_path)
        self.relic_costs = load_relic_costs()
        self.scorer = ProgressScorer(
            relic_weight=RELIC_WEIGHT,
            gear_weight=GEAR_WEIGHT,
            star_weight=STAR_WEIGHT,
            relic_star_requirements=RELIC_STAR_REQUIREMENTS,
            relic_costs=self.relic_costs,
        )

    def analyze(
        self,
        player: PlayerResponse,
        units_data: UnitsResponse,
        target_gl: str | None = None,
        top_n: int = 3,
        include_unowned: bool = True,
    ) -> JourneyPathReport:
        """Analyze and rank Journey Guide paths for a player."""
        unit_index = self._build_unit_index(units_data.data)
        player_units = {u.data.base_id: u.data for u in player.units}
        candidate_paths = self._filter_paths(target_gl)
        scores = [
            self._score_path(path, unit_index, player_units, include_unowned)
            for path in candidate_paths
            if not self._player_owns(path, unit_index, player_units)
        ]
        ranked = sorted(
            scores,
            key=lambda s: (
                s.total_distance,
                s.total_requirements - s.completed_requirements,
                s.gl_name,
            ),
        )
        return JourneyPathReport(
            player_name=player.data.name,
            ally_code=player.data.ally_code,
            ranked_paths=ranked[:top_n],
        )

    def format_report(self, report: JourneyPathReport) -> str:
        """Render a concise command-line report."""
        lines = [
            "",
            "=" * 72,
            "Journey Guide Path Advisor",
            f"Player: {report.player_name} ({report.ally_code})",
            "=" * 72,
        ]
        if not report.ranked_paths:
            lines.append(
                "No paths available. Check your Journey Guide requirements data."
            )
            return "\n".join(lines)

        for idx, path in enumerate(report.ranked_paths, 1):
            lines.extend(self._format_path_block(idx, path))
        return "\n".join(lines).rstrip()

    def _format_path_block(self, rank: int, path: JourneyPathScore) -> list[str]:
        missing_count = path.total_requirements - path.completed_requirements
        header = (
            f"\n[{rank}] {path.gl_name}  "
            f"{path.completed_requirements}/{path.total_requirements} complete"
        )
        summary = (
            f"    Missing: {missing_count} | "
            f"Estimated distance: {path.total_distance:.1f}"
        )
        lines = [header, summary]
        completed_steps = [req for req in path.all_requirements if req.complete]
        if completed_steps:
            lines.append("    Already have:")
            for idx, req in enumerate(
                sorted(completed_steps, key=lambda r: r.unit_name), 1
            ):
                lines.append(f"    {idx}. {self._format_completed_requirement(req)}")
        if not path.missing_requirements:
            lines.append("    🎉 Ready to unlock!")
            return lines

        lines.append("    Unlock path (lowest weight first):")
        ordered_steps = sorted(
            path.missing_requirements,
            key=lambda r: (r.distance, r.unit_name),
        )
        for idx, req in enumerate(ordered_steps, 1):
            lines.append(f"    {idx}. {self._format_requirement(req)}")
        return lines

    def _format_completed_requirement(
        self, requirement: JourneyRequirementProgress
    ) -> str:
        target = self._format_target(requirement)
        current = self._format_current(requirement)
        return f"{requirement.unit_name}: {current} meets {target}"

    def _format_requirement(self, requirement: JourneyRequirementProgress) -> str:
        target = self._format_target(requirement)
        current = self._format_current(requirement)
        return (
            f"{requirement.unit_name}: {current} -> {target} "
            f"(weight {requirement.distance:.1f})"
        )

    def _format_target(self, requirement: JourneyRequirementProgress) -> str:
        if requirement.required_relic is not None:
            return f"R{requirement.required_relic}"
        if requirement.required_gear is not None:
            return f"G{requirement.required_gear}/{requirement.required_stars}*"
        return f"{requirement.required_stars}*"

    def _format_current(self, requirement: JourneyRequirementProgress) -> str:
        if not requirement.owned:
            return "unowned"
        if requirement.current_relic >= 0:
            return f"R{requirement.current_relic} ({requirement.current_stars}*)"
        return f"G{requirement.current_gear}/{requirement.current_stars}*"

    def _score_path(
        self,
        path: JourneyPathDefinition,
        unit_index: dict[str, Unit],
        player_units: dict[str, object],
        include_unowned: bool,
    ) -> JourneyPathScore:
        progress = [
            self._score_requirement(req, unit_index, player_units, include_unowned)
            for req in path.requirements
        ]
        completed = sum(1 for p in progress if p.complete)
        distance = sum(p.distance for p in progress if not p.complete)
        missing = [p for p in progress if not p.complete]
        return JourneyPathScore(
            gl_name=path.name,
            total_requirements=len(path.requirements),
            completed_requirements=completed,
            total_distance=distance,
            all_requirements=progress,
            missing_requirements=missing,
        )

    def _score_requirement(
        self,
        requirement: JourneyRequirement,
        unit_index: dict[str, Unit],
        player_units: dict[str, object],
        include_unowned: bool,
    ) -> JourneyRequirementProgress:
        if requirement.unit_id:
            player_unit = player_units.get(requirement.unit_id)
        else:
            unit = self._resolve_unit(requirement.unit_name, unit_index)
            player_unit = player_units.get(unit.base_id) if unit else None
        owned = player_unit is not None
        relic = getattr(player_unit, "relic_tier_or_minus_one", -1) if owned else -1
        gear = getattr(player_unit, "gear_level", 0) if owned else 0
        stars = getattr(player_unit, "rarity", 0) if owned else 0
        complete = self._is_requirement_complete(requirement, owned, relic, gear, stars)
        distance = self._requirement_distance(
            requirement,
            owned,
            relic,
            gear,
            stars,
            include_unowned,
        )
        return JourneyRequirementProgress(
            unit_name=requirement.unit_name,
            required_relic=requirement.required_relic,
            required_gear=requirement.required_gear,
            required_stars=requirement.required_stars,
            owned=owned,
            complete=complete,
            current_relic=relic,
            current_gear=gear,
            current_stars=stars,
            distance=0.0 if complete else distance,
        )

    def _is_requirement_complete(
        self,
        requirement: JourneyRequirement,
        owned: bool,
        relic: int,
        gear: int,
        stars: int,
    ) -> bool:
        if not owned:
            return False
        if stars < requirement.required_stars:
            return False
        if requirement.required_relic is not None:
            return relic >= requirement.required_relic
        if requirement.required_gear is not None:
            return gear >= requirement.required_gear
        return True

    def _requirement_distance(
        self,
        requirement: JourneyRequirement,
        owned: bool,
        relic: int,
        gear: int,
        stars: int,
        include_unowned: bool,
    ) -> float:
        if requirement.required_relic is not None:
            base = self.scorer.unit_distance(
                relic,
                max(gear, 1),
                stars,
                requirement.required_relic,
            )
        elif requirement.required_gear is not None:
            base = self.scorer.gear_distance(
                max(gear, 1),
                stars,
                requirement.required_gear,
                requirement.required_stars,
            )
        else:
            base = max(0, requirement.required_stars - stars) * STAR_WEIGHT

        if owned:
            return base
        penalty = UNOWNED_UNIT_PENALTY if include_unowned else UNOWNED_UNIT_PENALTY * 4
        return base + penalty

    def _player_owns(
        self,
        path: JourneyPathDefinition,
        unit_index: dict[str, Unit],
        player_units: dict[str, object],
    ) -> bool:
        if path.unit_id:
            return path.unit_id in player_units
        unit = self._resolve_unit(path.name, unit_index)
        if unit is None:
            return False
        return unit.base_id in player_units

    def _filter_paths(self, target_gl: str | None) -> list[JourneyPathDefinition]:
        if not target_gl:
            return self.paths
        normalized = _normalize_name(target_gl)
        matched = [p for p in self.paths if normalized in _normalize_name(p.name)]
        return matched

    def _resolve_unit(self, unit_name: str, unit_index: dict[str, Unit]) -> Unit | None:
        key = _normalize_name(unit_name)
        exact = unit_index.get(key)
        if exact is not None:
            return exact
        return next((unit for name, unit in unit_index.items() if key in name), None)

    def _build_unit_index(self, units: list[Unit]) -> dict[str, Unit]:
        index = {}
        for unit in units:
            index[_normalize_name(unit.name)] = unit
        return index

    def _load_requirements(self, path: Path) -> list[JourneyPathDefinition]:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return self._load_requirements_v2(data)

    def _load_requirements_v2(
        self, data: dict[str, Any]
    ) -> list[JourneyPathDefinition]:
        schema = JourneyGuideSchemaV2.model_validate(data)
        paths = []
        for target in schema.targets:
            requirements = self._extract_v2_requirements(schema, target.requirement)
            paths.append(
                JourneyPathDefinition(
                    unit_id=target.id,
                    name=target.name,
                    requirements=requirements,
                )
            )
        return paths

    def _extract_v2_requirements(
        self,
        schema: JourneyGuideSchemaV2,
        expression: RequirementExprV2,
    ) -> list[JourneyRequirement]:
        flattened = self._flatten_v2_expression(
            schema,
            expression,
            schema.defaults.stars,
            set(),
        )
        return self._dedupe_requirements(flattened)

    def _flatten_v2_expression(
        self,
        schema: JourneyGuideSchemaV2,
        expression: RequirementExprV2,
        default_stars: int,
        seen_refs: set[str],
    ) -> list[JourneyRequirement]:
        if isinstance(expression, UnitExprV2):
            return [
                self._unit_rule_to_requirement(schema, expression.unit, default_stars)
            ]
        if isinstance(expression, SelectorExprV2):
            return self._selector_rule_to_requirements(
                schema, expression.selector, default_stars
            )
        if isinstance(expression, RefExprV2):
            return self._resolve_ref_expression(
                schema, expression.ref, default_stars, seen_refs
            )
        if isinstance(expression, AtLeastExprV2):
            return self._flatten_expression_items(
                schema, expression.of, default_stars, seen_refs
            )
        if isinstance(expression, (AllExprV2, AnyExprV2, NoneExprV2)):
            return self._flatten_expression_items(
                schema, expression.items, default_stars, seen_refs
            )
        return []

    def _flatten_expression_items(
        self,
        schema: JourneyGuideSchemaV2,
        items: list[RequirementExprV2],
        default_stars: int,
        seen_refs: set[str],
    ) -> list[JourneyRequirement]:
        requirements: list[JourneyRequirement] = []
        for item in items:
            requirements.extend(
                self._flatten_v2_expression(schema, item, default_stars, seen_refs)
            )
        return requirements

    def _resolve_ref_expression(
        self,
        schema: JourneyGuideSchemaV2,
        ref: str,
        default_stars: int,
        seen_refs: set[str],
    ) -> list[JourneyRequirement]:
        if ref in seen_refs:
            return []
        ref_expression = schema.catalog.sets.get(ref)
        if ref_expression is None:
            return []
        next_refs = set(seen_refs)
        next_refs.add(ref)
        return self._flatten_v2_expression(
            schema,
            ref_expression,
            default_stars,
            next_refs,
        )

    def _unit_rule_to_requirement(
        self,
        schema: JourneyGuideSchemaV2,
        rule: UnitRuleV2,
        default_stars: int,
    ) -> JourneyRequirement:
        catalog_entry = schema.catalog.units.get(rule.id)
        min_stars = rule.min.stars if rule.min.stars is not None else default_stars
        unit_name = catalog_entry.name if catalog_entry is not None else rule.id
        return JourneyRequirement(
            unit_id=rule.id,
            unit_name=unit_name,
            required_relic=rule.min.relic,
            required_gear=rule.min.gear,
            required_stars=min_stars,
        )

    def _selector_rule_to_requirements(
        self,
        schema: JourneyGuideSchemaV2,
        rule: SelectorRuleV2,
        default_stars: int,
    ) -> list[JourneyRequirement]:
        requirements: list[JourneyRequirement] = []
        min_stars = (
            rule.min_each.stars if rule.min_each.stars is not None else default_stars
        )
        for unit_id in rule.filter.include_ids:
            catalog_entry = schema.catalog.units.get(unit_id)
            unit_name = catalog_entry.name if catalog_entry is not None else unit_id
            requirements.append(
                JourneyRequirement(
                    unit_id=unit_id,
                    unit_name=unit_name,
                    required_relic=rule.min_each.relic,
                    required_gear=rule.min_each.gear,
                    required_stars=min_stars,
                )
            )
        return requirements

    def _dedupe_requirements(
        self,
        requirements: list[JourneyRequirement],
    ) -> list[JourneyRequirement]:
        merged: dict[str, JourneyRequirement] = {}
        for requirement in requirements:
            key = requirement.unit_id or requirement.unit_name
            existing = merged.get(key)
            if existing is None:
                merged[key] = requirement
                continue
            existing.required_stars = max(
                existing.required_stars, requirement.required_stars
            )
            existing.required_relic = self._max_optional(
                existing.required_relic,
                requirement.required_relic,
            )
            existing.required_gear = self._max_optional(
                existing.required_gear,
                requirement.required_gear,
            )
        return list(merged.values())

    def _max_optional(self, left: int | None, right: int | None) -> int | None:
        if left is None:
            return right
        if right is None:
            return left
        return max(left, right)

    def _default_requirements_path(self) -> Path:
        return (
            Path(__file__).parent.parent.parent
            / "data"
            / JOURNEY_GUIDE_REQUIREMENTS_FILENAME
        )
