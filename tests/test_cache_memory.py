"""Tests for Memory Cache."""

from ttskit.cache.memory import MemoryCache, memory_cache


class TestMemoryCache:
    """Test cases for MemoryCache."""

    def test_initialization(self):
        """Test MemoryCache initialization."""
        cache = MemoryCache()

        assert cache is not None
        assert isinstance(cache._cache, dict)
        assert cache.default_ttl == 3600

    def test_initialization_with_ttl(self):
        """Test MemoryCache initialization with custom TTL."""
        cache = MemoryCache(default_ttl=1800)

        assert cache.default_ttl == 1800

    def test_set_and_get(self):
        """Test setting and getting values."""
        cache = MemoryCache()

        cache.set("key1", "value1")

        value = cache.get("key1")

        assert value == "value1"

    def test_set_with_ttl(self):
        """Test setting value with custom TTL."""
        cache = MemoryCache()

        cache.set("key1", "value1", ttl=60)

        value = cache.get("key1")

        assert value == "value1"

    def test_get_nonexistent_key(self):
        """Test getting non-existent key."""
        cache = MemoryCache()

        value = cache.get("nonexistent")

        assert value is None

    def test_delete(self):
        """Test deleting a key."""
        cache = MemoryCache()

        cache.set("key1", "value1")

        cache.delete("key1")

        value = cache.get("key1")

        assert value is None

    def test_delete_nonexistent_key(self):
        """Test deleting non-existent key."""
        cache = MemoryCache()

        cache.delete("nonexistent")

    def test_clear(self):
        """Test clearing all cache."""
        cache = MemoryCache()

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_exists(self):
        """Test checking if key exists."""
        cache = MemoryCache()

        cache.set("key1", "value1")

        assert cache.exists("key1") is True
        assert cache.exists("nonexistent") is False

    def test_keys(self):
        """Test getting all keys."""
        cache = MemoryCache()

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        keys = cache.keys()

        assert "key1" in keys
        assert "key2" in keys
        assert len(keys) == 2

    def test_values(self):
        """Test getting all values."""
        cache = MemoryCache()

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        values = cache.values()

        assert "value1" in values
        assert "value2" in values
        assert len(values) == 2

    def test_items(self):
        """Test getting all items."""
        cache = MemoryCache()

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        items = cache.items()

        assert ("key1", "value1") in items
        assert ("key2", "value2") in items
        assert len(items) == 2

    def test_size(self):
        """Test getting cache size."""
        cache = MemoryCache()

        assert cache.size() == 0

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        assert cache.size() == 2

    def test_ttl_expiration(self):
        """Test TTL expiration."""
        cache = MemoryCache()

        cache.set("key1", "value1", ttl=0.001)

        import time

        time.sleep(0.05)

        value = cache.get("key1")
        assert value is None

    def test_ttl_not_expired(self):
        """Test TTL not expired."""
        cache = MemoryCache()

        cache.set("key1", "value1", ttl=3600)

        value = cache.get("key1")
        assert value == "value1"

    def test_update_existing_key(self):
        """Test updating existing key."""
        cache = MemoryCache()

        cache.set("key1", "value1")

        cache.set("key1", "value2")

        value = cache.get("key1")
        assert value == "value2"

    def test_get_with_default(self):
        """Test getting value with default."""
        cache = MemoryCache()

        value = cache.get("nonexistent", default="default_value")

        assert value == "default_value"

    def test_get_with_default_existing_key(self):
        """Test getting existing key with default."""
        cache = MemoryCache()

        cache.set("key1", "value1")

        value = cache.get("key1", default="default_value")

        assert value == "value1"

    def test_set_multiple_types(self):
        """Test setting different data types."""
        cache = MemoryCache()

        cache.set("string", "hello")
        cache.set("number", 42)
        cache.set("float", 3.14)
        cache.set("boolean", True)
        cache.set("list", [1, 2, 3])
        cache.set("dict", {"a": 1, "b": 2})

        assert cache.get("string") == "hello"
        assert cache.get("number") == 42
        assert cache.get("float") == 3.14
        assert cache.get("boolean") is True
        assert cache.get("list") == [1, 2, 3]
        assert cache.get("dict") == {"a": 1, "b": 2}

    def test_set_with_none_value(self):
        """Test setting None value."""
        cache = MemoryCache()

        cache.set("key1", None)

        value = cache.get("key1")

        assert value is None

    def test_set_with_empty_string(self):
        """Test setting empty string."""
        cache = MemoryCache()

        cache.set("key1", "")

        value = cache.get("key1")

        assert value == ""

    def test_set_with_zero(self):
        """Test setting zero value."""
        cache = MemoryCache()

        cache.set("key1", 0)

        value = cache.get("key1")

        assert value == 0

    def test_set_with_false(self):
        """Test setting False value."""
        cache = MemoryCache()

        cache.set("key1", False)

        value = cache.get("key1")

        assert value is False

    def test_global_memory_cache_instance(self):
        """Test global memory_cache instance."""
        assert memory_cache is not None
        assert isinstance(memory_cache, MemoryCache)

    def test_cache_isolation(self):
        """Test that different cache instances are isolated."""
        cache1 = MemoryCache()
        cache2 = MemoryCache()

        cache1.set("key1", "value1")

        assert cache2.get("key1") is None

        cache2.set("key1", "value2")

        assert cache1.get("key1") == "value1"
        assert cache2.get("key1") == "value2"

    def test_cache_with_large_data(self):
        """Test cache with large data."""
        cache = MemoryCache()

        large_data = "x" * 10000
        cache.set("large", large_data)

        value = cache.get("large")

        assert value == large_data

    def test_cache_with_many_keys(self):
        """Test cache with many keys."""
        cache = MemoryCache()

        for i in range(1000):
            cache.set(f"key{i}", f"value{i}")

        assert cache.size() == 1000

        assert cache.get("key0") == "value0"
        assert cache.get("key999") == "value999"

    def test_cache_with_special_characters_in_key(self):
        """Test cache with special characters in key."""
        cache = MemoryCache()

        special_key = "key:with:colons"
        cache.set(special_key, "value1")

        value = cache.get(special_key)

        assert value == "value1"

    def test_cache_with_unicode_key(self):
        """Test cache with unicode key."""
        cache = MemoryCache()

        unicode_key = "کلید"
        cache.set(unicode_key, "value1")

        value = cache.get(unicode_key)

        assert value == "value1"

    def test_cache_with_unicode_value(self):
        """Test cache with unicode value."""
        cache = MemoryCache()

        unicode_value = "مقدار"
        cache.set("key1", unicode_value)

        value = cache.get("key1")

        assert value == unicode_value
