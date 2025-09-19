"""Comprehensive tests for Public API to achieve 100% coverage."""

import asyncio
import io
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from ttskit.exceptions import (
    AllEnginesFailedError,
    EngineNotAvailableError,
    TTSKitEngineError,
)
from ttskit.public import (
    TTS,
    AudioOut,
    SynthConfig,
    clear_cache,
    convert_audio_format,
    get_audio_info,
    get_cache_stats,
    get_config,
    get_documentation,
    get_engine_capabilities,
    get_engines,
    get_examples,
    get_health_status,
    get_rate_limit_info,
    get_stats,
    get_supported_formats,
    get_supported_languages,
    get_system_info,
    get_version_info,
    is_cache_enabled,
    list_voices,
    normalize_audio,
    reset_rate_limits,
    synth,
    synth_async,
)


class TestSynthConfigComprehensive:
    """Comprehensive tests for SynthConfig class."""

    def test_synth_config_post_init_valid(self):
        """Test SynthConfig.__post_init__ with valid values."""
        config = SynthConfig(
            text="Hello World", lang="en", rate=1.0, output_format="ogg"
        )
        assert config.text == "Hello World"
        assert config.lang == "en"
        assert config.rate == 1.0
        assert config.output_format == "ogg"

    def test_synth_config_post_init_invalid_rate(self):
        """Test SynthConfig.__post_init__ with invalid rate."""
        with pytest.raises(ValueError, match="Rate must be positive"):
            SynthConfig(text="Hello World", lang="en", rate=0.0, output_format="ogg")

    def test_synth_config_post_init_invalid_rate_negative(self):
        """Test SynthConfig.__post_init__ with negative rate."""
        with pytest.raises(ValueError, match="Rate must be positive"):
            SynthConfig(text="Hello World", lang="en", rate=-1.0, output_format="ogg")

    def test_synth_config_post_init_invalid_format(self):
        """Test SynthConfig.__post_init__ with invalid output format."""
        with pytest.raises(
            ValueError, match="Output format must be 'ogg', 'mp3', or 'wav'"
        ):
            SynthConfig(
                text="Hello World", lang="en", rate=1.0, output_format="invalid"
            )

    def test_synth_config_post_init_valid_formats(self):
        """Test SynthConfig.__post_init__ with all valid formats."""
        formats = ["ogg", "mp3", "wav"]
        for fmt in formats:
            config = SynthConfig(
                text="Hello World", lang="en", rate=1.0, output_format=fmt
            )
            assert config.output_format == fmt


