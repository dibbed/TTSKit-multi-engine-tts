"""
Tests for ttskit.cache.__init__ module.

This module tests all functions and imports in the cache __init__.py file
to achieve 100% coverage.
"""

import json
from unittest.mock import MagicMock, patch

from ttskit.cache import (
    CacheInterface,
    MemoryCache,
    RedisCache,
    cache_key,
    clear_cache,
    get_cache,
    get_cache_config,
    get_cache_stats,
    is_cache_enabled,
    memory_cache,
    set_cache_config,
    set_cache_enabled,
)


class TestCacheInitImports:
    """Test that all imports work correctly."""

    def test_cache_interface_import(self):
        """Test CacheInterface import."""
        assert CacheInterface is not None
        assert hasattr(CacheInterface, "__init__")

    def test_memory_cache_import(self):
        """Test MemoryCache import."""
        assert MemoryCache is not None
        assert hasattr(MemoryCache, "__init__")

    def test_memory_cache_instance_import(self):
        """Test memory_cache instance import."""
        assert memory_cache is not None
        assert isinstance(memory_cache, MemoryCache)

    def test_redis_cache_import(self):
        """Test RedisCache import."""
        assert RedisCache is not None
        assert hasattr(RedisCache, "__init__")

    def test_cache_functions_import(self):
        """Test that all cache functions are importable."""
        assert cache_key is not None
        assert callable(cache_key)
        assert get_cache is not None
        assert callable(get_cache)
        assert clear_cache is not None
        assert callable(clear_cache)
        assert get_cache_stats is not None
        assert callable(get_cache_stats)
        assert is_cache_enabled is not None
        assert callable(is_cache_enabled)
        assert set_cache_enabled is not None
        assert callable(set_cache_enabled)
        assert get_cache_config is not None
        assert callable(get_cache_config)
        assert set_cache_config is not None
        assert callable(set_cache_config)


class TestCacheKey:
    """Test cache_key function."""

    def test_cache_key_basic(self):
        """Test basic cache key generation."""
        key = cache_key("hello", "en", "gtts")

        assert isinstance(key, str)
        assert len(key) == 64
        assert key.isalnum()

    def test_cache_key_deterministic(self):
        """Test that cache key is deterministic."""
        key1 = cache_key("hello", "en", "gtts")
        key2 = cache_key("hello", "en", "gtts")

        assert key1 == key2

    def test_cache_key_different_inputs(self):
        """Test that different inputs produce different keys."""
        key1 = cache_key("hello", "en", "gtts")
        key2 = cache_key("world", "en", "gtts")
        key3 = cache_key("hello", "fa", "gtts")
        key4 = cache_key("hello", "en", "edge")

        assert key1 != key2
        assert key1 != key3
        assert key1 != key4
        assert key2 != key3
        assert key2 != key4
        assert key3 != key4

    def test_cache_key_empty_strings(self):
        """Test cache key with empty strings."""
        key = cache_key("", "", "")

        assert isinstance(key, str)
        assert len(key) == 64

    def test_cache_key_unicode_text(self):
        """Test cache key with unicode text."""
        key1 = cache_key("سلام", "fa", "gtts")
        key2 = cache_key("hello", "en", "gtts")

        assert isinstance(key1, str)
        assert len(key1) == 64
        assert key1 != key2

    def test_cache_key_special_characters(self):
        """Test cache key with special characters."""
        key = cache_key("Hello, World! @#$%", "en", "gtts")

        assert isinstance(key, str)
        assert len(key) == 64

    def test_cache_key_json_structure(self):
        """Test that cache key uses proper JSON structure."""
        text = "test"
        lang = "en"
        engine = "gtts"

        key = cache_key(text, lang, engine)

        payload = json.dumps(
            {"t": text, "l": lang, "e": engine},
            ensure_ascii=False,
            separators=(",", ":"),
        )

        import hashlib

        expected_key = hashlib.sha256(payload.encode("utf-8")).hexdigest()

        assert key == expected_key


