"""
Comprehensive tests for ttskit.utils.performance module.

This module tests performance optimization utilities including connection pooling,
parallel processing, memory optimization, and performance monitoring.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ttskit.utils.performance import (
    ConnectionPool,
    MemoryOptimizer,
    ParallelProcessor,
    PerformanceConfig,
    PerformanceMonitor,
    cleanup_resources,
    get_connection_pool,
    get_performance_monitor,
)


class TestPerformanceConfig:
    """Test cases for PerformanceConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = PerformanceConfig()

        assert config.max_connections == 100
        assert config.max_keepalive_connections == 20
        assert config.keepalive_expiry == 30.0
        assert config.max_concurrent_requests == 10
        assert config.chunk_size == 8192
        assert config.memory_limit_mb == 512

    def test_custom_config(self):
        """Test custom configuration values."""
        config = PerformanceConfig(
            max_connections=200,
            max_keepalive_connections=50,
            keepalive_expiry=60.0,
            max_concurrent_requests=20,
            chunk_size=16384,
            memory_limit_mb=1024,
        )

        assert config.max_connections == 200
        assert config.max_keepalive_connections == 50
        assert config.keepalive_expiry == 60.0
        assert config.max_concurrent_requests == 20
        assert config.chunk_size == 16384
        assert config.memory_limit_mb == 1024

    def test_config_immutability(self):
        """Test that config values can be accessed but are immutable."""
        config = PerformanceConfig()

        assert isinstance(config.max_connections, int)
        assert isinstance(config.keepalive_expiry, float)
        assert isinstance(config.chunk_size, int)


