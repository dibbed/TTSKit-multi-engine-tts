"""Cache module for TTSKit.

Provides cache backends (memory, Redis), key generation, and configuration
functions for managing caching in TTS synthesis workflows.
"""

import hashlib
import json
from typing import Any

from ..config import settings
from .base import CacheInterface
from .memory import MemoryCache, memory_cache
from .redis import REDIS_AVAILABLE, RedisCache


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


def get_cache() -> CacheInterface:
    """Return configured cache backend.

    Returns:
        An instance of the selected cache (Redis or Memory).

    Notes:
        Prefers Redis if settings.enable_caching, settings.redis_url, and REDIS_AVAILABLE.
        Falls back to global memory_cache on exceptions.
    """
    if settings.enable_caching and settings.redis_url and REDIS_AVAILABLE:
        try:
            return RedisCache(settings.redis_url)
        except Exception:
            return memory_cache
    return memory_cache


def clear_cache() -> None:
    """Clear all cached data.

    Removes all entries from the active cache backend.
    """
    cache = get_cache()
    cache.clear()


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