class TestTTSComprehensive:
    """Comprehensive tests for TTS class."""

    def test_tts_setup_engines_success(self):
        """Test TTS._setup_engines with successful engine registration."""
        with patch("ttskit.public.engine_factory") as mock_factory:
            mock_factory.setup_registry.return_value = None

            tts = TTS(default_lang="en")

            mock_factory.setup_registry.assert_called_once()

    def test_tts_setup_engines_failure(self):
        """Test TTS._setup_engines with engine registration failure."""
        with patch("ttskit.public.engine_factory") as mock_factory:
            mock_factory.setup_registry.side_effect = Exception("Registration failed")

            tts = TTS(default_lang="en")

            mock_factory.setup_registry.assert_called_once()

    def test_tts_set_engine_preferences_valid(self):
        """Test TTS.set_engine_preferences with valid preferences."""
        tts = TTS(default_lang="en")

        preferences = {"en": ["gtts", "edge"], "fa": ["edge"]}
        tts.set_engine_preferences(preferences)

        assert tts._engine_preferences == preferences

    def test_tts_set_engine_preferences_invalid(self):
        """Test TTS.set_engine_preferences with invalid preferences."""
        tts = TTS(default_lang="en")

        with pytest.raises(ValueError, match="preferences must be a dict"):
            tts.set_engine_preferences("invalid")

    def test_tts_get_engines(self):
        """Test TTS.get_engines method."""
        with patch("ttskit.public.engine_factory") as mock_factory:
            mock_factory.get_all_engines_info.return_value = {
                "gtts": {"name": "Google TTS", "available": True},
                "edge": {"name": "Edge TTS", "available": True},
            }

            tts = TTS(default_lang="en")
            engines = tts.get_engines()

            assert isinstance(engines, list)
            assert len(engines) == 2
            assert engines[0]["name"] == "Google TTS"
            assert engines[1]["name"] == "Edge TTS"

    @pytest.mark.asyncio
    async def test_tts_synth_async_with_cache_hit(self):
        """Test TTS.synth_async with cache hit."""
        with patch("ttskit.public.audio_manager") as mock_manager:
            mock_manager.get_from_cache.return_value = b"cached_audio_data"

            tts = TTS(default_lang="en", cache_enabled=True)
            config = SynthConfig(text="Hello", cache=True)

            result = await tts.synth_async(config)

            assert isinstance(result, AudioOut)
            assert result.data == b"cached_audio_data"

    @pytest.mark.asyncio
    async def test_tts_synth_async_with_specific_engine(self):
        """Test TTS.synth_async with specific engine."""
        with (
            patch("ttskit.public.engine_factory") as mock_factory,
            patch("ttskit.public.audio_manager") as mock_manager,
        ):
            mock_engine = Mock()
            mock_engine.synth_async = AsyncMock(return_value=b"audio_data")
            mock_factory.get_engine.return_value = mock_engine
            mock_manager.get_from_cache.return_value = None
            mock_manager.process_audio = AsyncMock(return_value=b"processed_audio")
            mock_manager.get_audio_info.return_value = {
                "duration": 1.0,
                "sample_rate": 48000,
                "channels": 1,
                "bitrate": 128,
            }

            tts = TTS(default_lang="en")
            config = SynthConfig(text="Hello", engine="gtts")

            result = await tts.synth_async(config)

            assert isinstance(result, AudioOut)
            assert result.data == b"processed_audio"

    @pytest.mark.asyncio
    async def test_tts_synth_async_engine_not_available(self):
        """Test TTS.synth_async with unavailable engine."""
        with (
            patch("ttskit.public.engine_factory") as mock_factory,
            patch("ttskit.public.audio_manager") as mock_manager,
        ):
            mock_factory.get_engine.return_value = None
            mock_manager.get_from_cache.return_value = None

            tts = TTS(default_lang="en")
            config = SynthConfig(text="Hello", engine="nonexistent")

            with pytest.raises(EngineNotAvailableError):
                await tts.synth_async(config)

    @pytest.mark.asyncio
    async def test_tts_synth_async_auto_engine_selection(self):
        """Test TTS.synth_async with automatic engine selection."""
        with (
            patch("ttskit.public.engine_factory") as mock_factory,
            patch("ttskit.public.audio_manager") as mock_manager,
        ):
            mock_engine = Mock()
            mock_engine.synth_async = AsyncMock(return_value=b"audio_data")
            mock_factory.get_engine.return_value = mock_engine
            mock_factory.get_available_engines.return_value = ["gtts"]
            mock_manager.get_from_cache.return_value = None
            mock_manager.process_audio = AsyncMock(return_value=b"processed_audio")
            mock_manager.get_audio_info.return_value = {
                "duration": 1.0,
                "sample_rate": 48000,
                "channels": 1,
                "bitrate": 128,
            }

            tts = TTS(default_lang="en")
            config = SynthConfig(text="Hello")

            result = await tts.synth_async(config)

            assert isinstance(result, AudioOut)
            assert result.data == b"processed_audio"

    @pytest.mark.asyncio
    async def test_tts_synth_async_engine_with_output_format_param(self):
        """Test TTS.synth_async with engine supporting output_format parameter."""
        with (
            patch("ttskit.public.engine_factory") as mock_factory,
            patch("ttskit.public.audio_manager") as mock_manager,
            patch("inspect.signature") as mock_signature,
        ):
            mock_engine = Mock()
            mock_engine.synth_async = AsyncMock(return_value=b"audio_data")
            mock_engine.__class__.__name__ = "TestEngine"
            mock_factory.get_engine.return_value = mock_engine

            mock_sig = Mock()
            mock_sig.parameters = {"output_format": Mock()}
            mock_signature.return_value = mock_sig

            mock_manager.get_from_cache.return_value = None
            mock_manager.process_audio = AsyncMock(return_value=b"processed_audio")
            mock_manager.get_audio_info.return_value = {
                "duration": 1.0,
                "sample_rate": 48000,
                "channels": 1,
                "bitrate": 128,
            }

            tts = TTS(default_lang="en")
            config = SynthConfig(text="Hello", engine="gtts", output_format="mp3")

            result = await tts.synth_async(config)

            mock_engine.synth_async.assert_called_once_with(
                text="Hello",
                lang="en",
                voice=None,
                rate=1.0,
                pitch=0.0,
                output_format="mp3",
            )

    @pytest.mark.asyncio
    async def test_tts_synth_async_piper_engine(self):
        """Test TTS.synth_async with Piper engine (WAV format)."""
        with (
            patch("ttskit.public.engine_factory") as mock_factory,
            patch("ttskit.public.audio_manager") as mock_manager,
        ):
            mock_engine = Mock()
            mock_engine.synth_async = AsyncMock(return_value=b"audio_data")
            mock_engine.__class__.__name__ = "PiperEngine"
            mock_factory.get_engine.return_value = mock_engine

            mock_manager.get_from_cache.return_value = None
            mock_manager.process_audio = AsyncMock(return_value=b"processed_audio")
            mock_manager.get_audio_info.return_value = {
                "duration": 1.0,
                "sample_rate": 48000,
                "channels": 1,
                "bitrate": 128,
            }

            tts = TTS(default_lang="en")
            config = SynthConfig(text="Hello", engine="piper")

            result = await tts.synth_async(config)

            mock_manager.process_audio.assert_called_once_with(
                b"audio_data",
                input_format="wav",
                output_format="ogg",
                sample_rate=48000,
                channels=1,
            )

    @pytest.mark.asyncio
    async def test_tts_synth_async_engine_failure_with_fallback(self):
        """Test TTS.synth_async with engine failure and successful fallback."""
        with (
            patch("ttskit.public.engine_factory") as mock_factory,
            patch("ttskit.public.audio_manager") as mock_manager,
            patch.object(TTS, "_try_fallback_engines") as mock_fallback,
        ):
            mock_engine = Mock()
            mock_engine.synth_async = AsyncMock(side_effect=Exception("Engine failed"))
            mock_factory.get_engine.return_value = mock_engine

            mock_manager.get_from_cache.return_value = None
            mock_fallback.return_value = AudioOut(
                data=b"fallback_audio", format="ogg", duration=1.0, size=10
            )

            tts = TTS(default_lang="en")
            config = SynthConfig(text="Hello", engine="gtts")

            result = await tts.synth_async(config)

            assert isinstance(result, AudioOut)
            assert result.data == b"fallback_audio"

    @pytest.mark.asyncio
    async def test_tts_synth_async_all_engines_failed(self):
        """Test TTS.synth_async when all engines fail."""
        with (
            patch("ttskit.public.engine_factory") as mock_factory,
            patch("ttskit.public.audio_manager") as mock_manager,
            patch.object(TTS, "_try_fallback_engines") as mock_fallback,
        ):
            mock_engine = Mock()
            mock_engine.synth_async = AsyncMock(side_effect=Exception("Engine failed"))
            mock_factory.get_engine.return_value = mock_engine

            mock_manager.get_from_cache.return_value = None
            mock_fallback.side_effect = AllEnginesFailedError("All engines failed")

            tts = TTS(default_lang="en")
            config = SynthConfig(text="Hello", engine="gtts")

            with pytest.raises(AllEnginesFailedError):
                await tts.synth_async(config)

    @pytest.mark.asyncio
    async def test_tts_synth_async_fallback_with_other_error(self):
        """Test TTS.synth_async with fallback raising non-AllEnginesFailedError."""
        with (
            patch("ttskit.public.engine_factory") as mock_factory,
            patch("ttskit.public.audio_manager") as mock_manager,
            patch.object(TTS, "_try_fallback_engines") as mock_fallback,
        ):
            mock_engine = Mock()
            mock_engine.synth_async = AsyncMock(side_effect=Exception("Engine failed"))
            mock_factory.get_engine.return_value = mock_engine

            mock_manager.get_from_cache.return_value = None
            mock_fallback.side_effect = Exception("Fallback error")

            tts = TTS(default_lang="en")
            config = SynthConfig(text="Hello", engine="gtts")

            with pytest.raises(TTSKitEngineError):
                await tts.synth_async(config)

    @pytest.mark.asyncio
    async def test_tts_try_fallback_engines_success(self):
        """Test TTS._try_fallback_engines with successful fallback."""
        with (
            patch("ttskit.public.engine_factory") as mock_factory,
            patch("ttskit.public.audio_manager") as mock_manager,
        ):
            mock_engine = Mock()
            mock_engine.synth_async = AsyncMock(return_value=b"audio_data")
            mock_factory.get_available_engines.return_value = ["edge", "gtts"]
            mock_factory.get_engine.return_value = mock_engine

            mock_manager.process_audio = AsyncMock(return_value=b"processed_audio")
            mock_manager.get_audio_info.return_value = {
                "duration": 1.0,
                "sample_rate": 48000,
                "channels": 1,
                "bitrate": 128,
            }

            tts = TTS(default_lang="en")
            config = SynthConfig(text="Hello", engine="gtts")

            result = await tts._try_fallback_engines(config)

            assert isinstance(result, AudioOut)
            assert result.data == b"processed_audio"

    @pytest.mark.asyncio
    async def test_tts_try_fallback_engines_all_failed(self):
        """Test TTS._try_fallback_engines when all engines fail."""
        with (
            patch("ttskit.public.engine_factory") as mock_factory,
            patch("ttskit.public.audio_manager") as mock_manager,
        ):
            mock_engine = Mock()
            mock_engine.synth_async = AsyncMock(side_effect=Exception("Engine failed"))
            mock_factory.get_available_engines.return_value = ["edge", "gtts"]
            mock_factory.get_engine.return_value = mock_engine

            tts = TTS(default_lang="en")
            config = SynthConfig(text="Hello", engine="gtts")

            with pytest.raises(AllEnginesFailedError):
                await tts._try_fallback_engines(config)

    @pytest.mark.asyncio
    async def test_tts_try_fallback_engines_skip_failed_engine(self):
        """Test TTS._try_fallback_engines skips the already failed engine."""
        with (
            patch("ttskit.public.engine_factory") as mock_factory,
            patch("ttskit.public.audio_manager") as mock_manager,
        ):
            mock_engine = Mock()
            mock_engine.synth_async = AsyncMock(return_value=b"audio_data")
            mock_factory.get_available_engines.return_value = ["gtts", "edge"]
            mock_factory.get_engine.return_value = mock_engine

            mock_manager.process_audio = AsyncMock(return_value=b"processed_audio")
            mock_manager.get_audio_info.return_value = {
                "duration": 1.0,
                "sample_rate": 48000,
                "channels": 1,
                "bitrate": 128,
            }

            tts = TTS(default_lang="en")
            config = SynthConfig(text="Hello", engine="gtts")

            result = await tts._try_fallback_engines(config)

            assert mock_factory.get_engine.call_count == 1
            mock_factory.get_engine.assert_called_with("edge")

    @pytest.mark.asyncio
    async def test_tts_try_fallback_engines_engine_none(self):
        """Test TTS._try_fallback_engines when engine factory returns None."""
        with (
            patch("ttskit.public.engine_factory") as mock_factory,
            patch("ttskit.public.audio_manager") as mock_manager,
        ):
            mock_factory.get_available_engines.return_value = ["edge"]
            mock_factory.get_engine.return_value = None

            tts = TTS(default_lang="en")
            config = SynthConfig(text="Hello", engine="gtts")

            with pytest.raises(AllEnginesFailedError):
                await tts._try_fallback_engines(config)

    def test_tts_list_voices_with_engine(self):
        """Test TTS.list_voices with specific engine."""
        with patch("ttskit.public.engine_factory") as mock_factory:
            mock_engine = Mock()
            mock_engine.list_voices.return_value = ["voice1", "voice2"]
            mock_factory.create_engine.return_value = mock_engine

            tts = TTS(default_lang="en")
            voices = tts.list_voices(lang="en", engine="gtts")

            assert set(voices) == {"voice1", "voice2"}
            mock_factory.create_engine.assert_called_once_with("gtts")
            mock_engine.list_voices.assert_called_once_with("en")

    def test_tts_list_voices_without_engine(self):
        """Test TTS.list_voices without specific engine."""
        with patch("ttskit.public.engine_factory") as mock_factory:
            mock_engine1 = Mock()
            mock_engine1.list_voices.return_value = ["voice1", "voice2"]
            mock_engine2 = Mock()
            mock_engine2.list_voices.return_value = ["voice3", "voice4"]

            mock_factory.get_available_engines.return_value = ["gtts", "edge"]
            mock_factory.create_engine.side_effect = [mock_engine1, mock_engine2]

            tts = TTS(default_lang="en")
            voices = tts.list_voices(lang="en")

            assert set(voices) == {"voice1", "voice2", "voice3", "voice4"}

    def test_tts_list_voices_engine_none(self):
        """Test TTS.list_voices when engine factory returns None."""
        with patch("ttskit.public.engine_factory") as mock_factory:
            mock_factory.create_engine.return_value = None

            tts = TTS(default_lang="en")
            voices = tts.list_voices(lang="en", engine="nonexistent")

            assert voices == []

    def test_tts_generate_cache_key(self):
        """Test TTS._generate_cache_key method."""
        tts = TTS(default_lang="en")
        config = SynthConfig(
            text="Hello World",
            lang="en",
            voice="default",
            engine="gtts",
            rate=1.0,
            pitch=0.0,
            output_format="ogg",
        )

        key = tts._generate_cache_key(config)

        assert isinstance(key, str)
        assert len(key) == 64

    def test_tts_bytes_to_audio_out(self):
        """Test TTS._bytes_to_audio_out method."""
        with patch("ttskit.public.audio_manager") as mock_manager:
            mock_manager.get_audio_info.return_value = {
                "duration": 2.5,
                "sample_rate": 44100,
                "channels": 2,
                "bitrate": 192,
            }

            tts = TTS(default_lang="en")
            audio_data = b"test_audio_data"

            result = tts._bytes_to_audio_out(audio_data, "mp3")

            assert isinstance(result, AudioOut)
            assert result.data == audio_data
            assert result.format == "mp3"
            assert result.duration == 2.5
            assert result.sample_rate == 44100
            assert result.channels == 2
            assert result.bitrate == 192
            assert result.size == len(audio_data)


