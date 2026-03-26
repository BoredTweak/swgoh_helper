"""
Enums used across SWGOH data models.
"""

from enum import Enum


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
