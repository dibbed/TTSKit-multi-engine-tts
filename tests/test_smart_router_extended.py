"""Extended tests for Smart Router module - covering untested paths."""

from unittest.mock import Mock

import pytest

from ttskit.engines.registry import EngineRegistry
from ttskit.engines.smart_router import SmartRouter
from ttskit.exceptions import AllEnginesFailedError


class TestSmartRouterEngineSelectionExtended:
    """Extended tests for engine selection scenarios (language/voice rules)."""

    @pytest.fixture
    def mock_registry(self):
        """Create mock engine registry."""
        registry = Mock(spec=EngineRegistry)
        registry.get_available_engines.return_value = ["gtts", "edge", "piper"]
        registry.get_engines_for_language.return_value = ["gtts", "edge"]
        registry.get_engine.return_value = Mock()
        registry.meets_requirements.return_value = True
        registry.get_engine_stats.return_value = {
            "total_requests": 100,
            "success_rate": 0.95,
            "avg_duration": 1.0,
        }
        return registry

    @pytest.fixture
    def smart_router(self, mock_registry):
        """Create SmartRouter instance."""
        return SmartRouter(mock_registry)

    def test_select_engine_language_rule_scenario_1(self, smart_router, mock_registry):
        """Test engine selection for English language rule scenario."""
        lang = "en"
        requirements = {}

        mock_registry.get_engines_for_language.return_value = ["gtts", "edge"]

        mock_engine1 = Mock()
        mock_engine1.is_available.return_value = True
        mock_engine2 = Mock()
        mock_engine2.is_available.return_value = True

        mock_registry.get_engine.side_effect = (
            lambda name: mock_engine1 if name == "gtts" else mock_engine2
        )

        selected_engine = smart_router.select_engine(lang, requirements)

        assert selected_engine is not None
        assert selected_engine in ["gtts", "edge"]

    def test_select_engine_language_rule_scenario_2(self, smart_router, mock_registry):
        """Test engine selection for Persian language rule scenario."""
        lang = "fa"
        requirements = {"offline": True}

        mock_registry.get_engines_for_language.return_value = ["piper", "edge"]

        mock_engine1 = Mock()
        mock_engine1.is_available.return_value = True
        mock_engine1.get_capabilities.return_value.offline = True

        mock_engine2 = Mock()
        mock_engine2.is_available.return_value = True
        mock_engine2.get_capabilities.return_value.offline = False

        mock_registry.get_engine.side_effect = (
            lambda name: mock_engine1 if name == "piper" else mock_engine2
        )
        mock_registry.meets_requirements.side_effect = lambda name, req: name == "piper"

        selected_engine = smart_router.select_engine(lang, requirements)

        assert selected_engine == "piper"

    def test_select_engine_language_rule_scenario_3(self, smart_router, mock_registry):
        """Test engine selection for Arabic language with voice requirement."""
        lang = "ar"
        requirements = {"voice": "kareem"}

        mock_registry.get_engines_for_language.return_value = ["piper", "gtts"]

        mock_engine1 = Mock()
        mock_engine1.is_available.return_value = True
        mock_engine2 = Mock()
        mock_engine2.is_available.return_value = True

        mock_registry.get_engine.side_effect = (
            lambda name: mock_engine1 if name == "piper" else mock_engine2
        )
        mock_registry.meets_requirements.return_value = True

        selected_engine = smart_router.select_engine(lang, requirements)

        assert selected_engine is not None
        assert selected_engine in ["piper", "gtts"]

    def test_select_engine_voice_rule_scenario_1(self, smart_router, mock_registry):
        """Test engine selection for specific voice rule scenario."""
        lang = "en"
        requirements = {"voice": "lessac"}

        mock_registry.get_engines_for_language.return_value = ["piper", "edge"]

        mock_engine1 = Mock()
        mock_engine1.is_available.return_value = True
        mock_engine2 = Mock()
        mock_engine2.is_available.return_value = True

        mock_registry.get_engine.side_effect = (
            lambda name: mock_engine1 if name == "piper" else mock_engine2
        )
        mock_registry.meets_requirements.return_value = True

        selected_engine = smart_router.select_engine(lang, requirements)

        assert selected_engine is not None
        assert selected_engine in ["piper", "edge"]

    def test_select_engine_voice_rule_scenario_2(self, smart_router, mock_registry):
        """Test engine selection for voice with offline requirement."""
        lang = "fa"
        requirements = {"voice": "amir", "offline": True}

        mock_registry.get_engines_for_language.return_value = ["piper", "gtts"]

        mock_engine1 = Mock()
        mock_engine1.is_available.return_value = True
        mock_engine1.get_capabilities.return_value.offline = True

        mock_engine2 = Mock()
        mock_engine2.is_available.return_value = True
        mock_engine2.get_capabilities.return_value.offline = False

        mock_registry.get_engine.side_effect = (
            lambda name: mock_engine1 if name == "piper" else mock_engine2
        )
        mock_registry.meets_requirements.side_effect = lambda name, req: name == "piper"

        selected_engine = smart_router.select_engine(lang, requirements)

        assert selected_engine == "piper"

    def test_select_engine_voice_rule_scenario_3(self, smart_router, mock_registry):
        """Test engine selection for voice with performance requirement."""
        lang = "en"
        requirements = {"voice": "lessac", "performance": "high"}

        mock_registry.get_engines_for_language.return_value = ["edge", "piper"]

        mock_engine1 = Mock()
        mock_engine1.is_available.return_value = True
        mock_engine2 = Mock()
        mock_engine2.is_available.return_value = True

        mock_registry.get_engine.side_effect = (
            lambda name: mock_engine1 if name == "edge" else mock_engine2
        )
        mock_registry.meets_requirements.return_value = True

        selected_engine = smart_router.select_engine(lang, requirements)

        assert selected_engine is not None
        assert selected_engine in ["edge", "piper"]

    def test_get_best_engine_performance_based_selection(
        self, smart_router, mock_registry
    ):
        """Test best engine selection based on performance metrics."""
        mock_registry.get_engines_for_language.return_value = ["gtts", "edge", "piper"]

        mock_engine1 = Mock()
        mock_engine1.is_available.return_value = True
        mock_engine2 = Mock()
        mock_engine2.is_available.return_value = True
        mock_engine3 = Mock()
        mock_engine3.is_available.return_value = True

        mock_registry.get_engine.side_effect = lambda name: {
            "gtts": mock_engine1,
            "edge": mock_engine2,
            "piper": mock_engine3,
        }[name]

        mock_registry.get_engine_stats.side_effect = lambda name: {
            "gtts": {"total_requests": 100, "success_rate": 0.9, "avg_duration": 2.0},
            "edge": {"total_requests": 100, "success_rate": 0.95, "avg_duration": 1.0},
            "piper": {"total_requests": 100, "success_rate": 0.85, "avg_duration": 1.5},
        }[name]

        mock_registry.meets_requirements.return_value = True

        best_engine = smart_router.get_best_engine("en")

        assert best_engine == "edge"

    def test_get_best_engine_no_suitable_engines(self, smart_router, mock_registry):
        """Test best engine selection when no engines meet requirements."""
        mock_registry.get_engines_for_language.return_value = ["gtts", "edge"]

        mock_engine1 = Mock()
        mock_engine1.is_available.return_value = True
        mock_engine2 = Mock()
        mock_engine2.is_available.return_value = True

        mock_registry.get_engine.side_effect = (
            lambda name: mock_engine1 if name == "gtts" else mock_engine2
        )

        mock_registry.meets_requirements.return_value = False

        best_engine = smart_router.get_best_engine("en", {"offline": True})

        assert best_engine is None

    def test_get_best_engine_no_engines_available(self, smart_router, mock_registry):
        """Test best engine selection when no engines are available."""
        mock_registry.get_engines_for_language.return_value = []

        best_engine = smart_router.get_best_engine("xyz")

        assert best_engine is None