class TestConvenienceFunctionsComprehensive:
    """Comprehensive tests for convenience functions."""

    @pytest.mark.asyncio
    async def test_synth_async_function(self):
        """Test synth_async convenience function."""
        with patch("ttskit.public.TTS") as mock_tts_class:
            mock_tts = Mock()
            mock_audio_out = AudioOut(
                data=b"audio_data", format="ogg", duration=1.0, size=10
            )
            mock_tts.synth_async.return_value = mock_audio_out
            mock_tts_class.return_value = mock_tts

            result = await synth_async("Hello World", "en")

            assert isinstance(result, AudioOut)
            assert result.data == b"audio_data"

    @pytest.mark.asyncio
    async def test_synth_async_function_with_await(self):
        """Test synth_async convenience function with awaitable result."""
        with patch("ttskit.public.TTS") as mock_tts_class:
            mock_tts = Mock()
            mock_audio_out = AudioOut(
                data=b"audio_data", format="ogg", duration=1.0, size=10
            )

            async def async_synth():
                return mock_audio_out

            mock_tts.synth_async.return_value = async_synth()
            mock_tts_class.return_value = mock_tts

            result = await synth_async("Hello World", "en")

            assert isinstance(result, AudioOut)
            assert result.data == b"audio_data"

    def test_synth_function(self):
        """Test synth convenience function."""
        with patch("ttskit.public.TTS") as mock_tts_class:
            mock_tts = Mock()
            mock_audio_out = AudioOut(
                data=b"audio_data", format="ogg", duration=1.0, size=10
            )
            mock_tts.synth.return_value = mock_audio_out
            mock_tts_class.return_value = mock_tts

            result = synth("Hello World", "en")

            assert isinstance(result, AudioOut)
            assert result.data == b"audio_data"

    def test_synth_function_with_format_alias(self):
        """Test synth convenience function with format alias."""
        with patch("ttskit.public.TTS") as mock_tts_class:
            mock_tts = Mock()
            mock_audio_out = AudioOut(
                data=b"audio_data", format="mp3", duration=1.0, size=10
            )
            mock_tts.synth.return_value = mock_audio_out
            mock_tts_class.return_value = mock_tts

            result = synth("Hello World", "en", format="mp3")

            assert isinstance(result, AudioOut)
            assert result.data == b"audio_data"

    def test_list_voices_function(self):
        """Test list_voices convenience function."""
        with patch("ttskit.public.TTS") as mock_tts_class:
            mock_tts = Mock()
            mock_tts.list_voices.return_value = ["voice1", "voice2"]
            mock_tts_class.return_value = mock_tts

            voices = list_voices("en", "gtts")

            assert voices == ["voice1", "voice2"]
            mock_tts.list_voices.assert_called_once_with("en", "gtts")

    def test_get_engines_function(self):
        """Test get_engines convenience function."""
        with patch("ttskit.public.engine_factory") as mock_factory:
            mock_factory.get_all_engines_info.return_value = {
                "gtts": {
                    "name": "Google TTS",
                    "capabilities": {
                        "offline": False,
                        "languages": ["en", "es"],
                        "voices": ["default"],
                    },
                },
                "edge": {
                    "name": "Edge TTS",
                    "capabilities": {
                        "offline": False,
                        "languages": ["en", "fa"],
                        "voices": ["multiple"],
                    },
                },
            }

            engines = get_engines()

            assert isinstance(engines, list)
            assert len(engines) == 2

            gtts_engine = next(e for e in engines if e["name"] == "Google TTS")
            assert gtts_engine["offline"] is False
            assert gtts_engine["languages"] == ["en", "es"]
            assert gtts_engine["voices"] == ["default"]

    def test_get_engines_function_with_none_info(self):
        """Test get_engines convenience function with None info."""
        with patch("ttskit.public.engine_factory") as mock_factory:
            mock_factory.get_all_engines_info.return_value = {
                "gtts": {"name": "Google TTS"},
                "edge": None,
            }

            engines = get_engines()

            assert isinstance(engines, list)
            assert len(engines) == 1
            assert engines[0]["name"] == "Google TTS"

    def test_get_engines_function_missing_name(self):
        """Test get_engines convenience function with missing name."""
        with patch("ttskit.public.engine_factory") as mock_factory:
            mock_factory.get_all_engines_info.return_value = {
                "gtts": {
                    "capabilities": {
                        "offline": False,
                        "languages": ["en"],
                        "voices": ["default"],
                    }
                }
            }

            engines = get_engines()

            assert isinstance(engines, list)
            assert len(engines) == 1
            assert engines[0]["name"] == "gtts"


