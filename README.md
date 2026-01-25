# SWGOH Helper

Tools for analyzing Star Wars Galaxy of Heroes data via the SWGOH.gg API.

## Prerequisites

- Python 3.12+
- SWGOH.gg API key

## Setup

1. Install dependencies:
   ```powershell
   py -3.12 -m pip install -r requirements.txt
   ```

2. Create a `.env` file with your API key:
   ```
   SWGOH_API_KEY=your_api_key_here
   ```

## Usage

### Kyrotech Analysis

Analyze a player's roster for Kyrotech gear requirements (current gear → G13):

```powershell
py -3.12 app.py kyrotech <ally_code>
```

Example:
```powershell
py -3.12 app.py kyrotech 123-456-789
```

### ROTE Platoon Analysis

Analyze guild coverage for Rise of the Empire Territory Battle platoon requirements:

```powershell
py -3.12 app.py rote_platoon <ally_code>
```

Optionally limit analysis to a specific phase:
```powershell
py -3.12 app.py rote_platoon 123-456-789 --max-phase 4
```

Valid phases: `1`, `2`, `3`, `3b`, `4`, `4b`, `5`, `5b`, `6`

**Output includes:**
- Coverage summary by territory (✅ 100%, ⚠️ 80%+, ❌ below 80%)
- Unfillable platoon slots by relic tier
- Critical gaps (units with fewer players than slots needed)
- Limited availability units (only 1-3 players have them)

## Caching

API responses are cached in `data/` for 1 hour. Delete the folder to force a refresh.
- Player ally codes must be synced with SWGOH.gg
