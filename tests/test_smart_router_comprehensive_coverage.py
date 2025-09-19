"""
Comprehensive tests to improve SmartRouter coverage, ensuring full path coverage.

This file provides thorough testing for synthesis, engine selection, filtering, and best engine determination.
"""

import asyncio
from unittest.mock import Mock

import pytest

from ttskit.engines.registry import EngineRegistry
from ttskit.engines.smart_router import SmartRouter
from ttskit.exceptions import AllEnginesFailedError, EngineNotFoundError


class TestSmartRouterSynthCoverage:
    """
    Comprehensive tests for the synth method, achieving 100% coverage.

    Focuses on success cases, error handling, and various parameter combinations in synthesis.
    """

    @pytest.fixture
    def mock_registry(self):
        """
        Create a mock registry for tests.

        Sets up default behaviors for engine availability, language support, requirements, and stats.
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
        Create a SmartRouter instance.

        Uses the mock registry to isolate tests from real engine dependencies.
        """
        return SmartRouter(mock_registry)

    def test_synth_success_basic(self, smart_router, mock_registry):
        """
        Test successful synth with basic parameters.

        Verifies that synth calls the engine's synth_async with defaults and returns audio data.
        """
        mock_engine = Mock()
        mock_engine.is_available.return_value = True
        mock_engine.synth_async.return_value = b"audio_data"

        mock_registry.get_engine.return_value = mock_engine
        mock_registry.engines = {"gtts": mock_engine}

        smart_router.select_best_engine = Mock(return_value="gtts")

        audio_data, engine_name = smart_router.synth("Hello", "en")

        assert audio_data == b"audio_data"
        assert engine_name == "gtts"
        mock_engine.synth_async.assert_called_once_with("Hello", "en", None, 1.0, 0.0)

    def test_synth_success_with_all_parameters(self, smart_router, mock_registry):
        """
        Test successful synth with all parameters provided.

        Ensures custom requirements, voice, speed, and pitch are passed to the engine.
        """
        mock_engine = Mock()
        mock_engine.is_available.return_value = True
        mock_engine.synth_async.return_value = b"audio_data"

        mock_registry.get_engine.return_value = mock_engine
        mock_registry.engines = {"gtts": mock_engine}

        smart_router.select_best_engine = Mock(return_value="gtts")

        requirements = {"offline": True}
        audio_data, engine_name = smart_router.synth(
            "Hello", "en", requirements, "voice1", 1.5, 0.5
        )

        assert audio_data == b"audio_data"
        assert engine_name == "gtts"
        mock_engine.synth_async.assert_called_once_with(
            "Hello", "en", "voice1", 1.5, 0.5
        )

    def test_synth_async_awaitable_result(self, smart_router, mock_registry):
        """
        Test synth_async with an awaitable result from the engine.

        Handles cases where the engine returns a coroutine and awaits it properly.
        """
        mock_engine = Mock()
        mock_engine.is_available.return_value = True

        async def async_synth(*args, **kwargs):
            return b"async_audio_data"

        mock_engine.synth_async.return_value = async_synth()

        mock_registry.get_engine.return_value = mock_engine
        mock_registry.engines = {"gtts": mock_engine}

        smart_router.select_best_engine = Mock(return_value="gtts")

        async def run_test():
            audio_data, engine_name = await smart_router.synth_async("Hello", "en")
            assert audio_data == b"async_audio_data"
            assert engine_name == "gtts"

        asyncio.run(run_test())

    def test_synth_async_non_bytes_result(self, smart_router, mock_registry):
        """
        Test synth_async with non-bytes result from the engine.

        Converts non-bytes to bytes by encoding, ensuring compatibility.
        """
        mock_engine = Mock()
        mock_engine.is_available.return_value = True
        mock_engine.synth_async.return_value = "not_bytes"

        mock_registry.get_engine.return_value = mock_engine
        mock_registry.engines = {"gtts": mock_engine}

        smart_router.select_best_engine = Mock(return_value="gtts")

        async def run_test():
            audio_data, engine_name = await smart_router.synth_async("Hello", "en")
            assert audio_data == b"audio"
            assert engine_name == "gtts"

        asyncio.run(run_test())

    def test_synth_engine_not_meets_requirements(self, smart_router, mock_registry):
        """
        Test synth when the engine does not meet requirements.

        Raises AllEnginesFailedError if requirements are not satisfied.
        """
        mock_engine = Mock()
        mock_engine.is_available.return_value = True
        mock_engine.synth_async.return_value = b"audio_data"

        mock_registry.get_engine.return_value = mock_engine
        mock_registry.engines = {"gtts": mock_engine}

        smart_router.select_best_engine = Mock(return_value="gtts")

        mock_registry.meets_requirements.return_value = False

        async def run_test():
            with pytest.raises(AllEnginesFailedError):
                await smart_router.synth_async("Hello", "en", {"offline": True})

        asyncio.run(run_test())

    def test_synth_engine_not_available(self, smart_router, mock_registry):
        """
        Test synth when the engine is not available.

        Expects AllEnginesFailedError when is_available returns False.
        """
        mock_engine = Mock()
        mock_engine.is_available.return_value = False

        mock_registry.get_engine.return_value = mock_engine
        mock_registry.engines = {"gtts": mock_engine}

        smart_router.select_best_engine = Mock(return_value="gtts")

        async def run_test():
            with pytest.raises(AllEnginesFailedError):
                await smart_router.synth_async("Hello", "en")

        asyncio.run(run_test())

    def test_synth_engine_not_found_in_registry(self, smart_router, mock_registry):
        """
        Test synth when engine is not found in registry.

        Simulates get_engine exception, leading to AllEnginesFailedError.
        """
        mock_registry.get_engine.side_effect = Exception("Engine not found")
        mock_registry.engines = {"gtts": None}

        smart_router.select_best_engine = Mock(return_value="gtts")

        async def run_test():
            with pytest.raises(AllEnginesFailedError):
                await smart_router.synth_async("Hello", "en")

        asyncio.run(run_test())

    def test_synth_engine_synthesis_failure(self, smart_router, mock_registry):
        """
        Test synth when engine synthesis fails.

        Catches synthesis exception and raises AllEnginesFailedError.
        """
        mock_engine = Mock()
        mock_engine.is_available.return_value = True
        mock_engine.synth_async.side_effect = Exception("Synthesis failed")

        mock_registry.get_engine.return_value = mock_engine
        mock_registry.engines = {"gtts": mock_engine}

        smart_router.select_best_engine = Mock(return_value="gtts")

        async def run_test():
            with pytest.raises(AllEnginesFailedError):
                await smart_router.synth_async("Hello", "en")

        asyncio.run(run_test())

    def test_synth_no_engine_selected(self, smart_router, mock_registry):
        """تست synth وقتی هیچ engine انتخاب نمی‌شود."""
        smart_router.select_best_engine = Mock(return_value=None)

        async def run_test():
            with pytest.raises(EngineNotFoundError):
                await smart_router.synth_async("Hello", "en")

        asyncio.run(run_test())

    def test_synth_registry_engines_fallback(self, smart_router, mock_registry):
        """تست synth با استفاده از registry.engines fallback."""
        mock_engine = Mock()
        mock_engine.is_available.return_value = True
        mock_engine.synth_async.return_value = b"audio_data"

        mock_registry.get_engine.side_effect = Exception("Engine not found")
        mock_registry.engines = {"gtts": mock_engine}

        smart_router.select_best_engine = Mock(return_value="gtts")

        async def run_test():
            audio_data, engine_name = await smart_router.synth_async("Hello", "en")
            assert audio_data == b"audio_data"
            assert engine_name == "gtts"

        asyncio.run(run_test())

    def test_synth_registry_engines_fallback_failure(self, smart_router, mock_registry):
        """تست synth وقتی registry.engines fallback هم fail می‌کند."""
        mock_registry.get_engine.side_effect = Exception("Engine not found")
        mock_registry.engines = {"gtts": None}

        smart_router.select_best_engine = Mock(return_value="gtts")

        async def run_test():
            with pytest.raises(AllEnginesFailedError):
                await smart_router.synth_async("Hello", "en")

        asyncio.run(run_test())


