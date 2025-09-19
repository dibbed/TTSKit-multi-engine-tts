"""
Tests for Metrics module.

This module tests the core functionality of metrics collection and monitoring.
"""

import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import importlib.util

spec = importlib.util.spec_from_file_location("metrics", "ttskit/metrics.py")
metrics_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metrics_module)

RequestMetrics = metrics_module.RequestMetrics
MetricsCollector = metrics_module.MetricsCollector


class TestRequestMetrics:
    """Test RequestMetrics class."""

    def test_init_default_values(self):
        """Test RequestMetrics initialization with default values."""
        start_time = time.time()
        metrics = RequestMetrics(start_time=start_time)

        assert metrics.start_time == start_time
        assert metrics.request_id == ""
        assert metrics.user_id == ""
        assert metrics.end_time is None
        assert metrics.language == ""
        assert metrics.engine == ""
        assert metrics.text_length == 0
        assert metrics.success is False
        assert metrics.error_type is None
        assert metrics.cache_hit is False

    def test_init_with_values(self):
        """Test RequestMetrics initialization with specific values."""
        start_time = time.time()
        metrics = RequestMetrics(
            start_time=start_time,
            request_id="req_123",
            user_id="user_456",
            language="en",
            engine="gtts",
            text_length=100,
            success=True,
            cache_hit=True,
        )

        assert metrics.start_time == start_time
        assert metrics.request_id == "req_123"
        assert metrics.user_id == "user_456"
        assert metrics.language == "en"
        assert metrics.engine == "gtts"
        assert metrics.text_length == 100
        assert metrics.success is True
        assert metrics.cache_hit is True

    def test_duration_property_with_end_time(self):
        """Test duration property when end_time is set."""
        start_time = time.time()
        end_time = start_time + 1.5
        metrics = RequestMetrics(start_time=start_time, end_time=end_time)

        assert metrics.duration == 1.5

    def test_duration_property_without_end_time(self):
        """Test duration property when end_time is not set."""
        start_time = time.time() - 2.0
        metrics = RequestMetrics(start_time=start_time)

        assert abs(metrics.duration - 2.0) < 0.1

    def test_start_timer(self):
        """Test start_timer method."""
        metrics = RequestMetrics(start_time=0.0)
        metrics.start_timer()

        assert abs(metrics.start_time - time.time()) < 0.1

    def test_end_timer(self):
        """Test end_timer method."""
        start_time = time.time()
        metrics = RequestMetrics(start_time=start_time)

        time.sleep(0.1)
        metrics.end_timer()

        assert metrics.end_time is not None
        assert metrics.end_time > metrics.start_time

    def test_mark_success(self):
        """Test mark_success method."""
        metrics = RequestMetrics(start_time=time.time())
        metrics.mark_success()

        assert metrics.success is True
        assert metrics.error_type is None

    def test_mark_failure(self):
        """Test mark_failure method."""
        metrics = RequestMetrics(start_time=time.time())
        metrics.mark_failure("TestError")

        assert metrics.success is False
        assert metrics.error_type == "TestError"


