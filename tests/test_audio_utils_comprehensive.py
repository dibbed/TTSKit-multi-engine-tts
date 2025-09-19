"""Comprehensive tests for audio utilities."""

import os
import subprocess
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from pydub import AudioSegment

from ttskit.exceptions import (
    AudioConversionError,
    FFmpegNotFoundError,
    TTSKitAudioError,
    TTSKitFileError,
)
from ttskit.utils.audio import (
    analyze_audio_quality,
    check_ffmpeg_available,
    get_audio_info,
    to_opus_ogg,
)


class TestFFmpegAvailability:
    """Test FFmpeg availability checking."""

    def test_check_ffmpeg_available_success(self):
        """Test successful FFmpeg check."""
        with patch("shutil.which") as mock_which, patch("subprocess.run") as mock_run:
            mock_which.return_value = "/usr/bin/ffmpeg"
            mock_run.return_value.returncode = 0

            result = check_ffmpeg_available()

            assert result is True
            mock_run.assert_called_once()

    def test_check_ffmpeg_available_failure(self):
        """Test failed FFmpeg check."""
        with patch("shutil.which") as mock_which, patch("subprocess.run") as mock_run:
            mock_which.return_value = "/usr/bin/ffmpeg"
            mock_run.return_value.returncode = 1

            result = check_ffmpeg_available()

            assert result is False

    def test_check_ffmpeg_available_not_found(self):
        """Test FFmpeg not found."""
        with patch("shutil.which") as mock_which, patch("subprocess.run") as mock_run:
            mock_which.return_value = None
            mock_run.return_value.returncode = 0

            result = check_ffmpeg_available()

            assert result is True

    def test_check_ffmpeg_available_file_not_found_error(self):
        """Test FFmpeg check with FileNotFoundError."""
        with (
            patch("shutil.which") as mock_which,
            patch("subprocess.run", side_effect=FileNotFoundError()),
        ):
            mock_which.return_value = "/usr/bin/ffmpeg"

            result = check_ffmpeg_available()

            assert result is False

    def test_check_ffmpeg_available_timeout_error(self):
        """Test FFmpeg check with TimeoutExpired."""
        with (
            patch("shutil.which") as mock_which,
            patch("subprocess.run", side_effect=subprocess.TimeoutExpired("ffmpeg", 5)),
        ):
            mock_which.return_value = "/usr/bin/ffmpeg"

            result = check_ffmpeg_available()

            assert result is False

    def test_check_ffmpeg_available_general_exception(self):
        """Test FFmpeg check with general exception."""
        with (
            patch("shutil.which") as mock_which,
            patch("subprocess.run", side_effect=Exception("General error")),
        ):
            mock_which.return_value = "/usr/bin/ffmpeg"

            result = check_ffmpeg_available()

            assert result is False


