"""
Final tests for complete coverage of SmartRouter, focusing on remaining lines.

This file targets exception handling and edge cases in synth_async and engine filtering.
"""

from unittest.mock import Mock

import pytest

from ttskit.engines.registry import EngineRegistry
from ttskit.engines.smart_router import SmartRouter


class TestSmartRouterFinalCoverage:
    """
    Final coverage tests for SmartRouter.

    These tests cover remaining exception paths in engine selection and filtering.
    """

    @pytest.fixture
    def mock_registry(self):
        """
        Create a mock EngineRegistry for use in tests.

        Configures default returns for available engines, language support, requirements, and stats.
        """
        registry = Mock(spec=EngineRegistry)
        registry.get_available_engines.return_value = ["gtts", "edge", "piper"]
        registry.get_engines_for_language.return_value = ["gtts", "edge"]
        registry.meets_requirements.return_value = True
        registry.get_engine_stats.return_value = {
            "total_requests": 100,
            "success_rate": 0.95,
            "avg_duration": 1.0,
        }
        return registry

    @pytest.fixture
    def smart_router(self, mock_registry):
        """
        Create a SmartRouter instance using the mock registry.

        Provides a fixture for testing router behavior with controlled dependencies.
        """
        return SmartRouter(mock_registry)

    def test_synth_async_registry_engines_exception(self, smart_router, mock_registry):
        """
        Test synth_async with exception during registry.engines access.

        Simulates failure in accessing engines to ensure proper error propagation.
        Expects an Exception with match 'All engines failed'.
        """
        mock_engine = Mock()
        mock_engine.is_available.return_value = True
        mock_engine.synth_async.return_value = b"audio_data"

        mock_registry.get_engine.side_effect = Exception("Engine not found")

        def engines_access(name):
            raise Exception("Registry engines access failed")

        mock_registry.engines = {"gtts": engines_access}

        smart_router.select_best_engine = Mock(return_value="gtts")

        async def run_test():
            with pytest.raises(Exception, match="All engines failed"):
                await smart_router.synth_async("Hello", "en")

        import asyncio

        asyncio.run(run_test())

    def test_get_best_engine_stats_int_conversion_exception(
        self, smart_router, mock_registry
    ):
        """
        Test get_best_engine with exception during int conversion in stats.

        Uses invalid string for total_requests to trigger conversion error.
        Verifies fallback to default engine 'gtts'.
        """
        mock_engine = Mock()
        mock_engine.is_available.return_value = True

        mock_registry.get_engine.return_value = mock_engine
        mock_registry.meets_requirements.return_value = True

        mock_registry.get_engine_stats.return_value = {
            "total_requests": "invalid_int",
            "success_rate": 0.95,
            "avg_duration": 1.0,
        }

        result = smart_router.get_best_engine("en")

        assert result == "gtts"

    def test_get_best_engine_stats_float_conversion_exception(
        self, smart_router, mock_registry
    ):
        """
        Test get_best_engine with exception during float conversion in stats.

        Invalid string for success_rate triggers the error path.
        Ensures selection defaults to 'gtts'.
        """
        mock_engine = Mock()
        mock_engine.is_available.return_value = True

        mock_registry.get_engine.return_value = mock_engine
        mock_registry.meets_requirements.return_value = True

        mock_registry.get_engine_stats.return_value = {
            "total_requests": 100,
            "success_rate": "invalid_float",
            "avg_duration": 1.0,
        }

        result = smart_router.get_best_engine("en")

        assert result == "gtts"

    def test_get_best_engine_stats_avg_duration_conversion_exception(
        self, smart_router, mock_registry
    ):
        """
        Test get_best_engine with exception during avg_duration conversion.

        Invalid float string for avg_duration covers the handling logic.
        Confirms engine selection proceeds to 'gtts'.
        """
        mock_engine = Mock()
        mock_engine.is_available.return_value = True

        mock_registry.get_engine.return_value = mock_engine
        mock_registry.meets_requirements.return_value = True

        mock_registry.get_engine_stats.return_value = {
            "total_requests": 100,
            "success_rate": 0.95,
            "avg_duration": "invalid_float",
        }

        result = smart_router.get_best_engine("en")

        assert result == "gtts"

    def test_filter_engines_offline_requirement_engine_get_exception(
        self, smart_router, mock_registry
    ):
        """
        Test _filter_engines_by_requirements with exception in engine retrieval.

        Simulates get_engine failure for offline requirement.
        Verifies all engines are included due to exception fallback.
        """
        engines = ["gtts", "edge"]
        requirements = {"offline": True}

        mock_engine = Mock()
        mock_engine.get_capabilities.return_value.offline = True

        mock_registry.meets_requirements.return_value = True
        mock_registry.get_engine.side_effect = Exception("Engine get failed")

        mock_registry.engines = {"gtts": mock_engine, "edge": mock_engine}

        result = smart_router._filter_engines_by_requirements(engines, requirements)

        assert result == ["gtts", "edge"]

    def test_filter_engines_offline_requirement_no_engines_attr(
        self, smart_router, mock_registry
    ):
        """
        Test _filter_engines_by_requirements without engines attribute.

        Deletes engines attr to test attribute error path for offline filtering.
        Expects all engines returned.
        """
        engines = ["gtts", "edge"]
        requirements = {"offline": True}

        mock_engine = Mock()
        mock_engine.get_capabilities.return_value.offline = True

        mock_registry.meets_requirements.return_value = True
        mock_registry.get_engine.side_effect = Exception("Engine get failed")

        del mock_registry.engines

        result = smart_router._filter_engines_by_requirements(engines, requirements)

        assert result == [
            "gtts",
            "edge",
        ]

    def test_filter_engines_offline_requirement_capabilities_exception(
        self, smart_router, mock_registry
    ):
        """
        Test _filter_engines_by_requirements with exception in capabilities access.

        Raises error in get_capabilities for offline check.
        Ensures engines are not filtered out.
        """
        engines = ["gtts", "edge"]
        requirements = {"offline": True}

        mock_engine = Mock()
        mock_engine.get_capabilities.side_effect = Exception("Capabilities failed")

        mock_registry.meets_requirements.return_value = True
        mock_registry.get_engine.return_value = mock_engine

        result = smart_router._filter_engines_by_requirements(engines, requirements)

        assert result == ["gtts", "edge"]

    def test_filter_engines_offline_requirement_continue_path(
        self, smart_router, mock_registry
    ):
        """
        Test _filter_engines_by_requirements continue path for offline requirement.

        Sets offline capability to False to trigger continue.
        Results in empty filtered list.
        """
        engines = ["gtts", "edge"]
        requirements = {"offline": True}

        mock_engine = Mock()
        mock_engine.get_capabilities.return_value.offline = False

        mock_registry.meets_requirements.return_value = True
        mock_registry.get_engine.return_value = mock_engine

        result = smart_router._filter_engines_by_requirements(engines, requirements)

        assert result == []

    def test_filter_engines_outer_exception_continue(self, smart_router, mock_registry):
        """
        Test _filter_engines_by_requirements with outer exception and continue.

        Multiple exceptions in meets_requirements and get_engine.
        Verifies empty list due to error handling.
        """
        engines = ["gtts", "edge"]
        requirements = {"offline": True}

        mock_engine = Mock()
        mock_engine.get_capabilities.side_effect = Exception("Capabilities failed")

        mock_registry.meets_requirements.side_effect = Exception(
            "Requirements check failed"
        )
        mock_registry.get_engine.side_effect = Exception("Engine get failed")
        mock_registry.engines = {"gtts": mock_engine, "edge": mock_engine}

        result = smart_router._filter_engines_by_requirements(engines, requirements)

        assert result == []

    def test_filter_engines_offline_requirement_fallback_continue(
        self, smart_router, mock_registry
    ):
        """
        Test _filter_engines_by_requirements fallback continue for offline.

        Exception in meets_requirements with offline=False capability.
        Expects empty filtered engines list.
        """
        engines = ["gtts", "edge"]
        requirements = {"offline": True}

        mock_engine = Mock()
        mock_engine.get_capabilities.return_value.offline = False

        mock_registry.meets_requirements.side_effect = Exception(
            "Requirements check failed"
        )
        mock_registry.get_engine.return_value = mock_engine

        result = smart_router._filter_engines_by_requirements(engines, requirements)

        assert result == []
