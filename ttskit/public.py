"""Public SDK classes and high-level functions for TTSKit.

This module offers a clean, easy-to-use API for integrating TTS synthesis,
engine management, and utilities into applications, hiding internal details.
"""

import asyncio
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .engines.factory import factory as engine_factory
from .engines.registry import registry as engine_registry
from .engines.smart_router import SmartRouter
from .exceptions import (
    AllEnginesFailedError,
    EngineNotAvailableError,
    TTSKitEngineError,
)
from .utils.audio_manager import audio_manager
from .utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class SynthConfig:
    """Settings for a TTS synthesis request.

    Defines text, language, voice, engine preferences, audio options, and cache behavior.

    Args:
        text: The text to convert to speech (required).
        lang: Language code like 'en', 'fa', 'ar' (default 'en').
        voice: Specific voice name for the engine (optional).
        engine: Preferred TTS engine (optional; auto-selects if None).
        rate: Speed multiplier (1.0 normal; >0 required).
        pitch: Semitone adjustment (0.0 normal).
        output_format: Audio format ('ogg', 'mp3', 'wav'; default 'ogg').
        cache: Enable caching for this request (default True).

    Notes:
        Validates rate >0 and format on init; raises ValueError if invalid.
    """

    text: str
    lang: str = "en"
    voice: str | None = None
    engine: str | None = None
    rate: float = 1.0
    pitch: float = 0.0
    output_format: str = "ogg"
    cache: bool = True

    def __post_init__(self):
        if self.rate <= 0:
            raise ValueError("Rate must be positive")
        if self.output_format not in ["ogg", "mp3", "wav"]:
            raise ValueError("Output format must be 'ogg', 'mp3', or 'wav'")


@dataclass
class AudioOut:
    """Output container for synthesized audio data and metadata.

    Holds bytes, format, duration, and specs for easy handling and saving.

    Args:
        data: Raw audio bytes.
        format: Format string ('ogg', 'mp3', 'wav').
        duration: Length in seconds.
        sample_rate: Hz (default 48000).
        channels: 1 or 2 (default 1).
        bitrate: kbps (default 128).
        size: Bytes length (default 0).
        engine: Optional engine name used.

    Notes:
        size auto-calculates from data if 0; supports saving and info export.
    """

    data: bytes
    format: str
    duration: float
    sample_rate: int = 48000
    channels: int = 1
    bitrate: int = 128
    size: int = 0
    engine: str | None = None

    def save(self, filepath: str | Path) -> None:
        """Write the audio bytes to a file path.

        Args:
            filepath: Destination path (str or Path); overwrites if exists.

        Notes:
            Logs success via logger.
        """
        filepath = Path(filepath)
        filepath.write_bytes(self.data)
        logger.info(f"Audio saved to {filepath}")

    def get_info(self) -> dict[str, Any]:
        """Extract metadata as a dictionary (excludes raw data).

        Returns:
            Dict with format, duration, sample_rate, channels, bitrate, size.
        """
        return {
            "format": self.format,
            "duration": self.duration,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "bitrate": self.bitrate,
            "size": self.size,
        }


