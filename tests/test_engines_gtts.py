"""Tests for gTTS engine."""

from unittest.mock import Mock, patch

import pytest

from ttskit.engines.gtts_engine import GTTSEngine


class TestGTTSEngine:
    """Test cases for GTTSEngine."""

    def test_initialization(self):
        """Test engine initialization."""
        engine = GTTSEngine(default_lang="en")
        assert engine.default_lang == "en"
        assert engine.is_available()

    def test_get_capabilities(self):
        """Test engine capabilities."""
        engine = GTTSEngine()
        caps = engine.get_capabilities()

        assert caps.offline is False
        assert caps.ssml is False
        assert caps.rate is False
        assert caps.pitch is False
        assert "en" in caps.languages
        assert caps.max_text_length > 0

    def test_capabilities_dict(self):
        """Test capabilities as dictionary."""
        engine = GTTSEngine()
        caps_dict = engine.capabilities()

        assert isinstance(caps_dict, dict)
        assert "offline" in caps_dict
        assert "ssml" in caps_dict
        assert "rate" in caps_dict
        assert "pitch" in caps_dict
        assert "langs" in caps_dict
        assert "voices" in caps_dict

    def test_list_voices(self):
        """Test voice listing."""
        engine = GTTSEngine()
        voices = engine.list_voices()

        assert isinstance(voices, list)
        assert len(voices) > 0

    def test_list_voices_with_lang(self):
        """Test voice listing with language filter."""
        engine = GTTSEngine()
        voices = engine.list_voices("en")

        assert isinstance(voices, list)

    def test_supports_language(self):
        """Test language support checking."""
        engine = GTTSEngine()

        assert engine.supports_language("en")
        assert engine.supports_language("fa")
        assert not engine.supports_language("invalid")

    def test_validate_input(self):
        """Test input validation."""
        engine = GTTSEngine()

        assert engine.validate_input("Hello world", "en") is None

        result = engine.validate_input("Hello world", "invalid")
        assert result is not None
        assert "language" in result.lower()

    def test_can_handle_text_length(self):
        """Test text length handling."""
        engine = GTTSEngine()

        assert engine.can_handle_text_length("Hello")

        long_text = "Hello " * 1000
        assert not engine.can_handle_text_length(long_text)

    @patch("ttskit.engines.gtts_engine.gTTS")
    def test_synth_to_mp3(self, mock_gtts):
        """Test MP3 synthesis."""
        mock_tts = Mock()
        mock_tts.save.return_value = None
        mock_gtts.return_value = mock_tts

        engine = GTTSEngine()
        result = engine.synth_to_mp3("Hello world", "en")

        assert isinstance(result, str)
        assert result.endswith(".mp3")
        mock_gtts.assert_called_once()

    @pytest.mark.asyncio
    async def test_synth_async(self):
        """Test async synthesis."""
        engine = GTTSEngine()

        with patch.object(engine, "synth_to_mp3") as mock_synth:
            mock_synth.return_value = "/tmp/test.mp3"

            with patch("builtins.open", mock_open(b"fake audio data")):
                result = await engine.synth_async("Hello world", "en")

                assert isinstance(result, bytes)
                assert len(result) > 0

    def test_synth_roadmap_signature(self):
        """Test roadmap synth method signature."""
        engine = GTTSEngine()

        with patch.object(engine, "synth_to_mp3") as mock_synth:
            mock_synth.return_value = "/tmp/test.mp3"

            with patch("builtins.open", mock_open(b"fake audio data")):
                result = engine.synth("Hello world", "en", "default", "1.0", "0.0")

                assert isinstance(result, bytes)

    def test_get_info(self):
        """Test engine info."""
        engine = GTTSEngine()
        info = engine.get_info()

        assert isinstance(info, dict)
        assert "name" in info
        assert "version" in info
        assert "description" in info

    def test_set_available(self):
        """Test availability setting."""
        engine = GTTSEngine()

        assert engine.is_available()

        engine.set_available(False)
        assert not engine.is_available()

        engine.set_available(True)
        assert engine.is_available()


def mock_open(data):
    """Mock open function for testing."""
    from unittest.mock import mock_open as _mock_open

    return _mock_open(read_data=data)
