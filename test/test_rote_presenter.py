"""Tests for ROTE presenter owner output."""

from swgoh_helper.models import CombatType
from swgoh_helper.models.rote import (
    CoverageMatrix,
    PlayerUnitInfo,
    RotePath,
    SimpleRoteRequirements,
    UnitCoverage,
    UnitRequirement,
)
from swgoh_helper.rote_bottleneck_analyzer import BottleneckAnalyzer
from swgoh_helper.rote_coverage import CoverageAnalyzer
from swgoh_helper.rote_gap_analyzer import GapAnalyzer
from swgoh_helper.rote_presenter import RotePresenter


def test_show_owners_groups_requirements_by_territory():
    """Presenter should list qualifying owners under each territory."""
    requirements = SimpleRoteRequirements(
        last_updated="2026-04-01",
        requirements=[
            UnitRequirement(
                unit_id="VADER",
                unit_name="Darth Vader",
                min_relic=7,
                path=RotePath.DARK_SIDE,
                territory="Mustafar",
                count=2,
            ),
            UnitRequirement(
                unit_id="THRAWN",
                unit_name="Grand Admiral Thrawn",
                min_relic=5,
                path=RotePath.DARK_SIDE,
                territory="Mustafar",
                count=1,
            ),
        ],
    )
    matrix = CoverageMatrix(
        guild_name="Test Guild",
        guild_id="guild-1",
        member_count=3,
        units={
            "VADER": UnitCoverage(
                unit_id="VADER",
                unit_name="Darth Vader",
                alignment=2,
                combat_type=CombatType.CHARACTER,
                players_by_relic={
                    7: [
                        PlayerUnitInfo(
                            player_name="Alpha",
                            ally_code=111111111,
                            relic_tier=7,
                        ),
                        PlayerUnitInfo(
                            player_name="Beta",
                            ally_code=222222222,
                            relic_tier=8,
                        ),
                    ]
                },
            ),
            "THRAWN": UnitCoverage(
                unit_id="THRAWN",
                unit_name="Grand Admiral Thrawn",
                alignment=2,
                combat_type=CombatType.CHARACTER,
                players_by_relic={5: []},
            ),
        },
    )
    analyzer = CoverageAnalyzer(matrix, requirements)
    gap_analyzer = GapAnalyzer(matrix, requirements)
    bottleneck_analyzer = BottleneckAnalyzer(matrix, requirements)

    output = RotePresenter().format_results(
        analyzer,
        matrix,
        gap_analyzer,
        bottleneck_analyzer,
        show_owners=True,
    )

    assert "**Requirement Owners**" in output
    assert "P1 Mustafar:" in output
    assert "- Darth Vader R7 x2: Alpha, Beta" in output
    assert "- Grand Admiral Thrawn R5: (none)" in output