class TTS:
    """Core SDK class for TTS synthesis with smart routing and processing.

    Handles engine selection, caching, fallbacks, and audio output for seamless use.

    Args:
        default_lang: Default language (default 'en').
        default_engine: Preferred engine (optional).
        cache_enabled: Use caching (default True).
    """

    def __init__(
        self,
        default_lang: str = "en",
        default_engine: str | None = None,
        cache_enabled: bool = True,
    ):
        self.default_lang = default_lang
        self.default_engine = default_engine
        self.cache_enabled = cache_enabled

        self.router = SmartRouter(engine_registry)
        self.smart_router = self.router
        self.stats = self.router.stats  # Expose stats for tests
        self._setup_engines()

    def _setup_engines(self) -> None:
        """Initialize and register available TTS engines with the factory."""
        try:
            # Register all engines with the factory
            engine_factory.setup_registry(engine_registry)
            logger.info("Engines registered successfully")
        except Exception as e:
            logger.warning(f"Failed to register some engines: {e}")

    async def synth_async(self, config: SynthConfig) -> AudioOut:
        """Generate speech from text asynchronously, with caching and fallbacks.

        Selects engine based on config; processes audio; caches if enabled.

        Args:
            config: SynthConfig with text, lang, etc.

        Returns:
            AudioOut with synthesized audio bytes and metadata.

        Raises:
            EngineNotAvailableError: If specified engine unavailable.
            AllEnginesFailedError: If no engine succeeds after fallbacks.
            TTSKitEngineError: For internal synthesis issues.

        Notes:
            Checks cache first; uses SmartRouter for selection; formats via audio_manager.
        """
        cached_audio = None
        if self.cache_enabled and config.cache:
            cache_key = self._generate_cache_key(config)
            maybe = audio_manager.get_from_cache(cache_key)
            cached_audio = await maybe if hasattr(maybe, "__await__") else maybe
            if cached_audio:
                logger.info("Using cached audio")
                return self._bytes_to_audio_out(cached_audio, config.output_format)

        if config.engine:
            engine = engine_factory.get_engine(config.engine)
            if not engine:
                raise EngineNotAvailableError(
                    config.engine, f"Engine '{config.engine}' not available"
                )
        else:
            selected = self.router.select_engine(
                lang=config.lang,
                requirements={"offline": False},
            )
            if isinstance(selected, str):
                engine = engine_factory.get_engine(selected)
            else:
                engine = selected
            if not engine:
                available_engines = engine_factory.get_available_engines()
                if available_engines:
                    engine = engine_factory.get_engine(available_engines[0])
                else:
                    raise AllEnginesFailedError("No suitable engine found")

        try:
            import inspect

            sig = inspect.signature(engine.synth_async)
            if "output_format" in sig.parameters:
                audio_data = await engine.synth_async(
                    text=config.text,
                    lang=config.lang,
                    voice=config.voice,
                    rate=config.rate,
                    pitch=config.pitch,
                    output_format=config.output_format,
                )
            else:
                audio_data = await engine.synth_async(
                    text=config.text,
                    lang=config.lang,
                    voice=config.voice,
                    rate=config.rate,
                    pitch=config.pitch,
                )

            input_format = "mp3"
            if engine.__class__.__name__ == "PiperEngine":
                input_format = "wav"

            processed_audio = await audio_manager.process_audio(
                audio_data,
                input_format=input_format,
                output_format=config.output_format,
                sample_rate=48000,
                channels=1,
            )

            audio_out = self._bytes_to_audio_out(processed_audio, config.output_format)

            if self.cache_enabled and config.cache:
                maybe_save = audio_manager.save_to_cache(cache_key, processed_audio)
                if hasattr(maybe_save, "__await__"):
                    await maybe_save

            return audio_out

        except Exception as e:
            logger.error(f"Engine {engine.__class__.__name__} failed: {e}")
            try:
                return await self._try_fallback_engines(config)
            except AllEnginesFailedError:
                raise
            except Exception as fallback_error:
                raise TTSKitEngineError(
                    f"All engines failed. Last error: {fallback_error}",
                    engine.__class__.__name__,
                ) from fallback_error

    def synth(self, config: SynthConfig) -> AudioOut:
        """Synchronous wrapper for synth_async using asyncio.run.

        Args:
            config: SynthConfig for the request.

        Returns:
            AudioOut with the audio.

        Notes:
            Blocks until complete; suitable for non-async contexts.
        """
        return asyncio.run(self.synth_async(config))

    async def _try_fallback_engines(self, config: SynthConfig) -> AudioOut:
        """Attempt synthesis with alternative engines if primary fails.

        Tries all available except the original; processes audio on success.

        Args:
            config: The original synthesis config.

        Returns:
            AudioOut from the successful engine.

        Raises:
            AllEnginesFailedError: If every engine fails.

        Notes:
            Logs warnings for each failure; skips original engine.
        """
        available_engines = engine_factory.get_available_engines()
        failed_engines = []

        for engine_name in available_engines:
            if engine_name == config.engine:
                continue  # Skip the already failed engine

            try:
                engine = engine_factory.get_engine(engine_name)
                if not engine:
                    continue

                audio_data = await engine.synth_async(
                    text=config.text,
                    lang=config.lang,
                    voice=config.voice,
                    rate=config.rate,
                    pitch=config.pitch,
                )

                processed_audio = await audio_manager.process_audio(
                    audio_data,
                    input_format="mp3",
                    output_format=config.output_format,
                    sample_rate=48000,
                    channels=1,
                )

                return self._bytes_to_audio_out(processed_audio, config.output_format)

            except Exception as e:
                failed_engines.append(engine_name)
                logger.warning(f"Fallback engine {engine_name} failed: {e}")
                continue

        raise AllEnginesFailedError(f"All engines failed: {failed_engines}")

    def _generate_cache_key(self, config: SynthConfig) -> str:
        """Create a SHA256 hash key from config params for caching.

        Args:
            config: SynthConfig to hash.

        Returns:
            Hex digest string for cache lookup.
        """
        import hashlib

        key_data = f"{config.text}|{config.lang}|{config.voice}|{config.engine}|{config.rate}|{config.pitch}|{config.output_format}"
        return hashlib.sha256(key_data.encode()).hexdigest()

    def _bytes_to_audio_out(self, audio_data: bytes, format: str) -> AudioOut:
        """Wrap audio bytes in AudioOut with metadata from audio_manager.

        Args:
            audio_data: Raw bytes.
            format: The audio format.

        Returns:
            Populated AudioOut instance.
        """
        info = audio_manager.get_audio_info(audio_data)

        return AudioOut(
            data=audio_data,
            format=format,
            duration=info.get("duration", 0.0),
            sample_rate=info.get("sample_rate", 48000),
            channels=info.get("channels", 1),
            bitrate=info.get("bitrate", 128),
            size=len(audio_data),
        )

    def list_voices(
        self, lang: str | None = None, engine: str | None = None
    ) -> list[str]:
        """Query available voices, filtered by language or engine.

        Aggregates from all engines if no engine specified; deduplicates.

        Args:
            lang: Optional language filter.
            engine: Optional engine filter (e.g., 'edge').

        Returns:
            Unique list of voice names.
        """
        voices: list[str] = []

        if engine:
            engine_instance = engine_factory.create_engine(engine)
            if engine_instance:
                voices = engine_instance.list_voices(lang)
        else:
            available_engines = engine_factory.get_available_engines()
            for engine_name in available_engines:
                engine_instance = engine_factory.create_engine(engine_name)
                if engine_instance:
                    engine_voices = engine_instance.list_voices(lang)
                    voices.extend(engine_voices)

        return list(set(voices))  # Remove duplicates

    def get_engines(self) -> list[dict[str, Any]]:
        """Retrieve details on all configured TTS engines.

        Returns:
            List of dicts with engine names, capabilities, etc.
        """
        engines_info = engine_factory.get_all_engines_info()
        return list(engines_info.values())

    # --- Preferences (stubs for tests) ---
    def set_engine_preferences(self, preferences: dict[str, Any]) -> None:
        """Stub for setting engine prefs (used in testing).

        Args:
            preferences: Dict of preferences.

        Raises:
            ValueError: If not a dict.
        """
        if not isinstance(preferences, dict):
            raise ValueError("preferences must be a dict")
        self._engine_preferences = preferences

    def get_stats(self) -> dict[str, Any]:
        """Fetch routing and synthesis stats from the router.

        Returns:
            Dict of aggregated stats.
        """
        return self.router.get_all_stats()

    def reset_stats(self) -> None:
        """Clear router statistics."""
        self.router.reset_stats()

    def get_engine_preferences(self) -> dict[str, Any]:
        """Retrieve current engine preferences or defaults.

        Returns:
            Dict with default_lang, default_engine, cache_enabled.
        """
        return getattr(self, "_engine_preferences", {}) or {
            "default_lang": self.default_lang,
            "default_engine": self.default_engine,
            "cache_enabled": self.cache_enabled,
        }