class TestGetCache:
    """Test get_cache function."""

    def test_get_cache_with_redis_available(self):
        """Test get_cache when Redis is available."""
        with (
            patch("ttskit.cache.REDIS_AVAILABLE", True),
            patch("ttskit.cache.settings") as mock_settings,
            patch("ttskit.cache.RedisCache") as mock_redis_cache,
        ):
            mock_settings.enable_caching = True
            mock_settings.redis_url = "redis://localhost:6379"
            mock_redis_instance = MagicMock()
            mock_redis_cache.return_value = mock_redis_instance

            cache = get_cache()

            assert cache == mock_redis_instance
            mock_redis_cache.assert_called_once_with("redis://localhost:6379")

    def test_get_cache_with_redis_unavailable(self):
        """Test get_cache when Redis is not available."""
        with (
            patch("ttskit.cache.REDIS_AVAILABLE", False),
            patch("ttskit.cache.settings") as mock_settings,
        ):
            mock_settings.enable_caching = True
            mock_settings.redis_url = "redis://localhost:6379"

            cache = get_cache()

            assert cache == memory_cache

    def test_get_cache_with_caching_disabled(self):
        """Test get_cache when caching is disabled."""
        with (
            patch("ttskit.cache.REDIS_AVAILABLE", True),
            patch("ttskit.cache.settings") as mock_settings,
        ):
            mock_settings.enable_caching = False
            mock_settings.redis_url = "redis://localhost:6379"

            cache = get_cache()

            assert cache == memory_cache

    def test_get_cache_with_no_redis_url(self):
        """Test get_cache when Redis URL is not set."""
        with (
            patch("ttskit.cache.REDIS_AVAILABLE", True),
            patch("ttskit.cache.settings") as mock_settings,
        ):
            mock_settings.enable_caching = True
            mock_settings.redis_url = None

            cache = get_cache()

            assert cache == memory_cache

    def test_get_cache_with_redis_exception(self):
        """Test get_cache when Redis connection fails."""
        with (
            patch("ttskit.cache.REDIS_AVAILABLE", True),
            patch("ttskit.cache.settings") as mock_settings,
            patch("ttskit.cache.RedisCache") as mock_redis_cache,
        ):
            mock_settings.enable_caching = True
            mock_settings.redis_url = "redis://localhost:6379"
            mock_redis_cache.side_effect = Exception("Connection failed")

            cache = get_cache()

            assert cache == memory_cache

    def test_get_cache_fallback_to_memory(self):
        """Test that get_cache falls back to memory cache in all error cases."""
        error_cases = [
            (True, True, "redis://localhost:6379", Exception("Redis error")),
            (True, False, "redis://localhost:6379", None),
            (True, True, None, None),
            (False, True, "redis://localhost:6379", None),
        ]

        for redis_available, caching_enabled, redis_url, redis_exception in error_cases:
            with (
                patch("ttskit.cache.REDIS_AVAILABLE", redis_available),
                patch("ttskit.cache.settings") as mock_settings,
                patch("ttskit.cache.RedisCache") as mock_redis_cache,
            ):
                mock_settings.enable_caching = caching_enabled
                mock_settings.redis_url = redis_url

                if redis_exception:
                    mock_redis_cache.side_effect = redis_exception

                cache = get_cache()
                assert cache == memory_cache


class TestClearCache:
    """Test clear_cache function."""

    def test_clear_cache(self):
        """Test clear_cache function."""
        with patch("ttskit.cache.get_cache") as mock_get_cache:
            mock_cache = MagicMock()
            mock_get_cache.return_value = mock_cache

            clear_cache()

            mock_get_cache.assert_called_once()
            mock_cache.clear.assert_called_once()


class TestGetCacheStats:
    """Test get_cache_stats function."""

    def test_get_cache_stats(self):
        """Test get_cache_stats function."""
        with patch("ttskit.cache.get_cache") as mock_get_cache:
            mock_cache = MagicMock()
            mock_stats = {"hits": 10, "misses": 5}
            mock_cache.get_stats.return_value = mock_stats
            mock_get_cache.return_value = mock_cache

            stats = get_cache_stats()

            assert stats == mock_stats
            mock_get_cache.assert_called_once()
            mock_cache.get_stats.assert_called_once()


class TestIsCacheEnabled:
    """Test is_cache_enabled function."""

    def test_is_cache_enabled_true(self):
        """Test is_cache_enabled when caching is enabled."""
        with patch("ttskit.cache.settings") as mock_settings:
            mock_settings.enable_caching = True

            result = is_cache_enabled()

            assert result is True

    def test_is_cache_enabled_false(self):
        """Test is_cache_enabled when caching is disabled."""
        with patch("ttskit.cache.settings") as mock_settings:
            mock_settings.enable_caching = False

            result = is_cache_enabled()

            assert result is False


