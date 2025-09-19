"""Additional tests for comprehensive SmartRouter coverage.

This module contains tests focusing on remaining paths and edge cases in SmartRouter,
including stats handling, ranking, recommendations, and internal methods.
"""

from unittest.mock import Mock

import pytest

from ttskit.engines.registry import EngineRegistry
from ttskit.engines.smart_router import SmartRouter


class TestSmartRouterAdditionalCoverage:
    """Tests for full path coverage in SmartRouter.

    Covers additional scenarios like empty metrics, failures, ranking with/without requirements,
    and internal resolution methods.
    """

    @pytest.fixture
    def mock_registry(self):
        """Create a mock EngineRegistry for testing.

        Sets up common return values for available engines, language support,
        requirements, and stats.
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
        """Create an instance of SmartRouter using the mock registry."""
        return SmartRouter(mock_registry)

    def test_get_engine_stats_empty_metrics(self, smart_router, mock_registry):
        """Test get_engine_stats with empty performance metrics.

        Parameters:
            smart_router: Fixture instance of SmartRouter.
            mock_registry: Fixture mock for EngineRegistry.

        Verifies all stats default to zero when no metrics are recorded.
        """
        smart_router.performance_metrics["gtts"] = []
        smart_router.failure_counts["gtts"] = 0

        stats = smart_router.get_engine_stats("gtts")

        assert stats["avg_duration"] == 0.0
        assert stats["min_duration"] == 0.0
        assert stats["max_duration"] == 0.0
        assert stats["total_requests"] == 0
        assert stats["failures"] == 0
        assert stats["success_rate"] == 0.0

    def test_get_engine_stats_with_failures(self, smart_router, mock_registry):
        """Test get_engine_stats when failures are present.

        Parameters:
            smart_router: Fixture instance of SmartRouter.
            mock_registry: Fixture mock for EngineRegistry.

        Notes:
            With 3 successful durations and 2 failures, expects average 1.5 and success rate 0.6.
        """
        smart_router.performance_metrics["gtts"] = [1.0, 1.5, 2.0]
        smart_router.failure_counts["gtts"] = 2

        stats = smart_router.get_engine_stats("gtts")

        assert stats["avg_duration"] == 1.5
        assert stats["min_duration"] == 1.0
        assert stats["max_duration"] == 2.0
        assert stats["total_requests"] == 3
        assert stats["failures"] == 2
        assert stats["success_rate"] == 0.6

    def test_get_engine_stats_with_last_used(self, smart_router, mock_registry):
        """Test get_engine_stats including last_used timestamp.

        Parameters:
            smart_router: Fixture instance of SmartRouter.
            mock_registry: Fixture mock for EngineRegistry.

        Notes:
            Sets last_used to current time and verifies it's positive in stats.
        """
        import time

        smart_router.performance_metrics["gtts"] = [1.0, 1.5]
        smart_router.failure_counts["gtts"] = 1
        smart_router.last_used["gtts"] = time.time()

        stats = smart_router.get_engine_stats("gtts")

        assert stats["last_used"] > 0

    def test_get_all_stats_with_engines_dict(self, smart_router, mock_registry):
        """Test get_all_stats when registry has an engines dictionary.

        Parameters:
            smart_router: Fixture instance of SmartRouter.
            mock_registry: Fixture mock for EngineRegistry.

        Notes:
            Includes per-engine stats and overall totals.
        """
        mock_registry.engines = {"gtts": Mock(), "edge": Mock()}

        smart_router.performance_metrics["gtts"] = [1.0, 1.5]
        smart_router.failure_counts["gtts"] = 1

        stats = smart_router.get_all_stats()

        assert "gtts" in stats
        assert "edge" in stats
        assert "total_requests" in stats

    def test_get_all_stats_without_engines_dict(self, smart_router, mock_registry):
        """Test get_all_stats without an engines dictionary on registry.

        Parameters:
            smart_router: Fixture instance of SmartRouter.
            mock_registry: Fixture mock for EngineRegistry.

        Notes:
            Falls back to available engines list for overall stats.
        """
        del mock_registry.engines
        mock_registry.get_available_engines.return_value = ["gtts", "edge"]

        stats = smart_router.get_all_stats()

        assert "total_requests" in stats
        assert "successful_requests" in stats
        assert "failed_requests" in stats

    def test_get_all_stats_with_exception(self, smart_router, mock_registry):
        """Test get_all_stats when getting available engines raises an exception.

        Parameters:
            smart_router: Fixture instance of SmartRouter.
            mock_registry: Fixture mock for EngineRegistry.

        Notes:
            Ensures stats are still computed with defaults despite the error.
        """
        del mock_registry.engines
        mock_registry.get_available_engines.side_effect = Exception(
            "Service unavailable"
        )

        stats = smart_router.get_all_stats()

        assert "total_requests" in stats
        assert "successful_requests" in stats
        assert "failed_requests" in stats

    def test_reset_stats_with_existing_data(self, smart_router, mock_registry):
        """Test reset_stats on existing performance data.

        Parameters:
            smart_router: Fixture instance of SmartRouter.
            mock_registry: Fixture mock for EngineRegistry.

        Notes:
            Clears all metrics, failures, last_used, and overall stats to defaults.
        """
        smart_router.performance_metrics["gtts"] = [1.0, 1.5]
        smart_router.failure_counts["gtts"] = 1
        smart_router.last_used["gtts"] = 1234567890
        smart_router.stats["total_requests"] = 10
        smart_router.stats["successful_requests"] = 8
        smart_router.stats["failed_requests"] = 2

        smart_router.reset_stats()

        assert smart_router.performance_metrics["gtts"] == []
        assert smart_router.failure_counts["gtts"] == 0
        assert smart_router.last_used["gtts"] == 0
        assert smart_router.stats["total_requests"] == 0
        assert smart_router.stats["successful_requests"] == 0
        assert smart_router.stats["failed_requests"] == 0

    def test_get_engine_ranking_with_requirements(self, smart_router, mock_registry):
        """Test get_engine_ranking with specific requirements.

        Parameters:
            smart_router: Fixture instance of SmartRouter.
            mock_registry: Fixture mock for EngineRegistry.

        Notes:
            Ranks engines based on performance metrics, filtering by offline requirement.
        """
        mock_registry.get_engines_for_language.return_value = ["gtts", "edge"]
        mock_registry.meets_requirements.return_value = True

        smart_router.performance_metrics["gtts"] = [1.0, 1.5]
        smart_router.performance_metrics["edge"] = [0.5, 0.8]
        smart_router.failure_counts["gtts"] = 0
        smart_router.failure_counts["edge"] = 0

        mock_engine = Mock()
        mock_engine.is_available.return_value = True
        mock_registry.get_engine.return_value = mock_engine

        ranking = smart_router.get_engine_ranking("en", {"offline": True})

        assert isinstance(ranking, list)
        assert len(ranking) == 2

    def test_get_engine_ranking_without_requirements(self, smart_router, mock_registry):
        """Test get_engine_ranking without requirements.

        Parameters:
            smart_router: Fixture instance of SmartRouter.
            mock_registry: Fixture mock for EngineRegistry.

        Notes:
            Ranks all available engines for the language based on performance.
        """
        mock_registry.get_engines_for_language.return_value = ["gtts", "edge"]

        smart_router.performance_metrics["gtts"] = [1.0, 1.5]
        smart_router.performance_metrics["edge"] = [0.5, 0.8]
        smart_router.failure_counts["gtts"] = 0
        smart_router.failure_counts["edge"] = 0

        ranking = smart_router.get_engine_ranking("en")

        assert isinstance(ranking, list)
        assert len(ranking) == 2

    def test_get_engine_ranking_new_engines(self, smart_router, mock_registry):
        """Test get_engine_ranking for new engines with no prior metrics.

        Parameters:
            smart_router: Fixture instance of SmartRouter.
            mock_registry: Fixture mock for EngineRegistry.

        Notes:
            Defaults to ranking based on availability when metrics are empty.
        """
        mock_registry.get_engines_for_language.return_value = ["gtts", "edge"]

        smart_router.performance_metrics = {}
        smart_router.failure_counts = {}

        ranking = smart_router.get_engine_ranking("en")

        assert isinstance(ranking, list)
        assert len(ranking) == 2

    def test_get_recommendations_with_requirements(self, smart_router, mock_registry):
        """Test get_recommendations with requirements.

        Parameters:
            smart_router: Fixture instance of SmartRouter.
            mock_registry: Fixture mock for EngineRegistry.

        Notes:
            Recommends top engines meeting offline requirements based on performance.
        """
        mock_registry.get_engines_for_language.return_value = ["gtts", "edge"]
        mock_registry.meets_requirements.return_value = True

        mock_engine = Mock()
        mock_engine.is_available.return_value = True
        mock_registry.get_engine.return_value = mock_engine
        mock_registry.engines = {"gtts": mock_engine, "edge": mock_engine}

        smart_router.performance_metrics["gtts"] = [1.0, 1.5]
        smart_router.performance_metrics["edge"] = [0.5, 0.8]
        smart_router.failure_counts["gtts"] = 0
        smart_router.failure_counts["edge"] = 0

        recommendations = smart_router.get_recommendations("en", {"offline": True})

        assert isinstance(recommendations, list)

    def test_get_recommendations_without_requirements(
        self, smart_router, mock_registry
    ):
        """Test get_recommendations without requirements.

        Parameters:
            smart_router: Fixture instance of SmartRouter.
            mock_registry: Fixture mock for EngineRegistry.

        Notes:
            Recommends best engines for the language based on overall performance.
        """
        mock_registry.get_engines_for_language.return_value = ["gtts", "edge"]
        mock_registry.meets_requirements.return_value = True

        mock_engine = Mock()
        mock_engine.is_available.return_value = True
        mock_registry.get_engine.return_value = mock_engine
        mock_registry.engines = {"gtts": mock_engine, "edge": mock_engine}

        smart_router.performance_metrics["gtts"] = [1.0, 1.5]
        smart_router.performance_metrics["edge"] = [0.5, 0.8]
        smart_router.failure_counts["gtts"] = 0
        smart_router.failure_counts["edge"] = 0

        recommendations = smart_router.get_recommendations("en")

        assert isinstance(recommendations, list)

    def test_resolve_available_engines_success(self, smart_router, mock_registry):
        """Test successful resolution of available engines.

        Parameters:
            smart_router: Fixture instance of SmartRouter.
            mock_registry: Fixture mock for EngineRegistry.

        Notes:
            Returns engines for the specified language when query succeeds.
        """
        mock_registry.get_engines_for_language.return_value = ["gtts", "edge"]

        engines = smart_router._resolve_available_engines("en")

        assert engines == ["gtts", "edge"]

    def test_resolve_available_engines_fallback(self, smart_router, mock_registry):
        """Test fallback in _resolve_available_engines on language query failure.

        Parameters:
            smart_router: Fixture instance of SmartRouter.
            mock_registry: Fixture mock for EngineRegistry.

        Notes:
            Falls back to all available engines when language-specific query fails.
        """
        mock_registry.get_engines_for_language.side_effect = Exception(
            "Service unavailable"
        )
        mock_registry.get_available_engines.return_value = ["gtts", "edge", "piper"]

        engines = smart_router._resolve_available_engines("en")

        assert engines == ["gtts", "edge", "piper"]

    def test_resolve_available_engines_complete_failure(
        self, smart_router, mock_registry
    ):
        """Test complete failure in _resolve_available_engines.

        Parameters:
            smart_router: Fixture instance of SmartRouter.
            mock_registry: Fixture mock for EngineRegistry.

        Notes:
            Returns empty list if both language and general queries fail.
        """
        mock_registry.get_engines_for_language.side_effect = Exception(
            "Service unavailable"
        )
        mock_registry.get_available_engines.side_effect = Exception(
            "Service unavailable"
        )

        engines = smart_router._resolve_available_engines("en")

        assert engines == []

    def test_resolve_available_engines_non_list_result(
        self, smart_router, mock_registry
    ):
        """Test _resolve_available_engines with non-list result from query.

        Parameters:
            smart_router: Fixture instance of SmartRouter.
            mock_registry: Fixture mock for EngineRegistry.

        Notes:
            Falls back to available engines if language query returns invalid type.
        """
        mock_registry.get_engines_for_language.return_value = "not_a_list"

        engines = smart_router._resolve_available_engines("en")

        assert engines == ["gtts", "edge", "piper"]

    def test_record_success_new_engine(self, smart_router, mock_registry):
        """Test record_success for a new engine.

        Parameters:
            smart_router: Fixture instance of SmartRouter.
            mock_registry: Fixture mock for EngineRegistry.

        Notes:
            Initializes metrics and last_used for the new engine with the duration.
        """
        smart_router.record_success("new_engine", 1.0)

        assert "new_engine" in smart_router.performance_metrics
        assert len(smart_router.performance_metrics["new_engine"]) == 1
        assert smart_router.performance_metrics["new_engine"][0] == 1.0
        assert "new_engine" in smart_router.last_used

    def test_record_success_existing_engine(self, smart_router, mock_registry):
        """Test record_success for an existing engine.

        Parameters:
            smart_router: Fixture instance of SmartRouter.
            mock_registry: Fixture mock for EngineRegistry.

        Notes:
            Appends the new duration to existing metrics list.
        """
        smart_router.performance_metrics["gtts"] = [1.0]
        smart_router.record_success("gtts", 1.5)

        assert len(smart_router.performance_metrics["gtts"]) == 2
        assert smart_router.performance_metrics["gtts"][1] == 1.5

    def test_record_success_trim_metrics(self, smart_router, mock_registry):
        """Test record_success with metrics trimming.

        Parameters:
            smart_router: Fixture instance of SmartRouter.
            mock_registry: Fixture mock for EngineRegistry.

        Notes:
            Ensures the metrics list stays at max length (100) by trimming old entries.
        """
        smart_router.performance_metrics["gtts"] = list(range(100))

        smart_router.record_success("gtts", 101.0)

        assert len(smart_router.performance_metrics["gtts"]) == 100
        assert smart_router.performance_metrics["gtts"][-1] == 101.0

    def test_record_failure_new_engine(self, smart_router, mock_registry):
        """Test record_failure for a new engine.

        Parameters:
            smart_router: Fixture instance of SmartRouter.
            mock_registry: Fixture mock for EngineRegistry.

        Notes:
            Initializes failure count to 1 for the new engine.
        """
        smart_router.record_failure("new_engine")

        assert smart_router.failure_counts["new_engine"] == 1

    def test_record_failure_existing_engine(self, smart_router, mock_registry):
        """Test record_failure for an existing engine.

        Parameters:
            smart_router: Fixture instance of SmartRouter.
            mock_registry: Fixture mock for EngineRegistry.

        Notes:
            Increments the failure count for the engine.
        """
        smart_router.failure_counts["gtts"] = 1
        smart_router.record_failure("gtts")

        assert smart_router.failure_counts["gtts"] == 2

    def test_calculate_success_rate_with_requests(self, smart_router, mock_registry):
        """Test _calculate_success_rate with recorded requests.

        Parameters:
            smart_router: Fixture instance of SmartRouter.
            mock_registry: Fixture mock for EngineRegistry.

        Notes:
            Computes success rate as successful / total (8/10 = 0.8).
        """
        smart_router.stats["total_requests"] = 10
        smart_router.stats["successful_requests"] = 8

        success_rate = smart_router._calculate_success_rate()

        assert success_rate == 0.8

    def test_calculate_success_rate_zero_requests(self, smart_router, mock_registry):
        """Test _calculate_success_rate with zero requests.

        Parameters:
            smart_router: Fixture instance of SmartRouter.
            mock_registry: Fixture mock for EngineRegistry.

        Notes:
            Returns 0.0 when no requests have been made.
        """
        smart_router.stats["total_requests"] = 0
        smart_router.stats["successful_requests"] = 0

        success_rate = smart_router._calculate_success_rate()

        assert success_rate == 0.0

    def test_update_stats_success(self, smart_router, mock_registry):
        """Test _update_stats for a successful operation.

        Parameters:
            smart_router: Fixture instance of SmartRouter.
            mock_registry: Fixture mock for EngineRegistry.

        Notes:
            Increments both total and successful request counts.
        """
        initial_total = smart_router.stats["total_requests"]
        initial_success = smart_router.stats["successful_requests"]

        smart_router._update_stats(True)

        assert smart_router.stats["total_requests"] == initial_total + 1
        assert smart_router.stats["successful_requests"] == initial_success + 1

    def test_update_stats_failure(self, smart_router, mock_registry):
        """Test _update_stats for a failed operation.

        Parameters:
            smart_router: Fixture instance of SmartRouter.
            mock_registry: Fixture mock for EngineRegistry.

        Notes:
            Increments total and failed request counts.
        """
        initial_total = smart_router.stats["total_requests"]
        initial_failed = smart_router.stats["failed_requests"]

        smart_router._update_stats(False)

        assert smart_router.stats["total_requests"] == initial_total + 1
        assert smart_router.stats["failed_requests"] == initial_failed + 1

    def test_select_best_engine_compatibility(self, smart_router, mock_registry):
        """Test compatibility layer in select_best_engine.

        Parameters:
            smart_router: Fixture instance of SmartRouter.
            mock_registry: Fixture mock for EngineRegistry.

        Notes:
            Ensures select_best_engine calls get_best_engine without requirements.
        """
        smart_router.get_best_engine = Mock(return_value="gtts")

        result = smart_router.select_best_engine("en")

        assert result == "gtts"
        smart_router.get_best_engine.assert_called_once_with("en", None)

    def test_get_engine_compatibility(self, smart_router, mock_registry):
        """Test compatibility in get_engine method.

        Parameters:
            smart_router: Fixture instance of SmartRouter.
            mock_registry: Fixture mock for EngineRegistry.

        Notes:
            Retrieves existing engines from registry; returns None for unknown ones.
        """
        mock_registry.engines = {"gtts": Mock(), "edge": Mock()}

        engine = smart_router.get_engine("gtts")
        assert engine is not None

        engine = smart_router.get_engine("nonexistent")
        assert engine is None