class TestAudioConversion:
    """Test audio conversion functionality."""

    def test_to_opus_ogg_ffmpeg_not_available(self):
        """Test conversion when FFmpeg is not available."""
        with patch("ttskit.utils.audio.check_ffmpeg_available", return_value=False):
            with pytest.raises(FFmpegNotFoundError) as exc_info:
                to_opus_ogg("input.mp3", "output.ogg")

            assert "FFmpeg is required" in str(exc_info.value)

    def test_to_opus_ogg_source_file_not_found(self):
        """Test conversion with non-existent source file."""
        with patch("ttskit.utils.audio.check_ffmpeg_available", return_value=True):
            with pytest.raises(AudioConversionError) as exc_info:
                to_opus_ogg("nonexistent.mp3", "output.ogg")

            assert "Source file not found" in str(exc_info.value)

    def test_to_opus_ogg_success(self):
        """Test successful audio conversion."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = os.path.join(temp_dir, "input.wav")
            output_path = os.path.join(temp_dir, "output.ogg")

            audio = AudioSegment.silent(duration=1000, frame_rate=44100)
            audio.export(input_path, format="wav")

            with (
                patch("ttskit.utils.audio.check_ffmpeg_available", return_value=True),
                patch("ttskit.utils.audio.settings") as mock_settings,
                patch("ttskit.utils.audio.AudioSegment.from_file") as mock_from_file,
            ):
                mock_settings.audio_bitrate = "128k"
                mock_settings.audio_sample_rate = 44100
                mock_settings.audio_channels = 2

                mock_audio = MagicMock()
                mock_audio.set_frame_rate.return_value = mock_audio
                mock_audio.set_channels.return_value = mock_audio
                mock_audio.export.return_value = None
                mock_from_file.return_value = mock_audio

                to_opus_ogg(input_path, output_path)

                mock_from_file.assert_called_once_with(input_path)
                mock_audio.set_frame_rate.assert_called_once_with(44100)
                mock_audio.set_channels.assert_called_once_with(2)
                mock_audio.export.assert_called_once()

    def test_to_opus_ogg_with_custom_parameters(self):
        """Test conversion with custom parameters."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = os.path.join(temp_dir, "input.wav")
            output_path = os.path.join(temp_dir, "output.ogg")

            audio = AudioSegment.silent(duration=1000, frame_rate=44100)
            audio.export(input_path, format="wav")

            with (
                patch("ttskit.utils.audio.check_ffmpeg_available", return_value=True),
                patch("ttskit.utils.audio.AudioSegment.from_file") as mock_from_file,
            ):
                mock_audio = MagicMock()
                mock_audio.set_frame_rate.return_value = mock_audio
                mock_audio.set_channels.return_value = mock_audio
                mock_audio.export.return_value = None
                mock_from_file.return_value = mock_audio

                to_opus_ogg(
                    input_path,
                    output_path,
                    bitrate="256k",
                    sample_rate=48000,
                    channels=1,
                )

                mock_from_file.assert_called_once_with(input_path)
                mock_audio.set_frame_rate.assert_called_once_with(48000)
                mock_audio.set_channels.assert_called_once_with(1)
                mock_audio.export.assert_called_once()

    def test_to_opus_ogg_libopus_fallback(self):
        """Test conversion with libopus fallback."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = os.path.join(temp_dir, "input.wav")
            output_path = os.path.join(temp_dir, "output.ogg")

            audio = AudioSegment.silent(duration=1000, frame_rate=44100)
            audio.export(input_path, format="wav")

            with (
                patch("ttskit.utils.audio.check_ffmpeg_available", return_value=True),
                patch("ttskit.utils.audio.AudioSegment.from_file") as mock_from_file,
                patch("ttskit.utils.audio.logger") as mock_logger,
            ):
                mock_audio = MagicMock()
                mock_audio.set_frame_rate.return_value = mock_audio
                mock_audio.set_channels.return_value = mock_audio

                mock_audio.export.side_effect = [Exception("libopus error"), None]
                mock_from_file.return_value = mock_audio

                to_opus_ogg(input_path, output_path)

                assert mock_audio.export.call_count == 2
                mock_logger.warning.assert_called_once_with(
                    "libopus codec not available, using default codec"
                )

    def test_to_opus_ogg_conversion_error(self):
        """Test conversion error handling."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = os.path.join(temp_dir, "input.wav")
            output_path = os.path.join(temp_dir, "output.ogg")

            audio = AudioSegment.silent(duration=1000, frame_rate=44100)
            audio.export(input_path, format="wav")

            with (
                patch("ttskit.utils.audio.check_ffmpeg_available", return_value=True),
                patch("ttskit.utils.audio.AudioSegment.from_file") as mock_from_file,
            ):
                mock_audio = MagicMock()
                mock_audio.set_frame_rate.return_value = mock_audio
                mock_audio.set_channels.return_value = mock_audio
                mock_audio.export.side_effect = Exception("Export error")
                mock_from_file.return_value = mock_audio

                with pytest.raises(AudioConversionError) as exc_info:
                    to_opus_ogg(input_path, output_path)

                assert "Failed to convert audio" in str(exc_info.value)

    def test_to_opus_ogg_destination_directory_creation(self):
        """Test destination directory creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = os.path.join(temp_dir, "input.wav")
            output_path = os.path.join(temp_dir, "subdir", "output.ogg")

            audio = AudioSegment.silent(duration=1000, frame_rate=44100)
            audio.export(input_path, format="wav")

            with (
                patch("ttskit.utils.audio.check_ffmpeg_available", return_value=True),
                patch("ttskit.utils.audio.AudioSegment.from_file") as mock_from_file,
            ):
                mock_audio = MagicMock()
                mock_audio.set_frame_rate.return_value = mock_audio
                mock_audio.set_channels.return_value = mock_audio
                mock_audio.export.return_value = None
                mock_from_file.return_value = mock_audio

                to_opus_ogg(input_path, output_path)

                assert os.path.exists(os.path.dirname(output_path))


class TestAudioInfo:
    """Test audio information extraction."""

    def test_get_audio_info_file_not_found(self):
        """Test get audio info with non-existent file."""
        with pytest.raises(TTSKitFileError) as exc_info:
            get_audio_info("nonexistent.wav")

        assert "Audio file not found" in str(exc_info.value)

    def test_get_audio_info_success(self):
        """Test successful audio info extraction."""
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = os.path.join(temp_dir, "test.wav")

            audio = AudioSegment.silent(duration=2000, frame_rate=44100)
            audio.export(audio_path, format="wav")

            with (
                patch("ttskit.utils.audio.AudioSegment.from_file") as mock_from_file,
                patch("os.path.getsize", return_value=1024),
            ):
                mock_audio = MagicMock()
                mock_audio.__len__ = lambda self: 2000
                mock_audio.frame_rate = 44100
                mock_audio.channels = 2
                mock_audio.sample_width = 2
                mock_from_file.return_value = mock_audio

                info = get_audio_info(audio_path)

                assert info["duration"] == 2.0
                assert info["sample_rate"] == 44100
                assert info["channels"] == 2
                assert info["bitrate"] == 1411200
                assert info["format"] == ".wav"
                assert info["size"] == 1024

    def test_get_audio_info_error(self):
        """Test audio info extraction error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = os.path.join(temp_dir, "test.wav")

            audio = AudioSegment.silent(duration=1000, frame_rate=44100)
            audio.export(audio_path, format="wav")

            with patch(
                "ttskit.utils.audio.AudioSegment.from_file",
                side_effect=Exception("Audio error"),
            ):
                with pytest.raises(TTSKitAudioError) as exc_info:
                    get_audio_info(audio_path)

                assert "Failed to get audio info" in str(exc_info.value)