class TestSetCacheEnabled:
    """Test set_cache_enabled function."""

    def test_set_cache_enabled_true(self):
        """Test set_cache_enabled with True."""
        with patch("ttskit.cache.settings") as mock_settings:
            set_cache_enabled(True)

            assert mock_settings.enable_caching is True

    def test_set_cache_enabled_false(self):
        """Test set_cache_enabled with False."""
        with patch("ttskit.cache.settings") as mock_settings:
            set_cache_enabled(False)

            assert mock_settings.enable_caching is False

    def test_set_cache_enabled_none(self):
        """Test set_cache_enabled with None."""
        with patch("ttskit.cache.settings") as mock_settings:
            set_cache_enabled(None)

            assert mock_settings.enable_caching is None


class TestGetCacheConfig:
    """Test get_cache_config function."""

    def test_get_cache_config(self):
        """Test get_cache_config function."""
        with patch("ttskit.cache.settings") as mock_settings:
            mock_settings.enable_caching = True
            mock_settings.cache_ttl = 3600
            mock_settings.redis_url = "redis://localhost:6379"

            config = get_cache_config()

            expected_config = {
                "enabled": True,
                "ttl": 3600,
                "redis_url": "redis://localhost:6379",
            }

            assert config == expected_config

    def test_get_cache_config_with_none_values(self):
        """Test get_cache_config with None values."""
        with patch("ttskit.cache.settings") as mock_settings:
            mock_settings.enable_caching = False
            mock_settings.cache_ttl = None
            mock_settings.redis_url = None

            config = get_cache_config()

            expected_config = {
                "enabled": False,
                "ttl": None,
                "redis_url": None,
            }

            assert config == expected_config


class TestSetCacheConfig:
    """Test set_cache_config function."""

    def test_set_cache_config_all_values(self):
        """Test set_cache_config with all values."""
        with patch("ttskit.cache.settings") as mock_settings:
            config = {
                "enabled": True,
                "ttl": 7200,
                "redis_url": "redis://localhost:6380",
            }

            set_cache_config(config)

            assert mock_settings.enable_caching is True
            assert mock_settings.cache_ttl == 7200
            assert mock_settings.redis_url == "redis://localhost:6380"

    def test_set_cache_config_partial_values(self):
        """Test set_cache_config with partial values."""
        with patch("ttskit.cache.settings") as mock_settings:
            mock_settings.enable_caching = True
            mock_settings.cache_ttl = 3600
            mock_settings.redis_url = "redis://localhost:6379"

            config = {
                "enabled": False,
            }

            set_cache_config(config)

            assert mock_settings.enable_caching is False
            assert mock_settings.cache_ttl == 3600
            assert (
                mock_settings.redis_url == "redis://localhost:6379"
            )

    def test_set_cache_config_empty_dict(self):
        """Test set_cache_config with empty dict."""
        with patch("ttskit.cache.settings") as mock_settings:
            mock_settings.enable_caching = True
            mock_settings.cache_ttl = 3600
            mock_settings.redis_url = "redis://localhost:6379"

            set_cache_config({})

            assert mock_settings.enable_caching is True
            assert mock_settings.cache_ttl == 3600
            assert mock_settings.redis_url == "redis://localhost:6379"

    def test_set_cache_config_individual_values(self):
        """Test set_cache_config with individual values."""
        with patch("ttskit.cache.settings") as mock_settings:
            set_cache_config({"enabled": False})
            assert mock_settings.enable_caching is False

            set_cache_config({"ttl": 1800})
            assert mock_settings.cache_ttl == 1800

            set_cache_config({"redis_url": "redis://new:6379"})
            assert mock_settings.redis_url == "redis://new:6379"

    def test_set_cache_config_none_values(self):
        """Test set_cache_config with None values."""
        with patch("ttskit.cache.settings") as mock_settings:
            config = {
                "enabled": None,
                "ttl": None,
                "redis_url": None,
            }

            set_cache_config(config)

            assert mock_settings.enable_caching is None
            assert mock_settings.cache_ttl is None
            assert mock_settings.redis_url is None