class TestSmartRouterFallbackExtended:
    """Extended tests for fallback mechanisms when engine loading fails."""

    @pytest.fixture
    def mock_registry(self):
        """Create mock engine registry."""
        registry = Mock(spec=EngineRegistry)
        registry.get_available_engines.return_value = ["gtts", "edge", "piper"]
        registry.get_engines_for_language.return_value = ["gtts", "edge", "piper"]
        registry.meets_requirements.return_value = True
        return registry

    @pytest.fixture
    def smart_router(self, mock_registry):
        """Create SmartRouter instance."""
        return SmartRouter(mock_registry)

    @pytest.mark.asyncio
    async def test_synth_async_engine_load_failure_fallback(
        self, smart_router, mock_registry
    ):
        """Test synthesis with engine load failure and fallback."""
        mock_registry.get_engines_for_language.return_value = ["gtts", "edge", "piper"]

        mock_registry.get_engine.side_effect = [
            None,
            Mock(),
            Mock(),
        ]

        mock_engine_edge = Mock()
        mock_engine_edge.is_available.return_value = True
        mock_engine_edge.synth_async.return_value = b"audio_data"

        mock_engine_piper = Mock()
        mock_engine_piper.is_available.return_value = True
        mock_engine_piper.synth_async.return_value = b"audio_data"

        mock_registry.engines = {
            "gtts": None,
            "edge": mock_engine_edge,
            "piper": mock_engine_piper,
        }

        smart_router.select_best_engine = Mock(return_value="edge")

        audio_data, engine_name = await smart_router.synth_async("Hello", "en")

        assert audio_data == b"audio_data"
        assert engine_name == "edge"

    @pytest.mark.asyncio
    async def test_synth_async_engine_availability_failure_fallback(
        self, smart_router, mock_registry
    ):
        """Test synthesis with engine availability failure and fallback."""
        mock_registry.get_engines_for_language.return_value = ["gtts", "edge", "piper"]

        mock_engine_gtts = Mock()
        mock_engine_gtts.is_available.return_value = False

        mock_engine_edge = Mock()
        mock_engine_edge.is_available.return_value = True
        mock_engine_edge.synth_async.return_value = b"audio_data"

        mock_engine_piper = Mock()
        mock_engine_piper.is_available.return_value = True
        mock_engine_piper.synth_async.return_value = b"audio_data"

        mock_registry.get_engine.side_effect = lambda name: {
            "gtts": mock_engine_gtts,
            "edge": mock_engine_edge,
            "piper": mock_engine_piper,
        }[name]

        smart_router.select_best_engine = Mock(return_value="edge")

        audio_data, engine_name = await smart_router.synth_async("Hello", "en")

        assert audio_data == b"audio_data"
        assert engine_name == "edge"

    @pytest.mark.asyncio
    async def test_synth_async_engine_synthesis_failure_fallback(
        self, smart_router, mock_registry
    ):
        """Test synthesis with engine synthesis failure and fallback."""
        mock_registry.get_engines_for_language.return_value = ["gtts", "edge", "piper"]

        mock_engine_gtts = Mock()
        mock_engine_gtts.is_available.return_value = True
        mock_engine_gtts.synth_async.side_effect = Exception("gTTS service unavailable")

        mock_engine_edge = Mock()
        mock_engine_edge.is_available.return_value = True
        mock_engine_edge.synth_async.return_value = b"audio_data"

        mock_engine_piper = Mock()
        mock_engine_piper.is_available.return_value = True
        mock_engine_piper.synth_async.return_value = b"audio_data"

        mock_registry.get_engine.side_effect = lambda name: {
            "gtts": mock_engine_gtts,
            "edge": mock_engine_edge,
            "piper": mock_engine_piper,
        }[name]

        smart_router.select_best_engine = Mock(return_value="edge")

        audio_data, engine_name = await smart_router.synth_async("Hello", "en")

        assert audio_data == b"audio_data"
        assert engine_name == "edge"

    @pytest.mark.asyncio
    async def test_synth_async_all_engines_fail_fallback(
        self, smart_router, mock_registry
    ):
        """Test synthesis when all engines fail."""
        mock_registry.get_engines_for_language.return_value = ["gtts", "edge", "piper"]

        mock_engine_gtts = Mock()
        mock_engine_gtts.is_available.return_value = True
        mock_engine_gtts.synth_async.side_effect = Exception("gTTS service unavailable")

        mock_engine_edge = Mock()
        mock_engine_edge.is_available.return_value = True
        mock_engine_edge.synth_async.side_effect = Exception("Edge service unavailable")

        mock_engine_piper = Mock()
        mock_engine_piper.is_available.return_value = True
        mock_engine_piper.synth_async.side_effect = Exception(
            "Piper service unavailable"
        )

        mock_registry.get_engine.side_effect = lambda name: {
            "gtts": mock_engine_gtts,
            "edge": mock_engine_edge,
            "piper": mock_engine_piper,
        }[name]

        smart_router.select_best_engine = Mock(return_value="gtts")

        with pytest.raises(AllEnginesFailedError):
            await smart_router.synth_async("Hello", "en")

    @pytest.mark.asyncio
    async def test_synth_async_engine_not_found_fallback(
        self, smart_router, mock_registry
    ):
        """Test synthesis when engine is not found in registry."""
        mock_registry.get_engines_for_language.return_value = ["gtts", "edge", "piper"]

        mock_registry.get_engine.side_effect = Exception("Engine not found")

        mock_registry.engines = {"gtts": None, "edge": None, "piper": None}

        smart_router.select_best_engine = Mock(return_value="gtts")

        with pytest.raises(AllEnginesFailedError):
            await smart_router.synth_async("Hello", "en")

    @pytest.mark.asyncio
    async def test_synth_async_requirements_not_met_fallback(
        self, smart_router, mock_registry
    ):
        """Test synthesis when engine doesn't meet requirements."""
        mock_registry.get_engines_for_language.return_value = ["gtts", "edge", "piper"]

        mock_engine_gtts = Mock()
        mock_engine_gtts.is_available.return_value = True
        mock_engine_gtts.synth_async.return_value = b"audio_data"

        mock_engine_edge = Mock()
        mock_engine_edge.is_available.return_value = True
        mock_engine_edge.synth_async.return_value = b"audio_data"

        mock_registry.get_engine.side_effect = lambda name: {
            "gtts": mock_engine_gtts,
            "edge": mock_engine_edge,
            "piper": Mock(),
        }[name]

        mock_registry.meets_requirements.side_effect = lambda name, req: name != "gtts"

        smart_router.select_best_engine = Mock(return_value="edge")

        audio_data, engine_name = await smart_router.synth_async(
            "Hello", "en", {"offline": True}
        )

        assert audio_data == b"audio_data"
        assert engine_name == "edge"