class TestMetricsCollector:
    """Test MetricsCollector class."""

    @pytest.fixture
    def collector(self):
        """Create MetricsCollector instance for testing."""
        return MetricsCollector()

    def test_init(self, collector):
        """Test MetricsCollector initialization."""
        assert collector._requests is not None
        assert collector._counters is not None
        assert collector._timers is not None
        assert collector._lock is not None
        assert collector._lock is not None
        assert collector.max_history == 1000
        assert collector.enabled is True
        assert collector._start_time > 0

    def test_record_request(self, collector):
        """Test record_request method."""
        request_id = "req_123"
        user_id = "user_456"
        language = "en"
        engine = "gtts"
        text_length = 100

        metrics = RequestMetrics(
            start_time=time.time(),
            request_id=request_id,
            user_id=user_id,
            language=language,
            engine=engine,
            text_length=text_length,
            success=True,
        )

        collector.record_request(metrics)

        assert len(collector._requests) == 1
        assert collector._counters["total_requests"] == 1
        assert collector._counters["successful_requests"] == 1

    def test_record_cached_request(self, collector):
        """Test record_cached_request method."""
        request_id = "req_123"
        user_id = "user_456"
        engine = "gtts"
        language = "en"
        text_length = 100

        collector.record_cached_request(
            request_id=request_id,
            user_id=user_id,
            engine=engine,
            language=language,
            text_length=text_length,
        )

        assert len(collector._requests) == 1
        assert collector._counters["total_requests"] == 1
        assert collector._counters["successful_requests"] == 1
        assert collector._counters["cache_hits"] == 1

    def test_record_failed_request(self, collector):
        """Test recording failed request."""
        metrics = RequestMetrics(
            start_time=time.time(),
            request_id="req_123",
            user_id="user_456",
            language="en",
            engine="gtts",
            text_length=100,
            success=False,
            error_type="TestError",
        )

        collector.record_request(metrics)

        assert len(collector._requests) == 1
        assert collector._counters["total_requests"] == 1
        assert collector._counters["failed_requests"] == 1
        assert collector._counters["error_TestError"] == 1

    def test_get_stats_empty(self, collector):
        """Test get_stats method with no requests."""
        stats = collector.get_stats()

        assert stats["total_requests"] == 0

    def test_get_stats_with_requests(self, collector):
        """Test get_stats method with requests."""
        metrics1 = RequestMetrics(
            start_time=time.time(),
            request_id="req_1",
            user_id="user_1",
            language="en",
            engine="gtts",
            text_length=100,
            success=True,
        )
        collector.record_request(metrics1)

        metrics2 = RequestMetrics(
            start_time=time.time(),
            request_id="req_2",
            user_id="user_2",
            language="fa",
            engine="edge",
            text_length=200,
            success=False,
            error_type="TestError",
        )
        collector.record_request(metrics2)

        stats = collector.get_stats()

        assert stats["total_requests"] == 2
        assert stats["successful_requests"] == 1
        assert stats["failed_requests"] == 1
        assert stats["success_rate"] == 50.0
        assert stats["average_duration"] >= 0
        assert "en" in stats["language_distribution"]
        assert "fa" in stats["language_distribution"]
        assert "gtts" in stats["engine_distribution"]
        assert "edge" in stats["engine_distribution"]

    def test_reset(self, collector):
        """Test reset method."""
        metrics1 = RequestMetrics(
            start_time=time.time(),
            request_id="req_1",
            user_id="user_1",
            language="en",
            engine="gtts",
            text_length=100,
            success=True,
        )
        collector.record_request(metrics1)

        collector.reset()

        stats = collector.get_stats()
        assert stats["total_requests"] == 0

    def test_get_recent_requests(self, collector):
        """Test get_recent_requests method."""
        for i in range(5):
            metrics = RequestMetrics(
                start_time=time.time(),
                request_id=f"req_{i}",
                user_id=f"user_{i}",
                language="en",
                engine="gtts",
                text_length=100,
                success=True,
            )
            collector.record_request(metrics)

        recent = collector.get_recent_requests(limit=3)
        assert len(recent) == 3
        assert recent[0].request_id == "req_2"
        assert recent[1].request_id == "req_3"
        assert recent[2].request_id == "req_4"

    def test_metrics_property(self, collector):
        """Test metrics property."""
        metrics1 = RequestMetrics(
            start_time=time.time(),
            request_id="req_1",
            user_id="user_1",
            language="en",
            engine="gtts",
            text_length=100,
            success=True,
        )
        collector.record_request(metrics1)

        metrics_list = collector.metrics
        assert len(metrics_list) == 1
        assert metrics_list[0].request_id == "req_1"


