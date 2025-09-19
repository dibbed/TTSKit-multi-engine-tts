"""
Comprehensive branch coverage tests for ttskit.engines.factory module.

This module tests all conditional branches and error paths to achieve 100% branch coverage.
"""

from unittest.mock import MagicMock, patch

import pytest

from ttskit.engines.factory import (
    _EDGE_AVAILABLE,
    EDGE_AVAILABLE,
    EngineFactory,
    create_engine,
    get_available_engines,
    get_engine_capabilities,
    setup_default_registry,
    setup_registry,
)


class TestEngineFactoryBranchCoverage:
    """Test cases for complete branch coverage in EngineFactory."""

    @pytest.fixture
    def factory(self):
        """Create test factory instance."""
        factory = EngineFactory()
        factory.engine_classes.clear()
        factory.engine_configs.clear()
        factory.engines.clear()
        return factory

    def test_register_default_engines_edge_available(self, factory):
        """Test registering default engines when Edge is available."""
        with patch("ttskit.engines.factory._EDGE_AVAILABLE", True):
            with patch("ttskit.engines.factory.PIPER_AVAILABLE", True):
                factory._register_default_engines()

                assert "gtts" in factory.engine_classes
                assert "edge" in factory.engine_classes
                assert "piper" in factory.engine_classes

    def test_register_default_engines_edge_unavailable(self, factory):
        """Test registering default engines when Edge is unavailable."""
        factory.engine_classes.clear()
        factory.engine_configs.clear()

        with patch("ttskit.engines.factory._EDGE_AVAILABLE", False):
            with patch("ttskit.engines.factory.PIPER_AVAILABLE", True):
                factory._register_default_engines()

                assert "gtts" in factory.engine_classes
                assert "edge" not in factory.engine_classes
                assert "piper" in factory.engine_classes

    def test_register_default_engines_piper_unavailable(self, factory):
        """Test registering default engines when Piper is unavailable."""
        factory.engine_classes.clear()
        factory.engine_configs.clear()

        with patch("ttskit.engines.factory._EDGE_AVAILABLE", True):
            with patch("ttskit.engines.factory.PIPER_AVAILABLE", False):
                factory._register_default_engines()

                assert "gtts" in factory.engine_classes
                assert "edge" in factory.engine_classes
                assert "piper" not in factory.engine_classes

    def test_register_default_engines_both_unavailable(self, factory):
        """Test registering default engines when both Edge and Piper are unavailable."""
        factory.engine_classes.clear()
        factory.engine_configs.clear()

        with patch("ttskit.engines.factory._EDGE_AVAILABLE", False):
            with patch("ttskit.engines.factory.PIPER_AVAILABLE", False):
                factory._register_default_engines()

                assert "gtts" in factory.engine_classes
                assert "edge" not in factory.engine_classes
                assert "piper" not in factory.engine_classes

    def test_create_engine_success(self, factory):
        """Test successful engine creation."""
        mock_engine_class = MagicMock()
        mock_engine_instance = MagicMock()
        mock_engine_class.return_value = mock_engine_instance

        factory.engine_classes["test_engine"] = mock_engine_class

        result = factory.create_engine("test_engine", param1="value1")

        mock_engine_class.assert_called_once_with(param1="value1")
        assert result == mock_engine_instance

    def test_create_engine_not_found(self, factory):
        """Test engine creation when engine not found."""
        with pytest.raises(ValueError, match="Engine 'nonexistent' not found"):
            factory.create_engine("nonexistent")

    def test_get_engine_capabilities_with_name(self, factory):
        """Test getting capabilities for specific engine."""
        capabilities = {"offline": True, "ssml": False}
        factory.engine_configs["test_engine"] = capabilities

        result = factory.get_engine_capabilities("test_engine")
        assert result == capabilities

    def test_get_engine_capabilities_with_none(self, factory):
        """Test getting capabilities for all engines."""
        factory.engine_configs = {
            "engine1": {"offline": True, "rate_control": False},
            "engine2": {"offline": False, "rate_control": True},
        }

        result = factory.get_engine_capabilities(None)

        assert "engine1" in result
        assert "engine2" in result
        assert result["engine1"]["rate"] is False
        assert result["engine1"]["pitch"] is False
        assert result["engine1"]["langs"] == []

    def test_get_engine_capabilities_engine_not_found(self, factory):
        """Test getting capabilities for non-existent engine."""
        result = factory.get_engine_capabilities("nonexistent")
        assert result is None

    def test_create_all_engines_piper_specific_kwargs(self, factory):
        """Test creating all engines with Piper-specific kwargs."""
        mock_piper_class = MagicMock()
        mock_piper_instance = MagicMock()
        mock_piper_class.return_value = mock_piper_instance

        factory.engine_classes["piper"] = mock_piper_class

        kwargs = {
            "model_path": "/path/to/model",
            "use_cuda": True,
            "other_param": "value",
        }
        result = factory.create_all_engines(**kwargs)

        mock_piper_class.assert_called_once_with(
            model_path="/path/to/model", use_cuda=True
        )
        assert "piper" in result

    def test_create_all_engines_gtts_edge_kwargs(self, factory):
        """Test creating all engines with gTTS/Edge kwargs filtering."""
        mock_gtts_class = MagicMock()
        mock_gtts_instance = MagicMock()
        mock_gtts_class.return_value = mock_gtts_instance

        factory.engine_classes["gtts"] = mock_gtts_class

        kwargs = {
            "model_path": "/path/to/model",
            "use_cuda": True,
            "valid_param": "value",
        }
        result = factory.create_all_engines(**kwargs)

        mock_gtts_class.assert_called_once_with(valid_param="value")
        assert "gtts" in result

    def test_create_all_engines_other_engine_kwargs(self, factory):
        """Test creating all engines with other engine kwargs."""
        mock_other_class = MagicMock()
        mock_other_instance = MagicMock()
        mock_other_class.return_value = mock_other_instance

        factory.engine_classes["other_engine"] = mock_other_class

        kwargs = {"param1": "value1", "param2": "value2"}
        result = factory.create_all_engines(**kwargs)

        mock_other_class.assert_called_once_with(param1="value1", param2="value2")
        assert "other_engine" in result

    def test_create_all_engines_exception_handling(self, factory):
        """Test exception handling in create_all_engines."""
        mock_failing_class = MagicMock()
        mock_failing_class.side_effect = Exception("Engine creation failed")

        factory.engine_classes["failing_engine"] = mock_failing_class

        with patch("ttskit.engines.factory.logger") as mock_logger:
            result = factory.create_all_engines()

            mock_logger.warning.assert_called_once()
            assert "failing_engine" not in result

    def test_setup_registry_with_piper(self, factory):
        """Test setting up registry with Piper engine."""
        mock_registry = MagicMock()
        mock_piper_class = MagicMock()
        mock_piper_instance = MagicMock()
        mock_piper_class.return_value = mock_piper_instance

        factory.engine_classes["piper"] = mock_piper_class
        factory.engine_configs["piper"] = {
            "offline": True,
            "ssml": False,
            "rate_control": True,
            "pitch_control": False,
            "languages": ["en"],
            "voices": [],
            "max_text_length": 5000,
        }

        with patch("ttskit.config.settings") as mock_settings:
            mock_settings.piper_model_path = "/path/to/model"
            mock_settings.piper_use_cuda = True

            factory.setup_registry(mock_registry)

            mock_piper_class.assert_called_once_with(
                model_path="/path/to/model", use_cuda=True
            )
            mock_registry.register_engine.assert_called_once()

    def test_setup_registry_without_piper(self, factory):
        """Test setting up registry without Piper engine."""
        mock_registry = MagicMock()
        mock_gtts_class = MagicMock()
        mock_gtts_instance = MagicMock()
        mock_gtts_class.return_value = mock_gtts_instance

        factory.engine_classes["gtts"] = mock_gtts_class
        factory.engine_configs["gtts"] = {
            "offline": False,
            "ssml": False,
            "rate_control": False,
            "pitch_control": False,
            "languages": ["en"],
            "voices": [],
            "max_text_length": 5000,
        }

        factory.setup_registry(mock_registry)

        mock_gtts_class.assert_called_once()
        mock_registry.register_engine.assert_called_once()

    def test_get_engine_info_with_gtts_available(self, factory):
        """Test getting engine info when gTTS is available."""
        mock_class = MagicMock()
        mock_class.__name__ = "GTTSEngine"
        factory.engine_classes["gtts"] = mock_class
        factory.engine_configs["gtts"] = {"offline": False}

        result = factory.get_engine_info(None)

        assert result is not None
        assert result["name"] == "gtts"

    def test_get_engine_info_without_gtts(self, factory):
        """Test getting engine info when gTTS is not available."""
        mock_class = MagicMock()
        mock_class.__name__ = "OtherEngine"
        factory.engine_classes["other_engine"] = mock_class
        factory.engine_configs["other_engine"] = {"offline": True}

        result = factory.get_engine_info(None)

        assert result is not None
        assert result["name"] == "other_engine"

    def test_get_engine_info_no_engines(self, factory):
        """Test getting engine info when no engines are available."""
        factory.engine_classes = {}
        factory.engine_configs = {}

        result = factory.get_engine_info(None)

        assert result is None

    def test_get_engine_info_specific_engine_not_found(self, factory):
        """Test getting engine info for non-existent engine."""
        result = factory.get_engine_info("nonexistent")
        assert result is None

    def test_get_engine_info_specific_engine_no_capabilities(self, factory):
        """Test getting engine info when engine has no capabilities."""
        factory.engine_classes["test_engine"] = MagicMock()
        factory.engine_configs["test_engine"] = None

        result = factory.get_engine_info("test_engine")
        assert result is None

    def test_get_engine_existing_instance(self, factory):
        """Test getting existing engine instance."""
        mock_engine = MagicMock()
        factory.engines["test_engine"] = mock_engine

        result = factory.get_engine("test_engine")

        assert result == mock_engine

    def test_get_engine_unknown_engine_in_known_names(self, factory):
        """Test getting unknown engine that's in known names."""
        result = factory.get_engine("edge")
        assert result is None

    def test_get_engine_unknown_engine_not_in_known_names(self, factory):
        """Test getting unknown engine not in known names."""
        with pytest.raises(ValueError, match="Unknown engine"):
            factory.get_engine("completely_unknown")

    def test_get_engine_piper_kwargs_filtering(self, factory):
        """Test getting Piper engine with kwargs filtering."""
        mock_piper_class = MagicMock()
        mock_piper_instance = MagicMock()
        mock_piper_class.return_value = mock_piper_instance

        factory.engine_classes["piper"] = mock_piper_class

        kwargs = {"model_path": "/path", "use_cuda": True, "invalid_param": "value"}
        result = factory.get_engine("piper", **kwargs)

        mock_piper_class.assert_called_once_with(model_path="/path", use_cuda=True)
        assert result == mock_piper_instance

    def test_get_engine_gtts_edge_kwargs_filtering(self, factory):
        """Test getting gTTS/Edge engine with kwargs filtering."""
        mock_gtts_class = MagicMock()
        mock_gtts_instance = MagicMock()
        mock_gtts_class.return_value = mock_gtts_instance

        factory.engine_classes["gtts"] = mock_gtts_class

        kwargs = {"model_path": "/path", "use_cuda": True, "valid_param": "value"}
        result = factory.get_engine("gtts", **kwargs)

        mock_gtts_class.assert_called_once_with(valid_param="value")
        assert result == mock_gtts_instance

    def test_get_engine_other_engine_kwargs(self, factory):
        """Test getting other engine with all kwargs."""
        mock_other_class = MagicMock()
        mock_other_instance = MagicMock()
        mock_other_class.return_value = mock_other_instance

        factory.engine_classes["other_engine"] = mock_other_class

        kwargs = {"param1": "value1", "param2": "value2"}
        result = factory.get_engine("other_engine", **kwargs)

        mock_other_class.assert_called_once_with(param1="value1", param2="value2")
        assert result == mock_other_instance

    def test_get_engine_set_default_lang_success(self, factory):
        """Test setting default_lang on engine successfully."""
        mock_engine_class = MagicMock()
        mock_engine_instance = MagicMock()
        mock_engine_instance.default_lang = "en"
        mock_engine_class.return_value = mock_engine_instance

        factory.engine_classes["test_engine"] = mock_engine_class

        result = factory.get_engine("test_engine", default_lang="fa")

        assert mock_engine_instance.default_lang == "fa"
        assert result == mock_engine_instance

    def test_get_engine_set_default_lang_failure(self, factory):
        """Test setting default_lang on engine with failure."""
        mock_engine_class = MagicMock()
        mock_engine_instance = MagicMock()
        mock_engine_class.return_value = mock_engine_instance

        factory.engine_classes["test_engine"] = mock_engine_class

        result = factory.get_engine("test_engine")
        assert result == mock_engine_instance

    def test_get_engine_exception_handling(self, factory):
        """Test exception handling in get_engine."""
        mock_engine_class = MagicMock()
        mock_engine_class.side_effect = Exception("Engine creation failed")

        factory.engine_classes["failing_engine"] = mock_engine_class

        result = factory.get_engine("failing_engine")

        assert result is None

    def test_is_engine_available_in_classes(self, factory):
        """Test checking engine availability in engine_classes."""
        factory.engine_classes["test_engine"] = MagicMock()

        assert factory.is_engine_available("test_engine") is True

    def test_is_engine_available_in_engines(self, factory):
        """Test checking engine availability in engines."""
        factory.engines["test_engine"] = MagicMock()

        assert factory.is_engine_available("test_engine") is True

    def test_is_engine_available_in_configs(self, factory):
        """Test checking engine availability in engine_configs."""
        factory.engine_configs["test_engine"] = {}

        assert factory.is_engine_available("test_engine") is True

    def test_is_engine_available_not_found(self, factory):
        """Test checking engine availability when not found."""
        assert factory.is_engine_available("nonexistent") is False

    def test_get_recommended_engine_edge_available(self, factory):
        """Test getting recommended engine when Edge is available."""
        factory.engine_classes["edge"] = MagicMock()

        result = factory.get_recommended_engine("en")
        assert result == "edge"

    def test_get_recommended_engine_gtts_available(self, factory):
        """Test getting recommended engine when only gTTS is available."""
        factory.engine_classes["gtts"] = MagicMock()

        result = factory.get_recommended_engine("en")
        assert result == "gtts"

    def test_get_recommended_engine_no_engines(self, factory):
        """Test getting recommended engine when no engines are available."""
        result = factory.get_recommended_engine("en")
        assert result is None

    def test_get_recommended_engine_unsupported_language(self, factory):
        """Test getting recommended engine for unsupported language."""
        result = factory.get_recommended_engine("xyz")
        assert result is None

    def test_get_engines_by_capability_with_value_true(self, factory):
        """Test getting engines by capability with value=True."""
        factory.engine_configs = {
            "engine1": {"offline": True},
            "engine2": {"offline": False},
            "engine3": {"offline": True},
        }

        result = factory.get_engines_by_capability("offline", True)

        assert "engine1" in result
        assert "engine3" in result
        assert "engine2" not in result

    def test_get_engines_by_capability_with_value_false(self, factory):
        """Test getting engines by capability with value=False."""
        factory.engine_configs = {
            "engine1": {"offline": True},
            "engine2": {"offline": False},
            "engine3": {"offline": True},
        }

        result = factory.get_engines_by_capability("offline", False)

        assert "engine2" in result
        assert "engine1" not in result
        assert "engine3" not in result

    def test_get_engines_by_capability_with_value_none(self, factory):
        """Test getting engines by capability with value=None (defaults to True)."""
        factory.engine_configs = {
            "engine1": {"offline": True},
            "engine2": {"offline": False},
            "engine3": {"offline": True},
        }

        result = factory.get_engines_by_capability("offline", None)

        assert "engine1" in result
        assert "engine3" in result
        assert "engine2" not in result

    def test_get_engines_by_capability_missing_capability(self, factory):
        """Test getting engines by capability when capability is missing."""
        factory.engine_configs = {
            "engine1": {"other_capability": True},
            "engine2": {"offline": True},
        }

        result = factory.get_engines_by_capability("offline", True)

        assert "engine2" in result
        assert "engine1" not in result

    def test_get_engines_by_language_supported(self, factory):
        """Test getting engines by language when language is supported."""
        factory.engine_configs = {
            "engine1": {"languages": ["en", "fa"]},
            "engine2": {"languages": ["ar", "es"]},
            "engine3": {"languages": ["en", "ar"]},
        }

        result = factory.get_engines_by_language("en")

        assert "engine1" in result
        assert "engine3" in result
        assert "engine2" not in result

    def test_get_engines_by_language_not_supported(self, factory):
        """Test getting engines by language when language is not supported."""
        factory.engine_configs = {
            "engine1": {"languages": ["en", "fa"]},
            "engine2": {"languages": ["ar", "es"]},
        }

        result = factory.get_engines_by_language("xyz")

        assert len(result) == 0

    def test_get_engines_by_language_missing_languages(self, factory):
        """Test getting engines by language when languages key is missing."""
        factory.engine_configs = {
            "engine1": {"other_key": ["en", "fa"]},
            "engine2": {"languages": ["en", "fa"]},
        }

        result = factory.get_engines_by_language("en")

        assert "engine2" in result
        assert "engine1" not in result

    def test_register_engine_with_capabilities(self, factory):
        """Test registering engine with capabilities."""
        mock_engine = MagicMock()
        capabilities = {"offline": True, "ssml": False}

        factory.register_engine("test_engine", mock_engine, capabilities)

        assert factory.engines["test_engine"] == mock_engine
        assert factory.engine_configs["test_engine"] == capabilities

    def test_register_engine_without_capabilities(self, factory):
        """Test registering engine without capabilities."""
        mock_engine = MagicMock()

        factory.register_engine("test_engine", mock_engine, None)

        assert factory.engines["test_engine"] == mock_engine
        assert factory.engine_configs["test_engine"]["offline"] is False
        assert factory.engine_configs["test_engine"]["ssml"] is False

    def test_unregister_engine_success(self, factory):
        """Test successful engine unregistration."""
        mock_engine = MagicMock()
        factory.engines["test_engine"] = mock_engine
        factory.engine_configs["test_engine"] = {}

        result = factory.unregister_engine("test_engine")

        assert result is True
        assert "test_engine" not in factory.engines
        assert "test_engine" not in factory.engine_configs

    def test_unregister_engine_not_found(self, factory):
        """Test unregistering non-existent engine."""
        result = factory.unregister_engine("nonexistent")

        assert result is False

    def test_unregister_engine_without_config(self, factory):
        """Test unregistering engine that has no config."""
        mock_engine = MagicMock()
        factory.engines["test_engine"] = mock_engine

        result = factory.unregister_engine("test_engine")

        assert result is True
        assert "test_engine" not in factory.engines


