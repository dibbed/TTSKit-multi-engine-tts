"""Tests for Cache Base Classes."""

import pytest

from ttskit.cache.base import BaseCache, CacheInterface


class TestCacheInterface:
    """Test cases for CacheInterface abstract class."""

    def test_cache_interface_is_abstract(self):
        """Test that CacheInterface cannot be instantiated directly."""
        with pytest.raises(TypeError):
            CacheInterface()

    def test_cache_interface_methods_are_abstract(self):
        """Test that CacheInterface methods raise NotImplementedError."""

        class ConcreteCache(CacheInterface):
            def get(self, key: str):
                return super().get(key)

            def set(self, key: str, value, ttl: int | None = None):
                return super().set(key, value, ttl)

            def delete(self, key: str):
                return super().delete(key)

            def clear(self):
                return super().clear()

            def exists(self, key: str):
                return super().exists(key)

            def get_stats(self):
                return super().get_stats()

        cache = ConcreteCache()

        with pytest.raises(NotImplementedError):
            cache.get("test")

        with pytest.raises(NotImplementedError):
            cache.set("test", "value")

        with pytest.raises(NotImplementedError):
            cache.delete("test")

        with pytest.raises(NotImplementedError):
            cache.clear()

        with pytest.raises(NotImplementedError):
            cache.exists("test")

        with pytest.raises(NotImplementedError):
            cache.get_stats()


class TestBaseCache:
    """Test cases for BaseCache class."""

    def _create_concrete_cache(self, default_ttl: int = 3600):
        """Create a concrete implementation of BaseCache for testing."""

        class ConcreteCache(BaseCache):
            def __init__(self, default_ttl: int = 3600):
                super().__init__(default_ttl)
                self._data = {}

            def get(self, key: str):
                return self._data.get(key)

            def set(self, key: str, value, ttl: int | None = None):
                self._data[key] = value

            def delete(self, key: str):
                if key in self._data:
                    del self._data[key]
                    return True
                return False

            def clear(self):
                self._data.clear()

            def exists(self, key: str):
                return key in self._data

        return ConcreteCache(default_ttl)

    def test_base_cache_initialization(self):
        """Test BaseCache initialization."""
        cache = self._create_concrete_cache()

        assert cache.default_ttl == 3600
        assert isinstance(cache._stats, dict)
        assert cache._stats["hits"] == 0
        assert cache._stats["misses"] == 0
        assert cache._stats["sets"] == 0
        assert cache._stats["deletes"] == 0
        assert cache._stats["errors"] == 0

    def test_base_cache_initialization_with_custom_ttl(self):
        """Test BaseCache initialization with custom TTL."""
        cache = self._create_concrete_cache(default_ttl=1800)

        assert cache.default_ttl == 1800

    def test_increment_stat(self):
        """Test _increment_stat method."""
        cache = self._create_concrete_cache()

        cache._increment_stat("hits")
        assert cache._stats["hits"] == 1

        cache._increment_stat("hits")
        assert cache._stats["hits"] == 2

        cache._increment_stat("nonexistent")

    def test_record_hit(self):
        """Test _record_hit method."""
        cache = self._create_concrete_cache()

        cache._record_hit()
        assert cache._stats["hits"] == 1

        cache._record_hit()
        assert cache._stats["hits"] == 2

    def test_record_miss(self):
        """Test _record_miss method."""
        cache = self._create_concrete_cache()

        cache._record_miss()
        assert cache._stats["misses"] == 1

        cache._record_miss()
        assert cache._stats["misses"] == 2

    def test_record_set(self):
        """Test _record_set method."""
        cache = self._create_concrete_cache()

        cache._record_set()
        assert cache._stats["sets"] == 1

        cache._record_set()
        assert cache._stats["sets"] == 2

    def test_record_delete(self):
        """Test _record_delete method."""
        cache = self._create_concrete_cache()

        cache._record_delete()
        assert cache._stats["deletes"] == 1

        cache._record_delete()
        assert cache._stats["deletes"] == 2

    def test_record_error(self):
        """Test _record_error method."""
        cache = self._create_concrete_cache()

        cache._record_error()
        assert cache._stats["errors"] == 1

        cache._record_error()
        assert cache._stats["errors"] == 2

    def test_get_stats_empty(self):
        """Test get_stats with no requests."""
        cache = self._create_concrete_cache()

        stats = cache.get_stats()

        assert isinstance(stats, dict)
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["sets"] == 0
        assert stats["deletes"] == 0
        assert stats["errors"] == 0
        assert stats["hit_rate"] == 0
        assert stats["total_requests"] == 0

    def test_get_stats_with_hits_and_misses(self):
        """Test get_stats with hits and misses."""
        cache = self._create_concrete_cache()

        cache._record_hit()
        cache._record_hit()
        cache._record_miss()

        stats = cache.get_stats()

        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["total_requests"] == 3
        assert stats["hit_rate"] == 66.67

    def test_get_stats_hit_rate_calculation(self):
        """Test hit rate calculation in get_stats."""
        cache = self._create_concrete_cache()

        cache._record_hit()
        cache._record_hit()
        cache._record_hit()
        cache._record_miss()

        stats = cache.get_stats()

        assert stats["hit_rate"] == 75.0

    def test_reset_stats(self):
        """Test reset_stats method."""
        cache = self._create_concrete_cache()

        cache._record_hit()
        cache._record_miss()
        cache._record_set()
        cache._record_delete()
        cache._record_error()

        cache.reset_stats()

        assert cache._stats["hits"] == 0
        assert cache._stats["misses"] == 0
        assert cache._stats["sets"] == 0
        assert cache._stats["deletes"] == 0
        assert cache._stats["errors"] == 0

    def test_get_stats_after_reset(self):
        """Test get_stats after reset."""
        cache = self._create_concrete_cache()

        cache._record_hit()
        cache._record_miss()

        cache.reset_stats()

        stats = cache.get_stats()

        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["total_requests"] == 0
        assert stats["hit_rate"] == 0

    def test_base_cache_inheritance(self):
        """Test that BaseCache properly inherits from CacheInterface."""
        assert issubclass(BaseCache, CacheInterface)

        cache = self._create_concrete_cache()
        assert isinstance(cache, CacheInterface)
        assert isinstance(cache, BaseCache)

    def test_base_cache_abstract_methods_still_raise_not_implemented(self):
        """Test that BaseCache still raises NotImplementedError for abstract methods."""
        with pytest.raises(TypeError):
            BaseCache()

    def test_stats_initialization_values(self):
        """Test that stats are initialized with correct values."""
        cache = self._create_concrete_cache()

        expected_stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0,
        }

        assert cache._stats == expected_stats

    def test_default_ttl_values(self):
        """Test different default TTL values."""
        cache1 = self._create_concrete_cache()
        assert cache1.default_ttl == 3600

        cache2 = self._create_concrete_cache(default_ttl=7200)
        assert cache2.default_ttl == 7200

        cache3 = self._create_concrete_cache(default_ttl=0)
        assert cache3.default_ttl == 0

        cache4 = self._create_concrete_cache(default_ttl=-1)
        assert cache4.default_ttl == -1
