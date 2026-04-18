"""Tests for ROTE presenter owner output."""

from swgoh_helper.models import CombatType
from swgoh_helper.models.rote import (
    CoverageMatrix,
    PlayerUnitInfo,
    RotePath,
    SimpleRoteRequirements,
    UnitType,
    UnitCoverage,
    UnitRequirement,
)
from swgoh_helper.rote_bottleneck_analyzer import BottleneckAnalyzer
from swgoh_helper.rote_coverage import CoverageAnalyzer
from swgoh_helper.rote_gap_analyzer import GapAnalyzer
from swgoh_helper.rote_presenter import RotePresenter


def test_output_format_owners_groups_requirements_by_territory():
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
            UnitRequirement(
                unit_id="TARKIN",
                unit_name="Grand Moff Tarkin",
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
        output_format="owners",
    )

    assert "**Requirement Owners**" in output
    assert "P1 Mustafar:" in output
    assert "- Darth Vader R7 x2: Alpha, Beta" in output
    assert "- Grand Admiral Thrawn R5: (none)" in output


def test_output_format_gaps_only_shows_gap_sections():
    """Presenter should support rendering only gap-related sections."""
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
            )
        ],
    )
    matrix = CoverageMatrix(
        guild_name="Test Guild",
        guild_id="guild-1",
        member_count=1,
        units={
            "VADER": UnitCoverage(
                unit_id="VADER",
                unit_name="Darth Vader",
                alignment=2,
                combat_type=CombatType.CHARACTER,
                players_by_relic={7: []},
            )
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
        output_format="gaps",
    )

    assert "**Gaps**" in output
    assert "**Coverage**" not in output


def test_output_format_coverage_only_shows_coverage_section():
    """Presenter should support rendering only coverage sections."""
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
            )
        ],
    )
    matrix = CoverageMatrix(
        guild_name="Test Guild",
        guild_id="guild-1",
        member_count=1,
        units={
            "VADER": UnitCoverage(
                unit_id="VADER",
                unit_name="Darth Vader",
                alignment=2,
                combat_type=CombatType.CHARACTER,
                players_by_relic={7: []},
            )
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
        output_format="coverage",
    )

    assert "**Coverage**" in output
    assert "**Gaps**" not in output


def test_output_format_gaps_includes_noncritical_unfillable_gaps():
    """Gaps view should include unfillable warning gaps, not just critical gaps."""
    requirements = SimpleRoteRequirements(
        last_updated="2026-04-01",
        requirements=[
            UnitRequirement(
                unit_id="MTALZIN",
                unit_name="Mother Talzin",
                min_relic=7,
                path=RotePath.DARK_SIDE,
                territory="Dathomir",
                count=5,
            )
        ],
    )
    matrix = CoverageMatrix(
        guild_name="Test Guild",
        guild_id="guild-1",
        member_count=10,
        units={
            "MTALZIN": UnitCoverage(
                unit_id="MTALZIN",
                unit_name="Mother Talzin",
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
                            relic_tier=7,
                        ),
                        PlayerUnitInfo(
                            player_name="Gamma",
                            ally_code=333333333,
                            relic_tier=7,
                        ),
                        PlayerUnitInfo(
                            player_name="Delta",
                            ally_code=444444444,
                            relic_tier=7,
                        ),
                    ]
                },
            )
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
        output_format="gaps",
    )

    assert "P3 Dathomir:" in output
    assert "- Mother Talzin R7: 4/5 (Alpha, Beta, Gamma, Delta)" in output


