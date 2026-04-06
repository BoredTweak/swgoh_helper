"""
Constants used throughout the swgoh_helper application.
"""

# Kyrotech salvage IDs and display names
KYROTECH_SALVAGE_IDS = {
    "172Salvage": "Mk 7 Kyrotech Shock Prod Prototype Salvage",
    "173Salvage": "Mk 9 Kyrotech Battle Computer Prototype Salvage",
    "174Salvage": "Mk 5 Kyrotech Power Cell Prototype Salvage",
}

MAX_GEAR_TIER = 13

# Bo-Katan (Mand'alor) unlock requirements: R7 for all of these
BOKATAN_PREREQS = {
    "KELLERANBEQ": "Kelleran Beq",
    "PAZVIZSLA": "Paz Vizsla",
    "IG12": "IG-12 & Grogu",
    "THEMANDALORIANBESKARARMOR": "The Mandalorian (Beskar Armor)",
}

# The Mandalorian (Beskar Armor) unlock requirements: 7* G12 for all of these
BESKAR_PREREQS = {
    "THEMANDALORIAN": "The Mandalorian",
    "GREEFKARGA": "Greef Karga",
    "CARADUNE": "Cara Dune",
    "IG11": "IG-11",
    "KUIIL": "Kuiil",
}

# Unlock thresholds
ZEFFO_THRESHOLD = 30
MANDALORE_THRESHOLD = 25

# Minimum relic tier required (R1 = 1, R5 = 5, etc.)
MIN_RELIC_TIER = 7  # Must have at least R7 to qualify

# Beskar Mando unlock requirement
BESKAR_MIN_GEAR = 12
BESKAR_MIN_STARS = 7

# Bo-Katan unlock requirement (all prereqs at R7)
BOKATAN_MIN_RELIC = 7

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
