"""Tests for Audio Manager."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from ttskit.utils.audio_manager import AudioManager, audio_manager


class TestAudioManager:
    """Test cases for AudioManager."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def audio_manager_instance(self, temp_dir):
        """Create AudioManager instance for testing."""
        return AudioManager(cache_dir=str(temp_dir))

    def test_initialization(self, temp_dir):
        """Test AudioManager initialization."""
        manager = AudioManager(cache_dir=str(temp_dir))

        assert manager.cache_dir == str(temp_dir)
        assert isinstance(manager.cache_stats, dict)
        assert "hits" in manager.cache_stats
        assert "misses" in manager.cache_stats
        assert "total_requests" in manager.cache_stats

    def test_get_cache_key(self, audio_manager_instance):
        """Test cache key generation."""
        key = audio_manager_instance._get_cache_key("Hello", "en", "gtts")

        assert isinstance(key, str)
        assert len(key) > 0

        key2 = audio_manager_instance._get_cache_key("Hello", "en", "gtts")
        assert key == key2

        key3 = audio_manager_instance._get_cache_key("World", "en", "gtts")
        assert key != key3

    def test_get_cache_path(self, audio_manager_instance):
        """Test cache path generation."""
        key = "test_key"
        path = audio_manager_instance._get_cache_path(key)

        assert isinstance(path, Path)
        assert path.name == f"{key}.ogg"

    def test_is_cached(self, audio_manager_instance, temp_dir):
        """Test cache existence check."""
        assert audio_manager_instance._is_cached("nonexistent_key") is False

        test_file = temp_dir / "test_key.ogg"
        test_file.write_bytes(b"test_data")

        assert audio_manager_instance._is_cached("test_key") is True

    def test_save_to_cache(self, audio_manager_instance, temp_dir):
        """Test saving to cache."""
        key = "test_save_key"
        audio_data = b"test_audio_data"

        audio_manager_instance._save_to_cache(key, audio_data)

        cache_file = temp_dir / f"{key}.ogg"
        assert cache_file.exists()
        assert cache_file.read_bytes() == audio_data

    def test_load_from_cache(self, audio_manager_instance, temp_dir):
        """Test loading from cache."""
        key = "test_load_key"
        audio_data = b"test_audio_data"

        cache_file = temp_dir / f"{key}.ogg"
        cache_file.write_bytes(audio_data)

        loaded_data = audio_manager_instance._load_from_cache(key)

        assert loaded_data == audio_data

    def test_load_from_cache_nonexistent(self, audio_manager_instance):
        """Test loading from cache when file doesn't exist."""
        loaded_data = audio_manager_instance._load_from_cache("nonexistent_key")

        assert loaded_data is None

    def test_get_cache_stats(self, audio_manager_instance):
        """Test getting cache statistics."""
        stats = audio_manager_instance.get_cache_stats()

        assert isinstance(stats, dict)
        assert "hits" in stats
        assert "misses" in stats
        assert "total_requests" in stats
        assert "hit_rate" in stats

    def test_clear_cache(self, audio_manager_instance, temp_dir):
        """Test clearing cache."""
        (temp_dir / "file1.ogg").write_bytes(b"data1")
        (temp_dir / "file2.ogg").write_bytes(b"data2")

        audio_manager_instance.clear_cache()

        assert not (temp_dir / "file1.ogg").exists()
        assert not (temp_dir / "file2.ogg").exists()

    def test_get_cache_size(self, audio_manager_instance, temp_dir):
        """Test getting cache size."""
        (temp_dir / "file1.ogg").write_bytes(b"data1")
        (temp_dir / "file2.ogg").write_bytes(b"data2")

        size = audio_manager_instance.get_cache_size()

        assert size > 0

    def test_get_cache_files(self, audio_manager_instance, temp_dir):
        """Test getting cache files."""
        (temp_dir / "file1.ogg").write_bytes(b"data1")
        (temp_dir / "file2.ogg").write_bytes(b"data2")
        (temp_dir / "not_ogg.txt").write_bytes(b"data3")

        files = audio_manager_instance.get_cache_files()

        assert len(files) == 2
        assert all(f.suffix == ".ogg" for f in files)

    @pytest.mark.asyncio
    async def test_get_audio_cached(self, audio_manager_instance, temp_dir):
        """Test getting cached audio."""
        key = "test_cached_key"
        audio_data = b"cached_audio_data"

        audio_manager_instance._save_to_cache(key, audio_data)

        with patch("ttskit.utils.audio_manager.global_cache_key", return_value=key):
            result = await audio_manager_instance.get_audio("Hello", "en", "gtts")

        assert result == audio_data

    @pytest.mark.asyncio
    async def test_get_audio_not_cached(self, audio_manager_instance):
        """Test getting audio when not cached."""
        with patch(
            "ttskit.utils.audio_manager.global_cache_key", return_value="test_key"
        ):
            with patch.object(
                audio_manager_instance, "_generate_audio"
            ) as mock_generate:
                mock_generate.return_value = b"generated_audio_data"

                result = await audio_manager_instance.get_audio("Hello", "en", "gtts")

                assert result == b"generated_audio_data"
                mock_generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_audio_with_save_to_cache(self, audio_manager_instance):
        """Test getting audio and saving to cache."""
        with patch(
            "ttskit.utils.audio_manager.global_cache_key", return_value="test_key"
        ):
            with patch.object(
                audio_manager_instance, "_generate_audio"
            ) as mock_generate:
                mock_generate.return_value = b"generated_audio_data"

                result = await audio_manager_instance.get_audio("Hello", "en", "gtts")

                assert result == b"generated_audio_data"

                cached_data = audio_manager_instance._load_from_cache("test_key")
                assert cached_data == b"generated_audio_data"

    @pytest.mark.asyncio
    async def test_generate_audio(self, audio_manager_instance):
        """Test audio generation."""
        mock_engine = Mock()
        mock_engine.synth_async.return_value = b"audio_data"

        with patch("ttskit.utils.audio_manager.engine_registry") as mock_registry:
            mock_registry.engines = {"gtts": mock_engine}

            result = await audio_manager_instance._generate_audio(
                "Hello", "en", "gtts", None, None, "ogg"
            )

            assert isinstance(result, bytes)
            assert len(result) > 0
            mock_engine.synth_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_audio_with_voice_and_rate(self, audio_manager_instance):
        """Test audio generation with voice and rate parameters."""
        mock_engine = Mock()
        mock_engine.synth_async.return_value = b"audio_data"

        with patch("ttskit.utils.audio_manager.engine_registry") as mock_registry:
            mock_registry.engines = {"gtts": mock_engine}

            result = await audio_manager_instance._generate_audio(
                "Hello", "en", "gtts", "voice1", 1.2, "ogg"
            )

            assert isinstance(result, bytes)
            assert len(result) > 0
            mock_engine.synth_async.assert_called_once()

    def test_cache_stats_update_on_hit(self, audio_manager_instance):
        """Test cache stats update on hit."""
        initial_hits = audio_manager_instance.cache_stats["hits"]
        initial_total = audio_manager_instance.cache_stats["total_requests"]

        audio_manager_instance._update_cache_stats(True)

        assert audio_manager_instance.cache_stats["hits"] == initial_hits + 1
        assert audio_manager_instance.cache_stats["total_requests"] == initial_total + 1

    def test_cache_stats_update_on_miss(self, audio_manager_instance):
        """Test cache stats update on miss."""
        initial_misses = audio_manager_instance.cache_stats["misses"]
        initial_total = audio_manager_instance.cache_stats["total_requests"]

        audio_manager_instance._update_cache_stats(False)

        assert audio_manager_instance.cache_stats["misses"] == initial_misses + 1
        assert audio_manager_instance.cache_stats["total_requests"] == initial_total + 1

    def test_hit_rate_calculation(self, audio_manager_instance):
        """Test hit rate calculation."""
        audio_manager_instance.cache_stats["hits"] = 8
        audio_manager_instance.cache_stats["total_requests"] = 10

        hit_rate = audio_manager_instance._calculate_hit_rate()

        assert hit_rate == 0.8

    def test_hit_rate_calculation_zero_requests(self, audio_manager_instance):
        """Test hit rate calculation with zero requests."""
        audio_manager_instance.cache_stats["hits"] = 0
        audio_manager_instance.cache_stats["total_requests"] = 0

        hit_rate = audio_manager_instance._calculate_hit_rate()

        assert hit_rate == 0.0

    def test_global_audio_manager_instance(self):
        """Test global audio_manager instance."""
        assert audio_manager is not None
        assert isinstance(audio_manager, AudioManager)

    def test_cache_directory_creation(self, temp_dir):
        """Test that cache directory is created if it doesn't exist."""
        new_cache_dir = temp_dir / "new_cache"

        manager = AudioManager(cache_dir=str(new_cache_dir))

        assert new_cache_dir.exists()
        assert manager.cache_dir == str(new_cache_dir)

    def test_cleanup_old_files(self, audio_manager_instance, temp_dir):
        """Test cleanup of old cache files."""
        audio_manager_instance.cleanup_old_files(max_age_days=1)

        assert True

    def test_format_cache_size(self, audio_manager_instance):
        """Test cache size formatting."""
        assert audio_manager_instance._format_cache_size(1024) == "1.0 KB"
        assert audio_manager_instance._format_cache_size(1048576) == "1.0 MB"
        assert audio_manager_instance._format_cache_size(1073741824) == "1.0 GB"
        assert audio_manager_instance._format_cache_size(512) == "512 B"
