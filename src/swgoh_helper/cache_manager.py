"""
Cache manager for storing and retrieving API responses with time-based expiration.
"""

import json
import os
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar


T = TypeVar("T")


class CacheManager:
    """
    Manages time-based file cache for API responses.
    """

    IO_RETRY_COUNT = 5
    IO_RETRY_DELAY_SECONDS = 0.05

    def __init__(self, cache_dir: str = "data", cache_duration_hours: int = 6):
        self.cache_dir = Path(cache_dir)
        self.cache_duration = timedelta(hours=cache_duration_hours)
        self.cache_dir.mkdir(exist_ok=True)

    def _get_cache_path(self, cache_key: str) -> Path:
        return self.cache_dir / f"{cache_key}.json"

    def is_valid(self, cache_key: str) -> bool:
        """Check if a cache entry exists and is still valid."""
        cache_path = self._get_cache_path(cache_key)

        if not cache_path.exists():
            return False

        try:
            cache_data = self._load_cache_file(cache_path)
            return self._is_timestamp_valid(cache_data.get("timestamp"))
        except (json.JSONDecodeError, KeyError, ValueError, OSError):
            return False

    def get(self, cache_key: str) -> Optional[dict]:
        """Retrieve data from cache if valid, otherwise None."""
        cache_path = self._get_cache_path(cache_key)

        if not cache_path.exists():
            return None

        try:
            cache_data = self._load_cache_file(cache_path)
            if not self._is_timestamp_valid(cache_data.get("timestamp")):
                return None
            return cache_data.get("data")
        except (json.JSONDecodeError, KeyError, ValueError, OSError):
            return None

    def set(self, cache_key: str, data: Any) -> None:
        """Store data in cache with current timestamp."""
        cache_path = self._get_cache_path(cache_key)
        cache_data = {"timestamp": datetime.now().isoformat(), "data": data}

        self._write_cache_file(cache_path, cache_data)

        self.prune_expired()

    def invalidate(self, cache_key: str) -> None:
        """Remove a cache entry."""
        cache_path = self._get_cache_path(cache_key)
        if cache_path.exists():
            self._retry_io(cache_path.unlink)

    def clear_all(self) -> None:
        """Remove all cache entries."""
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                self._retry_io(cache_file.unlink)
            except OSError:
                continue

    def prune_expired(self) -> int:
        """Delete cached files whose timestamps have exceeded the TTL.

        Only removes files that contain the ``{"timestamp": ...}`` wrapper
        written by :meth:`set`, so static data files are left untouched.

        Returns:
            Number of files removed.
        """
        removed = 0
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                cache_data = self._load_cache_file(cache_file)
                timestamp = cache_data.get("timestamp")
                if timestamp is None:
                    continue
                if not self._is_timestamp_valid(timestamp):
                    self._retry_io(cache_file.unlink)
                    removed += 1
            except (json.JSONDecodeError, KeyError, ValueError, OSError):
                continue
        return removed

    def _write_cache_file(self, cache_path: Path, cache_data: dict) -> None:
        fd, tmp_path = tempfile.mkstemp(
            prefix=f"{cache_path.stem}.",
            suffix=".tmp",
            dir=str(self.cache_dir),
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            self._retry_io(Path(tmp_path).replace, cache_path)
        finally:
            tmp = Path(tmp_path)
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass

    def _retry_io(self, operation: Callable[..., T], *args: Any) -> T:
        last_error: Optional[OSError] = None
        for attempt in range(self.IO_RETRY_COUNT):
            try:
                return operation(*args)
            except OSError as error:
                last_error = error
                if attempt == self.IO_RETRY_COUNT - 1:
                    break
                time.sleep(self.IO_RETRY_DELAY_SECONDS)
        if last_error is not None:
            raise last_error
        raise OSError("Unknown cache I/O failure")

    def _load_cache_file(self, cache_path: Path) -> dict:
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _is_timestamp_valid(self, timestamp: Optional[str]) -> bool:
        if not timestamp:
            return False

        cached_time = datetime.fromisoformat(timestamp)
        return datetime.now() - cached_time < self.cache_duration
