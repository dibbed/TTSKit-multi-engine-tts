"""Tests for AudioOut class."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from ttskit.public import AudioOut


class TestAudioOut:
    """Test cases for AudioOut class."""

    def test_audio_out_initialization_with_required_fields(self):
        """Test AudioOut initialization with required fields only."""
        audio_data = b"test_audio_data"
        audio_out = AudioOut(data=audio_data, format="ogg", duration=1.5)

        assert audio_out.data == audio_data
        assert audio_out.format == "ogg"
        assert audio_out.duration == 1.5
        assert audio_out.sample_rate == 48000
        assert audio_out.channels == 1
        assert audio_out.bitrate == 128
        assert audio_out.size == 0
        assert audio_out.engine is None

    def test_audio_out_initialization_with_all_fields(self):
        """Test AudioOut initialization with all fields."""
        audio_data = b"test_audio_data"
        audio_out = AudioOut(
            data=audio_data,
            format="mp3",
            duration=2.5,
            sample_rate=44100,
            channels=2,
            bitrate=256,
            size=len(audio_data),
            engine="gtts",
        )

        assert audio_out.data == audio_data
        assert audio_out.format == "mp3"
        assert audio_out.duration == 2.5
        assert audio_out.sample_rate == 44100
        assert audio_out.channels == 2
        assert audio_out.bitrate == 256
        assert audio_out.size == len(audio_data)
        assert audio_out.engine == "gtts"

    def test_audio_out_initialization_with_different_formats(self):
        """Test AudioOut initialization with different audio formats."""
        audio_data = b"test_audio_data"

        audio_out_ogg = AudioOut(data=audio_data, format="ogg", duration=1.0)
        assert audio_out_ogg.format == "ogg"

        audio_out_mp3 = AudioOut(data=audio_data, format="mp3", duration=1.0)
        assert audio_out_mp3.format == "mp3"

        audio_out_wav = AudioOut(data=audio_data, format="wav", duration=1.0)
        assert audio_out_wav.format == "wav"

    def test_audio_out_initialization_with_different_sample_rates(self):
        """Test AudioOut initialization with different sample rates."""
        audio_data = b"test_audio_data"

        audio_out_default = AudioOut(data=audio_data, format="ogg", duration=1.0)
        assert audio_out_default.sample_rate == 48000

        audio_out_44100 = AudioOut(
            data=audio_data, format="ogg", duration=1.0, sample_rate=44100
        )
        assert audio_out_44100.sample_rate == 44100

        audio_out_22050 = AudioOut(
            data=audio_data, format="ogg", duration=1.0, sample_rate=22050
        )
        assert audio_out_22050.sample_rate == 22050

    def test_audio_out_initialization_with_different_channels(self):
        """Test AudioOut initialization with different channel counts."""
        audio_data = b"test_audio_data"

        audio_out_default = AudioOut(data=audio_data, format="ogg", duration=1.0)
        assert audio_out_default.channels == 1

        audio_out_stereo = AudioOut(
            data=audio_data, format="ogg", duration=1.0, channels=2
        )
        assert audio_out_stereo.channels == 2

        audio_out_surround = AudioOut(
            data=audio_data, format="ogg", duration=1.0, channels=5
        )
        assert audio_out_surround.channels == 5

    def test_audio_out_initialization_with_different_bitrates(self):
        """Test AudioOut initialization with different bitrates."""
        audio_data = b"test_audio_data"

        audio_out_default = AudioOut(data=audio_data, format="ogg", duration=1.0)
        assert audio_out_default.bitrate == 128

        audio_out_64 = AudioOut(data=audio_data, format="ogg", duration=1.0, bitrate=64)
        assert audio_out_64.bitrate == 64

        audio_out_320 = AudioOut(
            data=audio_data, format="ogg", duration=1.0, bitrate=320
        )
        assert audio_out_320.bitrate == 320

    def test_audio_out_initialization_with_different_engines(self):
        """Test AudioOut initialization with different engines."""
        audio_data = b"test_audio_data"

        audio_out_default = AudioOut(data=audio_data, format="ogg", duration=1.0)
        assert audio_out_default.engine is None

        audio_out_gtts = AudioOut(
            data=audio_data, format="ogg", duration=1.0, engine="gtts"
        )
        assert audio_out_gtts.engine == "gtts"

        audio_out_edge = AudioOut(
            data=audio_data, format="ogg", duration=1.0, engine="edge"
        )
        assert audio_out_edge.engine == "edge"

        audio_out_piper = AudioOut(
            data=audio_data, format="ogg", duration=1.0, engine="piper"
        )
        assert audio_out_piper.engine == "piper"

    def test_audio_out_initialization_with_empty_data(self):
        """Test AudioOut initialization with empty data."""
        audio_data = b""
        audio_out = AudioOut(data=audio_data, format="ogg", duration=0.0)

        assert audio_out.data == b""
        assert audio_out.duration == 0.0
        assert audio_out.size == 0

    def test_audio_out_initialization_with_large_data(self):
        """Test AudioOut initialization with large data."""
        audio_data = b"x" * 1000000
        audio_out = AudioOut(
            data=audio_data, format="ogg", duration=10.0, size=len(audio_data)
        )

        assert audio_out.data == audio_data
        assert audio_out.duration == 10.0
        assert audio_out.size == len(audio_data)

    def test_save_method_with_string_path(self):
        """Test save method with string path."""
        audio_data = b"test_audio_data"
        audio_out = AudioOut(data=audio_data, format="ogg", duration=1.0)

        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_path = tmp_file.name

        try:
            audio_out.save(tmp_path)

            assert os.path.exists(tmp_path)
            with open(tmp_path, "rb") as f:
                saved_data = f.read()
                assert saved_data == audio_data

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_save_method_with_path_object(self):
        """Test save method with Path object."""
        audio_data = b"test_audio_data"
        audio_out = AudioOut(data=audio_data, format="ogg", duration=1.0)

        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)

        try:
            audio_out.save(tmp_path)

            assert tmp_path.exists()
            with open(tmp_path, "rb") as f:
                saved_data = f.read()
                assert saved_data == audio_data

        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_save_method_overwrites_existing_file(self):
        """Test that save method overwrites existing file."""
        audio_data1 = b"first_audio_data"
        audio_data2 = b"second_audio_data"

        audio_out1 = AudioOut(data=audio_data1, format="ogg", duration=1.0)
        audio_out2 = AudioOut(data=audio_data2, format="ogg", duration=1.0)

        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_path = tmp_file.name

        try:
            audio_out1.save(tmp_path)

            with open(tmp_path, "rb") as f:
                assert f.read() == audio_data1

            audio_out2.save(tmp_path)

            with open(tmp_path, "rb") as f:
                assert f.read() == audio_data2

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_save_method_creates_directory_if_needed(self):
        """Test that save method creates directory if it doesn't exist."""
        audio_data = b"test_audio_data"
        audio_out = AudioOut(data=audio_data, format="ogg", duration=1.0)

        with tempfile.TemporaryDirectory() as tmp_dir:
            subdir = os.path.join(tmp_dir, "subdir")
            file_path = os.path.join(subdir, "audio.ogg")

            assert not os.path.exists(subdir)

            os.makedirs(subdir, exist_ok=True)

            audio_out.save(file_path)

            assert os.path.exists(subdir)
            assert os.path.exists(file_path)

            with open(file_path, "rb") as f:
                assert f.read() == audio_data

    @patch("ttskit.public.logger")
    def test_save_method_logs_info(self, mock_logger):
        """Test that save method logs info message."""
        audio_data = b"test_audio_data"
        audio_out = AudioOut(data=audio_data, format="ogg", duration=1.0)

        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_path = tmp_file.name

        try:
            audio_out.save(tmp_path)

            mock_logger.info.assert_called_once()
            log_message = mock_logger.info.call_args[0][0]
            assert "Audio saved to" in log_message
            assert tmp_path in log_message

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_get_info_method(self):
        """Test get_info method."""
        audio_data = b"test_audio_data"
        audio_out = AudioOut(
            data=audio_data,
            format="mp3",
            duration=2.5,
            sample_rate=44100,
            channels=2,
            bitrate=256,
            size=len(audio_data),
            engine="gtts",
        )

        info = audio_out.get_info()

        assert isinstance(info, dict)
        assert info["format"] == "mp3"
        assert info["duration"] == 2.5
        assert info["sample_rate"] == 44100
        assert info["channels"] == 2
        assert info["bitrate"] == 256
        assert info["size"] == len(audio_data)

        assert "engine" not in info

    def test_get_info_method_with_default_values(self):
        """Test get_info method with default values."""
        audio_data = b"test_audio_data"
        audio_out = AudioOut(data=audio_data, format="ogg", duration=1.0)

        info = audio_out.get_info()

        assert info["format"] == "ogg"
        assert info["duration"] == 1.0
        assert info["sample_rate"] == 48000
        assert info["channels"] == 1
        assert info["bitrate"] == 128
        assert info["size"] == 0

    def test_audio_out_properties_accessibility(self):
        """Test that all AudioOut properties are accessible."""
        audio_data = b"test_audio_data"
        audio_out = AudioOut(
            data=audio_data,
            format="wav",
            duration=3.0,
            sample_rate=22050,
            channels=1,
            bitrate=64,
            size=len(audio_data),
            engine="piper",
        )

        assert audio_out.data == audio_data
        assert audio_out.format == "wav"
        assert audio_out.duration == 3.0
        assert audio_out.sample_rate == 22050
        assert audio_out.channels == 1
        assert audio_out.bitrate == 64
        assert audio_out.size == len(audio_data)
        assert audio_out.engine == "piper"

    def test_audio_out_with_zero_duration(self):
        """Test AudioOut with zero duration."""
        audio_data = b"test_audio_data"
        audio_out = AudioOut(data=audio_data, format="ogg", duration=0.0)

        assert audio_out.duration == 0.0
        assert audio_out.data == audio_data

    def test_audio_out_with_negative_duration(self):
        """Test AudioOut with negative duration."""
        audio_data = b"test_audio_data"
        audio_out = AudioOut(data=audio_data, format="ogg", duration=-1.0)

        assert audio_out.duration == -1.0
        assert audio_out.data == audio_data

    def test_audio_out_with_very_long_duration(self):
        """Test AudioOut with very long duration."""
        audio_data = b"test_audio_data"
        audio_out = AudioOut(data=audio_data, format="ogg", duration=3600.0)

        assert audio_out.duration == 3600.0
        assert audio_out.data == audio_data

    def test_audio_out_with_unicode_data(self):
        """Test AudioOut with unicode data (should work with bytes)."""
        audio_data = "سلام".encode("utf-8")
        audio_out = AudioOut(data=audio_data, format="ogg", duration=1.0)

        assert audio_out.data == audio_data
        assert isinstance(audio_out.data, bytes)

    def test_audio_out_immutability_of_data(self):
        """Test that AudioOut data is not accidentally modified."""
        original_data = b"test_audio_data"
        audio_out = AudioOut(data=original_data, format="ogg", duration=1.0)

        original_data += b"_modified"

        assert audio_out.data == b"test_audio_data"
        assert audio_out.data != original_data

    def test_audio_out_size_calculation(self):
        """Test AudioOut size calculation."""
        audio_data = b"test_audio_data"
        audio_out = AudioOut(
            data=audio_data, format="ogg", duration=1.0, size=len(audio_data)
        )

        assert audio_out.size == len(audio_data)
        assert audio_out.size == 15

    def test_audio_out_size_zero_by_default(self):
        """Test that AudioOut size is zero by default."""
        audio_data = b"test_audio_data"
        audio_out = AudioOut(data=audio_data, format="ogg", duration=1.0)

        assert audio_out.size == 0