async def synth_async(
    text: str,
    lang: str = "en",
    voice: str | None = None,
    engine: str | None = None,
    rate: float = 1.0,
    pitch: float = 0.0,
    output_format: str = "ogg",
    cache: bool = True,
) -> AudioOut:
    """Quick async TTS synthesis without instantiating TTS class.

    Builds config internally and calls synth_async.

    Args:
        text: Text to synthesize (required).
        lang: Language (default 'en').
        voice: Voice (optional).
        engine: Engine (optional).
        rate: Speed (default 1.0).
        pitch: Adjustment (default 0.0).
        output_format: Format (default 'ogg').
        cache: Enable cache (default True).

    Returns:
        AudioOut with result.
    """
    config = SynthConfig(
        text=text,
        lang=lang,
        voice=voice,
        engine=engine,
        rate=rate,
        pitch=pitch,
        output_format=output_format,
        cache=cache,
    )

    tts = TTS(default_lang=lang)
    result = tts.synth_async(config)
    return await result if hasattr(result, "__await__") else result


def synth(
    text: str,
    lang: str = "en",
    voice: str | None = None,
    engine: str | None = None,
    rate: float = 1.0,
    pitch: float = 0.0,
    output_format: str = "ogg",
    cache: bool = True,
    **kwargs,
) -> AudioOut:
    """Synchronous TTS convenience function, alias for async via asyncio.run.

    Supports legacy 'format' kwarg for output_format.

    Args:
        text: Text (required).
        lang: Language (default 'en').
        voice: Voice (optional).
        engine: Engine (optional).
        rate: Speed (default 1.0).
        pitch: Adjustment (default 0.0).
        output_format: Format (default 'ogg').
        cache: Cache (default True).
        **kwargs: For backward compat, 'format' sets output_format.

    Returns:
        AudioOut.
    """
    if "format" in kwargs and not output_format:
        output_format = kwargs["format"]
    config = SynthConfig(
        text=text,
        lang=lang,
        voice=voice,
        engine=engine,
        rate=rate,
        pitch=pitch,
        output_format=output_format,
        cache=cache,
    )

    tts = TTS(default_lang=lang)
    return tts.synth(config)


