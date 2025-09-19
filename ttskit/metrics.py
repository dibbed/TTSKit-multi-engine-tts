"""Metrics collection and monitoring for TTSKit.

This module handles tracking of TTS requests, errors, performance, and system stats
for observability, debugging, and health monitoring.
"""

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any


@dataclass
class RequestMetrics:
    """Data class capturing metrics for an individual TTS request.

    Tracks timing, success, engine usage, and cache hits for analysis.

    Args:
        start_time: Timestamp when request began.
        request_id: Unique ID for the request.
        user_id: Identifier for the user making the request.
        end_time: Optional timestamp when request completed.
        language: Language code (e.g., 'en').
        engine: TTS engine used (e.g., 'edge').
        text_length: Length of input text in characters.
        success: True if synthesis succeeded.
        error_type: Optional category of failure.
        cache_hit: True if served from cache.
    """

    start_time: float
    request_id: str = ""
    user_id: str = ""
    end_time: float | None = None
    language: str = ""
    engine: str = ""
    text_length: int = 0
    success: bool = False
    error_type: str | None = None
    cache_hit: bool = False

    @property
    def duration(self) -> float:
        """Calculate the request duration in seconds.

        Uses end_time if set, otherwise current time minus start_time.

        Returns:
            Float representing elapsed time.
        """
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time

    def start_timer(self) -> None:
        """Update start_time to current timestamp."""
        self.start_time = time.time()

    def end_timer(self) -> None:
        """Set end_time to current timestamp."""
        self.end_time = time.time()

    def mark_success(self) -> None:
        """Set success flag to True."""
        self.success = True

    def mark_failure(self, error_type: str) -> None:
        """Set success to False and record error type.

        Args:
            error_type: String categorizing the failure (e.g., 'timeout').
        """
        self.success = False
        self.error_type = error_type


class MetricsCollector:
    """Central collector for aggregating TTS request metrics and stats.

    Uses thread-safe storage for histories, counters, and timers; supports enabling/disabling.

    Args:
        max_history: Max number of recent requests to keep (default 1000).
        enabled: Whether to collect metrics (default True).
        max_metrics: Optional cap on total metrics (defaults to max_history).
    """

    def __init__(
        self, max_history: int = 1000, enabled: bool = True, max_metrics: int = None
    ):
        self.max_history = max_history
        self.enabled = enabled
        self.max_metrics = max_metrics or max_history
        self._requests: deque = deque(maxlen=max_history)
        self._counters: dict[str, int] = defaultdict(int)
        self._timers: dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self._lock = threading.Lock()
        self._start_time = time.time()

    def record_request(self, metrics: RequestMetrics) -> None:
        """Log a completed request and update counters/timers.

        Thread-safe; skips if disabled.

        Args:
            metrics: Populated RequestMetrics instance.
        """
        if not self.enabled:
            return

        with self._lock:
            self._requests.append(metrics)
            self._counters["total_requests"] += 1

            if metrics.success:
                self._counters["successful_requests"] += 1
            else:
                self._counters["failed_requests"] += 1
                if metrics.error_type:
                    self._counters[f"error_{metrics.error_type}"] += 1

            if metrics.cache_hit:
                self._counters["cache_hits"] += 1

            self._counters[f"requests_{metrics.language}"] += 1
            self._counters[f"requests_{metrics.engine}"] += 1

            self._timers["request_duration"].append(metrics.duration)
            self._timers[f"duration_{metrics.language}"].append(metrics.duration)
            self._timers[f"duration_{metrics.engine}"].append(metrics.duration)

    def get_stats(self) -> dict[str, Any]:
        """Compute and return aggregated metrics summary.

        Includes totals, rates, distributions, and uptime.

        Returns:
            Dict with keys like 'success_rate', 'language_distribution', etc.

        Notes:
            Thread-safe; empty if no requests; rounds values for readability.
        """
        with self._lock:
            total_requests = self._counters["total_requests"]
            successful_requests = self._counters["successful_requests"]
            failed_requests = self._counters["failed_requests"]

            if total_requests == 0:
                return {"total_requests": 0}

            durations = list(self._timers["request_duration"])
            avg_duration = sum(durations) / len(durations) if durations else 0

            success_rate = (successful_requests / total_requests) * 100

            cache_hits = self._counters["cache_hits"]
            cache_hit_rate = (
                (cache_hits / total_requests) * 100 if total_requests > 0 else 0
            )

            language_stats = {}
            for key, count in self._counters.items():
                if key.startswith("requests_"):
                    lang = key.replace("requests_", "")
                    if lang not in ["total", "successful", "failed"]:
                        language_stats[lang] = count

            engine_stats = {}
            for key, count in self._counters.items():
                if key.startswith("requests_"):
                    engine = key.replace("requests_", "")
                    if engine in ["gtts", "edge"]:
                        engine_stats[engine] = count

            return {
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "failed_requests": failed_requests,
                "success_rate": round(success_rate, 2),
                "cache_hit_rate": round(cache_hit_rate, 2),
                "average_duration": round(avg_duration, 3),
                "language_distribution": language_stats,
                "engine_distribution": engine_stats,
                "error_breakdown": {
                    k.replace("error_", ""): v
                    for k, v in self._counters.items()
                    if k.startswith("error_")
                },
                "uptime": time.time() - self._start_time,
            }

    def reset(self) -> None:
        """Clear all stored metrics and reset uptime counter.

        Thread-safe; useful for testing or periodic resets.
        """
        with self._lock:
            self._requests.clear()
            self._counters.clear()
            self._timers.clear()
            self._start_time = time.time()

    @property
    def metrics(self) -> list[RequestMetrics]:
        """Access the list of recent RequestMetrics objects.

        Returns:
            Copy of the deque as list (limited by max_history).
        """
        with self._lock:
            return list(self._requests)

    def record_cached_request(
        self,
        request_id: str,
        user_id: str,
        engine: str,
        language: str,
        text_length: int,
    ) -> None:
        """Log a cache hit as a successful request with minimal overhead.

        Creates a RequestMetrics with success=True and cache_hit=True.

        Args:
            request_id: Unique request ID.
            user_id: User identifier.
            engine: Engine that would have been used.
            language: Language code.
            text_length: Input text length.
        """
        metrics = RequestMetrics(
            start_time=time.time(),
            request_id=request_id,
            user_id=user_id,
            engine=engine,
            language=language,
            text_length=text_length,
            success=True,
            cache_hit=True,
        )
        self.record_request(metrics)

    def get_recent_requests(self, limit: int = 10) -> list:
        """Retrieve the most recent requests up to the limit.

        Args:
            limit: Max number to return (default 10).

        Returns:
            List of recent RequestMetrics.
        """
        with self._lock:
            return list(self._requests)[-limit:]


