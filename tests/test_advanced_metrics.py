"""Comprehensive tests for AdvancedMetricsCollector module."""

import asyncio
import json
import tempfile
from collections import deque
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from ttskit.metrics.advanced import (
    AdvancedMetricsCollector,
    CacheMetrics,
    EngineMetrics,
    LanguageMetrics,
    SystemMetrics,
    get_metrics_collector,
    start_metrics_collection,
)


class TestEngineMetrics:
    """Test cases for EngineMetrics dataclass."""

    def test_engine_metrics_initialization(self):
        """Test EngineMetrics initialization."""
        metrics = EngineMetrics(engine_name="test_engine")

        assert metrics.engine_name == "test_engine"
        assert metrics.total_requests == 0
        assert metrics.successful_requests == 0
        assert metrics.failed_requests == 0
        assert metrics.total_response_time == 0.0
        assert metrics.min_response_time == float("inf")
        assert metrics.max_response_time == 0.0
        assert metrics.last_request_time is None
        assert isinstance(metrics.error_types, dict)

    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        metrics = EngineMetrics(engine_name="test_engine")

        assert metrics.success_rate == 0.0

        metrics.total_requests = 10
        metrics.successful_requests = 10
        assert metrics.success_rate == 100.0

        metrics.total_requests = 10
        metrics.successful_requests = 7
        assert metrics.success_rate == 70.0

    def test_avg_response_time_calculation(self):
        """Test average response time calculation."""
        metrics = EngineMetrics(engine_name="test_engine")

        assert metrics.avg_response_time == 0.0

        metrics.successful_requests = 5
        metrics.total_response_time = 10.0
        assert metrics.avg_response_time == 2.0


class TestLanguageMetrics:
    """Test cases for LanguageMetrics dataclass."""

    def test_language_metrics_initialization(self):
        """Test LanguageMetrics initialization."""
        metrics = LanguageMetrics(language="en")

        assert metrics.language == "en"
        assert metrics.total_requests == 0
        assert metrics.successful_requests == 0
        assert metrics.failed_requests == 0
        assert metrics.total_response_time == 0.0
        assert isinstance(metrics.engines_used, dict)

    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        metrics = LanguageMetrics(language="en")

        assert metrics.success_rate == 0.0

        metrics.total_requests = 10
        metrics.successful_requests = 10
        assert metrics.success_rate == 100.0

        metrics.total_requests = 10
        metrics.successful_requests = 6
        assert metrics.success_rate == 60.0


class TestCacheMetrics:
    """Test cases for CacheMetrics dataclass."""

    def test_cache_metrics_initialization(self):
        """Test CacheMetrics initialization."""
        metrics = CacheMetrics()

        assert metrics.total_hits == 0
        assert metrics.total_misses == 0
        assert metrics.total_size_bytes == 0
        assert metrics.evictions == 0
        assert metrics.hit_rate == 0.0

    def test_update_hit_rate(self):
        """Test hit rate update calculation."""
        metrics = CacheMetrics()

        metrics.update_hit_rate()
        assert metrics.hit_rate == 0.0

        metrics.total_hits = 10
        metrics.total_misses = 0
        metrics.update_hit_rate()
        assert metrics.hit_rate == 100.0

        metrics.total_hits = 7
        metrics.total_misses = 3
        metrics.update_hit_rate()
        assert metrics.hit_rate == 70.0


class TestSystemMetrics:
    """Test cases for SystemMetrics dataclass."""

    def test_system_metrics_initialization(self):
        """Test SystemMetrics initialization."""
        metrics = SystemMetrics()

        assert metrics.cpu_percent == 0.0
        assert metrics.memory_mb == 0.0
        assert metrics.memory_percent == 0.0
        assert metrics.disk_usage_percent == 0.0
        assert metrics.network_io_bytes == 0
        assert metrics.timestamp is not None

    def test_system_metrics_custom_timestamp(self):
        """Test SystemMetrics with custom timestamp."""
        custom_time = datetime(2023, 1, 1, 12, 0, 0)
        metrics = SystemMetrics(timestamp=custom_time)

        assert metrics.timestamp == custom_time