def test_output_format_mine_groups_requester_coverage_by_territory():
    """Mine view should show requirements requester can cover grouped by territory."""
    requirements = SimpleRoteRequirements(
        last_updated="2026-04-01",
        requirements=[
            UnitRequirement(
                unit_id="VADER",
                unit_name="Darth Vader",
                min_relic=7,
                path=RotePath.DARK_SIDE,
                territory="Mustafar",
                count=1,
            ),
            UnitRequirement(
                unit_id="THRAWN",
                unit_name="Grand Admiral Thrawn",
                min_relic=5,
                path=RotePath.DARK_SIDE,
                territory="Mustafar",
                count=1,
            ),
            UnitRequirement(
                unit_id="TARKIN",
                unit_name="Grand Moff Tarkin",
                min_relic=5,
                path=RotePath.DARK_SIDE,
                territory="Coruscant",
                count=1,
            ),
            UnitRequirement(
                unit_id="EPALPATINE",
                unit_name="Emperor Palpatine",
                min_relic=6,
                path=RotePath.DARK_SIDE,
                territory="Coruscant",
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
                        )
                    ]
                },
            ),
            "THRAWN": UnitCoverage(
                unit_id="THRAWN",
                unit_name="Grand Admiral Thrawn",
                alignment=2,
                combat_type=CombatType.CHARACTER,
                players_by_relic={
                    5: [
                        PlayerUnitInfo(
                            player_name="Alpha",
                            ally_code=111111111,
                            relic_tier=5,
                        ),
                        PlayerUnitInfo(
                            player_name="Beta",
                            ally_code=222222222,
                            relic_tier=6,
                        ),
                    ]
                },
            ),
            "TARKIN": UnitCoverage(
                unit_id="TARKIN",
                unit_name="Grand Moff Tarkin",
                alignment=2,
                combat_type=CombatType.CHARACTER,
                players_by_relic={
                    5: [
                        PlayerUnitInfo(
                            player_name="Gamma",
                            ally_code=333333333,
                            relic_tier=5,
                        )
                    ]
                },
            ),
            "EPALPATINE": UnitCoverage(
                unit_id="EPALPATINE",
                unit_name="Emperor Palpatine",
                alignment=2,
                combat_type=CombatType.CHARACTER,
                players_by_relic={
                    6: [
                        PlayerUnitInfo(
                            player_name="Beta",
                            ally_code=222222222,
                            relic_tier=6,
                        )
                    ]
                },
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
        output_format="mine",
        requester_ally_code=111111111,
    )

    assert "**Your Planet Coverage**" in output
    assert "P1 Mustafar:" in output
    assert "You own **2/2** at the required levels." in output
    assert "- Darth Vader R7" in output
    assert "- Grand Admiral Thrawn R5" in output
    assert "- Grand Moff Tarkin R5" not in output
    assert "- Emperor Palpatine R6" not in output