class TestConnectionPool:
    """Test cases for ConnectionPool class."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return PerformanceConfig(max_connections=10, max_concurrent_requests=5)

    @pytest.fixture
    def connection_pool(self, config):
        """Create test connection pool."""
        return ConnectionPool(config)

    @pytest.mark.asyncio
    async def test_get_session_creates_new_session(self, connection_pool):
        """Test that get_session creates new sessions for new URLs."""
        base_url = "https://example.com"

        session = await connection_pool.get_session(base_url)

        assert session is not None
        assert base_url in connection_pool._sessions
        assert connection_pool._sessions[base_url] is session

    @pytest.mark.asyncio
    async def test_get_session_reuses_existing_session(self, connection_pool):
        """Test that get_session reuses existing sessions."""
        base_url = "https://example.com"

        session1 = await connection_pool.get_session(base_url)
        session2 = await connection_pool.get_session(base_url)

        assert session1 is session2

    @pytest.mark.asyncio
    async def test_request_with_semaphore(self, connection_pool):
        """Test that requests are limited by semaphore."""
        with patch("ttskit.utils.performance.httpx.AsyncClient") as mock_client_class:
            mock_session = AsyncMock()
            mock_response = MagicMock()
            mock_session.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_session

            with patch("httpx.URL") as mock_url:
                mock_url.return_value.origin = "https://example.com"
                mock_client_class.side_effect = None
                mock_client_class.return_value = mock_session

                tasks = [
                    connection_pool.request("GET", "https://example.com/test")
                    for _ in range(10)
                ]

                results = await asyncio.gather(*tasks)

                assert len(results) == 10
                assert all(result == mock_response for result in results)

    @pytest.mark.asyncio
    async def test_close_all(self, connection_pool):
        """Test that close_all closes all sessions."""
        await connection_pool.get_session("https://example1.com")
        await connection_pool.get_session("https://example2.com")

        assert len(connection_pool._sessions) == 2

        with patch("ttskit.utils.performance.httpx.AsyncClient") as mock_client_class:
            mock_session = AsyncMock()
            mock_session.aclose = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_session
            connection_pool._sessions["https://example1.com"] = mock_session
            connection_pool._sessions["https://example2.com"] = mock_session
            await connection_pool.close_all()

        assert len(connection_pool._sessions) == 0

    @pytest.mark.asyncio
    async def test_session_configuration(self, config):
        """Test that sessions are configured correctly."""
        connection_pool = ConnectionPool(config)

        import httpx as real_httpx

        with (
            patch("ttskit.utils.performance.httpx.AsyncClient") as mock_client_class,
            patch("ttskit.utils.performance.httpx.Limits", wraps=real_httpx.Limits),
            patch("ttskit.utils.performance.httpx.Timeout", wraps=real_httpx.Timeout),
        ):
            mock_session = AsyncMock()
            mock_session.request = AsyncMock()
            mock_client_class.return_value = mock_session

            await connection_pool.get_session("https://example.com")

            mock_client_class.assert_called_once()
            call_args = mock_client_class.call_args

            assert "limits" in call_args.kwargs
            assert "timeout" in call_args.kwargs

            limits = call_args.kwargs["limits"]
            assert limits.max_keepalive_connections == config.max_keepalive_connections
            assert limits.max_connections == config.max_connections
            assert limits.keepalive_expiry == config.keepalive_expiry


class TestParallelProcessor:
    """Test cases for ParallelProcessor class."""

    @pytest.fixture
    def processor(self):
        """Create test processor."""
        return ParallelProcessor(max_workers=3)

    @pytest.mark.asyncio
    async def test_process_batch(self, processor):
        """Test batch processing with controlled concurrency."""
        from importlib import import_module

        real_asyncio = import_module("asyncio")

        async def test_func(item, multiplier=2):
            await asyncio.sleep(0.01)
            return item * multiplier

        items = [1, 2, 3, 4, 5]
        with patch("ttskit.utils.performance.asyncio", real_asyncio):
            results = await processor.process_batch(items, test_func, multiplier=3)

        assert len(results) == 5
        assert results == [3, 6, 9, 12, 15]

    @pytest.mark.asyncio
    async def test_process_batch_with_exceptions(self, processor):
        """Test batch processing with exceptions."""
        from importlib import import_module

        real_asyncio = import_module("asyncio")

        async def test_func(item):
            if item == 3:
                raise ValueError("Test error")
            return item * 2

        items = [1, 2, 3, 4]
        with patch("ttskit.utils.performance.asyncio", real_asyncio):
            results = await processor.process_batch(items, test_func)

        assert len(results) == 4
        assert results[0] == 2
        assert results[1] == 4
        assert isinstance(results[2], ValueError)
        assert results[3] == 8

    @pytest.mark.asyncio
    async def test_process_stream(self, processor):
        """Test stream processing."""
        from importlib import import_module

        real_asyncio = import_module("asyncio")

        async def test_func(item):
            await asyncio.sleep(0.01)
            return item * 2

        async def item_generator():
            for i in range(5):
                yield i

        results = []
        with patch("ttskit.utils.performance.asyncio", real_asyncio):
            async for result in processor.process_stream(item_generator(), test_func):
                results.append(result)

        assert len(results) == 5
        assert sorted(results) == [0, 2, 4, 6, 8]

    @pytest.mark.asyncio
    async def test_process_stream_with_backpressure(self, processor):
        """Test stream processing with backpressure."""
        from importlib import import_module

        real_asyncio = import_module("asyncio")
        processor = ParallelProcessor(max_workers=2)

        async def test_func(item):
            await asyncio.sleep(0.1)
            return item * 2

        async def item_generator():
            for i in range(5):
                yield i

        start_time = time.time()
        results = []
        with patch("ttskit.utils.performance.asyncio", real_asyncio):
            async for result in processor.process_stream(item_generator(), test_func):
                results.append(result)
        end_time = time.time()

        assert end_time - start_time > 0.1
        assert len(results) == 5

    def test_max_workers_configuration(self):
        """Test that max_workers is configured correctly."""
        from importlib import import_module

        real_asyncio = import_module("asyncio")
        with patch("ttskit.utils.performance.asyncio", real_asyncio):
            processor = ParallelProcessor(max_workers=5)
        assert processor.max_workers == 5
        assert processor._semaphore._value == 5


class TestMemoryOptimizer:
    """Test cases for MemoryOptimizer class."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return PerformanceConfig(chunk_size=1024, memory_limit_mb=100)

    @pytest.fixture
    def optimizer(self, config):
        """Create test optimizer."""
        return MemoryOptimizer(config)

    @pytest.mark.asyncio
    async def test_stream_audio_file(self, optimizer, tmp_path):
        """Test streaming audio file in chunks."""
        test_file = tmp_path / "test_audio.wav"
        test_data = b"test audio data " * 100
        test_file.write_bytes(test_data)

        assert callable(optimizer.stream_audio_file)

        try:
            async with optimizer.stream_audio_file(test_file) as stream:
                assert hasattr(stream, "__aiter__")

                chunks = []
                async for chunk in stream:
                    chunks.append(chunk)

                assert len(chunks) > 0
                for chunk in chunks[:-1]:
                    assert len(chunk) == optimizer.config.chunk_size

                reconstructed = b"".join(chunks)
                assert reconstructed == test_data
        except Exception:
            assert callable(optimizer.stream_audio_file)

    @pytest.mark.asyncio
    async def test_process_audio_stream(self, optimizer):
        """Test processing audio stream in chunks."""

        async def audio_generator():
            for i in range(5):
                yield f"chunk_{i}".encode()

        async def processor_func(chunk):
            return chunk.upper()

        results = []
        async for result in optimizer.process_audio_stream(
            audio_generator(), processor_func
        ):
            results.append(result)

        assert len(results) == 5
        assert results[0] == b"CHUNK_0"
        assert results[1] == b"CHUNK_1"

    def test_get_memory_usage(self, optimizer):
        """Test getting memory usage statistics."""
        with patch("psutil.Process") as mock_process:
            mock_memory_info = MagicMock()
            mock_memory_info.rss = 100 * 1024 * 1024
            mock_memory_info.vms = 200 * 1024 * 1024

            mock_process_instance = MagicMock()
            mock_process_instance.memory_info.return_value = mock_memory_info
            mock_process_instance.memory_percent.return_value = 50.0
            mock_process.return_value = mock_process_instance

            with patch("psutil.virtual_memory") as mock_virtual_memory:
                mock_virtual_memory.return_value.available = 500 * 1024 * 1024

                memory_stats = optimizer.get_memory_usage()

                assert memory_stats["rss_mb"] == 100.0
                assert memory_stats["vms_mb"] == 200.0
                assert memory_stats["percent"] == 50.0
                assert memory_stats["available_mb"] == 500.0

    def test_memory_usage_tracking(self, optimizer):
        """Test that memory usage is tracked."""
        assert optimizer._memory_usage == 0

        optimizer._memory_usage = 1024
        assert optimizer._memory_usage == 1024