def list_voices(lang: str | None = None, engine: str | None = None) -> list[str]:
    """List voices using a temporary TTS instance.

    Args:
        lang: Optional language filter.
        engine: Optional engine filter.

    Returns:
        Unique voice names list.
    """
    tts = TTS()
    return tts.list_voices(lang, engine)


def get_engines() -> list[dict[str, Any]]:
    """Get flattened info for all engines from factory.

    Includes capabilities like offline, languages, voices.

    Returns:
        List of dicts per engine.
    """
    engines_info = engine_factory.get_all_engines_info()
    out: list[dict[str, Any]] = []
    for name, info in engines_info.items():
        if not info:
            continue
        caps = info.get("capabilities", {})
        flattened = {
            **info,
            **{
                "offline": caps.get("offline", False),
                "languages": caps.get("languages", []),
                "voices": caps.get("voices", []),
            },
        }
        if "name" not in flattened:
            flattened["name"] = name
        out.append(flattened)
    return out


def clear_cache() -> None:
    """Flush the entire cache system."""
    from .cache import clear_cache as _clear_cache

    _clear_cache()


def get_cache_stats() -> dict[str, Any]:
    """Retrieve current cache usage and performance stats."""
    from .cache import get_cache_stats as _get_cache_stats

    return _get_cache_stats()


def is_cache_enabled() -> bool:
    """Query if the cache system is active."""
    from .cache import is_cache_enabled as _is_cache_enabled

    return _is_cache_enabled()


def convert_audio_format(
    input_path: str, output_path: str, target_format: str = "ogg"
) -> None:
    """Convert an audio file to OGG Opus (only format supported).

    Args:
        input_path: Source file path.
        output_path: Destination path.
        target_format: Must be 'ogg' (raises ValueError otherwise).

    Raises:
        ValueError: For unsupported formats.
    """
    from .utils.audio import to_opus_ogg

    if target_format.lower() == "ogg":
        to_opus_ogg(input_path, output_path)
    else:
        raise ValueError(f"Unsupported target format: {target_format}")