class TestAudioQualityAnalysis:
    """Test audio quality analysis."""

    def test_analyze_audio_quality_file_not_found(self):
        """Test quality analysis with non-existent file."""
        with pytest.raises(TTSKitFileError) as exc_info:
            analyze_audio_quality("nonexistent.wav")

        assert "Audio file not found" in str(exc_info.value)

    def test_analyze_audio_quality_success(self):
        """Test successful quality analysis."""
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = os.path.join(temp_dir, "test.wav")

            audio = AudioSegment.silent(duration=1000, frame_rate=44100)
            audio.export(audio_path, format="wav")

            with patch("ttskit.utils.audio.AudioSegment.from_file") as mock_from_file:
                mock_audio = MagicMock()
                mock_audio.__len__ = lambda self: 1000
                mock_audio.frame_rate = 44100
                mock_audio.channels = 2
                mock_audio.sample_width = 2
                mock_audio.max = 1000
                mock_audio.rms = 100
                mock_from_file.return_value = mock_audio

                with patch("os.path.getsize", return_value=1024):
                    quality = analyze_audio_quality(audio_path)

                    assert quality["duration"] == 1.0
                    assert quality["sample_rate"] == 44100
                    assert quality["channels"] == 2
                    assert quality["bitrate"] == 1411200
                    assert quality["max_amplitude"] == 1000
                    assert quality["rms"] == 100
                    assert quality["format"] == ".wav"
                    assert quality["size"] == 1024
                    assert "quality_score" in quality

    def test_analyze_audio_quality_score_calculation(self):
        """Test quality score calculation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = os.path.join(temp_dir, "test.wav")

            audio = AudioSegment.silent(duration=1000, frame_rate=44100)
            audio.export(audio_path, format="wav")

            with patch("ttskit.utils.audio.AudioSegment.from_file") as mock_from_file:
                mock_audio = MagicMock()
                mock_audio.__len__ = lambda self: 1000
                mock_audio.frame_rate = 44100
                mock_audio.channels = 2
                mock_audio.sample_width = 2
                mock_audio.max = 1000
                mock_audio.rms = 100
                mock_from_file.return_value = mock_audio

                with patch("os.path.getsize", return_value=1024):
                    quality = analyze_audio_quality(audio_path)

                    assert quality["quality_score"] == 100

    def test_analyze_audio_quality_score_low_quality(self):
        """Test quality score calculation for low quality audio."""
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = os.path.join(temp_dir, "test.wav")

            audio = AudioSegment.silent(duration=1000, frame_rate=44100)
            audio.export(audio_path, format="wav")

            with patch("ttskit.utils.audio.AudioSegment.from_file") as mock_from_file:
                mock_audio = MagicMock()
                mock_audio.__len__ = lambda self: 1000
                mock_audio.frame_rate = 8000
                mock_audio.channels = 1
                mock_audio.sample_width = 1
                mock_audio.max = 100
                mock_audio.rms = 100
                mock_from_file.return_value = mock_audio

                with patch("os.path.getsize", return_value=1024):
                    quality = analyze_audio_quality(audio_path)

                    assert quality["quality_score"] == 60

    def test_analyze_audio_quality_score_boundary_values(self):
        """Test quality score calculation with boundary values."""
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = os.path.join(temp_dir, "test.wav")

            audio = AudioSegment.silent(duration=1000, frame_rate=44100)
            audio.export(audio_path, format="wav")

            with patch("ttskit.utils.audio.AudioSegment.from_file") as mock_from_file:
                mock_audio = MagicMock()
                mock_audio.__len__ = lambda self: 1000
                mock_audio.frame_rate = 22050
                mock_audio.channels = 2
                mock_audio.sample_width = 1
                mock_audio.max = 1000
                mock_audio.rms = 100
                mock_from_file.return_value = mock_audio

                with patch("os.path.getsize", return_value=1024):
                    quality = analyze_audio_quality(audio_path)

                    assert quality["quality_score"] == 80

    def test_analyze_audio_quality_error(self):
        """Test quality analysis error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = os.path.join(temp_dir, "test.wav")

            audio = AudioSegment.silent(duration=1000, frame_rate=44100)
            audio.export(audio_path, format="wav")

            with patch(
                "ttskit.utils.audio.AudioSegment.from_file",
                side_effect=Exception("Audio error"),
            ):
                with pytest.raises(TTSKitAudioError) as exc_info:
                    analyze_audio_quality(audio_path)

                assert "Failed to analyze audio quality" in str(exc_info.value)