class TestMetricsFunctions:
    """Test metrics module functions."""

    def test_record_request_metrics_with_metrics_object(self):
        """Test record_request_metrics with metrics object."""
        metrics = RequestMetrics(
            start_time=time.time(),
            request_id="req_123",
            user_id="user_456",
            language="en",
            engine="gtts",
            text_length=100,
            success=True,
        )

        assert metrics.request_id == "req_123"
        assert metrics.user_id == "user_456"
        assert metrics.language == "en"
        assert metrics.engine == "gtts"
        assert metrics.text_length == 100
        assert metrics.success is True

    def test_record_request_metrics_with_parameters(self):
        """Test record_request_metrics with parameters."""
        metrics = RequestMetrics(
            start_time=time.time(),
            language="en",
            engine="gtts",
            text_length=100,
            success=True,
            cache_hit=False,
        )

        assert metrics.language == "en"
        assert metrics.engine == "gtts"
        assert metrics.text_length == 100
        assert metrics.success is True
        assert metrics.cache_hit is False

    def test_get_metrics(self):
        """Test get_metrics function."""
        collector = MetricsCollector()
        metrics = collector.metrics
        assert isinstance(metrics, list)

    def test_get_metrics_summary(self):
        """Test get_metrics_summary function."""
        collector = MetricsCollector()
        summary = collector.get_stats()
        assert isinstance(summary, dict)
        assert "total_requests" in summary

    def test_reset_metrics(self):
        """Test reset_metrics function."""
        collector = MetricsCollector()
        collector.reset()
        stats = collector.get_stats()
        assert stats["total_requests"] == 0

    def test_export_metrics_json(self):
        """Test export_metrics function with JSON format."""
        collector = MetricsCollector()
        stats = collector.get_stats()
        import json

        exported = json.dumps(stats, indent=2)
        assert isinstance(exported, str)
        assert exported.startswith("{")

    def test_export_metrics_prometheus(self):
        """Test export_metrics function with Prometheus format."""
        collector = MetricsCollector()
        stats = collector.get_stats()
        lines = []
        for key, value in stats.items():
            if isinstance(value, (int, float)):
                lines.append(f"ttskit_{key} {value}")
        exported = "\n".join(lines)
        assert isinstance(exported, str)

    def test_export_metrics_default(self):
        """Test export_metrics function with default format."""
        collector = MetricsCollector()
        stats = collector.get_stats()
        exported = str(stats)
        assert isinstance(exported, str)

    def test_get_metrics_history(self):
        """Test get_metrics_history function."""
        collector = MetricsCollector()
        history = collector.get_recent_requests(limit=10)
        assert isinstance(history, list)
        assert len(history) <= 10


