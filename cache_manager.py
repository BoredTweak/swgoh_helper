"""
Cache manager for storing and retrieving API responses with time-based expiration.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional


class CacheManager:
    """
    Manages time-based file cache for API responses.
    """

    def __init__(self, cache_dir: str = "data", cache_duration_hours: int = 1):
        """
        Initialize the cache manager.

        Args:
            cache_dir: Directory path for cache storage
            cache_duration_hours: How long cache entries remain valid (in hours)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_duration = timedelta(hours=cache_duration_hours)
        self.cache_dir.mkdir(exist_ok=True)

    def _get_cache_path(self, cache_key: str) -> Path:
        """
        Get the file path for a cache key.

        Args:
            cache_key: Unique identifier for the cached data

        Returns:
            Path object pointing to the cache file
        """
        return self.cache_dir / f"{cache_key}.json"

    def is_valid(self, cache_key: str) -> bool:
        """
        Check if a cache entry exists and is still valid.

        Args:
            cache_key: Unique identifier for the cached data

        Returns:
            True if cache exists and is not expired, False otherwise
        """
        cache_path = self._get_cache_path(cache_key)

        if not cache_path.exists():
            return False

        try:
            cache_data = self._load_cache_file(cache_path)
            return self._is_timestamp_valid(cache_data.get("timestamp"))
        except (json.JSONDecodeError, KeyError, ValueError, OSError):
            return False

    def get(self, cache_key: str) -> Optional[dict]:
        """
        Retrieve data from cache if valid.

        Args:
            cache_key: Unique identifier for the cached data

        Returns:
            Cached data dictionary, or None if cache is invalid/missing
        """
        if not self.is_valid(cache_key):
            return None

        cache_path = self._get_cache_path(cache_key)
        try:
            cache_data = self._load_cache_file(cache_path)
            return cache_data.get("data")
        except (json.JSONDecodeError, KeyError, OSError):
            return None

    def set(self, cache_key: str, data: Any) -> None:
        """
        Store data in cache with current timestamp.

        Args:
            cache_key: Unique identifier for the cached data
            data: Data to cache (must be JSON-serializable)
        """
        cache_path = self._get_cache_path(cache_key)
        cache_data = {"timestamp": datetime.now().isoformat(), "data": data}

        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)

    def invalidate(self, cache_key: str) -> None:
        """
        Remove a cache entry.

        Args:
            cache_key: Unique identifier for the cached data
        """
        cache_path = self._get_cache_path(cache_key)
        if cache_path.exists():
            cache_path.unlink()

    def clear_all(self) -> None:
        """Remove all cache entries."""
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()

    def _load_cache_file(self, cache_path: Path) -> dict:
        """
        Load and parse a cache file.

        Args:
            cache_path: Path to the cache file

        Returns:
            Parsed cache data dictionary

        Raises:
            json.JSONDecodeError: If file contains invalid JSON
            OSError: If file cannot be read
        """
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _is_timestamp_valid(self, timestamp: Optional[str]) -> bool:
        """
        Check if a timestamp is within the cache duration.

        Args:
            timestamp: ISO format timestamp string

        Returns:
            True if timestamp is valid and not expired, False otherwise
        """
        if not timestamp:
            return False

        cached_time = datetime.fromisoformat(timestamp)
        return datetime.now() - cached_time < self.cache_duration