class TestUtilityFunctionsComprehensive:
    """Comprehensive tests for utility functions."""

    def test_clear_cache(self):
        """Test clear_cache function."""
        with patch("ttskit.cache.clear_cache") as mock_clear:
            clear_cache()
            mock_clear.assert_called_once()

    def test_get_cache_stats(self):
        """Test get_cache_stats function."""
        with patch("ttskit.cache.get_cache_stats") as mock_stats:
            mock_stats.return_value = {"hits": 10, "misses": 5}

            stats = get_cache_stats()

            assert stats == {"hits": 10, "misses": 5}
            mock_stats.assert_called_once()

    def test_is_cache_enabled(self):
        """Test is_cache_enabled function."""
        with patch("ttskit.cache.is_cache_enabled") as mock_enabled:
            mock_enabled.return_value = True

            enabled = is_cache_enabled()

            assert enabled is True
            mock_enabled.assert_called_once()

    def test_convert_audio_format_ogg(self):
        """Test convert_audio_format function with OGG format."""
        with patch("ttskit.utils.audio.to_opus_ogg") as mock_convert:
            convert_audio_format("input.wav", "output.ogg", "ogg")
            mock_convert.assert_called_once_with("input.wav", "output.ogg")

    def test_convert_audio_format_unsupported(self):
        """Test convert_audio_format function with unsupported format."""
        with pytest.raises(ValueError, match="Unsupported target format: mp3"):
            convert_audio_format("input.wav", "output.mp3", "mp3")

    def test_get_audio_info(self):
        """Test get_audio_info function."""
        with patch("ttskit.utils.audio.get_audio_info") as mock_info:
            mock_info.return_value = {
                "duration": 1.5,
                "sample_rate": 44100,
                "channels": 2,
            }

            info = get_audio_info("test.wav")

            assert info["duration"] == 1.5
            assert info["sample_rate"] == 44100
            assert info["channels"] == 2
            mock_info.assert_called_once_with("test.wav")

    def test_get_config(self):
        """Test get_config function."""
        with patch("ttskit.config.get_settings") as mock_settings:
            mock_settings_obj = Mock()
            mock_settings_obj.model_dump.return_value = {"setting1": "value1"}
            mock_settings.return_value = mock_settings_obj

            config = get_config()

            assert config == {"setting1": "value1"}
            mock_settings.assert_called_once()

    def test_get_documentation(self):
        """Test get_documentation function."""
        doc = get_documentation()

        assert isinstance(doc, dict)
        assert doc["name"] == "TTSKit"
        assert doc["version"] == "1.0.0"
        assert "features" in doc
        assert "engines" in doc
        assert "telegram_adapters" in doc
        assert "supported_languages" in doc

    def test_get_engine_capabilities(self):
        """Test get_engine_capabilities function."""
        capabilities = get_engine_capabilities()

        assert isinstance(capabilities, dict)
        assert "gtts" in capabilities
        assert "edge" in capabilities
        assert "piper" in capabilities

        gtts_caps = capabilities["gtts"]
        assert gtts_caps["name"] == "Google Text-to-Speech"
        assert "en" in gtts_caps["languages"]
        assert "online" in gtts_caps["features"]

    def test_get_examples(self):
        """Test get_examples function."""
        examples = get_examples()

        assert isinstance(examples, dict)
        assert "basic_usage" in examples
        assert "engine_selection" in examples
        assert "telegram_bot" in examples
        assert "audio_processing" in examples
        assert "caching" in examples
        assert "rate_limiting" in examples

        for category, example_list in examples.items():
            assert isinstance(example_list, list)
            for example in example_list:
                assert isinstance(example, str)

    def test_get_health_status(self):
        """Test get_health_status function."""
        with patch("ttskit.health.check_system_health") as mock_health:
            mock_health.return_value = {
                "overall": True,
                "checks": {"database": True, "redis": True},
                "details": {"database": "OK", "redis": "OK"},
            }

            result = get_health_status()
            health = asyncio.run(result) if hasattr(result, "__await__") else result

            assert isinstance(health, dict)
            assert health["overall_status"] == "healthy"
            assert "components" in health
            assert "details" in health
            assert health["version"] == "1.0.0"

    def test_get_rate_limit_info_success(self):
        """Test get_rate_limit_info function with success."""
        with patch("ttskit.utils.rate_limiter.get_rate_limiter") as mock_get_limiter:
            mock_limiter = Mock()
            mock_limiter.get_user_info.return_value = {
                "user_id": "test_user",
                "rate_limited": False,
                "remaining_requests": 100,
                "reset_time": 1234567890,
            }
            mock_get_limiter.return_value = mock_limiter

            result = get_rate_limit_info("test_user")
            info = asyncio.run(result) if hasattr(result, "__await__") else result

            assert info["user_id"] == "test_user"
            assert info["rate_limited"] is False
            assert info["remaining_requests"] == 100

    def test_get_rate_limit_info_error(self):
        """Test get_rate_limit_info function with error."""
        with patch("ttskit.utils.rate_limiter.get_rate_limiter") as mock_get_limiter:
            mock_get_limiter.side_effect = Exception("Rate limiter error")

            result = get_rate_limit_info("test_user")
            info = asyncio.run(result) if hasattr(result, "__await__") else result

            assert info["user_id"] == "test_user"
            assert info["error"] == "Rate limiter error"
            assert info["rate_limited"] is False
            assert info["remaining_requests"] == 0
            assert info["reset_time"] is None

    def test_get_stats(self):
        """Test get_stats function."""
        with patch("ttskit.metrics.get_metrics_summary") as mock_metrics:
            mock_metrics.return_value = {
                "total_requests": 100,
                "successful_requests": 95,
                "failed_requests": 5,
            }

            stats = get_stats()

            assert stats["total_requests"] == 100
            assert stats["successful_requests"] == 95
            assert stats["failed_requests"] == 5
            mock_metrics.assert_called_once()

    def test_get_supported_formats(self):
        """Test get_supported_formats function."""
        formats = get_supported_formats()

        assert isinstance(formats, list)
        assert "ogg" in formats
        assert "mp3" in formats
        assert "wav" in formats
        assert "flac" in formats
        assert "aac" in formats
        assert "m4a" in formats

    def test_get_supported_languages(self):
        """Test get_supported_languages function."""
        languages = get_supported_languages()

        assert isinstance(languages, list)
        assert "en" in languages
        assert "fa" in languages
        assert "ar" in languages
        assert "es" in languages
        assert "fr" in languages
        assert "de" in languages

    def test_get_system_info(self):
        """Test get_system_info function."""
        with (
            patch("platform.platform") as mock_platform,
            patch("platform.architecture") as mock_arch,
            patch("platform.processor") as mock_processor,
            patch("platform.machine") as mock_machine,
            patch("platform.system") as mock_system,
            patch("platform.release") as mock_release,
            patch("platform.version") as mock_version,
        ):
            mock_platform.return_value = "Windows-10-10.0.19045"
            mock_arch.return_value = ("64bit", "WindowsPE")
            mock_processor.return_value = (
                "Intel64 Family 6 Model 142 Stepping 10, GenuineIntel"
            )
            mock_machine.return_value = "AMD64"
            mock_system.return_value = "Windows"
            mock_release.return_value = "10"
            mock_version.return_value = "10.0.19045"

            info = get_system_info()

            assert isinstance(info, dict)
            assert "python_version" in info
            assert "platform" in info
            assert "architecture" in info
            assert "processor" in info
            assert "machine" in info
            assert "system" in info
            assert "release" in info
            assert "version" in info

    def test_get_version_info(self):
        """Test get_version_info function."""
        with patch("ttskit.version.__version__", "1.0.0"):
            version_info = get_version_info()

            assert isinstance(version_info, dict)
            assert version_info["version"] == "1.0.0"
            assert version_info["package"] == "ttskit"
            assert (
                version_info["description"]
                == "Professional Telegram TTS library and bot"
            )
            assert version_info["author"] == "TTSKit Team"
            assert version_info["license"] == "MIT"

    def test_normalize_audio_success(self):
        """Test normalize_audio function with success."""
        with patch("pydub.AudioSegment") as mock_audio_segment:
            mock_audio = Mock()
            mock_normalized = Mock()
            mock_output = io.BytesIO()
            mock_output.write(b"normalized_audio")
            mock_output.seek(0)

            mock_audio_segment.from_file.return_value = mock_audio
            mock_audio.normalize.return_value = mock_normalized
            mock_normalized.export.return_value = None

            with patch("io.BytesIO") as mock_bytesio:
                mock_bytesio.return_value = mock_output

                result = normalize_audio(b"test_audio_data")

                assert isinstance(result, bytes)
                mock_audio_segment.from_file.assert_called_once()
                mock_audio.normalize.assert_called_once()
                mock_normalized.export.assert_called_once()

    def test_normalize_audio_error(self):
        """Test normalize_audio function with error."""
        with patch("pydub.AudioSegment") as mock_audio_segment:
            mock_audio_segment.from_file.side_effect = Exception(
                "Audio processing error"
            )

            result = normalize_audio(b"test_audio_data")

            assert result == b"test_audio_data"

    def test_reset_rate_limits_success(self):
        """Test reset_rate_limits function with success."""
        with patch("ttskit.utils.rate_limiter.get_rate_limiter") as mock_get_limiter:
            mock_limiter = Mock()
            mock_limiter._user_limits = {"user1": 10, "user2": 5}
            mock_get_limiter.return_value = mock_limiter

            with patch("time.time", return_value=1234567890):
                result = reset_rate_limits()

                assert result["status"] == "success"
                assert result["message"] == "Rate limits reset successfully"
                assert result["timestamp"] == 1234567890
                assert len(mock_limiter._user_limits) == 0

    def test_reset_rate_limits_error(self):
        """Test reset_rate_limits function with error."""
        with patch("ttskit.utils.rate_limiter.get_rate_limiter") as mock_get_limiter:
            mock_get_limiter.side_effect = Exception("Rate limiter error")

            with patch("time.time", return_value=1234567890):
                result = reset_rate_limits()

                assert result["status"] == "error"
                assert result["message"] == "Rate limiter error"
                assert result["timestamp"] == 1234567890


