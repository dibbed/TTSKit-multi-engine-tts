"""Tests for validation utilities."""

from ttskit.utils.validate import (
    validate_engine,
    validate_engine_name,
    validate_language,
    validate_language_code,
    validate_pitch,
    validate_rate,
    validate_user_input,
    validate_voice,
    validate_voice_name,
)


class TestLanguageValidation:
    """Test language validation."""

    def test_validate_language_valid(self):
        """Test valid language codes."""
        assert validate_language("en") is True
        assert validate_language("fa") is True
        assert validate_language("ar") is True

    def test_validate_language_invalid(self):
        """Test invalid language codes."""
        assert validate_language("invalid") is False
        assert validate_language("") is False
        assert validate_language("xyz") is False

    def test_validate_language_code_alias(self):
        """Test validate_language_code alias."""
        assert validate_language_code("en") is True
        assert validate_language_code("invalid") is False


class TestEngineValidation:
    """Test engine validation."""

    def test_validate_engine_valid(self):
        """Test valid engine names."""
        assert validate_engine("gtts") is True
        assert validate_engine("edge") is True
        assert validate_engine("piper") is True

    def test_validate_engine_invalid(self):
        """Test invalid engine names."""
        assert validate_engine("invalid") is False
        assert validate_engine("") is False
        assert validate_engine("gTTS") is False

    def test_validate_engine_name_alias(self):
        """Test validate_engine_name alias."""
        assert validate_engine_name("gtts") is True
        assert validate_engine_name("invalid") is False


class TestVoiceValidation:
    """Test voice validation."""

    def test_validate_voice_edge(self):
        """Test Edge-TTS voice validation."""
        assert validate_voice("en-US-AriaNeural", "edge") is True
        assert validate_voice("fa-IR-DilaraNeural", "edge") is True
        assert validate_voice("invalid", "edge") is False

    def test_validate_voice_gtts(self):
        """Test gTTS voice validation."""
        assert validate_voice("en", "gtts") is True
        assert validate_voice("fa", "gtts") is True
        assert validate_voice("invalid", "gtts") is False

    def test_validate_voice_piper(self):
        """Test Piper voice validation."""
        assert validate_voice("en_us", "piper") is True
        assert validate_voice("fa_ir", "piper") is True
        assert validate_voice("invalid", "piper") is True

    def test_validate_voice_name_alias(self):
        """Test validate_voice_name alias."""
        assert validate_voice_name("en-US-AriaNeural", "edge") is True
        assert validate_voice_name("invalid", "edge") is False


class TestRateValidation:
    """Test rate validation."""

    def test_validate_rate_valid(self):
        """Test valid rate values."""
        assert validate_rate(0.5) is True
        assert validate_rate(1.0) is True
        assert validate_rate(2.0) is True
        assert validate_rate(3.0) is True

    def test_validate_rate_invalid(self):
        """Test invalid rate values."""
        assert validate_rate(0.0) is False
        assert validate_rate(3.1) is False
        assert validate_rate(-1.0) is False


class TestPitchValidation:
    """Test pitch validation."""

    def test_validate_pitch_valid(self):
        """Test valid pitch values."""
        assert validate_pitch(-12.0) is True
        assert validate_pitch(0.0) is True
        assert validate_pitch(12.0) is True

    def test_validate_pitch_invalid(self):
        """Test invalid pitch values."""
        assert validate_pitch(-13.0) is False
        assert validate_pitch(13.0) is False


class TestUserInputValidation:
    """Test user input validation."""

    def test_validate_user_input_valid(self):
        """Test valid user input."""
        assert validate_user_input("Hello world", "en") is True
        assert validate_user_input("سلام دنیا", "fa") is True
        assert validate_user_input("مرحبا بالعالم", "ar") is True

    def test_validate_user_input_with_engine(self):
        """Test user input with engine."""
        assert validate_user_input("Hello world", "en", "gtts") is True
        assert validate_user_input("سلام دنیا", "fa", "edge") is True

    def test_validate_user_input_invalid_text(self):
        """Test invalid text input."""
        assert validate_user_input("", "en") is False
        assert validate_user_input("   ", "en") is False

    def test_validate_user_input_invalid_language(self):
        """Test invalid language input."""
        assert validate_user_input("Hello world", "invalid") is False

    def test_validate_user_input_invalid_engine(self):
        """Test invalid engine input."""
        assert validate_user_input("Hello world", "en", "invalid") is False


class TestValidationIntegration:
    """Integration tests for validation utilities."""

    def test_complete_validation_pipeline(self):
        """Test complete validation pipeline."""
        text = "Hello world"
        lang = "en"
        engine = "gtts"
        voice = "en"
        rate = 1.0
        pitch = 0.0

        assert validate_language(lang) is True
        assert validate_engine(engine) is True
        assert validate_voice(voice, engine) is True
        assert validate_rate(rate) is True
        assert validate_pitch(pitch) is True
        assert validate_user_input(text, lang, engine) is True

    def test_edge_cases(self):
        """Test edge cases and error handling."""
        edge_cases = [
            ("", "en", "gtts"),
            ("   ", "en", "gtts"),
            ("Hello world", "", "gtts"),
            ("Hello world", "en", ""),
            ("Hello world", "invalid", "gtts"),
            ("Hello world", "en", "invalid"),
        ]

        for text, lang, engine in edge_cases:
            result = validate_user_input(text, lang, engine)
            assert isinstance(result, bool)

    def test_multilingual_validation(self):
        """Test validation with multiple languages."""
        test_cases = [
            ("Hello world", "en", "gtts", "en"),
            ("سلام دنیا", "fa", "edge", "fa-IR-DilaraNeural"),
            ("مرحبا بالعالم", "ar", "edge", "ar-SA-HamedNeural"),
        ]

        for text, lang, engine, voice in test_cases:
            assert validate_language(lang) is True
            assert validate_engine(engine) is True
            assert validate_voice(voice, engine) is True
            assert validate_user_input(text, lang, engine) is True
