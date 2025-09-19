"""In-memory cache backend for TTSKit.

Implements a simple, thread-unsafe dictionary-based cache with TTL support and
automatic expiration on access.
"""

from time import monotonic as _monotonic
from typing import Any

from .base import BaseCache


class MemoryCache(BaseCache):
    """In-memory cache implementation."""

    def __init__(self, default_ttl: int = 3600):
        """Initialize memory cache.

        Args:
            default_ttl: Default time to live in seconds
        """
        super().__init__(default_ttl)
        self._cache: dict[str, bytes] = {}
        self._timestamps: dict[str, float] = {}

    def _is_expired(self, key: str) -> bool:
        """Check if key is expired.

        Args:
            key: Cache key

        Returns:
            True if key is expired, False otherwise
        """
        if key not in self._timestamps:
            return True
        return _monotonic() > self._timestamps[key]

    def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache.

        Args:
            key: Cache key
            default: Default value if key not found

        Returns:
            Cached value or default if not found
        """
        if key in self._cache:
            if self._is_expired(key):
                # Auto-evict expired entries on access
                self._cache.pop(key, None)
                self._timestamps.pop(key, None)
                self._record_miss()
            else:
                self._record_hit()
                return self._cache[key]

        self._record_miss()
        return default

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (optional)
        """
        ttl = ttl if ttl is not None else self.default_ttl
        self._cache[key] = value
        self._timestamps[key] = _monotonic() + float(ttl)
        self._record_set()

    def delete(self, key: str) -> bool:
        """Delete value from cache.

        Args:
            key: Cache key

        Returns:
            True if key was deleted, False if not found
        """
        if key in self._cache:
            del self._cache[key]
            del self._timestamps[key]
            self._record_delete()
            return True
        return False

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        self._timestamps.clear()

    def exists(self, key: str) -> bool:
        """Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists, False otherwise
        """
        return key in self._cache and not self._is_expired(key)

    def keys(self) -> list[str]:
        """Get all cache keys.

        Returns:
            List of cache keys
        """
        # Clean up expired keys first
        current_time = _monotonic()
        expired_keys = [
            key
            for key, timestamp in self._timestamps.items()
            if current_time > timestamp
        ]
        for key in expired_keys:
            self._cache.pop(key, None)
            self._timestamps.pop(key, None)

        return list(self._cache.keys())

    def values(self) -> list[Any]:
        """Get all cache values.

        Returns:
            List of cache values
        """
        # Clean up expired keys first
        current_time = _monotonic()
        expired_keys = [
            key
            for key, timestamp in self._timestamps.items()
            if current_time > timestamp
        ]
        for key in expired_keys:
            self._cache.pop(key, None)
            self._timestamps.pop(key, None)

        return list(self._cache.values())

    def items(self) -> list[tuple[str, Any]]:
        """Get all cache items.

        Returns:
            List of (key, value) tuples
        """
        # Clean up expired keys first
        current_time = _monotonic()
        expired_keys = [
            key
            for key, timestamp in self._timestamps.items()
            if current_time > timestamp
        ]
        for key in expired_keys:
            self._cache.pop(key, None)
            self._timestamps.pop(key, None)

        return list(self._cache.items())

    def size(self) -> int:
        """Get number of cache entries.

        Returns:
            Number of cache entries

        Notes:
            Cleans up expired keys before counting to reflect only valid entries.
        """
        # Clean up expired keys first
        current_time = _monotonic()
        expired_keys = [
            key
            for key, timestamp in self._timestamps.items()
            if current_time > timestamp
        ]
        for key in expired_keys:
            self._cache.pop(key, None)
            self._timestamps.pop(key, None)

        return len(self._cache)

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics

        Notes:
            Includes base stats plus memory-specific details like total keys, expired keys cleaned up during this call, and estimated memory usage in bytes.
        """
        # Clean up expired entries
        current_time = _monotonic()
        expired_keys = [
            key
            for key, timestamp in self._timestamps.items()
            if current_time > timestamp
        ]

        for key in expired_keys:
            self._cache.pop(key, None)
            self._timestamps.pop(key, None)

        # Get base stats from parent class
        base_stats = super().get_stats()

        # Add memory-specific stats
        memory_usage = sum(
            (
                len(value)
                if isinstance(value, bytes | bytearray)
                else len(str(value).encode("utf-8"))
            )
            for value in self._cache.values()
        )

        return {
            **base_stats,
            "total_keys": len(self._cache),
            "expired_keys": len(expired_keys),
            "memory_usage_bytes": memory_usage,
            "memory_usage": memory_usage,
        }
# Default global in-memory cache instance for quick access without instantiation
memory_cache = MemoryCache()