class TestAudioOutComprehensive:
    """Comprehensive tests for AudioOut class."""

    def test_audio_out_save(self):
        """Test AudioOut.save method."""
        with patch("pathlib.Path.write_bytes") as mock_write:
            audio_data = b"test_audio_data"
            audio_out = AudioOut(
                data=audio_data, format="ogg", duration=1.0, size=len(audio_data)
            )

            audio_out.save("test_output.ogg")

            mock_write.assert_called_once_with(audio_data)

    def test_audio_out_save_with_path_object(self):
        """Test AudioOut.save method with Path object."""
        with patch("pathlib.Path.write_bytes") as mock_write:
            audio_data = b"test_audio_data"
            audio_out = AudioOut(
                data=audio_data, format="ogg", duration=1.0, size=len(audio_data)
            )

            audio_out.save(Path("test_output.ogg"))

            mock_write.assert_called_once_with(audio_data)

    def test_audio_out_get_info(self):
        """Test AudioOut.get_info method."""
        audio_data = b"test_audio_data"
        audio_out = AudioOut(
            data=audio_data,
            format="mp3",
            duration=2.5,
            sample_rate=44100,
            channels=2,
            bitrate=192,
            size=len(audio_data),
            engine="gtts",
        )

        info = audio_out.get_info()

        assert isinstance(info, dict)
        assert info["format"] == "mp3"
        assert info["duration"] == 2.5
        assert info["sample_rate"] == 44100
        assert info["channels"] == 2
        assert info["bitrate"] == 192
        assert info["size"] == len(audio_data)
        assert "engine" not in info

    def test_audio_out_default_values(self):
        """Test AudioOut with default values."""
        audio_data = b"test_audio_data"
        audio_out = AudioOut(data=audio_data, format="ogg", duration=1.0)

        assert audio_out.sample_rate == 48000
        assert audio_out.channels == 1
        assert audio_out.bitrate == 128
        assert audio_out.size == 0
        assert audio_out.engine is None


class TestTTSAdvancedScenarios:
    """Advanced test scenarios for TTS class."""

    @pytest.mark.asyncio
    async def test_tts_synth_async_no_engine_selected(self):
        """Test TTS.synth_async when no engine is selected by router."""
        with (
            patch("ttskit.public.engine_factory") as mock_factory,
            patch("ttskit.public.audio_manager") as mock_manager,
        ):
            mock_factory.get_available_engines.return_value = ["gtts"]
            mock_engine = Mock()
            mock_engine.synth_async = AsyncMock(return_value=b"audio_data")
            mock_factory.get_engine.return_value = mock_engine

            mock_manager.get_from_cache.return_value = None
            mock_manager.process_audio = AsyncMock(return_value=b"processed_audio")
            mock_manager.get_audio_info.return_value = {
                "duration": 1.0,
                "sample_rate": 48000,
                "channels": 1,
                "bitrate": 128,
            }

            tts = TTS(default_lang="en")
            config = SynthConfig(text="Hello")

            result = await tts.synth_async(config)

            assert isinstance(result, AudioOut)
            assert result.data == b"processed_audio"

    @pytest.mark.asyncio
    async def test_tts_synth_async_no_available_engines(self):
        """Test TTS.synth_async when no engines are available."""
        with (
            patch("ttskit.public.engine_factory") as mock_factory,
            patch("ttskit.public.audio_manager") as mock_manager,
        ):
            mock_factory.get_available_engines.return_value = []
            mock_manager.get_from_cache.return_value = None

            tts = TTS(default_lang="en")
            config = SynthConfig(text="Hello")

            with pytest.raises(AllEnginesFailedError):
                await tts.synth_async(config)

    @pytest.mark.asyncio
    async def test_tts_synth_async_router_returns_engine_object(self):
        """Test TTS.synth_async when router returns engine object instead of string."""
        with (
            patch("ttskit.public.engine_factory") as mock_factory,
            patch("ttskit.public.audio_manager") as mock_manager,
        ):
            mock_engine = Mock()
            mock_engine.synth_async = AsyncMock(return_value=b"audio_data")
            mock_factory.get_engine.return_value = mock_engine

            mock_manager.get_from_cache.return_value = None
            mock_manager.process_audio = AsyncMock(return_value=b"processed_audio")
            mock_manager.get_audio_info.return_value = {
                "duration": 1.0,
                "sample_rate": 48000,
                "channels": 1,
                "bitrate": 128,
            }

            tts = TTS(default_lang="en")
            config = SynthConfig(text="Hello")

            result = await tts.synth_async(config)

            assert isinstance(result, AudioOut)
            assert result.data == b"processed_audio"

    @pytest.mark.asyncio
    async def test_tts_synth_async_cache_disabled(self):
        """Test TTS.synth_async with cache disabled."""
        with (
            patch("ttskit.public.engine_factory") as mock_factory,
            patch("ttskit.public.audio_manager") as mock_manager,
        ):
            mock_engine = Mock()
            mock_engine.synth_async = AsyncMock(return_value=b"audio_data")
            mock_factory.get_engine.return_value = mock_engine

            mock_manager.process_audio = AsyncMock(return_value=b"processed_audio")
            mock_manager.get_audio_info.return_value = {
                "duration": 1.0,
                "sample_rate": 48000,
                "channels": 1,
                "bitrate": 128,
            }

            tts = TTS(default_lang="en", cache_enabled=False)
            config = SynthConfig(text="Hello", cache=False)

            result = await tts.synth_async(config)

            assert isinstance(result, AudioOut)
            assert result.data == b"processed_audio"
            mock_manager.get_from_cache.assert_not_called()

    @pytest.mark.asyncio
    async def test_tts_synth_async_cache_save_async(self):
        """Test TTS.synth_async with async cache save."""
        with (
            patch("ttskit.public.engine_factory") as mock_factory,
            patch("ttskit.public.audio_manager") as mock_manager,
        ):
            mock_engine = Mock()
            mock_engine.synth_async = AsyncMock(return_value=b"audio_data")
            mock_factory.get_engine.return_value = mock_engine

            mock_manager.get_from_cache.return_value = None
            mock_manager.process_audio = AsyncMock(return_value=b"processed_audio")
            mock_manager.get_audio_info.return_value = {
                "duration": 1.0,
                "sample_rate": 48000,
                "channels": 1,
                "bitrate": 128,
            }

            mock_save_task = AsyncMock()
            mock_manager.save_to_cache.return_value = mock_save_task

            tts = TTS(default_lang="en", cache_enabled=True)
            config = SynthConfig(text="Hello", cache=True)

            result = await tts.synth_async(config)

            assert isinstance(result, AudioOut)
            assert result.data == b"processed_audio"
            mock_manager.save_to_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_tts_synth_async_cache_save_sync(self):
        """Test TTS.synth_async with sync cache save."""
        with (
            patch("ttskit.public.engine_factory") as mock_factory,
            patch("ttskit.public.audio_manager") as mock_manager,
        ):
            mock_engine = Mock()
            mock_engine.synth_async = AsyncMock(return_value=b"audio_data")
            mock_factory.get_engine.return_value = mock_engine

            mock_manager.get_from_cache.return_value = None
            mock_manager.process_audio = AsyncMock(return_value=b"processed_audio")
            mock_manager.get_audio_info.return_value = {
                "duration": 1.0,
                "sample_rate": 48000,
                "channels": 1,
                "bitrate": 128,
            }

            mock_manager.save_to_cache.return_value = None

            tts = TTS(default_lang="en", cache_enabled=True)
            config = SynthConfig(text="Hello", cache=True)

            result = await tts.synth_async(config)

            assert isinstance(result, AudioOut)
            assert result.data == b"processed_audio"

    def test_tts_get_engine_preferences_default(self):
        """Test TTS.get_engine_preferences with default values."""
        tts = TTS(default_lang="fa", default_engine="edge", cache_enabled=False)

        preferences = tts.get_engine_preferences()

        assert preferences["default_lang"] == "fa"
        assert preferences["default_engine"] == "edge"
        assert preferences["cache_enabled"] is False

    def test_tts_get_engine_preferences_custom(self):
        """Test TTS.get_engine_preferences with custom preferences."""
        tts = TTS(default_lang="en")
        tts.set_engine_preferences({"en": ["gtts"], "fa": ["edge"]})

        preferences = tts.get_engine_preferences()

        assert preferences["en"] == ["gtts"]
        assert preferences["fa"] == ["edge"]

    def test_tts_get_engine_preferences_empty(self):
        """Test TTS.get_engine_preferences with empty preferences."""
        tts = TTS(default_lang="en")
        tts.set_engine_preferences({})

        preferences = tts.get_engine_preferences()

        assert preferences["default_lang"] == "en"
        assert preferences["default_engine"] is None
        assert preferences["cache_enabled"] is True


