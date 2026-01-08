# SWGOH Kyrotech Analysis Tool

This tool analyzes a player's Star Wars Galaxy of Heroes roster and identifies which characters have the highest Kyrotech gear requirements remaining.

## Setup

1. Install dependencies:
   ```powershell
   py -3.12 -m pip install -r .\requirements.txt
   ```

2. Create a `.env` file with your SWGOH.gg API key:
   ```
   SWGOH_API_KEY=your_api_key_here
   ```

## Caching

The tool automatically caches API responses in the `data/` folder to improve performance and reduce API calls:

- **Units data** (`units.json`): All game characters and their gear requirements
- **Gear recipes** (`gear.json`): Crafting recipes for all gear pieces
- **Player data** (`player_<allycode>.json`): Individual player roster data

**Cache behavior:**
- Cache expires after **1 hour** from initial fetch
- Expired cache is automatically refreshed on next run
- First run: "Fetching from API..."
- Subsequent runs: "Loading from cache..."
- Cache files are stored in JSON format with timestamps

**Manual cache management:**
- Delete `data/` folder to force fresh API fetch
- Useful if you need the most recent player data before cache expires

## Usage

Run the app with a player's ally code:

```powershell
python app.py <ally_code>
```

Example:
```powershell
python app.py 123-456-789
```

Or without dashes:
```powershell
python app.py 123456789
```

## Output

The tool will display:
1. Character name and current gear level
2. Total Kyrotech pieces needed
3. Breakdown by Kyrotech type
4. Summary statistics

Example output:
```
================================================================================
CHARACTERS WITH HIGHEST KYROTECH REQUIREMENTS
================================================================================

#1. Commander Ahsoka Tano (Currently G12)
   Total Kyrotech Pieces: 4
   Breakdown:
      - Kyrotech Power Cell Prototype: 2
      - Kyrotech Shock Prod Prototype: 2

#2. Jedi Knight Luke Skywalker (Currently G11)
   Total Kyrotech Pieces: 4
   Breakdown:
      - Kyrotech Battle Computer Prototype: 2
      - Kyrotech Shock Prod Prototype: 2

================================================================================
Total characters needing kyrotech: 50
Total kyrotech pieces needed: 250
================================================================================
```

## How It Works

1. **Loads Game Data**: Fetches from cache or SWGOH.gg API (units and gear recipes)
2. **Fetches Player Data**: Gets the player's current roster (from cache or API)
3. **Calculates Requirements**: For each character, calculates Kyrotech needed from current gear to G13
4. **Ranks Results**: Sorts characters by total Kyrotech count needed
5. **Displays**: Shows formatted output with rankings and breakdowns

The caching system ensures fast subsequent runs while keeping data reasonably fresh.

## API Requirements

This tool requires access to the SWGOH.gg API. You need:
- A valid SWGOH.gg account
- API access token (obtained from SWGOH.gg)
- Player ally codes must be synced with SWGOH.gg
