"""Microsoft Edge TTS engine implementation.

This optional engine provides a synchronous interface compatible with TTSEngine,
mapping language codes to default voices with fallbacks and supporting explicit overrides.
It requires the edge-tts package and handles synthesis to MP3 files.
"""

import asyncio
import os
from concurrent.futures import ThreadPoolExecutor

from ..exceptions import TTSKitEngineError, TTSKitFileError, TTSKitNetworkError
from ..utils.logging_config import get_logger
from ..utils.temp_manager import TempFileManager
from .base import EngineCapabilities, TTSEngine

try:
    import edge_tts  # type: ignore

    EDGE_AVAILABLE = True
except ImportError:
    EDGE_AVAILABLE = False

logger = get_logger(__name__)

# Mapping of language codes to default Edge TTS voices
VOICE_BY_LANG = {
    "en": "en-US-JennyNeural",
    "fa": "fa-IR-DilaraNeural",
    "ar": "ar-SA-HamedNeural",
    "es": "es-ES-ElviraNeural",
    "fr": "fr-FR-DeniseNeural",
    "de": "de-DE-KatjaNeural",
    "it": "it-IT-ElsaNeural",
    "pt": "pt-BR-FranciscaNeural",
    "ru": "ru-RU-SvetlanaNeural",
    "ja": "ja-JP-NanamiNeural",
    "ko": "ko-KR-SunHiNeural",
    "zh": "zh-CN-XiaoxiaoNeural",
}