class TestGlobalFunctionsBranchCoverage:
    """Test cases for global functions branch coverage."""

    def test_create_engine_success(self):
        """Test successful engine creation via global function."""
        with patch("ttskit.engines.factory.factory") as mock_factory:
            mock_engine = MagicMock()
            mock_factory.create_engine.return_value = mock_engine

            result = create_engine("test_engine", param="value")

            mock_factory.create_engine.assert_called_once_with(
                "test_engine", param="value"
            )
            assert result == mock_engine

    def test_setup_default_registry_with_registry(self):
        """Test setting up default registry with provided registry."""
        mock_registry = MagicMock()

        with patch("ttskit.engines.factory.factory") as mock_factory:
            result = setup_default_registry(mock_registry, param="value")

            mock_factory.setup_registry.assert_called_once_with(
                mock_registry, param="value"
            )
            assert result == mock_registry

    def test_setup_default_registry_without_registry(self):
        """Test setting up default registry without provided registry."""
        with patch("ttskit.engines.factory.factory") as mock_factory:
            with patch("ttskit.engines.factory.EngineRegistry") as mock_registry_class:
                mock_registry = MagicMock()
                mock_registry_class.return_value = mock_registry

                result = setup_default_registry(None, param="value")

                mock_registry_class.assert_called_once()
                mock_factory.setup_registry.assert_called_once_with(
                    mock_registry, param="value"
                )
                assert result == mock_registry

    def test_get_available_engines(self):
        """Test getting available engines via global function."""
        with patch("ttskit.engines.factory.factory") as mock_factory:
            mock_factory.get_available_engines.return_value = ["engine1", "engine2"]

            result = get_available_engines()

            mock_factory.get_available_engines.assert_called_once()
            assert result == ["engine1", "engine2"]

    def test_setup_registry_global_function(self):
        """Test setup_registry global function."""
        mock_registry = MagicMock()

        with patch("ttskit.engines.factory.factory") as mock_factory:
            setup_registry(mock_registry, param="value")

            mock_factory.setup_registry.assert_called_once_with(
                mock_registry, param="value"
            )

    def test_get_engine_capabilities_global_function(self):
        """Test get_engine_capabilities global function."""
        with patch("ttskit.engines.factory.factory") as mock_factory:
            mock_capabilities = {"offline": True}
            mock_factory.get_engine_capabilities.return_value = mock_capabilities

            result = get_engine_capabilities("test_engine")

            mock_factory.get_engine_capabilities.assert_called_once_with("test_engine")
            assert result == mock_capabilities

    def test_edge_available_exposure(self):
        """Test that EDGE_AVAILABLE is properly exposed."""
        assert EDGE_AVAILABLE == _EDGE_AVAILABLE


