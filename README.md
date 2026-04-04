# SWGOH Helper

Tools for analyzing Star Wars Galaxy of Heroes data via the SWGOH.gg API.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- SWGOH.gg API key

## Setup

1. Install uv (if not already installed):
   ```powershell
   pip install uv
   ```

2. Sync dependencies:
   ```powershell
   uv sync
   ```

3. Create a `.env` file with your API key:
   ```
   SWGOH_API_KEY=your_api_key_here
   ```
NOTE:
You can obtain an API key by 
1. Creating an account with https://swgoh.gg/
1. Under your profile, select manage api applications
1. Add a new application for this helper. 
   - This process will take a few days for SWGOH to approve

## Usage

### Kyrotech Analysis

Analyze a player's roster for Kyrotech gear requirements (current gear → G13):

```powershell
uv run kyrotech <ally_code>
```

Example:
```powershell
uv run kyrotech 123-456-789
```

### ROTE Platoon Analysis

Analyze guild coverage for Rise of the Empire Territory Battle platoon requirements:

```powershell
uv run rote-platoon <ally_code>
```

Optionally limit analysis to a specific phase:
```powershell
uv run rote-platoon 123-456-789 --max-phase 4
```

Show every qualifying owner for each platoon requirement, grouped by territory:
```powershell
uv run rote-platoon 123-456-789 --max-phase 4 --show-owners
```

Valid phases: `1`, `2`, `3`, `3b`, `4`, `4b`, `5`, `5b`, `6`

**Output includes:**
- Coverage summary by territory (✅ 100%, ⚠️ 80%+, ❌ below 80%)
- Unfillable platoon slots by relic tier
- Critical gaps (units with fewer players than slots needed)
- Limited availability units (only 1-3 players have them)
- Farming recommendations (closest players to each gap)

**Optional flags:**
- `--by-territory` groups farming recommendations by planet
- `--show-owners` lists all qualifying players for each platoon requirement by planet

See [Farming Recommendations](docs/farming_recommendations.md) for details on how proximity is calculated.

### Bonus Zone Readiness Analysis

Compare guild readiness for Zeffo vs Mandalore bonus zones in Rise of the Empire TB:

```powershell
uv run pytest test/test_bonus_zone_readiness.py -v -s
```

**What it analyzes:**
- Current qualifying player count vs unlock threshold (Zeffo: 30/30, Mandalore: 25/25)
- "Distance" to qualify for each near-qualifying player using the farming formula:
  - `distance = (relic_gap × 1.0) + (gear_gap × 0.5) + (star_gap × 2.0)`
- Total guild farming effort to fill the gap
- Quick wins (players within distance < 5)

**Mandalore unlock chain (factored into distance calculations):**
- Bo-Katan (Mand'alor) requires R7: Kelleran Beq, Paz Vizsla, IG-12 & Grogu, Beskar Mando
- Beskar Mando requires 7★ G12: Mando, Greef Karga, Cara Dune, IG-11, Kuiil

**Output includes:**
- Officer briefing with priority player lists
- Comparison summary (which zone is closer to unlock)
- Quick wins for each zone

See [Bonus Zone Analysis](docs/bonus_zone_analysis.md) for the latest results.

## Caching

API responses are cached in `data/` for 1 hour. Delete the folder to force a refresh.
- Player ally codes must be synced with SWGOH.gg
