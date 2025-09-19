"""Tests for Base Engine Classes."""

import os
import tempfile

import pytest

from ttskit.engines.base import BaseEngine, EngineCapabilities, TTSEngine


class TestEngineCapabilities:
    """Test cases for EngineCapabilities dataclass."""

    def test_engine_capabilities_initialization(self):
        """Test EngineCapabilities initialization."""
        caps = EngineCapabilities(
            offline=True,
            ssml=True,
            rate_control=True,
            pitch_control=True,
            languages=["en", "fa"],
            voices=["voice1", "voice2"],
            max_text_length=5000,
        )

        assert caps.offline is True
        assert caps.ssml is True
        assert caps.rate_control is True
        assert caps.pitch_control is True
        assert caps.languages == ["en", "fa"]
        assert caps.voices == ["voice1", "voice2"]
        assert caps.max_text_length == 5000

    def test_engine_capabilities_backward_compat_properties(self):
        """Test backward compatibility properties."""
        caps = EngineCapabilities(
            offline=True,
            ssml=True,
            rate_control=True,
            pitch_control=True,
            languages=["en"],
            voices=["voice1"],
            max_text_length=1000,
        )

        assert caps.rate == caps.rate_control
        assert caps.pitch == caps.pitch_control

        caps2 = EngineCapabilities(
            offline=False,
            ssml=False,
            rate_control=False,
            pitch_control=False,
            languages=["en"],
            voices=["voice1"],
            max_text_length=1000,
        )

        assert caps2.rate is False
        assert caps2.pitch is False