class TestAudioUtilsEdgeCases:
    """Test audio utilities edge cases."""

    def test_to_opus_ogg_empty_filename(self):
        """Test conversion with empty filename."""
        with patch("ttskit.utils.audio.check_ffmpeg_available", return_value=True):
            with pytest.raises(AudioConversionError) as exc_info:
                to_opus_ogg("", "output.ogg")

            assert "Source file not found" in str(exc_info.value)

    def test_to_opus_ogg_none_filename(self):
        """Test conversion with None filename."""
        with patch("ttskit.utils.audio.check_ffmpeg_available", return_value=True):
            with pytest.raises(TypeError) as exc_info:
                to_opus_ogg(None, "output.ogg")

            assert "path should be string" in str(exc_info.value)

    def test_get_audio_info_empty_filename(self):
        """Test get audio info with empty filename."""
        with pytest.raises(TTSKitFileError) as exc_info:
            get_audio_info("")

        assert "Audio file not found" in str(exc_info.value)

    def test_analyze_audio_quality_empty_filename(self):
        """Test quality analysis with empty filename."""
        with pytest.raises(TTSKitFileError) as exc_info:
            analyze_audio_quality("")

        assert "Audio file not found" in str(exc_info.value)

    def test_to_opus_ogg_zero_duration_audio(self):
        """Test conversion with zero duration audio."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = os.path.join(temp_dir, "input.wav")
            output_path = os.path.join(temp_dir, "output.ogg")

            audio = AudioSegment.silent(duration=0, frame_rate=44100)
            audio.export(input_path, format="wav")

            with (
                patch("ttskit.utils.audio.check_ffmpeg_available", return_value=True),
                patch("ttskit.utils.audio.AudioSegment.from_file") as mock_from_file,
            ):
                mock_audio = MagicMock()
                mock_audio.__len__ = lambda self: 0
                mock_audio.set_frame_rate.return_value = mock_audio
                mock_audio.set_channels.return_value = mock_audio
                mock_audio.export.return_value = None
                mock_from_file.return_value = mock_audio

                to_opus_ogg(input_path, output_path)

                mock_from_file.assert_called_once_with(input_path)

    def test_analyze_audio_quality_zero_rms(self):
        """Test quality analysis with zero RMS."""
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = os.path.join(temp_dir, "test.wav")

            audio = AudioSegment.silent(duration=1000, frame_rate=44100)
            audio.export(audio_path, format="wav")

            with patch("ttskit.utils.audio.AudioSegment.from_file") as mock_from_file:
                mock_audio = MagicMock()
                mock_audio.__len__ = lambda self: 1000
                mock_audio.frame_rate = 44100
                mock_audio.channels = 2
                mock_audio.sample_width = 2
                mock_audio.max = 1000
                mock_audio.rms = 0
                mock_from_file.return_value = mock_audio

                with patch("os.path.getsize", return_value=1024):
                    quality = analyze_audio_quality(audio_path)

                    assert (
                        quality["quality_score"] == 90
                    )


class TestAudioUtilsIntegration:
    """Test audio utilities integration."""

    def test_full_conversion_and_analysis_workflow(self):
        """Test full workflow from conversion to analysis."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = os.path.join(temp_dir, "input.wav")
            output_path = os.path.join(temp_dir, "output.ogg")

            audio = AudioSegment.silent(duration=1000, frame_rate=44100)
            audio.export(input_path, format="wav")

            with (
                patch("ttskit.utils.audio.check_ffmpeg_available", return_value=True),
                patch("ttskit.utils.audio.AudioSegment.from_file") as mock_from_file,
            ):
                mock_audio = MagicMock()
                mock_audio.__len__ = lambda self: 1000
                mock_audio.frame_rate = 44100
                mock_audio.channels = 2
                mock_audio.sample_width = 2
                mock_audio.max = 1000
                mock_audio.rms = 100
                mock_audio.set_frame_rate.return_value = mock_audio
                mock_audio.set_channels.return_value = mock_audio
                mock_audio.export.return_value = None
                mock_from_file.return_value = mock_audio

                to_opus_ogg(input_path, output_path)

                with (
                    patch("os.path.getsize", return_value=1024),
                    patch("os.path.exists", return_value=True),
                    patch("pydub.AudioSegment.from_file") as mock_from_file_info,
                ):
                    mock_audio_info = MagicMock()
                    mock_audio_info.__len__ = lambda self: 1000
                    mock_audio_info.frame_rate = 44100
                    mock_audio_info.channels = 2
                    mock_audio_info.sample_width = 2
                    mock_audio_info.max = 1000
                    mock_audio_info.rms = 100
                    mock_from_file_info.return_value = mock_audio_info

                    info = get_audio_info(output_path)
                    assert info["duration"] == 1.0
                    assert info["sample_rate"] == 44100

                    quality = analyze_audio_quality(output_path)
                    assert quality["quality_score"] == 100

    def test_error_propagation(self):
        """Test error propagation through the workflow."""
        with patch("ttskit.utils.audio.check_ffmpeg_available", return_value=False):
            with pytest.raises(FFmpegNotFoundError):
                to_opus_ogg("input.mp3", "output.ogg")

        with pytest.raises(TTSKitFileError):
            get_audio_info("nonexistent.wav")

        with pytest.raises(TTSKitFileError):
            analyze_audio_quality("nonexistent.wav")


