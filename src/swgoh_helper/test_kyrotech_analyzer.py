"""
Unit tests for kyrotech_analyzer module.
"""

import unittest
from swgoh_helper.kyrotech_analyzer import (
    KyrotechAnalyzer,
    RosterAnalyzer,
    MAX_GEAR_TIER,
)
from swgoh_helper.models import (
    GearPiece,
    GearIngredient,
    GearTier,
    Unit,
    PlayerUnit,
    UnitData,
    GearSlot,
)


class TestKyrotechAnalyzer(unittest.TestCase):
    """Test cases for KyrotechAnalyzer class."""

    def setUp(self):
        """Set up test fixtures with mock gear data."""
        # Create mock gear pieces
        self.gear_lookup = {
            # Kyrotech salvage pieces (base materials)
            "172Salvage": GearPiece(
                base_id="172Salvage",
                name="Mk 7 Kyrotech Shock Prod Prototype Salvage",
                tier=7,
                mark="Mk VII",
                required_level=1,
                cost=0,
                image="",
                url="",
                recipes=[],
                ingredients=[],
                stats={},
            ),
            "173Salvage": GearPiece(
                base_id="173Salvage",
                name="Mk 9 Kyrotech Battle Computer Prototype Salvage",
                tier=9,
                mark="Mk IX",
                required_level=1,
                cost=0,
                image="",
                url="",
                recipes=[],
                ingredients=[],
                stats={},
            ),
            # Prototype pieces that require kyrotech salvage
            "172Prototype": GearPiece(
                base_id="172Prototype",
                name="Mk 7 Kyrotech Shock Prod Prototype",
                tier=7,
                mark="Mk VII",
                required_level=1,
                cost=4600,
                image="",
                url="",
                recipes=[],
                ingredients=[GearIngredient(amount=50, gear="172Salvage")],
                stats={},
            ),
            "173Prototype": GearPiece(
                base_id="173Prototype",
                name="Mk 9 Kyrotech Battle Computer Prototype",
                tier=9,
                mark="Mk IX",
                required_level=1,
                cost=4600,
                image="",
                url="",
                recipes=[],
                ingredients=[GearIngredient(amount=50, gear="173Salvage")],
                stats={},
            ),
            # Full gear piece that requires kyrotech prototypes
            "172": GearPiece(
                base_id="172",
                name="Mk 7 Kyrotech Shock Prod",
                tier=7,
                mark="Mk VII",
                required_level=1,
                cost=10000,
                image="",
                url="",
                recipes=[],
                ingredients=[
                    GearIngredient(amount=1, gear="172Prototype"),
                    GearIngredient(amount=1, gear="173Prototype"),
                ],
                stats={},
            ),
            # Regular gear with no kyrotech
            "117": GearPiece(
                base_id="117",
                name="Mk 5 Arakyd Droid Caller",
                tier=5,
                mark="Mk V",
                required_level=1,
                cost=1400,
                image="",
                url="",
                recipes=[],
                ingredients=[],
                stats={},
            ),
            "109": GearPiece(
                base_id="109",
                name="Mk 3 Czerka Stun Cuffs",
                tier=3,
                mark="Mk III",
                required_level=1,
                cost=1274,
                image="",
                url="",
                recipes=[],
                ingredients=[],
                stats={},
            ),
        }

        self.analyzer = KyrotechAnalyzer(self.gear_lookup)

    def test_given_kyrotech_gear_when_calculate_salvage_requirements_then_returns_correct_amounts(
        self,
    ):
        """Test that kyrotech salvage is correctly calculated for gear pieces."""
        result = self.analyzer.calculate_salvage_requirements("172")

        # Gear 172 requires 1x 172Prototype (50 salvage) + 1x 173Prototype (50 salvage)
        self.assertEqual(result["172Salvage"], 50)
        self.assertEqual(result["173Salvage"], 50)

    def test_given_non_kyrotech_gear_when_calculate_salvage_requirements_then_returns_empty(
        self,
    ):
        """Test that non-kyrotech gear returns empty dict."""
        result = self.analyzer.calculate_salvage_requirements("117")
        self.assertEqual(result, {})

    def test_given_character_at_g8_with_no_equipped_gear_when_calculate_requirements_then_counts_current_and_future_tiers(
        self,
    ):
        """Test kyrotech calculation with no equipped gear (baseline case)."""
        gear_levels = [
            GearTier(tier=8, gear=["172", "117", "109"]),
            GearTier(tier=9, gear=["172", "117"]),
        ]

        # Character at G8, nothing equipped
        result = self.analyzer.calculate_character_requirements(gear_levels, 8, [])

        # Should count G8 (all unequipped) + G9
        # G8 has 1x gear 172 (50 of each salvage)
        # G9 has 1x gear 172 (50 of each salvage)
        # Total: 100 of each
        self.assertEqual(result["172Salvage"], 100)  # 2x gear 172 (G8 + G9)
        self.assertEqual(result["173Salvage"], 100)  # 2x gear 172 (G8 + G9)

    def test_given_character_at_g8_with_some_equipped_gear_when_calculate_requirements_then_unequipped_current_tier_gear_counted(
        self,
    ):
        """Test that unequipped gear at current tier is included in calculation."""
        gear_levels = [
            GearTier(tier=8, gear=["172", "117", "109"]),
            GearTier(tier=9, gear=["172", "117"]),
        ]

        # Character at G8 with gear 117 and 109 equipped (but not 172)
        equipped = ["117", "109"]
        result = self.analyzer.calculate_character_requirements(
            gear_levels, 8, equipped
        )

        # G8 gear 172 is NOT equipped, so it should be counted
        # G9 gear should all be counted
        # Total: G8 (1x 172) + G9 (1x 172) = 100 of each salvage
        self.assertEqual(result["172Salvage"], 100)
        self.assertEqual(result["173Salvage"], 100)

    def test_given_character_with_six_kyrotech_slots_and_four_equipped_when_calculate_requirements_then_only_counts_two_unequipped(
        self,
    ):
        """
        Test a character at current tier with 6 kyrotech gear slots, 4 equipped.

        This validates that only the 2 unequipped gear slots are counted
        in the kyrotech calculation, not all 6 or none.
        """
        gear_levels = [
            GearTier(tier=10, gear=["172", "172", "172", "172", "172", "172"]),
        ]

        # Character at G10 with 4 of 6 gear pieces equipped
        # Since gear list can have duplicates, we need to track which ones are equipped
        # We'll say slots 0, 1, 2, 3 are equipped (4 pieces of gear 172)
        # Slots 4, 5 are NOT equipped (2 pieces of gear 172)
        equipped = ["172", "172", "172", "172"]  # 4 equipped

        result = self.analyzer.calculate_character_requirements(
            gear_levels, 10, equipped
        )

        # Should count only the 2 unequipped gear 172 pieces
        # Each gear 172 requires 50 of each salvage type
        # 2 unequipped * 50 = 100 of each salvage
        self.assertEqual(result["172Salvage"], 100)
        self.assertEqual(result["173Salvage"], 100)

    def test_given_character_at_g8_partially_equipped_when_calculate_requirements_then_missing_current_tier_gear_counted(
        self,
    ):
        """
        Test the main fix: partially equipped gear at current tier.

        This is the key test case - a character at G8 with 2/3 pieces equipped.
        The one missing piece (172) SHOULD be counted since it's not equipped yet.
        """
        gear_levels = [
            GearTier(tier=8, gear=["172", "117", "109"]),
            GearTier(tier=9, gear=["172"]),
            GearTier(tier=10, gear=["117"]),
        ]

        # Character at G8 with 117 and 109 equipped, but 172 is missing
        equipped = ["117", "109"]
        result = self.analyzer.calculate_character_requirements(
            gear_levels, 8, equipped
        )

        # G8 gear 172 is NOT equipped, so it should be counted
        # G9 and G10 should all be counted
        # Total: G8 (1x 172) + G9 (1x 172) = 100 of each salvage
        self.assertEqual(
            result.get("172Salvage", 0), 100
        )  # From G8's gear 172 + G9's gear 172
        self.assertEqual(
            result.get("173Salvage", 0), 100
        )  # From G8's gear 172 + G9's gear 172

    def test_given_character_at_max_gear_fully_equipped_when_calculate_requirements_then_returns_empty(
        self,
    ):
        """Test that characters at max gear tier with all gear equipped return empty requirements."""
        gear_levels = [
            GearTier(tier=13, gear=["172", "117"]),
        ]

        # Character at max gear with all gear equipped
        result = self.analyzer.calculate_character_requirements(
            gear_levels, MAX_GEAR_TIER, ["172", "117"]
        )
        self.assertEqual(result, {})

    def test_given_character_at_g7_when_calculate_requirements_then_counts_all_future_kyrotech_tiers(
        self,
    ):
        """Test kyrotech calculation across multiple gear tiers."""
        gear_levels = [
            GearTier(tier=8, gear=["172", "117"]),
            GearTier(tier=9, gear=["172"]),
            GearTier(tier=10, gear=["109"]),
            GearTier(tier=11, gear=["172"]),
        ]

        # Character at G7, no equipped gear
        result = self.analyzer.calculate_character_requirements(gear_levels, 7, [])

        # Should count G8, G9, and G11 (all have gear 172)
        # 3 instances of gear 172 = 3 * 50 = 150 of each salvage type
        self.assertEqual(result["172Salvage"], 150)
        self.assertEqual(result["173Salvage"], 150)


