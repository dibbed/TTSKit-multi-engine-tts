"""Piper TTS Engine implementation (offline, fast).

This engine provides offline text-to-speech using the new Piper TTS library.
It's fast, lightweight, and supports multiple languages with local models.
"""

import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from ..utils.logging_config import get_logger
from ..utils.temp_manager import TempFileManager
from .base import EngineCapabilities, TTSEngine

# Setup logging
logger = get_logger(__name__)

try:
    from piper import PiperVoice, SynthesisConfig

    PIPER_AVAILABLE = True
except ImportError:
    PIPER_AVAILABLE = False


class PiperEngine(TTSEngine):
    """TTS engine using the new Piper TTS library (offline, fast)."""

    def __init__(
        self,
        model_path: str = "./models/piper/",
        default_lang: str | None = None,
        use_cuda: bool = False,
    ):
        """Initialize the Piper engine.

        Args:
            model_path: Path to Piper voices directory
            default_lang: Default language code
            use_cuda: Whether to use CUDA for GPU acceleration
        """
        if not PIPER_AVAILABLE:
            raise ImportError(
                "piper-tts package not installed. Install with: pip install piper-tts"
            )

        super().__init__(default_lang)
        self.model_path = Path(model_path)
        self.use_cuda = use_cuda
        self.voices: dict[str, PiperVoice] = {}
        self.available_voices: list[str] = []
        self.configs: dict[str, dict] = {}
        self._available = True

        # Load available voices
        self.load_voices()

    def load_voices(self) -> None:
        """Load all available Piper voices."""
        if not self.model_path.exists():
            logger.warning(f"Piper voices path does not exist: {self.model_path}")
            self._available = False
            return

        # Look for .onnx files in the voices directory
        voice_files = list(self.model_path.glob("*.onnx"))
        if not voice_files:
            logger.warning(f"No Piper voice models found in {self.model_path}")
            self._available = False
            return

        for voice_file in voice_files:
            try:
                # Extract voice name from filename (e.g., "fa_IR-amir-medium.onnx")
                voice_name = voice_file.stem

                # Load voice model
                voice = PiperVoice.load(str(voice_file), use_cuda=self.use_cuda)
                self.voices[voice_name] = voice
                self.available_voices.append(voice_name)

                logger.info(f"Loaded Piper voice: {voice_name}")

            except Exception as e:
                logger.warning(f"Failed to load Piper voice {voice_file}: {e}")

        if not self.voices:
            logger.warning("No Piper voices loaded successfully")
            self._available = False
        else:
            logger.info(f"Loaded {len(self.voices)} Piper voices")

    def synth_to_mp3(self, text: str, lang: str | None = None) -> str:
        """Synthesize text to MP3 using Piper.

        Args:
            text: Text to synthesize
            lang: Language code

        Returns:
            Path to generated MP3 file
        """
        lang = lang or self.default_lang
        self.validate_input(text, lang)

        # Find best voice for language
        voice_name = self._find_best_voice(lang)
        if not voice_name:
            raise ValueError(f"No Piper voice found for language: {lang}")

        # Run synthesis in thread pool
        try:
            asyncio.get_running_loop()
            # If we're already in an event loop, run in thread
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self._synth_sync_to_mp3, text, voice_name)
                return future.result()
        except RuntimeError:
            # No running loop, safe to use asyncio.run
            return asyncio.run(self._synth_async_to_mp3(text, voice_name))

    async def synth_async(
        self,
        text: str,
        lang: str | None = None,
        voice: str | None = None,
        rate: float = 1.0,
        pitch: float = 0.0,
        output_format: str = "wav",
    ) -> bytes:
        """Synthesize text to audio asynchronously using Piper.

        Args:
            text: Text to synthesize
            lang: Language code
            voice: Voice name
            rate: Speech rate multiplier
            pitch: Pitch adjustment
            output_format: Output format (wav, mp3, ogg)

        Returns:
            Audio data as bytes
        """
        lang = lang or self.default_lang
        self.validate_input(text, lang)

        # Find voice
        if voice:
            voice_name = voice
        else:
            voice_name = self._find_best_voice(lang)

        if not voice_name or voice_name not in self.voices:
            raise ValueError(f"No Piper voice found: {voice_name}")

        # Run synthesis in thread pool
        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor(max_workers=1) as executor:
            audio_data = await loop.run_in_executor(
                executor, self._synth_sync_to_bytes, text, voice_name, rate, pitch
            )

        # If output format is WAV, return as-is (already has WAV header)
        if output_format.lower() == "wav":
            return audio_data

        # For other formats, we need to convert
        # This will be handled by the audio processing pipeline
        return audio_data

    def _find_best_voice(self, lang: str) -> str | None:
        """Find the best voice for a language.

        Args:
            lang: Language code

        Returns:
            Voice name or None if not found
        """
        # Try exact language match first (e.g., "fa_IR-amir-medium")
        for voice_name in self.available_voices:
            if voice_name.startswith(f"{lang}_"):
                return voice_name

        # Try language prefix match
        lang_prefix = lang.split("-")[0]
        for voice_name in self.available_voices:
            if voice_name.startswith(f"{lang_prefix}_"):
                return voice_name

        # Return first available voice as fallback
        if self.available_voices:
            return self.available_voices[0]

        return None

    def _synth_sync(self, text: str, voice_name: str) -> str:
        """Synchronous synthesis to WAV file.

        Args:
            text: Text to synthesize
            voice_name: Voice name

        Returns:
            Path to WAV file
        """
        # Generate audio data (now returns WAV format)
        audio_data = self._synth_sync_to_bytes(text, voice_name)

        # Save to temporary WAV file
        temp_manager = TempFileManager(prefix="piper_")
        td = temp_manager.create_temp_dir()
        wav_path = os.path.join(td, "synth.wav")

        with open(wav_path, "wb") as f:
            f.write(audio_data)

        return wav_path

    def _synth_sync_to_mp3(self, text: str, voice_name: str) -> str:
        """Synchronous synthesis to MP3 file.

        Args:
            text: Text to synthesize
            voice_name: Voice name

        Returns:
            Path to MP3 file
        """
        # Generate audio data (now returns WAV format)
        audio_data = self._synth_sync_to_bytes(text, voice_name)

        # Save to temporary MP3 file
        temp_manager = TempFileManager(prefix="piper_")
        td = temp_manager.create_temp_dir()
        mp3_path = os.path.join(td, "synth.mp3")

        with open(mp3_path, "wb") as f:
            f.write(audio_data)

        return mp3_path

    def _synth_sync_to_bytes(
        self, text: str, voice_name: str, rate: float = 1.0, pitch: float = 0.0
    ) -> bytes:
        """Synchronous synthesis to bytes using new Piper API.

        Args:
            text: Text to synthesize
            voice_name: Voice name
            rate: Speech rate multiplier
            pitch: Pitch adjustment

        Returns:
            Audio data as bytes (WAV format with proper header)
        """
        voice = self.voices[voice_name]

        # Create synthesis config
        syn_config = SynthesisConfig(
            volume=0.8,
            length_scale=rate,
            noise_scale=0.8,
            noise_w_scale=0.9,
            normalize_audio=True,
        )

        # Generate audio using streaming synthesis
        audio_chunks = []
        for chunk in voice.synthesize(text, syn_config=syn_config):
            audio_chunks.append(chunk.audio_int16_bytes)

        # Combine all chunks
        raw_audio_data = b"".join(audio_chunks)

        # Convert to WAV format with proper header
        return self._raw_audio_to_wav(raw_audio_data)

    def _raw_audio_to_wav(self, raw_audio_data: bytes) -> bytes:
        """Convert raw audio data to WAV format with proper header.

        Args:
            raw_audio_data: Raw 16-bit PCM audio data

        Returns:
            WAV file data with header
        """
        import io
        import wave

        # WAV parameters (Piper default)
        sample_rate = 22050
        channels = 1
        bits_per_sample = 16

        # Create WAV file in memory
        wav_buffer = io.BytesIO()

        with wave.open(wav_buffer, "wb") as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(bits_per_sample // 8)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(raw_audio_data)

        # Get the complete WAV file data
        wav_buffer.seek(0)
        return wav_buffer.read()

    async def _synth_async_to_wav(self, text: str, voice_name: str) -> str:
        """Asynchronous synthesis to WAV file.

        Args:
            text: Text to synthesize
            voice_name: Voice name

        Returns:
            Path to WAV file
        """
        # Generate audio data (now returns WAV format)
        audio_data = self._synth_sync_to_bytes(text, voice_name)

        # Save to temporary WAV file
        temp_manager = TempFileManager(prefix="piper_")
        td = temp_manager.create_temp_dir()
        wav_path = os.path.join(td, "synth.wav")

        with open(wav_path, "wb") as f:
            f.write(audio_data)

        return wav_path

    async def _synth_async_to_mp3(self, text: str, voice_name: str) -> str:
        """Asynchronous synthesis to MP3 file.

        Args:
            text: Text to synthesize
            voice_name: Voice name

        Returns:
            Path to MP3 file
        """
        # Generate audio data (now returns WAV format)
        audio_data = self._synth_sync_to_bytes(text, voice_name)

        # Save to temporary MP3 file
        temp_manager = TempFileManager(prefix="piper_")
        td = temp_manager.create_temp_dir()
        mp3_path = os.path.join(td, "synth.mp3")

        with open(mp3_path, "wb") as f:
            f.write(audio_data)

        return mp3_path

    def get_capabilities(self) -> EngineCapabilities:
        """Get engine capabilities and limitations.

        Returns:
            EngineCapabilities object
        """
        # Extract languages from loaded voices
        languages = set()
        for voice_name in self.available_voices:
            # Extract language from voice name (e.g., "fa_IR-amir-medium" -> "fa")
            lang = voice_name.split("_")[0]
            languages.add(lang)

        return EngineCapabilities(
            offline=True,
            ssml=False,
            rate_control=True,  # Supported via SynthesisConfig
            pitch_control=False,  # Not directly supported
            languages=list(languages),
            voices=self.available_voices,
            max_text_length=5000,
        )

    def list_voices(self, lang: str | None = None) -> list[str]:
        """List available voices for language.

        Args:
            lang: Language code. If None, return all voices.

        Returns:
            List of voice names
        """
        if lang is None:
            return self.available_voices

        # Filter voices by language
        lang_voices = []
        for voice in self.available_voices:
            if voice.startswith(f"{lang}_"):
                lang_voices.append(voice)

        return lang_voices

    def is_available(self) -> bool:
        """Check if engine is available and ready to use.

        Returns:
            True if engine is available
        """
        return PIPER_AVAILABLE and self._available and len(self.voices) > 0

    def set_available(self, available: bool) -> None:
        """Set engine availability (for testing).

        Args:
            available: Whether engine is available
        """
        self._available = available

    def get_model_info(self, model_key: str) -> dict[str, Any] | None:
        """Get information about a specific model.

        Args:
            model_key: Model key

        Returns:
            Model information or None if not found
        """
        if model_key not in self.voices:
            return None

        config = self.configs.get(model_key, {})
        return {
            "model_key": model_key,
            "language": model_key.split("_")[0],
            "voice": model_key.split("_")[1],
            "config": config,
            "available": True,
        }

    def get_all_models_info(self) -> dict[str, dict[str, Any]]:
        """Get information about all loaded models.

        Returns:
            Dictionary with model information
        """
        return {
            model_key: self.get_model_info(model_key)
            for model_key in self.voices.keys()
        }