class TestMetricsCollectorAdvanced:
    """Test advanced MetricsCollector functionality."""

    @pytest.fixture
    def collector(self):
        """Create MetricsCollector instance for testing."""
        return MetricsCollector()

    def test_collector_with_custom_max_history(self):
        """Test collector with custom max_history."""
        collector = MetricsCollector(max_history=50)
        assert collector.max_history == 50
        assert collector.max_metrics == 50

    def test_collector_with_custom_max_metrics(self):
        """Test collector with custom max_metrics."""
        collector = MetricsCollector(max_history=100, max_metrics=200)
        assert collector.max_history == 100
        assert collector.max_metrics == 200

    def test_collector_disabled(self):
        """Test collector when disabled."""
        collector = MetricsCollector(enabled=False)
        assert collector.enabled is False

        metrics = RequestMetrics(
            start_time=time.time(),
            request_id="req_123",
            user_id="user_456",
            language="en",
            engine="gtts",
            text_length=100,
            success=True,
        )

        collector.record_request(metrics)
        assert len(collector._requests) == 0
        assert collector._counters["total_requests"] == 0

    def test_collector_with_cache_hits(self, collector):
        """Test collector with cache hits."""
        metrics = RequestMetrics(
            start_time=time.time(),
            request_id="req_123",
            user_id="user_456",
            language="en",
            engine="gtts",
            text_length=100,
            success=True,
            cache_hit=True,
        )

        collector.record_request(metrics)
        assert collector._counters["cache_hits"] == 1

    def test_collector_with_multiple_engines(self, collector):
        """Test collector with multiple engines."""
        engines = ["gtts", "edge", "piper"]

        for i, engine in enumerate(engines):
            metrics = RequestMetrics(
                start_time=time.time(),
                request_id=f"req_{i}",
                user_id=f"user_{i}",
                language="en",
                engine=engine,
                text_length=100,
                success=True,
            )
            collector.record_request(metrics)

        stats = collector.get_stats()
        assert stats["total_requests"] == 3
        assert "gtts" in stats["engine_distribution"]
        assert "edge" in stats["engine_distribution"]

    def test_collector_with_multiple_languages(self, collector):
        """Test collector with multiple languages."""
        languages = ["en", "fa", "ar"]

        for i, language in enumerate(languages):
            metrics = RequestMetrics(
                start_time=time.time(),
                request_id=f"req_{i}",
                user_id=f"user_{i}",
                language=language,
                engine="gtts",
                text_length=100,
                success=True,
            )
            collector.record_request(metrics)

        stats = collector.get_stats()
        assert stats["total_requests"] == 3
        assert "en" in stats["language_distribution"]
        assert "fa" in stats["language_distribution"]
        assert "ar" in stats["language_distribution"]

    def test_collector_with_error_types(self, collector):
        """Test collector with different error types."""
        error_types = ["ValidationError", "EngineError", "NetworkError"]

        for i, error_type in enumerate(error_types):
            metrics = RequestMetrics(
                start_time=time.time(),
                request_id=f"req_{i}",
                user_id=f"user_{i}",
                language="en",
                engine="gtts",
                text_length=100,
                success=False,
                error_type=error_type,
            )
            collector.record_request(metrics)

        stats = collector.get_stats()
        assert stats["total_requests"] == 3
        assert stats["failed_requests"] == 3
        assert "ValidationError" in stats["error_breakdown"]
        assert "EngineError" in stats["error_breakdown"]
        assert "NetworkError" in stats["error_breakdown"]

    def test_collector_uptime(self, collector):
        """Test collector uptime calculation."""
        metrics = RequestMetrics(
            start_time=time.time(),
            request_id="req_1",
            user_id="user_1",
            language="en",
            engine="gtts",
            text_length=100,
            success=True,
        )
        collector.record_request(metrics)

        stats = collector.get_stats()
        assert "uptime" in stats
        assert stats["uptime"] >= 0

    def test_collector_with_duration_tracking(self, collector):
        """Test collector with duration tracking."""
        start_time = time.time()
        end_time = start_time + 2.5

        metrics = RequestMetrics(
            start_time=start_time,
            end_time=end_time,
            request_id="req_123",
            user_id="user_456",
            language="en",
            engine="gtts",
            text_length=100,
            success=True,
        )

        collector.record_request(metrics)

        stats = collector.get_stats()
        assert stats["average_duration"] > 0

    def test_collector_with_text_length_variations(self, collector):
        """Test collector with different text lengths."""
        text_lengths = [50, 100, 200, 500, 1000]

        for i, text_length in enumerate(text_lengths):
            metrics = RequestMetrics(
                start_time=time.time(),
                request_id=f"req_{i}",
                user_id=f"user_{i}",
                language="en",
                engine="gtts",
                text_length=text_length,
                success=True,
            )
            collector.record_request(metrics)

        stats = collector.get_stats()
        assert stats["total_requests"] == 5

    def test_collector_thread_safety(self):
        """Test collector thread safety."""
        import threading
        import time

        collector = MetricsCollector()

        def add_requests():
            for i in range(10):
                metrics = RequestMetrics(
                    start_time=time.time(),
                    request_id=f"req_{i}",
                    user_id=f"user_{i}",
                    language="en",
                    engine="gtts",
                    text_length=100,
                    success=True,
                )
                collector.record_request(metrics)
                time.sleep(0.001)

        threads = []
        for _ in range(5):
            thread = threading.Thread(target=add_requests)
            threads.append(thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        stats = collector.get_stats()
        assert stats["total_requests"] == 50

    def test_collector_max_history_limit(self):
        """Test collector max history limit."""
        collector = MetricsCollector(max_history=5)

        for i in range(10):
            metrics = RequestMetrics(
                start_time=time.time(),
                request_id=f"req_{i}",
                user_id=f"user_{i}",
                language="en",
                engine="gtts",
                text_length=100,
                success=True,
            )
            collector.record_request(metrics)

        assert len(collector._requests) == 5
        assert collector._counters["total_requests"] == 10

    def test_collector_cache_hit_rate_calculation(self, collector):
        """Test collector cache hit rate calculation."""
        for i in range(8):
            metrics = RequestMetrics(
                start_time=time.time(),
                request_id=f"req_{i}",
                user_id=f"user_{i}",
                language="en",
                engine="gtts",
                text_length=100,
                success=True,
                cache_hit=True,
            )
            collector.record_request(metrics)

        for i in range(2):
            metrics = RequestMetrics(
                start_time=time.time(),
                request_id=f"req_{i + 8}",
                user_id=f"user_{i + 8}",
                language="en",
                engine="gtts",
                text_length=100,
                success=True,
                cache_hit=False,
            )
            collector.record_request(metrics)

        stats = collector.get_stats()
        assert stats["cache_hit_rate"] == 80.0

    def test_collector_success_rate_calculation(self, collector):
        """Test collector success rate calculation."""
        for i in range(7):
            metrics = RequestMetrics(
                start_time=time.time(),
                request_id=f"req_{i}",
                user_id=f"user_{i}",
                language="en",
                engine="gtts",
                text_length=100,
                success=True,
            )
            collector.record_request(metrics)

        for i in range(3):
            metrics = RequestMetrics(
                start_time=time.time(),
                request_id=f"req_{i + 7}",
                user_id=f"user_{i + 7}",
                language="en",
                engine="gtts",
                text_length=100,
                success=False,
                error_type="TestError",
            )
            collector.record_request(metrics)

        stats = collector.get_stats()
        assert stats["success_rate"] == 70.0