class TestTTSEngine:
    """Test cases for TTSEngine abstract class."""

    def test_tts_engine_is_abstract(self):
        """Test that TTSEngine cannot be instantiated directly."""
        with pytest.raises(TypeError):
            TTSEngine()

    def test_tts_engine_initialization_with_default_lang(self):
        """Test TTSEngine initialization with default language."""

        class ConcreteEngine(TTSEngine):
            def synth_to_mp3(self, text: str, lang: str | None = None) -> str:
                return "test.mp3"

            async def synth_async(
                self,
                text: str,
                lang: str | None = None,
                voice: str | None = None,
                rate: float = 1.0,
                pitch: float = 0.0,
            ) -> bytes:
                return b"audio_data"

            def get_capabilities(self) -> EngineCapabilities:
                return EngineCapabilities(
                    offline=False,
                    ssml=False,
                    rate_control=False,
                    pitch_control=False,
                    languages=["en"],
                    voices=[],
                    max_text_length=1000,
                )

            def list_voices(self, lang: str | None = None) -> list[str]:
                return ["voice1"]

            def is_available(self) -> bool:
                return True

        engine = ConcreteEngine(default_lang="fa")
        assert engine.default_lang == "fa"

    def test_tts_engine_initialization_without_default_lang(self):
        """Test TTSEngine initialization without default language."""

        class ConcreteEngine(TTSEngine):
            def synth_to_mp3(self, text: str, lang: str | None = None) -> str:
                return "test.mp3"

            async def synth_async(
                self,
                text: str,
                lang: str | None = None,
                voice: str | None = None,
                rate: float = 1.0,
                pitch: float = 0.0,
            ) -> bytes:
                return b"audio_data"

            def get_capabilities(self) -> EngineCapabilities:
                return EngineCapabilities(
                    offline=False,
                    ssml=False,
                    rate_control=False,
                    pitch_control=False,
                    languages=["en"],
                    voices=[],
                    max_text_length=1000,
                )

            def list_voices(self, lang: str | None = None) -> list[str]:
                return ["voice1"]

            def is_available(self) -> bool:
                return True

        engine = ConcreteEngine()
        assert engine.default_lang == "en"

    def test_synth_method_rate_parsing(self):
        """Test synth method rate parsing."""

        class ConcreteEngine(TTSEngine):
            def synth_to_mp3(self, text: str, lang: str | None = None) -> str:
                return "test.mp3"

            async def synth_async(
                self,
                text: str,
                lang: str | None = None,
                voice: str | None = None,
                rate: float = 1.0,
                pitch: float = 0.0,
            ) -> bytes:
                return b"audio_data"

            def get_capabilities(self) -> EngineCapabilities:
                return EngineCapabilities(
                    offline=False,
                    ssml=False,
                    rate_control=False,
                    pitch_control=False,
                    languages=["en"],
                    voices=[],
                    max_text_length=1000,
                )

            def list_voices(self, lang: str | None = None) -> list[str]:
                return ["voice1"]

            def is_available(self) -> bool:
                return True

        engine = ConcreteEngine()

        result = engine.synth("Hello", "en", "voice1", "150%", "0")
        assert result == b"audio_data"

        result = engine.synth("Hello", "en", "voice1", "1.5", "0")
        assert result == b"audio_data"

        result = engine.synth("Hello", "en", "voice1", "invalid", "0")
        assert result == b"audio_data"

    def test_synth_method_pitch_parsing(self):
        """Test synth method pitch parsing."""

        class ConcreteEngine(TTSEngine):
            def synth_to_mp3(self, text: str, lang: str | None = None) -> str:
                return "test.mp3"

            async def synth_async(
                self,
                text: str,
                lang: str | None = None,
                voice: str | None = None,
                rate: float = 1.0,
                pitch: float = 0.0,
            ) -> bytes:
                return b"audio_data"

            def get_capabilities(self) -> EngineCapabilities:
                return EngineCapabilities(
                    offline=False,
                    ssml=False,
                    rate_control=False,
                    pitch_control=False,
                    languages=["en"],
                    voices=[],
                    max_text_length=1000,
                )

            def list_voices(self, lang: str | None = None) -> list[str]:
                return ["voice1"]

            def is_available(self) -> bool:
                return True

        engine = ConcreteEngine()

        result = engine.synth("Hello", "en", "voice1", "1.0", "2st")
        assert result == b"audio_data"

        result = engine.synth("Hello", "en", "voice1", "1.0", "2.0")
        assert result == b"audio_data"

        result = engine.synth("Hello", "en", "voice1", "1.0", "invalid")
        assert result == b"audio_data"

    def test_capabilities_method(self):
        """Test capabilities method."""

        class ConcreteEngine(TTSEngine):
            def synth_to_mp3(self, text: str, lang: str | None = None) -> str:
                return "test.mp3"

            async def synth_async(
                self,
                text: str,
                lang: str | None = None,
                voice: str | None = None,
                rate: float = 1.0,
                pitch: float = 0.0,
            ) -> bytes:
                return b"audio_data"

            def get_capabilities(self) -> EngineCapabilities:
                return EngineCapabilities(
                    offline=True,
                    ssml=True,
                    rate_control=True,
                    pitch_control=True,
                    languages=["en", "fa"],
                    voices=["voice1", "voice2"],
                    max_text_length=5000,
                )

            def list_voices(self, lang: str | None = None) -> list[str]:
                return ["voice1"]

            def is_available(self) -> bool:
                return True

        engine = ConcreteEngine()
        caps_dict = engine.capabilities()

        assert caps_dict["offline"] is True
        assert caps_dict["ssml"] is True
        assert caps_dict["rate"] is True
        assert caps_dict["pitch"] is True
        assert caps_dict["langs"] == ["en", "fa"]
        assert caps_dict["voices"] == ["voice1", "voice2"]
        assert caps_dict["max_text_length"] == 5000

    def test_get_supported_languages(self):
        """Test get_supported_languages method."""

        class ConcreteEngine(TTSEngine):
            def synth_to_mp3(self, text: str, lang: str | None = None) -> str:
                return "test.mp3"

            async def synth_async(
                self,
                text: str,
                lang: str | None = None,
                voice: str | None = None,
                rate: float = 1.0,
                pitch: float = 0.0,
            ) -> bytes:
                return b"audio_data"

            def get_capabilities(self) -> EngineCapabilities:
                return EngineCapabilities(
                    offline=False,
                    ssml=False,
                    rate_control=False,
                    pitch_control=False,
                    languages=["en", "fa", "ar"],
                    voices=[],
                    max_text_length=1000,
                )

            def list_voices(self, lang: str | None = None) -> list[str]:
                return ["voice1"]

            def is_available(self) -> bool:
                return True

        engine = ConcreteEngine()
        languages = engine.get_supported_languages()

        assert languages == ["en", "fa", "ar"]

    def test_supports_language(self):
        """Test supports_language method."""

        class ConcreteEngine(TTSEngine):
            def synth_to_mp3(self, text: str, lang: str | None = None) -> str:
                return "test.mp3"

            async def synth_async(
                self,
                text: str,
                lang: str | None = None,
                voice: str | None = None,
                rate: float = 1.0,
                pitch: float = 0.0,
            ) -> bytes:
                return b"audio_data"

            def get_capabilities(self) -> EngineCapabilities:
                return EngineCapabilities(
                    offline=False,
                    ssml=False,
                    rate_control=False,
                    pitch_control=False,
                    languages=["en", "fa"],
                    voices=[],
                    max_text_length=1000,
                )

            def list_voices(self, lang: str | None = None) -> list[str]:
                return ["voice1"]

            def is_available(self) -> bool:
                return True

        engine = ConcreteEngine()

        assert engine.supports_language("en") is True
        assert engine.supports_language("fa") is True
        assert engine.supports_language("ar") is False

    def test_supports_voice(self):
        """Test supports_voice method."""

        class ConcreteEngine(TTSEngine):
            def synth_to_mp3(self, text: str, lang: str | None = None) -> str:
                return "test.mp3"

            async def synth_async(
                self,
                text: str,
                lang: str | None = None,
                voice: str | None = None,
                rate: float = 1.0,
                pitch: float = 0.0,
            ) -> bytes:
                return b"audio_data"

            def get_capabilities(self) -> EngineCapabilities:
                return EngineCapabilities(
                    offline=False,
                    ssml=False,
                    rate_control=False,
                    pitch_control=False,
                    languages=["en"],
                    voices=["voice1", "voice2"],
                    max_text_length=1000,
                )

            def list_voices(self, lang: str | None = None) -> list[str]:
                return ["voice1"]

            def is_available(self) -> bool:
                return True

        engine = ConcreteEngine()

        assert engine.supports_voice("voice1") is True
        assert engine.supports_voice("voice2") is True
        assert engine.supports_voice("voice3") is False

    def test_can_handle_text_length(self):
        """Test can_handle_text_length method."""

        class ConcreteEngine(TTSEngine):
            def synth_to_mp3(self, text: str, lang: str | None = None) -> str:
                return "test.mp3"

            async def synth_async(
                self,
                text: str,
                lang: str | None = None,
                voice: str | None = None,
                rate: float = 1.0,
                pitch: float = 0.0,
            ) -> bytes:
                return b"audio_data"

            def get_capabilities(self) -> EngineCapabilities:
                return EngineCapabilities(
                    offline=False,
                    ssml=False,
                    rate_control=False,
                    pitch_control=False,
                    languages=["en"],
                    voices=[],
                    max_text_length=100,
                )

            def list_voices(self, lang: str | None = None) -> list[str]:
                return ["voice1"]

            def is_available(self) -> bool:
                return True

        engine = ConcreteEngine()

        assert engine.can_handle_text_length("Hello") is True

        assert engine.can_handle_text_length("x" * 100) is True

        assert engine.can_handle_text_length("x" * 101) is False

    def test_validate_input_empty_text(self):
        """Test validate_input with empty text."""

        class ConcreteEngine(TTSEngine):
            def synth_to_mp3(self, text: str, lang: str | None = None) -> str:
                return "test.mp3"

            async def synth_async(
                self,
                text: str,
                lang: str | None = None,
                voice: str | None = None,
                rate: float = 1.0,
                pitch: float = 0.0,
            ) -> bytes:
                return b"audio_data"

            def get_capabilities(self) -> EngineCapabilities:
                return EngineCapabilities(
                    offline=False,
                    ssml=False,
                    rate_control=False,
                    pitch_control=False,
                    languages=["en"],
                    voices=[],
                    max_text_length=100,
                )

            def list_voices(self, lang: str | None = None) -> list[str]:
                return ["voice1"]

            def is_available(self) -> bool:
                return True

        engine = ConcreteEngine()

        with pytest.raises(ValueError, match="Text cannot be empty"):
            engine.validate_input("")

        with pytest.raises(ValueError, match="Text cannot be empty"):
            engine.validate_input("   ")

    def test_validate_input_text_too_long(self):
        """Test validate_input with text too long."""

        class ConcreteEngine(TTSEngine):
            def synth_to_mp3(self, text: str, lang: str | None = None) -> str:
                return "test.mp3"

            async def synth_async(
                self,
                text: str,
                lang: str | None = None,
                voice: str | None = None,
                rate: float = 1.0,
                pitch: float = 0.0,
            ) -> bytes:
                return b"audio_data"

            def get_capabilities(self) -> EngineCapabilities:
                return EngineCapabilities(
                    offline=False,
                    ssml=False,
                    rate_control=False,
                    pitch_control=False,
                    languages=["en"],
                    voices=[],
                    max_text_length=10,
                )

            def list_voices(self, lang: str | None = None) -> list[str]:
                return ["voice1"]

            def is_available(self) -> bool:
                return True

        engine = ConcreteEngine()

        with pytest.raises(ValueError, match="Text too long"):
            engine.validate_input("This text is too long")

    def test_validate_input_invalid_language(self):
        """Test validate_input with invalid language."""

        class ConcreteEngine(TTSEngine):
            def synth_to_mp3(self, text: str, lang: str | None = None) -> str:
                return "test.mp3"

            async def synth_async(
                self,
                text: str,
                lang: str | None = None,
                voice: str | None = None,
                rate: float = 1.0,
                pitch: float = 0.0,
            ) -> bytes:
                return b"audio_data"

            def get_capabilities(self) -> EngineCapabilities:
                return EngineCapabilities(
                    offline=False,
                    ssml=False,
                    rate_control=False,
                    pitch_control=False,
                    languages=["en"],
                    voices=[],
                    max_text_length=100,
                )

            def list_voices(self, lang: str | None = None) -> list[str]:
                return ["voice1"]

            def is_available(self) -> bool:
                return True

        engine = ConcreteEngine()

        result = engine.validate_input("Hello", lang="fa")
        assert result == "invalid_language"

    def test_validate_input_invalid_voice(self):
        """Test validate_input with invalid voice."""

        class ConcreteEngine(TTSEngine):
            def synth_to_mp3(self, text: str, lang: str | None = None) -> str:
                return "test.mp3"

            async def synth_async(
                self,
                text: str,
                lang: str | None = None,
                voice: str | None = None,
                rate: float = 1.0,
                pitch: float = 0.0,
            ) -> bytes:
                return b"audio_data"

            def get_capabilities(self) -> EngineCapabilities:
                return EngineCapabilities(
                    offline=False,
                    ssml=False,
                    rate_control=False,
                    pitch_control=False,
                    languages=["en"],
                    voices=["voice1"],
                    max_text_length=100,
                )

            def list_voices(self, lang: str | None = None) -> list[str]:
                return ["voice1"]

            def is_available(self) -> bool:
                return True

        engine = ConcreteEngine()

        result = engine.validate_input("Hello", voice="invalid_voice")
        assert result == "invalid_voice"

    def test_validate_input_valid(self):
        """Test validate_input with valid input."""

        class ConcreteEngine(TTSEngine):
            def synth_to_mp3(self, text: str, lang: str | None = None) -> str:
                return "test.mp3"

            async def synth_async(
                self,
                text: str,
                lang: str | None = None,
                voice: str | None = None,
                rate: float = 1.0,
                pitch: float = 0.0,
            ) -> bytes:
                return b"audio_data"

            def get_capabilities(self) -> EngineCapabilities:
                return EngineCapabilities(
                    offline=False,
                    ssml=False,
                    rate_control=False,
                    pitch_control=False,
                    languages=["en"],
                    voices=["voice1"],
                    max_text_length=100,
                )

            def list_voices(self, lang: str | None = None) -> list[str]:
                return ["voice1"]

            def is_available(self) -> bool:
                return True

        engine = ConcreteEngine()

        result = engine.validate_input("Hello", lang="en", voice="voice1")
        assert result is None

    @pytest.mark.asyncio
    async def test_synth_to_file_async(self):
        """Test synth_to_file_async method."""

        class ConcreteEngine(TTSEngine):
            def synth_to_mp3(self, text: str, lang: str | None = None) -> str:
                return "test.mp3"

            async def synth_async(
                self,
                text: str,
                lang: str | None = None,
                voice: str | None = None,
                rate: float = 1.0,
                pitch: float = 0.0,
            ) -> bytes:
                return b"test_audio_data"

            def get_capabilities(self) -> EngineCapabilities:
                return EngineCapabilities(
                    offline=False,
                    ssml=False,
                    rate_control=False,
                    pitch_control=False,
                    languages=["en"],
                    voices=[],
                    max_text_length=100,
                )

            def list_voices(self, lang: str | None = None) -> list[str]:
                return ["voice1"]

            def is_available(self) -> bool:
                return True

        engine = ConcreteEngine()

        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_path = tmp_file.name

        try:
            result_path = await engine.synth_to_file_async("Hello", tmp_path)

            assert result_path == tmp_path
            assert os.path.exists(tmp_path)

            with open(tmp_path, "rb") as f:
                content = f.read()
                assert content == b"test_audio_data"

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_synth_to_file_sync(self):
        """Test synth_to_file method."""

        class ConcreteEngine(TTSEngine):
            def synth_to_mp3(self, text: str, lang: str | None = None) -> str:
                return "test.mp3"

            async def synth_async(
                self,
                text: str,
                lang: str | None = None,
                voice: str | None = None,
                rate: float = 1.0,
                pitch: float = 0.0,
            ) -> bytes:
                return b"test_audio_data"

            def get_capabilities(self) -> EngineCapabilities:
                return EngineCapabilities(
                    offline=False,
                    ssml=False,
                    rate_control=False,
                    pitch_control=False,
                    languages=["en"],
                    voices=[],
                    max_text_length=100,
                )

            def list_voices(self, lang: str | None = None) -> list[str]:
                return ["voice1"]

            def is_available(self) -> bool:
                return True

        engine = ConcreteEngine()

        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_path = tmp_file.name

        try:
            result_path = engine.synth_to_file("Hello", tmp_path)

            assert result_path == tmp_path
            assert os.path.exists(tmp_path)

            with open(tmp_path, "rb") as f:
                content = f.read()
                assert content == b"test_audio_data"

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_get_info(self):
        """Test get_info method."""

        class ConcreteEngine(TTSEngine):
            def synth_to_mp3(self, text: str, lang: str | None = None) -> str:
                return "test.mp3"

            async def synth_async(
                self,
                text: str,
                lang: str | None = None,
                voice: str | None = None,
                rate: float = 1.0,
                pitch: float = 0.0,
            ) -> bytes:
                return b"audio_data"

            def get_capabilities(self) -> EngineCapabilities:
                return EngineCapabilities(
                    offline=True,
                    ssml=True,
                    rate_control=True,
                    pitch_control=True,
                    languages=["en", "fa"],
                    voices=["voice1", "voice2"],
                    max_text_length=5000,
                )

            def list_voices(self, lang: str | None = None) -> list[str]:
                return ["voice1"]

            def is_available(self) -> bool:
                return True

        engine = ConcreteEngine(default_lang="fa")
        info = engine.get_info()

        assert info["name"] == "ConcreteEngine"
        assert info["version"] == "1.0.0"
        assert info["default_lang"] == "fa"
        assert info["available"] is True
        assert info["description"] == ""
        assert info["capabilities"]["offline"] is True
        assert info["capabilities"]["ssml"] is True
        assert info["capabilities"]["rate_control"] is True
        assert info["capabilities"]["pitch_control"] is True
        assert info["capabilities"]["max_text_length"] == 5000
        assert info["languages"] == ["en", "fa"]
        assert info["voices_count"] == 2
        assert info["supported_languages"] == ["en", "fa"]