class TestSynthFunctionAdvanced:
    """Advanced tests for synth convenience function."""

    def test_synth_function_with_kwargs(self):
        """Test synth convenience function with additional kwargs."""
        with patch("ttskit.public.TTS") as mock_tts_class:
            mock_tts = Mock()
            mock_audio_out = AudioOut(
                data=b"audio_data", format="ogg", duration=1.0, size=10
            )
            mock_tts.synth.return_value = mock_audio_out
            mock_tts_class.return_value = mock_tts

            result = synth("Hello World", "en", extra_param="value")

            assert isinstance(result, AudioOut)
            assert result.data == b"audio_data"

    def test_synth_function_with_format_and_output_format(self):
        """Test synth convenience function with both format and output_format."""
        with patch("ttskit.public.TTS") as mock_tts_class:
            mock_tts = Mock()
            mock_audio_out = AudioOut(
                data=b"audio_data", format="mp3", duration=1.0, size=10
            )
            mock_tts.synth.return_value = mock_audio_out
            mock_tts_class.return_value = mock_tts

            result = synth("Hello World", "en", format="mp3", output_format="ogg")

            assert isinstance(result, AudioOut)
            assert result.data == b"audio_data"

    def test_synth_function_with_empty_output_format(self):
        """Test synth convenience function with empty output_format."""
        with patch("ttskit.public.TTS") as mock_tts_class:
            mock_tts = Mock()
            mock_audio_out = AudioOut(
                data=b"audio_data", format="mp3", duration=1.0, size=10
            )
            mock_tts.synth.return_value = mock_audio_out
            mock_tts_class.return_value = mock_tts

            result = synth("Hello World", "en", format="mp3", output_format="")

            assert isinstance(result, AudioOut)
            assert result.data == b"audio_data"


class TestAdditionalUtilityFunctions:
    """Tests for additional utility functions not covered in main tests."""

    def test_get_engine_capabilities_comprehensive(self):
        """Test get_engine_capabilities function comprehensively."""
        capabilities = get_engine_capabilities()

        expected_engines = ["gtts", "edge", "piper"]
        for engine in expected_engines:
            assert engine in capabilities

        gtts = capabilities["gtts"]
        assert gtts["name"] == "Google Text-to-Speech"
        assert isinstance(gtts["languages"], list)
        assert len(gtts["languages"]) > 0
        assert "en" in gtts["languages"]
        assert isinstance(gtts["voices"], list)
        assert "default" in gtts["voices"]
        assert isinstance(gtts["features"], list)
        assert "online" in gtts["features"]
        assert "free" in gtts["features"]
        assert "fast" in gtts["features"]
        assert gtts["quality"] == "good"
        assert gtts["latency"] == "low"

        edge = capabilities["edge"]
        assert edge["name"] == "Microsoft Edge TTS"
        assert "ar" in edge["languages"]
        assert "fa" in edge["languages"]
        assert "multiple" in edge["voices"]
        assert "high_quality" in edge["features"]
        assert edge["quality"] == "excellent"
        assert edge["latency"] == "medium"

        piper = capabilities["piper"]
        assert piper["name"] == "Piper TTS"
        assert "offline" in piper["features"]
        assert piper["quality"] == "good"
        assert piper["latency"] == "very_low"

    def test_get_documentation_comprehensive(self):
        """Test get_documentation function comprehensively."""
        doc = get_documentation()

        required_fields = [
            "name",
            "version",
            "description",
            "features",
            "engines",
            "telegram_adapters",
            "supported_languages",
            "documentation_url",
            "api_docs",
        ]
        for field in required_fields:
            assert field in doc

        assert doc["name"] == "TTSKit"
        assert doc["version"] == "1.0.0"
        assert (
            doc["description"]
            == "Multi-engine Text-to-Speech toolkit with Telegram bot support"
        )

        expected_features = [
            "Multiple TTS engines (gTTS, Edge-TTS, Piper)",
            "Telegram bot support (Aiogram, Pyrogram, Telethon, Telebot)",
            "Audio processing and conversion",
            "Caching and rate limiting",
            "Internationalization support",
            "Health monitoring and metrics",
        ]
        assert doc["features"] == expected_features

        expected_engines = ["gtts", "edge", "piper"]
        assert doc["engines"] == expected_engines

        expected_adapters = ["aiogram", "pyrogram", "telethon", "telebot"]
        assert doc["telegram_adapters"] == expected_adapters

        expected_languages = [
            "en",
            "fa",
            "ar",
            "es",
            "fr",
            "de",
            "it",
            "pt",
            "ru",
            "ja",
            "ko",
            "zh",
        ]
        assert doc["supported_languages"] == expected_languages

        assert doc["documentation_url"] == "https://github.com/your-repo/ttskit"
        assert (
            doc["api_docs"]
            == "https://github.com/your-repo/ttskit/blob/main/docs/api.md"
        )

    def test_get_examples_comprehensive(self):
        """Test get_examples function comprehensively."""
        examples = get_examples()

        expected_categories = [
            "basic_usage",
            "engine_selection",
            "telegram_bot",
            "audio_processing",
            "caching",
            "rate_limiting",
        ]
        for category in expected_categories:
            assert category in examples

        basic_usage = examples["basic_usage"]
        assert isinstance(basic_usage, list)
        assert len(basic_usage) > 0
        assert any("TTSBot" in example for example in basic_usage)

        engine_selection = examples["engine_selection"]
        assert isinstance(engine_selection, list)
        assert any("get_engine" in example for example in engine_selection)

        telegram_bot = examples["telegram_bot"]
        assert isinstance(telegram_bot, list)
        assert any("TTSBot" in example for example in telegram_bot)

        audio_processing = examples["audio_processing"]
        assert isinstance(audio_processing, list)
        assert any("to_opus_ogg" in example for example in audio_processing)

        caching = examples["caching"]
        assert isinstance(caching, list)
        assert any("get_cache" in example for example in caching)

        rate_limiting = examples["rate_limiting"]
        assert isinstance(rate_limiting, list)
        assert any("check_rate_limit" in example for example in rate_limiting)

    def test_get_supported_languages_comprehensive(self):
        """Test get_supported_languages function comprehensively."""
        languages = get_supported_languages()

        assert isinstance(languages, list)
        assert len(languages) > 0

        expected_languages = [
            "en",
            "fa",
            "ar",
            "es",
            "fr",
            "de",
            "it",
            "pt",
            "ru",
            "ja",
            "ko",
            "zh",
            "hi",
            "tr",
            "pl",
            "nl",
            "sv",
            "da",
            "no",
        ]
        for lang in expected_languages:
            assert lang in languages

        assert len(languages) == len(set(languages))

    def test_get_supported_formats_comprehensive(self):
        """Test get_supported_formats function comprehensively."""
        formats = get_supported_formats()

        assert isinstance(formats, list)
        assert len(formats) > 0

        expected_formats = ["ogg", "mp3", "wav", "flac", "aac", "m4a"]
        for fmt in expected_formats:
            assert fmt in formats

        assert len(formats) == len(set(formats))