class TestEngineFactoryStatisticsBranchCoverage:
    """Test cases for engine statistics branch coverage."""

    @pytest.fixture
    def factory(self):
        """Create test factory with various engines."""
        factory = EngineFactory()
        mock_class1 = MagicMock()
        mock_class1.__name__ = "Engine1"
        mock_class2 = MagicMock()
        mock_class2.__name__ = "Engine2"
        mock_class3 = MagicMock()
        mock_class3.__name__ = "Engine3"

        factory.engine_classes = {
            "engine1": mock_class1,
            "engine2": mock_class2,
            "engine3": mock_class3,
        }
        factory.engines = {"engine1": MagicMock(), "engine2": MagicMock()}
        factory.engine_configs = {
            "engine1": {
                "offline": True,
                "ssml": False,
                "rate_control": True,
                "pitch_control": False,
            },
            "engine2": {
                "offline": False,
                "ssml": True,
                "rate_control": False,
                "pitch_control": True,
            },
            "engine3": {
                "offline": True,
                "ssml": True,
                "rate_control": True,
                "pitch_control": True,
            },
        }
        return factory

    def test_get_engine_statistics_complete(self, factory):
        """Test getting complete engine statistics."""
        result = factory.get_engine_statistics()

        assert result["total_engines"] == 3
        assert result["available_engines"] == 2
        assert len(result["engine_names"]) == 3
        assert "engine1" in result["offline_engines"]
        assert "engine3" in result["offline_engines"]
        assert "engine2" in result["online_engines"]
        assert "engine2" in result["capabilities"]["ssml"]
        assert "engine3" in result["capabilities"]["ssml"]
        assert "engine1" in result["capabilities"]["rate_control"]
        assert "engine3" in result["capabilities"]["rate_control"]
        assert "engine2" in result["capabilities"]["pitch_control"]
        assert "engine3" in result["capabilities"]["pitch_control"]

    def test_get_all_engines_info(self, factory):
        """Test getting info for all engines."""
        result = factory.get_all_engines_info()

        assert len(result) == 3
        assert "engine1" in result
        assert "engine2" in result
        assert "engine3" in result

        for engine_name in result:
            engine_info = result[engine_name]
            assert engine_info["name"] == engine_name
            assert engine_info["available"] is True
            assert "capabilities" in engine_info