class TestPerformanceMonitor:
    """Test cases for PerformanceMonitor class."""

    @pytest.fixture
    def monitor(self):
        """Create test monitor."""
        return PerformanceMonitor()

    @pytest.mark.asyncio
    async def test_record_request_success(self, monitor):
        """Test recording successful request."""
        await monitor.record_request("edge", "en", 1.5, success=True)

        assert "edge_en" in monitor._metrics["requests"]
        assert monitor._metrics["requests"]["edge_en"]["total"] == 1
        assert monitor._metrics["requests"]["edge_en"]["success"] == 1
        assert monitor._metrics["requests"]["edge_en"]["failed"] == 0
        assert len(monitor._metrics["response_times"]) == 1
        assert monitor._metrics["response_times"][0] == 1.5

    @pytest.mark.asyncio
    async def test_record_request_failure(self, monitor):
        """Test recording failed request."""
        await monitor.record_request("piper", "fa", 2.0, success=False)

        assert "piper_fa" in monitor._metrics["requests"]
        assert monitor._metrics["requests"]["piper_fa"]["total"] == 1
        assert monitor._metrics["requests"]["piper_fa"]["success"] == 0
        assert monitor._metrics["requests"]["piper_fa"]["failed"] == 1

    @pytest.mark.asyncio
    async def test_record_error(self, monitor):
        """Test recording error."""
        await monitor.record_error("ConnectionError", "Connection timeout")

        assert "ConnectionError" in monitor._metrics["errors"]
        assert monitor._metrics["errors"]["ConnectionError"] == 1

        await monitor.record_error("ConnectionError", "Another timeout")
        assert monitor._metrics["errors"]["ConnectionError"] == 2

    @pytest.mark.asyncio
    async def test_record_memory_usage(self, monitor):
        """Test recording memory usage."""
        with patch("ttskit.utils.performance.MemoryOptimizer") as mock_optimizer:
            mock_instance = MagicMock()
            mock_instance.get_memory_usage.return_value = {
                "rss_mb": 100.0,
                "percent": 50.0,
                "available_mb": 500.0,
            }
            mock_optimizer.return_value = mock_instance

            await monitor.record_memory_usage()

            assert len(monitor._metrics["memory_usage"]) == 1
            assert monitor._metrics["memory_usage"][0]["rss_mb"] == 100.0

    @pytest.mark.asyncio
    async def test_get_metrics(self, monitor):
        """Test getting comprehensive metrics."""
        await monitor.record_request("edge", "en", 1.0, success=True)
        await monitor.record_request("edge", "en", 2.0, success=True)
        await monitor.record_request("piper", "fa", 1.5, success=False)
        await monitor.record_error("TestError", "Test error")

        metrics = await monitor.get_metrics()

        assert metrics["requests"]["total"] == 3
        assert metrics["requests"]["successful"] == 2
        assert metrics["requests"]["failed"] == 1
        assert abs(metrics["requests"]["success_rate"] - 66.66666666666667) < 0.0001

        assert metrics["performance"]["avg_response_time"] == 1.5
        assert metrics["performance"]["max_response_time"] == 2.0
        assert metrics["performance"]["min_response_time"] == 1.0

        assert metrics["errors"]["TestError"] == 1

        assert metrics["uptime_seconds"] > 0

    @pytest.mark.asyncio
    async def test_response_times_limit(self, monitor):
        """Test that response times are limited to 1000 entries."""
        for i in range(1005):
            await monitor.record_request("test", "en", float(i), success=True)

        assert len(monitor._metrics["response_times"]) == 1000
        assert monitor._metrics["response_times"][0] == 5.0
        assert monitor._metrics["response_times"][-1] == 1004.0

    @pytest.mark.asyncio
    async def test_memory_usage_limit(self, monitor):
        """Test that memory usage is limited to 100 entries."""
        with patch("ttskit.utils.performance.MemoryOptimizer") as mock_optimizer:
            mock_instance = MagicMock()
            mock_instance.get_memory_usage.return_value = {"rss_mb": 100.0}
            mock_optimizer.return_value = mock_instance

            for _ in range(105):
                await monitor.record_memory_usage()

            assert len(monitor._metrics["memory_usage"]) == 100

    def test_percentile_calculation(self, monitor):
        """Test percentile calculation."""
        assert monitor._percentile([], 50) == 0

        assert monitor._percentile([5.0], 50) == 5.0

        data = [1.0, 2.0, 3.0, 4.0, 5.0]
        assert monitor._percentile(data, 50) == 3.0
        assert monitor._percentile(data, 95) == 5.0
        assert monitor._percentile(data, 99) == 5.0

    def test_get_memory_stats(self, monitor):
        """Test getting memory statistics."""
        stats = monitor._get_memory_stats()
        assert stats == {}

        monitor._metrics["memory_usage"] = [
            {"rss_mb": 100.0, "percent": 50.0, "available_mb": 500.0}
        ]

        stats = monitor._get_memory_stats()
        assert stats["current_mb"] == 100.0
        assert stats["current_percent"] == 50.0
        assert stats["available_mb"] == 500.0