class TestErrorHandlingAndEdgeCases:
    """Tests for error handling and edge cases."""

    def test_synth_config_empty_text(self):
        """Test SynthConfig with empty text (should be allowed)."""
        config = SynthConfig(text="")
        assert config.text == ""
        assert config.lang == "en"
        assert config.rate == 1.0

    def test_synth_config_minimal_values(self):
        """Test SynthConfig with minimal required values."""
        config = SynthConfig(text="Test")
        assert config.text == "Test"
        assert config.lang == "en"
        assert config.voice is None
        assert config.engine is None
        assert config.rate == 1.0
        assert config.pitch == 0.0
        assert config.output_format == "ogg"
        assert config.cache is True

    def test_synth_config_maximal_values(self):
        """Test SynthConfig with all values specified."""
        config = SynthConfig(
            text="Hello World",
            lang="fa",
            voice="female",
            engine="edge",
            rate=1.5,
            pitch=2.0,
            output_format="mp3",
            cache=False,
        )
        assert config.text == "Hello World"
        assert config.lang == "fa"
        assert config.voice == "female"
        assert config.engine == "edge"
        assert config.rate == 1.5
        assert config.pitch == 2.0
        assert config.output_format == "mp3"
        assert config.cache is False

    def test_audio_out_minimal_construction(self):
        """Test AudioOut with minimal required values."""
        audio_data = b"test"
        audio_out = AudioOut(data=audio_data, format="ogg", duration=0.0)

        assert audio_out.data == audio_data
        assert audio_out.format == "ogg"
        assert audio_out.duration == 0.0
        assert audio_out.sample_rate == 48000
        assert audio_out.channels == 1
        assert audio_out.bitrate == 128
        assert audio_out.size == 0
        assert audio_out.engine is None

    def test_audio_out_maximal_construction(self):
        """Test AudioOut with all values specified."""
        audio_data = b"test_audio_data"
        audio_out = AudioOut(
            data=audio_data,
            format="mp3",
            duration=3.5,
            sample_rate=44100,
            channels=2,
            bitrate=320,
            size=len(audio_data),
            engine="gtts",
        )

        assert audio_out.data == audio_data
        assert audio_out.format == "mp3"
        assert audio_out.duration == 3.5
        assert audio_out.sample_rate == 44100
        assert audio_out.channels == 2
        assert audio_out.bitrate == 320
        assert audio_out.size == len(audio_data)
        assert audio_out.engine == "gtts"

    def test_tts_initialization_variations(self):
        """Test TTS initialization with various parameter combinations."""
        tts1 = TTS(default_lang="fa", default_engine="edge", cache_enabled=False)
        assert tts1.default_lang == "fa"
        assert tts1.default_engine == "edge"
        assert tts1.cache_enabled is False

        tts2 = TTS()
        assert tts2.default_lang == "en"
        assert tts2.default_engine is None
        assert tts2.cache_enabled is True

        tts3 = TTS(default_lang="ar")
        assert tts3.default_lang == "ar"
        assert tts3.default_engine is None
        assert tts3.cache_enabled is True

    def test_cache_key_generation_variations(self):
        """Test cache key generation with various configurations."""
        tts = TTS(default_lang="en")

        config1 = SynthConfig(
            text="Hello",
            lang="en",
            voice="default",
            engine="gtts",
            rate=1.0,
            pitch=0.0,
            output_format="ogg",
        )
        key1 = tts._generate_cache_key(config1)

        config2 = SynthConfig(text="Hello")
        key2 = tts._generate_cache_key(config2)

        assert key1 != key2

        assert len(key1) == 64
        assert len(key2) == 64
        assert all(c in "0123456789abcdef" for c in key1)
        assert all(c in "0123456789abcdef" for c in key2)

    def test_bytes_to_audio_out_variations(self):
        """Test _bytes_to_audio_out with various audio manager responses."""
        tts = TTS(default_lang="en")
        audio_data = b"test_audio_data"

        with patch("ttskit.public.audio_manager") as mock_manager:
            mock_manager.get_audio_info.return_value = {
                "duration": 2.0,
                "sample_rate": 22050,
                "channels": 2,
                "bitrate": 64,
            }

            result = tts._bytes_to_audio_out(audio_data, "wav")

            assert result.data == audio_data
            assert result.format == "wav"
            assert result.duration == 2.0
            assert result.sample_rate == 22050
            assert result.channels == 2
            assert result.bitrate == 64
            assert result.size == len(audio_data)

        with patch("ttskit.public.audio_manager") as mock_manager:
            mock_manager.get_audio_info.return_value = {}

            result = tts._bytes_to_audio_out(audio_data, "mp3")

            assert result.data == audio_data
            assert result.format == "mp3"
            assert result.duration == 0.0
            assert result.sample_rate == 48000
            assert result.channels == 1
            assert result.bitrate == 128
            assert result.size == len(audio_data)


class TestMissingCoverageFunctions:
    """Tests for functions that were missing from coverage report."""

    def test_tts_reset_stats(self):
        """Test TTS.reset_stats method."""
        tts = TTS(default_lang="en")
        tts.reset_stats()
        stats = tts.get_stats()
        assert isinstance(stats, dict)

    def test_tts_get_stats_comprehensive(self):
        """Test TTS.get_stats method comprehensively."""
        tts = TTS(default_lang="en")
        stats = tts.get_stats()

        assert isinstance(stats, dict)
        expected_keys = ["total_requests", "successful_requests", "failed_requests"]
        for key in expected_keys:
            assert key in stats

    def test_tts_synth_sync_comprehensive(self):
        """Test TTS.synth method comprehensively."""
        with (
            patch("ttskit.public.engine_factory") as mock_factory,
            patch("ttskit.public.audio_manager") as mock_manager,
        ):
            mock_engine = Mock()
            mock_engine.synth_async = AsyncMock(return_value=b"audio_data")
            mock_factory.get_engine.return_value = mock_engine

            mock_manager.get_from_cache.return_value = None
            mock_manager.process_audio = AsyncMock(return_value=b"processed_audio")
            mock_manager.get_audio_info.return_value = {
                "duration": 1.0,
                "sample_rate": 48000,
                "channels": 1,
                "bitrate": 128,
            }

            tts = TTS(default_lang="en")
            config = SynthConfig(text="Hello", engine="gtts")

            result = tts.synth(config)

            assert isinstance(result, AudioOut)
            assert result.data == b"processed_audio"

    def test_tts_synth_sync_with_fallback(self):
        """Test TTS.synth method with fallback scenario."""
        with (
            patch("ttskit.public.engine_factory") as mock_factory,
            patch("ttskit.public.audio_manager") as mock_manager,
            patch.object(TTS, "_try_fallback_engines") as mock_fallback,
        ):
            mock_engine = Mock()
            mock_engine.synth_async = AsyncMock(side_effect=Exception("Engine failed"))
            mock_factory.get_engine.return_value = mock_engine

            mock_manager.get_from_cache.return_value = None
            mock_fallback.return_value = AudioOut(
                data=b"fallback_audio", format="ogg", duration=1.0, size=10
            )

            tts = TTS(default_lang="en")
            config = SynthConfig(text="Hello", engine="gtts")

            result = tts.synth(config)

            assert isinstance(result, AudioOut)
            assert result.data == b"fallback_audio"

    def test_tts_synth_sync_with_all_engines_failed(self):
        """Test TTS.synth method when all engines fail."""
        with (
            patch("ttskit.public.engine_factory") as mock_factory,
            patch("ttskit.public.audio_manager") as mock_manager,
            patch.object(TTS, "_try_fallback_engines") as mock_fallback,
        ):
            mock_engine = Mock()
            mock_engine.synth_async = AsyncMock(side_effect=Exception("Engine failed"))
            mock_factory.get_engine.return_value = mock_engine

            mock_manager.get_from_cache.return_value = None
            mock_fallback.side_effect = AllEnginesFailedError("All engines failed")

            tts = TTS(default_lang="en")
            config = SynthConfig(text="Hello", engine="gtts")

            with pytest.raises(AllEnginesFailedError):
                tts.synth(config)

    def test_tts_synth_sync_with_other_fallback_error(self):
        """Test TTS.synth method with other fallback error."""
        with (
            patch("ttskit.public.engine_factory") as mock_factory,
            patch("ttskit.public.audio_manager") as mock_manager,
            patch.object(TTS, "_try_fallback_engines") as mock_fallback,
        ):
            mock_engine = Mock()
            mock_engine.synth_async = AsyncMock(side_effect=Exception("Engine failed"))
            mock_factory.get_engine.return_value = mock_engine

            mock_manager.get_from_cache.return_value = None
            mock_fallback.side_effect = Exception("Fallback error")

            tts = TTS(default_lang="en")
            config = SynthConfig(text="Hello", engine="gtts")

            with pytest.raises(TTSKitEngineError):
                tts.synth(config)


