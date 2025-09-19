"""
Base abstract class for TTS engines.

This module defines the abstract base class and common functionality
for all TTS engines in TTSKit, providing a consistent interface
and shared capabilities.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from ..metrics.advanced import get_metrics_collector
from ..utils.performance import get_performance_monitor


@dataclass
class EngineCapabilities:
    """
    Engine capabilities and limitations.
    
    This class defines what features and limitations a TTS engine has,
    including supported languages, voices, and control options.
    """

    offline: bool
    ssml: bool
    rate_control: bool
    pitch_control: bool
    languages: list[str]
    voices: list[str]
    max_text_length: int

    @property
    def rate(self) -> bool:
        return self.rate_control

    @property
    def pitch(self) -> bool:
        return self.pitch_control


class TTSEngine(ABC):
    """
    Abstract base class for TTS engines.
    
    This class defines the interface that all TTS engines must implement,
    providing both synchronous and asynchronous synthesis methods along
    with capability reporting and validation.
    """

    def __init__(self, default_lang: str | None = None):
        """
        Initialize the engine.

        Args:
            default_lang: Default language code to use when none specified
        """
        self.default_lang = default_lang or "en"

    @abstractmethod
    def synth_to_mp3(self, text: str, lang: str | None = None) -> str:
        """
        Synthesize text to MP3 file (synchronous).

        Args:
            text: The text to synthesize.
            lang: Language code (e.g., 'en', 'fa', 'ar'). If None, use default.

        Returns:
            Path to the generated MP3 file. Caller is responsible for cleanup.
        """
        raise NotImplementedError

    def synth(
        self,
        text: str,
        lang: str,
        voice: str,
        rate: str,
        pitch: str,
    ) -> bytes:
        """
        Synchronous shortcut that delegates to synth_async.

        This default implementation converts string-based parameters to
        numeric values and calls the async implementation. Engines don't
        need to override this unless they want custom behavior.
        
        Args:
            text: Text to synthesize
            lang: Language code
            voice: Voice name
            rate: Rate as string (e.g., "100%", "1.5")
            pitch: Pitch as string (e.g., "0st", "5")
            
        Returns:
            Audio data as bytes
        """

        def _parse_rate(r: str) -> float:
            try:
                if r.endswith("%"):
                    return 1.0 + float(r[:-1]) / 100.0
                return float(r)
            except Exception:
                return 1.0

        def _parse_pitch(p: str) -> float:
            try:
                if p.endswith("st"):
                    return float(p[:-2])
                return float(p)
            except Exception:
                return 0.0

        numeric_rate = _parse_rate(rate)
        numeric_pitch = _parse_pitch(pitch)

        return asyncio.run(
            self.synth_async(text, lang, voice, numeric_rate, numeric_pitch)
        )

    @abstractmethod
    async def synth_async(
        self,
        text: str,
        lang: str | None = None,
        voice: str | None = None,
        rate: float = 1.0,
        pitch: float = 0.0,
    ) -> bytes:
        """
        Synthesize text to audio asynchronously with performance monitoring.

        Args:
            text: The text to synthesize.
            lang: Language code (e.g., 'en', 'fa', 'ar').
            voice: Voice name (engine-specific).
            rate: Speech rate multiplier (1.0 = normal).
            pitch: Pitch adjustment in semitones (0.0 = normal).

        Returns:
            Audio data as bytes.
        """

        start_time = time.time()
        performance_monitor = get_performance_monitor()
        metrics_collector = get_metrics_collector()

        try:
            result = await self._synth_async_impl(text, lang, voice, rate, pitch)

            duration = time.time() - start_time
            engine_name = self.__class__.__name__.lower().replace("engine", "")
            await performance_monitor.record_request(
                engine_name, lang or "unknown", duration, success=True
            )
            await metrics_collector.record_request(
                engine_name, lang or "unknown", duration, success=True
            )

            return result

        except Exception as e:
            duration = time.time() - start_time
            engine_name = self.__class__.__name__.lower().replace("engine", "")
            await performance_monitor.record_request(
                engine_name, lang or "unknown", duration, success=False
            )
            await metrics_collector.record_request(
                engine_name,
                lang or "unknown",
                duration,
                success=False,
                error_type=type(e).__name__,
            )
            await metrics_collector.record_error(type(e).__name__, str(e))
            raise

    async def _synth_async_impl(
        self,
        text: str,
        lang: str | None = None,
        voice: str | None = None,
        rate: float = 1.0,
        pitch: float = 0.0,
    ) -> bytes:
        """
        Actual implementation of synthesis (to be overridden by engines).

        Args:
            text: The text to synthesize.
            lang: Language code (e.g., 'en', 'fa', 'ar').
            voice: Voice name (engine-specific).
            rate: Speech rate multiplier (1.0 = normal).
            pitch: Pitch adjustment in semitones (0.0 = normal).

        Returns:
            Audio data as bytes.
        """
        raise NotImplementedError

    def capabilities(self) -> dict:
        """
        Get engine capabilities as dictionary.

        Returns:
            Dictionary with engine capabilities for API compatibility
        """
        caps = self.get_capabilities()
        return {
            "offline": caps.offline,
            "ssml": caps.ssml,
            "rate": caps.rate_control,
            "pitch": caps.pitch_control,
            "langs": caps.languages,
            "voices": caps.voices,
            "max_text_length": caps.max_text_length,
        }

    @abstractmethod
    def get_capabilities(self) -> EngineCapabilities:
        """Get engine capabilities and limitations.

        Returns:
            EngineCapabilities object
        """
        raise NotImplementedError

    @abstractmethod
    def list_voices(self, lang: str | None = None) -> list[str]:
        """List available voices for language.

        Args:
            lang: Language code. If None, return all voices.

        Returns:
            List of voice names
        """
        raise NotImplementedError

    @abstractmethod
    def is_available(self) -> bool:
        """Check if engine is available and ready to use.

        Returns:
            True if engine is available
        """
        raise NotImplementedError

    def get_supported_languages(self) -> list[str]:
        """Get list of supported languages.

        Returns:
            List of language codes
        """
        return list(self.get_capabilities().languages)

    def supports_language(self, lang: str) -> bool:
        """Check if engine supports a specific language.

        Args:
            lang: Language code

        Returns:
            True if language is supported
        """
        return lang in self.get_supported_languages()

    def supports_voice(self, voice: str) -> bool:
        """Check if engine supports a specific voice.

        Args:
            voice: Voice name

        Returns:
            True if voice is supported
        """
        return voice in self.get_capabilities().voices

    def can_handle_text_length(self, text: str) -> bool:
        """Check if engine can handle text of given length.

        Args:
            text: Text to check

        Returns:
            True if text length is acceptable
        """
        max_length = self.get_capabilities().max_text_length
        return len(text) <= max_length

    def validate_input(
        self, text: str, lang: str | None = None, voice: str | None = None
    ) -> None:
        """Validate input parameters.

        Args:
            text: Text to synthesize
            lang: Language code
            voice: Voice name

        Raises:
            ValueError: If input is invalid
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        if not self.can_handle_text_length(text):
            max_length = self.get_capabilities().max_text_length
            raise ValueError(f"Text too long. Maximum {max_length} characters allowed")

        if lang and not self.supports_language(lang):
            return "invalid_language"

        if voice and not self.supports_voice(voice):
            return "invalid_voice"

    async def synth_to_file_async(
        self,
        text: str,
        output_path: str,
        lang: str | None = None,
        voice: str | None = None,
        rate: float = 1.0,
        pitch: float = 0.0,
    ) -> str:
        """Synthesize text to file asynchronously.

        Args:
            text: Text to synthesize
            output_path: Output file path
            lang: Language code
            voice: Voice name
            rate: Speech rate multiplier
            pitch: Pitch adjustment

        Returns:
            Path to generated file
        """
        audio_data = await self.synth_async(text, lang, voice, rate, pitch)

        with open(output_path, "wb") as f:
            f.write(audio_data)

        return output_path

    def synth_to_file(
        self,
        text: str,
        output_path: str,
        lang: str | None = None,
        voice: str | None = None,
        rate: float = 1.0,
        pitch: float = 0.0,
    ) -> str:
        """Synthesize text to file (synchronous).

        Args:
            text: Text to synthesize
            output_path: Output file path
            lang: Language code
            voice: Voice name
            rate: Speech rate multiplier
            pitch: Pitch adjustment

        Returns:
            Path to generated file
        """
        return asyncio.run(
            self.synth_to_file_async(text, output_path, lang, voice, rate, pitch)
        )

    def get_info(self) -> dict[str, Any]:
        """Get engine information.

        Returns:
            Dictionary with engine information
        """
        capabilities = self.get_capabilities()
        return {
            "name": self.__class__.__name__,
            "version": "1.0.0",
            "default_lang": self.default_lang,
            "available": self.is_available(),
            "description": self.__class__.__doc__ or "",
            "capabilities": {
                "offline": capabilities.offline,
                "ssml": capabilities.ssml,
                "rate_control": capabilities.rate_control,
                "pitch_control": capabilities.pitch_control,
                "max_text_length": capabilities.max_text_length,
            },
            "languages": capabilities.languages,
            "voices_count": len(capabilities.voices),
            "supported_languages": self.get_supported_languages(),
        }