class TestBaseEngine:
    """Test cases for BaseEngine class."""

    def _create_concrete_engine(self, default_lang: str | None = None):
        """Create a concrete implementation of BaseEngine for testing."""

        class ConcreteEngine(BaseEngine):
            def __init__(self, default_lang: str | None = None):
                super().__init__(default_lang)

            def synth_to_mp3(self, text: str, lang: str | None = None) -> str:
                return "test.mp3"

            async def synth_async(
                self,
                text: str,
                lang: str | None = None,
                voice: str | None = None,
                rate: float = 1.0,
                pitch: float = 0.0,
            ) -> bytes:
                return b"audio_data"

            def list_voices(self, lang: str | None = None) -> list[str]:
                return ["voice1"]

        return ConcreteEngine(default_lang)

    def test_base_engine_initialization(self):
        """Test BaseEngine initialization."""
        engine = self._create_concrete_engine()

        assert engine.default_lang == "en"
        assert isinstance(engine._capabilities, EngineCapabilities)
        assert engine._available is True
        assert engine._connection_pool is None

    def test_base_engine_initialization_with_default_lang(self):
        """Test BaseEngine initialization with default language."""
        engine = self._create_concrete_engine(default_lang="fa")

        assert engine.default_lang == "fa"

    def test_get_default_capabilities(self):
        """Test _get_default_capabilities method."""
        engine = self._create_concrete_engine()
        caps = engine._get_default_capabilities()

        assert caps.offline is False
        assert caps.ssml is False
        assert caps.rate_control is False
        assert caps.pitch_control is False
        assert caps.languages == ["en"]
        assert caps.voices == []
        assert caps.max_text_length == 1000

    def test_get_capabilities(self):
        """Test get_capabilities method."""
        engine = self._create_concrete_engine()
        caps = engine.get_capabilities()

        assert isinstance(caps, EngineCapabilities)
        assert caps.offline is False
        assert caps.ssml is False
        assert caps.rate_control is False
        assert caps.pitch_control is False
        assert caps.languages == ["en"]
        assert caps.voices == []
        assert caps.max_text_length == 1000

    def test_is_available(self):
        """Test is_available method."""
        engine = self._create_concrete_engine()

        assert engine.is_available() is True

        engine._available = False
        assert engine.is_available() is False

    def test_cleanup_temp_files(self):
        """Test _cleanup_temp_files method."""
        engine = self._create_concrete_engine()

        engine._cleanup_temp_files("/nonexistent/file.mp3")

        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_path = tmp_file.name

        try:
            assert os.path.exists(tmp_path)

            engine._cleanup_temp_files(tmp_path)

            assert not os.path.exists(tmp_path)

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_validate_text_input_empty(self):
        """Test _validate_text_input with empty text."""
        engine = self._create_concrete_engine()

        with pytest.raises(ValueError, match="Text cannot be empty"):
            engine._validate_text_input("")

        with pytest.raises(ValueError, match="Text cannot be empty"):
            engine._validate_text_input("   ")

    def test_validate_text_input_too_long(self):
        """Test _validate_text_input with text too long."""
        engine = self._create_concrete_engine()

        long_text = "x" * 1001

        with pytest.raises(ValueError, match="Text too long"):
            engine._validate_text_input(long_text)

    def test_validate_text_input_valid(self):
        """Test _validate_text_input with valid text."""
        engine = self._create_concrete_engine()

        engine._validate_text_input("Hello World")

    def test_validate_language(self):
        """Test _validate_language method."""
        engine = self._create_concrete_engine()

        assert engine._validate_language("en") is True

        assert engine._validate_language("fa") is False

    def test_validate_voice(self):
        """Test _validate_voice method."""
        engine = self._create_concrete_engine()

        assert engine._validate_voice("voice1") is False

        engine._capabilities = EngineCapabilities(
            offline=False,
            ssml=False,
            rate_control=False,
            pitch_control=False,
            languages=["en"],
            voices=["voice1"],
            max_text_length=1000,
        )

        assert engine._validate_voice("voice1") is True
        assert engine._validate_voice("voice2") is False

    @pytest.mark.asyncio
    async def test_get_connection_pool(self):
        """Test _get_connection_pool method."""
        engine = self._create_concrete_engine()

        pool1 = await engine._get_connection_pool()
        assert pool1 is not None

        pool2 = await engine._get_connection_pool()
        assert pool2 is pool1

    def test_base_engine_inheritance(self):
        """Test that BaseEngine properly inherits from TTSEngine."""
        assert issubclass(BaseEngine, TTSEngine)

        engine = self._create_concrete_engine()
        assert isinstance(engine, TTSEngine)
        assert isinstance(engine, BaseEngine)

    def test_base_engine_abstract_methods_still_raise_not_implemented(self):
        """Test that BaseEngine still raises NotImplementedError for abstract methods."""
        with pytest.raises(TypeError):
            BaseEngine()

    @pytest.mark.asyncio
    async def test_base_engine_async_methods_still_raise_not_implemented(self):
        """Test that BaseEngine async methods still raise NotImplementedError."""
        with pytest.raises(TypeError):
            BaseEngine()