class TestAudioUtilsPerformance:
    """Test audio utilities performance."""

    def test_check_ffmpeg_available_performance(self):
        """Test FFmpeg availability check performance."""
        with patch("shutil.which") as mock_which, patch("subprocess.run") as mock_run:
            mock_which.return_value = "/usr/bin/ffmpeg"
            mock_run.return_value.returncode = 0

            import time

            start_time = time.time()
            result = check_ffmpeg_available()
            end_time = time.time()

            assert result is True
            assert (end_time - start_time) < 1.0

    def test_get_audio_info_performance(self):
        """Test audio info extraction performance."""
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = os.path.join(temp_dir, "test.wav")

            audio = AudioSegment.silent(duration=1000, frame_rate=44100)
            audio.export(audio_path, format="wav")

            with patch("ttskit.utils.audio.AudioSegment.from_file") as mock_from_file:
                mock_audio = MagicMock()
                mock_audio.__len__ = lambda self: 1000
                mock_audio.frame_rate = 44100
                mock_audio.channels = 2
                mock_audio.sample_width = 2
                mock_from_file.return_value = mock_audio

                with patch("os.path.getsize", return_value=1024):
                    import time

                    start_time = time.time()
                    info = get_audio_info(audio_path)
                    end_time = time.time()

                    assert info["duration"] == 1.0
                    assert (end_time - start_time) < 0.5