class TestRosterAnalyzer(unittest.TestCase):
    """Test cases for RosterAnalyzer class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create mock gear lookup with kyrotech gear
        self.gear_lookup = {
            "172Salvage": GearPiece(
                base_id="172Salvage",
                name="Kyro Salvage",
                tier=7,
                mark="Mk VII",
                required_level=1,
                cost=0,
                image="",
                url="",
                recipes=[],
                ingredients=[],
                stats={},
            ),
            "173Salvage": GearPiece(
                base_id="173Salvage",
                name="Kyro Computer",
                tier=9,
                mark="Mk IX",
                required_level=1,
                cost=0,
                image="",
                url="",
                recipes=[],
                ingredients=[],
                stats={},
            ),
            "172": GearPiece(
                base_id="172",
                name="Kyro Gear",
                tier=7,
                mark="Mk VII",
                required_level=1,
                cost=10000,
                image="",
                url="",
                recipes=[],
                ingredients=[
                    GearIngredient(amount=50, gear="172Salvage"),
                    GearIngredient(amount=50, gear="173Salvage"),
                ],
                stats={},
            ),
            "117": GearPiece(
                base_id="117",
                name="Regular Gear",
                tier=5,
                mark="Mk V",
                required_level=1,
                cost=1400,
                image="",
                url="",
                recipes=[],
                ingredients=[],
                stats={},
            ),
        }

        self.kyrotech_analyzer = KyrotechAnalyzer(self.gear_lookup)
        self.roster_analyzer = RosterAnalyzer(self.kyrotech_analyzer)

    def test_given_character_with_partial_equipment_when_analyze_character_then_passes_equipped_gear_correctly(
        self,
    ):
        """Test that RosterAnalyzer correctly passes equipped gear to KyrotechAnalyzer."""
        # Create a mock unit with gear requirements
        unit = Unit(
            name="Test Character",
            base_id="TEST_CHAR",
            url="",
            image="",
            power=10000,
            description="Test",
            combat_type=1,
            gear_levels=[
                GearTier(tier=8, gear=["172", "117"]),
                GearTier(tier=9, gear=["172"]),
            ],
            alignment=1,
            categories=[],
            ability_classes=[],
            role="Attacker",
            activate_shard_count=10,
            is_capital_ship=False,
            is_galactic_legend=False,
            made_available_on="2020-01-01",
            crew_base_ids=[],
            omicron_ability_ids=[],
            zeta_ability_ids=[],
        )

        # Create a player unit at G8 with partial equipment
        player_unit = PlayerUnit(
            data=UnitData(
                base_id="TEST_CHAR",
                name="Test Character",
                gear_level=8,
                level=85,
                power=10000,
                rarity=7,
                gear=[
                    GearSlot(slot=0, is_obtained=True, base_id="117"),  # Equipped
                    GearSlot(slot=1, is_obtained=False, base_id="172"),  # NOT equipped
                ],
                url="",
                stats={},
                combat_type=1,
                has_ultimate=False,
                is_galactic_legend=False,
            )
        )

        units_by_id = {"TEST_CHAR": unit}
        result = self.roster_analyzer._analyze_character(player_unit, units_by_id)

        # Should return results since G8 has unequipped gear and G9 has kyrotech gear
        self.assertIsNotNone(result)
        name, gear_level, kyrotech_needs, total = result

        self.assertEqual(name, "Test Character")
        self.assertEqual(gear_level, 8)
        # G8 unequipped gear 172 (50 of each) + G9 gear 172 (50 of each) = 100 of each
        self.assertEqual(kyrotech_needs["172Salvage"], 100)
        self.assertEqual(kyrotech_needs["173Salvage"], 100)
        self.assertEqual(total, 200)

    def test_given_character_fully_equipped_at_current_tier_when_analyze_character_then_only_counts_future_tiers(
        self,
    ):
        """Test character with all current tier gear equipped."""
        unit = Unit(
            name="Test Character",
            base_id="TEST_CHAR",
            url="",
            image="",
            power=10000,
            description="Test",
            combat_type=1,
            gear_levels=[
                GearTier(tier=8, gear=["172", "117"]),
                GearTier(tier=9, gear=["172"]),
            ],
            alignment=1,
            categories=[],
            ability_classes=[],
            role="Attacker",
            activate_shard_count=10,
            is_capital_ship=False,
            is_galactic_legend=False,
            made_available_on="2020-01-01",
            crew_base_ids=[],
            omicron_ability_ids=[],
            zeta_ability_ids=[],
        )

        # All G8 gear equipped
        player_unit = PlayerUnit(
            data=UnitData(
                base_id="TEST_CHAR",
                name="Test Character",
                gear_level=8,
                level=85,
                power=10000,
                rarity=7,
                gear=[
                    GearSlot(slot=0, is_obtained=True, base_id="117"),
                    GearSlot(slot=1, is_obtained=True, base_id="172"),
                ],
                url="",
                stats={},
                combat_type=1,
                has_ultimate=False,
                is_galactic_legend=False,
            )
        )

        units_by_id = {"TEST_CHAR": unit}
        result = self.roster_analyzer._analyze_character(player_unit, units_by_id)

        # Should still need G9 gear
        self.assertIsNotNone(result)
        _, _, kyrotech_needs, total = result
        self.assertEqual(total, 100)  # Only G9's kyrotech


class TestPartialEquipmentIntegration(unittest.TestCase):
    """
    Integration test for the partial equipment fix.

    This test validates the complete scenario described in the bug:
    A character at Gear 9 with some gear pieces already applied should
    not have those pieces counted in the kyrotech calculation.
    """

    def test_given_temple_guard_scenario_when_calculate_requirements_then_missing_g8_gear_not_counted(
        self,
    ):
        """
        Test a real-world scenario: Character at G8 with 5/6 pieces equipped.

        This simulates Temple Guard from the player data:
        - At Gear Level 8
        - Has 5 out of 6 pieces equipped
        - Missing piece is gear 172 which contains kyrotech
        - Should only count G9+ gear, not the missing G8 gear
        """
        gear_lookup = {
            "172Salvage": GearPiece(
                base_id="172Salvage",
                name="Mk 7 Kyrotech Shock Prod Prototype Salvage",
                tier=7,
                mark="Mk VII",
                required_level=1,
                cost=0,
                image="",
                url="",
                recipes=[],
                ingredients=[],
                stats={},
            ),
            "173Salvage": GearPiece(
                base_id="173Salvage",
                name="Mk 9 Kyrotech Battle Computer Prototype Salvage",
                tier=9,
                mark="Mk IX",
                required_level=1,
                cost=0,
                image="",
                url="",
                recipes=[],
                ingredients=[],
                stats={},
            ),
            "172Prototype": GearPiece(
                base_id="172Prototype",
                name="Mk 7 Kyrotech Shock Prod Prototype",
                tier=7,
                mark="Mk VII",
                required_level=1,
                cost=4600,
                image="",
                url="",
                recipes=[],
                ingredients=[GearIngredient(amount=50, gear="172Salvage")],
                stats={},
            ),
            "173Prototype": GearPiece(
                base_id="173Prototype",
                name="Mk 9 Kyrotech Battle Computer Prototype",
                tier=9,
                mark="Mk IX",
                required_level=1,
                cost=4600,
                image="",
                url="",
                recipes=[],
                ingredients=[GearIngredient(amount=50, gear="173Salvage")],
                stats={},
            ),
            "172": GearPiece(
                base_id="172",
                name="Mk 7 Kyrotech Shock Prod",
                tier=7,
                mark="Mk VII",
                required_level=1,
                cost=10000,
                image="",
                url="",
                recipes=[],
                ingredients=[
                    GearIngredient(amount=1, gear="172Prototype"),
                    GearIngredient(amount=1, gear="173Prototype"),
                ],
                stats={},
            ),
            "117": GearPiece(
                base_id="117",
                name="Regular Gear 1",
                tier=5,
                mark="Mk V",
                required_level=1,
                cost=0,
                image="",
                url="",
                recipes=[],
                ingredients=[],
                stats={},
            ),
            "109": GearPiece(
                base_id="109",
                name="Regular Gear 2",
                tier=3,
                mark="Mk III",
                required_level=1,
                cost=0,
                image="",
                url="",
                recipes=[],
                ingredients=[],
                stats={},
            ),
            "112": GearPiece(
                base_id="112",
                name="Regular Gear 3",
                tier=3,
                mark="Mk III",
                required_level=1,
                cost=0,
                image="",
                url="",
                recipes=[],
                ingredients=[],
                stats={},
            ),
            "111": GearPiece(
                base_id="111",
                name="Regular Gear 4",
                tier=3,
                mark="Mk III",
                required_level=1,
                cost=0,
                image="",
                url="",
                recipes=[],
                ingredients=[],
                stats={},
            ),
        }

        analyzer = KyrotechAnalyzer(gear_lookup)

        # Temple Guard gear levels (simplified)
        gear_levels = [
            GearTier(tier=8, gear=["117", "172", "109", "112", "112", "111"]),
            GearTier(tier=9, gear=["172", "117", "109", "112", "112", "111"]),
            GearTier(tier=10, gear=["117", "109", "112", "112", "111", "117"]),
            GearTier(tier=11, gear=["172", "117", "109", "112", "112", "111"]),
        ]

        # Character at G8 with 5/6 equipped (missing slot 1 which is gear 172)
        equipped_gear = ["117", "109", "112", "112", "111"]

        result = analyzer.calculate_character_requirements(
            gear_levels, 8, equipped_gear
        )

        # Expected: G8 unequipped (100) + G9 (100) + G11 (100) = 300 total kyrotech
        # G8 has one unequipped gear 172, which should be counted
        expected_total = 300
        actual_total = sum(result.values())

        self.assertEqual(
            actual_total,
            expected_total,
            f"Expected {expected_total} total kyrotech, got {actual_total}. "
            f"G8 unequipped gear should be counted. "
            f"Result: {result}",
        )


if __name__ == "__main__":
    unittest.main()
