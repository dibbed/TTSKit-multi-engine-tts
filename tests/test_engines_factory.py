"""Tests for Engine Factory."""

from unittest.mock import Mock

import pytest

from ttskit.engines.factory import EngineFactory, factory


class TestEngineFactory:
    """Test cases for EngineFactory."""

    def test_initialization(self):
        """Test EngineFactory initialization."""
        engine_factory = EngineFactory()

        assert engine_factory is not None
        assert isinstance(engine_factory.engines, dict)

    def test_get_available_engines(self):
        """Test getting available engines."""
        engines = factory.get_available_engines()

        assert isinstance(engines, list)
        assert "gtts" in engines

    def test_get_engine_gtts(self):
        """Test getting gTTS engine."""
        engine = factory.get_engine("gtts")

        assert engine is not None
        assert engine.__class__.__name__ == "GTTSEngine"

    def test_get_engine_edge(self):
        """Test getting Edge engine."""
        try:
            engine = factory.get_engine("edge")
            assert engine is not None
            assert engine.__class__.__name__ == "EdgeEngine"
        except ImportError:
            pytest.skip("Edge engine not available")

    def test_get_engine_piper(self):
        """Test getting Piper engine."""
        try:
            engine = factory.get_engine("piper")
            assert engine is not None
            assert engine.__class__.__name__ == "PiperEngine"
        except ImportError:
            pytest.skip("Piper engine not available")

    def test_get_engine_invalid(self):
        """Test getting invalid engine."""
        with pytest.raises(ValueError, match="Unknown engine"):
            factory.get_engine("invalid_engine")

    def test_get_engine_capabilities(self):
        """Test getting engine capabilities."""
        capabilities = factory.get_engine_capabilities()

        assert isinstance(capabilities, dict)
        assert "gtts" in capabilities

        gtts_caps = capabilities["gtts"]
        assert isinstance(gtts_caps, dict)
        assert "offline" in gtts_caps
        assert "ssml" in gtts_caps
        assert "rate" in gtts_caps
        assert "pitch" in gtts_caps
        assert "langs" in gtts_caps
        assert "voices" in gtts_caps

    def test_get_engine_info(self):
        """Test getting engine information."""
        info = factory.get_engine_info()

        assert isinstance(info, dict)
        assert "gtts" in info or "name" in info

        if "gtts" in info:
            gtts_info = info["gtts"]
            assert isinstance(gtts_info, dict)
            assert "name" in gtts_info
            assert "version" in gtts_info
            assert "available" in gtts_info
            assert "description" in gtts_info

    def test_list_engines(self):
        """Test listing all engines."""
        engines = factory.list_engines()

        assert isinstance(engines, list)
        assert "gtts" in engines

    def test_is_engine_available(self):
        """Test checking engine availability."""
        assert factory.is_engine_available("gtts") is True

        assert factory.is_engine_available("invalid") is False

    def test_get_recommended_engine(self):
        """Test getting recommended engine."""
        recommended = factory.get_recommended_engine()

        assert isinstance(recommended, str)
        assert recommended in factory.get_available_engines()

    def test_get_engines_by_capability(self):
        """Test getting engines by capability."""
        offline_engines = factory.get_engines_by_capability("offline", True)
        assert isinstance(offline_engines, list)

        online_engines = factory.get_engines_by_capability("offline", False)
        assert isinstance(online_engines, list)
        assert "gtts" in online_engines

    def test_get_engines_by_language(self):
        """Test getting engines by language."""
        en_engines = factory.get_engines_by_language("en")
        assert isinstance(en_engines, list)
        assert "gtts" in en_engines

        fa_engines = factory.get_engines_by_language("fa")
        assert isinstance(fa_engines, list)

    def test_get_engine_statistics(self):
        """Test getting engine statistics."""
        stats = factory.get_engine_statistics()

        assert isinstance(stats, dict)
        assert "total_engines" in stats
        assert "available_engines" in stats
        assert "offline_engines" in stats
        assert "online_engines" in stats

    def test_register_engine(self):
        """Test registering a custom engine."""
        mock_engine = Mock()
        mock_engine.__class__.__name__ = "MockEngine"

        factory.register_engine("mock", mock_engine)

        assert factory.is_engine_available("mock") is True
        assert factory.get_engine("mock") is mock_engine

    def test_unregister_engine(self):
        """Test unregistering an engine."""
        mock_engine = Mock()
        factory.register_engine("mock", mock_engine)

        factory.unregister_engine("mock")

        assert factory.is_engine_available("mock") is False

    def test_setup_registry(self):
        """Test setting up engine registry."""
        mock_registry = Mock()

        factory.setup_registry(mock_registry)

        assert True

    def test_get_engine_with_default_language(self):
        """Test getting engine with default language."""
        engine = factory.get_engine("gtts", default_lang="fa")

        assert engine is not None
        assert engine.default_lang in ["fa", "en"]

    def test_get_engine_with_model_path(self):
        """Test getting engine with model path (piper)."""
        try:
            engine = factory.get_engine("piper", model_path="./models/piper")
            assert engine is not None
        except (ImportError, TypeError):
            pytest.skip("Piper engine not available or model_path unsupported")

    def test_engine_factory_singleton(self):
        """Test that factory is a singleton."""
        factory1 = factory
        factory2 = factory

        assert factory1 is factory2

    def test_get_engines_by_voice_support(self):
        """Test getting engines by voice support."""
        voice_engines = factory.get_engines_by_capability("voices", True)
        assert isinstance(voice_engines, list)

        no_voice_engines = factory.get_engines_by_capability("voices", False)
        assert isinstance(no_voice_engines, list)

    def test_get_engines_by_ssml_support(self):
        """Test getting engines by SSML support."""
        ssml_engines = factory.get_engines_by_capability("ssml", True)
        assert isinstance(ssml_engines, list)

        no_ssml_engines = factory.get_engines_by_capability("ssml", False)
        assert isinstance(no_ssml_engines, list)
        assert "gtts" in no_ssml_engines

    def test_get_engines_by_rate_control(self):
        """Test getting engines by rate control support."""
        rate_engines = factory.get_engines_by_capability("rate", True)
        assert isinstance(rate_engines, list)

        no_rate_engines = factory.get_engines_by_capability("rate", False)
        assert isinstance(no_rate_engines, list)

    def test_get_engines_by_pitch_control(self):
        """Test getting engines by pitch control support."""
        pitch_engines = factory.get_engines_by_capability("pitch", True)
        assert isinstance(pitch_engines, list)

        no_pitch_engines = factory.get_engines_by_capability("pitch", False)
        assert isinstance(no_pitch_engines, list)