class TestSmartRouterSelectEngineCoverage:
    """
    Comprehensive tests for the select_engine method, achieving 100% coverage.

    Tests various scenarios for engine selection based on availability and requirements.
    """

    @pytest.fixture
    def mock_registry(self):
        """
        Create a mock registry for select_engine tests.

        Defaults to engines gtts, edge, piper with basic availability.
        """
        registry = Mock(spec=EngineRegistry)
        registry.get_available_engines.return_value = ["gtts", "edge", "piper"]
        registry.get_engines_for_language.return_value = ["gtts", "edge"]
        registry.meets_requirements.return_value = True
        return registry

    @pytest.fixture
    def smart_router(self, mock_registry):
        """
        Create SmartRouter instance for select_engine testing.

        Integrates with the mock registry for controlled selection logic.
        """
        return SmartRouter(mock_registry)

    def test_select_engine_success_basic(self, smart_router, mock_registry):
        """
        Test successful select_engine with basic parameters.

        Returns the default engine 'gtts' when all checks pass.
        """
        mock_engine = Mock()
        mock_engine.is_available.return_value = True

        mock_registry.get_engine.return_value = mock_engine
        mock_registry.meets_requirements.return_value = True

        result = smart_router.select_engine("en")

        assert result == "gtts"
        mock_registry.meets_requirements.assert_called_once()

    def test_select_engine_success_with_requirements(self, smart_router, mock_registry):
        """
        Test successful select_engine with requirements.

        Verifies requirements are checked against the selected engine.
        """
        mock_engine = Mock()
        mock_engine.is_available.return_value = True

        mock_registry.get_engine.return_value = mock_engine
        mock_registry.meets_requirements.return_value = True

        requirements = {"offline": True}
        result = smart_router.select_engine("en", requirements)

        assert result == "gtts"
        mock_registry.meets_requirements.assert_called_once_with("gtts", requirements)

    def test_select_engine_no_requirements_none(self, smart_router, mock_registry):
        """تست select_engine با requirements=None."""
        mock_engine = Mock()
        mock_engine.is_available.return_value = True

        mock_registry.get_engine.return_value = mock_engine
        mock_registry.meets_requirements.return_value = True

        result = smart_router.select_engine("en", None)

        assert result == "gtts"
        mock_registry.meets_requirements.assert_called_once_with("gtts", {})

    def test_select_engine_requirements_not_met(self, smart_router, mock_registry):
        """تست select_engine وقتی requirements برآورده نمی‌شود."""
        mock_engine = Mock()
        mock_engine.is_available.return_value = True

        mock_registry.get_engine.return_value = mock_engine
        mock_registry.meets_requirements.return_value = False

        result = smart_router.select_engine("en", {"offline": True})

        assert result is None

    def test_select_engine_get_engine_failure(self, smart_router, mock_registry):
        """تست select_engine وقتی get_engine fail می‌کند."""
        mock_registry.get_engine.side_effect = Exception("Engine not found")
        mock_registry.meets_requirements.return_value = True

        result = smart_router.select_engine("en")

        assert result is None

    def test_select_engine_registry_engines_fallback(self, smart_router, mock_registry):
        """تست select_engine با استفاده از registry.engines fallback."""
        mock_engine = Mock()
        mock_engine.is_available.return_value = True

        mock_registry.get_engine.side_effect = Exception("Engine not found")
        mock_registry.engines = {"gtts": mock_engine}
        mock_registry.meets_requirements.return_value = True

        result = smart_router.select_engine("en")

        assert result == "gtts"

    def test_select_engine_registry_engines_fallback_failure(
        self, smart_router, mock_registry
    ):
        """
        Test select_engine when registry.engines fallback also fails.

        Returns None when fallback access is None.
        """
        mock_registry.get_engine.side_effect = Exception("Engine not found")
        mock_registry.engines = {"gtts": None}
        mock_registry.meets_requirements.return_value = True

        result = smart_router.select_engine("en")

        assert result is None

    def test_select_engine_engine_not_available(self, smart_router, mock_registry):
        """
        Test select_engine when engine is not available.

        Returns None if is_available is False.
        """
        mock_engine = Mock()
        mock_engine.is_available.return_value = False

        mock_registry.get_engine.return_value = mock_engine
        mock_registry.meets_requirements.return_value = True

        result = smart_router.select_engine("en")

        assert result is None

    def test_select_engine_meets_requirements_exception(
        self, smart_router, mock_registry
    ):
        """
        Test select_engine when meets_requirements raises exception.

        Treats exception as met requirements and proceeds with selection.
        """
        mock_engine = Mock()
        mock_engine.is_available.return_value = True

        mock_registry.get_engine.return_value = mock_engine
        mock_registry.meets_requirements.side_effect = Exception(
            "Requirements check failed"
        )

        result = smart_router.select_engine("en")

        assert result == "gtts"

    def test_select_engine_fallback_engine_not_available(
        self, smart_router, mock_registry
    ):
        """
        Test select_engine fallback when engine is not available.

        Returns None in fallback if is_available fails.
        """
        mock_engine = Mock()
        mock_engine.is_available.return_value = False

        mock_registry.get_engine.return_value = mock_engine
        mock_registry.meets_requirements.side_effect = Exception(
            "Requirements check failed"
        )

        result = smart_router.select_engine("en")

        assert result is None

    def test_select_engine_fallback_get_engine_failure(
        self, smart_router, mock_registry
    ):
        """تست select_engine در fallback وقتی get_engine fail می‌کند."""
        mock_registry.get_engine.side_effect = Exception("Engine not found")
        mock_registry.meets_requirements.side_effect = Exception(
            "Requirements check failed"
        )

        result = smart_router.select_engine("en")

        assert result is None

    def test_select_engine_no_suitable_engines(self, smart_router, mock_registry):
        """تست select_engine وقتی هیچ engine مناسبی وجود ندارد."""
        mock_registry.get_engines_for_language.return_value = []

        result = smart_router.select_engine("en")

        assert result is None


