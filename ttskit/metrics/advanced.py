"""
Advanced metrics for TTSKit.

This module handles advanced collection and analysis of metrics, providing comprehensive
monitoring, analytics, and performance tracking tailored for production environments.
"""

import asyncio
import json
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import aiofiles
import psutil


@dataclass
class EngineMetrics:
    """Metrics tracker for individual TTS engines.

    This dataclass captures key performance indicators for a specific TTS engine, including
    request counts, success rates, response times, and error breakdowns.

    Args:
        engine_name: Identifier for the TTS engine.
        total_requests: Cumulative count of all requests processed.
        successful_requests: Count of requests that completed without errors.
        failed_requests: Count of requests that encountered errors.
        total_response_time: Sum of response times for successful requests (in seconds).
        min_response_time: Shortest recorded response time.
        max_response_time: Longest recorded response time.
        last_request_time: Timestamp of the most recent request.
        error_types: Dictionary mapping error categories to their occurrence counts.

    Notes:
        Automatically initializes error_types as a defaultdict if not provided.
        Properties like success_rate and avg_response_time are computed on access.
    """
    engine_name: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_response_time: float = 0.0
    min_response_time: float = float("inf")
    max_response_time: float = 0.0
    last_request_time: datetime | None = None
    error_types: dict[str, int] = None

    def __post_init__(self):
        """Post-initialization setup for mutable fields."""
        if self.error_types is None:
            self.error_types = defaultdict(int)

    @property
    def success_rate(self) -> float:
        """Success rate of requests for this engine.

        Returns:
            float: Percentage of successful requests (0.0 if no requests).
        """
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100

    @property
    def avg_response_time(self) -> float:
        """Average response time for successful requests.

        Returns:
            float: Mean response time in seconds (0.0 if no successful requests).
        """
        if self.successful_requests == 0:
            return 0.0
        return self.total_response_time / self.successful_requests


@dataclass
class LanguageMetrics:
    """Metrics tracker for TTS requests by language.

    This dataclass monitors request volumes, success rates, and engine preferences
    across different languages.

    Args:
        language: Language code (e.g., 'en_US').
        total_requests: Total number of requests for this language.
        successful_requests: Successful requests count.
        failed_requests: Failed requests count.
        total_response_time: Aggregate response time for successful requests.
        engines_used: Dictionary of engine names to usage counts.

    Notes:
        engines_used defaults to a defaultdict(int) for easy incrementing.
        success_rate property computes the percentage dynamically.
    """
    language: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_response_time: float = 0.0
    engines_used: dict[str, int] = None

    def __post_init__(self):
        """Post-initialization for mutable fields like engines_used."""
        if self.engines_used is None:
            self.engines_used = defaultdict(int)

    @property
    def success_rate(self) -> float:
        """Success rate for requests in this language.

        Returns:
            float: Percentage of successful requests (0.0 if no requests).
        """
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100


@dataclass
class CacheMetrics:
    """Performance metrics for cache operations.

    This dataclass tracks cache hits, misses, storage usage, evictions, and overall hit rate
    to monitor caching efficiency.

    Args:
        total_hits: Number of successful cache lookups.
        total_misses: Number of cache lookup failures.
        total_size_bytes: Cumulative size of cached items.
        evictions: Count of items removed due to space limits.
        hit_rate: Percentage of hits among total requests (updated via method).

    Notes:
        Call update_hit_rate() after modifying hits/misses to refresh the rate.
    """
    total_hits: int = 0
    total_misses: int = 0
    total_size_bytes: int = 0
    evictions: int = 0
    hit_rate: float = 0.0

    def update_hit_rate(self):
        """Recalculate and update the cache hit rate.

        This method should be called after updating hit or miss counts to ensure
        the hit_rate reflects the current state.
        """
        total_requests = self.total_hits + self.total_misses
        if total_requests > 0:
            self.hit_rate = (self.total_hits / total_requests) * 100