class TestSmartRouterBranchCoverageExtended:
    """Extended tests for complete branch coverage - both happy and error paths."""

    @pytest.fixture
    def mock_registry(self):
        """Create mock engine registry."""
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
        """Create SmartRouter instance."""
        return SmartRouter(mock_registry)

    def test_resolve_available_engines_both_paths(self, smart_router, mock_registry):
        """Test _resolve_available_engines - both success and failure."""
        mock_registry.get_engines_for_language.return_value = ["gtts", "edge"]
        engines = smart_router._resolve_available_engines("en")
        assert engines == ["gtts", "edge"]

        mock_registry.get_engines_for_language.side_effect = Exception(
            "Service unavailable"
        )
        mock_registry.get_available_engines.return_value = ["gtts", "edge", "piper"]
        engines = smart_router._resolve_available_engines("en")
        assert engines == ["gtts", "edge", "piper"]

        mock_registry.get_engines_for_language.side_effect = Exception(
            "Service unavailable"
        )
        mock_registry.get_available_engines.side_effect = Exception(
            "Service unavailable"
        )
        engines = smart_router._resolve_available_engines("en")
        assert engines == []

    def test_filter_engines_by_requirements_both_paths(
        self, smart_router, mock_registry
    ):
        """Test _filter_engines_by_requirements - both success and failure."""
        mock_registry.meets_requirements.return_value = True
        engines = ["gtts", "edge", "piper"]
        requirements = {"offline": True}

        filtered = smart_router._filter_engines_by_requirements(engines, requirements)
        assert filtered == ["gtts", "edge", "piper"]

        mock_registry.meets_requirements.side_effect = Exception("Service unavailable")

        mock_engine = Mock()
        mock_engine.get_capabilities.return_value.offline = True
        mock_registry.get_engine.return_value = mock_engine

        filtered = smart_router._filter_engines_by_requirements(engines, requirements)
        assert filtered == ["gtts", "edge", "piper"]

    def test_get_engine_stats_both_paths(self, smart_router, mock_registry):
        """Test get_engine_stats - both with and without metrics."""
        smart_router.performance_metrics["gtts"] = [1.0, 1.5, 2.0]
        smart_router.failure_counts["gtts"] = 1

        stats = smart_router.get_engine_stats("gtts")
        assert "avg_duration" in stats
        assert "total_requests" in stats
        assert "success_rate" in stats

        stats = smart_router.get_engine_stats("nonexistent")
        assert stats == {}

        smart_router.performance_metrics["edge"] = {
            "avg_time": 1.0,
            "success_rate": 0.9,
        }
        smart_router.failure_counts["edge"] = 2

        stats = smart_router.get_engine_stats("edge")
        assert "avg_duration" in stats
        assert "total_requests" in stats
        assert "success_rate" in stats

    def test_get_all_stats_both_paths(self, smart_router, mock_registry):
        """Test get_all_stats - both with and without engines."""
        mock_registry.engines = {"gtts": Mock(), "edge": Mock()}
        stats = smart_router.get_all_stats()
        assert "gtts" in stats
        assert "edge" in stats
        assert "total_requests" in stats

        mock_registry.engines = {}
        mock_registry.get_available_engines.side_effect = Exception(
            "Service unavailable"
        )
        stats = smart_router.get_all_stats()
        assert "total_requests" in stats
        assert "successful_requests" in stats
        assert "failed_requests" in stats

    def test_get_engine_ranking_both_paths(self, smart_router, mock_registry):
        """Test get_engine_ranking - both with and without requirements."""
        mock_registry.get_engines_for_language.return_value = ["gtts", "edge"]
        smart_router.performance_metrics = {"gtts": [1.0, 1.5], "edge": [0.5, 0.8]}
        smart_router.failure_counts = {"gtts": 0, "edge": 0}

        ranking = smart_router.get_engine_ranking("en")
        assert isinstance(ranking, list)
        assert len(ranking) == 2

        requirements = {"offline": True}
        mock_registry.meets_requirements.return_value = True

        ranking = smart_router.get_engine_ranking("en", requirements)
        assert isinstance(ranking, list)

    def test_get_recommendations_both_paths(self, smart_router, mock_registry):
        """Test get_recommendations - both with and without requirements."""
        mock_registry.get_engines_for_language.return_value = ["gtts", "edge"]
        mock_engine = Mock()
        mock_engine.is_available.return_value = True
        mock_registry.get_engine.return_value = mock_engine
        mock_registry.meets_requirements.return_value = True

        mock_registry.engines = {"gtts": mock_engine, "edge": mock_engine}

        recommendations = smart_router.get_recommendations("en")
        assert isinstance(recommendations, list)

        requirements = {"offline": True}
        recommendations = smart_router.get_recommendations("en", requirements)
        assert isinstance(recommendations, list)

    def test_record_success_both_paths(self, smart_router, mock_registry):
        """Test record_success - both new and existing engine."""
        smart_router.record_success("new_engine", 1.0)
        assert "new_engine" in smart_router.performance_metrics
        assert len(smart_router.performance_metrics["new_engine"]) == 1

        smart_router.record_success("new_engine", 1.5)
        assert len(smart_router.performance_metrics["new_engine"]) == 2

        for _ in range(105):
            smart_router.record_success("new_engine", 1.0)
        assert len(smart_router.performance_metrics["new_engine"]) == 100

    def test_record_failure_both_paths(self, smart_router, mock_registry):
        """Test record_failure - both new and existing engine."""
        smart_router.record_failure("new_engine")
        assert smart_router.failure_counts["new_engine"] == 1

        smart_router.record_failure("new_engine")
        assert smart_router.failure_counts["new_engine"] == 2

    def test_reset_stats_both_paths(self, smart_router, mock_registry):
        """Test reset_stats - both with and without metrics."""
        smart_router.performance_metrics = {"gtts": [1.0, 1.5], "edge": [0.5]}
        smart_router.failure_counts = {"gtts": 1, "edge": 0}
        smart_router.stats = {
            "total_requests": 10,
            "successful_requests": 8,
            "failed_requests": 2,
        }

        smart_router.reset_stats()

        assert smart_router.performance_metrics["gtts"] == []
        assert smart_router.performance_metrics["edge"] == []
        assert smart_router.failure_counts["gtts"] == 0
        assert smart_router.failure_counts["edge"] == 0
        assert smart_router.stats["total_requests"] == 0
        assert smart_router.stats["successful_requests"] == 0
        assert smart_router.stats["failed_requests"] == 0

        smart_router.reset_stats()

    def test_calculate_success_rate_both_paths(self, smart_router, mock_registry):
        """Test _calculate_success_rate - both with and without requests."""
        smart_router.stats["total_requests"] = 10
        smart_router.stats["successful_requests"] = 8
        success_rate = smart_router._calculate_success_rate()
        assert success_rate == 0.8

        smart_router.stats["total_requests"] = 0
        smart_router.stats["successful_requests"] = 0
        success_rate = smart_router._calculate_success_rate()
        assert success_rate == 0.0

    def test_update_stats_both_paths(self, smart_router, mock_registry):
        """Test _update_stats - both success and failure."""
        initial_total = smart_router.stats["total_requests"]
        initial_success = smart_router.stats["successful_requests"]

        smart_router._update_stats(True)

        assert smart_router.stats["total_requests"] == initial_total + 1
        assert smart_router.stats["successful_requests"] == initial_success + 1

        initial_total = smart_router.stats["total_requests"]
        initial_failed = smart_router.stats["failed_requests"]

        smart_router._update_stats(False)

        assert smart_router.stats["total_requests"] == initial_total + 1
        assert smart_router.stats["failed_requests"] == initial_failed + 1

    def test_select_best_engine_compatibility_alias(self, smart_router, mock_registry):
        """Test select_best_engine compatibility alias."""
        smart_router.get_best_engine = Mock(return_value="gtts")

        result = smart_router.select_best_engine("en")

        assert result == "gtts"
        smart_router.get_best_engine.assert_called_once_with("en", None)

    def test_get_engine_compatibility_method(self, smart_router, mock_registry):
        """Test get_engine compatibility method."""
        mock_registry.engines = {"gtts": Mock(), "edge": Mock()}

        engine = smart_router.get_engine("gtts")
        assert engine is not None

        engine = smart_router.get_engine("nonexistent")
        assert engine is None
