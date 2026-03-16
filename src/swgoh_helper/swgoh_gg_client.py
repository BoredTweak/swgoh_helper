import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Callable, TypeVar, Any, List, Tuple, Optional

from .models import (
    PlayerResponse,
    UnitsResponse,
    GearPiece,
    GuildResponse,
    GACFormat,
    GACBracket,
    GACBracketPlayer,
    GACHistory,
    GACSeasonEvent,
    GACRoundResult,
    GACMatchAnalysis,
    GACSquad,
    GACSquadUnit,
    GACBattle,
)
from .cache_manager import CacheManager


T = TypeVar("T")


class SwgohGGClient:
    """
    Client for interacting with the SWGOH.GG API with intelligent caching.
    """

    def __init__(self, api_key: str, cache_manager: CacheManager = None):
        """
        Initialize the SWGOH.GG API client.

        Args:
            api_key: API key for SWGOH.GG authentication
            cache_manager: Optional cache manager instance (creates default if None)
        """
        self.api_key = api_key
        self.base_url = "https://swgoh.gg/api"
        self.headers = {"x-gg-bot-access": self.api_key}
        self.cache = cache_manager or CacheManager()

    def _fetch_with_cache(
        self,
        cache_key: str,
        fetch_func: Callable[[], Any],
        cache_message: str,
        fetch_message: str,
    ) -> Any:
        cached_data = self.cache.get(cache_key)
        if cached_data is not None:
            print(cache_message)
            return cached_data

        # Fetch from API if cache miss
        print(fetch_message)
        data = fetch_func()
        self.cache.set(cache_key, data)
        return data

    def get_units(self) -> UnitsResponse:
        """Fetch all units from SWGOH.GG API."""

        def fetch_from_api():
            response = requests.get(f"{self.base_url}/units/", headers=self.headers)
            response.raise_for_status()
            return response.json()

        data = self._fetch_with_cache(
            cache_key="units",
            fetch_func=fetch_from_api,
            cache_message="Loading units from cache...",
            fetch_message="Fetching units from API...",
        )

        return UnitsResponse(**data)

    def get_gear_recipes(self) -> Dict[str, GearPiece]:
        """
        Fetch all gear/equipment data from SWGOH.GG API including crafting recipes.

        Returns:
            Dictionary mapping gear base_id to GearPiece object
        """

        def fetch_from_api():
            response = requests.get(f"{self.base_url}/gear/", headers=self.headers)
            response.raise_for_status()
            return response.json()

        gear_data = self._fetch_with_cache(
            cache_key="gear",
            fetch_func=fetch_from_api,
            cache_message="Loading gear recipes from cache...",
            fetch_message="Fetching gear recipes from API...",
        )

        return self._build_gear_lookup(gear_data)

    def _build_gear_lookup(self, gear_data: list) -> Dict[str, GearPiece]:
        gear_by_id: Dict[str, GearPiece] = {}
        for gear_json in gear_data:
            gear_piece = GearPiece(**gear_json)
            gear_by_id[gear_piece.base_id] = gear_piece
        return gear_by_id

    def get_player_units(self, ally_code: str) -> PlayerResponse:
        """Fetch player's units/roster from SWGOH.GG API."""
        normalized_ally_code = ally_code.replace("-", "")

        def fetch_from_api():
            url = f"{self.base_url}/player/{normalized_ally_code}/"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()

        data = self._fetch_with_cache(
            cache_key=f"player_{normalized_ally_code}",
            fetch_func=fetch_from_api,
            cache_message=f"Loading {normalized_ally_code} player data from cache...",
            fetch_message="Fetching player data from API...",
        )

        return PlayerResponse(**data)

    def get_guild(self, guild_id: str) -> GuildResponse:
        """Fetch guild data from SWGOH.GG API."""

        def fetch_from_api():
            url = f"{self.base_url}/guild-profile/{guild_id}/"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()

        data = self._fetch_with_cache(
            cache_key=f"guild_{guild_id}",
            fetch_func=fetch_from_api,
            cache_message="Loading guild data from cache...",
            fetch_message="Fetching guild data from API...",
        )

        return GuildResponse(**data)

    def get_guild_player_ids(self, guild_id: str) -> List[int]:
        """Fetch all player ally codes in a guild."""
        guild = self.get_guild(guild_id)
        return [
            member.ally_code
            for member in guild.data.members
            if member.ally_code is not None
        ]

    def get_guild_id_from_player(self, ally_code: str) -> str:
        """Get the guild ID from a player's ally code. Raises ValueError if not in a guild."""
        player = self.get_player_units(ally_code)
        guild_id = player.data.guild_id

        if not guild_id:
            raise ValueError(
                f"Player {player.data.name} is not in a guild or guild data is not available"
            )

        return guild_id

    def get_guild_from_ally_code(self, ally_code: str) -> tuple[str, str, List[int]]:
        """Get guild info (id, name, member ally codes) from a player's ally code."""
        print(f"\nFetching guild information for ally code {ally_code}...")

        guild_id = self.get_guild_id_from_player(ally_code)
        guild = self.get_guild(guild_id)

        guild_name = guild.data.name
        member_ally_codes = self.get_guild_player_ids(guild_id)

        print(f"Found guild: {guild_name} (ID: {guild_id})")
        print(f"Guild has {len(member_ally_codes)} members with ally codes.")

        return guild_id, guild_name, member_ally_codes

    def invalidate_player_caches(self, ally_codes: List[int]) -> None:
        """Invalidate cache entries for the specified ally codes."""
        for ally_code in ally_codes:
            normalized_code = str(ally_code).replace("-", "")
            cache_key = f"player_{normalized_code}"
            self.cache.invalidate(cache_key)

    def get_guild_rosters(
        self, ally_codes: List[int], delay_seconds: float = 1.0
    ) -> List[PlayerResponse]:
        """Fetch rosters for all guild members. Fetches cached in parallel, uncached sequentially."""
        total = len(ally_codes)
        print(f"\nFetching rosters for {total} guild members...")

        cached_codes, uncached_codes = self._partition_by_cache_status(ally_codes)
        print(
            f"  Found {len(cached_codes)} cached, {len(uncached_codes)} to fetch from API"
        )

        rosters: List[PlayerResponse] = []
        if cached_codes:
            print(f"\n  Loading {len(cached_codes)} cached rosters in parallel...")
            cached_rosters = self._fetch_players_parallel(cached_codes)
            rosters.extend(cached_rosters)
            print(f"  Loaded {len(cached_rosters)} cached rosters.")

        if uncached_codes:
            print(f"\n  Fetching {len(uncached_codes)} rosters from API...")
            uncached_rosters = self._fetch_players_sequential(
                uncached_codes, delay_seconds
            )
            rosters.extend(uncached_rosters)

        print(f"\nSuccessfully fetched {len(rosters)} rosters.\n")
        return rosters

    def _partition_by_cache_status(
        self, ally_codes: List[int]
    ) -> Tuple[List[int], List[int]]:
        cached_codes = []
        uncached_codes = []

        for ally_code in ally_codes:
            normalized_code = str(ally_code).replace("-", "")
            cache_key = f"player_{normalized_code}"

            if self.cache.is_valid(cache_key):
                cached_codes.append(ally_code)
            else:
                uncached_codes.append(ally_code)

        return cached_codes, uncached_codes

    def _fetch_players_parallel(
        self, ally_codes: List[int], max_workers: int = 10
    ) -> List[PlayerResponse]:
        rosters = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_code = {
                executor.submit(self.get_player_units, str(code)): code
                for code in ally_codes
            }

            for future in as_completed(future_to_code):
                ally_code = future_to_code[future]
                try:
                    roster = future.result()
                    rosters.append(roster)
                except Exception as e:
                    print(f"    Warning: Failed to load cached {ally_code}: {e}")

        return rosters

    def _fetch_players_sequential(
        self, ally_codes: List[int], delay_seconds: float
    ) -> List[PlayerResponse]:
        rosters = []
        total = len(ally_codes)

        for idx, ally_code in enumerate(ally_codes, 1):
            try:
                print(f"    [{idx}/{total}] Fetching {ally_code}...")
                roster = self.get_player_units(str(ally_code))
                rosters.append(roster)
                if idx < total and delay_seconds > 0:
                    time.sleep(delay_seconds)
            except Exception as e:
                print(f"    Warning: Failed to fetch {ally_code}: {e}")
                continue

        return rosters

    # ===== Grand Arena Championship (GAC) Methods =====

    def _determine_gac_format(self, event_id: Optional[str] = None) -> GACFormat:
        """
        Determine the GAC format (3v3 or 5v5) from event data.

        GAC alternates between 3v3 and 5v5 formats. The format can often
        be determined from the event_id or season identifier.

        Args:
            event_id: Optional event identifier that may contain format info

        Returns:
            GACFormat enum value
        """
        if event_id:
            # Event IDs often contain format indicators
            event_lower = event_id.lower()
            if "3v3" in event_lower or "3x3" in event_lower:
                return GACFormat.THREE_V_THREE
            if "5v5" in event_lower or "5x5" in event_lower:
                return GACFormat.FIVE_V_FIVE
        # Default to 5v5 as it's the more common format
        return GACFormat.FIVE_V_FIVE

    def get_gac_bracket(
        self, ally_code: str, event_id: Optional[str] = None
    ) -> GACBracket:
        """
        Fetch the current GAC bracket for a given player.

        Args:
            ally_code: The player's ally code
            event_id: Optional specific event ID. If None, fetches current event.

        Returns:
            GACBracket containing all players in the bracket
        """
        normalized_ally_code = ally_code.replace("-", "")

        def fetch_from_api():
            # Try the gac-bracket endpoint pattern
            url = f"{self.base_url}/gac-bracket/{normalized_ally_code}/"
            if event_id:
                url = f"{url}?event={event_id}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()

        cache_key = f"gac_bracket_{normalized_ally_code}"
        if event_id:
            cache_key = f"{cache_key}_{event_id}"

        try:
            data = self._fetch_with_cache(
                cache_key=cache_key,
                fetch_func=fetch_from_api,
                cache_message=f"Loading GAC bracket for {normalized_ally_code} from cache...",
                fetch_message=f"Fetching GAC bracket for {normalized_ally_code} from API...",
            )
            return self._parse_gac_bracket(data)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                # Endpoint might not exist, try alternative approach
                print(
                    f"GAC bracket endpoint not available, building from player data..."
                )
                return self._build_bracket_from_player_data(ally_code)
            raise

    def _parse_gac_bracket(self, data: Dict[str, Any]) -> GACBracket:
        """Parse raw API response into GACBracket model."""
        players = []
        bracket_data = data.get("data", data)

        # Handle different response formats
        player_list = bracket_data.get("players", bracket_data.get("bracket", []))

        for player_data in player_list:
            player = GACBracketPlayer(
                ally_code=player_data.get("ally_code", 0),
                name=player_data.get("name", "Unknown"),
                skill_rating=player_data.get("skill_rating", 0),
                galactic_power=player_data.get("galactic_power", 0),
                league=player_data.get("league_name", player_data.get("league")),
                division=player_data.get(
                    "division_number", player_data.get("division")
                ),
                wins=player_data.get("wins", 0),
                losses=player_data.get("losses", 0),
                current_round_score=player_data.get("score", 0),
                portrait_image=player_data.get("portrait_image"),
                title=player_data.get("title"),
                guild_name=player_data.get("guild_name"),
            )
            players.append(player)

        event_id = bracket_data.get("event_id", bracket_data.get("eventId"))
        gac_format = self._determine_gac_format(event_id)

        return GACBracket(
            event_id=event_id,
            bracket_id=bracket_data.get("bracket_id", bracket_data.get("bracketId")),
            format=gac_format,
            league=bracket_data.get("league_name", bracket_data.get("league")),
            division=bracket_data.get("division_number", bracket_data.get("division")),
            players=players,
            round_number=bracket_data.get("round_number", bracket_data.get("round", 1)),
            total_rounds=bracket_data.get("total_rounds", 3),
            start_time=bracket_data.get("start_time"),
            end_time=bracket_data.get("end_time"),
        )

    def _build_bracket_from_player_data(self, ally_code: str) -> GACBracket:
        """
        Build a minimal bracket from player data when GAC bracket endpoint is unavailable.

        This provides basic GAC info from the player's profile data.
        """
        player = self.get_player_units(ally_code)
        player_data = player.data

        # Create a bracket with just the requesting player's info
        bracket_player = GACBracketPlayer(
            ally_code=player_data.ally_code,
            name=player_data.name,
            skill_rating=player_data.skill_rating,
            galactic_power=player_data.galactic_power,
            league=player_data.league_name,
            division=player_data.division_number,
            portrait_image=player_data.portrait_image,
            title=player_data.title,
            guild_name=player_data.guild_name,
        )

        return GACBracket(
            format=GACFormat.FIVE_V_FIVE,  # Default, will be updated if info available
            league=player_data.league_name,
            division=player_data.division_number,
            players=[bracket_player],
        )

    def get_gac_history(
        self,
        ally_code: str,
        format_filter: Optional[GACFormat] = None,
        limit: Optional[int] = None,
    ) -> GACHistory:
        """
        Fetch GAC history for a player.

        Args:
            ally_code: The player's ally code
            format_filter: Optional filter for 3v3 or 5v5 events only
            limit: Maximum number of events to return

        Returns:
            GACHistory containing the player's GAC event history
        """
        normalized_ally_code = ally_code.replace("-", "")

        def fetch_from_api():
            url = f"{self.base_url}/gac-history/{normalized_ally_code}/"
            params = {}
            if format_filter:
                params["format"] = format_filter.value
            if limit:
                params["limit"] = limit
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()

        cache_key = f"gac_history_{normalized_ally_code}"

        try:
            data = self._fetch_with_cache(
                cache_key=cache_key,
                fetch_func=fetch_from_api,
                cache_message=f"Loading GAC history for {normalized_ally_code} from cache...",
                fetch_message=f"Fetching GAC history for {normalized_ally_code} from API...",
            )
            history = self._parse_gac_history(data, normalized_ally_code)

            # Apply filters if specified
            if format_filter:
                history.events = history.get_events_by_format(format_filter)
            if limit and len(history.events) > limit:
                history.events = history.events[:limit]

            return history
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                print(
                    f"GAC history endpoint not available, building from player data..."
                )
                return self._build_history_from_player_data(ally_code)
            raise

    def _parse_gac_history(self, data: Dict[str, Any], ally_code: str) -> GACHistory:
        """Parse raw API response into GACHistory model."""
        history_data = data.get("data", data)
        events = []

        event_list = history_data.get("events", history_data.get("seasons", []))
        for event_data in event_list:
            event_id = event_data.get("event_id", event_data.get("eventId", ""))
            gac_format = self._determine_gac_format(event_id)

            rounds = []
            for round_data in event_data.get("rounds", []):
                round_result = GACRoundResult(
                    opponent_ally_code=round_data.get("opponent_ally_code"),
                    opponent_name=round_data.get("opponent_name"),
                    opponent_galactic_power=round_data.get("opponent_galactic_power"),
                    player_score=round_data.get("player_score", 0),
                    opponent_score=round_data.get("opponent_score", 0),
                    was_victory=round_data.get("was_victory"),
                )
                rounds.append(round_result)

            event = GACSeasonEvent(
                event_id=event_id,
                season_id=event_data.get("season_id", event_data.get("seasonId")),
                format=gac_format,
                start_time=event_data.get("start_time"),
                end_time=event_data.get("end_time"),
                league=event_data.get("league_name", event_data.get("league")),
                division=event_data.get("division_number", event_data.get("division")),
                skill_rating_start=event_data.get("skill_rating_start"),
                skill_rating_end=event_data.get("skill_rating_end"),
                final_rank=event_data.get("final_rank", event_data.get("rank")),
                wins=event_data.get("wins", 0),
                losses=event_data.get("losses", 0),
                rounds=rounds,
            )
            events.append(event)

        return GACHistory(
            ally_code=int(ally_code),
            player_name=history_data.get("player_name", history_data.get("name")),
            current_skill_rating=history_data.get("skill_rating", 0),
            current_league=history_data.get("league_name", history_data.get("league")),
            current_division=history_data.get(
                "division_number", history_data.get("division")
            ),
            events=events,
        )

    def _build_history_from_player_data(self, ally_code: str) -> GACHistory:
        """
        Build minimal GAC history from player profile data.

        Player profiles contain aggregate GAC stats but not detailed history.
        """
        player = self.get_player_units(ally_code)
        player_data = player.data

        return GACHistory(
            ally_code=player_data.ally_code,
            player_name=player_data.name,
            current_skill_rating=player_data.skill_rating,
            current_league=player_data.league_name,
            current_division=player_data.division_number,
            events=[],  # No detailed event history available from player endpoint
        )

    def get_gac_match_details(
        self, ally_code: str, event_id: str, round_number: int = 1
    ) -> GACRoundResult:
        """
        Fetch detailed information about a specific GAC match.

        Args:
            ally_code: The player's ally code
            event_id: The GAC event identifier
            round_number: The round number (1-3 typically)

        Returns:
            GACRoundResult with detailed attack and defense information
        """
        normalized_ally_code = ally_code.replace("-", "")

        def fetch_from_api():
            url = f"{self.base_url}/gac-match/{normalized_ally_code}/{event_id}/{round_number}/"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()

        cache_key = f"gac_match_{normalized_ally_code}_{event_id}_{round_number}"

        try:
            data = self._fetch_with_cache(
                cache_key=cache_key,
                fetch_func=fetch_from_api,
                cache_message=f"Loading GAC match from cache...",
                fetch_message=f"Fetching GAC match details from API...",
            )
            return self._parse_gac_match(data)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                print(f"GAC match details endpoint not available")
                return GACRoundResult()
            raise

    def _parse_gac_match(self, data: Dict[str, Any]) -> GACRoundResult:
        """Parse raw API response into GACRoundResult model."""
        match_data = data.get("data", data)

        player_attacks = []
        for attack_data in match_data.get("player_attacks", []):
            battle = self._parse_gac_battle(attack_data)
            player_attacks.append(battle)

        opponent_attacks = []
        for attack_data in match_data.get("opponent_attacks", []):
            battle = self._parse_gac_battle(attack_data)
            opponent_attacks.append(battle)

        return GACRoundResult(
            opponent_ally_code=match_data.get("opponent_ally_code"),
            opponent_name=match_data.get("opponent_name"),
            opponent_galactic_power=match_data.get("opponent_galactic_power"),
            player_score=match_data.get("player_score", 0),
            opponent_score=match_data.get("opponent_score", 0),
            player_attacks=player_attacks,
            opponent_attacks=opponent_attacks,
            was_victory=match_data.get("was_victory"),
        )

    def _parse_gac_battle(self, battle_data: Dict[str, Any]) -> GACBattle:
        """Parse a single battle from match data."""
        attack_squad = None
        defense_squad = None

        if "attack_squad" in battle_data:
            attack_squad = self._parse_gac_squad(battle_data["attack_squad"])
        if "defense_squad" in battle_data:
            defense_squad = self._parse_gac_squad(battle_data["defense_squad"])

        return GACBattle(
            attack_squad=attack_squad,
            defense_squad=defense_squad,
            banners=battle_data.get("banners", 0),
            attempt_number=battle_data.get("attempt_number", 1),
            was_successful=battle_data.get("was_successful", False),
            territory=battle_data.get("territory"),
        )

    def _parse_gac_squad(self, squad_data: Dict[str, Any]) -> GACSquad:
        """Parse a squad from match data."""
        units = []
        unit_list = squad_data.get("units", squad_data.get("members", []))

        for idx, unit_data in enumerate(unit_list):
            if isinstance(unit_data, str):
                # Simple base_id format
                unit = GACSquadUnit(base_id=unit_data, is_leader=(idx == 0))
            else:
                # Full unit data format
                unit = GACSquadUnit(
                    base_id=unit_data.get("base_id", ""),
                    name=unit_data.get("name"),
                    gear_level=unit_data.get("gear_level"),
                    relic_tier=unit_data.get("relic_tier"),
                    rarity=unit_data.get("rarity"),
                    power=unit_data.get("power"),
                    is_leader=unit_data.get("is_leader", idx == 0),
                )
            units.append(unit)

        return GACSquad(
            units=units,
            leader_base_id=squad_data.get("leader_base_id", squad_data.get("leader")),
            banners_earned=squad_data.get("banners_earned"),
            banners_lost=squad_data.get("banners_lost"),
            survived=squad_data.get("survived", True),
        )

    def analyze_gac_tendencies(
        self,
        ally_code: str,
        format_filter: Optional[GACFormat] = None,
        include_opponents: bool = False,
    ) -> GACMatchAnalysis:
        """
        Analyze a player's GAC tendencies to identify likely attackers and defenders.

        This analyzes historical match data to determine:
        - Squads frequently used on offense
        - Squads frequently placed on defense
        - Common leader usage patterns

        Args:
            ally_code: The player's ally code
            format_filter: Optional filter for 3v3 or 5v5 analysis
            include_opponents: Whether to fetch opponent data for comparison

        Returns:
            GACMatchAnalysis with attack/defense tendency information
        """
        normalized_ally_code = ally_code.replace("-", "")

        # Try to get GAC history first
        try:
            history = self.get_gac_history(ally_code, format_filter=format_filter)
        except Exception as e:
            print(f"Could not fetch GAC history: {e}")
            history = GACHistory(ally_code=int(normalized_ally_code), events=[])

        attack_squads: List[GACSquad] = []
        defense_squads: List[GACSquad] = []
        attack_leaders: Dict[str, int] = {}
        defense_leaders: Dict[str, int] = {}

        # Analyze each event's rounds
        for event in history.events:
            for round_result in event.rounds:
                # Collect attack squads
                for battle in round_result.player_attacks:
                    if battle.attack_squad:
                        attack_squads.append(battle.attack_squad)
                        leader = battle.attack_squad.leader
                        if leader:
                            attack_leaders[leader.base_id] = (
                                attack_leaders.get(leader.base_id, 0) + 1
                            )

                # Collect defense squads from opponent attacks (what they attacked)
                for battle in round_result.opponent_attacks:
                    if battle.defense_squad:
                        defense_squads.append(battle.defense_squad)
                        leader = battle.defense_squad.leader
                        if leader:
                            defense_leaders[leader.base_id] = (
                                defense_leaders.get(leader.base_id, 0) + 1
                            )

        gac_format = format_filter or GACFormat.FIVE_V_FIVE

        return GACMatchAnalysis(
            ally_code=int(normalized_ally_code),
            format=gac_format,
            likely_attack_squads=attack_squads[:10],  # Top 10 most recent
            likely_defense_squads=defense_squads[:10],
            attack_squad_frequency=attack_leaders,
            defense_squad_frequency=defense_leaders,
        )

    def get_gac_leaderboard(
        self,
        league: str = "Kyber",
        division: int = 1,
        limit: int = 50,
    ) -> List[GACBracketPlayer]:
        """
        Fetch GAC leaderboard for a specific league and division.

        Args:
            league: League name (Carbonite, Bronzium, Chromium, Aurodium, Kyber)
            division: Division number (1-5, where 1 is highest)
            limit: Maximum number of players to return

        Returns:
            List of players on the leaderboard
        """

        def fetch_from_api():
            url = f"{self.base_url}/gac-leaderboard/"
            params = {"league": league, "division": division, "limit": limit}
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()

        cache_key = f"gac_leaderboard_{league}_{division}"

        try:
            data = self._fetch_with_cache(
                cache_key=cache_key,
                fetch_func=fetch_from_api,
                cache_message=f"Loading GAC leaderboard from cache...",
                fetch_message=f"Fetching GAC leaderboard from API...",
            )

            players = []
            player_list = data.get("data", data.get("players", []))
            for player_data in player_list[:limit]:
                player = GACBracketPlayer(
                    ally_code=player_data.get("ally_code", 0),
                    name=player_data.get("name", "Unknown"),
                    skill_rating=player_data.get("skill_rating", 0),
                    galactic_power=player_data.get("galactic_power", 0),
                    league=player_data.get("league_name", league),
                    division=player_data.get("division_number", division),
                    wins=player_data.get("wins", 0),
                    losses=player_data.get("losses", 0),
                    guild_name=player_data.get("guild_name"),
                )
                players.append(player)

            return players
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                print(f"GAC leaderboard endpoint not available")
                return []
            raise

    def get_player_gac_summary(self, ally_code: str) -> Dict[str, Any]:
        """
        Get a summary of a player's GAC stats from their profile.

        This uses data already available in the player profile endpoint.

        Args:
            ally_code: The player's ally code

        Returns:
            Dictionary with GAC summary statistics
        """
        player = self.get_player_units(ally_code)
        player_data = player.data

        return {
            "ally_code": player_data.ally_code,
            "name": player_data.name,
            "skill_rating": player_data.skill_rating,
            "league": player_data.league_name,
            "division": player_data.division_number,
            "league_image": player_data.league_image,
            "division_image": player_data.division_image,
            "lifetime_stats": {
                "full_clears": player_data.season_full_clears,
                "successful_defends": player_data.season_successful_defends,
                "league_score": player_data.season_league_score,
                "undersized_wins": player_data.season_undersized_squad_wins,
                "promotions_earned": player_data.season_promotions_earned,
                "banners_earned": player_data.season_banners_earned,
                "offensive_battles_won": player_data.season_offensive_battles_won,
                "territories_defeated": player_data.season_territories_defeated,
            },
        }