class TestConvenienceFunctionsMissingCoverage:
    """Tests for convenience functions that were missing coverage."""

    @pytest.mark.asyncio
    async def test_synth_async_function_comprehensive(self):
        """Test synth_async convenience function comprehensively."""
        with patch("ttskit.public.TTS") as mock_tts_class:
            mock_tts = Mock()
            mock_audio_out = AudioOut(
                data=b"audio_data", format="ogg", duration=1.0, size=10
            )

            async def async_synth():
                return mock_audio_out

            mock_tts.synth_async.return_value = async_synth()
            mock_tts_class.return_value = mock_tts

            result = await synth_async("Hello World", "en")

            assert isinstance(result, AudioOut)
            assert result.data == b"audio_data"

    @pytest.mark.asyncio
    async def test_synth_async_function_with_all_parameters(self):
        """Test synth_async convenience function with all parameters."""
        with patch("ttskit.public.TTS") as mock_tts_class:
            mock_tts = Mock()
            mock_audio_out = AudioOut(
                data=b"audio_data", format="mp3", duration=2.0, size=20
            )
            mock_tts.synth_async.return_value = mock_audio_out
            mock_tts_class.return_value = mock_tts

            result = await synth_async(
                "Hello World",
                "fa",
                voice="female",
                engine="edge",
                rate=1.2,
                pitch=1.0,
                output_format="mp3",
                cache=False,
            )

            assert isinstance(result, AudioOut)
            assert result.data == b"audio_data"

    def test_synth_function_comprehensive(self):
        """Test synth convenience function comprehensively."""
        with patch("ttskit.public.TTS") as mock_tts_class:
            mock_tts = Mock()
            mock_audio_out = AudioOut(
                data=b"audio_data", format="wav", duration=1.5, size=15
            )
            mock_tts.synth.return_value = mock_audio_out
            mock_tts_class.return_value = mock_tts

            result = synth(
                "Hello World",
                "ar",
                voice="male",
                engine="piper",
                rate=0.8,
                pitch=-1.0,
                output_format="wav",
                cache=True,
            )

            assert isinstance(result, AudioOut)
            assert result.data == b"audio_data"

    def test_list_voices_function_comprehensive(self):
        """Test list_voices convenience function comprehensively."""
        with patch("ttskit.public.TTS") as mock_tts_class:
            mock_tts = Mock()
            mock_voices = ["voice1", "voice2", "voice3"]
            mock_tts.list_voices.return_value = mock_voices
            mock_tts_class.return_value = mock_tts

            voices = list_voices()
            assert voices == mock_voices
            mock_tts.list_voices.assert_called_with(None, None)

            voices = list_voices("fa")
            assert voices == mock_voices
            mock_tts.list_voices.assert_called_with("fa", None)

            voices = list_voices(engine="edge")
            assert voices == mock_voices
            mock_tts.list_voices.assert_called_with(None, "edge")

    def test_get_engines_function_comprehensive(self):
        """Test get_engines convenience function comprehensively."""
        with patch("ttskit.public.engine_factory") as mock_factory:
            mock_factory.get_all_engines_info.return_value = {
                "gtts": {
                    "name": "Google TTS",
                    "available": True,
                    "capabilities": {
                        "offline": False,
                        "languages": ["en", "es", "fr"],
                        "voices": ["default", "female", "male"],
                    },
                },
                "edge": {
                    "name": "Edge TTS",
                    "available": True,
                    "capabilities": {
                        "offline": False,
                        "languages": ["en", "fa", "ar"],
                        "voices": ["multiple"],
                    },
                },
                "piper": {
                    "name": "Piper TTS",
                    "available": True,
                    "capabilities": {
                        "offline": True,
                        "languages": ["en", "es"],
                        "voices": ["en_US-lessac-low"],
                    },
                },
            }

            engines = get_engines()

            assert isinstance(engines, list)
            assert len(engines) == 3

            for engine in engines:
                assert "offline" in engine
                assert "languages" in engine
                assert "voices" in engine
                assert "name" in engine
                assert "available" in engine

    def test_get_engines_function_with_empty_capabilities(self):
        """Test get_engines convenience function with empty capabilities."""
        with patch("ttskit.public.engine_factory") as mock_factory:
            mock_factory.get_all_engines_info.return_value = {
                "gtts": {
                    "name": "Google TTS",
                    "available": True,
                    "capabilities": {},
                }
            }

            engines = get_engines()

            assert isinstance(engines, list)
            assert len(engines) == 1

            engine = engines[0]
            assert engine["offline"] is False
            assert engine["languages"] == []
            assert engine["voices"] == []


class TestAdditionalEdgeCases:
    """Additional edge cases and scenarios for complete coverage."""

    def test_synth_config_edge_cases(self):
        """Test SynthConfig with edge case values."""
        config = SynthConfig(text="Test", rate=0.001)
        assert config.rate == 0.001

        config = SynthConfig(text="Test", rate=10.0)
        assert config.rate == 10.0

        config = SynthConfig(text="Test", pitch=-5.0)
        assert config.pitch == -5.0

        config = SynthConfig(text="Test", pitch=5.0)
        assert config.pitch == 5.0

    def test_audio_out_edge_cases(self):
        """Test AudioOut with edge case values."""
        audio_out = AudioOut(data=b"test", format="ogg", duration=0.0)
        assert audio_out.duration == 0.0

        audio_out = AudioOut(data=b"test", format="ogg", duration=3600.0)
        assert audio_out.duration == 3600.0

        audio_out = AudioOut(data=b"", format="ogg", duration=1.0, size=0)
        assert audio_out.size == 0

        audio_out = AudioOut(
            data=b"x" * 1000000, format="ogg", duration=1.0, size=1000000
        )
        assert audio_out.size == 1000000

    def test_tts_initialization_edge_cases(self):
        """Test TTS initialization with edge case values."""
        tts = TTS(default_lang="")
        assert tts.default_lang == ""

        tts = TTS(default_lang="very-long-language-code")
        assert tts.default_lang == "very-long-language-code"

        tts = TTS(default_engine="")
        assert tts.default_engine == ""

    def test_cache_key_generation_edge_cases(self):
        """Test cache key generation with edge case values."""
        tts = TTS(default_lang="en")

        config = SynthConfig(text="")
        key = tts._generate_cache_key(config)
        assert isinstance(key, str)
        assert len(key) == 64

        long_text = "x" * 10000
        config = SynthConfig(text=long_text)
        key = tts._generate_cache_key(config)
        assert isinstance(key, str)
        assert len(key) == 64

        config = SynthConfig(text="Hello 世界! مرحبا! 🌍")
        key = tts._generate_cache_key(config)
        assert isinstance(key, str)
        assert len(key) == 64

    def test_bytes_to_audio_out_edge_cases(self):
        """Test _bytes_to_audio_out with edge case values."""
        tts = TTS(default_lang="en")

        with patch("ttskit.public.audio_manager") as mock_manager:
            mock_manager.get_audio_info.return_value = {
                "duration": 0.0,
                "sample_rate": 48000,
                "channels": 1,
                "bitrate": 128,
            }

            result = tts._bytes_to_audio_out(b"", "ogg")
            assert result.data == b""
            assert result.size == 0

        large_data = b"x" * 1000000
        with patch("ttskit.public.audio_manager") as mock_manager:
            mock_manager.get_audio_info.return_value = {
                "duration": 100.0,
                "sample_rate": 48000,
                "channels": 2,
                "bitrate": 320,
            }

            result = tts._bytes_to_audio_out(large_data, "mp3")
            assert result.data == large_data
            assert result.size == len(large_data)
            assert result.duration == 100.0
            assert result.sample_rate == 48000
            assert result.channels == 2
            assert result.bitrate == 320

    def test_audio_out_save_edge_cases(self):
        """Test AudioOut.save with edge case file paths."""
        audio_data = b"test_audio_data"
        audio_out = AudioOut(data=audio_data, format="ogg", duration=1.0)

        with patch("pathlib.Path.write_bytes") as mock_write:
            audio_out.save("relative/path/file.ogg")
            mock_write.assert_called_once_with(audio_data)

        with patch("pathlib.Path.write_bytes") as mock_write:
            audio_out.save("/absolute/path/file.ogg")
            mock_write.assert_called_once_with(audio_data)

        with patch("pathlib.Path.write_bytes") as mock_write:
            audio_out.save("path/with spaces & symbols!.ogg")
            mock_write.assert_called_once_with(audio_data)

    def test_audio_out_get_info_edge_cases(self):
        """Test AudioOut.get_info with edge case values."""
        audio_out = AudioOut(data=b"test", format="ogg", duration=0.0)
        info = audio_out.get_info()

        assert info["format"] == "ogg"
        assert info["duration"] == 0.0
        assert info["sample_rate"] == 48000
        assert info["channels"] == 1
        assert info["bitrate"] == 128
        assert info["size"] == 0

        audio_out = AudioOut(
            data=b"test_data",
            format="mp3",
            duration=999.999,
            sample_rate=44100,
            channels=2,
            bitrate=320,
            size=12345,
            engine="custom_engine",
        )
        info = audio_out.get_info()

        assert info["format"] == "mp3"
        assert info["duration"] == 999.999
        assert info["sample_rate"] == 44100
        assert info["channels"] == 2
        assert info["bitrate"] == 320
        assert info["size"] == 12345
        assert "engine" not in info
