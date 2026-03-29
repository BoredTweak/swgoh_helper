"""
Enums used across SWGOH data models.
"""

from enum import Enum, IntEnum


class CombatType(IntEnum):
    """Unit combat type from SWGOH.GG API."""

    CHARACTER = 1
    SHIP = 2


class GACFormat(str, Enum):
    """Grand Arena Championship format types."""

    THREE_V_THREE = "3v3"
    FIVE_V_FIVE = "5v5"


class GACLeague(str, Enum):
    """Grand Arena Championship league tiers."""

    CARBONITE = "Carbonite"
    BRONZIUM = "Bronzium"
    CHROMIUM = "Chromium"
    AURODIUM = "Aurodium"
    KYBER = "Kyber"
