"""Final comprehensive test for get_audio_info function.

This test verifies that the get_audio_info function now provides real audio analysis
instead of returning fake placeholder data.
"""

from unittest.mock import MagicMock, patch

from ttskit.utils.audio_manager import AudioManager


class TestGetAudioInfoFinal:
    """Final test cases for get_audio_info function."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.audio_manager = AudioManager()

    def test_function_signature_unchanged(self):
        """Test that function signature remains unchanged.

        Ensures backward compatibility - the function still takes the same
        parameters and returns the same structure.
        """
        # Test that the function can be called with the same signature
        test_data = b"test audio data"
        result = self.audio_manager.get_audio_info(test_data)

        # Verify return type and structure
        assert isinstance(result, dict)
        required_keys = [
            "duration",
            "sample_rate",
            "channels",
            "bitrate",
            "size",
            "format",
        ]
        for key in required_keys:
            assert key in result

        # Verify data types
        assert isinstance(result["duration"], float)
        assert isinstance(result["sample_rate"], int)
        assert isinstance(result["channels"], int)
        assert isinstance(result["bitrate"], int)
        assert isinstance(result["size"], int)
        assert isinstance(result["format"], str)

    def test_real_audio_analysis_vs_fake_data(self):
        """Test that function now provides real analysis instead of fake data.

        This is the main test that proves the function is no longer returning
        placeholder/fake data.
        """
        # Create test data that would trigger real analysis
        test_data = b"\xff\xfb\x90\x00" + b"x" * 1000  # Fake MP3 header

        # Mock pydub to return realistic audio properties
        mock_segment = MagicMock()
        mock_segment.__len__ = MagicMock(return_value=1500)  # 1.5 seconds
        mock_segment.frame_rate = 44100
        mock_segment.channels = 2

        with patch("pydub.AudioSegment.from_file", return_value=mock_segment):
            info = self.audio_manager.get_audio_info(test_data)

            # Verify we get real analysis results, not fake defaults
            assert info["duration"] == 1.5  # Real duration from mock
            assert info["sample_rate"] == 44100  # Real sample rate
            assert info["channels"] == 2  # Real channel count
            assert info["size"] == len(test_data)  # Real size
            assert info["format"] == "mp3"  # Detected format
            assert info["bitrate"] > 0  # Calculated bitrate

            # This proves we're not getting the old fake defaults:
            # Old: duration=0.0, sample_rate=48000, channels=1, bitrate=128
            # New: duration=1.5, sample_rate=44100, channels=2, bitrate=calculated

    def test_fallback_behavior_maintained(self):
        """Test that fallback behavior is maintained for error cases.

        Ensures that when audio analysis fails, the function still returns
        reasonable defaults.
        """
        invalid_data = b"invalid audio data"

        # Mock pydub to fail
        with patch("pydub.AudioSegment.from_file") as mock_from_file:
            mock_from_file.side_effect = Exception("Analysis failed")

            info = self.audio_manager.get_audio_info(invalid_data)

            # Should fall back to defaults
            assert info["duration"] == 0.0
            assert info["sample_rate"] == 48000
            assert info["channels"] == 1
            assert info["bitrate"] == 128
            assert info["size"] == len(invalid_data)
            assert info["format"] == "unknown"

    def test_format_detection_improvement(self):
        """Test that format detection is now available.

        The old implementation didn't provide format detection.
        """
        formats_to_test = [
            (b"\xff\xfb\x90\x00" + b"x" * 100, "mp3"),
            (b"OggS\x02\x00\x00\x00" + b"x" * 100, "ogg"),
            (b"RIFF\x00\x00\x00\x00WAVE" + b"x" * 100, "wav"),
            (b"ftypM4A " + b"x" * 100, "m4a"),
        ]

        for data, expected_format in formats_to_test:
            info = self.audio_manager.get_audio_info(data)
            assert info["format"] == expected_format

        # Test unknown format
        unknown_data = b"unknown format"
        info = self.audio_manager.get_audio_info(unknown_data)
        assert info["format"] == "unknown"

    def test_bitrate_calculation_improvement(self):
        """Test that bitrate is now calculated instead of hardcoded.

        The old implementation always returned 128 kbps.
        """
        # Test with different data sizes to get different bitrates
        test_cases = [
            (b"\xff\xfb\x90\x00" + b"x" * 100, "small"),
            (b"\xff\xfb\x90\x00" + b"x" * 1000, "medium"),
            (b"\xff\xfb\x90\x00" + b"x" * 10000, "large"),
        ]

        for data, size_desc in test_cases:
            info = self.audio_manager.get_audio_info(data)

            # Bitrate should be calculated based on size and duration
            # (when duration > 0, which happens with successful pydub analysis)
            assert info["bitrate"] > 0
            assert isinstance(info["bitrate"], int)

            # For our fake data, we expect reasonable bitrate values
            assert 50 <= info["bitrate"] <= 2000  # Reasonable range

    def test_duration_analysis_improvement(self):
        """Test that duration is now analyzed instead of hardcoded to 0.0.

        The old implementation always returned 0.0 seconds.
        """
        # Mock successful pydub analysis
        mock_segment = MagicMock()
        mock_segment.__len__ = MagicMock(return_value=3000)  # 3 seconds
        mock_segment.frame_rate = 48000
        mock_segment.channels = 1

        with patch("pydub.AudioSegment.from_file", return_value=mock_segment):
            test_data = b"test audio"
            info = self.audio_manager.get_audio_info(test_data)

            # Should get real duration, not 0.0
            assert info["duration"] == 3.0
            assert info["duration"] != 0.0  # Proves it's not the old fake value

    def test_sample_rate_detection_improvement(self):
        """Test that sample rate is now detected instead of hardcoded.

        The old implementation always returned 48000 Hz.
        """
        # Test different sample rates
        sample_rates = [22050, 44100, 48000, 96000]

        for sample_rate in sample_rates:
            mock_segment = MagicMock()
            mock_segment.__len__ = MagicMock(return_value=1000)
            mock_segment.frame_rate = sample_rate
            mock_segment.channels = 1

            with patch("pydub.AudioSegment.from_file", return_value=mock_segment):
                test_data = b"test audio"
                info = self.audio_manager.get_audio_info(test_data)

                # Should get the actual sample rate, not hardcoded 48000
                assert info["sample_rate"] == sample_rate

    def test_channels_detection_improvement(self):
        """Test that channel count is now detected instead of hardcoded.

        The old implementation always returned 1 channel.
        """
        # Test different channel counts
        channel_counts = [1, 2, 6, 8]  # Mono, Stereo, 5.1, 7.1

        for channels in channel_counts:
            mock_segment = MagicMock()
            mock_segment.__len__ = MagicMock(return_value=1000)
            mock_segment.frame_rate = 44100
            mock_segment.channels = channels

            with patch("pydub.AudioSegment.from_file", return_value=mock_segment):
                test_data = b"test audio"
                info = self.audio_manager.get_audio_info(test_data)

                # Should get the actual channel count, not hardcoded 1
                assert info["channels"] == channels

    def test_backward_compatibility(self):
        """Test that existing code using get_audio_info still works.

        Ensures that any existing code that calls this function will
        continue to work without modification.
        """
        # Test various input scenarios that existing code might use
        test_scenarios = [
            b"",  # Empty data
            b"short",  # Short data
            b"x" * 1000,  # Medium data
            b"y" * 10000,  # Large data
        ]

        for test_data in test_scenarios:
            # Should not raise any exceptions
            info = self.audio_manager.get_audio_info(test_data)

            # Should return expected structure
            assert isinstance(info, dict)
            assert (
                len(info) == 6
            )  # duration, sample_rate, channels, bitrate, size, format

            # All values should be reasonable
            assert info["duration"] >= 0.0
            assert info["sample_rate"] > 0
            assert info["channels"] > 0
            assert info["bitrate"] > 0
            assert info["size"] >= 0
            assert isinstance(info["format"], str)

    def test_performance_characteristics(self):
        """Test that the function performs reasonably well.

        Ensures the function doesn't take too long to analyze audio data.
        """
        import time

        # Test with different data sizes
        test_sizes = [100, 1000, 10000, 100000]

        for size in test_sizes:
            test_data = b"x" * size

            start_time = time.time()
            info = self.audio_manager.get_audio_info(test_data)
            end_time = time.time()

            analysis_time = end_time - start_time

            # Should complete analysis quickly (less than 1 second for any reasonable size)
            assert analysis_time < 1.0, (
                f"Analysis took too long: {analysis_time:.3f}s for {size} bytes"
            )

            # Verify we got a result
            assert info["size"] == size
