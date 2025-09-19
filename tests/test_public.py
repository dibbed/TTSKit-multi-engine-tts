"""Tests for Public API."""

from unittest.mock import Mock, patch

import pytest

from ttskit.public import (
    TTS,
    AudioOut,
    SynthConfig,
    get_engines,
    get_supported_languages,
    list_voices,
    synth,
    synth_async,
)


class TestPublicAPI:
    """Test cases for Public API."""

    def test_synth_config_initialization(self):
        """Test SynthConfig initialization."""
        config = SynthConfig(
            text="Hello World",
            lang="en",
            voice="default",
            engine="gtts",
            rate=1.0,
            pitch=0.0,
            output_format="ogg",
            cache=True,
        )

        assert config.text == "Hello World"
        assert config.lang == "en"
        assert config.voice == "default"
        assert config.engine == "gtts"
        assert config.rate == 1.0
        assert config.pitch == 0.0
        assert config.output_format == "ogg"
        assert config.cache is True

    def test_synth_config_default_values(self):
        """Test SynthConfig with default values."""
        config = SynthConfig(text="Hello World")

        assert config.text == "Hello World"
        assert config.lang == "en"
        assert config.voice is None
        assert config.engine is None
        assert config.rate == 1.0
        assert config.pitch == 0.0
        assert config.output_format == "ogg"
        assert config.cache is True

    def test_audio_out_initialization(self):
        """Test AudioOut initialization."""
        audio_data = b"test_audio_data"
        audio_out = AudioOut(
            data=audio_data,
            format="ogg",
            duration=1.5,
            size=len(audio_data),
            engine="gtts",
        )

        assert audio_out.data == audio_data
        assert audio_out.format == "ogg"
        assert audio_out.duration == 1.5
        assert audio_out.size == len(audio_data)
        assert audio_out.engine == "gtts"

    def test_tts_initialization(self):
        """Test TTS initialization."""
        tts = TTS(default_lang="en")

        assert tts.default_lang == "en"
        assert tts.smart_router is not None

    def test_tts_initialization_with_default_lang(self):
        """Test TTS initialization with default language."""
        tts = TTS(default_lang="fa")

        assert tts.default_lang == "fa"

    @pytest.mark.asyncio
    async def test_tts_synth_async(self):
        """Test TTS async synthesis."""
        tts = TTS(default_lang="en")

        mock_router = Mock()
        mock_router.synth_async.return_value = (b"audio_data", "gtts")
        tts.smart_router = mock_router

        config = SynthConfig(text="Hello World")
        result = await tts.synth_async(config)

        assert isinstance(result, AudioOut)
        assert isinstance(result.data, bytes)
        assert len(result.data) > 0

    @pytest.mark.asyncio
    async def test_tts_synth_async_with_voice(self):
        """Test TTS async synthesis with voice."""
        tts = TTS(default_lang="en")

        mock_router = Mock()
        mock_router.synth_async.return_value = (b"audio_data", "gtts")
        tts.smart_router = mock_router

        config = SynthConfig(text="Hello World", voice="voice1")
        result = await tts.synth_async(config)

        assert isinstance(result, AudioOut)
        assert isinstance(result.data, bytes)
        assert len(result.data) > 0

    def test_tts_synth_sync(self):
        """Test TTS synchronous synthesis."""
        tts = TTS(default_lang="en")

        mock_router = Mock()
        mock_router.synth_async.return_value = (b"audio_data", "gtts")
        tts.smart_router = mock_router

        config = SynthConfig(text="Hello World")
        result = tts.synth(config)

        assert isinstance(result, AudioOut)
        assert isinstance(result.data, bytes)
        assert len(result.data) > 0

    def test_tts_get_stats(self):
        """Test TTS statistics."""
        tts = TTS(default_lang="en")

        stats = tts.get_stats()

        assert isinstance(stats, dict)
        assert "total_requests" in stats
        assert "successful_requests" in stats
        assert "failed_requests" in stats

    def test_tts_reset_stats(self):
        """Test TTS statistics reset."""
        tts = TTS(default_lang="en")

        tts.stats["total_requests"] = 10
        tts.stats["successful_requests"] = 8

        tts.reset_stats()

        assert tts.stats["total_requests"] == 0
        assert tts.stats["successful_requests"] == 0

    def test_get_engines(self):
        """Test getting available engines."""
        engines = get_engines()

        assert isinstance(engines, list)
        assert len(engines) > 0

        for engine in engines:
            assert "name" in engine
            assert "available" in engine
            assert "offline" in engine
            assert "languages" in engine
            assert "voices" in engine

    def test_get_supported_languages(self):
        """Test getting supported languages."""
        languages = get_supported_languages()

        assert isinstance(languages, list)
        assert len(languages) > 0
        assert "en" in languages

    def test_list_voices(self):
        """Test listing voices."""
        voices = list_voices()
        assert isinstance(voices, list)

    def test_list_voices_with_language(self):
        """Test listing voices with specific language."""
        voices = list_voices(lang="en")
        assert isinstance(voices, list)

    def test_list_voices_with_engine(self):
        """Test listing voices with specific engine."""
        voices = list_voices(engine="gtts")
        assert isinstance(voices, list)

    def test_list_voices_with_language_and_engine(self):
        """Test listing voices with specific language and engine."""
        voices = list_voices(lang="en", engine="gtts")
        assert isinstance(voices, list)

    @pytest.mark.asyncio
    async def test_synth_async_function(self):
        """Test synth_async function."""
        with patch("ttskit.public.TTS") as mock_tts_class:
            mock_tts = Mock()
            mock_tts.synth_async.return_value = AudioOut(
                data=b"audio_data",
                format="ogg",
                duration=1.0,
                size=10,
                engine="gtts",
            )
            mock_tts_class.return_value = mock_tts

            result = await synth_async("Hello World", "en")

            assert isinstance(result, AudioOut)
            assert result.data == b"audio_data"

    def test_synth_function(self):
        """Test synth function."""
        with patch("ttskit.public.TTS") as mock_tts_class:
            mock_tts = Mock()
            mock_tts.synth.return_value = AudioOut(
                data=b"audio_data",
                format="ogg",
                duration=1.0,
                size=10,
                engine="gtts",
            )
            mock_tts_class.return_value = mock_tts

            result = synth("Hello World", "en")

            assert isinstance(result, AudioOut)
            assert result.data == b"audio_data"

    def test_synth_with_voice(self):
        """Test synth function with voice."""
        with patch("ttskit.public.TTS") as mock_tts_class:
            mock_tts = Mock()
            mock_tts.synth.return_value = AudioOut(
                data=b"audio_data",
                format="ogg",
                duration=1.0,
                size=10,
                engine="gtts",
            )
            mock_tts_class.return_value = mock_tts

            result = synth("Hello World", "en", voice="voice1")

            assert isinstance(result, AudioOut)
            assert result.data == b"audio_data"

    def test_synth_with_engine(self):
        """Test synth function with engine."""
        with patch("ttskit.public.TTS") as mock_tts_class:
            mock_tts = Mock()
            mock_tts.synth.return_value = AudioOut(
                data=b"audio_data",
                format="ogg",
                duration=1.0,
                size=10,
                engine="gtts",
            )
            mock_tts_class.return_value = mock_tts

            result = synth("Hello World", "en", engine="gtts")

            assert isinstance(result, AudioOut)
            assert result.data == b"audio_data"

    def test_synth_with_rate_and_pitch(self):
        """Test synth function with rate and pitch."""
        with patch("ttskit.public.TTS") as mock_tts_class:
            mock_tts = Mock()
            mock_tts.synth.return_value = AudioOut(
                data=b"audio_data",
                format="ogg",
                duration=1.0,
                size=10,
                engine="gtts",
            )
            mock_tts_class.return_value = mock_tts

            result = synth("Hello World", "en", rate=1.2, pitch=2.0)

            assert isinstance(result, AudioOut)
            assert result.data == b"audio_data"

    def test_synth_with_format(self):
        """Test synth function with format."""
        with patch("ttskit.public.TTS") as mock_tts_class:
            mock_tts = Mock()
            mock_tts.synth.return_value = AudioOut(
                data=b"audio_data",
                format="mp3",
                duration=1.0,
                size=10,
                engine="gtts",
            )
            mock_tts_class.return_value = mock_tts

            result = synth("Hello World", "en", format="mp3")

            assert isinstance(result, AudioOut)
            assert result.data == b"audio_data"
            assert result.format == "mp3"

    def test_synth_with_cache(self):
        """Test synth function with cache parameter."""
        with patch("ttskit.public.TTS") as mock_tts_class:
            mock_tts = Mock()
            mock_tts.synth.return_value = AudioOut(
                data=b"audio_data",
                format="ogg",
                duration=1.0,
                size=10,
                engine="gtts",
            )
            mock_tts_class.return_value = mock_tts

            result = synth("Hello World", "en", cache=False)

            assert isinstance(result, AudioOut)
            assert result.data == b"audio_data"

    def test_audio_out_properties(self):
        """Test AudioOut properties."""
        audio_data = b"test_audio_data"
        audio_out = AudioOut(
            data=audio_data,
            format="ogg",
            duration=1.5,
            size=len(audio_data),
            engine="gtts",
        )

        assert audio_out.data == audio_data
        assert audio_out.format == "ogg"
        assert audio_out.duration == 1.5
        assert audio_out.size == len(audio_data)
        assert audio_out.engine == "gtts"

    def test_synth_config_validation(self):
        """Test SynthConfig validation."""
        config = SynthConfig(text="Hello World")
        assert config.text == "Hello World"

        config = SynthConfig(text="")
        assert config.text == ""

    def test_tts_engine_preferences(self):
        """Test TTS engine preferences."""
        tts = TTS(default_lang="en")

        preferences = tts.get_engine_preferences()
        assert isinstance(preferences, dict)

        tts.set_engine_preferences({"en": ["gtts", "edge"]})
        preferences = tts.get_engine_preferences()
        assert preferences["en"] == ["gtts", "edge"]