def get_audio_info(file_path: str) -> dict[str, Any]:
    """Extract metadata from an audio file.

    Args:
        file_path: Path to the audio file.

    Returns:
        Dict with duration, sample_rate, etc.
    """
    from .utils.audio import get_audio_info as _get_audio_info

    return _get_audio_info(file_path)


def get_config() -> dict[str, Any]:
    """Export the full settings as a dictionary.

    Returns:
        Dict from settings.model_dump().
    """
    from .config import get_settings

    settings = get_settings()
    return settings.model_dump()


def get_documentation() -> dict[str, Any]:
    """Return static project info and features.

    Returns:
        Dict with name, version, features, supported langs, etc.

    Notes:
        Hardcoded; update as project evolves.
    """
    return {
        "name": "TTSKit",
        "version": "1.0.0",
        "description": "Multi-engine Text-to-Speech toolkit with Telegram bot support",
        "features": [
            "Multiple TTS engines (gTTS, Edge-TTS, Piper)",
            "Telegram bot support (Aiogram, Pyrogram, Telethon, Telebot)",
            "Audio processing and conversion",
            "Caching and rate limiting",
            "Internationalization support",
            "Health monitoring and metrics",
        ],
        "engines": ["gtts", "edge", "piper"],
        "telegram_adapters": ["aiogram", "pyrogram", "telethon", "telebot"],
        "supported_languages": [
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
        ],
        "documentation_url": "https://github.com/your-repo/ttskit",
        "api_docs": "https://github.com/your-repo/ttskit/blob/main/docs/api.md",
    }


def get_engine_capabilities() -> dict[str, dict[str, Any]]:
    """Static overview of supported engines' features and limits.

    Returns:
        Dict keyed by engine name with langs, voices, features, etc.

    Notes:
        Hardcoded; reflects core capabilities—dynamic checks via factory.
    """
    return {
        "gtts": {
            "name": "Google Text-to-Speech",
            "languages": ["en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh"],
            "voices": ["default"],
            "features": ["online", "free", "fast"],
            "quality": "good",
            "latency": "low",
        },
        "edge": {
            "name": "Microsoft Edge TTS",
            "languages": [
                "en",
                "es",
                "fr",
                "de",
                "it",
                "pt",
                "ru",
                "ja",
                "ko",
                "zh",
                "ar",
                "fa",
            ],
            "voices": ["multiple"],
            "features": ["online", "free", "high_quality"],
            "quality": "excellent",
            "latency": "medium",
        },
        "piper": {
            "name": "Piper TTS",
            "languages": ["en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh"],
            "voices": ["multiple"],
            "features": ["offline", "free", "fast"],
            "quality": "good",
            "latency": "very_low",
        },
    }


def get_examples() -> dict[str, list[str]]:
    """Return code snippets for common TTSKit usage patterns.

    Returns:
        Dict of category to list of example lines.

    Notes:
        Basic to advanced; for docs or onboarding.
    """
    return {
        "basic_usage": [
            "from ttskit import TTSBot",
            "bot = TTSBot('your_bot_token')",
            "bot.start()",
        ],
        "engine_selection": [
            "from ttskit.engines import get_engine",
            "engine = get_engine('edge')",
            "audio = engine.synthesize('Hello world', 'en')",
        ],
        "telegram_bot": [
            "from ttskit.bot import TTSBot",
            "bot = TTSBot('token', engine='edge')",
            "bot.add_message_handler()",
            "bot.start_polling()",
        ],
        "audio_processing": [
            "from ttskit.utils.audio import to_opus_ogg",
            "to_opus_ogg('input.wav', 'output.ogg')",
        ],
        "caching": [
            "from ttskit.cache import get_cache",
            "cache = get_cache()",
            "cache.set('key', 'value', ttl=3600)",
        ],
        "rate_limiting": [
            "from ttskit.utils.rate_limiter import check_rate_limit",
            "allowed, remaining = await check_rate_limit('user_id')",
        ],
    }


