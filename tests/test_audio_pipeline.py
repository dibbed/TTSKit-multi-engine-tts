"""Comprehensive tests for AudioPipeline module."""

import asyncio
from unittest.mock import MagicMock, mock_open, patch

import numpy as np
import pytest

from ttskit.audio.pipeline import AudioPipeline, convert_format, process_audio


@pytest.fixture(autouse=True)
def mock_audio_libraries():
    """Mock audio libraries to prevent import errors."""
    import sys

    mock_librosa = MagicMock()
    mock_librosa.resample.return_value = np.array(
        [1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float32
    )
    mock_librosa.effects.trim.return_value = (
        np.array([0.1, 0.2, 0.1], dtype=np.float32),
        0,
    )

    mock_sf = MagicMock()
    mock_sf.read.return_value = (np.array([0.1, 0.2, 0.1], dtype=np.float32), 22050)

    def mock_write(filepath, data, samplerate, format=None):
        if hasattr(filepath, "write"):
            filepath.write(b"fake_audio_data_for_testing")
            return
        with open(filepath, "wb") as f:
            f.write(b"fake_audio_data_for_testing")

    mock_sf.write.side_effect = mock_write

    mock_pydub = MagicMock()
    mock_audio_segment = MagicMock()
    mock_audio_segment.from_file.return_value = mock_audio_segment
    mock_audio_segment.__add__.return_value = mock_audio_segment
    mock_audio_segment.__iadd__.return_value = mock_audio_segment

    mock_audio_segment.frame_rate = 22050
    mock_audio_segment.channels = 1
    mock_audio_segment.sample_width = 2
    mock_audio_segment.duration_seconds = 0.1

    mock_export_result = MagicMock()
    mock_export_result.read.return_value = (
        b"fake_merged_audio_data" * 2100
    )
    mock_export_result.__enter__.return_value = mock_export_result
    mock_export_result.__exit__.return_value = None

    mock_audio_segment.export.return_value = mock_export_result

    mock_audio_segment.__len__.return_value = 2000
    mock_audio_segment.__getitem__.return_value = mock_audio_segment

    mock_pydub.AudioSegment = mock_audio_segment

    sys.modules["librosa"] = mock_librosa
    sys.modules["librosa.effects"] = mock_librosa.effects
    sys.modules["soundfile"] = mock_sf
    sys.modules["pydub"] = mock_pydub
    sys.modules["pydub.AudioSegment"] = mock_audio_segment

    with (
        patch("ttskit.audio.pipeline.LIBROSA_AVAILABLE", True),
        patch("ttskit.audio.pipeline.SOUNDFILE_AVAILABLE", True),
        patch("ttskit.audio.pipeline.PYDUB_AVAILABLE", True),
        patch("ttskit.audio.pipeline.AudioSegment", mock_audio_segment),
    ):
        import ttskit.audio.pipeline

        original_sf = getattr(ttskit.audio.pipeline, "sf", None)
        ttskit.audio.pipeline.sf = mock_sf

        try:
            yield mock_librosa, mock_sf, mock_pydub
        finally:
            if original_sf is not None:
                ttskit.audio.pipeline.sf = original_sf
            elif hasattr(ttskit.audio.pipeline, "sf"):
                delattr(ttskit.audio.pipeline, "sf")

    for module in ["librosa", "librosa.effects", "soundfile", "pydub"]:
        if module in sys.modules:
            del sys.modules[module]


@pytest.fixture
def sample_wav_data():
    """Create sample WAV audio data."""
    sample_rate = 22050
    duration = 1.0
    frequency = 440

    t = np.linspace(0, duration, int(sample_rate * duration), False)
    audio_data = np.sin(2 * np.pi * frequency * t) * 0.3

    audio_data = (audio_data * 32767).astype(np.int16)

    import io
    import wave

    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data.tobytes())

    wav_data = wav_buffer.getvalue()

    return wav_data


