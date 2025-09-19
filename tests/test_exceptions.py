"""Tests for Custom Exceptions."""

from ttskit.exceptions import (
    AllEnginesFailedError,
    AudioConversionError,
    AudioProcessingError,
    BotTokenError,
    CacheError,
    ConfigurationError,
    EngineNotAvailableError,
    EngineNotFoundError,
    FFmpegNotFoundError,
    LanguageNotSupportedError,
    NetworkError,
    RateLimitError,
    RateLimitExceededError,
    TextValidationError,
    TTSError,
    TTSKitAudioError,
    TTSKitEngineError,
    TTSKitError,
    TTSKitFileError,
    TTSKitInternalError,
    TTSKitNetworkError,
)


class TestTTSError:
    """Test cases for TTSError base class."""

    def test_tts_error_initialization_with_message(self):
        """Test TTSError initialization with message only."""
        error = TTSError("Test error message")

        assert str(error) == "Test error message"
        assert error.message == "Test error message"
        assert error.error_code is None

    def test_tts_error_initialization_with_message_and_code(self):
        """Test TTSError initialization with message and error code."""
        error = TTSError("Test error message", "TEST_ERROR")

        assert str(error) == "Test error message"
        assert error.message == "Test error message"
        assert error.error_code == "TEST_ERROR"

    def test_tts_error_inheritance(self):
        """Test that TTSError inherits from Exception."""
        assert issubclass(TTSError, Exception)

        error = TTSError("Test")
        assert isinstance(error, Exception)


class TestEngineNotFoundError:
    """Test cases for EngineNotFoundError."""

    def test_engine_not_found_error_initialization_with_language(self):
        """Test EngineNotFoundError initialization with language only."""
        error = EngineNotFoundError("fa")

        assert str(error) == "No TTS engine found for language: fa"
        assert error.message == "No TTS engine found for language: fa"
        assert error.error_code == "ENGINE_NOT_FOUND"
        assert error.language == "fa"
        assert error.available_engines == []

    def test_engine_not_found_error_initialization_with_engines(self):
        """Test EngineNotFoundError initialization with available engines."""
        error = EngineNotFoundError("fa", ["gtts", "edge"])

        assert (
            str(error)
            == "No TTS engine found for language: fa. Available engines: gtts, edge"
        )
        assert (
            error.message
            == "No TTS engine found for language: fa. Available engines: gtts, edge"
        )
        assert error.error_code == "ENGINE_NOT_FOUND"
        assert error.language == "fa"
        assert error.available_engines == ["gtts", "edge"]

    def test_engine_not_found_error_inheritance(self):
        """Test that EngineNotFoundError inherits from TTSError."""
        assert issubclass(EngineNotFoundError, TTSError)

        error = EngineNotFoundError("fa")
        assert isinstance(error, TTSError)


class TestAudioConversionError:
    """Test cases for AudioConversionError."""

    def test_audio_conversion_error_initialization_with_message(self):
        """Test AudioConversionError initialization with message only."""
        error = AudioConversionError("Conversion failed")

        assert str(error) == "Conversion failed"
        assert error.message == "Conversion failed"
        assert error.error_code == "AUDIO_CONVERSION_FAILED"
        assert error.source_format is None
        assert error.target_format is None

    def test_audio_conversion_error_initialization_with_formats(self):
        """Test AudioConversionError initialization with source and target formats."""
        error = AudioConversionError("Conversion failed", "wav", "mp3")

        assert str(error) == "Conversion failed"
        assert error.message == "Conversion failed"
        assert error.error_code == "AUDIO_CONVERSION_FAILED"
        assert error.source_format == "wav"
        assert error.target_format == "mp3"

    def test_audio_conversion_error_inheritance(self):
        """Test that AudioConversionError inherits from TTSError."""
        assert issubclass(AudioConversionError, TTSError)

        error = AudioConversionError("Test")
        assert isinstance(error, TTSError)