def test_output_format_mine_shows_success_when_no_qualifying_requirements():
    """Mine view should report when requester cannot cover any requirements."""
    requirements = SimpleRoteRequirements(
        last_updated="2026-04-01",
        requirements=[
            UnitRequirement(
                unit_id="THRAWN",
                unit_name="Grand Admiral Thrawn",
                min_relic=5,
                path=RotePath.DARK_SIDE,
                territory="Mustafar",
                count=1,
            )
        ],
    )
    matrix = CoverageMatrix(
        guild_name="Test Guild",
        guild_id="guild-1",
        member_count=2,
        units={
            "THRAWN": UnitCoverage(
                unit_id="THRAWN",
                unit_name="Grand Admiral Thrawn",
                alignment=2,
                combat_type=CombatType.CHARACTER,
                players_by_relic={
                    5: [
                        PlayerUnitInfo(
                            player_name="Alpha",
                            ally_code=111111111,
                            relic_tier=5,
                        ),
                        PlayerUnitInfo(
                            player_name="Beta",
                            ally_code=222222222,
                            relic_tier=5,
                        ),
                    ]
                },
            )
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
        output_format="mine",
        requester_ally_code=333333333,
    )

    assert "You do not currently qualify for any platoon requirements." in output


def test_output_format_mine_adds_limited_availability_callout():
    """Mine view should call out units with low owner counts."""
    requirements = SimpleRoteRequirements(
        last_updated="2026-04-01",
        requirements=[
            UnitRequirement(
                unit_id="VADER",
                unit_name="Darth Vader",
                min_relic=7,
                path=RotePath.DARK_SIDE,
                territory="Mustafar",
                count=1,
            ),
            UnitRequirement(
                unit_id="THRAWN",
                unit_name="Grand Admiral Thrawn",
                min_relic=5,
                path=RotePath.DARK_SIDE,
                territory="Mustafar",
                count=1,
            ),
            UnitRequirement(
                unit_id="TARKIN",
                unit_name="Grand Moff Tarkin",
                min_relic=5,
                path=RotePath.DARK_SIDE,
                territory="Mustafar",
                count=1,
            ),
            UnitRequirement(
                unit_id="MILLENNIUMFALCON",
                unit_name="Millennium Falcon",
                min_relic=7,
                path=RotePath.DARK_SIDE,
                territory="Mustafar",
                count=1,
                unit_type=UnitType.SHIP,
            ),
        ],
    )
    matrix = CoverageMatrix(
        guild_name="Test Guild",
        guild_id="guild-1",
        member_count=6,
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
                            relic_tier=7,
                        ),
                        PlayerUnitInfo(
                            player_name="Gamma",
                            ally_code=333333333,
                            relic_tier=7,
                        ),
                        PlayerUnitInfo(
                            player_name="Delta",
                            ally_code=444444444,
                            relic_tier=7,
                        ),
                    ]
                },
            ),
            "THRAWN": UnitCoverage(
                unit_id="THRAWN",
                unit_name="Grand Admiral Thrawn",
                alignment=2,
                combat_type=CombatType.CHARACTER,
                players_by_relic={
                    5: [
                        PlayerUnitInfo(
                            player_name="Alpha",
                            ally_code=111111111,
                            relic_tier=5,
                        ),
                        PlayerUnitInfo(
                            player_name="Beta",
                            ally_code=222222222,
                            relic_tier=5,
                        ),
                        PlayerUnitInfo(
                            player_name="Gamma",
                            ally_code=333333333,
                            relic_tier=5,
                        ),
                        PlayerUnitInfo(
                            player_name="Delta",
                            ally_code=444444444,
                            relic_tier=5,
                        ),
                        PlayerUnitInfo(
                            player_name="Epsilon",
                            ally_code=555555555,
                            relic_tier=5,
                        ),
                    ]
                },
            ),
            "TARKIN": UnitCoverage(
                unit_id="TARKIN",
                unit_name="Grand Moff Tarkin",
                alignment=2,
                combat_type=CombatType.CHARACTER,
                players_by_relic={
                    5: [
                        PlayerUnitInfo(
                            player_name="Alpha",
                            ally_code=111111111,
                            relic_tier=5,
                        )
                    ]
                },
            ),
            "MILLENNIUMFALCON": UnitCoverage(
                unit_id="MILLENNIUMFALCON",
                unit_name="Millennium Falcon",
                alignment=2,
                combat_type=CombatType.SHIP,
                players_by_relic={
                    7: [
                        PlayerUnitInfo(
                            player_name="Alpha",
                            ally_code=111111111,
                            relic_tier=7,
                            rarity=7,
                        )
                    ]
                },
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
        output_format="mine",
        requester_ally_code=111111111,
    )

    assert (
        "You own **3/3** characters and **1/1** ships at the required levels." in output
    )
    assert (
        "- Darth Vader R7 **You are one of only 4 players that own this unit "
        "at the required level**" in output
    )
    assert (
        "- Grand Moff Tarkin R5 "
        "**PRIORITY DEPLOY: You are the only player that owns this unit at the required level**"
        in output
    )
    assert (
        "- Millennium Falcon 7* **PRIORITY DEPLOY: You are the only player that owns this unit"
        in output
    )
    assert "- Grand Admiral Thrawn R5 **You are one of only" not in output