class TestSmartRouterFilterEnginesCoverage:
    """
    Comprehensive tests for _filter_engines_by_requirements method, achieving 100% coverage.

    Covers filtering logic for engines based on requirements, including exceptions and fallbacks.
    """

    @pytest.fixture
    def mock_registry(self):
        """
        Create mock registry for filter engines tests.

        Defaults to meets_requirements returning True.
        """
        registry = Mock(spec=EngineRegistry)
        registry.meets_requirements.return_value = True
        return registry

    @pytest.fixture
    def smart_router(self, mock_registry):
        """
        Create SmartRouter instance for filter engines testing.

        Uses mock registry to control filtering behavior.
        """
        return SmartRouter(mock_registry)

    def test_filter_engines_success_basic(self, smart_router, mock_registry):
        """
        Test successful _filter_engines_by_requirements with basic parameters.

        Returns all engines when requirements are met.
        """
        engines = ["gtts", "edge", "piper"]
        requirements = {"offline": True}

        mock_registry.meets_requirements.return_value = True

        result = smart_router._filter_engines_by_requirements(engines, requirements)

        assert result == ["gtts", "edge", "piper"]
        assert mock_registry.meets_requirements.call_count == 3

    def test_filter_engines_offline_requirement_success(
        self, smart_router, mock_registry
    ):
        """
        Test _filter_engines_by_requirements with successful offline requirement.

        Includes engines that support offline capability.
        """
        engines = ["gtts", "edge"]
        requirements = {"offline": True}

        mock_engine = Mock()
        mock_engine.get_capabilities.return_value.offline = True

        mock_registry.meets_requirements.return_value = True
        mock_registry.get_engine.return_value = mock_engine

        result = smart_router._filter_engines_by_requirements(engines, requirements)

        assert result == ["gtts", "edge"]

    def test_filter_engines_offline_requirement_failure(
        self, smart_router, mock_registry
    ):
        """تست _filter_engines_by_requirements با offline requirement fail."""
        engines = ["gtts", "edge"]
        requirements = {"offline": True}

        mock_engine = Mock()
        mock_engine.get_capabilities.return_value.offline = False

        mock_registry.meets_requirements.return_value = True
        mock_registry.get_engine.return_value = mock_engine

        result = smart_router._filter_engines_by_requirements(engines, requirements)

        assert result == []

    def test_filter_engines_meets_requirements_exception(
        self, smart_router, mock_registry
    ):
        """تست _filter_engines_by_requirements وقتی meets_requirements exception می‌دهد."""
        engines = ["gtts", "edge"]
        requirements = {"offline": True}

        mock_engine = Mock()
        mock_engine.get_capabilities.return_value.offline = True

        mock_registry.meets_requirements.side_effect = Exception(
            "Requirements check failed"
        )
        mock_registry.get_engine.return_value = mock_engine

        result = smart_router._filter_engines_by_requirements(engines, requirements)

        assert result == ["gtts", "edge"]

    def test_filter_engines_get_engine_failure(self, smart_router, mock_registry):
        """تست _filter_engines_by_requirements وقتی get_engine fail می‌کند."""
        engines = ["gtts", "edge"]
        requirements = {"offline": True}

        mock_registry.meets_requirements.side_effect = Exception(
            "Requirements check failed"
        )
        mock_registry.get_engine.side_effect = Exception("Engine not found")

        result = smart_router._filter_engines_by_requirements(engines, requirements)

        assert result == []

    def test_filter_engines_registry_engines_fallback(
        self, smart_router, mock_registry
    ):
        """تست _filter_engines_by_requirements با استفاده از registry.engines fallback."""
        engines = ["gtts", "edge"]
        requirements = {"offline": True}

        mock_engine = Mock()
        mock_engine.get_capabilities.return_value.offline = True

        mock_registry.meets_requirements.side_effect = Exception(
            "Requirements check failed"
        )
        mock_registry.get_engine.side_effect = Exception("Engine not found")
        mock_registry.engines = {"gtts": mock_engine, "edge": mock_engine}

        result = smart_router._filter_engines_by_requirements(engines, requirements)

        assert result == ["gtts", "edge"]

    def test_filter_engines_registry_engines_fallback_failure(
        self, smart_router, mock_registry
    ):
        """
        Test _filter_engines_by_requirements when registry.engines fallback fails.

        Returns empty list when fallback engines are None.
        """
        engines = ["gtts", "edge"]
        requirements = {"offline": True}

        mock_registry.meets_requirements.side_effect = Exception(
            "Requirements check failed"
        )
        mock_registry.get_engine.side_effect = Exception("Engine not found")
        mock_registry.engines = {"gtts": None, "edge": None}

        result = smart_router._filter_engines_by_requirements(engines, requirements)

        assert result == []

    def test_filter_engines_get_capabilities_failure(self, smart_router, mock_registry):
        """
        Test _filter_engines_by_requirements when get_capabilities fails.

        Excludes engines with capability check exceptions, resulting in empty list.
        """
        engines = ["gtts", "edge"]
        requirements = {"offline": True}

        mock_engine = Mock()
        mock_engine.get_capabilities.side_effect = Exception(
            "Capabilities check failed"
        )

        mock_registry.meets_requirements.side_effect = Exception(
            "Requirements check failed"
        )
        mock_registry.get_engine.return_value = mock_engine

        result = smart_router._filter_engines_by_requirements(engines, requirements)

        assert result == []

    def test_filter_engines_capabilities_none(self, smart_router, mock_registry):
        """
        Test _filter_engines_by_requirements when capabilities is None.

        Treats None capabilities as not meeting offline requirement.
        """
        engines = ["gtts", "edge"]
        requirements = {"offline": True}

        mock_engine = Mock()
        mock_engine.get_capabilities.return_value = None

        mock_registry.meets_requirements.side_effect = Exception(
            "Requirements check failed"
        )
        mock_registry.get_engine.return_value = mock_engine

        result = smart_router._filter_engines_by_requirements(engines, requirements)

        assert result == []

    def test_filter_engines_outer_exception(self, smart_router, mock_registry):
        """
        Test _filter_engines_by_requirements with outer level exception.

        Handles multiple exceptions in loop, returning empty list.
        """
        engines = ["gtts", "edge"]
        requirements = {"offline": True}

        mock_engine = Mock()
        mock_engine.get_capabilities.side_effect = Exception(
            "Capabilities check failed"
        )

        mock_registry.meets_requirements.side_effect = Exception(
            "Requirements check failed"
        )
        mock_registry.get_engine.side_effect = Exception("Engine not found")
        mock_registry.engines = {"gtts": mock_engine, "edge": mock_engine}

        result = smart_router._filter_engines_by_requirements(engines, requirements)

        assert result == []

    def test_filter_engines_no_offline_requirement(self, smart_router, mock_registry):
        """تست _filter_engines_by_requirements بدون offline requirement."""
        engines = ["gtts", "edge"]
        requirements = {"voice": "lessac"}

        mock_engine = Mock()
        mock_engine.get_capabilities.return_value.offline = True

        mock_registry.meets_requirements.side_effect = Exception(
            "Requirements check failed"
        )
        mock_registry.get_engine.return_value = mock_engine

        result = smart_router._filter_engines_by_requirements(engines, requirements)

        assert result == ["gtts", "edge"]


