"""
Performance optimization utilities for TTSKit.

This module offers tools for efficient HTTP connection pooling, parallel batch/stream processing,
memory-efficient audio streaming, and real-time performance monitoring. Designed for
high-scale TTS applications with async support and resource management.
"""

import asyncio
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import aiofiles
import httpx


@dataclass
class PerformanceConfig:
    """Dataclass holding configuration values for performance features.

    Defaults are tuned for typical TTS workloads: moderate concurrency,
    efficient keepalives, and memory limits to prevent OOM.

    Attributes:
        max_connections: Total HTTP connections allowed (int, default 100).
        max_keepalive_connections: Persistent connections (int, default 20).
        keepalive_expiry: Seconds before keepalive timeout (float, default 30.0).
        max_concurrent_requests: Semaphore limit for async requests (int, default 10).
        chunk_size: Bytes per read in streaming (int, default 8192).
        memory_limit_mb: Soft memory cap in MB (int, default 512).
    """
    max_connections: int = 100
    max_keepalive_connections: int = 20
    keepalive_expiry: float = 30.0
    max_concurrent_requests: int = 10
    chunk_size: int = 8192
    memory_limit_mb: int = 512


class ConnectionPool:
    """Async HTTP connection pool for TTS engine requests.

    Manages per-origin sessions with limits to optimize reuse and concurrency.
    Uses semaphore for max_concurrent_requests control.

    Attributes:
        config: PerformanceConfig instance (PerformanceConfig).
        _sessions: Dict of base_url to AsyncClient (dict).
        _semaphore: Limits concurrent requests (asyncio.Semaphore).
    """

    def __init__(self, config: PerformanceConfig):
        """Initialize pool with config for limits and timeouts.

        Args:
            config: Settings for connections/keepalives/semaphore (PerformanceConfig).
        """
        self.config = config
        self._sessions: dict[str, httpx.AsyncClient] = {}
        self._semaphore = asyncio.Semaphore(config.max_concurrent_requests)

    async def get_session(self, base_url: str) -> httpx.AsyncClient:
        """Retrieve or create an AsyncClient for the URL's origin.

        Args:
            base_url: Base URL for the engine (str).

        Returns:
            httpx.AsyncClient: Session with limits and 30s timeout.
        """
        if base_url not in self._sessions:
            self._sessions[base_url] = httpx.AsyncClient(
                limits=httpx.Limits(
                    max_keepalive_connections=self.config.max_keepalive_connections,
                    max_connections=self.config.max_connections,
                    keepalive_expiry=self.config.keepalive_expiry,
                ),
                timeout=httpx.Timeout(30.0),
            )
        return self._sessions[base_url]

    async def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Execute HTTP request using pooled session and semaphore.

        Args:
            method: HTTP method (str, e.g., 'GET').
            url: Request URL (str).
            **kwargs: Additional params for session.request (e.g., json, headers).

        Returns:
            httpx.Response: Server response.
        """
        async with self._semaphore:
            session = await self.get_session(str(httpx.URL(url).origin))
            return await session.request(method, url, **kwargs)

    async def close_all(self):
        """Close all open sessions and clear the pool."""
        for session in self._sessions.values():
            await session.aclose()
        self._sessions.clear()


class ParallelProcessor:
    """Async utilities for parallel batch and stream processing with concurrency limits.

    Uses semaphore to cap workers, enabling controlled parallelism for CPU/IO-bound tasks.

    Attributes:
        max_workers: Limit for semaphore (int, default 10).
        _semaphore: Controls concurrent executions (asyncio.Semaphore).
    """

    def __init__(self, max_workers: int = 10):
        """Initialize with concurrency limit.

        Args:
            max_workers: Maximum parallel tasks (int); defaults to 10.
        """
        self.max_workers = max_workers
        self._semaphore = asyncio.Semaphore(max_workers)

    async def process_batch(
        self, items: list[Any], processor_func: callable, *args, **kwargs
    ) -> list[Any]:
        """Process a list of items in parallel using gather.

        Creates tasks for each item, limited by semaphore in process_item.
        Returns results or exceptions via return_exceptions=True.

        Args:
            items: List of items to process (list[Any]).
            processor_func: Async callable to apply (callable).
            *args: Positional args for processor_func.
            **kwargs: Keyword args for processor_func.

        Returns:
            list[Any]: List of results (or Exception instances).
        """
        async def process_item(item):
            async with self._semaphore:
                return await processor_func(item, *args, **kwargs)

        tasks = [process_item(item) for item in items]
        return await asyncio.gather(*tasks, return_exceptions=True)

    async def process_stream(
        self,
        items: AsyncGenerator[Any, None],
        processor_func: callable,
        *args,
        **kwargs,
    ) -> AsyncGenerator[Any, None]:
        """Process streaming items in parallel, yielding as completed.

        Buffers up to max_workers tasks; waits on FIRST_COMPLETED when full,
        yields done results, continues with pending.

        Args:
            items: Async generator of items (AsyncGenerator[Any, None]).
            processor_func: Async callable (callable).
            *args: Positional args for processor_func.
            **kwargs: Keyword args for processor_func.

        Yields:
            Any: Processed item results sequentially as ready.
        """
        async def process_item(item):
            async with self._semaphore:
                return await processor_func(item, *args, **kwargs)

        tasks = []
        async for item in items:
            if len(tasks) >= self.max_workers:
                done, pending = await asyncio.wait(
                    tasks, return_when=asyncio.FIRST_COMPLETED
                )
                for task in done:
                    yield await task
                tasks = list(pending)

            tasks.append(asyncio.create_task(process_item(item)))

        for task in tasks:
            yield await task


class MemoryOptimizer:
    """Tools for low-memory audio processing and system monitoring.

    Provides chunked file streaming and stream processing to avoid loading large files fully.
    Tracks process memory via psutil.

    Attributes:
        config: Performance settings (PerformanceConfig).
        _memory_usage: Internal tracker (int, default 0; unused in current impl).
    """

    def __init__(self, config: PerformanceConfig):
        """Initialize with config for chunk sizes and limits.

        Args:
            config: PerformanceConfig for chunk_size and memory_limit_mb.
        """
        self.config = config
        self._memory_usage = 0

    @asynccontextmanager
    async def stream_audio_file(self, file_path: Path):
        """Async context manager to read audio file in configurable chunks.

        Yields bytes chunks sequentially to enable streaming without full load.

        Args:
            file_path: Path to audio file (Path).

        Yields:
            bytes: Next chunk of file data (up to chunk_size).

        Notes:
            Uses aiofiles.open for non-blocking reads.
            Continues until EOF (empty chunk).
        """
        async with aiofiles.open(file_path, "rb") as f:
            while True:
                chunk = await f.read(self.config.chunk_size)
                if not chunk:
                    break
                yield chunk

    async def process_audio_stream(
        self, audio_stream: AsyncGenerator[bytes, None], processor_func: callable
    ) -> AsyncGenerator[bytes, None]:
        """Apply processor to each chunk from an audio stream generator.

        Processes sequentially, yielding transformed chunks for pipeline use.

        Args:
            audio_stream: Generator of byte chunks (AsyncGenerator[bytes, None]).
            processor_func: Async callable taking bytes -> bytes (callable).

        Yields:
            bytes: Processed chunk.

        Notes:
            Assumes processor_func handles each chunk independently.
            No buffering beyond generator; memory-efficient for large streams.
        """
        async for chunk in audio_stream:
            processed_chunk = await processor_func(chunk)
            yield processed_chunk

    def get_memory_usage(self) -> dict[str, Any]:
        """Query current process and system memory stats via psutil.

        Returns:
            dict: Memory info with:
                - rss_mb: Resident set size in MB (float).
                - vms_mb: Virtual memory size in MB (float).
                - percent: Process % of total RAM (float).
                - available_mb: System available RAM in MB (float).
        """
        import psutil

        process = psutil.Process()
        memory_info = process.memory_info()

        return {
            "rss_mb": memory_info.rss / 1024 / 1024,
            "vms_mb": memory_info.vms / 1024 / 1024,
            "percent": process.memory_percent(),
            "available_mb": psutil.virtual_memory().available / 1024 / 1024,
        }


class PerformanceMonitor:
    """Real-time monitoring of requests, errors, response times, and memory.

    Tracks per-engine/language stats, percentiles, uptime, and recent memory snapshots.
    Thread-safe with asyncio.Lock for concurrent updates.

    Attributes:
        _metrics: Internal dict with requests, response_times, errors, memory_usage, start_time (dict).
        _lock: For async safe updates (asyncio.Lock).
    """

    def __init__(self):
        """Initialize metrics dict and lock; sets start_time to now."""
        self._metrics = {
            "requests": {},
            "response_times": [],
            "errors": {},
            "memory_usage": [],
            "start_time": time.time(),
        }
        self._lock = asyncio.Lock()

    async def record_request(
        self, engine: str, language: str, duration: float, success: bool = True
    ):
        """Log a synthesis request with engine, lang, time, and outcome.

        Updates per-key stats (total/success/failed) and appends duration.
        Caps response_times at 1000 recent entries.

        Args:
            engine: TTS engine used (str).
            language: Language code (str).
            duration: Response time in seconds (float).
            success: Whether request succeeded (bool, default True).
        """
        async with self._lock:
            key = f"{engine}_{language}"

            if key not in self._metrics["requests"]:
                self._metrics["requests"][key] = {"total": 0, "success": 0, "failed": 0}

            self._metrics["requests"][key]["total"] += 1
            if success:
                self._metrics["requests"][key]["success"] += 1
            else:
                self._metrics["requests"][key]["failed"] += 1

            self._metrics["response_times"].append(duration)

            if len(self._metrics["response_times"]) > 1000:
                self._metrics["response_times"] = self._metrics["response_times"][-1000:]

    async def record_error(self, error_type: str, details: str = ""):
        """Increment error count for type (details unused in storage).

        Args:
            error_type: Category of error (str, e.g., 'TTS_FAILURE').
            details: Optional description (str, default "").
        """
        async with self._lock:
            if error_type not in self._metrics["errors"]:
                self._metrics["errors"][error_type] = 0
            self._metrics["errors"][error_type] += 1

    async def record_memory_usage(self):
        """Append current memory stats from MemoryOptimizer to history.

        Caps at 100 recent readings for efficiency.

        Notes:
            Creates a temp MemoryOptimizer for get_memory_usage().
        """
        async with self._lock:
            memory_info = MemoryOptimizer(PerformanceConfig()).get_memory_usage()
            self._metrics["memory_usage"].append(memory_info)

            if len(self._metrics["memory_usage"]) > 100:
                self._metrics["memory_usage"] = self._metrics["memory_usage"][-100:]

    async def get_metrics(self) -> dict[str, Any]:
        """Compile aggregated metrics: uptime, requests breakdown, performance percentiles, errors, memory.

        Computes totals, rates, avg/P95/P99 times from stored data.

        Returns:
            dict: Structured metrics with:
                - uptime_seconds: Seconds since init (float).
                - requests: Total/success/failed/per_minute/success_rate/breakdown (dict).
                - performance: avg/p95/p99/max/min response times (dict).
                - errors: Count per type (dict).
                - memory: Current RSS % available from latest (dict).

        Notes:
            per_minute: total / (uptime/60); 0 if uptime=0.
            success_rate: (success/total * 100) or 0.
            Uses _percentile for P95/P99.
        """
        async with self._lock:
            uptime = time.time() - self._metrics["start_time"]
            total_requests = sum(req["total"] for req in self._metrics["requests"].values())
            successful_requests = sum(req["success"] for req in self._metrics["requests"].values())

            response_times = self._metrics["response_times"]
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0

            return {
                "uptime_seconds": uptime,
                "requests": {
                    "total": total_requests,
                    "successful": successful_requests,
                    "failed": total_requests - successful_requests,
                    "per_minute": total_requests / (uptime / 60) if uptime > 0 else 0,
                    "success_rate": (successful_requests / total_requests * 100) if total_requests > 0 else 0,
                    "breakdown": self._metrics["requests"],
                },
                "performance": {
                    "avg_response_time": avg_response_time,
                    "p95_response_time": self._percentile(response_times, 95),
                    "p99_response_time": self._percentile(response_times, 99),
                    "max_response_time": max(response_times) if response_times else 0,
                    "min_response_time": min(response_times) if response_times else 0,
                },
                "errors": self._metrics["errors"],
                "memory": self._get_memory_stats(),
            }

    def _percentile(self, data: list[float], percentile: int) -> float:
        """Helper to compute percentile from sorted data list.

        Args:
            data: List of numbers (list[float]).
            percentile: Value from 0-100 (int).

        Returns:
            float: Percentile value; 0 if empty.
        """
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]

    def _get_memory_stats(self) -> dict[str, Any]:
        """Extract latest memory info for get_metrics.

        Returns:
            dict: Current RSS MB, %, available MB from recent reading or {} if none.
        """
        if not self._metrics["memory_usage"]:
            return {}

        recent_memory = self._metrics["memory_usage"][-1]
        return {
            "current_mb": recent_memory["rss_mb"],
            "current_percent": recent_memory["percent"],
            "available_mb": recent_memory["available_mb"],
        }


# Global singleton instances for pool and monitor (lazy initialization)
_connection_pool: ConnectionPool | None = None
_performance_monitor: PerformanceMonitor | None = None


def get_connection_pool(config: PerformanceConfig | None = None) -> ConnectionPool:
    """Retrieve or create the global HTTP connection pool.

    Uses provided config or default; initializes if first call.

    Args:
        config: Optional settings (PerformanceConfig or None); defaults to PerformanceConfig().

    Returns:
        ConnectionPool: Shared instance.
    """
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = ConnectionPool(config or PerformanceConfig())
    return _connection_pool


def get_performance_monitor() -> PerformanceMonitor:
    """Retrieve or create the global performance monitor.

    Initializes if first call; no config param.

    Returns:
        PerformanceMonitor: Shared instance.
    """
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


async def cleanup_resources():
    """Close global connection pool and reset instances.

    Calls close_all on pool if exists; sets to None for re-init.

    Notes:
        Monitor does not need explicit cleanup (in-memory).
    """
    global _connection_pool
    if _connection_pool:
        await _connection_pool.close_all()
        _connection_pool = None