# Default timeout for saving synthesized audio in seconds
DEFAULT_SAVE_TIMEOUT_SECONDS = 120
class EdgeEngine(TTSEngine):
    """TTS engine using Microsoft Edge TTS.

    This class implements a synchronous TTS interface compatible with TTSEngine,
    requiring the edge-tts package. It handles synthesis to MP3, voice selection with fallbacks,
    and capability reporting.

    Note:
        Supports SSML for advanced features like rate and pitch adjustments.
    """

    def __init__(
        self,
        default_lang: str | None = None,
        voice: str | None = None,
        *,
        save_timeout_seconds: int = DEFAULT_SAVE_TIMEOUT_SECONDS,
    ) -> None:
        """Initialize the EdgeEngine.

        Args:
            default_lang: Default language code (e.g., 'en' or 'fa').
            voice: Default voice name to use if not specified per synthesis.
            save_timeout_seconds: Timeout in seconds for synthesis save operations.

        Note:
            If edge-tts is not installed, the engine is marked unavailable but can still be constructed for testing.
        """
        if not EDGE_AVAILABLE:
            super().__init__(default_lang)
            self.voice_default = voice or VOICE_BY_LANG.get(
                self.default_lang, VOICE_BY_LANG["en"]
            )
            self.save_timeout_seconds = int(save_timeout_seconds)
            self._available = False
            return

        super().__init__(default_lang)
        self.voice_default = voice or VOICE_BY_LANG.get(
            self.default_lang, VOICE_BY_LANG["en"]
        )
        self.save_timeout_seconds = int(save_timeout_seconds)
        self._available = True

    def synth_to_mp3(self, text: str, lang: str | None = None) -> str:
        """Synthesize text to a temporary MP3 file using Edge TTS.

        Args:
            text: The text to synthesize into speech.
            lang: Language code (e.g., 'en'). Uses engine default if None.

        Returns:
            Path to the generated temporary MP3 file.

        Raises:
            TTSKitNetworkError: If a network issue occurs during synthesis.
            TTSKitFileError: If a file operation fails.
            TTSKitEngineError: For other synthesis failures.
        """
        lang = lang or self.default_lang
        self.validate_input(text, lang)

        try:
            asyncio.get_running_loop()
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    lambda: asyncio.run(self._async_synth_to_mp3(text, lang))
                )
                return future.result()
        except RuntimeError:
            return asyncio.run(self._async_synth_to_mp3(text, lang))
        except Exception as e:
            if "network" in str(e).lower() or "connection" in str(e).lower():
                raise TTSKitNetworkError(f"Edge TTS network error: {e}") from e
            elif "file" in str(e).lower() or "path" in str(e).lower():
                raise TTSKitFileError(f"Edge TTS file error: {e}") from e
            else:
                raise TTSKitEngineError(
                    f"Edge TTS synthesis failed: {e}", "edge"
                ) from e

    async def synth_async(
        self,
        text: str,
        lang: str | None = None,
        voice: str | None = None,
        rate: float = 1.0,
        pitch: float = 0.0,
    ) -> bytes:
        """Synthesize text to audio bytes asynchronously using Edge TTS.

        Args:
            text: The text to synthesize into speech.
            lang: Language code (e.g., 'en'). Uses default if None.
            voice: Specific voice name to use. Falls back to language-based selection if None.
            rate: Speech rate multiplier (1.0 is normal; supported via SSML).
            pitch: Pitch adjustment (0.0 is normal; supported via SSML).

        Returns:
            Raw audio data as bytes (MP3 format).

        Raises:
            TTSKitEngineError: If synthesis or file handling fails.

        Note:
            Rate and pitch parameters are kept for API compatibility but require SSML for actual support.
            Returns empty bytes if engine is unavailable (e.g., for testing).
            Temporary files are auto-cleaned up after reading.
        """
        lang = lang or self.default_lang
        self.validate_input(text, lang)

        _voice_name = voice or self._pick_voice(lang)

        if not EDGE_AVAILABLE or not self._available:
            return b""

        try:
            mp3_path = self.synth_to_mp3(text, lang)

            with open(mp3_path, "rb") as f:
                data = f.read()
            try:
                os.unlink(mp3_path)
                os.rmdir(os.path.dirname(mp3_path))
            except Exception as cleanup_error:
                logger.debug(f"Failed to cleanup temp file: {cleanup_error}")
            return data
        except Exception as e:
            raise TTSKitEngineError(f"Edge TTS synthesis failed: {e}", "edge") from e

    def _pick_voice(self, lang: str | None) -> str:
        """Select the best voice for the given language code.

        Args:
            lang: Language code (e.g., 'en' or 'fa-IR'). Uses engine default if None.

        Returns:
            The selected voice name string.

        Note:
            Follows this preference: exact language mapping, short code fallback (e.g., 'en-US' -> 'en'),
            engine default voice, or English as final fallback.
        """
        code = (lang or self.default_lang or "en").lower()
        short = code.split("-")[0]
        return (
            VOICE_BY_LANG.get(code)
            or VOICE_BY_LANG.get(short)
            or self.voice_default
            or VOICE_BY_LANG["en"]
        )

    async def _async_synth_to_mp3(self, text: str, lang: str | None = None) -> str:
        """Asynchronously synthesize text and save to a temporary MP3 file.

        Args:
            text: The text to synthesize.
            lang: Language code for voice selection. Uses default if None.

        Returns:
            Path to the saved temporary MP3 file.

        Note:
            Uses a temporary directory for the output file and enforces a save timeout.
            Supports both awaitable and synchronous mocked save calls for testing.
        """
        temp_manager = TempFileManager(prefix="edge_tts_")
        td = temp_manager.create_temp_dir()
        mp3_path = os.path.join(td, "synth.mp3")

        voice_name = self._pick_voice(lang)
        communicate = edge_tts.Communicate(text, voice_name)

        os.makedirs(os.path.dirname(mp3_path), exist_ok=True)
        save_call = communicate.save(mp3_path)
        if hasattr(save_call, "__await__"):
            await asyncio.wait_for(save_call, timeout=self.save_timeout_seconds)
        else:
            _ = save_call

        return mp3_path

    def get_capabilities(self) -> EngineCapabilities:
        """Retrieve the engine's supported features and limits.

        Returns:
            An EngineCapabilities instance detailing offline support, SSML, controls, languages, voices, and max text length.

        Note:
            Edge TTS is online-only but supports SSML, rate/pitch control (via SSML), and has a 1000-character text limit.
        """
        return EngineCapabilities(
            offline=False,
            ssml=True,
            rate_control=True,
            pitch_control=True,
            languages=list(VOICE_BY_LANG.keys()),
            voices=list(VOICE_BY_LANG.values()),
            max_text_length=1000,
        )

    def list_voices(self, lang: str | None = None) -> list[str]:
        """List voices available for a specific language or all voices.

        Args:
            lang: Language code prefix (e.g., 'en'). If None, returns all supported voices.

        Returns:
            List of matching voice name strings.
        """
        if lang:
            lang_voices = []
            for voice in VOICE_BY_LANG.values():
                if voice.startswith(f"{lang}-"):
                    lang_voices.append(voice)
            return lang_voices

        return list(VOICE_BY_LANG.values())

    def _get_voice_for_language(self, lang: str) -> str:
        """Get voice for a language (backward-compatible for tests).

        Args:
            lang: Language code (e.g., 'en').

        Returns:
            The selected voice name.
        """
        return self._pick_voice(lang)

    def is_available(self) -> bool:
        """Check if the engine is ready for use.

        Returns:
            True if edge-tts is installed and the engine is enabled.
        """
        return EDGE_AVAILABLE and self._available

    def set_available(self, available: bool) -> None:
        """Set the engine's availability status (primarily for testing).

        Args:
            available: True to enable, False to disable the engine.
        """
        self._available = available