class TestTextValidationError:
    """Test cases for TextValidationError."""

    def test_text_validation_error_initialization_with_message(self):
        """Test TextValidationError initialization with message only."""
        error = TextValidationError("Text validation failed")

        assert str(error) == "Text validation failed"
        assert error.message == "Text validation failed"
        assert error.error_code == "TEXT_VALIDATION_FAILED"
        assert error.text is None
        assert error.max_length is None

    def test_text_validation_error_initialization_with_text_and_length(self):
        """Test TextValidationError initialization with text and max length."""
        error = TextValidationError("Text too long", "Very long text", 100)

        assert str(error) == "Text too long"
        assert error.message == "Text too long"
        assert error.error_code == "TEXT_VALIDATION_FAILED"
        assert error.text == "Very long text"
        assert error.max_length == 100

    def test_text_validation_error_inheritance(self):
        """Test that TextValidationError inherits from TTSError."""
        assert issubclass(TextValidationError, TTSError)

        error = TextValidationError("Test")
        assert isinstance(error, TTSError)


class TestLanguageNotSupportedError:
    """Test cases for LanguageNotSupportedError."""

    def test_language_not_supported_error_initialization_with_language_and_engine(self):
        """Test LanguageNotSupportedError initialization with language and engine."""
        error = LanguageNotSupportedError("fa", "gtts")

        assert str(error) == "Language 'fa' is not supported by engine 'gtts'"
        assert error.message == "Language 'fa' is not supported by engine 'gtts'"
        assert error.error_code == "LANGUAGE_NOT_SUPPORTED"
        assert error.language == "fa"
        assert error.engine == "gtts"
        assert error.supported_languages == []

    def test_language_not_supported_error_initialization_with_supported_languages(self):
        """Test LanguageNotSupportedError initialization with supported languages."""
        error = LanguageNotSupportedError("fa", "gtts", ["en", "es"])

        assert (
            str(error)
            == "Language 'fa' is not supported by engine 'gtts'. Supported languages: en, es"
        )
        assert (
            error.message
            == "Language 'fa' is not supported by engine 'gtts'. Supported languages: en, es"
        )
        assert error.error_code == "LANGUAGE_NOT_SUPPORTED"
        assert error.language == "fa"
        assert error.engine == "gtts"
        assert error.supported_languages == ["en", "es"]

    def test_language_not_supported_error_inheritance(self):
        """Test that LanguageNotSupportedError inherits from TTSError."""
        assert issubclass(LanguageNotSupportedError, TTSError)

        error = LanguageNotSupportedError("fa", "gtts")
        assert isinstance(error, TTSError)


class TestConfigurationError:
    """Test cases for ConfigurationError."""

    def test_configuration_error_initialization_with_message(self):
        """Test ConfigurationError initialization with message only."""
        error = ConfigurationError("Configuration error")

        assert str(error) == "Configuration error"
        assert error.message == "Configuration error"
        assert error.error_code == "CONFIGURATION_ERROR"
        assert error.setting_name is None

    def test_configuration_error_initialization_with_setting_name(self):
        """Test ConfigurationError initialization with setting name."""
        error = ConfigurationError("Invalid setting", "BOT_TOKEN")

        assert str(error) == "Invalid setting"
        assert error.message == "Invalid setting"
        assert error.error_code == "CONFIGURATION_ERROR"
        assert error.setting_name == "BOT_TOKEN"

    def test_configuration_error_inheritance(self):
        """Test that ConfigurationError inherits from TTSError."""
        assert issubclass(ConfigurationError, TTSError)

        error = ConfigurationError("Test")
        assert isinstance(error, TTSError)


class TestRateLimitError:
    """Test cases for RateLimitError."""

    def test_rate_limit_error_initialization(self):
        """Test RateLimitError initialization."""
        error = RateLimitError("Rate limit exceeded")

        assert str(error) == "Rate limit exceeded"
        assert error.message == "Rate limit exceeded"
        assert error.error_code == "RATE_LIMIT_EXCEEDED"

    def test_rate_limit_error_inheritance(self):
        """Test that RateLimitError inherits from TTSError."""
        assert issubclass(RateLimitError, TTSError)

        error = RateLimitError("Test")
        assert isinstance(error, TTSError)


class TestCacheError:
    """Test cases for CacheError."""

    def test_cache_error_initialization_with_message(self):
        """Test CacheError initialization with message only."""
        error = CacheError("Cache operation failed")

        assert str(error) == "Cache operation failed"
        assert error.message == "Cache operation failed"
        assert error.error_code == "CACHE_ERROR"
        assert error.operation is None

    def test_cache_error_initialization_with_operation(self):
        """Test CacheError initialization with operation."""
        error = CacheError("Cache operation failed", "get")

        assert str(error) == "Cache operation failed"
        assert error.message == "Cache operation failed"
        assert error.error_code == "CACHE_ERROR"
        assert error.operation == "get"

    def test_cache_error_inheritance(self):
        """Test that CacheError inherits from TTSError."""
        assert issubclass(CacheError, TTSError)

        error = CacheError("Test")
        assert isinstance(error, TTSError)


