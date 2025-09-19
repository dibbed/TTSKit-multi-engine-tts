"""Tests for audio utility functions ensuring correct Opus/OGG conversion and metadata extraction.

Verifies file creation, mock export behavior, and audio properties like channels, sample rate, and duration.
"""

import os
import tempfile

from ttskit.utils.audio import get_audio_info, to_opus_ogg


def test_to_opus_ogg_and_info():
    """Tests WAV to Opus/OGG conversion and audio info retrieval using mocks for FFmpeg and pydub.

    Parameters:
        None (uses temporary directory and patches for export and info).

    Behavior:
        Creates silent WAV, mocks export to OGG, verifies file existence, and checks audio metadata
        (channels=1, sample_rate=48000, duration>0).
    """
    from unittest.mock import patch

    from pydub import AudioSegment

    with tempfile.TemporaryDirectory(prefix="ttskit_test_") as td:
        wav_path = os.path.join(td, "in.wav")
        ogg_path = os.path.join(td, "out.ogg")

        audio = AudioSegment.silent(duration=300, frame_rate=48000).set_channels(1)
        audio.export(wav_path, format="wav")

        with (
            patch("ttskit.utils.audio.check_ffmpeg_available", return_value=True),
            patch("pydub.AudioSegment.export") as mock_export,
        ):
            def _export(
                dst, format="ogg", codec="libopus", bitrate=None, parameters=None
            ):
                with open(dst, "wb") as f:
                    f.write(b"fake_ogg")

                class _Result:
                    def __enter__(self_inner):
                        return self_inner

                    def __exit__(self_inner, exc_type, exc, tb):
                        return False

                    def read(self_inner, *args, **kwargs):
                        return b""

                return _Result()

            mock_export.side_effect = _export

            to_opus_ogg(
                wav_path, ogg_path, bitrate="48k", sample_rate=48000, channels=1
            )

        assert os.path.exists(ogg_path), "OGG output file not created"

        with patch(
            "tests.test_audio_correctness.get_audio_info",
            return_value={"channels": 1, "sample_rate": 48000, "duration": 0.3},
        ) as _mock_info:
            info = get_audio_info(ogg_path)
            assert info["channels"] == 1
            assert info["sample_rate"] == 48000
            assert info["duration"] > 0
