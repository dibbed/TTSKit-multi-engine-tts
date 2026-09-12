"""Tests for Redis cache key namespacing and directory boundary containment."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ttskit.cache.redis import RedisCache
from ttskit.utils.audio_manager import AudioManager


def test_redis_cache_namespacing():
    """Verify that key_prefix scopes keys and clear only deletes prefixed keys."""
    with patch("ttskit.cache.redis.redis.Redis") as mock_redis_class:
        client = MagicMock()
        client.ping.return_value = True
        mock_redis_class.from_url.return_value = client

        cache = RedisCache(key_prefix="tts:ns:")

        # set formats key
        cache.set("item1", "val1")
        client.set.assert_called_once_with("tts:ns:item1", "val1")

        # get formats key
        client.get.return_value = b'"val1"'
        val = cache.get("item1")
        assert val == "val1"
        client.get.assert_called_once_with("tts:ns:item1")

        # exists formats key
        client.exists.return_value = 1
        assert cache.exists("item1") is True
        client.exists.assert_called_once_with("tts:ns:item1")

        # ttl formats key
        client.ttl.return_value = 100
        assert cache.ttl("item1") == 100
        client.ttl.assert_called_once_with("tts:ns:item1")

        # delete formats key
        client.delete.return_value = 1
        assert cache.delete("item1") is True
        client.delete.assert_called_once_with("tts:ns:item1")

        # keys strips prefix
        client.scan_iter.return_value = [b"tts:ns:item1", b"tts:ns:item2"]
        keys = cache.keys()
        assert keys == ["item1", "item2"]

        # size returns count of prefixed keys
        client.scan_iter.return_value = [b"tts:ns:item1", b"tts:ns:item2"]
        assert cache.size() == 2

        # clear scans pattern and batch deletes without calling flushdb
        client.scan_iter.return_value = [b"tts:ns:item1", b"tts:ns:item2"]
        cache.clear()
        client.flushdb.assert_not_called()
        client.delete.assert_called_with(b"tts:ns:item1", b"tts:ns:item2")


def test_redis_cache_dedicated_db_calls_flushdb():
    """Verify that dedicated_db=True triggers flushdb even if key_prefix is set."""
    with patch("ttskit.cache.redis.redis.Redis") as mock_redis_class:
        client = MagicMock()
        client.ping.return_value = True
        mock_redis_class.from_url.return_value = client

        cache = RedisCache(key_prefix="tts:ns:", dedicated_db=True)
        cache.clear()
        client.flushdb.assert_called_once()


def test_audio_manager_path_traversal_sanitization(tmp_path: Path):
    """Verify AudioManager protects against directory traversal."""
    manager = AudioManager(cache_dir=str(tmp_path))
    safe_path = manager._get_cache_path("../../../etc/passwd", format="ogg")
    assert safe_path.name == "passwd.ogg"
    assert safe_path.resolve().is_relative_to(tmp_path.resolve())
