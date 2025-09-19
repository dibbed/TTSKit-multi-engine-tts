"""Audio conversion utilities for TTSKit using pydub and FFmpeg.

This module provides functions for checking FFmpeg availability, converting audio to OGG/Opus,
extracting audio information, and analyzing audio quality metrics.
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from pydub import AudioSegment

from ..config import settings
from ..exceptions import (
    AudioConversionError,
    FFmpegNotFoundError,
    TTSKitAudioError,
    TTSKitFileError,
)
from .logging_config import get_logger

logger = get_logger(__name__)


def check_ffmpeg_available() -> bool:
    """Check if FFmpeg is available and working.

    Returns:
        bool: True if FFmpeg is installed and executable, False otherwise.
    """
    try:
        ffmpeg_path = shutil.which("ffmpeg") or "ffmpeg"
        result = subprocess.run(
            [ffmpeg_path, "-version"],
            capture_output=True,
            text=True,
            timeout=5,
            shell=False,
            check=False,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        return False


def to_opus_ogg(
    src: str,
    dst: str,
    *,
    bitrate: str = None,
    sample_rate: int = None,
    channels: int = None,
) -> None:
    """Convert an audio file to OGG/Opus format using pydub and FFmpeg.

    This function loads the source audio, applies specified sample rate and channels,
    and exports it to the destination path. It falls back to default codec if libopus is unavailable.

    Args:
        src: Path to the source audio file (supports formats like MP3).
        dst: Path for the destination OGG file.
        bitrate: Target bitrate for Opus (str, e.g., '64k'); defaults to settings.audio_bitrate.
        sample_rate: Sample rate in Hz (int); defaults to settings.audio_sample_rate.
        channels: Number of audio channels (int); defaults to settings.audio_channels.

    Raises:
        FFmpegNotFoundError: Raised if FFmpeg is not installed or accessible. Install via:
            - Windows: Download from https://ffmpeg.org/download.html
            - macOS: brew install ffmpeg
            - Ubuntu/Debian: sudo apt install ffmpeg
            - CentOS/RHEL: sudo yum install ffmpeg
        AudioConversionError: Raised if source file is missing or conversion fails (e.g., invalid audio).

    Notes:
        Ensures the destination directory exists before conversion.
        Logs a warning and uses default OGG codec if libopus fails.
        Logs success on completion (debug level).
    """
    if not check_ffmpeg_available():
        raise FFmpegNotFoundError(
            "FFmpeg is required for audio conversion. Please install FFmpeg:\n"
            "  - Windows: Download from https://ffmpeg.org/download.html\n"
            "  - macOS: brew install ffmpeg\n"
            "  - Ubuntu/Debian: sudo apt install ffmpeg\n"
            "  - CentOS/RHEL: sudo yum install ffmpeg"
        )

    if not os.path.exists(src):
        raise AudioConversionError(f"Source file not found: {src}")

    dst_path = Path(dst)
    dst_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        bitrate = bitrate or settings.audio_bitrate
        sample_rate = sample_rate or settings.audio_sample_rate
        channels = channels or settings.audio_channels

        audio = AudioSegment.from_file(src)

        audio = audio.set_frame_rate(sample_rate).set_channels(channels)

        try:
            audio.export(
                dst,
                format="ogg",
                codec="libopus",
                bitrate=bitrate,
                parameters=["-ac", str(channels), "-ar", str(sample_rate)],
            )
        except Exception:
            logger.warning("libopus codec not available, using default codec")
            audio.export(
                dst,
                format="ogg",
                bitrate=bitrate,
                parameters=["-ac", str(channels), "-ar", str(sample_rate)],
            )

        logger.debug(f"Successfully converted {src} to {dst}")

    except Exception as e:
        raise AudioConversionError(f"Failed to convert audio: {e}") from e


def get_audio_info(file_path: str) -> dict:
    """Extract basic information from an audio file.

    Loads the file using pydub and computes duration, sample rate, channels, estimated bitrate,
    format, and file size.

    Args:
        file_path: Path to the audio file.

    Returns:
        dict: Audio metadata including:
            - duration: Length in seconds (float).
            - sample_rate: Frame rate in Hz (int).
            - channels: Number of channels (int).
            - bitrate: Estimated bitrate in bits per second (int).
            - format: File extension in lowercase (str).
            - size: File size in bytes (int).

    Raises:
        TTSKitFileError: If the file does not exist.
        TTSKitAudioError: If loading or processing the file fails.
    """
    if not os.path.exists(file_path):
        raise TTSKitFileError(f"Audio file not found: {file_path}")

    try:
        audio = AudioSegment.from_file(file_path)
        return {
            "duration": len(audio) / 1000.0,
            "sample_rate": audio.frame_rate,
            "channels": audio.channels,
            "bitrate": audio.frame_rate * audio.channels * audio.sample_width * 8,
            "format": os.path.splitext(file_path)[1].lower(),
            "size": os.path.getsize(file_path),
        }
    except Exception as e:
        raise TTSKitAudioError(f"Failed to get audio info: {e}") from e


def analyze_audio_quality(file_path: str) -> dict[str, Any]:
    """Analyze quality metrics and compute a score for an audio file.

    Loads the file and calculates basic metrics like duration, sample rate, and amplitude.
    Computes a quality score (0-100) based on sample rate, bit depth, channels, and dynamic range.

    Args:
        file_path: Path to the audio file.

    Returns:
        dict: Quality information including:
            - duration: Length in seconds (float).
            - sample_rate: Frame rate in Hz (int).
            - channels: Number of channels (int).
            - bitrate: Estimated bitrate in bits per second (int).
            - max_amplitude: Peak amplitude (int).
            - rms: Root mean square amplitude (float).
            - format: File extension in lowercase (str).
            - size: File size in bytes (int).
            - quality_score: Overall score from 0 to 100 (int).

    Raises:
        TTSKitFileError: If the file does not exist.
        TTSKitAudioError: If loading or analyzing the file fails.

    Notes:
        Scoring criteria:
        - Sample rate: +30 for >=44.1kHz, +20 for >=22.05kHz, +10 otherwise.
        - Bit depth: +30 for >=16-bit (sample_width >=2), +20 for >=8-bit, +10 otherwise.
        - Channels: +20 for stereo (>=2), +15 for mono.
        - Dynamic range: +20 if >20dB, +15 if >10dB, +10 otherwise.
        Score is capped at 100.
    """
    if not os.path.exists(file_path):
        raise TTSKitFileError(f"Audio file not found: {file_path}")

    try:
        audio = AudioSegment.from_file(file_path)

        quality_info = {
            "duration": len(audio) / 1000.0,
            "sample_rate": audio.frame_rate,
            "channels": audio.channels,
            "bitrate": audio.frame_rate * audio.channels * audio.sample_width * 8,
            "max_amplitude": audio.max,
            "rms": audio.rms,
            "format": os.path.splitext(file_path)[1].lower(),
            "size": os.path.getsize(file_path),
        }

        quality_score = 0

        if audio.frame_rate >= 44100:
            quality_score += 30
        elif audio.frame_rate >= 22050:
            quality_score += 20
        else:
            quality_score += 10

        if audio.sample_width >= 2:
            quality_score += 30
        elif audio.sample_width >= 1:
            quality_score += 20
        else:
            quality_score += 10

        if audio.channels >= 2:
            quality_score += 20
        else:
            quality_score += 15

        if audio.max > 0:
            dynamic_range = 20 * (audio.max / audio.rms) if audio.rms > 0 else 0
            if dynamic_range > 20:
                quality_score += 20
            elif dynamic_range > 10:
                quality_score += 15
            else:
                quality_score += 10

        quality_info["quality_score"] = min(quality_score, 100)

        return quality_info

    except Exception as e:
        raise TTSKitAudioError(f"Failed to analyze audio quality: {e}") from e


# Global instances for easy access to audio processing tools (initialized as needed)
audio_effects_processor = None
audio_file_optimizer = None
audio_file_repairer = None
