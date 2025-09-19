"""Simple test for get_audio_info function - Windows compatible.

This test creates minimal audio data and tests the get_audio_info function
without requiring complex audio generation.
"""

from unittest.mock import MagicMock, patch

from ttskit.utils.audio_manager import AudioManager


class TestGetAudioInfoSimple:
    """Simple test cases for get_audio_info function."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.audio_manager = AudioManager()

    def test_get_audio_info_basic_functionality(self):
        """Test basic functionality of get_audio_info.

        Tests that the function returns a dictionary with expected keys
        and handles basic cases.
        """
        # Test with empty data
        empty_data = b""
        info = self.audio_manager.get_audio_info(empty_data)

        assert isinstance(info, dict)
        assert "duration" in info
        assert "sample_rate" in info
        assert "channels" in info
        assert "bitrate" in info
        assert "size" in info
        assert "format" in info

        assert info["size"] == 0
        assert info["format"] == "unknown"

    def test_get_audio_info_with_fake_mp3_header(self):
        """Test get_audio_info with fake MP3 header.

        Tests format detection based on file headers.
        """
        # Create fake MP3 data with proper header
        fake_mp3 = b"\xff\xfb\x90\x00" + b"x" * 1000  # MP3 header + fake data

        info = self.audio_manager.get_audio_info(fake_mp3)

        assert isinstance(info, dict)
        assert info["size"] == len(fake_mp3)
        assert info["format"] == "mp3"

    def test_get_audio_info_with_fake_wav_header(self):
        """Test get_audio_info with fake WAV header.

        Tests WAV format detection.
        """
        # Create fake WAV data with proper header
        fake_wav = b"RIFF\x00\x00\x00\x00WAVE" + b"x" * 1000

        info = self.audio_manager.get_audio_info(fake_wav)

        assert isinstance(info, dict)
        assert info["size"] == len(fake_wav)
        assert info["format"] == "wav"

    def test_get_audio_info_with_fake_ogg_header(self):
        """Test get_audio_info with fake OGG header.

        Tests OGG format detection.
        """
        # Create fake OGG data with proper header
        fake_ogg = b"OggS\x02\x00\x00\x00" + b"x" * 1000

        info = self.audio_manager.get_audio_info(fake_ogg)

        assert isinstance(info, dict)
        assert info["size"] == len(fake_ogg)
        assert info["format"] == "ogg"

    def test_get_audio_info_fallback_on_error(self):
        """Test that get_audio_info falls back to defaults on error.

        Tests error handling when pydub fails to analyze audio.
        """
        invalid_data = b"This is definitely not audio data!"

        # Mock pydub to raise an exception
        with patch("pydub.AudioSegment.from_file") as mock_from_file:
            mock_from_file.side_effect = Exception("Audio analysis failed")

            info = self.audio_manager.get_audio_info(invalid_data)

            # Should fall back to defaults
            assert isinstance(info, dict)
            assert info["duration"] == 0.0
            assert info["sample_rate"] == 48000
            assert info["channels"] == 1
            assert info["bitrate"] == 128
            assert info["size"] == len(invalid_data)
            assert info["format"] == "unknown"

    def test_get_audio_info_return_types(self):
        """Test that get_audio_info returns correct data types.

        Ensures all returned values have the expected types.
        """
        test_data = b"some test data"
        info = self.audio_manager.get_audio_info(test_data)

        # Check data types
        assert isinstance(info["duration"], float)
        assert isinstance(info["sample_rate"], int)
        assert isinstance(info["channels"], int)
        assert isinstance(info["bitrate"], int)
        assert isinstance(info["size"], int)
        assert isinstance(info["format"], str)

        # Check value ranges
        assert info["duration"] >= 0.0
        assert info["sample_rate"] > 0
        assert info["channels"] > 0
        assert info["bitrate"] > 0
        assert info["size"] >= 0

    def test_get_audio_info_with_real_pydub_success(self):
        """Test get_audio_info with successful pydub analysis.

        Mocks pydub to return a successful analysis result.
        """
        test_data = b"fake audio data"

        # Mock AudioSegment to simulate successful analysis
        mock_segment = MagicMock()
        mock_segment.__len__ = MagicMock(return_value=1000)  # 1 second in ms
        mock_segment.frame_rate = 44100
        mock_segment.channels = 2

        with patch("pydub.AudioSegment.from_file", return_value=mock_segment):
            info = self.audio_manager.get_audio_info(test_data)

            assert isinstance(info, dict)
            assert info["duration"] == 1.0  # 1000ms / 1000
            assert info["sample_rate"] == 44100
            assert info["channels"] == 2
            assert info["size"] == len(test_data)
            assert info["bitrate"] > 0  # Calculated bitrate

    def test_get_audio_info_size_calculation(self):
        """Test that size is always correctly calculated.

        Tests that the size field always matches the input data length.
        """
        test_cases = [
            b"",
            b"a",
            b"hello world",
            b"x" * 1000,
            b"y" * 10000,
        ]

        for test_data in test_cases:
            info = self.audio_manager.get_audio_info(test_data)
            assert info["size"] == len(test_data)

    def test_get_audio_info_format_detection_edge_cases(self):
        """Test format detection with edge cases.

        Tests format detection with various header combinations.
        """
        # Test unknown format
        unknown_data = b"completely unknown format data"
        info = self.audio_manager.get_audio_info(unknown_data)
        assert info["format"] == "unknown"

        # Test M4A format
        m4a_data = b"ftypM4A " + b"x" * 100
        info = self.audio_manager.get_audio_info(m4a_data)
        assert info["format"] == "m4a"

        # Test very short data
        short_data = b"\xff"
        info = self.audio_manager.get_audio_info(short_data)
        assert info["format"] == "unknown"  # Too short for header detection