# Global metrics collector instance
metrics_collector = MetricsCollector()


def record_request_metrics(
    metrics: RequestMetrics | None = None,
    language: str = "",
    engine: str = "",
    text_length: int = 0,
    success: bool = False,
    error_type: str | None = None,
    cache_hit: bool = False,
    duration: float | None = None,
) -> None:
    """Convenience function to record metrics using the global collector.

    Accepts pre-built metrics or builds one from params.

    Args:
        metrics: Optional existing RequestMetrics.
        language: Language if building new.
        engine: Engine if building new.
        text_length: Text length if building new.
        success: Success flag if building new.
        error_type: Error category if building new.
        cache_hit: Cache flag if building new.
        duration: Optional duration for back-calculating timestamps.
    """
    if metrics is not None:
        metrics_collector.record_request(metrics)
    else:
        metrics = RequestMetrics(
            start_time=time.time() - (duration or 0),
            end_time=time.time() if duration else None,
            language=language,
            engine=engine,
            text_length=text_length,
            success=success,
            error_type=error_type,
            cache_hit=cache_hit,
        )
        metrics_collector.record_request(metrics)


def get_metrics() -> list[RequestMetrics]:
    """Access all stored RequestMetrics via the global collector.

    Returns:
        List of recent metrics.
    """
    return metrics_collector.metrics


def get_metrics_summary() -> dict[str, Any]:
    """Get the aggregated stats summary from the global collector.

    Returns:
        Dict with rates, distributions, etc.
    """
    return metrics_collector.get_stats()


def reset_metrics() -> None:
    """Reset the global metrics collector."""
    metrics_collector.reset()


def export_metrics(format: str = "json") -> str:
    """Serialize metrics in JSON or Prometheus format.

    Args:
        format: 'json' or 'prometheus' (default 'json'); str() for others.

    Returns:
        Formatted string of metrics data.
    """
    stats = get_metrics()
    if format == "json":
        import json

        return json.dumps(stats, indent=2)
    elif format == "prometheus":
        lines = []
        for key, value in stats.items():
            if isinstance(value, int | float):
                lines.append(f"ttskit_{key} {value}")
        return "\n".join(lines)
    else:
        return str(stats)


def get_metrics_history(limit: int = 100) -> list[dict[str, Any]]:
    """Fetch recent requests as dicts from the global collector.

    Args:
        limit: Max number to return (default 100).

    Returns:
        List of dict representations of recent RequestMetrics.
    """
    return metrics_collector.get_recent_requests(limit)
