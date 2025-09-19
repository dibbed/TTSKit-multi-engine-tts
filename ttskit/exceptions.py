"""
Custom exceptions for TTSKit.

This module provides structured exception classes for handling errors in TTSKit,
such as engine failures, validation issues, and configuration problems.
"""


class TTSError(Exception):
    """Base exception for all TTSKit errors.

    Serves as the parent for specific exceptions, adding optional error codes
    for consistent error handling across the application.

    Args:
        message: The error description string.
        error_code: Optional code for categorizing the error (e.g., 'ENGINE_NOT_FOUND').
    """

    def __init__(self, message: str, error_code: str | None = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


class EngineNotFoundError(TTSError):
    """Raised when no suitable TTS engine is available for the requested language.

    Helps identify language-engine mismatches during synthesis routing.

    Args:
        language: The unsupported language code (e.g., 'xx').
        available_engines: Optional list of engines that are configured but don't support the language.
    """

    def __init__(self, language: str, available_engines: list[str] | None = None):
        message = f"No TTS engine found for language: {language}"
        if available_engines:
            message += f". Available engines: {', '.join(available_engines)}"
        super().__init__(message, "ENGINE_NOT_FOUND")
        self.language = language
        self.available_engines = available_engines or []


class AudioConversionError(TTSError):
    """Raised during failures in audio format conversion or processing.

    Covers issues like FFmpeg errors or incompatible formats in the audio pipeline.

    Args:
        message: Description of the conversion failure.
        source_format: Optional original audio format (e.g., 'wav').
        target_format: Optional desired output format (e.g., 'ogg').
    """

    def __init__(
        self,
        message: str,
        source_format: str | None = None,
        target_format: str | None = None,
    ):
        super().__init__(message, "AUDIO_CONVERSION_FAILED")
        self.source_format = source_format
        self.target_format = target_format


class TextValidationError(TTSError):
    """Raised for invalid input text, like exceeding length limits or bad characters.

    Ensures text inputs are safe and within configurable bounds before processing.

    Args:
        message: Explanation of the validation failure.
        text: Optional snippet of the invalid text.
        max_length: Optional max allowed length for context.
    """

    def __init__(
        self, message: str, text: str | None = None, max_length: int | None = None
    ):
        super().__init__(message, "TEXT_VALIDATION_FAILED")
        self.text = text
        self.max_length = max_length


class LanguageNotSupportedError(TTSError):
    """Raised when a requested language isn't supported by the chosen TTS engine.

    Provides details on alternatives to help with fallback decisions.

    Args:
        language: The unsupported language code.
        engine: The engine name (e.g., 'gtts').
        supported_languages: Optional list of languages the engine does support.
    """

    def __init__(
        self, language: str, engine: str, supported_languages: list[str] | None = None
    ):
        message = f"Language '{language}' is not supported by engine '{engine}'"
        if supported_languages:
            message += f". Supported languages: {', '.join(supported_languages)}"
        super().__init__(message, "LANGUAGE_NOT_SUPPORTED")
        self.language = language
        self.engine = engine
        self.supported_languages = supported_languages or []


class ConfigurationError(TTSError):
    """Raised for invalid, missing, or incompatible configuration settings.

    Covers issues like bad env vars, invalid paths, or unmet dependencies.

    Args:
        message: Description of the config problem.
        setting_name: Optional name of the problematic setting (e.g., 'bot_token').
    """

    def __init__(self, message: str, setting_name: str | None = None):
        super().__init__(message, "CONFIGURATION_ERROR")
        self.setting_name = setting_name


class RateLimitError(TTSError):
    """Raised when a user or API exceeds the rate limit threshold.

    Delivers clear messages for throttling, helping with user feedback.

    Args:
        message: User-friendly explanation of the limit exceeded.
    """

    def __init__(self, message: str):
        super().__init__(message, "RATE_LIMIT_EXCEEDED")


class CacheError(TTSError):
    """Raised for failures in cache storage, retrieval, or management.

    Applies to memory or Redis cache issues during audio or session handling.

    Args:
        message: Details of the cache failure.
        operation: Optional type of operation (e.g., 'set', 'get').
    """

    def __init__(self, message: str, operation: str | None = None):
        super().__init__(message, "CACHE_ERROR")
        self.operation = operation


class FFmpegNotFoundError(TTSError):
    """Raised when FFmpeg is missing or unusable for audio tasks.

    Critical for format conversions; suggests installation if triggered.

    Args:
        message: Optional custom error message (defaults to standard notice).
    """

    def __init__(self, message: str = "FFmpeg not found or not working properly"):
        super().__init__(message, "FFMPEG_NOT_FOUND")


class NetworkError(TTSError):
    """Raised for network-related failures, like timeouts or connection issues.

    Common for online TTS engines (e.g., gTTS, Edge) or API calls.

    Args:
        message: Description of the network problem.
        url: Optional URL that failed (for debugging).
    """

    def __init__(self, message: str, url: str | None = None):
        super().__init__(message, "NETWORK_ERROR")
        self.url = url


class BotTokenError(TTSError):
    """Raised for issues with the Telegram bot token setup.

    Ensures valid authentication before bot operations start.

    Args:
        message: Optional custom message (defaults to standard error).
    """

    def __init__(self, message: str = "Invalid or missing bot token"):
        super().__init__(message, "BOT_TOKEN_ERROR")


class AllEnginesFailedError(TTSError):
    """Raised as a last resort when every available TTS engine fails.

    Indicates a systemic issue; no fallback succeeded for the request.

    Args:
        message: Optional details (defaults to general failure notice).
    """

    def __init__(self, message: str = "All TTS engines failed"):
        super().__init__(message, "ALL_ENGINES_FAILED")


class EngineNotAvailableError(TTSError):
    """Raised when a requested TTS engine isn't configured or ready.

    Differs from EngineNotFoundError by focusing on availability, not language support.

    Args:
        engine_name: The unavailable engine (e.g., 'piper').
        message: Optional custom message (auto-generates if None).
    """

    def __init__(self, engine_name: str, message: str | None = None):
        if message is None:
            message = f"Engine '{engine_name}' is not available"
        super().__init__(message, "ENGINE_NOT_AVAILABLE")
        self.engine_name = engine_name


class AudioProcessingError(TTSError):
    """Raised for errors in audio manipulation, beyond just conversion.

    Covers encoding, decoding, normalization, or other post-synthesis steps.

    Args:
        message: Details of the processing failure.
        operation: Optional step that failed (e.g., 'encoding').
    """

    def __init__(self, message: str, operation: str | None = None):
        super().__init__(message, "AUDIO_PROCESSING_ERROR")
        self.operation = operation


class TTSKitAudioError(TTSError):
    """TTSKit-specific exception for audio processing failures.

    Provides more context for internal audio handling issues.

    Args:
        message: The error description.
        operation: Optional specific operation (e.g., 'normalization').
    """

    def __init__(self, message: str, operation: str | None = None):
        super().__init__(message, "TTSKIT_AUDIO_ERROR")
        self.operation = operation


class TTSKitNetworkError(TTSError):
    """TTSKit-specific network failure exception.

    Includes URL for easier debugging of online service issues.

    Args:
        message: Network error details.
        url: Optional failing URL.
    """

    def __init__(self, message: str, url: str | None = None):
        super().__init__(message, "TTSKIT_NETWORK_ERROR")
        self.url = url


class TTSKitEngineError(TTSError):
    """TTSKit-specific error for TTS engine operations.

    Captures engine name for targeted troubleshooting.

    Args:
        message: Failure description.
        engine: Optional engine involved (e.g., 'edge').
    """

    def __init__(self, message: str, engine: str | None = None):
        super().__init__(message, "TTSKIT_ENGINE_ERROR")
        self.engine = engine


class TTSKitFileError(TTSError):
    """TTSKit-specific exception for file I/O failures.

    Includes path for quick identification of disk or permission issues.

    Args:
        message: File operation error.
        file_path: Optional affected file path.
    """

    def __init__(self, message: str, file_path: str | None = None):
        super().__init__(message, "TTSKIT_FILE_ERROR")
        self.file_path = file_path


class TTSKitInternalError(TTSError):
    """Catch-all for unexpected internal TTSKit failures.

    Use when errors don't match other categories; includes component for logging.

    Args:
        message: Internal error description.
        component: Optional module or part (e.g., 'router').
    """

    def __init__(self, message: str, component: str | None = None):
        super().__init__(message, "TTSKIT_INTERNAL_ERROR")
        self.component = component


class RateLimitExceededError(TTSError):
    """Detailed exception for per-user rate limit violations.

    Includes limits and window for precise throttling feedback.

    Args:
        user_id: The limited user's ID.
        max_requests: The maximum allowed requests.
        window_seconds: The time window in seconds.
    """

    def __init__(self, user_id: str, max_requests: int, window_seconds: int):
        message = f"Rate limit exceeded for user {user_id}"
        super().__init__(message, "RATE_LIMIT_EXCEEDED")
        self.user_id = user_id
        self.max_requests = max_requests
        self.window_seconds = window_seconds


# Alias for the base TTSError (legacy compatibility)
TTSKitError = TTSError