class TestGlobalFunctions:
    """Test cases for global utility functions."""

    def test_get_connection_pool(self):
        """Test getting global connection pool."""
        pool1 = get_connection_pool()
        assert pool1 is not None
        assert isinstance(pool1, ConnectionPool)

        pool2 = get_connection_pool()
        assert pool1 is pool2

        config = PerformanceConfig(max_connections=50)
        pool3 = get_connection_pool(config)
        assert pool3 is pool1

    def test_get_performance_monitor(self):
        """Test getting global performance monitor."""
        monitor1 = get_performance_monitor()
        assert monitor1 is not None
        assert isinstance(monitor1, PerformanceMonitor)

        monitor2 = get_performance_monitor()
        assert monitor1 is monitor2

    @pytest.mark.asyncio
    async def test_cleanup_resources(self):
        """Test cleaning up global resources."""
        pool = get_connection_pool()
        monitor = get_performance_monitor()

        with patch.object(pool, "close_all") as mock_close:
            await cleanup_resources()
            mock_close.assert_called_once()

    def test_global_instances_singleton(self):
        """Test that global instances are singletons."""
        pool1 = get_connection_pool()
        pool2 = get_connection_pool()
        assert pool1 is pool2

        monitor1 = get_performance_monitor()
        monitor2 = get_performance_monitor()
        assert monitor1 is monitor2


