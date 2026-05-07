# SWGOH Helper

SWGOH Helper is a local analysis toolkit for Star Wars: Galaxy of Heroes guild planning.

It provides:
- CLI commands for roster and guild analysis
- Optional Discord slash commands backed by the same app logic
- Local caching in `data/` for SWGOH.gg API responses

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- SWGOH.gg API key

## Setup

1. Install dependencies:

```powershell
uv sync
```

2. Create `.env`:

```env
SWGOH_API_KEY=your_api_key_here
```

API key notes:
1. Create an account at https://swgoh.gg/
2. Open profile -> manage API applications
3. Create an app for this tool (approval can take a few days)

## CLI

You can run commands either directly (for example `uv run rote-platoon ...`) or through the umbrella command (`uv run swgoh <command> ...`).

### Quickstart

If you just want to run something quickly, start here:

```powershell
# 1) platoon gaps for your guild
uv run rote-platoon 123-456-789

# 2) personal farm recommendations
uv run rote-farm 123-456-789 --max-phase 4

# 3) limited-availability member pressure view
uv run rote-limited 123-456-789

# 4) bonus zone readiness from cache (requires prior rote-platoon run)
uv run rote-bonus-readiness <guild_id>
```

Equivalent umbrella form:

```powershell
uv run swgoh rote-platoon 123-456-789
uv run swgoh rote-farm 123-456-789 --max-phase 4
```

### Command Reference

| Command | Purpose | Typical Input |
|---|---|---|
| `kyrotech` | Player kyrotech needs | ally code |
| `rote-platoon` | Guild platoon coverage/gaps | ally code |
| `rote-limited` | Limited-availability member counts | ally code |
| `rote-farm` | Personalized farming priorities | ally code |
| `rote-bonus-readiness` | Zeffo/Mandalore readiness from local cache | guild id |

### Kyrotech

Analyze a player's kyrotech needs:

```powershell
uv run kyrotech 123-456-789
uv run kyrotech --ally-code 123-456-789 --faction Empire --include-unowned
```

### ROTE Platoon

Analyze guild ROTE platoon coverage:

```powershell
uv run rote-platoon 123-456-789
uv run rote-platoon --ally-code 123-456-789 --max-phase 4 --output-format owners
```

Output formats:
- `gaps` (default)
- `coverage`
- `owners`
- `mine`
- `limited`
- `all`

Useful options:
- `--refresh`
- `--ignore-players "Name One,Name Two"`

### ROTE Limited

Show limited-availability requirements per member:

```powershell
uv run rote-limited 123-456-789
uv run rote-limited --ally-code 123-456-789 --max-phase 4 --ignore-players "Name One,Name Two"
uv run rote-limited 123-456-789 --output-format relic
```

Output formats:
- `member` (default): each guild member's count of limited-availability character requirements
- `relic`: all required ROTE characters grouped by required relic tier with owner counts and required slots

### ROTE Farm

Get player-specific farm recommendations:

```powershell
uv run rote-farm 123-456-789
uv run rote-farm --ally-code 123-456-789 --max-phase 4 --max-recommendations 10 --include-unowned
```

### ROTE Bonus Readiness

Analyze cached guild readiness for Zeffo and Mandalore bonus zones:

```powershell
uv run rote-bonus-readiness <guild_id>
```

This command reads local cache data. Run `rote-platoon` first to populate guild/player cache files.

## Discord Bot (Optional)

The Discord bot exposes these slash commands:
- `/kyrotech`
- `/rote-platoon`
- `/rote-farm`
- `/rote-bonus-readiness`

Setup:

1. Install optional dependency:

```powershell
uv sync --extra discord
```

2. Add Discord token to `.env`:

```env
DISCORD_TOKEN=your_discord_bot_token_here
```

3. Run bot:

```powershell
uv run --extra discord swgoh-discord
```

Note: `/rote-platoon` on Discord intentionally excludes the `limited` output mode. Use CLI `rote-limited` for that view.

## Caching

API responses are cached under `data/` for about 1 hour.

To force fresh fetches:
- use `--refresh` where supported
- or clear cached files in `data/`