class TestFFmpegNotFoundError:
    """Test cases for FFmpegNotFoundError."""

    def test_ffmpeg_not_found_error_initialization_with_default_message(self):
        """Test FFmpegNotFoundError initialization with default message."""
        error = FFmpegNotFoundError()

        assert str(error) == "FFmpeg not found or not working properly"
        assert error.message == "FFmpeg not found or not working properly"
        assert error.error_code == "FFMPEG_NOT_FOUND"

    def test_ffmpeg_not_found_error_initialization_with_custom_message(self):
        """Test FFmpegNotFoundError initialization with custom message."""
        error = FFmpegNotFoundError("Custom FFmpeg error")

        assert str(error) == "Custom FFmpeg error"
        assert error.message == "Custom FFmpeg error"
        assert error.error_code == "FFMPEG_NOT_FOUND"

    def test_ffmpeg_not_found_error_inheritance(self):
        """Test that FFmpegNotFoundError inherits from TTSError."""
        assert issubclass(FFmpegNotFoundError, TTSError)

        error = FFmpegNotFoundError()
        assert isinstance(error, TTSError)


class TestNetworkError:
    """Test cases for NetworkError."""

    def test_network_error_initialization_with_message(self):
        """Test NetworkError initialization with message only."""
        error = NetworkError("Network connection failed")

        assert str(error) == "Network connection failed"
        assert error.message == "Network connection failed"
        assert error.error_code == "NETWORK_ERROR"
        assert error.url is None

    def test_network_error_initialization_with_url(self):
        """Test NetworkError initialization with URL."""
        error = NetworkError("Network connection failed", "https://api.example.com")

        assert str(error) == "Network connection failed"
        assert error.message == "Network connection failed"
        assert error.error_code == "NETWORK_ERROR"
        assert error.url == "https://api.example.com"

    def test_network_error_inheritance(self):
        """Test that NetworkError inherits from TTSError."""
        assert issubclass(NetworkError, TTSError)

        error = NetworkError("Test")
        assert isinstance(error, TTSError)


class TestBotTokenError:
    """Test cases for BotTokenError."""

    def test_bot_token_error_initialization_with_default_message(self):
        """Test BotTokenError initialization with default message."""
        error = BotTokenError()

        assert str(error) == "Invalid or missing bot token"
        assert error.message == "Invalid or missing bot token"
        assert error.error_code == "BOT_TOKEN_ERROR"

    def test_bot_token_error_initialization_with_custom_message(self):
        """Test BotTokenError initialization with custom message."""
        error = BotTokenError("Custom bot token error")

        assert str(error) == "Custom bot token error"
        assert error.message == "Custom bot token error"
        assert error.error_code == "BOT_TOKEN_ERROR"

    def test_bot_token_error_inheritance(self):
        """Test that BotTokenError inherits from TTSError."""
        assert issubclass(BotTokenError, TTSError)

        error = BotTokenError()
        assert isinstance(error, TTSError)


class TestAllEnginesFailedError:
    """Test cases for AllEnginesFailedError."""

    def test_all_engines_failed_error_initialization_with_default_message(self):
        """Test AllEnginesFailedError initialization with default message."""
        error = AllEnginesFailedError()

        assert str(error) == "All TTS engines failed"
        assert error.message == "All TTS engines failed"
        assert error.error_code == "ALL_ENGINES_FAILED"

    def test_all_engines_failed_error_initialization_with_custom_message(self):
        """Test AllEnginesFailedError initialization with custom message."""
        error = AllEnginesFailedError("Custom engines failed message")

        assert str(error) == "Custom engines failed message"
        assert error.message == "Custom engines failed message"
        assert error.error_code == "ALL_ENGINES_FAILED"

    def test_all_engines_failed_error_inheritance(self):
        """Test that AllEnginesFailedError inherits from TTSError."""
        assert issubclass(AllEnginesFailedError, TTSError)

        error = AllEnginesFailedError()
        assert isinstance(error, TTSError)