async def get_health_status() -> dict[str, Any]:
    """Run health check and format results with status string.

    Returns:
        Dict with overall_status ('healthy'/'unhealthy'), components, details, version.
    """
    from .health import check_system_health

    status = await check_system_health()

    return {
        "overall_status": "healthy" if status["overall"] else "unhealthy",
        "components": status["checks"],
        "details": status["details"],
        "version": "1.0.0",
    }


async def get_rate_limit_info(user_id: str) -> dict[str, Any]:
    """Fetch rate limit status for a user from the limiter.

    Handles sync/async info; standardizes output dict; compatible with tests.

    Args:
        user_id: The user's ID string.

    Returns:
        Dict with rate_limited, remaining_requests, reset_time, message or error.

    Notes:
        Falls back to default if info is non-dict (e.g., message); wraps errors.
    """
    from .utils.rate_limiter import get_rate_limiter

    try:
        limiter = get_rate_limiter()
        info = limiter.get_user_info(user_id)
        if hasattr(info, "__await__"):
            info = await info

        # Ensure standard output structure
        if isinstance(info, dict):
            return info

        # If message returned, map to default structure
        return {
            "user_id": user_id,
            "rate_limited": False,
            "remaining_requests": 0,
            "reset_time": None,
            "message": str(info),
        }
    except Exception as e:
        return {
            "user_id": user_id,
            "error": str(e),
            "rate_limited": False,
            "remaining_requests": 0,
            "reset_time": None,
        }


def get_stats() -> dict[str, Any]:
    """Alias for get_metrics_summary().

    Returns:
        Aggregated metrics dict.
    """
    from .metrics import get_metrics_summary

    return get_metrics_summary()


def get_supported_formats() -> list[str]:
    """List formats handled by audio processing.

    Returns:
        Hardcoded list (may expand with backends).
    """
    return ["ogg", "mp3", "wav", "flac", "aac", "m4a"]


def get_supported_languages() -> list[str]:
    """Core supported languages across engines.

    Returns:
        List of codes; actual support varies by engine.
    """
    return [
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


def get_system_info() -> dict[str, Any]:
    """Gather platform and Python details.

    Returns:
        Dict with version, platform, arch, etc.
    """
    import platform
    import sys

    return {
        "python_version": sys.version,
        "platform": platform.platform(),
        "architecture": platform.architecture(),
        "processor": platform.processor(),
        "machine": platform.machine(),
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
    }


def get_version_info() -> dict[str, Any]:
    """Project metadata including version.

    Returns:
        Dict with version, package, description, author, license.
    """
    from .version import __version__

    return {
        "version": __version__,
        "package": "ttskit",
        "description": "Professional Telegram TTS library and bot",
        "author": "TTSKit Team",
        "license": "MIT",
    }


def normalize_audio(audio_data: bytes, **kwargs) -> bytes:
    """Normalize audio volume using pydub (to WAV).

    Args:
        audio_data: Input bytes (any format pydub supports).
        **kwargs: Passed to pydub.normalize (e.g., headroom).

    Returns:
        Normalized bytes; original if pydub fails.

    Notes:
        Logs errors; requires pydub installed.
    """
    try:
        import io

        from pydub import AudioSegment

        audio = AudioSegment.from_file(io.BytesIO(audio_data))

        normalized_audio = audio.normalize()

        output = io.BytesIO()
        normalized_audio.export(output, format="wav")
        return output.getvalue()
    except Exception as e:
        logger.error(f"Error normalizing audio: {e}")
        return audio_data


def reset_rate_limits() -> dict[str, Any]:
    """Clear all user rate limits in the limiter.

    Returns:
        Success dict with status/message/timestamp, or error on failure.

    Notes:
        Direct access to _user_limits; logs errors.
    """
    from .utils.rate_limiter import get_rate_limiter

    try:
        rate_limiter = get_rate_limiter()
        rate_limiter._user_limits.clear()

        return {
            "status": "success",
            "message": "Rate limits reset successfully",
            "timestamp": time.time(),
        }
    except Exception as e:
        logger.error(f"Error resetting rate limits: {e}")
        return {"status": "error", "message": str(e), "timestamp": time.time()}
