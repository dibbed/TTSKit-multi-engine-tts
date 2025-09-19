"""Metrics collection and analysis for TTSKit.

This package offers comprehensive monitoring tools for collecting, analyzing, and tracking
performance metrics in TTS operations, with a focus on production environments and
real-time analytics capabilities.
"""

from .advanced import (
    AdvancedMetricsCollector,
    CacheMetrics,
    EngineMetrics,
    LanguageMetrics,
    SystemMetrics,
    get_metrics_collector,
    start_metrics_collection,
)


def get_metrics_summary():
    """Retrieve a quick summary of current metrics.

    This function provides basic stats synchronously, falling back to an error dict
    if the collector is unavailable or an exception occurs.

    Returns:
        dict: Key metrics like uptime, request counts, success rate, and cache hit rate
              if successful; otherwise {"error": "Metrics not available"}.

    Notes:
        Imports asyncio and get_metrics_collector internally for access.
        Relies on the collector's get_stats() method, which avoids async locks for speed.
        Catches all exceptions to ensure graceful degradation.
    """
    try:
        import asyncio

        from .advanced import get_metrics_collector

        collector = get_metrics_collector()
        return collector.get_stats()
    except Exception:
        return {"error": "Metrics not available"}


__all__ = [
    "AdvancedMetricsCollector",
    "CacheMetrics",
    "EngineMetrics",
    "LanguageMetrics",
    "SystemMetrics",
    "get_metrics_collector",
    "start_metrics_collection",
    "get_metrics_summary",
]
