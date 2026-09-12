"""Redis-backed cache for TTSKit.

This module offers a persistent caching solution using Redis, including automatic serialization of common types and built-in statistics. It handles connection issues gracefully by falling back when Redis isn't available.
"""

from typing import Any

from ..utils.logging_config import get_logger
from .base import BaseCache

logger = get_logger(__name__)

# Flag to indicate if the Redis library can be imported
REDIS_AVAILABLE = False
try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    pass


class RedisCache(BaseCache):
    """Redis-based cache implementation."""

    def __init__(
        self,
        redis_url: str | None = None,
        url: str | None = None,
        default_ttl: int = 3600,
        key_prefix: str = "",
        dedicated_db: bool = False,
        **kwargs,
    ):
        """Initialize the Redis cache.

        Args:
            redis_url: Preferred Redis connection URL.
            url: Alternative URL for backward compatibility.
            default_ttl: Default time-to-live in seconds.
            key_prefix: Prefix for keys to support shared Redis instances.
            dedicated_db: Whether Redis DB is dedicated (permitting flushdb).
            **kwargs: Extra parameters passed to the Redis client.

        Notes:
            Prioritizes redis_url over url, defaulting to "redis://localhost:6379/0".
            Creates the client immediately for easier testing and pings to check connectivity.
            Logs a warning if connection fails but still allows initialization to proceed.
        """
        if not REDIS_AVAILABLE:
            raise ImportError(
                "Redis package not installed. Install with: pip install redis"
            )

        super().__init__(default_ttl)
        self.url = redis_url or url or "redis://localhost:6379/0"
        self.redis_kwargs = kwargs
        self.key_prefix = key_prefix
        self.dedicated_db = dedicated_db
        self._client: redis.Redis | None = None
        try:
            self._client = redis.Redis.from_url(self.url, **kwargs)
            self._client.ping()
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            self._client = None

    def _format_key(self, key: str) -> str:
        """Add namespace prefix to key if configured and not already prefixed."""
        if self.key_prefix and not key.startswith(self.key_prefix):
            return f"{self.key_prefix}{key}"
        return key

    def _strip_key(self, key: str) -> str:
        """Strip namespace prefix from key if present."""
        if self.key_prefix and key.startswith(self.key_prefix):
            return key[len(self.key_prefix) :]
        return key

    def _get_client(self) -> redis.Redis:
        """Get the Redis client, creating it if needed.

        Returns:
            The active Redis client instance.

        Notes:
            Recreates the client if it's None, using the stored URL and parameters.
            Designed to allow easy patching of the Redis constructor in tests.
        """
        if self._client is None:
            self._client = redis.Redis.from_url(self.url, **self.redis_kwargs)
        return self._client

    def get(self, key: str, default: Any = None) -> Any:
        """Get value from Redis cache.

        Args:
            key: Cache key
            default: Default value if key not found

        Returns:
            Cached value or default if not found

        Notes:
            Tries to deserialize the value as JSON if possible; falls back to UTF-8 decoding for strings/bytes, or returns raw if undecodable.
            Records a hit only if a valid value is retrieved.
        """
        if self._client is None:
            self._record_miss()
            return default
        client = self._get_client()
        full_key = self._format_key(key)
        value = client.get(full_key)
        if value is not None:
            self._record_hit()
            try:
                import json

                if isinstance(value, bytes | bytearray):
                    try:
                        return json.loads(value.decode("utf-8"))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        return value.decode("utf-8")
                if isinstance(value, str):
                    return json.loads(value)
                return value
            except Exception:
                if isinstance(value, bytes | bytearray):
                    try:
                        return value.decode("utf-8")
                    except UnicodeDecodeError:
                        return value
                return value
        else:
            self._record_miss()
            return default

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set value in Redis cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (optional)

        Notes:
            Automatically serializes dictionaries and lists to JSON strings.
            Sets expiration separately from the initial set operation for better testability.
            Records an error if no client is available.
        """
        if self._client is None:
            self._record_error()
            return
        client = self._get_client()
        if isinstance(value, (dict, list)):
            import json

            value_to_store = json.dumps(value)
        else:
            value_to_store = value

        full_key = self._format_key(key)
        ttl_to_use = ttl if ttl is not None else self.default_ttl
        client.set(full_key, value_to_store)
        if ttl_to_use is not None:
            client.expire(full_key, ttl_to_use)
        self._record_set()

    def delete(self, key: str) -> bool:
        """Delete value from Redis cache.

        Args:
            key: Cache key

        Returns:
            True if key was deleted, False if not found
        """
        if self._client is None:
            return False
        client = self._get_client()
        full_key = self._format_key(key)
        result = client.delete(full_key)
        if result > 0:
            self._record_delete()
        return result > 0

    def clear(self) -> None:
        """Clear all cache entries."""
        if self._client is None:
            return
        client = self._get_client()
        if self.dedicated_db or not self.key_prefix:
            client.flushdb()
        else:
            pattern = f"{self.key_prefix}*"
            keys_to_delete = []
            if hasattr(client, "scan_iter"):
                try:
                    for k in client.scan_iter(match=pattern):
                        keys_to_delete.append(k)
                except Exception as e:
                    logger.warning(f"Error scanning keys for clear: {e}")
            elif hasattr(client, "keys"):
                try:
                    keys_to_delete = client.keys(pattern)
                except Exception as e:
                    logger.warning(f"Error listing keys for clear: {e}")

            if keys_to_delete:
                try:
                    client.delete(*keys_to_delete)
                except Exception as e:
                    logger.warning(f"Error deleting keys in clear: {e}")

    def exists(self, key: str) -> bool:
        """Check if key exists in Redis cache.

        Args:
            key: Cache key

        Returns:
            True if key exists, False otherwise
        """
        if self._client is None:
            return False
        client = self._get_client()
        full_key = self._format_key(key)
        result = client.exists(full_key)
        return result > 0

    def keys(self) -> list[str]:
        """Get all cache keys.

        Returns:
            List of cache keys

        Notes:
            Decodes byte keys to UTF-8 strings; returns empty list if no client.
        """
        if self._client is None:
            return []
        client = self._get_client()
        pattern = f"{self.key_prefix}*" if self.key_prefix else "*"
        try:
            if hasattr(client, "scan_iter") and self.key_prefix:
                raw_keys = list(client.scan_iter(match=pattern))
            else:
                raw_keys = client.keys(pattern)
        except Exception as e:
            logger.warning(f"Error getting keys: {e}")
            return []
        return [
            self._strip_key(key.decode("utf-8") if isinstance(key, bytes) else key)
            for key in raw_keys
        ]

    def size(self) -> int:
        """Get number of cache entries.

        Returns:
            Number of cache entries

        Notes:
            Uses Redis DBSIZE command or prefix-filtered count.
        """
        if self._client is None:
            return 0
        client = self._get_client()
        if self.dedicated_db or not self.key_prefix:
            return client.dbsize()
        return len(self.keys())

    def ttl(self, key: str) -> int:
        """Get time to live for a key.

        Args:
            key: Cache key

        Returns:
            TTL in seconds (-1 for no expiration, -2 if key doesn't exist)

        Notes:
            Returns -2 if no client. Exceptions are allowed to propagate for testing error handling.
        """
        if self._client is None:
            return -2
        client = self._get_client()
        full_key = self._format_key(key)
        return client.ttl(full_key)

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics

        Notes:
            Pulls in Redis server details like memory usage, peak memory, connected clients, and command count.
            Includes the current database size. Falls back to base stats if there's an error fetching info.
        """
        if self._client is None:
            return super().get_stats()
        try:
            client = self._get_client()
            info = client.info()

            base_stats = super().get_stats()

            return {
                **base_stats,
                "redis_memory_used": info.get("used_memory", 0),
                "redis_memory_peak": info.get("used_memory_peak", 0),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "used_memory": info.get(
                    "used_memory_human", info.get("used_memory", 0)
                ),
                "redis_keys": client.dbsize(),
            }

        except Exception as e:
            logger.error(f"Redis stats error: {e}")
            return super().get_stats()

    def close(self) -> None:
        """Close the Redis connection.

        Notes:
            Logs any errors during close but proceeds to set client to None.
        """
        if self._client:
            try:
                self._client.close()
            except Exception as e:
                logger.debug(f"Error closing Redis connection: {e}")
            self._client = None
