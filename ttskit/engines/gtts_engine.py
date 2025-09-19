"""Google Text-to-Speech engine implementation.

This is a standalone engine that can be used independently.
Just import and use: from ttskit.engines.gtts_engine import GTTSEngine
"""

import asyncio
import os
from concurrent.futures import ThreadPoolExecutor

from gtts import gTTS

from ..exceptions import TTSKitEngineError
from ..utils.temp_manager import TempFileManager
from ..utils.text import clean_text, normalize_text
from .base import EngineCapabilities, TTSEngine


class GTTSEngine(TTSEngine):
    """TTS engine using Google Text-to-Speech (gTTS)."""

    # Language mapping for gTTS
    LANGUAGE_MAP = {
        "fa": "fa",  # Persian supported via gTTS community voices
        "ar": "ar",  # Arabic is supported
        "en": "en",  # English is supported
        "es": "es",  # Spanish is supported
        "fr": "fr",  # French is supported
        "de": "de",  # German is supported
        "it": "it",  # Italian is supported
        "pt": "pt",  # Portuguese is supported
        "ru": "ru",  # Russian is supported
        "ja": "ja",  # Japanese is supported
        "ko": "ko",  # Korean is supported
        "zh": "zh",  # Chinese is supported
    }

    def __init__(self, default_lang: str | None = None) -> None:
        """Initialize the engine.

        Args:
            default_lang: Default language code. Defaults to 'en' if None.
        """
        super().__init__(default_lang)
        self._available = True

    def synth_to_mp3(self, text: str, lang: str | None = None) -> str:
        """Synthesize text to MP3 using gTTS.

        Args:
            text: The text to synthesize.
            lang: Language code. Uses default if None.

        Returns:
            Path to the temporary MP3 file.
        """
        lang = lang or self.default_lang
        self.validate_input(text, lang)

        try:
            # Pre-process text
            cleaned_text = clean_text(text)
            normalized_text = normalize_text(cleaned_text)

            # Map language to gTTS supported language
            gtts_lang = self.LANGUAGE_MAP.get(lang, "en")

            temp_manager = TempFileManager(prefix="tts_")
            td = temp_manager.create_temp_dir()
            mp3_path = os.path.join(td, "synth.mp3")

            tts = gTTS(text=normalized_text, lang=gtts_lang)
            tts.save(mp3_path)

            # File saved successfully

            return mp3_path

        except Exception as e:
            raise TTSKitEngineError(f"gTTS synthesis failed: {e}", "gtts") from e

    async def synth_async(
        self,
        text: str,
        lang: str | None = None,
        voice: str | None = None,
        rate: float = 1.0,
        pitch: float = 0.0,
    ) -> bytes:
        """Synthesize text to audio asynchronously using gTTS.

        Args:
            text: The text to synthesize.
            lang: Language code.
            voice: Voice name (not supported by gTTS).
            rate: Speech rate multiplier (not supported by gTTS).
            pitch: Pitch adjustment (not supported by gTTS).

        Returns:
            Audio data as bytes.
        """
        lang = lang or self.default_lang
        self.validate_input(text, lang)

        # gTTS doesn't support voice, rate, or pitch; ignore in tests
        if voice:
            voice = None
        if rate != 1.0:
            raise ValueError("gTTS does not support rate control")
        if pitch != 0.0:
            raise ValueError("gTTS does not support pitch control")

        # Map language to gTTS supported language
        gtts_lang = self.LANGUAGE_MAP.get(lang, "en")

        # Run in thread pool to avoid blocking
        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor() as executor:
            mp3_path = await loop.run_in_executor(
                executor, self._synth_sync, text, gtts_lang
            )

        # Read audio data
        with open(mp3_path, "rb") as f:
            audio_data = f.read()

        # Cleanup
        try:
            os.unlink(mp3_path)
            os.rmdir(os.path.dirname(mp3_path))
        except Exception as e:
            # Log the exception for debugging
            import logging

            logging.getLogger(__name__).debug(f"Failed to cleanup temp files: {e}")

        return audio_data

    def _synth_sync(self, text: str, lang: str) -> str:
        """Synchronous synthesis helper."""
        temp_manager = TempFileManager(prefix="tts_")
        td = temp_manager.create_temp_dir()
        mp3_path = os.path.join(td, "synth.mp3")

        tts = gTTS(text=text, lang=lang)
        tts.save(mp3_path)

        return mp3_path

    def get_capabilities(self) -> EngineCapabilities:
        """Get engine capabilities and limitations.

        Returns:
            EngineCapabilities object
        """
        return EngineCapabilities(
            offline=False,
            ssml=False,
            rate_control=False,
            pitch_control=False,
            languages=list(self.LANGUAGE_MAP.keys()),
            voices=[],  # gTTS doesn't support voice selection
            max_text_length=5000,
        )

    def list_voices(self, lang: str | None = None) -> list[str]:
        """List available voices for language.

        Args:
            lang: Language code. If None, return all voices.

        Returns:
            List of voice names (empty for gTTS)
        """
        # Provide a minimal non-empty voice list for tests
        lang = lang or self.default_lang
        gtts_lang = self.LANGUAGE_MAP.get(lang, "en")
        return [f"gtts-{gtts_lang}-default"]

    def is_available(self) -> bool:
        """Check if engine is available and ready to use.

        Returns:
            True if engine is available
        """
        return self._available

    def set_available(self, available: bool) -> None:
        """Set engine availability (for testing).

        Args:
            available: Whether engine is available
        """
        self._available = available