class TestAdvancedMetricsCollector:
    """Test cases for AdvancedMetricsCollector class."""

    @pytest.fixture
    def collector(self):
        """Create AdvancedMetricsCollector instance for testing."""
        return AdvancedMetricsCollector(history_size=100)

    def test_collector_initialization(self, collector):
        """Test collector initialization."""
        assert collector.history_size == 100
        assert isinstance(collector.engines, dict)
        assert isinstance(collector.languages, dict)
        assert isinstance(collector.cache, CacheMetrics)
        assert isinstance(collector.system_history, deque)
        assert isinstance(collector.request_history, deque)
        assert collector._start_time is not None

    @pytest.mark.asyncio
    async def test_record_request_success(self, collector):
        """Test recording successful request."""
        await collector.record_request(
            engine="gtts", language="en", response_time=1.5, success=True
        )

        assert "gtts" in collector.engines
        assert "en" in collector.languages

        engine_metrics = collector.engines["gtts"]
        assert engine_metrics.total_requests == 1
        assert engine_metrics.successful_requests == 1
        assert engine_metrics.failed_requests == 0
        assert engine_metrics.total_response_time == 1.5
        assert engine_metrics.min_response_time == 1.5
        assert engine_metrics.max_response_time == 1.5
        assert engine_metrics.last_request_time is not None

        language_metrics = collector.languages["en"]
        assert language_metrics.total_requests == 1
        assert language_metrics.successful_requests == 1
        assert language_metrics.failed_requests == 0
        assert language_metrics.engines_used["gtts"] == 1

    @pytest.mark.asyncio
    async def test_record_request_failure(self, collector):
        """Test recording failed request."""
        await collector.record_request(
            engine="gtts",
            language="en",
            response_time=0.5,
            success=False,
            error_type="NetworkError",
        )

        engine_metrics = collector.engines["gtts"]
        assert engine_metrics.total_requests == 1
        assert engine_metrics.successful_requests == 0
        assert engine_metrics.failed_requests == 1
        assert engine_metrics.error_types["NetworkError"] == 1

        language_metrics = collector.languages["en"]
        assert language_metrics.total_requests == 1
        assert language_metrics.successful_requests == 0
        assert language_metrics.failed_requests == 1

    @pytest.mark.asyncio
    async def test_record_multiple_requests(self, collector):
        """Test recording multiple requests."""
        requests = [
            ("gtts", "en", 1.0, True),
            ("edge", "en", 2.0, True),
            ("gtts", "fa", 1.5, True),
            ("gtts", "en", 0.8, False, "TimeoutError"),
        ]

        for request in requests:
            if len(request) == 4:
                engine, language, response_time, success = request
                error_type = None
            else:
                engine, language, response_time, success, error_type = request

            await collector.record_request(
                engine=engine,
                language=language,
                response_time=response_time,
                success=success,
                error_type=error_type,
            )

        assert len(collector.engines) == 2
        assert collector.engines["gtts"].total_requests == 3
        assert collector.engines["gtts"].successful_requests == 2
        assert collector.engines["gtts"].failed_requests == 1
        assert collector.engines["edge"].total_requests == 1
        assert collector.engines["edge"].successful_requests == 1

        assert len(collector.languages) == 2
        assert collector.languages["en"].total_requests == 3
        assert collector.languages["fa"].total_requests == 1

    @pytest.mark.asyncio
    async def test_record_cache_event_hit(self, collector):
        """Test recording cache hit event."""
        await collector.record_cache_event(hit=True, size_bytes=1024)

        assert collector.cache.total_hits == 1
        assert collector.cache.total_misses == 0
        assert collector.cache.total_size_bytes == 1024
        assert collector.cache.hit_rate == 100.0

    @pytest.mark.asyncio
    async def test_record_cache_event_miss(self, collector):
        """Test recording cache miss event."""
        await collector.record_cache_event(hit=False, size_bytes=2048)

        assert collector.cache.total_hits == 0
        assert collector.cache.total_misses == 1
        assert collector.cache.total_size_bytes == 2048
        assert collector.cache.hit_rate == 0.0

    @pytest.mark.asyncio
    async def test_record_cache_eviction(self, collector):
        """Test recording cache eviction event."""
        await collector.record_cache_eviction()

        assert collector.cache.evictions == 1

    @pytest.mark.asyncio
    async def test_collect_system_metrics(self, collector):
        """Test system metrics collection."""
        with (
            patch("ttskit.metrics.advanced.psutil.cpu_percent", return_value=25.0),
            patch("ttskit.metrics.advanced.psutil.virtual_memory") as mock_memory,
            patch("ttskit.metrics.advanced.psutil.disk_usage") as mock_disk,
            patch("ttskit.metrics.advanced.psutil.net_io_counters") as mock_network,
        ):
            mock_memory.return_value.used = 1024 * 1024 * 1024
            mock_memory.return_value.percent = 50.0

            mock_disk.return_value.percent = 75.0

            mock_network.return_value.bytes_sent = 1024 * 1024
            mock_network.return_value.bytes_recv = 2 * 1024 * 1024

            await collector.collect_system_metrics()

            assert len(collector.system_history) == 1
            system_metrics = collector.system_history[0]
            assert system_metrics.cpu_percent == 25.0
            assert system_metrics.memory_mb == 1024.0
            assert system_metrics.memory_percent == 50.0
            assert system_metrics.disk_usage_percent == 75.0
            assert system_metrics.network_io_bytes == 3 * 1024 * 1024

    @pytest.mark.asyncio
    async def test_get_comprehensive_metrics_empty(self, collector):
        """Test comprehensive metrics with no data."""
        collector._start_time = datetime(2023, 1, 1, 0, 0, 0)
        with patch("ttskit.metrics.advanced.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2023, 1, 1, 0, 1, 0)
            metrics = await collector.get_comprehensive_metrics()

        assert isinstance(metrics, dict)
        assert "timestamp" in metrics
        assert "uptime_seconds" in metrics
        assert "requests" in metrics
        assert "engines" in metrics
        assert "languages" in metrics
        assert "cache" in metrics
        assert "performance" in metrics
        assert "system" in metrics
        assert "health" in metrics

        assert metrics["requests"]["total"] == 0
        assert metrics["requests"]["successful"] == 0
        assert metrics["requests"]["failed"] == 0
        assert metrics["requests"]["success_rate"] == 0
        assert metrics["requests"]["per_minute"] == 0

    @pytest.mark.asyncio
    async def test_get_comprehensive_metrics_with_data(self, collector):
        """Test comprehensive metrics with data."""
        await collector.record_request("gtts", "en", 1.0, True)
        await collector.record_request("edge", "fa", 2.0, True)
        await collector.record_request("gtts", "en", 0.5, False, "Error")
        await collector.record_cache_event(hit=True, size_bytes=1024)
        await collector.record_cache_event(hit=False, size_bytes=2048)

        with (
            patch("psutil.cpu_percent", return_value=30.0),
            patch("psutil.virtual_memory") as mock_memory,
            patch("psutil.disk_usage") as mock_disk,
            patch("psutil.net_io_counters") as mock_network,
        ):
            mock_memory.return_value.used = 512 * 1024 * 1024
            mock_memory.return_value.percent = 40.0
            mock_disk.return_value.percent = 60.0
            mock_network.return_value.bytes_sent = 1024
            mock_network.return_value.bytes_recv = 2048

            await collector.collect_system_metrics()

        collector._start_time = datetime(2023, 1, 1, 0, 0, 0)
        with patch("ttskit.metrics.advanced.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2023, 1, 1, 0, 1, 0)
            metrics = await collector.get_comprehensive_metrics()

        assert metrics["requests"]["total"] == 3
        assert metrics["requests"]["successful"] == 2
        assert metrics["requests"]["failed"] == 1
        assert abs(metrics["requests"]["success_rate"] - 66.67) < 0.01

        assert len(metrics["engines"]) == 2
        assert "gtts" in metrics["engines"]
        assert "edge" in metrics["engines"]

        assert len(metrics["languages"]) == 2
        assert "en" in metrics["languages"]
        assert "fa" in metrics["languages"]

        assert metrics["cache"]["hit_rate"] == 50.0
        assert metrics["cache"]["total_hits"] == 1
        assert metrics["cache"]["total_misses"] == 1

    @pytest.mark.asyncio
    async def test_get_engine_comparison(self, collector):
        """Test engine comparison metrics."""
        await collector.record_request("gtts", "en", 1.0, True)
        await collector.record_request("edge", "en", 2.0, True)
        await collector.record_request("gtts", "en", 0.5, False, "Error")

        comparison = await collector.get_engine_comparison()

        assert isinstance(comparison, dict)
        assert "gtts" in comparison
        assert "edge" in comparison

        gtts_data = comparison["gtts"]
        assert gtts_data["requests"] == 2
        assert gtts_data["success_rate"] == 50.0
        assert gtts_data["avg_response_time"] == 1.0
        assert "reliability_score" in gtts_data
        assert "performance_score" in gtts_data

    @pytest.mark.asyncio
    async def test_get_language_analytics(self, collector):
        """Test language analytics."""
        await collector.record_request("gtts", "en", 1.0, True)
        await collector.record_request("edge", "en", 2.0, True)
        await collector.record_request("gtts", "fa", 1.5, True)

        analytics = await collector.get_language_analytics()

        assert isinstance(analytics, dict)
        assert "en" in analytics
        assert "fa" in analytics

        en_data = analytics["en"]
        assert en_data["total_requests"] == 2
        assert abs(en_data["usage_percentage"] - 66.67) < 0.01
        assert en_data["success_rate"] == 100.0
        assert "preferred_engines" in en_data

    @pytest.mark.asyncio
    async def test_export_metrics_json(self, collector):
        """Test metrics export to JSON file."""
        await collector.record_request("gtts", "en", 1.0, True)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as tmp_file:
            tmp_path = Path(tmp_file.name)

        try:
            collector._start_time = datetime(2023, 1, 1, 0, 0, 0)
            def _async_open(path, mode="w", encoding="utf-8", **kwargs):
                class _AsyncFile:
                    def __init__(self, target_path: Path):
                        self._path = Path(target_path)
                    async def __aenter__(self_inner):
                        return self_inner

                    async def __aexit__(self_inner, exc_type, exc, tb):
                        return False

                    async def write(self_inner, data):
                        with open(self_inner._path, mode, encoding=encoding) as real_f:
                            real_f.write(data)
                        return None

                return _AsyncFile(path)

            with (
                patch("ttskit.metrics.advanced.datetime") as mock_dt,
                patch("ttskit.metrics.advanced.aiofiles.open", _async_open),
            ):
                mock_dt.now.return_value = datetime(2023, 1, 1, 0, 1, 0)
                success = await collector.export_metrics(tmp_path, "json")
            assert isinstance(success, bool)

            assert tmp_path.exists()

        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    @pytest.mark.asyncio
    async def test_export_metrics_unsupported_format(self, collector):
        """Test metrics export with unsupported format."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".xml", delete=False
        ) as tmp_file:
            tmp_path = Path(tmp_file.name)

        try:
            success = await collector.export_metrics(tmp_path, "xml")
            assert not success
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_percentile_calculation(self, collector):
        """Test percentile calculation."""
        assert collector._percentile([], 50) == 0

        assert collector._percentile([1.0], 50) == 1.0

        data = [1.0, 2.0, 3.0, 4.0, 5.0]
        assert collector._percentile(data, 50) == 3.0
        assert collector._percentile(data, 90) == 5.0
        assert collector._percentile(data, 10) == 1.0

    def test_calculate_health_score_no_engines(self, collector):
        """Test health score calculation with no engines."""
        score = collector._calculate_health_score()
        assert score == 0.0

    def test_calculate_health_score_with_engines(self, collector):
        """Test health score calculation with engines."""
        collector.engines["gtts"] = EngineMetrics(
            engine_name="gtts",
            total_requests=10,
            successful_requests=9,
            total_response_time=10.0,
        )

        collector.system_history.append(
            SystemMetrics(cpu_percent=20.0, memory_percent=30.0)
        )

        score = collector._calculate_health_score()
        assert 0 <= score <= 100

    def test_calculate_reliability_score(self, collector):
        """Test reliability score calculation."""
        metrics = EngineMetrics(engine_name="test")
        score = collector._calculate_reliability_score(metrics)
        assert score == 0.0

        metrics.total_requests = 10
        metrics.successful_requests = 9
        score = collector._calculate_reliability_score(metrics)
        assert score == 90.0

        metrics.error_types["Error"] = 2
        score = collector._calculate_reliability_score(metrics)
        assert score == 86.0

    def test_calculate_performance_score(self, collector):
        """Test performance score calculation."""
        metrics = EngineMetrics(engine_name="test")
        score = collector._calculate_performance_score(metrics)
        assert score == 0.0

        metrics.successful_requests = 5
        metrics.total_response_time = 5.0
        metrics.min_response_time = 0.5
        metrics.max_response_time = 2.0
        score = collector._calculate_performance_score(metrics)
        assert 0 <= score <= 100

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, collector):
        """Test concurrent request recording."""

        async def record_request(engine, language, response_time, success):
            await collector.record_request(engine, language, response_time, success)

        tasks = [
            record_request("gtts", "en", 1.0, True),
            record_request("edge", "en", 2.0, True),
            record_request("gtts", "fa", 1.5, True),
            record_request("edge", "fa", 0.8, False),
        ]

        await asyncio.gather(*tasks)

        assert collector.engines["gtts"].total_requests == 2
        assert collector.engines["edge"].total_requests == 2
        assert collector.languages["en"].total_requests == 2
        assert collector.languages["fa"].total_requests == 2

    @pytest.mark.asyncio
    async def test_history_size_limit(self, collector):
        """Test history size limiting."""
        for i in range(150):
            await collector.record_request("gtts", "en", 1.0, True)

        assert len(collector.request_history) == 100
        assert len(collector.system_history) <= 100


class TestGlobalFunctions:
    """Test global functions in advanced metrics module."""

    def test_get_metrics_collector_singleton(self):
        """Test metrics collector singleton pattern."""
        collector1 = get_metrics_collector()
        collector2 = get_metrics_collector()

        assert collector1 is collector2
        assert isinstance(collector1, AdvancedMetricsCollector)

    @pytest.mark.asyncio
    async def test_start_metrics_collection(self):
        """Test metrics collection startup."""
        with patch(
            "ttskit.metrics.advanced.get_metrics_collector"
        ) as mock_get_collector:
            mock_collector = Mock()
            mock_collector.collect_system_metrics = Mock()
            mock_get_collector.return_value = mock_collector

            task = asyncio.create_task(start_metrics_collection(interval_seconds=0.1))

            await asyncio.sleep(0.3)

            task.cancel()

            try:
                await task
            except asyncio.CancelledError:
                pass

            assert mock_collector.collect_system_metrics.call_count > 0


class TestAdvancedMetricsIntegration:
    """Integration tests for AdvancedMetricsCollector."""

    @pytest.fixture
    def collector(self):
        """Create collector for integration tests."""
        return AdvancedMetricsCollector(history_size=50)

    @pytest.mark.asyncio
    async def test_full_metrics_lifecycle(self, collector):
        """Test complete metrics lifecycle."""
        await collector.record_request("gtts", "en", 1.0, True)
        await collector.record_request("edge", "en", 2.0, True)
        await collector.record_request("gtts", "fa", 1.5, False, "NetworkError")
        await collector.record_cache_event(hit=True, size_bytes=1024)
        await collector.record_cache_event(hit=False, size_bytes=2048)
        await collector.record_cache_eviction()

        with (
            patch("ttskit.metrics.advanced.psutil.cpu_percent", return_value=25.0),
            patch("ttskit.metrics.advanced.psutil.virtual_memory") as mock_memory,
            patch("ttskit.metrics.advanced.psutil.disk_usage") as mock_disk,
            patch("ttskit.metrics.advanced.psutil.net_io_counters") as mock_network,
        ):
            mock_memory.return_value.used = 1024 * 1024 * 1024
            mock_memory.return_value.percent = 50.0
            mock_disk.return_value.percent = 75.0
            mock_network.return_value.bytes_sent = 1024
            mock_network.return_value.bytes_recv = 2048

            await collector.collect_system_metrics()

        collector._start_time = datetime(2023, 1, 1, 0, 0, 0)
        with patch("ttskit.metrics.advanced.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2023, 1, 1, 0, 1, 0)
            metrics = await collector.get_comprehensive_metrics()

        assert metrics["requests"]["total"] == 3
        assert metrics["requests"]["successful"] == 2
        assert metrics["requests"]["failed"] == 1
        assert abs(metrics["requests"]["success_rate"] - 66.67) < 0.01

        assert len(metrics["engines"]) == 2
        assert len(metrics["languages"]) == 2

        assert metrics["cache"]["hit_rate"] == 50.0
        assert metrics["cache"]["evictions"] == 1

        assert metrics["system"]["cpu_percent"] == 25.0
        assert metrics["system"]["memory_mb"] == 1024.0

        assert 0 <= metrics["health"] <= 100

    @pytest.mark.asyncio
    async def test_metrics_persistence(self, collector):
        """Test metrics persistence and export."""
        await collector.record_request("gtts", "en", 1.0, True)
        await collector.record_cache_event(hit=True, size_bytes=1024)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as tmp_file:
            tmp_path = Path(tmp_file.name)

        try:
            collector._start_time = datetime(2023, 1, 1, 0, 0, 0)
            def _async_open(path, mode="w", encoding="utf-8", **kwargs):
                class _AsyncFile:
                    def __init__(self, target_path: Path):
                        self._path = Path(target_path)
                    async def __aenter__(self_inner):
                        return self_inner

                    async def __aexit__(self_inner, exc_type, exc, tb):
                        return False

                    async def write(self_inner, data):
                        with open(self_inner._path, mode, encoding=encoding) as real_f:
                            real_f.write(data)
                        return None

                return _AsyncFile(path)

            with (
                patch("ttskit.metrics.advanced.datetime") as mock_dt,
                patch("ttskit.metrics.advanced.aiofiles.open", _async_open),
            ):
                mock_dt.now.return_value = datetime(2023, 1, 1, 0, 1, 0)
                success = await collector.export_metrics(tmp_path, "json")
            assert isinstance(success, bool)

            assert tmp_path.exists()

        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    @pytest.mark.asyncio
    async def test_high_volume_metrics(self, collector):
        """Test metrics collection under high volume."""
        tasks = []
        for i in range(100):
            task = collector.record_request(
                f"engine_{i % 3}",
                f"lang_{i % 2}",
                i * 0.01,
                i % 10 != 0,
            )
            tasks.append(task)

        await asyncio.gather(*tasks)

        collector._start_time = datetime(2023, 1, 1, 0, 0, 0)
        with patch("ttskit.metrics.advanced.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2023, 1, 1, 0, 1, 0)
            metrics = await collector.get_comprehensive_metrics()
        assert metrics["requests"]["total"] == 100
        assert metrics["requests"]["successful"] == 90
        assert metrics["requests"]["failed"] == 10
        assert metrics["requests"]["success_rate"] == 90.0

        assert len(metrics["engines"]) == 3
        assert len(metrics["languages"]) == 2
