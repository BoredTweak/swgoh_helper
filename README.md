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

By default, this now prints only the `gaps` view.

Choose a specific output format:

```powershell
uv run rote-platoon 123-456-789 --output-format gaps
uv run rote-platoon 123-456-789 --output-format coverage
uv run rote-platoon 123-456-789 --output-format owners
uv run rote-platoon 123-456-789 --output-format mine
uv run rote-platoon 123-456-789 --output-format all
```

Optionally limit analysis to a specific phase:
```powershell
uv run rote-platoon 123-456-789 --max-phase 4
```

Show every qualifying owner for each platoon requirement, grouped by territory:
```powershell
uv run rote-platoon 123-456-789 --max-phase 4 --output-format owners
```

Valid phases: `1`, `2`, `3`, `3b`, `4`, `4b`, `5`, `5b`, `6`

**Output formats:**
- `gaps` (default): critical gaps + limited availability units
- `coverage`: territory coverage summary
- `owners`: qualifying owners for each requirement, grouped by territory
- `mine`: planet-centric list of requirements you can cover, with limited-availability callouts
- `all`: coverage + gaps

**Optional flags:**
- `--ignore-players` excludes players from analysis by name or ally code (supports `123456789` or `123-456-789`)

Farming recommendations have moved to `rote-farm`.

### Bonus Zone Readiness Analysis

Compare guild readiness for Zeffo vs Mandalore bonus zones in Rise of the Empire TB:

```powershell
uv run pytest test/test_bonus_zone_readiness.py -v -s
```

**What it analyzes:**
- Current qualifying player count vs unlock threshold (Zeffo: 30/30, Mandalore: 25/25)
- "Distance" to qualify for each near-qualifying player using the same weighted farming model:
   - relic upgrade cost weights from `data/relic_costs.json`
   - `+2.0` per gear level needed to reach G13
   - `+5.0` per missing star
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

### Personal Farm Recommendations

Get personalized farming recommendations based on your guild's platoon gaps:

```powershell
uv run rote-farm <ally_code>
```

Options:
```powershell
uv run rote-farm 123-456-789 --max-phase 4
uv run rote-farm 123-456-789 --max-recommendations 10
uv run rote-farm 123-456-789 --include-unowned
```

## Discord Bot

The project includes an optional Discord bot that exposes all commands as slash commands.

### Discord Setup

1. Sync dependencies with the discord extra:
   ```powershell
   uv sync --extra discord
   ```

2. Add your Discord bot token to `.env`:
   ```
   DISCORD_TOKEN=your_discord_bot_token_here
   ```

3. Run the bot:
   ```powershell
   uv run --extra discord swgoh-discord
   ```

### Slash Commands

| Command | Description |
|---------|-------------|
| `/kyrotech` | Analyze a player's roster for kyrotech requirements |
| `/rote-platoon` | Analyze guild for RotE platoon requirements |
| `/rote-farm` | Personal farm recommendations based on guild needs |
| `/rote-bonus-readiness` | Analyze guild readiness for RotE bonus zones |

All commands accept the same options as their CLI counterparts (ally code, max-phase, etc.) as slash command parameters.

## Caching

API responses are cached in `data/` for 1 hour. Delete the folder to force a refresh.
- Player ally codes must be synced with SWGOH.gg
