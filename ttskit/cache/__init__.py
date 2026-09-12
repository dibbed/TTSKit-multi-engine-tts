"""Cache module for TTSKit.

Provides cache backends (memory, Redis), key generation, and configuration
functions for managing caching in TTS synthesis workflows.
"""

import hashlib
import json
from typing import Any

from ..config import settings
from ..utils.logging_config import get_logger
from .base import CacheInterface
from .memory import MemoryCache, memory_cache
from .redis import REDIS_AVAILABLE, RedisCache

logger = get_logger(__name__)


def cache_key(text: str, lang: str, engine: str) -> str:
    """Create deterministic cache key using SHA256.

    Args:
        text: Input text
        lang: Language code
        engine: Engine name

    Returns:
        Hex digest cache key (64 chars)

    Notes:
        Payload is JSON-serialized dict with keys 't', 'l', 'e' using compact separators.
    """
    payload = json.dumps(
        {"t": text, "l": lang, "e": engine}, ensure_ascii=False, separators=(",", ":")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


_redis_cache_instance: RedisCache | None = None


def get_cache(force_new: bool = False) -> CacheInterface:
    """Return configured cache backend.

    Returns:
        An instance of the selected cache (Redis or Memory).

    Notes:
        Prefers Redis if settings.enable_caching, settings.redis_url, and REDIS_AVAILABLE.
        Reuses RedisCache instance to avoid connection churn.
        Falls back to global memory_cache on exceptions.
    """
    global _redis_cache_instance
    if settings.enable_caching and settings.redis_url and REDIS_AVAILABLE:
        try:
            prefix = getattr(settings, "redis_key_prefix", None)
            dedicated = getattr(settings, "redis_dedicated_db", False)
            kwargs: dict[str, Any] = {}
            if prefix and isinstance(prefix, str):
                kwargs["key_prefix"] = prefix
            if isinstance(dedicated, bool):
                kwargs["dedicated_db"] = dedicated

            if (
                not force_new
                and _redis_cache_instance is not None
                and _redis_cache_instance.url == settings.redis_url
            ):
                return _redis_cache_instance

            if kwargs:
                _redis_cache_instance = RedisCache(settings.redis_url, **kwargs)
            else:
                _redis_cache_instance = RedisCache(settings.redis_url)
            return _redis_cache_instance
        except Exception:
            return memory_cache
    return memory_cache


def clear_cache() -> None:
    """Clear all cached data.

    Removes all entries from the active cache backend and audio manager disk cache.
    """
    cache = get_cache()
    cache.clear()
    try:
        from ..utils.audio_manager import audio_manager

        audio_manager.clear_cache()
    except Exception as e:
        logger.debug(f"Failed to clear audio manager cache: {e}")


def get_cache_stats() -> dict[str, Any]:
    """Get cache statistics.

    Returns:
        Dict of cache metrics from the active backend.
    """
    cache = get_cache()
    return cache.get_stats()


def is_cache_enabled() -> bool:
    """Check if caching is enabled.

    Returns:
        True if caching is active via settings.
    """
    return settings.enable_caching


def set_cache_enabled(enabled: bool) -> None:
    """Enable or disable caching.

    Args:
        enabled: Whether to enable caching.
    """
    settings.enable_caching = enabled


def get_cache_config() -> dict[str, Any]:
    """Get cache configuration.

    Returns:
        Dict with 'enabled', 'ttl', 'redis_url' from settings.
    """
    return {
        "enabled": settings.enable_caching,
        "ttl": settings.cache_ttl,
        "redis_url": settings.redis_url,
    }


def set_cache_config(config: dict[str, Any]) -> None:
    """Update the cache configuration from a dictionary.

    Args:
        config: Dictionary containing optional keys like 'enabled', 'ttl', or 'redis_url'.

    Notes:
        Only applies changes for the keys present in the config; any extra keys are ignored without error.
    """
    if "enabled" in config:
        settings.enable_caching = config["enabled"]
    if "ttl" in config:
        settings.cache_ttl = config["ttl"]
    if "redis_url" in config:
        settings.redis_url = config["redis_url"]


__all__ = [
    "CacheInterface",
    "MemoryCache",
    "memory_cache",
    "RedisCache",
    "cache_key",
    "get_cache",
    "clear_cache",
    "get_cache_stats",
    "is_cache_enabled",
    "set_cache_enabled",
    "get_cache_config",
    "set_cache_config",
]