class BaseEngine(TTSEngine):
    """
    Base engine implementation with common functionality.
    
    This class provides a concrete implementation of common TTS engine
    functionality that can be extended by specific engine implementations.
    """

    def __init__(self, default_lang: str | None = None):
        super().__init__(default_lang)
        self._capabilities = self._get_default_capabilities()
        self._available = True
        self._connection_pool = None

    def _get_default_capabilities(self) -> EngineCapabilities:
        """
        Get default capabilities for this engine.
        
        Returns:
            Default EngineCapabilities with basic settings
        """
        return EngineCapabilities(
            offline=False,
            ssml=False,
            rate_control=False,
            pitch_control=False,
            languages=["en"],
            voices=[],
            max_text_length=1000,
        )

    def get_capabilities(self) -> EngineCapabilities:
        """
        Get engine capabilities.
        
        Returns:
            EngineCapabilities object describing this engine's features
        """
        return self._capabilities

    def is_available(self) -> bool:
        """
        Check if engine is available.
        
        Returns:
            True if engine is ready for use
        """
        return self._available

    def _cleanup_temp_files(self, file_path: str) -> None:
        """
        Clean up temporary files.

        Args:
            file_path: Path to temporary file to clean up
        """
        import os

        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                parent_dir = os.path.dirname(file_path)
                if parent_dir and os.path.exists(parent_dir):
                    try:
                        os.rmdir(parent_dir)
                    except OSError:
                        pass
        except Exception as e:
            from ..utils.logging_config import get_logger

            logger = get_logger(__name__)
            logger.debug(f"Failed to cleanup temp files: {e}")

    def _validate_text_input(self, text: str) -> None:
        """
        Validate text input.

        Args:
            text: Text to validate

        Raises:
            ValueError: If text is invalid or too long
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        if not self.can_handle_text_length(text):
            max_length = self.get_capabilities().max_text_length
            raise ValueError(f"Text too long. Maximum {max_length} characters allowed")

    def _validate_language(self, lang: str) -> bool:
        """
        Validate language code.

        Args:
            lang: Language code to validate

        Returns:
            True if language is supported by this engine
        """
        return self.supports_language(lang)

    def _validate_voice(self, voice: str) -> bool:
        """
        Validate voice name.

        Args:
            voice: Voice name to validate

        Returns:
            True if voice is supported by this engine
        """
        return self.supports_voice(voice)

    async def _get_connection_pool(self):
        """
        Get connection pool for HTTP requests.
        
        Returns:
            Connection pool instance for making HTTP requests
        """
        if self._connection_pool is None:
            from ..utils.performance import get_connection_pool

            self._connection_pool = get_connection_pool()
        return self._connection_pool