class TestAudioPipeline:
    """Test cases for AudioPipeline class."""

    @pytest.fixture
    def pipeline(self):
        """Create AudioPipeline instance for testing."""
        return AudioPipeline()

    def test_pipeline_initialization(self, pipeline):
        """Test pipeline initialization."""
        assert pipeline.sample_rate == 22050
        assert pipeline.channels == 1
        assert pipeline.bit_depth == 16
        assert isinstance(pipeline._available, bool)

    def test_check_dependencies(self, pipeline):
        """Test dependency checking."""
        available = pipeline._check_dependencies()
        assert isinstance(available, bool)

    def test_check_dependencies_numpy_unavailable(self, pipeline):
        """Test dependency checking when numpy is unavailable."""
        with patch("ttskit.audio.pipeline.NUMPY_AVAILABLE", False):
            available = pipeline._check_dependencies()
            assert available is False

    def test_check_dependencies_soundfile_unavailable(self, pipeline):
        """Test dependency checking when soundfile is unavailable."""
        with patch("ttskit.audio.pipeline.SOUNDFILE_AVAILABLE", False):
            available = pipeline._check_dependencies()
            assert available is False

    def test_check_dependencies_librosa_unavailable(self, pipeline):
        """Test dependency checking when librosa is unavailable."""
        with patch("ttskit.audio.pipeline.LIBROSA_AVAILABLE", False):
            available = pipeline._check_dependencies()
            assert isinstance(available, bool)

    def test_check_dependencies_pydub_unavailable(self, pipeline):
        """Test dependency checking when pydub is unavailable."""
        with patch("ttskit.audio.pipeline.PYDUB_AVAILABLE", False):
            available = pipeline._check_dependencies()
            assert isinstance(available, bool)

    def test_check_dependencies_all_unavailable(self, pipeline):
        """Test dependency checking when all dependencies are unavailable."""
        with (
            patch("ttskit.audio.pipeline.NUMPY_AVAILABLE", False),
            patch("ttskit.audio.pipeline.SOUNDFILE_AVAILABLE", False),
            patch("ttskit.audio.pipeline.LIBROSA_AVAILABLE", False),
            patch("ttskit.audio.pipeline.PYDUB_AVAILABLE", False),
        ):
            available = pipeline._check_dependencies()
            assert available is False

    def test_check_dependencies_minimal_required(self, pipeline):
        """Test dependency checking with minimal required dependencies."""
        with (
            patch("ttskit.audio.pipeline.NUMPY_AVAILABLE", True),
            patch("ttskit.audio.pipeline.SOUNDFILE_AVAILABLE", True),
            patch("ttskit.audio.pipeline.LIBROSA_AVAILABLE", False),
            patch("ttskit.audio.pipeline.PYDUB_AVAILABLE", False),
        ):
            available = pipeline._check_dependencies()
            assert available is True

    def test_check_dependencies_all_available(self, pipeline):
        """Test dependency checking when all dependencies are available."""
        with (
            patch("ttskit.audio.pipeline.NUMPY_AVAILABLE", True),
            patch("ttskit.audio.pipeline.SOUNDFILE_AVAILABLE", True),
            patch("ttskit.audio.pipeline.LIBROSA_AVAILABLE", True),
            patch("ttskit.audio.pipeline.PYDUB_AVAILABLE", True),
        ):
            available = pipeline._check_dependencies()
            assert available is True

    def test_check_dependencies_numpy_only(self, pipeline):
        """Test dependency checking with only numpy available."""
        with (
            patch("ttskit.audio.pipeline.NUMPY_AVAILABLE", True),
            patch("ttskit.audio.pipeline.SOUNDFILE_AVAILABLE", False),
            patch("ttskit.audio.pipeline.LIBROSA_AVAILABLE", False),
            patch("ttskit.audio.pipeline.PYDUB_AVAILABLE", False),
        ):
            available = pipeline._check_dependencies()
            assert available is False

    def test_check_dependencies_soundfile_only(self, pipeline):
        """Test dependency checking with only soundfile available."""
        with (
            patch("ttskit.audio.pipeline.NUMPY_AVAILABLE", False),
            patch("ttskit.audio.pipeline.SOUNDFILE_AVAILABLE", True),
            patch("ttskit.audio.pipeline.LIBROSA_AVAILABLE", False),
            patch("ttskit.audio.pipeline.PYDUB_AVAILABLE", False),
        ):
            available = pipeline._check_dependencies()
            assert available is False

    def test_check_dependencies_numpy_and_librosa(self, pipeline):
        """Test dependency checking with numpy and librosa available."""
        with (
            patch("ttskit.audio.pipeline.NUMPY_AVAILABLE", True),
            patch("ttskit.audio.pipeline.SOUNDFILE_AVAILABLE", False),
            patch("ttskit.audio.pipeline.LIBROSA_AVAILABLE", True),
            patch("ttskit.audio.pipeline.PYDUB_AVAILABLE", False),
        ):
            available = pipeline._check_dependencies()
            assert available is False

    def test_check_dependencies_soundfile_and_pydub(self, pipeline):
        """Test dependency checking with soundfile and pydub available."""
        with (
            patch("ttskit.audio.pipeline.NUMPY_AVAILABLE", False),
            patch("ttskit.audio.pipeline.SOUNDFILE_AVAILABLE", True),
            patch("ttskit.audio.pipeline.LIBROSA_AVAILABLE", False),
            patch("ttskit.audio.pipeline.PYDUB_AVAILABLE", True),
        ):
            available = pipeline._check_dependencies()
            assert available is False

    def test_check_dependencies_numpy_soundfile_librosa(self, pipeline):
        """Test dependency checking with numpy, soundfile, and librosa available."""
        with (
            patch("ttskit.audio.pipeline.NUMPY_AVAILABLE", True),
            patch("ttskit.audio.pipeline.SOUNDFILE_AVAILABLE", True),
            patch("ttskit.audio.pipeline.LIBROSA_AVAILABLE", True),
            patch("ttskit.audio.pipeline.PYDUB_AVAILABLE", False),
        ):
            available = pipeline._check_dependencies()
            assert available is True

    def test_check_dependencies_numpy_soundfile_pydub(self, pipeline):
        """Test dependency checking with numpy, soundfile, and pydub available."""
        with (
            patch("ttskit.audio.pipeline.NUMPY_AVAILABLE", True),
            patch("ttskit.audio.pipeline.SOUNDFILE_AVAILABLE", True),
            patch("ttskit.audio.pipeline.LIBROSA_AVAILABLE", False),
            patch("ttskit.audio.pipeline.PYDUB_AVAILABLE", True),
        ):
            available = pipeline._check_dependencies()
            assert available is True

    def test_is_available(self, pipeline):
        """Test availability check."""
        available = pipeline.is_available()
        assert isinstance(available, bool)

    @pytest.mark.asyncio
    async def test_process_audio_not_available(self, pipeline):
        """Test process_audio when pipeline is not available."""
        with patch.object(pipeline, "is_available", return_value=False):
            with pytest.raises(RuntimeError, match="Audio pipeline not available"):
                await pipeline.process_audio(b"test_data")

    @pytest.mark.asyncio
    async def test_process_audio_basic(self, pipeline, sample_wav_data):
        """Test basic audio processing."""
        if not pipeline.is_available():
            pytest.skip("Audio pipeline not available - missing dependencies")

        result = await pipeline.process_audio(
            sample_wav_data,
            input_format="wav",
            output_format="wav",
            normalize=True,
            trim_silence=True,
        )

        assert isinstance(result, bytes)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_process_audio_with_effects(self, pipeline, sample_wav_data):
        """Test audio processing with effects."""
        if not pipeline.is_available():
            pytest.skip("Audio pipeline not available - missing dependencies")

        effects = {"volume": 0.8, "fade_in": 0.1, "fade_out": 0.1}

        result = await pipeline.process_audio(
            sample_wav_data, input_format="wav", output_format="wav", effects=effects
        )

        assert isinstance(result, bytes)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_process_audio_sample_rate_conversion(
        self, pipeline, sample_wav_data
    ):
        """Test audio processing with sample rate conversion."""
        if not pipeline.is_available():
            pytest.skip("Audio pipeline not available - missing dependencies")

        result = await pipeline.process_audio(
            sample_wav_data, input_format="wav", output_format="wav", sample_rate=44100
        )

        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_load_audio_not_available(self, pipeline):
        """Test _load_audio when dependencies not available."""
        with patch("ttskit.audio.pipeline.NUMPY_AVAILABLE", False):
            with pytest.raises(
                RuntimeError, match="Required audio libraries not available"
            ):
                pipeline._load_audio(b"test_data", "wav")

    def test_save_audio_not_available(self, pipeline):
        """Test _save_audio when dependencies not available."""
        with patch("ttskit.audio.pipeline.NUMPY_AVAILABLE", False):
            with pytest.raises(
                RuntimeError, match="Required audio libraries not available"
            ):
                pipeline._save_audio(np.array([1, 2, 3]), 22050, "wav")

    def test_resample_audio_without_librosa(self, pipeline):
        """Test resampling without librosa."""
        audio = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float32)

        with patch("ttskit.audio.pipeline.LIBROSA_AVAILABLE", False):
            result = pipeline._resample_audio(audio, 22050, 44100)

        assert isinstance(result, np.ndarray)
        assert len(result) > 0

    def test_normalize_audio_without_numpy(self, pipeline):
        """Test normalization without numpy."""
        with patch("ttskit.audio.pipeline.NUMPY_AVAILABLE", False):
            audio = [1, 2, 3, 4, 5]
            result = pipeline._normalize_audio(audio)
            assert result == audio

    def test_normalize_audio_with_numpy(self, pipeline):
        """Test normalization with numpy."""
        if not pipeline.is_available():
            pytest.skip("Audio pipeline not available - missing dependencies")

        audio = np.array([0.5, 1.0, -0.8, 0.3])
        result = pipeline._normalize_audio(audio)

        assert isinstance(result, np.ndarray)
        assert np.max(np.abs(result)) <= 1.0

    def test_normalize_audio_zero_max(self, pipeline):
        """Test normalization with zero max value."""
        if not pipeline.is_available():
            pytest.skip("Audio pipeline not available - missing dependencies")

        audio = np.array([0, 0, 0, 0])
        result = pipeline._normalize_audio(audio)

        assert isinstance(result, np.ndarray)
        assert np.array_equal(result, audio)

    def test_trim_silence_without_librosa(self, pipeline):
        """Test silence trimming without librosa."""
        audio = np.array([0, 0, 0.1, 0.2, 0.1, 0, 0])

        with patch("ttskit.audio.pipeline.LIBROSA_AVAILABLE", False):
            result = pipeline._trim_silence(audio, 22050)

        assert isinstance(result, np.ndarray)
        assert len(result) > 0

    def test_trim_silence_all_silence(self, pipeline):
        """Test trimming when audio is all silence."""
        audio = np.array([0, 0, 0, 0])

        with patch("ttskit.audio.pipeline.LIBROSA_AVAILABLE", False):
            result = pipeline._trim_silence(audio, 22050)

        assert isinstance(result, np.ndarray)
        assert len(result) > 0

    def test_apply_effects_without_numpy(self, pipeline):
        """Test applying effects without numpy."""
        with patch("ttskit.audio.pipeline.NUMPY_AVAILABLE", False):
            audio = [1, 2, 3, 4, 5]
            result = pipeline._apply_effects(audio, 22050, {"volume": 0.5})
            assert result == audio

    def test_apply_effects_volume(self, pipeline):
        """Test volume effect."""
        if not pipeline.is_available():
            pytest.skip("Audio pipeline not available - missing dependencies")

        audio = np.array([0.5, 1.0, -0.8, 0.3])
        effects = {"volume": 0.5}
        result = pipeline._apply_effects(audio, 22050, effects)

        assert isinstance(result, np.ndarray)
        assert np.allclose(result, audio * 0.5)

    def test_apply_effects_rate_change_without_librosa(self, pipeline):
        """Test rate change without librosa."""
        if not pipeline.is_available():
            pytest.skip("Audio pipeline not available - missing dependencies")

        audio = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float32)
        effects = {"rate": 0.5}

        with patch("ttskit.audio.pipeline.LIBROSA_AVAILABLE", False):
            result = pipeline._apply_effects(audio, 22050, effects)

        assert isinstance(result, np.ndarray)
        assert len(result) > 0

    def test_apply_effects_pitch_change_without_librosa(self, pipeline):
        """Test pitch change without librosa."""
        if not pipeline.is_available():
            pytest.skip("Audio pipeline not available - missing dependencies")

        audio = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float32)
        effects = {"pitch": 2.0}

        with patch("ttskit.audio.pipeline.LIBROSA_AVAILABLE", False):
            result = pipeline._apply_effects(audio, 22050, effects)

        assert isinstance(result, np.ndarray)
        assert np.array_equal(result, audio)

    def test_fade_in_without_numpy(self, pipeline):
        """Test fade in without numpy."""
        with patch("ttskit.audio.pipeline.NUMPY_AVAILABLE", False):
            audio = [1, 2, 3, 4, 5]
            result = pipeline._fade_in(audio, 22050, 0.1)
            assert result == audio

    def test_fade_in_with_numpy(self, pipeline):
        """Test fade in with numpy."""
        if not pipeline.is_available():
            pytest.skip("Audio pipeline not available - missing dependencies")

        audio = np.array([1.0, 1.0, 1.0, 1.0, 1.0])
        result = pipeline._fade_in(audio, 22050, 0.1)

        assert isinstance(result, np.ndarray)
        assert result[0] < result[-1]

    def test_fade_out_without_numpy(self, pipeline):
        """Test fade out without numpy."""
        with patch("ttskit.audio.pipeline.NUMPY_AVAILABLE", False):
            audio = [1, 2, 3, 4, 5]
            result = pipeline._fade_out(audio, 22050, 0.1)
            assert result == audio

    def test_fade_out_with_numpy(self, pipeline):
        """Test fade out with numpy."""
        if not pipeline.is_available():
            pytest.skip("Audio pipeline not available - missing dependencies")

        audio = np.array([1.0, 1.0, 1.0, 1.0, 1.0])
        result = pipeline._fade_out(audio, 22050, 0.1)

        assert isinstance(result, np.ndarray)
        assert result[0] > result[-1]

    def test_convert_format_not_available(self, pipeline):
        """Test format conversion when pydub not available."""
        with patch("ttskit.audio.pipeline.PYDUB_AVAILABLE", False):
            with pytest.raises(RuntimeError, match="pydub not available"):
                pipeline.convert_format(b"test_data", "wav", "mp3")

    def test_convert_format_unsupported_output(self, pipeline):
        """Test format conversion with unsupported output format."""
        if not pipeline.is_available():
            pytest.skip("Audio pipeline not available - missing dependencies")

        import io
        import wave

        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(22050)
            wav_file.writeframes(b"\x00\x01\x00\x02\x00\x03")

        wav_data = wav_buffer.getvalue()

        with pytest.raises(ValueError, match="Unsupported output format"):
            pipeline.convert_format(wav_data, "wav", "unsupported")

    def test_normalize_not_available(self, pipeline):
        """Test normalize when pipeline not available."""
        with patch.object(pipeline, "is_available", return_value=False):
            with pytest.raises(RuntimeError, match="Audio pipeline not available"):
                pipeline.normalize(b"test_data")

    def test_get_audio_info_not_available(self, pipeline):
        """Test get_audio_info when pydub not available."""
        with patch("ttskit.audio.pipeline.PYDUB_AVAILABLE", False):
            with pytest.raises(RuntimeError, match="pydub not available"):
                pipeline.get_audio_info(b"test_data", "wav")

    def test_merge_audio_not_available(self, pipeline):
        """Test merge_audio when pydub not available."""
        with patch("ttskit.audio.pipeline.PYDUB_AVAILABLE", False):
            with pytest.raises(RuntimeError, match="pydub not available"):
                pipeline.merge_audio([b"test_data"])

    def test_merge_audio_empty_list(self, pipeline):
        """Test merge_audio with empty list."""
        if not pipeline.is_available():
            pytest.skip("Audio pipeline not available - missing dependencies")

        with pytest.raises(ValueError, match="No audio files provided"):
            pipeline.merge_audio([])

    def test_split_audio_not_available(self, pipeline):
        """Test split_audio when pydub not available."""
        with patch("ttskit.audio.pipeline.PYDUB_AVAILABLE", False):
            with pytest.raises(RuntimeError, match="pydub not available"):
                pipeline.split_audio(b"test_data", "wav", 1.0)

    def test_convert_alias(self, pipeline):
        """Test convert method alias."""
        with patch.object(
            pipeline, "convert_format", return_value=b"converted"
        ) as mock_convert:
            pipeline.convert(b"test_data", "wav", "mp3")
            mock_convert.assert_called_once_with(b"test_data", "wav", "mp3")


