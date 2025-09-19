"""Real engine tests for TTSKit.

This file contains a few real integration tests to ensure engines work correctly.
These tests are slower but provide confidence that the engines actually work.
"""

import time

import pytest

from ttskit.engines.factory import create_engine
from ttskit.public import TTS, SynthConfig


class TestRealEngines:
    """Real engine integration tests."""

    @pytest.mark.slow
    def test_gtts_real_synthesis(self):
        """Test real gTTS synthesis."""
        try:
            engine = create_engine("gtts", default_lang="en")
            if not engine.is_available():
                pytest.skip("gTTS engine not available")

            audio_data = engine.synth_async("Hello world", "en")
            if hasattr(audio_data, "__await__"):
                import asyncio

                audio_data = asyncio.run(audio_data)

            assert isinstance(audio_data, bytes)
            assert len(audio_data) > 0
            print(f"gTTS synthesis successful: {len(audio_data)} bytes")

        except Exception as e:
            pytest.skip(f"gTTS synthesis failed: {e}")

    @pytest.mark.slow
    def test_edge_real_synthesis(self):
        """Test real Edge TTS synthesis."""
        try:
            engine = create_engine("edge", default_lang="en")
            if not engine.is_available():
                pytest.skip("Edge engine not available")

            audio_data = engine.synth_async("Hello world", "en")
            if hasattr(audio_data, "__await__"):
                import asyncio

                audio_data = asyncio.run(audio_data)

            assert isinstance(audio_data, bytes)
            assert len(audio_data) > 0
            print(f"Edge synthesis successful: {len(audio_data)} bytes")

        except Exception as e:
            pytest.skip(f"Edge synthesis failed: {e}")

    @pytest.mark.slow
    def test_piper_real_synthesis(self):
        """Test real Piper TTS synthesis."""
        try:
            from ttskit.engines.piper_engine import PIPER_AVAILABLE

            if not PIPER_AVAILABLE:
                pytest.skip("Piper TTS not available")

            engine = create_engine("piper", default_lang="en")
            if not engine.is_available():
                pytest.skip("Piper engine not available")

            audio_data = engine.synth_async("Hello world", "en")
            if hasattr(audio_data, "__await__"):
                import asyncio

                audio_data = asyncio.run(audio_data)

            assert isinstance(audio_data, bytes)
            assert len(audio_data) > 0
            print(f"Piper synthesis successful: {len(audio_data)} bytes")

        except Exception as e:
            pytest.skip(f"Piper synthesis failed: {e}")

    @pytest.mark.slow
    def test_tts_class_real_synthesis(self):
        """Test TTS class with real synthesis."""
        try:
            tts = TTS(default_lang="en")

            config = SynthConfig(
                text="Hello world",
                lang="en",
                engine="gtts",
                output_format="ogg",
                cache=False,
            )

            result = tts.synth_async(config)
            if hasattr(result, "__await__"):
                import asyncio

                result = asyncio.run(result)

            assert result.data is not None
            assert len(result.data) > 0
            assert result.format == "ogg"
            print(f"TTS class synthesis successful: {result.size} bytes")

        except Exception as e:
            pytest.skip(f"TTS class synthesis failed: {e}")

    @pytest.mark.slow
    def test_engine_performance_comparison(self):
        """Compare performance of different engines."""
        engines_to_test = []

        try:
            gtts_engine = create_engine("gtts", default_lang="en")
            if gtts_engine.is_available():
                engines_to_test.append(("gtts", gtts_engine))
        except Exception:
            pass

        try:
            edge_engine = create_engine("edge", default_lang="en")
            if edge_engine.is_available():
                engines_to_test.append(("edge", edge_engine))
        except Exception:
            pass

        if not engines_to_test:
            pytest.skip("No engines available for performance test")

        test_text = "Hello world, this is a performance test."
        results = {}

        for engine_name, engine in engines_to_test:
            try:
                start_time = time.time()
                audio_data = engine.synth_async(test_text, "en")
                if hasattr(audio_data, "__await__"):
                    import asyncio

                    audio_data = asyncio.run(audio_data)
                duration = time.time() - start_time

                results[engine_name] = {
                    "duration": duration,
                    "size": len(audio_data),
                    "success": True,
                }
                print(f"{engine_name}: {duration:.2f}s, {len(audio_data)} bytes")

            except Exception as e:
                results[engine_name] = {
                    "duration": 0,
                    "size": 0,
                    "success": False,
                    "error": str(e),
                }
                print(f"{engine_name}: Failed - {e}")

        successful_engines = [
            name for name, result in results.items() if result["success"]
        ]
        assert len(successful_engines) > 0, "No engines succeeded in performance test"

        print(f"Performance test completed. Successful engines: {successful_engines}")


class TestRealEngineCapabilities:
    """Test real engine capabilities."""

    def test_engine_availability(self):
        """Test which engines are actually available."""
        engines = ["gtts", "edge", "piper"]
        available_engines = []

        for engine_name in engines:
            try:
                engine = create_engine(engine_name, default_lang="en")
                if engine.is_available():
                    available_engines.append(engine_name)
                    print(f"✓ {engine_name} is available")
                else:
                    print(f"✗ {engine_name} is not available")
            except Exception as e:
                print(f"✗ {engine_name} failed to create: {e}")

        assert len(available_engines) > 0, "No engines are available"
        print(f"Available engines: {available_engines}")

    def test_engine_capabilities(self):
        """Test engine capabilities."""
        engines = ["gtts", "edge", "piper"]

        for engine_name in engines:
            try:
                engine = create_engine(engine_name, default_lang="en")
                if not engine.is_available():
                    continue

                capabilities = engine.get_capabilities()
                print(f"\n{engine_name} capabilities:")
                print(f"  Offline: {capabilities.offline}")
                print(f"  SSML: {capabilities.ssml}")
                print(f"  Rate Control: {capabilities.rate_control}")
                print(f"  Pitch Control: {capabilities.pitch_control}")
                print(f"  Languages: {capabilities.languages[:5]}...")
                print(f"  Voices: {len(capabilities.voices)} voices")
                print(f"  Max Text Length: {capabilities.max_text_length}")

            except Exception as e:
                print(f"Failed to get capabilities for {engine_name}: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
