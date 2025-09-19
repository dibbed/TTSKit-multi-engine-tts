"""Base classes for TTSKit's caching system.

This module provides an abstract interface for synchronous cache operations and a base class with shared functionality, such as tracking cache hits, misses, and other statistics.
"""

from abc import ABC, abstractmethod
from typing import Any


class CacheInterface(ABC):
    """Abstract base class for cache implementations (synchronous interface)."""

    @abstractmethod
    def get(self, key: str) -> Any | None:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        raise NotImplementedError

    @abstractmethod
    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache (arbitrary serializable object)
            ttl: Time to live in seconds (optional)
        """
        raise NotImplementedError

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete value from cache.

        Args:
            key: Cache key

        Returns:
            True if key was deleted, False if not found
        """
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        """Clear all cache entries."""
        raise NotImplementedError

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists, False otherwise
        """
        raise NotImplementedError

    @abstractmethod
    def get_stats(self) -> dict[str, int]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        raise NotImplementedError


class BaseCache(CacheInterface):
    """Base cache implementation with common functionality."""

    def __init__(self, default_ttl: int = 3600):
        """Initialize base cache.

        Args:
            default_ttl: Default time to live in seconds
        """
        self.default_ttl = default_ttl
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0,
        }

    def _increment_stat(self, stat_name: str) -> None:
        """Increment a specific statistic counter.

        Args:
            stat_name: The name of the statistic to increment
        """
        if stat_name in self._stats:
            self._stats[stat_name] += 1

    def _record_hit(self) -> None:
        """Record a cache hit."""
        self._increment_stat("hits")

    def _record_miss(self) -> None:
        """Record a cache miss."""
        self._increment_stat("misses")

    def _record_set(self) -> None:
        """Record a cache set operation."""
        self._increment_stat("sets")

    def _record_delete(self) -> None:
        """Record a cache delete operation."""
        self._increment_stat("deletes")

    def _record_error(self) -> None:
        """Record a cache error."""
        self._increment_stat("errors")

    def get_stats(self) -> dict[str, int]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics

        Notes:
            Includes calculated hit rate as (hits / total_requests) * 100.
        """
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = (
            (self._stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        )

        return {
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "sets": self._stats["sets"],
            "deletes": self._stats["deletes"],
            "errors": self._stats["errors"],
            "hit_rate": round(hit_rate, 2),
            "total_requests": total_requests,
        }

    def reset_stats(self) -> None:
        """Reset cache statistics."""
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0,
        }