def test_output_format_mine_sorts_scarcest_units_first_within_territory():
    """Mine view should sort sole-owner and scarcer units first for deploy priority."""
    requirements = SimpleRoteRequirements(
        last_updated="2026-04-01",
        requirements=[
            UnitRequirement(
                unit_id="A",
                unit_name="Unit A",
                min_relic=7,
                path=RotePath.DARK_SIDE,
                territory="Mustafar",
                count=1,
            ),
            UnitRequirement(
                unit_id="B",
                unit_name="Unit B",
                min_relic=7,
                path=RotePath.DARK_SIDE,
                territory="Mustafar",
                count=1,
            ),
            UnitRequirement(
                unit_id="C",
                unit_name="Unit C",
                min_relic=7,
                path=RotePath.DARK_SIDE,
                territory="Mustafar",
                count=1,
            ),
        ],
    )
    matrix = CoverageMatrix(
        guild_name="Test Guild",
        guild_id="guild-1",
        member_count=5,
        units={
            "A": UnitCoverage(
                unit_id="A",
                unit_name="Unit A",
                alignment=2,
                combat_type=CombatType.CHARACTER,
                players_by_relic={
                    7: [
                        PlayerUnitInfo(
                            player_name="Alpha", ally_code=111111111, relic_tier=7
                        )
                    ]
                },
            ),
            "B": UnitCoverage(
                unit_id="B",
                unit_name="Unit B",
                alignment=2,
                combat_type=CombatType.CHARACTER,
                players_by_relic={
                    7: [
                        PlayerUnitInfo(
                            player_name="Alpha", ally_code=111111111, relic_tier=7
                        ),
                        PlayerUnitInfo(
                            player_name="Beta", ally_code=222222222, relic_tier=7
                        ),
                    ]
                },
            ),
            "C": UnitCoverage(
                unit_id="C",
                unit_name="Unit C",
                alignment=2,
                combat_type=CombatType.CHARACTER,
                players_by_relic={
                    7: [
                        PlayerUnitInfo(
                            player_name="Alpha", ally_code=111111111, relic_tier=7
                        ),
                        PlayerUnitInfo(
                            player_name="Beta", ally_code=222222222, relic_tier=7
                        ),
                        PlayerUnitInfo(
                            player_name="Gamma", ally_code=333333333, relic_tier=7
                        ),
                    ]
                },
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
        output_format="mine",
        requester_ally_code=111111111,
    )

    idx_a = output.index("- Unit A R7")
    idx_b = output.index("- Unit B R7")
    idx_c = output.index("- Unit C R7")
    assert idx_a < idx_b < idx_c


def test_output_format_mine_uses_unique_character_requirements_per_planet():
    """Mine ratio should count unique character requirements per planet."""
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
                unit_id="VADER",
                unit_name="Darth Vader",
                min_relic=8,
                path=RotePath.DARK_SIDE,
                territory="Mustafar",
                count=1,
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
        member_count=2,
        units={
            "VADER": UnitCoverage(
                unit_id="VADER",
                unit_name="Darth Vader",
                alignment=2,
                combat_type=CombatType.CHARACTER,
                players_by_relic={
                    8: [
                        PlayerUnitInfo(
                            player_name="Alpha",
                            ally_code=111111111,
                            relic_tier=8,
                        )
                    ]
                },
            ),
            "THRAWN": UnitCoverage(
                unit_id="THRAWN",
                unit_name="Grand Admiral Thrawn",
                alignment=2,
                combat_type=CombatType.CHARACTER,
                players_by_relic={
                    5: [
                        PlayerUnitInfo(
                            player_name="Alpha",
                            ally_code=111111111,
                            relic_tier=5,
                        )
                    ]
                },
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
        output_format="mine",
        requester_ally_code=111111111,
    )

    assert "You own **2/2** at the required levels." in output
