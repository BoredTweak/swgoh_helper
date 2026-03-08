# Farming Recommendations

The farming recommendations feature identifies guild members who are **closest** to meeting platoon requirements for unfillable gaps. This helps guild leadership prioritize farming efforts strategically.

## How It Works

For each platoon **gap** (a unit requirement the guild can't fully fill), the system:

1. Finds all guild members who own the unit but don't meet the requirement
2. Calculates a "distance score" for each player
3. Groups players by distance and displays the closest candidates

## Distance Score Calculation

Each player's distance from a requirement is calculated using three weighted factors:

| Factor | Weight | Description |
|--------|--------|-------------|
| **Relic gap** | 1.0 | Number of relic levels needed to reach requirement |
| **Gear gap** | 0.5 | Gear levels needed to reach G13 (prerequisite for relics) |
| **Star gap** | 2.0 | Stars needed to unlock the required relic level |

**Formula:**
```
distance = (relic_gap × 1.0) + (gear_gap × 0.5) + (star_gap × 2.0)
```

Stars are weighted highest because they're the slowest to farm.

## Star Gates (Rarity Requirements)

Relic levels are gated by star rarity:

| Required Relic | Minimum Stars |
|---------------|---------------|
| Relic 1-3 | 5★ |
| Relic 4 | 6★ |
| Relic 5-9 | 7★ |

Players who lack the required stars are marked as "star gated" and their star gap contributes heavily to their distance score.

## Player Progress Stages

Players are categorized into progress stages:

| Stage | Description |
|-------|-------------|
| **+XR needed** | Has relics, just needs more relic levels |
| **at G13, needs relic** | At G13 but no relic yet |
| **needs G13 (+X gear)** | Below G13, needs to finish gearing |
| **needs X★ first** | Star gated - needs more stars before reaching required relic |

## Example Calculations

For a **R7 requirement**:

| Player State | Relic Gap | Gear Gap | Star Gap | Distance |
|--------------|-----------|----------|----------|----------|
| R5, 7★ | 2 | 0 | 0 | **2.0** |
| G13, 7★ | 7 | 0 | 0 | **7.0** |
| G12, 7★ | 7 | 1 | 0 | **7.5** |
| G10, 7★ | 7 | 3 | 0 | **8.5** |
| R5, 5★ | 2 | 0 | 2 | **6.0** (star gated) |
| G10, 5★ | 7 | 3 | 2 | **12.5** |

A player at R5 with 7★ (distance 2.0) would be prioritized over someone at G13 (distance 7.0), even though the G13 player is "closer" in terms of gear progression.

## Output Format

The farming recommendations section displays:

```
Farming recommendations (closest to gaps)
----------------------------------------

Luminara Unduli R7:
  - +2R needed (15): Player1, Player2, Player3, ...
  - +3R needed (8): Player4, Player5, ...
  - +4R needed (3): Player6, Player7, Player8

Starkiller R7:
  - +1R needed (2): Player9, Player10
  - at G13, needs relic (5): Player11, Player12, ...
```

Each line shows:
- **Label**: What the players need to do
- **Count**: Number of players at this distance
- **Names**: List of player names

Players with identical distance scores are grouped together (ties).
