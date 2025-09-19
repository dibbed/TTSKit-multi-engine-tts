"""Advanced Audio Processing Pipeline for TTSKit.

This module contains the core audio processing functionality for TTSKit, providing
a comprehensive pipeline for audio manipulation, enhancement, and conversion.
The AudioPipeline class offers high-performance audio processing capabilities
including format conversion, normalization, silence trimming, effect application,
audio merging, and segmentation. It uses optimized libraries like NumPy, Librosa,
and SoundFile when available, with graceful fallbacks for missing dependencies.

The module also provides convenience functions and a global pipeline instance
for easy access to audio processing features throughout the TTSKit ecosystem.
"""

import asyncio
import io
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from ..utils.logging_config import get_logger
from ..utils.temp_manager import TempFileManager

logger = get_logger(__name__)

try:
    import numpy as np

    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    import librosa

    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

try:
    from scipy import signal as _scipy_signal

    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

try:
    import soundfile

    SOUNDFILE_AVAILABLE = True
except ImportError:
    SOUNDFILE_AVAILABLE = False

try:
    from pydub import AudioSegment

    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False


class AudioPipeline:
    """Advanced audio processing pipeline for TTSKit.

    This class provides comprehensive audio processing capabilities for TTS-generated content,
    including format conversion, normalization, effect application, silence trimming, and audio
    manipulation. It automatically detects available audio processing libraries and implements
    performance optimizations with graceful degradation for missing dependencies.

    The pipeline supports various audio formats and offers both synchronous and asynchronous
    processing methods. It can process audio in memory or fallback to temporary files when
    memory operations are not supported.

    Attributes:
        sample_rate (int): Default sample rate for audio processing (22050 Hz).
        channels (int): Default number of audio channels (1 - mono).
        bit_depth (int): Default bit depth for audio (16 bits).

    Example:
        pipeline = AudioPipeline()

        # Basic audio processing
        processed_audio = await pipeline.process_audio(
            audio_data,
            input_format="wav",
            output_format="mp3",
            normalize=True,
            trim_silence=True
        )

        # Apply audio effects
        processed_audio = await pipeline.process_audio(
            audio_data,
            effects={
                "volume": 1.2,
                "fade_in": 0.5,
                "fade_out": 1.0
            }
        )
    """

    def __init__(self):
        """Set up the audio pipeline with default audio settings.

        Initializes key attributes like sample rate, channels, and bit depth
        to sensible defaults, while evaluating available dependencies to
        determine which processing features can be used safely.
        """
        self.sample_rate = 22050
        self.channels = 1
        self.bit_depth = 16
        self._available = self._check_dependencies()

    def _check_dependencies(self) -> bool:
        """Evaluate availability of audio processing libraries.

        Checks for key dependencies like NumPy and SoundFile, logging warnings
        for any missing optional libraries that limit functionality.
        Gracefully handles import errors and provides clear feedback.

        Returns:
            bool: True if essential audio processing dependencies are present.
        """
        if not NUMPY_AVAILABLE:
            logger.warning("numpy not available - some features will be limited")
        if not LIBROSA_AVAILABLE:
            logger.warning("librosa not available - advanced audio processing disabled")
        if not SOUNDFILE_AVAILABLE:
            logger.warning("soundfile not available - audio I/O will be limited")
        if not PYDUB_AVAILABLE:
            logger.warning("pydub not available - format conversion will be limited")

        return NUMPY_AVAILABLE and SOUNDFILE_AVAILABLE

    def is_available(self) -> bool:
        """Check if pipeline is available.

        Returns:
            True if pipeline is available
        """
        return self._available

    async def process_audio(
        self,
        audio_data: bytes,
        input_format: str = "wav",
        output_format: str = "mp3",
        sample_rate: int | None = None,
        normalize: bool = True,
        trim_silence: bool = True,
        effects: dict[str, Any] | None = None,
    ) -> bytes:
        """Process audio data with various enhancements.

        Args:
            audio_data: Input audio data
            input_format: Input audio format
            output_format: Output audio format
            sample_rate: Target sample rate
            normalize: Whether to normalize audio
            trim_silence: Whether to trim silence
            effects: Audio effects to apply

        Returns:
            Processed audio data
        """
        if not self.is_available():
            raise RuntimeError("Audio pipeline not available - missing dependencies")

        if len(audio_data) < 1024:
            return audio_data

        if len(audio_data) < 1024 * 1024:
            return self._process_audio_sync(
                audio_data,
                input_format,
                output_format,
                sample_rate,
                normalize,
                trim_silence,
                effects,
            )

        # Run processing in thread pool for larger files
        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor(max_workers=1) as executor:
            processed_data = await loop.run_in_executor(
                executor,
                self._process_audio_sync,
                audio_data,
                input_format,
                output_format,
                sample_rate,
                normalize,
                trim_silence,
                effects,
            )

        return processed_data

    def _process_audio_sync(
        self,
        audio_data: bytes,
        input_format: str,
        output_format: str,
        sample_rate: int | None,
        normalize: bool,
        trim_silence: bool,
        effects: dict[str, Any] | None,
    ) -> bytes:
        """Synchronous audio processing.

        Args:
            audio_data: Input audio data
            input_format: Input audio format
            output_format: Output audio format
            sample_rate: Target sample rate
            normalize: Whether to normalize audio
            trim_silence: Whether to trim silence
            effects: Audio effects to apply

        Returns:
            Processed audio data
        """
        audio, sr = self._load_audio(audio_data, input_format)

        if sample_rate and sr != sample_rate:
            audio = self._resample_audio(audio, sr, sample_rate)
            sr = sample_rate

        if effects:
            audio = self._apply_effects(audio, sr, effects)

        if normalize:
            audio = self._normalize_audio(audio)

        if trim_silence:
            audio = self._trim_silence(audio, sr)

        return self._save_audio(audio, sr, output_format)

    def _load_audio(self, audio_data: bytes, format: str) -> tuple[np.ndarray, int]:
        """Load audio data.

        Args:
            audio_data: Audio data bytes
            format: Audio format

        Returns:
            Tuple of (audio_array, sample_rate)
        """
        if not NUMPY_AVAILABLE or not SOUNDFILE_AVAILABLE:
            raise RuntimeError("Required audio libraries not available")

        try:
            import soundfile as sf

            audio, sr = sf.read(io.BytesIO(audio_data), format=format)
            return audio, sr
        except Exception:
            temp_manager = TempFileManager()
            tmp_file_path = temp_manager.create_temp_file(
                suffix=f".{format}", delete=False
            )

            with open(tmp_file_path, "wb") as tmp_file:
                tmp_file.write(audio_data)
                tmp_file.flush()

            import soundfile as sf

            audio, sr = sf.read(tmp_file_path)
            return audio, sr

    def _save_audio(self, audio: np.ndarray, sample_rate: int, format: str) -> bytes:
        """Save audio data.

        Args:
            audio: Audio array
            sample_rate: Sample rate
            format: Output format

        Returns:
            Audio data bytes
        """
        if not NUMPY_AVAILABLE or not SOUNDFILE_AVAILABLE:
            raise RuntimeError("Required audio libraries not available")

        try:
            import soundfile as sf

            output_buffer = io.BytesIO()
            sf.write(output_buffer, audio, sample_rate, format=format)
            return output_buffer.getvalue()
        except Exception:
            temp_manager = TempFileManager()
            tmp_file_path = temp_manager.create_temp_file(
                suffix=f".{format}", delete=False
            )

            import soundfile as sf

            sf.write(tmp_file_path, audio, sample_rate)

            with open(tmp_file_path, "rb") as f:
                return f.read()

    def _resample_audio(
        self, audio: np.ndarray, orig_sr: int, target_sr: int
    ) -> np.ndarray:
        """Resample audio to target sample rate.

        Args:
            audio: Input audio array
            orig_sr: Original sample rate
            target_sr: Target sample rate

        Returns:
            Resampled audio array
        """
        if orig_sr == target_sr:
            return audio

        if SCIPY_AVAILABLE:
            try:
                from math import gcd

                g = gcd(int(target_sr), int(orig_sr))
                up = int(target_sr // g)
                down = int(orig_sr // g)

                return _scipy_signal.resample_poly(audio, up, down)
            except Exception:
                pass

        if LIBROSA_AVAILABLE:
            try:
                import librosa

                return librosa.resample(
                    audio, orig_sr=orig_sr, target_sr=target_sr, res_type="linear"
                )
            except Exception:
                pass

        ratio = target_sr / orig_sr
        new_length = int(len(audio) * ratio)

        if ratio == 2.0:
            return np.repeat(audio, 2)[:new_length]
        elif ratio == 0.5:
            return audio[::2]
        else:
            return np.interp(
                np.linspace(0, len(audio) - 1, new_length), np.arange(len(audio)), audio
            )

    def _normalize_audio(self, audio: np.ndarray) -> np.ndarray:
        """Normalize audio to prevent clipping.

        Args:
            audio: Input audio array

        Returns:
            Normalized audio array
        """
        if not NUMPY_AVAILABLE:
            return audio

        max_val = np.max(np.abs(audio))
        if max_val > 0 and max_val > 1.0:
            return audio / max_val
        return audio

    def _trim_silence(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """Trim silence from audio.

        Args:
            audio: Input audio array
            sample_rate: Sample rate

        Returns:
            Trimmed audio array
        """
        threshold = 0.01
        mask = np.abs(audio) > threshold
        indices = np.where(mask)[0]

        if len(indices) > 0:
            padding = int(0.01 * sample_rate)  # 10ms padding
            start = max(0, indices[0] - padding)
            end = min(len(audio), indices[-1] + padding + 1)
            return audio[start:end]

        return audio

    def _apply_effects(
        self, audio: np.ndarray, sample_rate: int, effects: dict[str, Any]
    ) -> np.ndarray:
        """Apply audio effects.

        Args:
            audio: Input audio array
            sample_rate: Sample rate
            effects: Effects to apply

        Returns:
            Processed audio array
        """
        if not NUMPY_AVAILABLE:
            return audio

        processed = audio.copy()

        if "rate" in effects and effects["rate"] != 1.0:
            processed = self._change_rate(processed, sample_rate, effects["rate"])

        if "pitch" in effects and effects["pitch"] != 0.0:
            processed = self._change_pitch(processed, sample_rate, effects["pitch"])

        if "volume" in effects and effects["volume"] != 1.0:
            processed = processed * effects["volume"]

        if "fade_in" in effects and effects["fade_in"] > 0:
            processed = self._fade_in(processed, sample_rate, effects["fade_in"])

        if "fade_out" in effects and effects["fade_out"] > 0:
            processed = self._fade_out(processed, sample_rate, effects["fade_out"])

        return processed

    def _change_rate(
        self, audio: np.ndarray, sample_rate: int, rate: float
    ) -> np.ndarray:
        """Change audio playback rate.

        Args:
            audio: Input audio array
            sample_rate: Sample rate
            rate: Rate multiplier

        Returns:
            Rate-changed audio array
        """
        if not LIBROSA_AVAILABLE:
            new_length = int(len(audio) / rate)
            return np.interp(
                np.linspace(0, len(audio) - 1, new_length), np.arange(len(audio)), audio
            )

        if LIBROSA_AVAILABLE:
            try:
                import librosa

                return librosa.effects.time_stretch(audio, rate=rate)
            except Exception:
                pass

        orig_sr = sample_rate
        target_sr = int(sample_rate * rate)
        return self._resample_audio(audio, orig_sr, target_sr)

    def _change_pitch(
        self, audio: np.ndarray, sample_rate: int, pitch: float
    ) -> np.ndarray:
        """Change audio pitch.

        Args:
            audio: Input audio array
            sample_rate: Sample rate
            pitch: Pitch change in semitones

        Returns:
            Pitch-changed audio array
        """
        if not LIBROSA_AVAILABLE:
            return audio

        return librosa.effects.pitch_shift(audio, sr=sample_rate, n_steps=pitch)

    def _fade_in(
        self, audio: np.ndarray, sample_rate: int, duration: float
    ) -> np.ndarray:
        """Apply fade-in effect.

        Args:
            audio: Input audio array
            sample_rate: Sample rate
            duration: Fade duration in seconds

        Returns:
            Fade-in audio array
        """
        if not NUMPY_AVAILABLE:
            return audio

        fade_samples = int(duration * sample_rate)
        if fade_samples > len(audio):
            fade_samples = len(audio)

        fade_curve = np.linspace(0, 1, fade_samples)
        audio[:fade_samples] *= fade_curve

        return audio

    def _fade_out(
        self, audio: np.ndarray, sample_rate: int, duration: float
    ) -> np.ndarray:
        """Apply fade-out effect.

        Args:
            audio: Input audio array
            sample_rate: Sample rate
            duration: Fade duration in seconds

        Returns:
            Fade-out audio array
        """
        if not NUMPY_AVAILABLE:
            return audio

        fade_samples = int(duration * sample_rate)
        if fade_samples > len(audio):
            fade_samples = len(audio)

        fade_curve = np.linspace(1, 0, fade_samples)
        audio[-fade_samples:] *= fade_curve

        return audio

    def convert(
        self, input_bytes: bytes, input_format: str, output_format: str
    ) -> bytes:
        """Convert audio between formats (roadmap method).

        Args:
            input_bytes: Input audio data
            input_format: Input format
            output_format: Output format

        Returns:
            Converted audio data
        """
        return self.convert_format(input_bytes, input_format, output_format)

    def convert_format(
        self, audio_data: bytes, input_format: str, output_format: str
    ) -> bytes:
        """Convert audio between formats.

        Args:
            audio_data: Input audio data
            input_format: Input format
            output_format: Output format

        Returns:
            Converted audio data
        """
        if not PYDUB_AVAILABLE:
            raise RuntimeError("pydub not available for format conversion")

        audio = AudioSegment.from_file(io.BytesIO(audio_data), format=input_format)

        if output_format == "mp3":
            audio = audio.export(format="mp3")
        elif output_format == "wav":
            audio = audio.export(format="wav")
        elif output_format == "ogg":
            audio = audio.export(format="ogg")
        else:
            raise ValueError(f"Unsupported output format: {output_format}")

        return audio.read()

    def normalize(self, audio_data: bytes, input_format: str = "wav") -> bytes:
        """Normalize audio (roadmap method).

        Args:
            audio_data: Input audio data
            input_format: Input format

        Returns:
            Normalized audio data
        """
        if not self.is_available():
            raise RuntimeError("Audio pipeline not available - missing dependencies")

        audio, sr = self._load_audio(audio_data, input_format)

        normalized_audio = self._normalize_audio(audio)

        return self._save_audio(normalized_audio, sr, input_format)

    def get_audio_info(self, audio_data: bytes, format: str) -> dict[str, Any]:
        """Get audio information.

        Args:
            audio_data: Audio data
            format: Audio format

        Returns:
            Audio information dictionary
        """
        if not PYDUB_AVAILABLE:
            raise RuntimeError("pydub not available for audio info")

        audio = AudioSegment.from_file(io.BytesIO(audio_data), format=format)

        return {
            "duration": len(audio) / 1000.0,
            "sample_rate": audio.frame_rate,
            "channels": audio.channels,
            "bit_depth": audio.sample_width * 8,
            "format": format,
            "size_bytes": len(audio_data),
        }

    def merge_audio(
        self, audio_files: list[bytes], output_format: str = "mp3"
    ) -> bytes:
        """Merge multiple audio files.

        Args:
            audio_files: List of audio data
            output_format: Output format

        Returns:
            Merged audio data
        """
        if not audio_files:
            raise ValueError("No audio files provided")

        if PYDUB_AVAILABLE:
            merged = AudioSegment.from_file(io.BytesIO(audio_files[0]))

            for audio_data in audio_files[1:]:
                audio = AudioSegment.from_file(io.BytesIO(audio_data))
                merged += audio

            return merged.export(format=output_format).read()
        else:
            if output_format.lower() == "wav":
                return self._merge_wav_files(audio_files)
            else:
                raise RuntimeError(
                    "pydub not available for audio merging with non-WAV formats"
                )

    def _merge_wav_files(self, audio_files: list[bytes]) -> bytes:
        """Merge WAV files by concatenating audio data.

        Args:
            audio_files: List of WAV audio data

        Returns:
            Merged WAV audio data
        """
        if not NUMPY_AVAILABLE or not SOUNDFILE_AVAILABLE:
            raise RuntimeError("Required audio libraries not available for WAV merging")

        import wave

        first_wav = io.BytesIO(audio_files[0])
        with wave.open(first_wav, "rb") as wav_file:
            nchannels = wav_file.getnchannels()
            sampwidth = wav_file.getsampwidth()
            framerate = wav_file.getframerate()

        all_audio_data = []
        total_frames = 0

        for audio_data in audio_files:
            wav_buffer = io.BytesIO(audio_data)
            with wave.open(wav_buffer, "rb") as wav_file:
                if (
                    wav_file.getnchannels() != nchannels
                    or wav_file.getsampwidth() != sampwidth
                    or wav_file.getframerate() != framerate
                ):
                    raise ValueError("All WAV files must have the same format")

                frames = wav_file.readframes(wav_file.getnframes())
                all_audio_data.append(frames)
                total_frames += wav_file.getnframes()

        output_buffer = io.BytesIO()
        with wave.open(output_buffer, "wb") as output_wav:
            output_wav.setnchannels(nchannels)
            output_wav.setsampwidth(sampwidth)
            output_wav.setframerate(framerate)
            output_wav.setnframes(total_frames)

            for audio_data in all_audio_data:
                output_wav.writeframes(audio_data)

        return output_buffer.getvalue()

    def split_audio(
        self, audio_data: bytes, input_format: str, segment_duration: float
    ) -> list[bytes]:
        """Split audio into segments.

        Args:
            audio_data: Input audio data
            input_format: Input format
            segment_duration: Segment duration in seconds

        Returns:
            List of audio segments
        """
        if not PYDUB_AVAILABLE:
            raise RuntimeError("pydub not available for audio splitting")

        audio = AudioSegment.from_file(io.BytesIO(audio_data), format=input_format)
        segment_length = int(segment_duration * 1000)

        segments = []
        for i in range(0, len(audio), segment_length):
            segment = audio[i : i + segment_length]
            segments.append(segment.export(format=input_format).read())

        return segments


# Global pipeline instance for convenient audio processing access
pipeline = AudioPipeline()


def process_audio(audio_data: bytes, **kwargs) -> bytes:
    """Process audio data using the global pipeline.

    Args:
        audio_data: Input audio data
        **kwargs: Processing options

    Returns:
        Processed audio data
    """
    return asyncio.run(pipeline.process_audio(audio_data, **kwargs))


def convert_format(audio_data: bytes, input_format: str, output_format: str) -> bytes:
    """Convert audio format using the global pipeline.

    Args:
        audio_data: Input audio data
        input_format: Input format
        output_format: Output format

    Returns:
        Converted audio data
    """
    return pipeline.convert_format(audio_data, input_format, output_format)
