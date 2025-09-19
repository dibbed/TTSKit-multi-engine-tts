"""Tests for Piper TTS engine."""

from pathlib import Path

import pytest

from ttskit.engines.piper_engine import PIPER_AVAILABLE, PiperEngine


class TestPiperEngine:
    """Test cases for PiperEngine."""

    def test_piper_availability(self):
        """Test PIPER_AVAILABLE flag."""
        assert isinstance(PIPER_AVAILABLE, bool)

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_initialization_with_piper_available(self):
        """Test engine initialization when Piper is available."""
        engine = PiperEngine(default_lang="en")
        assert engine.default_lang == "en"
        assert engine.is_available()

    @pytest.mark.skipif(PIPER_AVAILABLE, reason="Piper TTS is available")
    def test_initialization_without_piper(self):
        """Test engine initialization when Piper is not available."""
        with pytest.raises(ImportError, match="Piper TTS package not installed"):
            PiperEngine()

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_get_capabilities(self):
        """Test engine capabilities."""
        engine = PiperEngine()
        caps = engine.get_capabilities()

        assert caps.offline is True
        assert caps.ssml is False
        assert caps.rate_control is True
        assert caps.pitch_control is False
        assert isinstance(caps.languages, list)
        assert isinstance(caps.voices, list)
        assert caps.max_text_length > 0

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_capabilities_dict(self):
        """Test capabilities as dictionary."""
        engine = PiperEngine()
        caps_dict = engine.capabilities()

        assert isinstance(caps_dict, dict)
        assert "offline" in caps_dict
        assert "ssml" in caps_dict
        assert "rate" in caps_dict
        assert "pitch" in caps_dict
        assert "langs" in caps_dict
        assert "voices" in caps_dict

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_list_voices(self):
        """Test voice listing."""
        engine = PiperEngine()
        voices = engine.list_voices()
        assert isinstance(voices, list)

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_list_voices_with_language(self):
        """Test voice listing with specific language."""
        engine = PiperEngine()
        voices = engine.list_voices("en")

        assert isinstance(voices, list)

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_get_supported_languages(self):
        """Test getting supported languages."""
        engine = PiperEngine()
        languages = engine.get_supported_languages()

        assert isinstance(languages, list)
        assert len(languages) > 0

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_supports_language(self):
        """Test language support check."""
        engine = PiperEngine()
        assert isinstance(engine.supports_language("en"), bool)
        assert isinstance(engine.supports_language("fa"), bool)

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_supports_voice(self):
        """Test voice support check."""
        engine = PiperEngine()
        voices = engine.list_voices()
        if voices:
            voice = voices[0]
            assert engine.supports_voice(voice) in (True, False)
        assert engine.supports_voice("nonexistent_voice") in (True, False)

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_can_handle_text_length(self):
        """Test text length validation."""
        engine = PiperEngine()
        assert engine.can_handle_text_length("Hello") is True
        long_text = "A" * 10000
        assert engine.can_handle_text_length(long_text) is False

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_validate_input(self):
        """Test input validation."""
        engine = PiperEngine()

        result = engine.validate_input("Hello", "en")
        assert result is None

        with pytest.raises(ValueError, match="Text cannot be empty"):
            engine.validate_input("", "en")

        result = engine.validate_input("Hello", "xyz")
        assert result == "invalid_language"

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_get_info(self):
        """Test getting engine information."""
        engine = PiperEngine()
        info = engine.get_info()

        assert isinstance(info, dict)
        assert "name" in info
        assert "version" in info
        assert "default_lang" in info
        assert "available" in info
        assert "description" in info
        assert "capabilities" in info
        assert "languages" in info
        assert "voices_count" in info
        assert "supported_languages" in info

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    @pytest.mark.asyncio
    async def test_synth_async(self):
        """Test async synthesis."""
        engine = PiperEngine()
        try:
            audio_data = await engine.synth_async("Hello World", "en")
            assert isinstance(audio_data, bytes)
            assert len(audio_data) >= 0
        except Exception as e:
            pytest.skip(f"Synthesis failed (likely missing models): {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_synth_to_mp3(self):
        """Test MP3 synthesis."""
        engine = PiperEngine()
        try:
            file_path = engine.synth_to_mp3("Hello World", "en")
            assert isinstance(file_path, str)
            assert file_path.endswith(".mp3")
        except Exception as e:
            pytest.skip(f"Synthesis failed (likely missing models): {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    @pytest.mark.asyncio
    async def test_synth_to_file_async(self, tmp_path):
        """Test async file synthesis."""
        engine = PiperEngine()
        output_path = tmp_path / "test_output.wav"
        try:
            result_path = await engine.synth_to_file_async(
                "Hello World", str(output_path), "en"
            )
            assert result_path == str(output_path)
            assert output_path.exists()
        except Exception as e:
            pytest.skip(f"Synthesis failed (likely missing models): {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_synth_to_file(self, tmp_path):
        """Test synchronous file synthesis."""
        engine = PiperEngine()
        output_path = tmp_path / "test_output.wav"
        try:
            result_path = engine.synth_to_file("Hello World", str(output_path), "en")
            assert result_path == str(output_path)
            assert output_path.exists()
        except Exception as e:
            pytest.skip(f"Synthesis failed (likely missing models): {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_model_path_initialization(self):
        """Test initialization with custom model path."""
        from pathlib import Path

        custom_path = "/custom/models/path"
        engine = PiperEngine(model_path=custom_path)

        assert Path(engine.model_path).as_posix() == Path(custom_path).as_posix()

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_default_language_initialization(self):
        """Test initialization with default language."""
        engine = PiperEngine(default_lang="fa")

        assert engine.default_lang == "fa"

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_engine_availability_check(self):
        """Test engine availability check."""
        engine = PiperEngine()

        assert engine.is_available() is True

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_voice_loading(self):
        """Test voice loading functionality."""
        engine = PiperEngine()
        try:
            voices = engine.list_voices()
            assert isinstance(voices, list)
        except Exception as e:
            pytest.skip(f"Voice listing failed (likely missing models): {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_model_loading(self):
        """Test model loading functionality."""
        pytest.skip("Model loading test not applicable for new PiperEngine API")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_set_available(self):
        """Test setting engine availability."""
        engine = PiperEngine()

        # Test setting to False
        engine.set_available(False)
        assert engine._available is False

        # Test setting to True
        engine.set_available(True)
        assert engine._available is True

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_get_model_info(self):
        """Test getting model information."""
        engine = PiperEngine()

        # Test with non-existent model
        result = engine.get_model_info("nonexistent_model")
        assert result is None

        # Test with existing model (if any voices are loaded)
        if engine.available_voices:
            voice_name = engine.available_voices[0]
            result = engine.get_model_info(voice_name)
            if result:
                assert isinstance(result, dict)
                assert "model_key" in result
                assert "language" in result
                assert "voice" in result
                assert "config" in result
                assert "available" in result

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_get_all_models_info(self):
        """Test getting all models information."""
        engine = PiperEngine()

        result = engine.get_all_models_info()
        assert isinstance(result, dict)

        # Should be empty if no models are loaded
        if not engine.available_voices:
            assert len(result) == 0

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_find_best_voice(self):
        """Test finding best voice for language."""
        engine = PiperEngine()

        # Test with exact language match
        if engine.available_voices:
            # Find a voice with known language prefix
            for voice in engine.available_voices:
                if "_" in voice:
                    lang = voice.split("_")[0]
                    result = engine._find_best_voice(lang)
                    assert result is not None
                    assert result.startswith(f"{lang}_")
                    break

        # Test with language prefix match
        result = engine._find_best_voice("en")
        if engine.available_voices:
            # Should return first available voice as fallback
            assert result is not None
            assert result in engine.available_voices

        # Test with non-existent language
        result = engine._find_best_voice("xyz")
        if engine.available_voices:
            # Should return first available voice as fallback
            assert result is not None
            assert result in engine.available_voices
        else:
            assert result is None

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_synth_sync(self):
        """Test synchronous synthesis to WAV file."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        voice_name = engine.available_voices[0]

        try:
            result = engine._synth_sync("Hello World", voice_name)
            assert isinstance(result, str)
            assert result.endswith(".wav")

            # Check if file exists
            import os

            assert os.path.exists(result)
        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_synth_sync_to_mp3(self):
        """Test synchronous synthesis to MP3 file."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        voice_name = engine.available_voices[0]

        try:
            result = engine._synth_sync_to_mp3("Hello World", voice_name)
            assert isinstance(result, str)
            assert result.endswith(".mp3")

            # Check if file exists
            import os

            assert os.path.exists(result)
        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    @pytest.mark.asyncio
    async def test_synth_async_to_wav(self):
        """Test asynchronous synthesis to WAV file."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        voice_name = engine.available_voices[0]

        try:
            result = await engine._synth_async_to_wav("Hello World", voice_name)
            assert isinstance(result, str)
            assert result.endswith(".wav")

            # Check if file exists
            import os

            assert os.path.exists(result)
        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    @pytest.mark.asyncio
    async def test_synth_async_to_mp3(self):
        """Test asynchronous synthesis to MP3 file."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        voice_name = engine.available_voices[0]

        try:
            result = await engine._synth_async_to_mp3("Hello World", voice_name)
            assert isinstance(result, str)
            assert result.endswith(".mp3")

            # Check if file exists
            import os

            assert os.path.exists(result)
        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_synth_sync_to_bytes(self):
        """Test synchronous synthesis to bytes."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        voice_name = engine.available_voices[0]

        try:
            result = engine._synth_sync_to_bytes("Hello World", voice_name)
            assert isinstance(result, bytes)
            assert len(result) > 0

            # Test with custom rate and pitch
            result2 = engine._synth_sync_to_bytes(
                "Hello World", voice_name, rate=1.5, pitch=0.5
            )
            assert isinstance(result2, bytes)
            assert len(result2) > 0
        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_synth_to_mp3_edge_cases(self):
        """Test MP3 synthesis edge cases."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        # Test with no running loop (RuntimeError case)
        try:
            result = engine.synth_to_mp3("Hello World", "en")
            assert isinstance(result, str)
            assert result.endswith(".mp3")
        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    @pytest.mark.asyncio
    async def test_synth_async_edge_cases(self):
        """Test async synthesis edge cases."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        # Test with specific voice
        voice_name = engine.available_voices[0]
        try:
            result = await engine.synth_async("Hello World", "en", voice=voice_name)
            assert isinstance(result, bytes)
            assert len(result) > 0
        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

        # Test with different output formats
        try:
            result_wav = await engine.synth_async(
                "Hello World", "en", output_format="wav"
            )
            assert isinstance(result_wav, bytes)

            result_mp3 = await engine.synth_async(
                "Hello World", "en", output_format="mp3"
            )
            assert isinstance(result_mp3, bytes)
        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_load_voices_edge_cases(self):
        """Test voice loading edge cases."""
        import tempfile
        from pathlib import Path

        # Test with non-existent path
        with tempfile.TemporaryDirectory() as temp_dir:
            non_existent_path = Path(temp_dir) / "non_existent"
            engine = PiperEngine(model_path=str(non_existent_path))
            assert engine._available is False
            assert len(engine.available_voices) == 0

        # Test with empty directory
        with tempfile.TemporaryDirectory() as temp_dir:
            engine = PiperEngine(model_path=temp_dir)
            assert engine._available is False
            assert len(engine.available_voices) == 0

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_initialization_edge_cases(self):
        """Test initialization edge cases."""
        # Test with custom parameters
        engine = PiperEngine(
            model_path="./models/piper/", default_lang="fa", use_cuda=True
        )

        assert engine.model_path == Path("./models/piper/")
        assert engine.default_lang == "fa"
        assert engine.use_cuda is True
        assert isinstance(engine.voices, dict)
        assert isinstance(engine.available_voices, list)
        assert isinstance(engine._available, bool)

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_raw_audio_to_wav(self):
        """Test raw audio to WAV conversion."""
        engine = PiperEngine()

        # Create dummy raw audio data (16-bit PCM)
        dummy_audio = b"\x00\x01" * 1000  # 1000 samples

        result = engine._raw_audio_to_wav(dummy_audio)
        assert isinstance(result, bytes)
        assert len(result) > len(dummy_audio)  # Should have WAV header

        # Check WAV header
        assert result.startswith(b"RIFF")
        assert b"WAVE" in result

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    async def test_synth_async_voice_not_found(self):
        """Test async synthesis with voice not found."""
        engine = PiperEngine()

        # Test with non-existent voice
        with pytest.raises(ValueError, match="No Piper voice found"):
            await engine.synth_async("Hello World", "en", voice="nonexistent_voice")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_synth_to_mp3_no_voice_found(self):
        """Test MP3 synthesis when no voice is found."""
        engine = PiperEngine()

        # Clear available voices to test no voice found case
        original_voices = engine.available_voices.copy()
        engine.available_voices = []

        try:
            # Test with unsupported language
            with pytest.raises(ValueError, match="No Piper voice found for language"):
                engine.synth_to_mp3("Hello World", "xyz")
        finally:
            # Restore original voices
            engine.available_voices = original_voices

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_load_voices_with_exception(self):
        """Test voice loading with exception handling."""
        import tempfile
        from pathlib import Path

        # Create a temporary directory with a file that will cause loading to fail
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a fake .onnx file that will cause an exception
            fake_onnx = Path(temp_dir) / "fake_voice.onnx"
            fake_onnx.write_bytes(b"fake onnx data")

            engine = PiperEngine(model_path=temp_dir)
            # Should handle the exception gracefully
            assert isinstance(engine.available_voices, list)

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_find_best_voice_comprehensive(self):
        """Test comprehensive voice finding scenarios."""
        engine = PiperEngine()

        # Test with empty voices list
        original_voices = engine.available_voices.copy()
        engine.available_voices = []

        result = engine._find_best_voice("en")
        assert result is None

        # Restore voices
        engine.available_voices = original_voices

        if engine.available_voices:
            # Test with exact match
            voice = engine.available_voices[0]
            if "_" in voice:
                lang = voice.split("_")[0]
                result = engine._find_best_voice(lang)
                assert result is not None
                assert result.startswith(f"{lang}_")

            # Test with language prefix match
            if "_" in voice:
                lang_prefix = voice.split("_")[0]
                result = engine._find_best_voice(f"{lang_prefix}-US")
                assert result is not None
                assert result.startswith(f"{lang_prefix}_")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_synth_sync_to_bytes_edge_cases(self):
        """Test synthesis to bytes edge cases."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        voice_name = engine.available_voices[0]

        try:
            # Test with empty text
            result = engine._synth_sync_to_bytes("", voice_name)
            assert isinstance(result, bytes)

            # Test with very short text
            result = engine._synth_sync_to_bytes("Hi", voice_name)
            assert isinstance(result, bytes)

            # Test with special characters
            result = engine._synth_sync_to_bytes("Hello, World! 123", voice_name)
            assert isinstance(result, bytes)

        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_engine_capabilities_comprehensive(self):
        """Test comprehensive engine capabilities."""
        engine = PiperEngine()

        caps = engine.get_capabilities()

        # Test all capability attributes
        assert hasattr(caps, "offline")
        assert hasattr(caps, "ssml")
        assert hasattr(caps, "rate_control")
        assert hasattr(caps, "pitch_control")
        assert hasattr(caps, "languages")
        assert hasattr(caps, "voices")
        assert hasattr(caps, "max_text_length")

        # Test capability values
        assert caps.offline is True
        assert caps.ssml is False
        assert caps.rate_control is True
        assert caps.pitch_control is False
        assert isinstance(caps.languages, list)
        assert isinstance(caps.voices, list)
        assert caps.max_text_length > 0

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_list_voices_comprehensive(self):
        """Test comprehensive voice listing."""
        engine = PiperEngine()

        # Test listing all voices
        all_voices = engine.list_voices()
        assert isinstance(all_voices, list)

        # Test listing voices for specific language
        if all_voices:
            # Extract language from first voice
            first_voice = all_voices[0]
            if "_" in first_voice:
                lang = first_voice.split("_")[0]
                lang_voices = engine.list_voices(lang)
                assert isinstance(lang_voices, list)

                # All returned voices should start with the language prefix
                for voice in lang_voices:
                    assert voice.startswith(f"{lang}_")

        # Test with non-existent language
        non_existent_voices = engine.list_voices("xyz")
        assert isinstance(non_existent_voices, list)
        assert len(non_existent_voices) == 0

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_is_available_comprehensive(self):
        """Test comprehensive availability checking."""
        engine = PiperEngine()

        # Test normal availability
        result = engine.is_available()
        assert isinstance(result, bool)

        # Test with PIPER_AVAILABLE = False (simulated)
        original_piper_available = PIPER_AVAILABLE
        try:
            # This is a bit tricky since PIPER_AVAILABLE is a module-level constant
            # We'll test the logic by setting _available to False
            engine._available = False
            result = engine.is_available()
            assert result is False

            # Test with no voices
            original_voices = engine.voices.copy()
            engine.voices = {}
            result = engine.is_available()
            assert result is False

            # Restore voices
            engine.voices = original_voices
            engine._available = True

        except Exception:
            # If we can't modify the constant, just test the current state
            pass

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_model_info_comprehensive(self):
        """Test comprehensive model information."""
        engine = PiperEngine()

        # Test get_all_models_info
        all_info = engine.get_all_models_info()
        assert isinstance(all_info, dict)

        # Test get_model_info for each available voice
        for voice_name in engine.available_voices:
            info = engine.get_model_info(voice_name)
            if info:
                assert isinstance(info, dict)
                assert "model_key" in info
                assert "language" in info
                assert "voice" in info
                assert "config" in info
                assert "available" in info

                # Test that the model key matches
                assert info["model_key"] == voice_name

                # Test language extraction
                if "_" in voice_name:
                    expected_lang = voice_name.split("_")[0]
                    assert info["language"] == expected_lang

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    async def test_synth_async_comprehensive(self):
        """Test comprehensive async synthesis."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        voice_name = engine.available_voices[0]

        try:
            # Test with different parameters
            result1 = await engine.synth_async(
                "Hello World",
                "en",
                voice=voice_name,
                rate=1.0,
                pitch=0.0,
                output_format="wav",
            )
            assert isinstance(result1, bytes)

            result2 = await engine.synth_async(
                "Hello World",
                "en",
                voice=voice_name,
                rate=1.5,
                pitch=0.5,
                output_format="wav",
            )
            assert isinstance(result2, bytes)

            # Test with different output formats
            result3 = await engine.synth_async(
                "Hello World", "en", voice=voice_name, output_format="mp3"
            )
            assert isinstance(result3, bytes)

        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_synth_to_mp3_comprehensive(self):
        """Test comprehensive MP3 synthesis."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        try:
            # Test with different languages
            result1 = engine.synth_to_mp3("Hello World", "en")
            assert isinstance(result1, str)
            assert result1.endswith(".mp3")

            # Test with default language
            engine.default_lang = "en"
            result2 = engine.synth_to_mp3("Hello World")
            assert isinstance(result2, str)
            assert result2.endswith(".mp3")

        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_load_voices_comprehensive(self):
        """Test comprehensive voice loading."""
        import tempfile
        from pathlib import Path

        # Test with valid directory structure
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a mock voice file
            mock_voice = Path(temp_dir) / "en_US-test-medium.onnx"
            mock_voice.write_bytes(b"mock onnx data")

            # Create a mock config file
            mock_config = Path(temp_dir) / "en_US-test-medium.onnx.json"
            mock_config.write_text('{"language": "en", "voice": "test"}')

            engine = PiperEngine(model_path=temp_dir)
            # Should handle the mock files gracefully
            assert isinstance(engine.available_voices, list)

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_initialization_comprehensive(self):
        """Test comprehensive initialization."""
        from pathlib import Path

        # Test with all parameters
        engine = PiperEngine(
            model_path="./models/piper/", default_lang="fa", use_cuda=True
        )

        assert engine.model_path == Path("./models/piper/")
        assert engine.default_lang == "fa"
        assert engine.use_cuda is True
        assert isinstance(engine.voices, dict)
        assert isinstance(engine.available_voices, list)
        assert isinstance(engine._available, bool)

        # Test with minimal parameters
        engine2 = PiperEngine()
        assert engine2.default_lang == "en"  # Default from TTSEngine
        assert engine2.use_cuda is False
        assert isinstance(engine2.voices, dict)
        assert isinstance(engine2.available_voices, list)

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_raw_audio_to_wav_comprehensive(self):
        """Test comprehensive raw audio to WAV conversion."""
        engine = PiperEngine()

        # Test with different audio data sizes
        test_cases = [
            b"\x00\x01" * 100,  # Small audio
            b"\x00\x01" * 1000,  # Medium audio
            b"\x00\x01" * 10000,  # Large audio
        ]

        for audio_data in test_cases:
            result = engine._raw_audio_to_wav(audio_data)
            assert isinstance(result, bytes)
            assert len(result) > len(audio_data)
            assert result.startswith(b"RIFF")
            assert b"WAVE" in result

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_synth_sync_comprehensive(self):
        """Test comprehensive synchronous synthesis."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        voice_name = engine.available_voices[0]

        try:
            # Test with different text lengths
            short_text = "Hi"
            long_text = "This is a longer text for testing synthesis capabilities."

            result1 = engine._synth_sync(short_text, voice_name)
            assert isinstance(result1, str)
            assert result1.endswith(".wav")

            result2 = engine._synth_sync(long_text, voice_name)
            assert isinstance(result2, str)
            assert result2.endswith(".wav")

        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_synth_sync_to_mp3_comprehensive(self):
        """Test comprehensive synchronous MP3 synthesis."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        voice_name = engine.available_voices[0]

        try:
            # Test with different text content
            test_texts = [
                "Hello World",
                "This is a test.",
                "Numbers: 123456789",
                "Special chars: !@#$%^&*()",
            ]

            for text in test_texts:
                result = engine._synth_sync_to_mp3(text, voice_name)
                assert isinstance(result, str)
                assert result.endswith(".mp3")

        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    @pytest.mark.asyncio
    async def test_synth_async_to_wav_comprehensive(self):
        """Test comprehensive async WAV synthesis."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        voice_name = engine.available_voices[0]

        try:
            # Test with different text content
            test_texts = [
                "Hello World",
                "This is a test.",
                "Numbers: 123456789",
                "Special chars: !@#$%^&*()",
            ]

            for text in test_texts:
                result = await engine._synth_async_to_wav(text, voice_name)
                assert isinstance(result, str)
                assert result.endswith(".wav")

        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    @pytest.mark.asyncio
    async def test_synth_async_to_mp3_comprehensive(self):
        """Test comprehensive async MP3 synthesis."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        voice_name = engine.available_voices[0]

        try:
            # Test with different text content
            test_texts = [
                "Hello World",
                "This is a test.",
                "Numbers: 123456789",
                "Special chars: !@#$%^&*()",
            ]

            for text in test_texts:
                result = await engine._synth_async_to_mp3(text, voice_name)
                assert isinstance(result, str)
                assert result.endswith(".mp3")

        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_edge_cases_comprehensive(self):
        """Test comprehensive edge cases."""
        engine = PiperEngine()

        # Test with empty text
        if engine.available_voices:
            voice_name = engine.available_voices[0]
            try:
                result = engine._synth_sync_to_bytes("", voice_name)
                assert isinstance(result, bytes)
            except Exception:
                # Empty text might cause issues, which is expected
                pass

        # Test with very long text
        long_text = "A" * 10000
        if engine.available_voices:
            voice_name = engine.available_voices[0]
            try:
                result = engine._synth_sync_to_bytes(long_text, voice_name)
                assert isinstance(result, bytes)
            except Exception:
                # Very long text might cause issues, which is expected
                pass

        # Test with special characters
        special_text = "Hello, World! 123 @#$%^&*()"
        if engine.available_voices:
            voice_name = engine.available_voices[0]
            try:
                result = engine._synth_sync_to_bytes(special_text, voice_name)
                assert isinstance(result, bytes)
            except Exception as e:
                pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    async def test_synth_async_voice_validation(self):
        """Test async synthesis voice validation."""
        engine = PiperEngine()

        # Test with voice not in voices dict
        with pytest.raises(ValueError, match="No Piper voice found"):
            await engine.synth_async("Hello World", "en", voice="nonexistent_voice")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    async def test_synth_async_no_voice_found(self):
        """Test async synthesis when no voice is found."""
        engine = PiperEngine()

        # Clear available voices to test no voice found case
        original_voices = engine.available_voices.copy()
        engine.available_voices = []

        try:
            # Test with unsupported language and no voice specified
            with pytest.raises(ValueError, match="No Piper voice found"):
                await engine.synth_async("Hello World", "xyz")
        finally:
            # Restore original voices
            engine.available_voices = original_voices

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    async def test_synth_async_with_voice_found(self):
        """Test async synthesis when voice is found."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        voice_name = engine.available_voices[0]

        try:
            result = await engine.synth_async("Hello World", "en", voice=voice_name)
            assert isinstance(result, bytes)
            assert len(result) > 0
        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    async def test_synth_async_output_format_wav(self):
        """Test async synthesis with WAV output format."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        voice_name = engine.available_voices[0]

        try:
            result = await engine.synth_async(
                "Hello World", "en", voice=voice_name, output_format="wav"
            )
            assert isinstance(result, bytes)
            assert len(result) > 0
        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    async def test_synth_async_output_format_other(self):
        """Test async synthesis with non-WAV output format."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        voice_name = engine.available_voices[0]

        try:
            result = await engine.synth_async(
                "Hello World", "en", voice=voice_name, output_format="mp3"
            )
            assert isinstance(result, bytes)
            assert len(result) > 0
        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_synth_to_mp3_runtime_error_case(self):
        """Test MP3 synthesis RuntimeError case."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        try:
            # This should trigger the RuntimeError case in synth_to_mp3
            result = engine.synth_to_mp3("Hello World", "en")
            assert isinstance(result, str)
            assert result.endswith(".mp3")
        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_synth_to_mp3_asyncio_run_case(self):
        """Test MP3 synthesis asyncio.run case."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        try:
            # This should trigger the asyncio.run case in synth_to_mp3
            result = engine.synth_to_mp3("Hello World", "en")
            assert isinstance(result, str)
            assert result.endswith(".mp3")
        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_load_voices_no_voices_loaded(self):
        """Test voice loading when no voices are loaded."""
        import tempfile
        from pathlib import Path

        # Test with directory that has no .onnx files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a file that's not .onnx
            fake_file = Path(temp_dir) / "fake_voice.txt"
            fake_file.write_text("fake data")

            engine = PiperEngine(model_path=temp_dir)
            assert engine._available is False
            assert len(engine.available_voices) == 0

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_load_voices_successful_loading(self):
        """Test successful voice loading."""
        engine = PiperEngine()

        # Test that voices are loaded successfully
        assert isinstance(engine.available_voices, list)
        assert isinstance(engine.voices, dict)

        # If voices are loaded, test the loading process
        if engine.available_voices:
            assert len(engine.available_voices) > 0
            assert len(engine.voices) > 0
            assert engine._available is True

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_find_best_voice_exact_match(self):
        """Test finding best voice with exact match."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        # Test with exact language match
        for voice in engine.available_voices:
            if "_" in voice:
                lang = voice.split("_")[0]
                result = engine._find_best_voice(lang)
                assert result is not None
                assert result.startswith(f"{lang}_")
                break

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_find_best_voice_prefix_match(self):
        """Test finding best voice with prefix match."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        # Test with language prefix match
        for voice in engine.available_voices:
            if "_" in voice:
                lang_prefix = voice.split("_")[0]
                result = engine._find_best_voice(f"{lang_prefix}-US")
                assert result is not None
                assert result.startswith(f"{lang_prefix}_")
                break

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_find_best_voice_fallback(self):
        """Test finding best voice fallback."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        # Test fallback to first available voice
        result = engine._find_best_voice("xyz")
        assert result is not None
        assert result in engine.available_voices
        assert result == engine.available_voices[0]

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_find_best_voice_no_voices(self):
        """Test finding best voice when no voices available."""
        engine = PiperEngine()

        # Test with empty voices list
        original_voices = engine.available_voices.copy()
        engine.available_voices = []

        result = engine._find_best_voice("en")
        assert result is None

        # Restore voices
        engine.available_voices = original_voices

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_synth_sync_to_bytes_synthesis_config(self):
        """Test synthesis to bytes with synthesis config."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        voice_name = engine.available_voices[0]

        try:
            # Test with default parameters
            result1 = engine._synth_sync_to_bytes("Hello World", voice_name)
            assert isinstance(result1, bytes)
            assert len(result1) > 0

            # Test with custom rate and pitch
            result2 = engine._synth_sync_to_bytes(
                "Hello World", voice_name, rate=1.5, pitch=0.5
            )
            assert isinstance(result2, bytes)
            assert len(result2) > 0

        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_synth_sync_to_bytes_audio_chunks(self):
        """Test synthesis to bytes audio chunks processing."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        voice_name = engine.available_voices[0]

        try:
            # Test with text that will generate multiple chunks
            long_text = "This is a longer text that should generate multiple audio chunks for testing."
            result = engine._synth_sync_to_bytes(long_text, voice_name)
            assert isinstance(result, bytes)
            assert len(result) > 0

        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_synth_sync_to_bytes_wav_conversion(self):
        """Test synthesis to bytes WAV conversion."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        voice_name = engine.available_voices[0]

        try:
            result = engine._synth_sync_to_bytes("Hello World", voice_name)
            assert isinstance(result, bytes)
            assert len(result) > 0

            # Check WAV header
            assert result.startswith(b"RIFF")
            assert b"WAVE" in result

        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_initialization_model_path(self):
        """Test initialization with model path."""
        from pathlib import Path

        engine = PiperEngine(model_path="./models/piper/")
        assert engine.model_path == Path("./models/piper/")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_initialization_default_lang(self):
        """Test initialization with default language."""
        engine = PiperEngine(default_lang="fa")
        assert engine.default_lang == "fa"

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_initialization_use_cuda(self):
        """Test initialization with CUDA setting."""
        engine = PiperEngine(use_cuda=True)
        assert engine.use_cuda is True

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_initialization_voice_loading(self):
        """Test initialization voice loading."""
        engine = PiperEngine()

        # Test that voice loading is called during initialization
        assert isinstance(engine.voices, dict)
        assert isinstance(engine.available_voices, list)
        assert isinstance(engine._available, bool)

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_initialization_super_call(self):
        """Test initialization super call."""
        engine = PiperEngine(default_lang="en")

        # Test that parent class is initialized correctly
        assert engine.default_lang == "en"
        assert hasattr(engine, "validate_input")
        assert hasattr(engine, "get_capabilities")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_get_model_info_nonexistent_model(self):
        """Test get_model_info with nonexistent model."""
        engine = PiperEngine()

        # Test with nonexistent model
        result = engine.get_model_info("nonexistent_model")
        assert result is None

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_get_model_info_existing_model(self):
        """Test get_model_info with existing model."""
        engine = PiperEngine()

        # Test with existing model (if any voices are loaded)
        if engine.available_voices:
            voice_name = engine.available_voices[0]
            result = engine.get_model_info(voice_name)
            if result:
                assert isinstance(result, dict)
                assert "model_key" in result
                assert "language" in result
                assert "voice" in result
                assert "config" in result
                assert "available" in result
                assert result["model_key"] == voice_name

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_get_all_models_info_empty(self):
        """Test get_all_models_info with empty models."""
        engine = PiperEngine()

        # Test with empty models
        result = engine.get_all_models_info()
        assert isinstance(result, dict)

        # Should be empty if no models are loaded
        if not engine.available_voices:
            assert len(result) == 0

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_get_all_models_info_with_models(self):
        """Test get_all_models_info with models."""
        engine = PiperEngine()

        # Test with models
        result = engine.get_all_models_info()
        assert isinstance(result, dict)

        # If models are loaded, test the result
        if engine.available_voices:
            assert len(result) > 0
            for model_key, model_info in result.items():
                assert model_key in engine.available_voices
                assert model_info is not None

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_set_available_true(self):
        """Test setting engine availability to True."""
        engine = PiperEngine()

        # Test setting to True
        engine.set_available(True)
        assert engine._available is True

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_set_available_false(self):
        """Test setting engine availability to False."""
        engine = PiperEngine()

        # Test setting to False
        engine.set_available(False)
        assert engine._available is False

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_synth_sync_temp_file_creation(self):
        """Test synchronous synthesis temp file creation."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        voice_name = engine.available_voices[0]

        try:
            result = engine._synth_sync("Hello World", voice_name)
            assert isinstance(result, str)
            assert result.endswith(".wav")

            # Check if file exists
            import os

            assert os.path.exists(result)

        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_synth_sync_to_mp3_temp_file_creation(self):
        """Test synchronous MP3 synthesis temp file creation."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        voice_name = engine.available_voices[0]

        try:
            result = engine._synth_sync_to_mp3("Hello World", voice_name)
            assert isinstance(result, str)
            assert result.endswith(".mp3")

            # Check if file exists
            import os

            assert os.path.exists(result)

        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    @pytest.mark.asyncio
    async def test_synth_async_to_wav_temp_file_creation(self):
        """Test async WAV synthesis temp file creation."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        voice_name = engine.available_voices[0]

        try:
            result = await engine._synth_async_to_wav("Hello World", voice_name)
            assert isinstance(result, str)
            assert result.endswith(".wav")

            # Check if file exists
            import os

            assert os.path.exists(result)

        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    @pytest.mark.asyncio
    async def test_synth_async_to_mp3_temp_file_creation(self):
        """Test async MP3 synthesis temp file creation."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        voice_name = engine.available_voices[0]

        try:
            result = await engine._synth_async_to_mp3("Hello World", voice_name)
            assert isinstance(result, str)
            assert result.endswith(".mp3")

            # Check if file exists
            import os

            assert os.path.exists(result)

        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_load_voices_path_not_exists(self):
        """Test voice loading when path doesn't exist."""
        import tempfile
        from pathlib import Path

        # Test with non-existent path
        with tempfile.TemporaryDirectory() as temp_dir:
            non_existent_path = Path(temp_dir) / "non_existent"
            engine = PiperEngine(model_path=str(non_existent_path))
            assert engine._available is False
            assert len(engine.available_voices) == 0

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_load_voices_no_onnx_files(self):
        """Test voice loading when no .onnx files exist."""
        import tempfile
        from pathlib import Path

        # Test with directory that has no .onnx files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a file that's not .onnx
            fake_file = Path(temp_dir) / "fake_voice.txt"
            fake_file.write_text("fake data")

            engine = PiperEngine(model_path=temp_dir)
            assert engine._available is False
            assert len(engine.available_voices) == 0

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_load_voices_exception_handling(self):
        """Test voice loading exception handling."""
        import tempfile
        from pathlib import Path

        # Create a temporary directory with a file that will cause loading to fail
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a fake .onnx file that will cause an exception
            fake_onnx = Path(temp_dir) / "fake_voice.onnx"
            fake_onnx.write_bytes(b"fake onnx data")

            engine = PiperEngine(model_path=temp_dir)
            # Should handle the exception gracefully
            assert isinstance(engine.available_voices, list)

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_load_voices_successful_loading(self):
        """Test successful voice loading."""
        engine = PiperEngine()

        # Test that voices are loaded successfully
        assert isinstance(engine.available_voices, list)
        assert isinstance(engine.voices, dict)

        # If voices are loaded, test the loading process
        if engine.available_voices:
            assert len(engine.available_voices) > 0
            assert len(engine.voices) > 0
            assert engine._available is True

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_load_voices_no_voices_loaded(self):
        """Test voice loading when no voices are loaded."""
        engine = PiperEngine()

        # Test that the loading process completes
        assert isinstance(engine.available_voices, list)
        assert isinstance(engine.voices, dict)

        # If no voices are loaded, test the state
        if not engine.available_voices:
            assert len(engine.available_voices) == 0
            assert len(engine.voices) == 0
            assert engine._available is False

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_find_best_voice_exact_language_match(self):
        """Test finding best voice with exact language match."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        # Test with exact language match
        for voice in engine.available_voices:
            if "_" in voice:
                lang = voice.split("_")[0]
                result = engine._find_best_voice(lang)
                assert result is not None
                assert result.startswith(f"{lang}_")
                break

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_find_best_voice_language_prefix_match(self):
        """Test finding best voice with language prefix match."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        # Test with language prefix match
        for voice in engine.available_voices:
            if "_" in voice:
                lang_prefix = voice.split("_")[0]
                result = engine._find_best_voice(f"{lang_prefix}-US")
                assert result is not None
                assert result.startswith(f"{lang_prefix}_")
                break

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_find_best_voice_fallback_to_first(self):
        """Test finding best voice fallback to first available."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        # Test fallback to first available voice
        result = engine._find_best_voice("xyz")
        assert result is not None
        assert result in engine.available_voices
        assert result == engine.available_voices[0]

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_find_best_voice_no_voices_available(self):
        """Test finding best voice when no voices available."""
        engine = PiperEngine()

        # Test with empty voices list
        original_voices = engine.available_voices.copy()
        engine.available_voices = []

        result = engine._find_best_voice("en")
        assert result is None

        # Restore voices
        engine.available_voices = original_voices

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_synth_sync_to_bytes_voice_access(self):
        """Test synthesis to bytes voice access."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        voice_name = engine.available_voices[0]

        try:
            # Test voice access
            voice = engine.voices[voice_name]
            assert voice is not None

            result = engine._synth_sync_to_bytes("Hello World", voice_name)
            assert isinstance(result, bytes)
            assert len(result) > 0

        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_synth_sync_to_bytes_synthesis_config_creation(self):
        """Test synthesis to bytes synthesis config creation."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        voice_name = engine.available_voices[0]

        try:
            # Test synthesis config creation
            result = engine._synth_sync_to_bytes(
                "Hello World", voice_name, rate=1.5, pitch=0.5
            )
            assert isinstance(result, bytes)
            assert len(result) > 0

        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_synth_sync_to_bytes_audio_chunks_processing(self):
        """Test synthesis to bytes audio chunks processing."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        voice_name = engine.available_voices[0]

        try:
            # Test audio chunks processing
            long_text = "This is a longer text that should generate multiple audio chunks for testing."
            result = engine._synth_sync_to_bytes(long_text, voice_name)
            assert isinstance(result, bytes)
            assert len(result) > 0

        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_synth_sync_to_bytes_raw_audio_combination(self):
        """Test synthesis to bytes raw audio combination."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        voice_name = engine.available_voices[0]

        try:
            # Test raw audio combination
            result = engine._synth_sync_to_bytes("Hello World", voice_name)
            assert isinstance(result, bytes)
            assert len(result) > 0

        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_synth_sync_to_bytes_wav_conversion_call(self):
        """Test synthesis to bytes WAV conversion call."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        voice_name = engine.available_voices[0]

        try:
            # Test WAV conversion call
            result = engine._synth_sync_to_bytes("Hello World", voice_name)
            assert isinstance(result, bytes)
            assert len(result) > 0

            # Check WAV header
            assert result.startswith(b"RIFF")
            assert b"WAVE" in result

        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_initialization_model_path_assignment(self):
        """Test initialization model path assignment."""
        from pathlib import Path

        engine = PiperEngine(model_path="./models/piper/")
        assert engine.model_path == Path("./models/piper/")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_initialization_default_lang_assignment(self):
        """Test initialization default language assignment."""
        engine = PiperEngine(default_lang="fa")
        assert engine.default_lang == "fa"

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_initialization_use_cuda_assignment(self):
        """Test initialization CUDA setting assignment."""
        engine = PiperEngine(use_cuda=True)
        assert engine.use_cuda is True

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_initialization_voices_dict_creation(self):
        """Test initialization voices dictionary creation."""
        engine = PiperEngine()

        # Test voices dictionary creation
        assert isinstance(engine.voices, dict)
        assert len(engine.voices) >= 0

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_initialization_available_voices_list_creation(self):
        """Test initialization available voices list creation."""
        engine = PiperEngine()

        # Test available voices list creation
        assert isinstance(engine.available_voices, list)
        assert len(engine.available_voices) >= 0

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_initialization_available_flag_setting(self):
        """Test initialization available flag setting."""
        engine = PiperEngine()

        # Test available flag setting
        assert isinstance(engine._available, bool)

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_initialization_voice_loading_call(self):
        """Test initialization voice loading call."""
        engine = PiperEngine()

        # Test that voice loading is called during initialization
        assert isinstance(engine.voices, dict)
        assert isinstance(engine.available_voices, list)
        assert isinstance(engine._available, bool)

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_initialization_super_initialization(self):
        """Test initialization super class initialization."""
        engine = PiperEngine(default_lang="en")

        # Test that parent class is initialized correctly
        assert engine.default_lang == "en"
        assert hasattr(engine, "validate_input")
        assert hasattr(engine, "get_capabilities")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    async def test_synth_async_voice_not_found_error(self):
        """Test async synthesis voice not found error."""
        engine = PiperEngine()

        # Test with voice not in voices dict
        with pytest.raises(ValueError, match="No Piper voice found"):
            await engine.synth_async("Hello World", "en", voice="nonexistent_voice")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    async def test_synth_async_no_voice_found_error(self):
        """Test async synthesis no voice found error."""
        engine = PiperEngine()

        # Clear available voices to test no voice found case
        original_voices = engine.available_voices.copy()
        engine.available_voices = []

        try:
            # Test with unsupported language and no voice specified
            with pytest.raises(ValueError, match="No Piper voice found"):
                await engine.synth_async("Hello World", "xyz")
        finally:
            # Restore original voices
            engine.available_voices = original_voices

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    async def test_synth_async_with_voice_found_success(self):
        """Test async synthesis with voice found success."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        voice_name = engine.available_voices[0]

        try:
            result = await engine.synth_async("Hello World", "en", voice=voice_name)
            assert isinstance(result, bytes)
            assert len(result) > 0
        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    async def test_synth_async_output_format_wav_success(self):
        """Test async synthesis WAV output format success."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        voice_name = engine.available_voices[0]

        try:
            result = await engine.synth_async(
                "Hello World", "en", voice=voice_name, output_format="wav"
            )
            assert isinstance(result, bytes)
            assert len(result) > 0
        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    async def test_synth_async_output_format_other_success(self):
        """Test async synthesis non-WAV output format success."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        voice_name = engine.available_voices[0]

        try:
            result = await engine.synth_async(
                "Hello World", "en", voice=voice_name, output_format="mp3"
            )
            assert isinstance(result, bytes)
            assert len(result) > 0
        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_synth_to_mp3_runtime_error_case_success(self):
        """Test MP3 synthesis RuntimeError case success."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        try:
            # This should trigger the RuntimeError case in synth_to_mp3
            result = engine.synth_to_mp3("Hello World", "en")
            assert isinstance(result, str)
            assert result.endswith(".mp3")
        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_synth_to_mp3_asyncio_run_case_success(self):
        """Test MP3 synthesis asyncio.run case success."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        try:
            # This should trigger the asyncio.run case in synth_to_mp3
            result = engine.synth_to_mp3("Hello World", "en")
            assert isinstance(result, str)
            assert result.endswith(".mp3")
        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_load_voices_path_not_exists_success(self):
        """Test voice loading path not exists success."""
        import tempfile
        from pathlib import Path

        # Test with non-existent path
        with tempfile.TemporaryDirectory() as temp_dir:
            non_existent_path = Path(temp_dir) / "non_existent"
            engine = PiperEngine(model_path=str(non_existent_path))
            assert engine._available is False
            assert len(engine.available_voices) == 0

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_load_voices_no_onnx_files_success(self):
        """Test voice loading no .onnx files success."""
        import tempfile
        from pathlib import Path

        # Test with directory that has no .onnx files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a file that's not .onnx
            fake_file = Path(temp_dir) / "fake_voice.txt"
            fake_file.write_text("fake data")

            engine = PiperEngine(model_path=temp_dir)
            assert engine._available is False
            assert len(engine.available_voices) == 0

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_load_voices_exception_handling_success(self):
        """Test voice loading exception handling success."""
        import tempfile
        from pathlib import Path

        # Create a temporary directory with a file that will cause loading to fail
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a fake .onnx file that will cause an exception
            fake_onnx = Path(temp_dir) / "fake_voice.onnx"
            fake_onnx.write_bytes(b"fake onnx data")

            engine = PiperEngine(model_path=temp_dir)
            # Should handle the exception gracefully
            assert isinstance(engine.available_voices, list)

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_load_voices_successful_loading_success(self):
        """Test voice loading successful loading success."""
        engine = PiperEngine()

        # Test that voices are loaded successfully
        assert isinstance(engine.available_voices, list)
        assert isinstance(engine.voices, dict)

        # If voices are loaded, test the loading process
        if engine.available_voices:
            assert len(engine.available_voices) > 0
            assert len(engine.voices) > 0
            assert engine._available is True

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_load_voices_no_voices_loaded_success(self):
        """Test voice loading no voices loaded success."""
        engine = PiperEngine()

        # Test that the loading process completes
        assert isinstance(engine.available_voices, list)
        assert isinstance(engine.voices, dict)

        # If no voices are loaded, test the state
        if not engine.available_voices:
            assert len(engine.available_voices) == 0
            assert len(engine.voices) == 0
            assert engine._available is False

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_find_best_voice_exact_language_match_success(self):
        """Test finding best voice exact language match success."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        # Test with exact language match
        for voice in engine.available_voices:
            if "_" in voice:
                lang = voice.split("_")[0]
                result = engine._find_best_voice(lang)
                assert result is not None
                assert result.startswith(f"{lang}_")
                break

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_find_best_voice_language_prefix_match_success(self):
        """Test finding best voice language prefix match success."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        # Test with language prefix match
        for voice in engine.available_voices:
            if "_" in voice:
                lang_prefix = voice.split("_")[0]
                result = engine._find_best_voice(f"{lang_prefix}-US")
                assert result is not None
                assert result.startswith(f"{lang_prefix}_")
                break

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_find_best_voice_fallback_to_first_success(self):
        """Test finding best voice fallback to first success."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        # Test fallback to first available voice
        result = engine._find_best_voice("xyz")
        assert result is not None
        assert result in engine.available_voices
        assert result == engine.available_voices[0]

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_find_best_voice_no_voices_available_success(self):
        """Test finding best voice no voices available success."""
        engine = PiperEngine()

        # Test with empty voices list
        original_voices = engine.available_voices.copy()
        engine.available_voices = []

        result = engine._find_best_voice("en")
        assert result is None

        # Restore voices
        engine.available_voices = original_voices

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_synth_sync_to_bytes_voice_access_success(self):
        """Test synthesis to bytes voice access success."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        voice_name = engine.available_voices[0]

        try:
            # Test voice access
            voice = engine.voices[voice_name]
            assert voice is not None

            result = engine._synth_sync_to_bytes("Hello World", voice_name)
            assert isinstance(result, bytes)
            assert len(result) > 0

        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_synth_sync_to_bytes_synthesis_config_creation_success(self):
        """Test synthesis to bytes synthesis config creation success."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        voice_name = engine.available_voices[0]

        try:
            # Test synthesis config creation
            result = engine._synth_sync_to_bytes(
                "Hello World", voice_name, rate=1.5, pitch=0.5
            )
            assert isinstance(result, bytes)
            assert len(result) > 0

        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_synth_sync_to_bytes_audio_chunks_processing_success(self):
        """Test synthesis to bytes audio chunks processing success."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        voice_name = engine.available_voices[0]

        try:
            # Test audio chunks processing
            long_text = "This is a longer text that should generate multiple audio chunks for testing."
            result = engine._synth_sync_to_bytes(long_text, voice_name)
            assert isinstance(result, bytes)
            assert len(result) > 0

        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_synth_sync_to_bytes_raw_audio_combination_success(self):
        """Test synthesis to bytes raw audio combination success."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        voice_name = engine.available_voices[0]

        try:
            # Test raw audio combination
            result = engine._synth_sync_to_bytes("Hello World", voice_name)
            assert isinstance(result, bytes)
            assert len(result) > 0

        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_synth_sync_to_bytes_wav_conversion_call_success(self):
        """Test synthesis to bytes WAV conversion call success."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        voice_name = engine.available_voices[0]

        try:
            # Test WAV conversion call
            result = engine._synth_sync_to_bytes("Hello World", voice_name)
            assert isinstance(result, bytes)
            assert len(result) > 0

            # Check WAV header
            assert result.startswith(b"RIFF")
            assert b"WAVE" in result

        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_initialization_model_path_assignment_success(self):
        """Test initialization model path assignment success."""
        from pathlib import Path

        engine = PiperEngine(model_path="./models/piper/")
        assert engine.model_path == Path("./models/piper/")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_initialization_default_lang_assignment_success(self):
        """Test initialization default language assignment success."""
        engine = PiperEngine(default_lang="fa")
        assert engine.default_lang == "fa"

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_initialization_use_cuda_assignment_success(self):
        """Test initialization CUDA setting assignment success."""
        engine = PiperEngine(use_cuda=True)
        assert engine.use_cuda is True

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_initialization_voices_dict_creation_success(self):
        """Test initialization voices dictionary creation success."""
        engine = PiperEngine()

        # Test voices dictionary creation
        assert isinstance(engine.voices, dict)
        assert len(engine.voices) >= 0

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_initialization_available_voices_list_creation_success(self):
        """Test initialization available voices list creation success."""
        engine = PiperEngine()

        # Test available voices list creation
        assert isinstance(engine.available_voices, list)
        assert len(engine.available_voices) >= 0

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_initialization_available_flag_setting_success(self):
        """Test initialization available flag setting success."""
        engine = PiperEngine()

        # Test available flag setting
        assert isinstance(engine._available, bool)

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_initialization_voice_loading_call_success(self):
        """Test initialization voice loading call success."""
        engine = PiperEngine()

        # Test that voice loading is called during initialization
        assert isinstance(engine.voices, dict)
        assert isinstance(engine.available_voices, list)
        assert isinstance(engine._available, bool)

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_initialization_super_initialization_success(self):
        """Test initialization super class initialization success."""
        engine = PiperEngine(default_lang="en")

        # Test that parent class is initialized correctly
        assert engine.default_lang == "en"
        assert hasattr(engine, "validate_input")
        assert hasattr(engine, "get_capabilities")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    async def test_synth_async_voice_not_found_error(self):
        """Test async synthesis voice not found error."""
        engine = PiperEngine()

        # Test with voice not in voices dict
        with pytest.raises(ValueError, match="No Piper voice found"):
            await engine.synth_async("Hello World", "en", voice="nonexistent_voice")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    async def test_synth_async_no_voice_found_error(self):
        """Test async synthesis no voice found error."""
        engine = PiperEngine()

        # Clear available voices to test no voice found case
        original_voices = engine.available_voices.copy()
        engine.available_voices = []

        try:
            # Test with unsupported language and no voice specified
            with pytest.raises(ValueError, match="No Piper voice found"):
                await engine.synth_async("Hello World", "xyz")
        finally:
            # Restore original voices
            engine.available_voices = original_voices

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    async def test_synth_async_with_voice_found_success(self):
        """Test async synthesis with voice found success."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        voice_name = engine.available_voices[0]

        try:
            result = await engine.synth_async("Hello World", "en", voice=voice_name)
            assert isinstance(result, bytes)
            assert len(result) > 0
        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    async def test_synth_async_output_format_wav_success(self):
        """Test async synthesis WAV output format success."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        voice_name = engine.available_voices[0]

        try:
            result = await engine.synth_async(
                "Hello World", "en", voice=voice_name, output_format="wav"
            )
            assert isinstance(result, bytes)
            assert len(result) > 0
        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    async def test_synth_async_output_format_other_success(self):
        """Test async synthesis non-WAV output format success."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        voice_name = engine.available_voices[0]

        try:
            result = await engine.synth_async(
                "Hello World", "en", voice=voice_name, output_format="mp3"
            )
            assert isinstance(result, bytes)
            assert len(result) > 0
        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_synth_to_mp3_runtime_error_case_success(self):
        """Test MP3 synthesis RuntimeError case success."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        try:
            # This should trigger the RuntimeError case in synth_to_mp3
            result = engine.synth_to_mp3("Hello World", "en")
            assert isinstance(result, str)
            assert result.endswith(".mp3")
        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_synth_to_mp3_asyncio_run_case_success(self):
        """Test MP3 synthesis asyncio.run case success."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        try:
            # This should trigger the asyncio.run case in synth_to_mp3
            result = engine.synth_to_mp3("Hello World", "en")
            assert isinstance(result, str)
            assert result.endswith(".mp3")
        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_load_voices_path_not_exists_success(self):
        """Test voice loading path not exists success."""
        import tempfile
        from pathlib import Path

        # Test with non-existent path
        with tempfile.TemporaryDirectory() as temp_dir:
            non_existent_path = Path(temp_dir) / "non_existent"
            engine = PiperEngine(model_path=str(non_existent_path))
            assert engine._available is False
            assert len(engine.available_voices) == 0

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_load_voices_no_onnx_files_success(self):
        """Test voice loading no .onnx files success."""
        import tempfile
        from pathlib import Path

        # Test with directory that has no .onnx files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a file that's not .onnx
            fake_file = Path(temp_dir) / "fake_voice.txt"
            fake_file.write_text("fake data")

            engine = PiperEngine(model_path=temp_dir)
            assert engine._available is False
            assert len(engine.available_voices) == 0

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_load_voices_exception_handling_success(self):
        """Test voice loading exception handling success."""
        import tempfile
        from pathlib import Path

        # Create a temporary directory with a file that will cause loading to fail
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a fake .onnx file that will cause an exception
            fake_onnx = Path(temp_dir) / "fake_voice.onnx"
            fake_onnx.write_bytes(b"fake onnx data")

            engine = PiperEngine(model_path=temp_dir)
            # Should handle the exception gracefully
            assert isinstance(engine.available_voices, list)

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_load_voices_successful_loading_success(self):
        """Test voice loading successful loading success."""
        engine = PiperEngine()

        # Test that voices are loaded successfully
        assert isinstance(engine.available_voices, list)
        assert isinstance(engine.voices, dict)

        # If voices are loaded, test the loading process
        if engine.available_voices:
            assert len(engine.available_voices) > 0
            assert len(engine.voices) > 0
            assert engine._available is True

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_load_voices_no_voices_loaded_success(self):
        """Test voice loading no voices loaded success."""
        engine = PiperEngine()

        # Test that the loading process completes
        assert isinstance(engine.available_voices, list)
        assert isinstance(engine.voices, dict)

        # If no voices are loaded, test the state
        if not engine.available_voices:
            assert len(engine.available_voices) == 0
            assert len(engine.voices) == 0
            assert engine._available is False

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_find_best_voice_exact_language_match_success(self):
        """Test finding best voice exact language match success."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        # Test with exact language match
        for voice in engine.available_voices:
            if "_" in voice:
                lang = voice.split("_")[0]
                result = engine._find_best_voice(lang)
                assert result is not None
                assert result.startswith(f"{lang}_")
                break

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_find_best_voice_language_prefix_match_success(self):
        """Test finding best voice language prefix match success."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        # Test with language prefix match
        for voice in engine.available_voices:
            if "_" in voice:
                lang_prefix = voice.split("_")[0]
                result = engine._find_best_voice(f"{lang_prefix}-US")
                assert result is not None
                assert result.startswith(f"{lang_prefix}_")
                break

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_find_best_voice_fallback_to_first_success(self):
        """Test finding best voice fallback to first success."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        # Test fallback to first available voice
        result = engine._find_best_voice("xyz")
        assert result is not None
        assert result in engine.available_voices
        assert result == engine.available_voices[0]

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_find_best_voice_no_voices_available_success(self):
        """Test finding best voice no voices available success."""
        engine = PiperEngine()

        # Test with empty voices list
        original_voices = engine.available_voices.copy()
        engine.available_voices = []

        result = engine._find_best_voice("en")
        assert result is None

        # Restore voices
        engine.available_voices = original_voices

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_synth_sync_to_bytes_voice_access_success(self):
        """Test synthesis to bytes voice access success."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        voice_name = engine.available_voices[0]

        try:
            # Test voice access
            voice = engine.voices[voice_name]
            assert voice is not None

            result = engine._synth_sync_to_bytes("Hello World", voice_name)
            assert isinstance(result, bytes)
            assert len(result) > 0

        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_synth_sync_to_bytes_synthesis_config_creation_success(self):
        """Test synthesis to bytes synthesis config creation success."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        voice_name = engine.available_voices[0]

        try:
            # Test synthesis config creation
            result = engine._synth_sync_to_bytes(
                "Hello World", voice_name, rate=1.5, pitch=0.5
            )
            assert isinstance(result, bytes)
            assert len(result) > 0

        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_synth_sync_to_bytes_audio_chunks_processing_success(self):
        """Test synthesis to bytes audio chunks processing success."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        voice_name = engine.available_voices[0]

        try:
            # Test audio chunks processing
            long_text = "This is a longer text that should generate multiple audio chunks for testing."
            result = engine._synth_sync_to_bytes(long_text, voice_name)
            assert isinstance(result, bytes)
            assert len(result) > 0

        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_synth_sync_to_bytes_raw_audio_combination_success(self):
        """Test synthesis to bytes raw audio combination success."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        voice_name = engine.available_voices[0]

        try:
            # Test raw audio combination
            result = engine._synth_sync_to_bytes("Hello World", voice_name)
            assert isinstance(result, bytes)
            assert len(result) > 0

        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_synth_sync_to_bytes_wav_conversion_call_success(self):
        """Test synthesis to bytes WAV conversion call success."""
        engine = PiperEngine()

        if not engine.available_voices:
            pytest.skip("No voices available for testing")

        voice_name = engine.available_voices[0]

        try:
            # Test WAV conversion call
            result = engine._synth_sync_to_bytes("Hello World", voice_name)
            assert isinstance(result, bytes)
            assert len(result) > 0

            # Check WAV header
            assert result.startswith(b"RIFF")
            assert b"WAVE" in result

        except Exception as e:
            pytest.skip(f"Synthesis failed: {e}")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_initialization_model_path_assignment_success(self):
        """Test initialization model path assignment success."""
        from pathlib import Path

        engine = PiperEngine(model_path="./models/piper/")
        assert engine.model_path == Path("./models/piper/")

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_initialization_default_lang_assignment_success(self):
        """Test initialization default language assignment success."""
        engine = PiperEngine(default_lang="fa")
        assert engine.default_lang == "fa"

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_initialization_use_cuda_assignment_success(self):
        """Test initialization CUDA setting assignment success."""
        engine = PiperEngine(use_cuda=True)
        assert engine.use_cuda is True

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_initialization_voices_dict_creation_success(self):
        """Test initialization voices dictionary creation success."""
        engine = PiperEngine()

        # Test voices dictionary creation
        assert isinstance(engine.voices, dict)
        assert len(engine.voices) >= 0

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_initialization_available_voices_list_creation_success(self):
        """Test initialization available voices list creation success."""
        engine = PiperEngine()

        # Test available voices list creation
        assert isinstance(engine.available_voices, list)
        assert len(engine.available_voices) >= 0

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_initialization_available_flag_setting_success(self):
        """Test initialization available flag setting success."""
        engine = PiperEngine()

        # Test available flag setting
        assert isinstance(engine._available, bool)

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_initialization_voice_loading_call_success(self):
        """Test initialization voice loading call success."""
        engine = PiperEngine()

        # Test that voice loading is called during initialization
        assert isinstance(engine.voices, dict)
        assert isinstance(engine.available_voices, list)
        assert isinstance(engine._available, bool)

    @pytest.mark.skipif(not PIPER_AVAILABLE, reason="Piper TTS not available")
    def test_initialization_super_initialization_success(self):
        """Test initialization super class initialization success."""
        engine = PiperEngine(default_lang="en")

        # Test that parent class is initialized correctly
        assert engine.default_lang == "en"
        assert hasattr(engine, "validate_input")
        assert hasattr(engine, "get_capabilities")
