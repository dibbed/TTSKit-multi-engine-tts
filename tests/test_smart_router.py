"""Tests for Smart Router."""

from unittest.mock import Mock

import pytest

from ttskit.engines.registry import EngineRegistry
from ttskit.engines.smart_router import SmartRouter
from ttskit.exceptions import AllEnginesFailedError, EngineNotFoundError


class TestSmartRouter:
    """Test cases for SmartRouter."""

    @pytest.fixture
    def mock_registry(self):
        """Create mock engine registry."""
        registry = Mock(spec=EngineRegistry)
        registry.get_available_engines.return_value = ["gtts", "edge"]
        registry.get_engine.return_value = Mock()
        registry.get_policy.return_value = ["gtts", "edge"]
        return registry

    @pytest.fixture
    def smart_router(self, mock_registry):
        """Create SmartRouter instance."""
        return SmartRouter(mock_registry)

    def test_initialization(self, mock_registry):
        """Test SmartRouter initialization."""
        router = SmartRouter(mock_registry)

        assert router.registry is mock_registry
        assert isinstance(router.stats, dict)
        assert "total_requests" in router.stats
        assert "successful_requests" in router.stats
        assert "failed_requests" in router.stats

    def test_get_engine_ranking(self, smart_router):
        """Test getting engine ranking."""
        ranking = smart_router.get_engine_ranking("en")

        assert isinstance(ranking, list)
        assert len(ranking) > 0

    def test_get_engine_ranking_with_requirements(self, smart_router):
        """Test getting engine ranking with requirements."""
        requirements = {"offline": True}
        ranking = smart_router.get_engine_ranking("en", requirements)

        assert isinstance(ranking, list)

    def test_get_engine_ranking_with_unsupported_language(self, smart_router):
        """Test getting engine ranking for unsupported language."""
        ranking = smart_router.get_engine_ranking("xyz")

        assert isinstance(ranking, list)

    def test_select_best_engine(self, smart_router):
        """Test selecting best engine."""
        engine_name = smart_router.select_best_engine("en")

        assert isinstance(engine_name, str)
        assert engine_name in ["gtts", "edge"]

    def test_select_best_engine_with_requirements(self, smart_router):
        """Test selecting best engine with requirements."""
        requirements = {"offline": False}
        engine_name = smart_router.select_best_engine("en", requirements)

        assert isinstance(engine_name, str)

    def test_select_best_engine_with_unsupported_language(self, smart_router):
        """Test selecting best engine for unsupported language."""
        engine_name = smart_router.select_best_engine("xyz")

        assert engine_name is None or isinstance(engine_name, str)

    def test_synth_async_success(self, smart_router):
        """Test successful async synthesis."""
        mock_engine = Mock()
        mock_engine.synth_async.return_value = b"audio_data"
        smart_router.registry.get_engine.return_value = mock_engine

        smart_router.select_best_engine = Mock(return_value="gtts")

        import asyncio

        async def run_test():
            audio_data, engine_name = await smart_router.synth_async("Hello", "en")
            assert audio_data == b"audio_data"
            assert engine_name == "gtts"

        asyncio.run(run_test())

    def test_synth_async_with_requirements(self, smart_router):
        """Test async synthesis with requirements."""
        mock_engine = Mock()
        mock_engine.synth_async.return_value = b"audio_data"
        smart_router.registry.get_engine.return_value = mock_engine

        smart_router.select_best_engine = Mock(return_value="gtts")

        import asyncio

        async def run_test():
            requirements = {"offline": False}
            audio_data, engine_name = await smart_router.synth_async(
                "Hello", "en", requirements=requirements
            )
            assert audio_data == b"audio_data"
            assert engine_name == "gtts"

        asyncio.run(run_test())

    def test_synth_async_engine_not_found(self, smart_router):
        """Test async synthesis when engine is not found."""
        smart_router.select_best_engine = Mock(return_value=None)

        import asyncio

        async def run_test():
            with pytest.raises(EngineNotFoundError):
                await smart_router.synth_async("Hello", "en")

        asyncio.run(run_test())

    def test_synth_async_all_engines_failed(self, smart_router):
        """Test async synthesis when all engines fail."""
        mock_engine = Mock()
        mock_engine.synth_async.side_effect = Exception("Engine failed")
        smart_router.registry.get_engine.return_value = mock_engine

        smart_router.select_best_engine = Mock(return_value="gtts")
        smart_router.registry.get_policy.return_value = ["gtts", "edge"]

        import asyncio

        async def run_test():
            with pytest.raises(AllEnginesFailedError):
                await smart_router.synth_async("Hello", "en")

        asyncio.run(run_test())

    def test_get_all_stats(self, smart_router):
        """Test getting all statistics."""
        stats = smart_router.get_all_stats()

        assert isinstance(stats, dict)
        assert "total_requests" in stats
        assert "successful_requests" in stats
        assert "failed_requests" in stats
        assert "success_rate" in stats

    def test_reset_stats(self, smart_router):
        """Test resetting statistics."""
        smart_router.stats["total_requests"] = 10
        smart_router.stats["successful_requests"] = 8
        smart_router.stats["failed_requests"] = 2

        smart_router.reset_stats()

        assert smart_router.stats["total_requests"] == 0
        assert smart_router.stats["successful_requests"] == 0
        assert smart_router.stats["failed_requests"] == 0

    def test_update_stats_success(self, smart_router):
        """Test updating stats for successful request."""
        initial_total = smart_router.stats["total_requests"]
        initial_success = smart_router.stats["successful_requests"]

        smart_router._update_stats(True)

        assert smart_router.stats["total_requests"] == initial_total + 1
        assert smart_router.stats["successful_requests"] == initial_success + 1

    def test_update_stats_failure(self, smart_router):
        """Test updating stats for failed request."""
        initial_total = smart_router.stats["total_requests"]
        initial_failed = smart_router.stats["failed_requests"]

        smart_router._update_stats(False)

        assert smart_router.stats["total_requests"] == initial_total + 1
        assert smart_router.stats["failed_requests"] == initial_failed + 1

    def test_calculate_success_rate(self, smart_router):
        """Test calculating success rate."""
        smart_router.stats["total_requests"] = 10
        smart_router.stats["successful_requests"] = 8

        success_rate = smart_router._calculate_success_rate()

        assert success_rate == 0.8

    def test_calculate_success_rate_zero_requests(self, smart_router):
        """Test calculating success rate with zero requests."""
        smart_router.stats["total_requests"] = 0
        smart_router.stats["successful_requests"] = 0

        success_rate = smart_router._calculate_success_rate()

        assert success_rate == 0.0

    def test_engine_ranking_with_performance_metrics(self, smart_router):
        """Test engine ranking with performance metrics."""
        smart_router.performance_metrics = {
            "gtts": {"avg_time": 1.0, "success_rate": 0.9},
            "edge": {"avg_time": 0.5, "success_rate": 0.95},
        }

        ranking = smart_router.get_engine_ranking("en")

        assert isinstance(ranking, list)
        if len(ranking) >= 2:
            assert ranking[0] == "edge"

    def test_requirements_filtering(self, smart_router):
        """Test filtering engines by requirements."""
        requirements = {"offline": True}

        mock_engine1 = Mock()
        mock_engine1.get_capabilities.return_value.offline = True
        mock_engine2 = Mock()
        mock_engine2.get_capabilities.return_value.offline = False

        smart_router.registry.get_available_engines.return_value = [
            "engine1",
            "engine2",
        ]
        smart_router.registry.get_engine.side_effect = (
            lambda name: mock_engine1 if name == "engine1" else mock_engine2
        )

        filtered_engines = smart_router._filter_engines_by_requirements(
            ["engine1", "engine2"], requirements
        )

        assert "engine1" in filtered_engines
        assert "engine2" not in filtered_engines