class TestGlobalFunctions:
    """Test global functions in pipeline module."""

    def test_process_audio_function(self):
        """Test global process_audio function."""
        with patch("ttskit.audio.pipeline.pipeline") as mock_pipeline:
            async def mock_process():
                return b"processed"

            mock_pipeline.process_audio.return_value = mock_process()

            process_audio(b"test_data", input_format="wav")
            mock_pipeline.process_audio.assert_called_once()

    def test_convert_format_function(self):
        """Test global convert_format function."""
        with patch("ttskit.audio.pipeline.pipeline") as mock_pipeline:
            mock_pipeline.convert_format.return_value = b"converted"

            result = convert_format(b"test_data", "wav", "mp3")
            mock_pipeline.convert_format.assert_called_once_with(
                b"test_data", "wav", "mp3"
            )
            assert result == b"converted"


class TestAudioPipelineIntegration:
    """Integration tests for AudioPipeline."""

    @pytest.fixture
    def pipeline(self):
        """Create AudioPipeline instance."""
        return AudioPipeline()

    @pytest.mark.asyncio
    async def test_full_processing_pipeline(self, pipeline, sample_wav_data):
        """Test complete audio processing pipeline."""
        if not pipeline.is_available():
            pytest.skip("Audio pipeline not available - missing dependencies")

        effects = {"volume": 0.8, "fade_in": 0.05, "fade_out": 0.05, "rate": 1.0}

        result = await pipeline.process_audio(
            sample_wav_data,
            input_format="wav",
            output_format="wav",
            sample_rate=44100,
            normalize=True,
            trim_silence=True,
            effects=effects,
        )

        assert isinstance(result, bytes)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_concurrent_processing(self, pipeline, sample_wav_data):
        """Test concurrent audio processing."""
        if not pipeline.is_available():
            pytest.skip("Audio pipeline not available - missing dependencies")

        async def process_audio_task(audio_data, task_id):
            return await pipeline.process_audio(
                audio_data, input_format="wav", output_format="wav"
            )

        tasks = [process_audio_task(sample_wav_data, i) for i in range(5)]

        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        for result in results:
            assert isinstance(result, bytes)
            assert len(result) > 0

    def test_audio_info_extraction(self, pipeline, sample_wav_data):
        """Test audio information extraction."""
        if not pipeline.is_available():
            pytest.skip("Audio pipeline not available - missing dependencies")

        info = pipeline.get_audio_info(sample_wav_data, "wav")

        assert isinstance(info, dict)
        assert "duration" in info
        assert "sample_rate" in info
        assert "channels" in info
        assert "bit_depth" in info
        assert "format" in info
        assert "size_bytes" in info

        assert info["format"] == "wav"
        assert info["size_bytes"] > 0

    def test_audio_merging(self, pipeline, sample_wav_data):
        """Test audio file merging."""
        if not pipeline.is_available():
            pytest.skip("Audio pipeline not available - missing dependencies")

        audio_files = [sample_wav_data, sample_wav_data, sample_wav_data]

        merged = pipeline.merge_audio(audio_files, "wav")

        assert isinstance(merged, bytes)
        assert len(merged) > len(sample_wav_data)

    def test_audio_splitting(self, pipeline, sample_wav_data):
        """Test audio file splitting."""
        if not pipeline.is_available():
            pytest.skip("Audio pipeline not available - missing dependencies")

        segments = pipeline.split_audio(
            sample_wav_data, "wav", 0.5
        )

        assert isinstance(segments, list)
        assert len(segments) > 0

        for segment in segments:
            assert isinstance(segment, bytes)
            assert len(segment) > 0

    def test_merge_wav_files_comprehensive(self, pipeline):
        """Test comprehensive WAV file merging functionality."""
        if not pipeline.is_available():
            pytest.skip("Audio pipeline not available - missing dependencies")

        import io
        import wave

        def create_wav_data(frequency=440, duration=0.1):
            sample_rate = 22050
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            audio_data = np.sin(2 * np.pi * frequency * t) * 0.3
            audio_data = (audio_data * 32767).astype(np.int16)

            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio_data.tobytes())
            return wav_buffer.getvalue()

        wav_files = [
            create_wav_data(440, 0.1),
            create_wav_data(880, 0.1),
            create_wav_data(1320, 0.1),
        ]

        merged = pipeline._merge_wav_files(wav_files)
        assert isinstance(merged, bytes)
        assert len(merged) > len(wav_files[0])

        single_wav = [create_wav_data(440, 0.1)]
        merged_single = pipeline._merge_wav_files(single_wav)
        assert isinstance(merged_single, bytes)
        assert len(merged_single) > 0

        with pytest.raises(IndexError):
            pipeline._merge_wav_files([])

    def test_merge_wav_files_format_mismatch(self, pipeline):
        """Test WAV file merging with format mismatch."""
        if not pipeline.is_available():
            pytest.skip("Audio pipeline not available - missing dependencies")

        import io
        import wave

        def create_wav_data(sample_rate=22050):
            duration = 0.1
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            audio_data = np.sin(2 * np.pi * 440 * t) * 0.3
            audio_data = (audio_data * 32767).astype(np.int16)

            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio_data.tobytes())
            return wav_buffer.getvalue()

        wav_files = [create_wav_data(22050), create_wav_data(44100)]

        with pytest.raises(ValueError, match="All WAV files must have the same format"):
            pipeline._merge_wav_files(wav_files)

    def test_merge_wav_files_not_available(self, pipeline):
        """Test WAV file merging when dependencies not available."""
        with patch("ttskit.audio.pipeline.NUMPY_AVAILABLE", False):
            with pytest.raises(
                RuntimeError, match="Required audio libraries not available"
            ):
                pipeline._merge_wav_files([b"test_data"])

    def test_change_rate_comprehensive(self, pipeline):
        """Test comprehensive rate change functionality."""
        if not pipeline.is_available():
            pytest.skip("Audio pipeline not available - missing dependencies")

        audio = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float32)
        sample_rate = 22050

        with patch("ttskit.audio.pipeline.LIBROSA_AVAILABLE", True):
            with patch("librosa.effects.time_stretch") as mock_time_stretch:
                mock_time_stretch.return_value = np.array(
                    [1.0, 2.0, 3.0], dtype=np.float32
                )

                result = pipeline._change_rate(audio, sample_rate, 0.5)
                assert isinstance(result, np.ndarray)
                mock_time_stretch.assert_called_once_with(audio, rate=0.5)

        with patch("ttskit.audio.pipeline.LIBROSA_AVAILABLE", False):
            result = pipeline._change_rate(audio, sample_rate, 0.5)
            assert isinstance(result, np.ndarray)
            assert len(result) > 0

        with patch("ttskit.audio.pipeline.LIBROSA_AVAILABLE", True):
            with patch(
                "librosa.effects.time_stretch", side_effect=Exception("librosa error")
            ):
                result = pipeline._change_rate(audio, sample_rate, 0.5)
                assert isinstance(result, np.ndarray)
                assert len(result) > 0

    def test_change_rate_edge_cases(self, pipeline):
        """Test rate change edge cases."""
        if not pipeline.is_available():
            pytest.skip("Audio pipeline not available - missing dependencies")

        audio = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float32)
        sample_rate = 22050

        with patch("ttskit.audio.pipeline.LIBROSA_AVAILABLE", False):
            result = pipeline._change_rate(audio, sample_rate, 1.0)
            assert isinstance(result, np.ndarray)
            assert len(result) > 0

        with patch("ttskit.audio.pipeline.LIBROSA_AVAILABLE", False):
            result = pipeline._change_rate(audio, sample_rate, 0.1)
            assert isinstance(result, np.ndarray)
            assert len(result) > 0

        with patch("ttskit.audio.pipeline.LIBROSA_AVAILABLE", False):
            result = pipeline._change_rate(audio, sample_rate, 2.0)
            assert isinstance(result, np.ndarray)
            assert len(result) > 0

    def test_normalize_comprehensive(self, pipeline):
        """Test comprehensive normalization functionality."""
        if not pipeline.is_available():
            pytest.skip("Audio pipeline not available - missing dependencies")

        audio = np.array([0.5, 1.5, -0.8, 0.3], dtype=np.float32)
        result = pipeline.normalize(audio.tobytes(), "wav")
        assert isinstance(result, bytes)
        assert len(result) > 0

        normalized_audio = np.array([0.1, 0.2, -0.1, 0.3], dtype=np.float32)
        result = pipeline.normalize(normalized_audio.tobytes(), "wav")
        assert isinstance(result, bytes)
        assert len(result) > 0

        zero_audio = np.array([0.0, 0.0, 0.0, 0.0], dtype=np.float32)
        result = pipeline.normalize(zero_audio.tobytes(), "wav")
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_normalize_edge_cases(self, pipeline):
        """Test normalization edge cases."""
        if not pipeline.is_available():
            pytest.skip("Audio pipeline not available - missing dependencies")

        small_audio = np.array([0.001], dtype=np.float32)
        result = pipeline.normalize(small_audio.tobytes(), "wav")
        assert isinstance(result, bytes)
        assert len(result) > 0

        large_audio = np.array([10.0, -10.0, 5.0, -5.0], dtype=np.float32)
        result = pipeline.normalize(large_audio.tobytes(), "wav")
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_check_dependencies_comprehensive(self, pipeline):
        """Test comprehensive dependency checking."""
        with (
            patch("ttskit.audio.pipeline.NUMPY_AVAILABLE", True),
            patch("ttskit.audio.pipeline.LIBROSA_AVAILABLE", True),
            patch("ttskit.audio.pipeline.SOUNDFILE_AVAILABLE", True),
            patch("ttskit.audio.pipeline.PYDUB_AVAILABLE", True),
        ):
            result = pipeline._check_dependencies()
            assert result is True

        with (
            patch("ttskit.audio.pipeline.NUMPY_AVAILABLE", False),
            patch("ttskit.audio.pipeline.LIBROSA_AVAILABLE", True),
            patch("ttskit.audio.pipeline.SOUNDFILE_AVAILABLE", True),
            patch("ttskit.audio.pipeline.PYDUB_AVAILABLE", True),
        ):
            result = pipeline._check_dependencies()
            assert result is False

        with (
            patch("ttskit.audio.pipeline.NUMPY_AVAILABLE", True),
            patch("ttskit.audio.pipeline.LIBROSA_AVAILABLE", False),
            patch("ttskit.audio.pipeline.SOUNDFILE_AVAILABLE", True),
            patch("ttskit.audio.pipeline.PYDUB_AVAILABLE", True),
        ):
            result = pipeline._check_dependencies()
            assert (
                result is True
            )

        with (
            patch("ttskit.audio.pipeline.NUMPY_AVAILABLE", True),
            patch("ttskit.audio.pipeline.LIBROSA_AVAILABLE", True),
            patch("ttskit.audio.pipeline.SOUNDFILE_AVAILABLE", False),
            patch("ttskit.audio.pipeline.PYDUB_AVAILABLE", True),
        ):
            result = pipeline._check_dependencies()
            assert result is False

        with (
            patch("ttskit.audio.pipeline.NUMPY_AVAILABLE", True),
            patch("ttskit.audio.pipeline.LIBROSA_AVAILABLE", True),
            patch("ttskit.audio.pipeline.SOUNDFILE_AVAILABLE", True),
            patch("ttskit.audio.pipeline.PYDUB_AVAILABLE", False),
        ):
            result = pipeline._check_dependencies()
            assert (
                result is True
            )

        with (
            patch("ttskit.audio.pipeline.NUMPY_AVAILABLE", False),
            patch("ttskit.audio.pipeline.LIBROSA_AVAILABLE", False),
            patch("ttskit.audio.pipeline.SOUNDFILE_AVAILABLE", False),
            patch("ttskit.audio.pipeline.PYDUB_AVAILABLE", False),
        ):
            result = pipeline._check_dependencies()
            assert result is False

    @pytest.mark.asyncio
    async def test_process_audio_comprehensive(self, pipeline, sample_wav_data):
        """Test comprehensive audio processing functionality."""
        if not pipeline.is_available():
            pytest.skip("Audio pipeline not available - missing dependencies")

        small_data = b"small"
        result = await pipeline.process_audio(small_data)
        assert result == small_data

        medium_data = sample_wav_data[:50000]
        result = await pipeline.process_audio(
            medium_data, input_format="wav", output_format="wav"
        )
        assert isinstance(result, bytes)
        assert len(result) > 0

        large_data = sample_wav_data * 100
        result = await pipeline.process_audio(
            large_data, input_format="wav", output_format="wav"
        )
        assert isinstance(result, bytes)
        assert len(result) > 0

        result = await pipeline.process_audio(
            sample_wav_data,
            input_format="wav",
            output_format="wav",
            sample_rate=44100,
            normalize=True,
            trim_silence=True,
            effects={
                "volume": 0.8,
                "fade_in": 0.1,
                "fade_out": 0.1,
                "rate": 1.0,
                "pitch": 0.0,
            },
        )
        assert isinstance(result, bytes)
        assert len(result) > 0

        result = await pipeline.process_audio(
            sample_wav_data,
            input_format="wav",
            output_format="wav",
            normalize=False,
            trim_silence=False,
            effects=None,
        )
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_change_pitch_comprehensive(self, pipeline):
        """Test comprehensive pitch change functionality."""
        if not pipeline.is_available():
            pytest.skip("Audio pipeline not available - missing dependencies")

        audio = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float32)
        sample_rate = 22050

        with patch("ttskit.audio.pipeline.LIBROSA_AVAILABLE", False):
            result = pipeline._change_pitch(audio, sample_rate, 2.0)
            assert isinstance(result, np.ndarray)
            assert np.array_equal(result, audio)

        with patch("ttskit.audio.pipeline.LIBROSA_AVAILABLE", False):
            result = pipeline._change_pitch(audio, sample_rate, 2.0)
            assert isinstance(result, np.ndarray)
            assert np.array_equal(result, audio)

        with patch("ttskit.audio.pipeline.LIBROSA_AVAILABLE", False):
            result = pipeline._change_pitch(audio, sample_rate, 0.0)
            assert isinstance(result, np.ndarray)
            assert np.array_equal(result, audio)

    def test_resample_audio_comprehensive(self, pipeline):
        """Test comprehensive audio resampling functionality."""
        if not pipeline.is_available():
            pytest.skip("Audio pipeline not available - missing dependencies")

        audio = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float32)
        orig_sr = 22050

        result = pipeline._resample_audio(audio, orig_sr, orig_sr)
        assert np.array_equal(result, audio)

        with patch("ttskit.audio.pipeline.LIBROSA_AVAILABLE", True):
            with patch("librosa.resample") as mock_resample:
                mock_resample.return_value = np.array([1.0, 2.0, 3.0], dtype=np.float32)

                result = pipeline._resample_audio(audio, orig_sr, 44100)
                assert isinstance(result, np.ndarray)
                mock_resample.assert_called_once_with(
                    audio, orig_sr=orig_sr, target_sr=44100, res_type="linear"
                )

        with patch("ttskit.audio.pipeline.LIBROSA_AVAILABLE", True):
            with patch("librosa.resample", side_effect=Exception("librosa error")):
                result = pipeline._resample_audio(audio, orig_sr, 44100)
                assert isinstance(result, np.ndarray)
                assert len(result) > 0

        with patch("ttskit.audio.pipeline.LIBROSA_AVAILABLE", False):
            result = pipeline._resample_audio(audio, orig_sr, orig_sr * 2)
            assert isinstance(result, np.ndarray)
            assert len(result) > len(audio)

        with patch("ttskit.audio.pipeline.LIBROSA_AVAILABLE", False):
            result = pipeline._resample_audio(audio, orig_sr, orig_sr // 2)
            assert isinstance(result, np.ndarray)
            assert len(result) < len(audio)

        with patch("ttskit.audio.pipeline.LIBROSA_AVAILABLE", False):
            result = pipeline._resample_audio(audio, orig_sr, 16000)
            assert isinstance(result, np.ndarray)
            assert len(result) > 0

    def test_resample_audio_edge_cases(self, pipeline):
        """Test resampling edge cases."""
        if not pipeline.is_available():
            pytest.skip("Audio pipeline not available - missing dependencies")

        audio = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float32)
        orig_sr = 22050

        small_audio = np.array([1.0], dtype=np.float32)
        with patch("ttskit.audio.pipeline.LIBROSA_AVAILABLE", False):
            result = pipeline._resample_audio(small_audio, orig_sr, 44100)
            assert isinstance(result, np.ndarray)
            assert len(result) > 0

        with patch("ttskit.audio.pipeline.LIBROSA_AVAILABLE", False):
            result = pipeline._resample_audio(audio, orig_sr, orig_sr * 10)
            assert isinstance(result, np.ndarray)
            assert len(result) > len(audio)

        with patch("ttskit.audio.pipeline.LIBROSA_AVAILABLE", False):
            result = pipeline._resample_audio(audio, orig_sr, orig_sr // 10)
            assert isinstance(result, np.ndarray)
            assert len(result) < len(audio)

    def test_load_audio_fallback(self, pipeline):
        """Test _load_audio fallback to temporary file."""
        if not pipeline.is_available():
            pytest.skip("Audio pipeline not available - missing dependencies")

        with patch("soundfile.read") as mock_read:
            mock_read.side_effect = [
                Exception("Memory loading failed"),
                (
                    np.array([0.1, 0.2, 0.1], dtype=np.float32),
                    22050,
                ),
            ]

            result = pipeline._load_audio(b"test_data", "wav")
            assert isinstance(result, tuple)
            assert len(result) == 2
            assert isinstance(result[0], np.ndarray)
            assert isinstance(result[1], int)

    def test_save_audio_fallback(self, pipeline):
        """Test _save_audio fallback to temporary file."""
        if not pipeline.is_available():
            pytest.skip("Audio pipeline not available - missing dependencies")

        audio = np.array([0.1, 0.2, 0.1], dtype=np.float32)
        sample_rate = 22050

        with patch("soundfile.write") as mock_write:
            mock_write.side_effect = [
                Exception("Memory saving failed"),
                None,
            ]

            with patch("builtins.open", mock_open(read_data=b"fake_audio_data")):
                result = pipeline._save_audio(audio, sample_rate, "wav")
                assert isinstance(result, bytes)
                assert len(result) > 0

    def test_apply_effects_comprehensive(self, pipeline):
        """Test comprehensive effects application."""
        if not pipeline.is_available():
            pytest.skip("Audio pipeline not available - missing dependencies")

        audio = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float32)
        sample_rate = 22050

        effects = {
            "rate": 0.5,
            "pitch": 2.0,
            "volume": 0.8,
            "fade_in": 0.1,
            "fade_out": 0.1,
        }

        with patch("ttskit.audio.pipeline.LIBROSA_AVAILABLE", True):
            with (
                patch.object(pipeline, "_change_rate") as mock_rate,
                patch.object(pipeline, "_change_pitch") as mock_pitch,
                patch.object(pipeline, "_fade_in") as mock_fade_in,
                patch.object(pipeline, "_fade_out") as mock_fade_out,
            ):
                mock_rate.return_value = audio
                mock_pitch.return_value = audio
                mock_fade_in.return_value = audio
                mock_fade_out.return_value = audio

                result = pipeline._apply_effects(audio, sample_rate, effects)

                assert isinstance(result, np.ndarray)
                mock_rate.assert_called_once()
                mock_pitch.assert_called_once()
                mock_fade_in.assert_called_once()
                mock_fade_out.assert_called_once()

        result = pipeline._apply_effects(audio, sample_rate, {})
        assert isinstance(result, np.ndarray)
        assert np.array_equal(result, audio)

        partial_effects = {"volume": 0.5}
        result = pipeline._apply_effects(audio, sample_rate, partial_effects)
        assert isinstance(result, np.ndarray)
        assert np.allclose(result, audio * 0.5)

    def test_fade_in_edge_cases(self, pipeline):
        """Test fade in edge cases."""
        if not pipeline.is_available():
            pytest.skip("Audio pipeline not available - missing dependencies")

        audio = np.array([1.0, 1.0, 1.0, 1.0, 1.0], dtype=np.float32)
        sample_rate = 22050

        result = pipeline._fade_in(
            audio, sample_rate, 1.0
        )
        assert isinstance(result, np.ndarray)
        assert result[0] < result[-1]

        result = pipeline._fade_in(audio, sample_rate, 0.001)
        assert isinstance(result, np.ndarray)
        assert result[0] < result[-1]

    def test_fade_out_edge_cases(self, pipeline):
        """Test fade out edge cases."""
        if not pipeline.is_available():
            pytest.skip("Audio pipeline not available - missing dependencies")

        audio = np.array([1.0, 1.0, 1.0, 1.0, 1.0], dtype=np.float32)
        sample_rate = 22050

        result = pipeline._fade_out(
            audio, sample_rate, 1.0
        )
        assert isinstance(result, np.ndarray)
        assert result[0] > result[-1]

        result = pipeline._fade_out(audio, sample_rate, 0.001)
        assert isinstance(result, np.ndarray)
        assert result[0] > result[-1]

    def test_trim_silence_edge_cases(self, pipeline):
        """Test silence trimming edge cases."""
        if not pipeline.is_available():
            pytest.skip("Audio pipeline not available - missing dependencies")

        sample_rate = 22050

        audio_no_silence = np.array([0.5, 0.6, 0.7, 0.8, 0.9], dtype=np.float32)
        result = pipeline._trim_silence(audio_no_silence, sample_rate)
        assert isinstance(result, np.ndarray)
        assert len(result) > 0

        audio_all_silence = np.array([0.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float32)
        result = pipeline._trim_silence(audio_all_silence, sample_rate)
        assert isinstance(result, np.ndarray)
        assert len(result) > 0

        short_audio = np.array([0.1], dtype=np.float32)
        result = pipeline._trim_silence(short_audio, sample_rate)
        assert isinstance(result, np.ndarray)
        assert len(result) > 0

    def test_process_audio_sync_comprehensive(self, pipeline):
        """Test comprehensive synchronous audio processing."""
        if not pipeline.is_available():
            pytest.skip("Audio pipeline not available - missing dependencies")

        import io
        import wave

        sample_rate = 22050
        duration = 0.1
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        audio_data = np.sin(2 * np.pi * 440 * t) * 0.3
        audio_data = (audio_data * 32767).astype(np.int16)

        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data.tobytes())

        wav_data = wav_buffer.getvalue()

        result = pipeline._process_audio_sync(
            wav_data,
            "wav",
            "wav",
            44100,
            True,
            True,
            {"volume": 0.8, "fade_in": 0.05, "fade_out": 0.05},
        )
        assert isinstance(result, bytes)
        assert len(result) > 0

        result = pipeline._process_audio_sync(
            wav_data,
            "wav",
            "wav",
            None,
            False,
            False,
            None,
        )
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_convert_format_comprehensive(self, pipeline):
        """Test comprehensive format conversion."""
        if not pipeline.is_available():
            pytest.skip("Audio pipeline not available - missing dependencies")

        import io
        import wave

        sample_rate = 22050
        duration = 0.1
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        audio_data = np.sin(2 * np.pi * 440 * t) * 0.3
        audio_data = (audio_data * 32767).astype(np.int16)

        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data.tobytes())

        wav_data = wav_buffer.getvalue()

        result = pipeline.convert_format(wav_data, "wav", "mp3")
        assert isinstance(result, bytes)
        assert len(result) > 0

        result = pipeline.convert_format(wav_data, "wav", "ogg")
        assert isinstance(result, bytes)
        assert len(result) > 0

        result = pipeline.convert_format(wav_data, "wav", "wav")
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_get_audio_info_comprehensive(self, pipeline):
        """Test comprehensive audio info extraction."""
        if not pipeline.is_available():
            pytest.skip("Audio pipeline not available - missing dependencies")

        import io
        import wave

        sample_rate = 22050
        duration = 0.1
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        audio_data = np.sin(2 * np.pi * 440 * t) * 0.3
        audio_data = (audio_data * 32767).astype(np.int16)

        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data.tobytes())

        wav_data = wav_buffer.getvalue()

        info = pipeline.get_audio_info(wav_data, "wav")
        assert isinstance(info, dict)
        assert "duration" in info
        assert "sample_rate" in info
        assert "channels" in info
        assert "bit_depth" in info
        assert "format" in info
        assert "size_bytes" in info

        assert info["format"] == "wav"
        assert info["size_bytes"] == len(wav_data)
        assert isinstance(info["duration"], (int, float))
        assert isinstance(info["sample_rate"], (int, float))
        assert isinstance(info["channels"], (int, float))
        assert isinstance(info["bit_depth"], (int, float))

        assert info["sample_rate"] == 22050
        assert info["channels"] == 1
        assert info["bit_depth"] == 16
        assert info["duration"] > 0

    def test_split_audio_comprehensive(self, pipeline):
        """Test comprehensive audio splitting."""
        if not pipeline.is_available():
            pytest.skip("Audio pipeline not available - missing dependencies")

        import io
        import wave

        sample_rate = 22050
        duration = 2.0
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        audio_data = np.sin(2 * np.pi * 440 * t) * 0.3
        audio_data = (audio_data * 32767).astype(np.int16)

        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data.tobytes())

        wav_data = wav_buffer.getvalue()

        segments = pipeline.split_audio(wav_data, "wav", 0.5)
        assert isinstance(segments, list)
        assert len(segments) > 0

        for segment in segments:
            assert isinstance(segment, bytes)
            assert len(segment) > 0

        segments = pipeline.split_audio(wav_data, "wav", 1.0)
        assert isinstance(segments, list)
        assert len(segments) > 0

        segments = pipeline.split_audio(wav_data, "wav", 0.1)
        assert isinstance(segments, list)
        assert len(segments) > 0

        segments = pipeline.split_audio(wav_data, "wav", 5.0)
        assert isinstance(segments, list)
        assert len(segments) > 0

    def test_merge_audio_fallback_to_wav_merging(self, pipeline):
        """Test merge_audio fallback to WAV merging when pydub not available."""
        if not pipeline.is_available():
            pytest.skip("Audio pipeline not available - missing dependencies")

        import io
        import wave

        def create_wav_data():
            sample_rate = 22050
            duration = 0.1
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            audio_data = np.sin(2 * np.pi * 440 * t) * 0.3
            audio_data = (audio_data * 32767).astype(np.int16)

            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio_data.tobytes())
            return wav_buffer.getvalue()

        wav_files = [create_wav_data(), create_wav_data()]

        with patch("ttskit.audio.pipeline.PYDUB_AVAILABLE", False):
            result = pipeline.merge_audio(wav_files, "wav")
            assert isinstance(result, bytes)
            assert len(result) > 0

    def test_merge_audio_fallback_non_wav_error(self, pipeline):
        """Test merge_audio fallback error for non-WAV formats."""
        if not pipeline.is_available():
            pytest.skip("Audio pipeline not available - missing dependencies")

        with patch("ttskit.audio.pipeline.PYDUB_AVAILABLE", False):
            with pytest.raises(
                RuntimeError,
                match="pydub not available for audio merging with non-WAV formats",
            ):
                pipeline.merge_audio([b"test_data"], "mp3")

    def test_save_audio_memory_success(self, pipeline):
        """Test _save_audio successful memory saving."""
        if not pipeline.is_available():
            pytest.skip("Audio pipeline not available - missing dependencies")

        audio = np.array([0.1, 0.2, 0.1], dtype=np.float32)
        sample_rate = 22050

        with patch("soundfile.write") as mock_write:
            mock_buffer = MagicMock()
            mock_buffer.getvalue.return_value = b"fake_audio_data"

            with patch("io.BytesIO", return_value=mock_buffer):
                result = pipeline._save_audio(audio, sample_rate, "wav")
                assert isinstance(result, bytes)
                assert len(result) > 0
                mock_write.assert_called_once()

    def test_import_error_handling(self):
        """Test import error handling for audio libraries."""

        import importlib
        import sys

        original_modules = {}

        for module in ["numpy", "librosa", "soundfile", "pydub"]:
            if module in sys.modules:
                original_modules[module] = sys.modules[module]
                del sys.modules[module]

        try:
            pipeline_module = importlib.import_module("ttskit.audio.pipeline")

            assert hasattr(pipeline_module, "NUMPY_AVAILABLE")
            assert hasattr(pipeline_module, "LIBROSA_AVAILABLE")
            assert hasattr(pipeline_module, "SOUNDFILE_AVAILABLE")
            assert hasattr(pipeline_module, "PYDUB_AVAILABLE")

        finally:
            for module, original_module in original_modules.items():
                sys.modules[module] = original_module