class TestSmartRouterGetBestEngineCoverage:
    """تست‌های جامع برای متد get_best_engine - پوشش کامل 100%."""

    @pytest.fixture
    def mock_registry(self):
        """ایجاد mock registry برای تست‌ها."""
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
        """ایجاد SmartRouter instance."""
        return SmartRouter(mock_registry)

    def test_get_best_engine_success_basic(self, smart_router, mock_registry):
        """تست get_best_engine موفق با پارامترهای پایه."""
        mock_engine = Mock()
        mock_engine.is_available.return_value = True

        mock_registry.get_engine.return_value = mock_engine
        mock_registry.meets_requirements.return_value = True

        mock_registry.get_engine_stats.return_value = {
            "total_requests": 100,
            "success_rate": 0.95,
            "avg_duration": 1.0,
        }

        result = smart_router.get_best_engine("en")

        assert result == "gtts"

    def test_get_best_engine_success_with_requirements(
        self, smart_router, mock_registry
    ):
        """
        Test successful get_best_engine with requirements.

        Applies requirements filtering before selecting based on performance.
        """
        mock_engine = Mock()
        mock_engine.is_available.return_value = True

        mock_registry.get_engine.return_value = mock_engine
        mock_registry.meets_requirements.return_value = True

        mock_registry.get_engine_stats.return_value = {
            "total_requests": 100,
            "success_rate": 0.95,
            "avg_duration": 1.0,
        }

        requirements = {"offline": True}
        result = smart_router.get_best_engine("en", requirements)

        assert result == "gtts"
        assert mock_registry.meets_requirements.call_count >= 1

    def test_get_best_engine_no_requirements_none(self, smart_router, mock_registry):
        """
        Test get_best_engine with requirements=None.

        Treats None as empty dict and proceeds with default selection.
        """
        mock_engine = Mock()
        mock_engine.is_available.return_value = True

        mock_registry.get_engine.return_value = mock_engine
        mock_registry.meets_requirements.return_value = True

        mock_registry.get_engine_stats.return_value = {
            "total_requests": 100,
            "success_rate": 0.95,
            "avg_duration": 1.0,
        }

        result = smart_router.get_best_engine("en", None)

        assert result == "gtts"
        assert mock_registry.meets_requirements.call_count >= 1

    def test_get_best_engine_requirements_not_met(self, smart_router, mock_registry):
        """
        Test get_best_engine when requirements are not met.

        Returns None if no engine satisfies the requirements.
        """
        mock_engine = Mock()
        mock_engine.is_available.return_value = True

        mock_registry.get_engine.return_value = mock_engine
        mock_registry.meets_requirements.return_value = False

        result = smart_router.get_best_engine("en", {"offline": True})

        assert result is None

    def test_get_best_engine_get_engine_failure(self, smart_router, mock_registry):
        """
        Test get_best_engine when get_engine fails.

        Returns None on engine retrieval exception.
        """
        mock_registry.get_engine.side_effect = Exception("Engine not found")
        mock_registry.meets_requirements.return_value = True

        result = smart_router.get_best_engine("en")

        assert result is None

    def test_get_best_engine_registry_engines_fallback(
        self, smart_router, mock_registry
    ):
        """تست get_best_engine با استفاده از registry.engines fallback."""
        mock_engine = Mock()
        mock_engine.is_available.return_value = True

        mock_registry.get_engine.side_effect = Exception("Engine not found")
        mock_registry.engines = {"gtts": mock_engine}
        mock_registry.meets_requirements.return_value = True

        mock_registry.get_engine_stats.return_value = {
            "total_requests": 100,
            "success_rate": 0.95,
            "avg_duration": 1.0,
        }

        result = smart_router.get_best_engine("en")

        assert result == "gtts"

    def test_get_best_engine_registry_engines_fallback_failure(
        self, smart_router, mock_registry
    ):
        """تست get_best_engine وقتی registry.engines fallback هم fail می‌کند."""
        mock_registry.get_engine.side_effect = Exception("Engine not found")
        mock_registry.engines = {"gtts": None}
        mock_registry.meets_requirements.return_value = True

        result = smart_router.get_best_engine("en")

        assert result is None

    def test_get_best_engine_engine_not_available(self, smart_router, mock_registry):
        """تست get_best_engine وقتی engine در دسترس نیست."""
        mock_engine = Mock()
        mock_engine.is_available.return_value = False

        mock_registry.get_engine.return_value = mock_engine
        mock_registry.meets_requirements.return_value = True

        result = smart_router.get_best_engine("en")

        assert result is None

    def test_get_best_engine_meets_requirements_exception(
        self, smart_router, mock_registry
    ):
        """تست get_best_engine وقتی meets_requirements exception می‌دهد."""
        mock_engine = Mock()
        mock_engine.is_available.return_value = True

        mock_registry.get_engine.return_value = mock_engine
        mock_registry.meets_requirements.side_effect = Exception(
            "Requirements check failed"
        )

        mock_registry.get_engine_stats.return_value = {
            "total_requests": 100,
            "success_rate": 0.95,
            "avg_duration": 1.0,
        }

        result = smart_router.get_best_engine("en")

        assert result == "gtts"

    def test_get_best_engine_no_suitable_engines(self, smart_router, mock_registry):
        """تست get_best_engine وقتی هیچ engine مناسبی وجود ندارد."""
        mock_registry.get_engines_for_language.return_value = []

        result = smart_router.get_best_engine("en")

        assert result is None

    def test_get_best_engine_performance_scoring(self, smart_router, mock_registry):
        """تست get_best_engine با محاسبه performance score."""
        mock_engine1 = Mock()
        mock_engine1.is_available.return_value = True
        mock_engine2 = Mock()
        mock_engine2.is_available.return_value = True

        mock_registry.get_engine.side_effect = (
            lambda name: mock_engine1 if name == "gtts" else mock_engine2
        )
        mock_registry.meets_requirements.return_value = True

        def get_stats(name):
            if name == "gtts":
                return {"total_requests": 100, "success_rate": 0.9, "avg_duration": 2.0}
            else:
                return {
                    "total_requests": 100,
                    "success_rate": 0.95,
                    "avg_duration": 1.0,
                }

        mock_registry.get_engine_stats.side_effect = get_stats

        result = smart_router.get_best_engine("en")

        assert result == "edge"

    def test_get_best_engine_stats_exception_handling(
        self, smart_router, mock_registry
    ):
        """تست get_best_engine با exception handling در stats."""
        mock_engine = Mock()
        mock_engine.is_available.return_value = True

        mock_registry.get_engine.return_value = mock_engine
        mock_registry.meets_requirements.return_value = True

        mock_registry.get_engine_stats.side_effect = Exception("Stats not available")

        with pytest.raises(Exception, match="Stats not available"):
            smart_router.get_best_engine("en")

    def test_get_best_engine_stats_invalid_format(self, smart_router, mock_registry):
        """تست get_best_engine با stats format نامعتبر."""
        mock_engine = Mock()
        mock_engine.is_available.return_value = True

        mock_registry.get_engine.return_value = mock_engine
        mock_registry.meets_requirements.return_value = True

        mock_registry.get_engine_stats.return_value = "invalid_stats"

        result = smart_router.get_best_engine("en")

        assert result == "gtts"

    def test_get_best_engine_zero_total_requests(self, smart_router, mock_registry):
        """تست get_best_engine با zero total_requests."""
        mock_engine = Mock()
        mock_engine.is_available.return_value = True

        mock_registry.get_engine.return_value = mock_engine
        mock_registry.meets_requirements.return_value = True

        mock_registry.get_engine_stats.return_value = {
            "total_requests": 0,
            "success_rate": 0.95,
            "avg_duration": 1.0,
        }

        result = smart_router.get_best_engine("en")

        assert result == "gtts"

    def test_get_best_engine_stats_type_conversion(self, smart_router, mock_registry):
        """تست get_best_engine با type conversion در stats."""
        mock_engine = Mock()
        mock_engine.is_available.return_value = True

        mock_registry.get_engine.return_value = mock_engine
        mock_registry.meets_requirements.return_value = True

        mock_registry.get_engine_stats.return_value = {
            "total_requests": "100",
            "success_rate": 0.95,
            "avg_duration": "1.0",
        }

        result = smart_router.get_best_engine("en")

        assert result == "gtts"

    def test_get_best_engine_stats_with_dict_attributes(
        self, smart_router, mock_registry
    ):
        """تست get_best_engine با stats که dict attributes دارد."""
        mock_engine = Mock()
        mock_engine.is_available.return_value = True

        mock_registry.get_engine.return_value = mock_engine
        mock_registry.meets_requirements.return_value = True

        mock_stats = {"total_requests": 100, "success_rate": 0.95, "avg_duration": 1.0}
        mock_registry.get_engine_stats.return_value = mock_stats

        result = smart_router.get_best_engine("en")

        assert result == "gtts"