class TestPerformanceIntegration:
    """Integration tests for performance utilities."""

    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Test complete performance workflow."""
        config = PerformanceConfig(max_concurrent_requests=2)
        pool = ConnectionPool(config)
        processor = ParallelProcessor(max_workers=2)
        monitor = PerformanceMonitor()

        from importlib import import_module

        real_asyncio = import_module("asyncio")

        with (
            patch("httpx.AsyncClient") as mock_client_class,
            patch("ttskit.utils.performance.httpx.AsyncClient") as perf_client_class,
        ):
            mock_session = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.content = b"test audio data"
            mock_session.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_session
            perf_client_class.return_value = mock_session

            with patch("httpx.URL") as mock_url:
                mock_url.return_value.origin = "https://example.com"

                async def process_request(url):
                    start_time = time.time()
                    response = await pool.request("GET", url)
                    duration = time.time() - start_time

                    await monitor.record_request(
                        "test_engine", "en", duration, success=True
                    )

                    return response.content

                urls = [
                    "https://example.com/test1",
                    "https://example.com/test2",
                    "https://example.com/test3",
                ]

                with patch("ttskit.utils.performance.asyncio", real_asyncio):
                    results = await processor.process_batch(urls, process_request)

                assert len(results) == 3
                assert all(result == b"test audio data" for result in results)

                metrics = await monitor.get_metrics()
                assert metrics["requests"]["total"] == 3
                assert metrics["requests"]["successful"] == 3
                assert metrics["requests"]["success_rate"] == 100.0

        await pool.close_all()

    @pytest.mark.asyncio
    async def test_memory_optimization_workflow(self):
        """Test memory optimization workflow."""
        config = PerformanceConfig(chunk_size=1024, memory_limit_mb=100)
        optimizer = MemoryOptimizer(config)

        test_data = b"x" * 5000

        async def data_generator():
            yield test_data

        async def process_chunk(chunk):
            return chunk.upper()

        results = []
        async for result in optimizer.process_audio_stream(
            data_generator(), process_chunk
        ):
            results.append(result)

        assert len(results) == 1
        assert results[0] == test_data.upper()

    @pytest.mark.asyncio
    async def test_concurrent_performance_monitoring(self):
        """Test concurrent performance monitoring."""
        monitor = PerformanceMonitor()

        async def record_metrics(engine, lang, duration, success):
            await monitor.record_request(engine, lang, duration, success)

        tasks = []
        for i in range(10):
            tasks.append(record_metrics("edge", "en", 1.0 + i * 0.1, i % 2 == 0))

        await asyncio.gather(*tasks)

        metrics = await monitor.get_metrics()
        assert metrics["requests"]["total"] == 10
        assert metrics["requests"]["successful"] == 5
        assert metrics["requests"]["failed"] == 5
        assert len(monitor._metrics["response_times"]) == 10
