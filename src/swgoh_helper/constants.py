"""
Constants used throughout the swgoh_helper application.
"""

from .models.rote import RotePath

# Kyrotech salvage IDs and display names
KYROTECH_SALVAGE_IDS = {
    "172Salvage": "Mk 7 Kyrotech Shock Prod Prototype Salvage",
    "173Salvage": "Mk 9 Kyrotech Battle Computer Prototype Salvage",
    "174Salvage": "Mk 5 Kyrotech Power Cell Prototype Salvage",
}

MAX_GEAR_TIER = 13

# Unlock thresholds
ZEFFO_THRESHOLD = 30
MANDALORE_THRESHOLD = 25

# Minimum relic tier required (R1 = 1, R5 = 5, etc.)
MIN_RELIC_TIER = 7  # Must have at least R7 to qualify

# Distance scoring weights (from farming recommendations)
RELIC_WEIGHT = 1.0  # Each relic level
GEAR_WEIGHT = 0.5  # Each gear level to G13
STAR_WEIGHT = 2.0  # Each missing star

# Star requirements for relic levels
RELIC_STAR_REQUIREMENTS = {
    0: 0,
    1: 5,
    2: 5,
    3: 5,
    4: 6,
    5: 7,
    6: 7,
    7: 7,
    8: 7,
    9: 7,
    10: 7,
}

# Farming recommendations
MAX_PLAYERS_PER_UNIT = 20  # Max players to show per unit in farming recommendations

# Journey guide path planning
JOURNEY_GUIDE_REQUIREMENTS_FILENAME = "journey_guide_requirements.json"
UNOWNED_UNIT_PENALTY = 15.0

# Limited-availability policy
LIMITED_AVAILABILITY_BASE_THRESHOLD = 3
LIMITED_AVAILABILITY_CALLOUT_THRESHOLD = 4

# ROTE path display/planet prefixes
PATH_TO_PLANET_PREFIX = {
    RotePath.DARK_SIDE: "DS",
    RotePath.LIGHT_SIDE: "LS",
    RotePath.NEUTRAL: "N",
}