class TestCacheInitAll:
    """Test __all__ list in cache __init__.py."""

    def test_all_exports(self):
        """Test that __all__ contains all expected exports."""
        from ttskit.cache import __all__

        expected_exports = [
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

        assert len(__all__) == len(expected_exports)
        for export in expected_exports:
            assert export in __all__

    def test_all_exports_are_importable(self):
        """Test that all exports in __all__ are actually importable."""
        from ttskit.cache import __all__

        for export_name in __all__:
            exec(f"from ttskit.cache import {export_name}")


class TestCacheInitDocstring:
    """Test module docstring."""

    def test_module_has_docstring(self):
        """Test that the module has a proper docstring."""
        import ttskit.cache

        assert ttskit.cache.__doc__ is not None
        assert len(ttskit.cache.__doc__.strip()) > 0
        assert "Cache module for TTSKit" in ttskit.cache.__doc__


class TestCacheInitIntegration:
    """Test integration between different parts of cache __init__.py."""

    def test_cache_key_with_get_cache_integration(self):
        """Test integration between cache_key and get_cache."""
        key = cache_key("test text", "en", "gtts")

        cache = get_cache()

        assert isinstance(key, str)
        assert len(key) == 64
        assert cache is not None

    def test_cache_config_integration(self):
        """Test integration between config functions."""
        initial_config = get_cache_config()
        assert isinstance(initial_config, dict)

        new_config = {
            "enabled": not initial_config.get("enabled", True),
            "ttl": 1800,
            "redis_url": "redis://test:6379",
        }

        set_cache_config(new_config)

        updated_config = get_cache_config()
        assert updated_config["enabled"] == new_config["enabled"]
        assert updated_config["ttl"] == new_config["ttl"]
        assert updated_config["redis_url"] == new_config["redis_url"]

    def test_cache_stats_integration(self):
        """Test integration between cache stats and other functions."""
        clear_cache()

        stats = get_cache_stats()
        assert isinstance(stats, dict)

    def test_all_functions_work_together(self):
        """Test that all functions work together without conflicts."""
        key = cache_key("integration test", "en", "gtts")
        cache = get_cache()
        enabled = is_cache_enabled()
        config = get_cache_config()
        stats = get_cache_stats()

        assert isinstance(key, str)
        assert cache is not None
        assert isinstance(enabled, bool)
        assert isinstance(config, dict)
        assert isinstance(stats, dict)

        set_cache_config({"enabled": True})
        assert is_cache_enabled() is True

        clear_cache()

        stats_after_clear = get_cache_stats()
        assert isinstance(stats_after_clear, dict)


class TestCacheInitEdgeCases:
    """Test edge cases and error conditions."""

    def test_cache_key_with_very_long_text(self):
        """Test cache key with very long text."""
        long_text = "a" * 10000
        key = cache_key(long_text, "en", "gtts")

        assert isinstance(key, str)
        assert len(key) == 64

    def test_cache_key_with_unicode_edge_cases(self):
        """Test cache key with unicode edge cases."""
        unicode_texts = [
            "🚀🎉💯",
            "مرحبا بالعالم",
            "こんにちは世界",
            "Привет мир",
            "你好世界",
        ]

        for text in unicode_texts:
            key = cache_key(text, "en", "gtts")
            assert isinstance(key, str)
            assert len(key) == 64

    def test_get_cache_with_invalid_redis_url(self):
        """Test get_cache with invalid Redis URL."""
        with (
            patch("ttskit.cache.REDIS_AVAILABLE", True),
            patch("ttskit.cache.settings") as mock_settings,
            patch("ttskit.cache.RedisCache") as mock_redis_cache,
        ):
            mock_settings.enable_caching = True
            mock_settings.redis_url = "invalid://url"
            mock_redis_cache.side_effect = ValueError("Invalid URL")

            cache = get_cache()

            assert cache == memory_cache

    def test_set_cache_config_with_invalid_keys(self):
        """Test set_cache_config with invalid keys."""
        with patch("ttskit.cache.settings") as mock_settings:
            config = {
                "invalid_key": "value",
                "enabled": True,
                "another_invalid": 123,
            }

            set_cache_config(config)

            assert mock_settings.enable_caching is True

    def test_cache_key_with_none_values(self):
        """Test cache key with None values."""
        key = cache_key(None, None, None)
        assert isinstance(key, str)
        assert len(key) == 64
