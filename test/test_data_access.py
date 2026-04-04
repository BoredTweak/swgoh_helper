"""
Unit tests for the SWGOH.gg data access layer.
"""

import pytest
from unittest.mock import Mock, patch

from swgoh_helper.data_access import (
    BaseApiClient,
    SwgohDataService,
    UnitsRepository,
    PlayersRepository,
    GuildsRepository,
    GearRepository,
    AbilitiesRepository,
    StatDefinitionsRepository,
)
from swgoh_helper.cache_manager import CacheManager
from swgoh_helper.models import (
    Unit,
    UnitsResponse,
    PlayerResponse,
    PlayerData,
    GuildResponse,
    GuildData,
    GearPiece,
)


class TestBaseApiClient:
    """Tests for the BaseApiClient class."""

    def test_init_creates_default_cache_manager(self):
        """Test that a default cache manager is created when none provided."""
        client = BaseApiClient("test_key")
        assert client.cache is not None
        assert isinstance(client.cache, CacheManager)

    def test_init_uses_provided_cache_manager(self):
        """Test that provided cache manager is used."""
        cache = CacheManager()
        client = BaseApiClient("test_key", cache)
        assert client.cache is cache

    @patch("swgoh_helper.data_access.base.requests.get")
    def test_get_makes_authenticated_request(self, mock_get):
        """Test that GET requests include authentication headers."""
        mock_response = Mock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        client = BaseApiClient("test_key_123")
        client.get("/units/")

        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args
        assert call_kwargs[1]["headers"] == {"x-gg-bot-access": "test_key_123"}

    def test_fetch_with_cache_returns_cached_data(self):
        """Test that cached data is returned when available."""
        cache = Mock()
        cache.get.return_value = {"cached": True}
        client = BaseApiClient("test_key", cache)

        result = client.fetch_with_cache(
            cache_key="test_key",
            fetch_func=lambda: {"fetched": True},
            silent=True,
        )

        assert result == {"cached": True}
        cache.set.assert_not_called()

    def test_fetch_with_cache_fetches_and_caches_on_miss(self):
        """Test that data is fetched and cached on cache miss."""
        cache = Mock()
        cache.get.return_value = None
        client = BaseApiClient("test_key", cache)

        result = client.fetch_with_cache(
            cache_key="test_key",
            fetch_func=lambda: {"fetched": True},
            silent=True,
        )

        assert result == {"fetched": True}
        cache.set.assert_called_once_with("test_key", {"fetched": True})


class TestUnitsRepository:
    """Tests for the UnitsRepository class."""

    def test_get_cache_key(self):
        """Test cache key generation."""
        client = Mock()
        repo = UnitsRepository(client)
        assert repo.get_cache_key("units") == "units"
        assert repo.get_cache_key("characters") == "characters"

    def test_build_units_lookup(self):
        """Test building a lookup dictionary from units."""
        client = Mock()
        repo = UnitsRepository(client)

        units = [
            Mock(base_id="UNIT1"),
            Mock(base_id="UNIT2"),
        ]

        lookup = repo.build_units_lookup(units)

        assert len(lookup) == 2
        assert "UNIT1" in lookup
        assert "UNIT2" in lookup


class TestPlayersRepository:
    """Tests for the PlayersRepository class."""

    def test_get_cache_key_normalizes_ally_code(self):
        """Test that ally codes are normalized in cache keys."""
        client = Mock()
        repo = PlayersRepository(client)

        assert repo.get_cache_key("123-456-789") == "player_123456789"
        assert repo.get_cache_key("123456789") == "player_123456789"

    def test_partition_by_cache_status(self):
        """Test partitioning ally codes by cache status."""
        client = Mock()
        client.is_cache_valid = Mock(side_effect=lambda k: k == "player_111")
        repo = PlayersRepository(client)

        cached, uncached = repo._partition_by_cache_status([111, 222])

        assert cached == [111]
        assert uncached == [222]


class TestGuildRepository:
    """Tests for the GuildsRepository class."""

    def test_get_cache_key(self):
        """Test cache key generation for guilds."""
        client = Mock()
        players_repo = Mock()
        repo = GuildsRepository(client, players_repo)

        assert repo.get_cache_key("guild123") == "guild_guild123"


class TestGearRepository:
    """Tests for the GearRepository class."""

    def test_build_gear_lookup(self):
        """Test building gear lookup dictionary."""
        client = Mock()
        repo = GearRepository(client)

        gear_data = [
            {
                "base_id": "GEAR1",
                "name": "Gear 1",
                "tier": 1,
                "mark": "I",
                "required_level": 1,
                "cost": 100,
                "image": "",
                "url": "",
            },
            {
                "base_id": "GEAR2",
                "name": "Gear 2",
                "tier": 2,
                "mark": "II",
                "required_level": 10,
                "cost": 200,
                "image": "",
                "url": "",
            },
        ]

        lookup = repo._build_gear_lookup(gear_data)

        assert len(lookup) == 2
        assert "GEAR1" in lookup
        assert lookup["GEAR1"].tier == 1


class TestSwgohDataService:
    """Tests for the SwgohDataService class."""

    def test_init_creates_all_repositories(self):
        """Test that all repositories are created on init."""
        with patch.object(BaseApiClient, "__init__", return_value=None):
            service = SwgohDataService.__new__(SwgohDataService)
            service._client = Mock()
            service._units = Mock()
            service._players = Mock()
            service._guilds = Mock()
            service._gear = Mock()
            service._abilities = Mock()
            service._stats = Mock()

            assert service._units is not None
            assert service._players is not None
            assert service._guilds is not None
            assert service._gear is not None
            assert service._abilities is not None
            assert service._stats is not None

    def test_repository_properties(self):
        """Test that repository properties return correct instances."""
        with patch.object(BaseApiClient, "__init__", return_value=None):
            service = SwgohDataService.__new__(SwgohDataService)
            service._client = Mock()
            service._units = Mock(spec=UnitsRepository)
            service._players = Mock(spec=PlayersRepository)
            service._guilds = Mock(spec=GuildsRepository)
            service._gear = Mock(spec=GearRepository)
            service._abilities = Mock(spec=AbilitiesRepository)
            service._stats = Mock(spec=StatDefinitionsRepository)

            assert service.units is service._units
            assert service.players is service._players
            assert service.guilds is service._guilds
            assert service.gear is service._gear
            assert service.abilities is service._abilities
            assert service.stats is service._stats