class TestEngineNotAvailableError:
    """Test cases for EngineNotAvailableError."""

    def test_engine_not_available_error_initialization_with_engine_name(self):
        """Test EngineNotAvailableError initialization with engine name only."""
        error = EngineNotAvailableError("gtts")

        assert str(error) == "Engine 'gtts' is not available"
        assert error.message == "Engine 'gtts' is not available"
        assert error.error_code == "ENGINE_NOT_AVAILABLE"
        assert error.engine_name == "gtts"

    def test_engine_not_available_error_initialization_with_custom_message(self):
        """Test EngineNotAvailableError initialization with custom message."""
        error = EngineNotAvailableError("gtts", "Custom engine error")

        assert str(error) == "Custom engine error"
        assert error.message == "Custom engine error"
        assert error.error_code == "ENGINE_NOT_AVAILABLE"
        assert error.engine_name == "gtts"

    def test_engine_not_available_error_inheritance(self):
        """Test that EngineNotAvailableError inherits from TTSError."""
        assert issubclass(EngineNotAvailableError, TTSError)

        error = EngineNotAvailableError("gtts")
        assert isinstance(error, TTSError)


class TestAudioProcessingError:
    """Test cases for AudioProcessingError."""

    def test_audio_processing_error_initialization_with_message(self):
        """Test AudioProcessingError initialization with message only."""
        error = AudioProcessingError("Audio processing failed")

        assert str(error) == "Audio processing failed"
        assert error.message == "Audio processing failed"
        assert error.error_code == "AUDIO_PROCESSING_ERROR"
        assert error.operation is None

    def test_audio_processing_error_initialization_with_operation(self):
        """Test AudioProcessingError initialization with operation."""
        error = AudioProcessingError("Audio processing failed", "normalize")

        assert str(error) == "Audio processing failed"
        assert error.message == "Audio processing failed"
        assert error.error_code == "AUDIO_PROCESSING_ERROR"
        assert error.operation == "normalize"

    def test_audio_processing_error_inheritance(self):
        """Test that AudioProcessingError inherits from TTSError."""
        assert issubclass(AudioProcessingError, TTSError)

        error = AudioProcessingError("Test")
        assert isinstance(error, TTSError)


class TestTTSKitAudioError:
    """Test cases for TTSKitAudioError."""

    def test_ttskit_audio_error_initialization_with_message(self):
        """Test TTSKitAudioError initialization with message only."""
        error = TTSKitAudioError("TTSKit audio error")

        assert str(error) == "TTSKit audio error"
        assert error.message == "TTSKit audio error"
        assert error.error_code == "TTSKIT_AUDIO_ERROR"
        assert error.operation is None

    def test_ttskit_audio_error_initialization_with_operation(self):
        """Test TTSKitAudioError initialization with operation."""
        error = TTSKitAudioError("TTSKit audio error", "convert")

        assert str(error) == "TTSKit audio error"
        assert error.message == "TTSKit audio error"
        assert error.error_code == "TTSKIT_AUDIO_ERROR"
        assert error.operation == "convert"

    def test_ttskit_audio_error_inheritance(self):
        """Test that TTSKitAudioError inherits from TTSError."""
        assert issubclass(TTSKitAudioError, TTSError)

        error = TTSKitAudioError("Test")
        assert isinstance(error, TTSError)


class TestTTSKitNetworkError:
    """Test cases for TTSKitNetworkError."""

    def test_ttskit_network_error_initialization_with_message(self):
        """Test TTSKitNetworkError initialization with message only."""
        error = TTSKitNetworkError("TTSKit network error")

        assert str(error) == "TTSKit network error"
        assert error.message == "TTSKit network error"
        assert error.error_code == "TTSKIT_NETWORK_ERROR"
        assert error.url is None

    def test_ttskit_network_error_initialization_with_url(self):
        """Test TTSKitNetworkError initialization with URL."""
        error = TTSKitNetworkError("TTSKit network error", "https://api.ttskit.com")

        assert str(error) == "TTSKit network error"
        assert error.message == "TTSKit network error"
        assert error.error_code == "TTSKIT_NETWORK_ERROR"
        assert error.url == "https://api.ttskit.com"

    def test_ttskit_network_error_inheritance(self):
        """Test that TTSKitNetworkError inherits from TTSError."""
        assert issubclass(TTSKitNetworkError, TTSError)

        error = TTSKitNetworkError("Test")
        assert isinstance(error, TTSError)