@dataclass
class SystemMetrics:
    """Snapshot of system resource usage.

    This dataclass holds metrics for CPU, memory, disk, network I/O, and timestamps
    to monitor overall system health during operation.

    Args:
        cpu_percent: Current CPU utilization percentage.
        memory_mb: Used memory in megabytes.
        memory_percent: Memory utilization percentage.
        disk_usage_percent: Disk space used percentage.
        network_io_bytes: Total bytes sent/received (network I/O).
        timestamp: When the metrics were captured.

    Notes:
        timestamp is auto-set to now() if not provided.
    """
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    memory_percent: float = 0.0
    disk_usage_percent: float = 0.0
    network_io_bytes: int = 0
    timestamp: datetime = None

    def __post_init__(self):
        """Set default timestamp if omitted."""
        if self.timestamp is None:
            self.timestamp = datetime.now()


class AdvancedMetricsCollector:
    """Collector for advanced, real-time TTS metrics.

    This class asynchronously gathers and analyzes metrics for TTS engines, languages,
    cache performance, and system resources. It maintains history for trends and supports
    detailed reporting with thread-safety via asyncio locks.

    Notes:
        Designed for production use with configurable history size to balance memory and detail.
        All recording methods are async and use locks to ensure safe concurrent access.
    """
    def __init__(self, history_size: int = 1000):
        """Initialize the metrics collector.

        Args:
            history_size: Maximum number of entries to keep in history deques.

        Initializes dictionaries for engines and languages, cache metrics, history deques,
        and an asyncio lock for thread-safety.
        """
        self.history_size = history_size
        self.engines: dict[str, EngineMetrics] = {}
        self.languages: dict[str, LanguageMetrics] = {}
        self.cache = CacheMetrics()
        self.system_history: deque = deque(maxlen=history_size)
        self.request_history: deque = deque(maxlen=history_size)
        self._lock = asyncio.Lock()
        self._start_time = datetime.now()

    async def record_request(
        self,
        engine: str,
        language: str,
        response_time: float,
        success: bool = True,
        error_type: str | None = None,
    ):
        """Record a TTS request and update related metrics.

        This async method logs a request outcome, updating engine-specific and language-specific
        metrics like counts, times, and errors. It also appends to request history.

        Args:
            engine: Name of the TTS engine used.
            language: Language code for the request.
            response_time: Time taken for the request in seconds.
            success: Whether the request succeeded.
            error_type: Type of error if failed.

        Notes:
            Thread-safe using asyncio lock.
            Initializes new EngineMetrics or LanguageMetrics if the engine/language is new.
            Updates min/max response times and error counts only for relevant cases.
        """
        async with self._lock:
            if engine not in self.engines:
                self.engines[engine] = EngineMetrics(engine_name=engine)

            engine_metrics = self.engines[engine]
            engine_metrics.total_requests += 1
            engine_metrics.last_request_time = datetime.now()

            if success:
                engine_metrics.successful_requests += 1
                engine_metrics.total_response_time += response_time
                engine_metrics.min_response_time = min(
                    engine_metrics.min_response_time, response_time
                )
                engine_metrics.max_response_time = max(
                    engine_metrics.max_response_time, response_time
                )
            else:
                engine_metrics.failed_requests += 1
                if error_type:
                    engine_metrics.error_types[error_type] += 1

            if language not in self.languages:
                self.languages[language] = LanguageMetrics(language=language)

            language_metrics = self.languages[language]
            language_metrics.total_requests += 1
            language_metrics.engines_used[engine] += 1

            if success:
                language_metrics.successful_requests += 1
                language_metrics.total_response_time += response_time
            else:
                language_metrics.failed_requests += 1

            self.request_history.append(
                {
                    "timestamp": datetime.now(),
                    "engine": engine,
                    "language": language,
                    "response_time": response_time,
                    "success": success,
                    "error_type": error_type,
                }
            )

    async def record_cache_event(self, hit: bool, size_bytes: int = 0):
        """Log a cache hit or miss event.

        Updates the cache metrics with the event details and refreshes the hit rate.

        Args:
            hit: True if it was a cache hit, False for a miss.
            size_bytes: Size of the item in bytes (0 if not applicable, e.g., for misses).

        Notes:
            Thread-safe with asyncio lock.
            Only adds to total_size_bytes if size_bytes > 0.
        """
        async with self._lock:
            if hit:
                self.cache.total_hits += 1
            else:
                self.cache.total_misses += 1

            if size_bytes > 0:
                self.cache.total_size_bytes += size_bytes

            self.cache.update_hit_rate()

    async def record_cache_eviction(self):
        """Log a cache item eviction.

        Simply increments the eviction count to track cache pressure.

        Notes:
            Thread-safe with asyncio lock.
        """
        async with self._lock:
            self.cache.evictions += 1

    async def record_error(self, error_type: str, error_message: str):
        """Record an error occurrence.

        Links the error to the latest request's engine and increments failure metrics.
        The error_message is provided but not stored in metrics (use for external logging).

        Args:
            error_type: Category or type of the error (e.g., 'timeout').
            error_message: Descriptive message of the error.

        Notes:
            Thread-safe with lock.
            Falls back to 'unknown' engine if no recent request history.
            Only updates if the engine exists in tracked engines.
        """
        async with self._lock:
            if self.request_history:
                last_request = self.request_history[-1]
                engine = last_request.get("engine", "unknown")

                if engine in self.engines:
                    self.engines[engine].error_types[error_type] += 1
                    self.engines[engine].failed_requests += 1

    async def collect_system_metrics(self):
        """Gather and store current system resource metrics.

        Uses psutil to snapshot CPU, memory, disk, and network usage, then adds
        to the system history deque.

        Notes:
            Thread-safe with lock.
            Disk usage is checked at root '/' (adjust for other OS if needed).
            CPU percent uses a 1-second interval for accuracy.
        """
        async with self._lock:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            network = psutil.net_io_counters()
            network_io = network.bytes_sent + network.bytes_recv

            system_metrics = SystemMetrics(
                cpu_percent=cpu_percent,
                memory_mb=memory.used / 1024 / 1024,
                memory_percent=memory.percent,
                disk_usage_percent=disk.percent,
                network_io_bytes=network_io,
            )

            self.system_history.append(system_metrics)

    async def get_comprehensive_metrics(self) -> dict[str, Any]:
        """Retrieve a full report of all tracked metrics.

        This method aggregates data from engines, languages, cache, performance history,
        and system stats, including calculated health score.

        Returns:
            dict: Comprehensive metrics dictionary with sections for requests, engines,
                  languages, cache, recent performance (e.g., p95/p99 latencies), system,
                  and overall health.

        Notes:
            Thread-safe with lock.
            Uses last 100 requests for recent performance percentiles.
            Uptime and rates (e.g., requests per minute) are computed from start time.
            Returns empty performance dict if no recent successful requests.
        """
        async with self._lock:
            uptime = datetime.now() - self._start_time

            total_requests = sum(eng.total_requests for eng in self.engines.values())
            total_successful = sum(
                eng.successful_requests for eng in self.engines.values()
            )
            total_failed = sum(eng.failed_requests for eng in self.engines.values())

            success_rate = (
                (total_successful / total_requests * 100) if total_requests > 0 else 0
            )
            requests_per_minute = (
                total_requests / (uptime.total_seconds() / 60)
                if uptime.total_seconds() > 0
                else 0
            )

            engine_stats = {}
            for engine_name, engine_metrics in self.engines.items():
                engine_stats[engine_name] = {
                    "total_requests": engine_metrics.total_requests,
                    "success_rate": engine_metrics.success_rate,
                    "avg_response_time": engine_metrics.avg_response_time,
                    "min_response_time": engine_metrics.min_response_time
                    if engine_metrics.min_response_time != float("inf")
                    else 0,
                    "max_response_time": engine_metrics.max_response_time,
                    "error_types": dict(engine_metrics.error_types),
                    "last_request": engine_metrics.last_request_time.isoformat()
                    if engine_metrics.last_request_time
                    else None,
                }

            language_stats = {}
            for lang_code, lang_metrics in self.languages.items():
                language_stats[lang_code] = {
                    "total_requests": lang_metrics.total_requests,
                    "success_rate": lang_metrics.success_rate,
                    "engines_used": dict(lang_metrics.engines_used),
                }

            recent_requests = list(self.request_history)[-100:]
            recent_response_times = [
                req["response_time"] for req in recent_requests if req["success"]
            ]

            recent_performance = {}
            if recent_response_times:
                recent_performance = {
                    "avg_response_time": sum(recent_response_times)
                    / len(recent_response_times),
                    "p95_response_time": self._percentile(recent_response_times, 95),
                    "p99_response_time": self._percentile(recent_response_times, 99),
                    "min_response_time": min(recent_response_times),
                    "max_response_time": max(recent_response_times),
                }

            current_system = (
                self.system_history[-1] if self.system_history else SystemMetrics()
            )

            return {
                "timestamp": datetime.now().isoformat(),
                "uptime_seconds": uptime.total_seconds(),
                "requests": {
                    "total": total_requests,
                    "successful": total_successful,
                    "failed": total_failed,
                    "success_rate": success_rate,
                    "per_minute": requests_per_minute,
                },
                "engines": engine_stats,
                "languages": language_stats,
                "cache": {
                    "hit_rate": self.cache.hit_rate,
                    "total_hits": self.cache.total_hits,
                    "total_misses": self.cache.total_misses,
                    "size_mb": self.cache.total_size_bytes / 1024 / 1024,
                    "evictions": self.cache.evictions,
                },
                "performance": recent_performance,
                "system": {
                    "cpu_percent": current_system.cpu_percent,
                    "memory_mb": current_system.memory_mb,
                    "memory_percent": current_system.memory_percent,
                    "disk_usage_percent": current_system.disk_usage_percent,
                    "network_io_mb": current_system.network_io_bytes / 1024 / 1024,
                },
                "health": self._calculate_health_score(),
            }

    async def get_engine_comparison(self) -> dict[str, Any]:
        """Compare performance across all tracked engines.

        Computes custom scores for reliability and performance per engine.

        Returns:
            dict: Engine name to stats dict, including requests, success_rate, avg_response_time,
                  reliability_score, and performance_score. Empty dict if no engines tracked.

        Notes:
            Thread-safe.
            Scores are calculated using private methods for consistency.
        """
        async with self._lock:
            if not self.engines:
                return {}

            comparison = {}
            for engine_name, engine_metrics in self.engines.items():
                comparison[engine_name] = {
                    "requests": engine_metrics.total_requests,
                    "success_rate": engine_metrics.success_rate,
                    "avg_response_time": engine_metrics.avg_response_time,
                    "reliability_score": self._calculate_reliability_score(
                        engine_metrics
                    ),
                    "performance_score": self._calculate_performance_score(
                        engine_metrics
                    ),
                }

            return comparison

    async def get_language_analytics(self) -> dict[str, Any]:
        """Analyze usage patterns across languages.

        Calculates usage percentages and identifies top engines for each language.

        Returns:
            dict: Language code to analytics dict with total_requests, usage_percentage,
                  success_rate, and preferred_engines (top 3). Empty if no languages tracked.

        Notes:
            Thread-safe.
            Usage percentage is relative to total requests across all languages.
            preferred_engines sorts by usage count, descending.
        """
        async with self._lock:
            if not self.languages:
                return {}

            analytics = {}
            total_requests = sum(
                lang.total_requests for lang in self.languages.values()
            )

            for lang_code, lang_metrics in self.languages.items():
                usage_percentage = (
                    (lang_metrics.total_requests / total_requests * 100)
                    if total_requests > 0
                    else 0
                )

                analytics[lang_code] = {
                    "total_requests": lang_metrics.total_requests,
                    "usage_percentage": usage_percentage,
                    "success_rate": lang_metrics.success_rate,
                    "preferred_engines": sorted(
                        lang_metrics.engines_used.items(),
                        key=lambda x: x[1],
                        reverse=True,
                    )[:3],
                }

            return analytics

    async def export_metrics(self, file_path: Path, format: str = "json") -> bool:
        """Save current metrics to a file.

        Supports JSON export via aiofiles for async writing.

        Args:
            file_path: Pathlib Path object for the output file.
            format: Export format ('json' only; others return False).

        Returns:
            bool: True on successful write, False on unsupported format or exceptions.

        Notes:
            Uses get_comprehensive_metrics() for the data.
            JSON is pretty-printed with indentation and UTF-8 encoding.
            Exceptions (e.g., IO errors) are caught and return False without raising.
        """
        try:
            metrics = await self.get_comprehensive_metrics()

            if format.lower() == "json":
                async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                    await f.write(json.dumps(metrics, indent=2, ensure_ascii=False))
            else:
                return False

            return True
        except Exception:
            return False

    def get_stats(self) -> dict[str, Any]:
        """Fetch a quick synchronous summary of key metrics.

        This non-async method provides basic stats without locks, suitable for simple queries.

        Returns:
            dict: Contains uptime_seconds, total_requests, successful_requests, failed_requests,
                  success_rate, requests_per_minute, engines_count, languages_count, and cache_hit_rate.

        Notes:
            Computations mirror parts of get_comprehensive_metrics but are faster (no lock, no deep aggregates).
            Rates are zero if no uptime or requests.
        """
        uptime = datetime.now() - self._start_time

        total_requests = sum(eng.total_requests for eng in self.engines.values())
        total_successful = sum(eng.successful_requests for eng in self.engines.values())
        total_failed = sum(eng.failed_requests for eng in self.engines.values())

        success_rate = (
            (total_successful / total_requests * 100) if total_requests > 0 else 0
        )
        requests_per_minute = (
            total_requests / (uptime.total_seconds() / 60)
            if uptime.total_seconds() > 0
            else 0
        )

        return {
            "uptime_seconds": uptime.total_seconds(),
            "total_requests": total_requests,
            "successful_requests": total_successful,
            "failed_requests": total_failed,
            "success_rate": success_rate,
            "requests_per_minute": requests_per_minute,
            "engines_count": len(self.engines),
            "languages_count": len(self.languages),
            "cache_hit_rate": self.cache.hit_rate,
        }

    def reset(self):
        """Clear all accumulated metrics and restart tracking.

        This synchronous method wipes engines, languages, cache, histories, and resets the start time
        to begin fresh monitoring.

        Notes:
            No lock needed as it's not async, but use cautiously in concurrent environments.
            All deques and dicts are emptied or recreated.
        """
        self.engines.clear()
        self.languages.clear()
        self.cache = CacheMetrics()
        self.system_history.clear()
        self.request_history.clear()
        self._start_time = datetime.now()

    def _percentile(self, data: list[float], percentile: int) -> float:
        """Compute the specified percentile from a list of values.

        Private helper for latency percentiles (e.g., p95, p99).

        Args:
            data: List of float values (e.g., response times).
            percentile: Integer from 0 to 100 indicating the percentile.

        Returns:
            float: The value at the computed index in sorted data (0 if empty list).

        Notes:
            Uses simple index calculation; for large datasets, consider more advanced methods.
            Bounds index to avoid out-of-range errors.
        """
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]

    def _calculate_health_score(self) -> float:
        """Compute an overall health score for the system (0-100).

        Private method that weights success rates, response times, and resource usage.

        Returns:
            float: Clamped score between 0 and 100; 0 if no engines tracked.

        Notes:
            Weights: 40% success, 30% response time (penalizes high avg), 30% system (CPU+mem avg).
            Uses latest system metrics; defaults to empty SystemMetrics if no history.
            Response score assumes <10s avg is ideal (adjust multiplier for tuning).
        """
        if not self.engines:
            return 0.0

        avg_success_rate = sum(eng.success_rate for eng in self.engines.values()) / len(
            self.engines
        )

        avg_response_time = sum(
            eng.avg_response_time for eng in self.engines.values()
        ) / len(self.engines)
        response_time_score = max(
            0, 100 - (avg_response_time * 10)
        )

        current_system = (
            self.system_history[-1] if self.system_history else SystemMetrics()
        )
        system_score = (
            100 - (current_system.cpu_percent + current_system.memory_percent) / 2
        )

        health_score = (
            avg_success_rate * 0.4 + response_time_score * 0.3 + system_score * 0.3
        )
        return min(100, max(0, health_score))

    def _calculate_reliability_score(self, engine_metrics: EngineMetrics) -> float:
        """Score an engine's reliability based on success and errors.

        Private helper that penalizes total error counts.

        Args:
            engine_metrics: The EngineMetrics instance to evaluate.

        Returns:
            float: Base success rate minus error penalty (min 0); 0 if no requests.

        Notes:
            Penalty is 2 points per error instance—tune as needed for sensitivity.
        """
        if engine_metrics.total_requests == 0:
            return 0.0

        base_score = engine_metrics.success_rate

        error_penalty = sum(engine_metrics.error_types.values()) * 2

        return max(0, base_score - error_penalty)

    def _calculate_performance_score(self, engine_metrics: EngineMetrics) -> float:
        """Score an engine's performance using response times and variability.

        Private method focusing on speed and consistency.

        Args:
            engine_metrics: The EngineMetrics to score.

        Returns:
            float: Combined score capped at 100; 0 if no successful requests.

        Notes:
            Response score penalizes avg >5s (20 points per second).
            Consistency bonus (0-10) from min/max ratio; higher ratio (closer times) is better.
        """
        if engine_metrics.successful_requests == 0:
            return 0.0

        response_time_score = max(0, 100 - (engine_metrics.avg_response_time * 20))

        consistency_bonus = 0
        if engine_metrics.max_response_time > 0:
            consistency_ratio = (
                engine_metrics.min_response_time / engine_metrics.max_response_time
            )
            consistency_bonus = consistency_ratio * 10

        return min(100, response_time_score + consistency_bonus)


# Singleton instance for the advanced metrics collector (lazy-initialized)
_metrics_collector: AdvancedMetricsCollector | None = None


def get_metrics_collector() -> AdvancedMetricsCollector:
    """Retrieve the global singleton metrics collector.

    Lazily initializes if not already created.

    Returns:
        AdvancedMetricsCollector: The shared instance for all metrics operations.
    """
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = AdvancedMetricsCollector()
    return _metrics_collector


async def start_metrics_collection(interval_seconds: int = 60):
    """Launch background task for periodic system metrics collection.

    Runs an infinite async loop, calling collect_system_metrics every interval,
    with error handling to continue on failures.

    Args:
        interval_seconds: Interval between collections (default 60 seconds).

    Notes:
        Uses the global collector instance.
        Exceptions are printed but don't halt the loop—sleeps and retries.
        Designed to run in an event loop (e.g., via asyncio.create_task).
    """
    collector = get_metrics_collector()

    while True:
        try:
            await collector.collect_system_metrics()
            await asyncio.sleep(interval_seconds)
        except Exception as e:
            print(f"Error in metrics collection: {e}")
            await asyncio.sleep(interval_seconds)
