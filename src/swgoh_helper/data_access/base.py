"""
Base API client for SWGOH.gg API with intelligent caching.

This module provides the foundational HTTP client that handles:
- Authentication with the SWGOH.gg API
- Request caching to minimize API calls
- Rate limiting and error handling
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional, TypeVar

import requests

from ..cache_manager import CacheManager
from ..progress import ProgressNotifier


T = TypeVar("T")


class BaseApiClient:
    """
    Low-level HTTP client for SWGOH.gg API operations.

    Provides authenticated HTTP requests with caching support.
    All repositories should use this client for API interactions.
    """

    BASE_URL = "https://swgoh.gg/api"

    def __init__(
        self,
        api_key: str,
        cache_manager: Optional[CacheManager] = None,
        progress: Optional[ProgressNotifier] = None,
    ):
        """
        Initialize the API client.

        Args:
            api_key: API key for SWGOH.gg authentication
            cache_manager: Optional cache manager instance (creates default if None)
            progress: Optional progress notifier for status updates
        """
        self._api_key = api_key
        self._headers = {"x-gg-bot-access": api_key}
        self._cache = cache_manager or CacheManager()
        self._progress = progress or ProgressNotifier()

    @property
    def progress(self) -> ProgressNotifier:
        """Access the progress notifier."""
        return self._progress

    @property
    def cache(self) -> CacheManager:
        """Access the cache manager."""
        return self._cache

    def get(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Perform an authenticated GET request to the API.

        Args:
            endpoint: API endpoint path (e.g., "/units/")
            params: Optional query parameters

        Returns:
            JSON response as a dictionary

        Raises:
            requests.exceptions.HTTPError: For non-2xx responses
        """
        url = f"{self.BASE_URL}{endpoint}"
        response = requests.get(url, headers=self._headers, params=params)
        response.raise_for_status()
        return response.json()

    def fetch_with_cache(
        self,
        cache_key: str,
        fetch_func: Callable[[], Any],
        cache_message: str = "",
        fetch_message: str = "",
        silent: bool = False,
    ) -> Any:
        """
        Fetch data with caching support.

        Args:
            cache_key: Unique key for caching the result
            fetch_func: Function to call if cache miss
            cache_message: Message to print on cache hit
            fetch_message: Message to print on cache miss
            silent: Suppress all output if True

        Returns:
            Cached or freshly fetched data
        """
        cached_data = self._cache.get(cache_key)
        if cached_data is not None:
            if not silent and cache_message:
                self._progress.update(cache_message)
            return cached_data

        if not silent and fetch_message:
            self._progress.update(fetch_message)
        data = fetch_func()
        self._cache.set(cache_key, data)
        return data

    def invalidate_cache(self, cache_key: str) -> None:
        """Invalidate a specific cache entry."""
        self._cache.invalidate(cache_key)

    def is_cache_valid(self, cache_key: str) -> bool:
        """Check if a cache entry is valid."""
        return self._cache.is_valid(cache_key)


class BaseRepository(ABC):
    """
    Abstract base class for all data repositories.

    Repositories encapsulate data access logic for specific domains.
    They use the BaseApiClient for HTTP operations and provide
    domain-specific methods with proper typing.
    """

    def __init__(self, client: BaseApiClient):
        """
        Initialize the repository with an API client.

        Args:
            client: The base API client for HTTP operations
        """
        self._client = client

    @property
    def client(self) -> BaseApiClient:
        """Access the underlying API client."""
        return self._client

    @abstractmethod
    def get_cache_key(self, *args: Any, **kwargs: Any) -> str:
        """
        Generate a cache key for the given parameters.

        Subclasses must implement this to provide consistent cache keys.
        """
        pass