class TestTTSKitEngineError:
    """Test cases for TTSKitEngineError."""

    def test_ttskit_engine_error_initialization_with_message(self):
        """Test TTSKitEngineError initialization with message only."""
        error = TTSKitEngineError("TTSKit engine error")

        assert str(error) == "TTSKit engine error"
        assert error.message == "TTSKit engine error"
        assert error.error_code == "TTSKIT_ENGINE_ERROR"
        assert error.engine is None

    def test_ttskit_engine_error_initialization_with_engine(self):
        """Test TTSKitEngineError initialization with engine."""
        error = TTSKitEngineError("TTSKit engine error", "gtts")

        assert str(error) == "TTSKit engine error"
        assert error.message == "TTSKit engine error"
        assert error.error_code == "TTSKIT_ENGINE_ERROR"
        assert error.engine == "gtts"

    def test_ttskit_engine_error_inheritance(self):
        """Test that TTSKitEngineError inherits from TTSError."""
        assert issubclass(TTSKitEngineError, TTSError)

        error = TTSKitEngineError("Test")
        assert isinstance(error, TTSError)


class TestTTSKitFileError:
    """Test cases for TTSKitFileError."""

    def test_ttskit_file_error_initialization_with_message(self):
        """Test TTSKitFileError initialization with message only."""
        error = TTSKitFileError("TTSKit file error")

        assert str(error) == "TTSKit file error"
        assert error.message == "TTSKit file error"
        assert error.error_code == "TTSKIT_FILE_ERROR"
        assert error.file_path is None

    def test_ttskit_file_error_initialization_with_file_path(self):
        """Test TTSKitFileError initialization with file path."""
        error = TTSKitFileError("TTSKit file error", "/path/to/file.mp3")

        assert str(error) == "TTSKit file error"
        assert error.message == "TTSKit file error"
        assert error.error_code == "TTSKIT_FILE_ERROR"
        assert error.file_path == "/path/to/file.mp3"

    def test_ttskit_file_error_inheritance(self):
        """Test that TTSKitFileError inherits from TTSError."""
        assert issubclass(TTSKitFileError, TTSError)

        error = TTSKitFileError("Test")
        assert isinstance(error, TTSError)


class TestTTSKitInternalError:
    """Test cases for TTSKitInternalError."""

    def test_ttskit_internal_error_initialization_with_message(self):
        """Test TTSKitInternalError initialization with message only."""
        error = TTSKitInternalError("TTSKit internal error")

        assert str(error) == "TTSKit internal error"
        assert error.message == "TTSKit internal error"
        assert error.error_code == "TTSKIT_INTERNAL_ERROR"
        assert error.component is None

    def test_ttskit_internal_error_initialization_with_component(self):
        """Test TTSKitInternalError initialization with component."""
        error = TTSKitInternalError("TTSKit internal error", "cache")

        assert str(error) == "TTSKit internal error"
        assert error.message == "TTSKit internal error"
        assert error.error_code == "TTSKIT_INTERNAL_ERROR"
        assert error.component == "cache"

    def test_ttskit_internal_error_inheritance(self):
        """Test that TTSKitInternalError inherits from TTSError."""
        assert issubclass(TTSKitInternalError, TTSError)

        error = TTSKitInternalError("Test")
        assert isinstance(error, TTSError)


class TestRateLimitExceededError:
    """Test cases for RateLimitExceededError."""

    def test_rate_limit_exceeded_error_initialization(self):
        """Test RateLimitExceededError initialization."""
        error = RateLimitExceededError("user123", 10, 60)

        assert str(error) == "Rate limit exceeded for user user123"
        assert error.message == "Rate limit exceeded for user user123"
        assert error.error_code == "RATE_LIMIT_EXCEEDED"
        assert error.user_id == "user123"
        assert error.max_requests == 10
        assert error.window_seconds == 60

    def test_rate_limit_exceeded_error_inheritance(self):
        """Test that RateLimitExceededError inherits from TTSError."""
        assert issubclass(RateLimitExceededError, TTSError)

        error = RateLimitExceededError("user123", 10, 60)
        assert isinstance(error, TTSError)


class TestTTSKitErrorAlias:
    """Test cases for TTSKitError alias."""

    def test_ttskit_error_is_alias_for_tts_error(self):
        """Test that TTSKitError is an alias for TTSError."""
        assert TTSKitError is TTSError

        error = TTSKitError("Test error")
        assert isinstance(error, TTSError)
        assert str(error) == "Test error"
