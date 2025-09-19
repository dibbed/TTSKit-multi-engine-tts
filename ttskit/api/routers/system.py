"""System and admin endpoints router."""

import time
from typing import Annotated

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ...metrics.advanced import get_metrics_collector
from ...public import (
    clear_cache,
    get_cache_stats,
    get_config,
    get_documentation,
    get_health_status,
    get_rate_limit_info,
    get_supported_formats,
    get_supported_languages,
    get_system_info,
    is_cache_enabled,
)
from ...utils.logging_config import get_logger
from ...utils.performance import get_performance_monitor
from ...version import __version__
from ..dependencies import RequiredAuth, WriteAuth

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["system"])

start_time = time.time()


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str = Field(description="Service status")
    engines: int = Field(description="Number of available engines")
    uptime: float = Field(description="Service uptime in seconds")
    version: str = Field(description="TTSKit version")


class CacheStatsResponse(BaseModel):
    """Cache statistics response model."""

    enabled: bool = Field(description="Whether cache is enabled")
    hits: int = Field(description="Cache hits")
    misses: int = Field(description="Cache misses")
    hit_rate: float = Field(description="Cache hit rate")
    size: int = Field(description="Cache size in bytes")
    entries: int = Field(description="Number of cache entries")


@router.get("/health", response_model=HealthResponse)
async def health_check(
    auth: Annotated[RequiredAuth, RequiredAuth],
):
    """
    Perform a health check on the TTSKit service.

    Executes a comprehensive health check that verifies service availability,
    counts available TTS engines, calculates uptime, and returns current version.

    Parameters:
        auth (RequiredAuth): Authentication context for accessing system endpoints.
            Must have read permissions for system status.

    Returns:
        HealthResponse: Service health information containing:
            - status: Service health status (healthy, degraded, etc.)
            - engines: Number of currently available TTS engines
            - uptime: Service uptime in seconds since startup
            - version: Current TTSKit version
    """
    try:
        from ...public import get_engines

        engines = get_engines()
        available_engines = [e for e in engines if e.get("available", False)]

        return HealthResponse(
            status="healthy",
            engines=len(available_engines),
            uptime=time.time() - start_time,
            version=__version__,
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/status")
async def get_status(
    auth: Annotated[RequiredAuth, RequiredAuth],
):
    """
    Retrieve detailed system status information.

    Provides comprehensive health status including system resources,
    service availability, and detailed diagnostics from the health monitoring system.

    Parameters:
        auth (RequiredAuth): Authentication context for accessing system endpoints.
            Must have read permissions for system status.

    Returns:
        Dict: Comprehensive system status information containing detailed
            diagnostics, resource utilization, service health indicators,
            and operational metrics.
    """
    try:
        status_info = await get_health_status()
        return status_info

    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/info")
async def get_system_information(
    auth: Annotated[RequiredAuth, RequiredAuth],
):
    """
    Retrieve comprehensive system information.

    Provides detailed information about system configuration, hardware specs,
    environment details, and operational parameters required for diagnostics.

    Parameters:
        auth (RequiredAuth): Authentication context for accessing system endpoints.
            Must have read permissions for system information.

    Returns:
        Dict: Comprehensive system information including:
            - environment: System environment details (OS, Python version, etc.)
            - configuration: System configuration parameters
            - capabilities: System operation capabilities
            - resources: Hardware and resource information
    """
    try:
        system_info = get_system_info()
        return system_info

    except Exception as e:
        logger.error(f"Failed to get system info: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/config")
async def get_configuration(
    auth: Annotated[RequiredAuth, RequiredAuth],
):
    """
    Retrieve current TTSKit configuration settings.

    Provides access to system configuration parameters while protecting
    sensitive information like API keys and database URLs by replacing them
    with masked values for security.

    Parameters:
        auth (RequiredAuth): Authentication context for accessing system configuration.
            Must have read permissions for configuration data.

    Returns:
        Dict: System configuration parameters with the following structure:
            - General settings (service config, timeouts, etc.)
            - Engine configurations (vocies, defaults, etc.)
            - Sensitive data fields masked with "***"

    Notes:
        Sensitive information fields like 'api_key' and 'redis_url' are
        automatically masked in the response for security reasons.
    """
    try:
        config = get_config()
        # Remove sensitive information
        if "api_key" in config:
            config["api_key"] = "***"
        if "redis_url" in config:
            config["redis_url"] = "***"

        return config

    except Exception as e:
        logger.error(f"Failed to get configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/cache/stats", response_model=CacheStatsResponse)
async def get_cache_statistics(
    auth: Annotated[RequiredAuth, RequiredAuth],
):
    """
    Retrieve cache performance statistics and metrics.

    Provides comprehensive insights into the current state of the audio cache
    system, including hit/miss ratios, memory usage, and entry counts.

    Parameters:
        auth (RequiredAuth): Authentication context for accessing cache metrics.
            Must have read permissions for system statistics.

    Returns:
        CacheStatsResponse: Complete cache statistics with the following metrics:
            - enabled: Boolean indicating if caching is currently active
            - hits: Total number of successful cache lookups
            - misses: Total number of cache misses requiring synthesis
            - hit_rate: Cache efficiency ratio (hits/total_requests)
            - size: Current total cache size in bytes
            - entries: Number of cached audio files stored
    """
    try:
        stats = get_cache_stats()
        enabled = is_cache_enabled()

        return CacheStatsResponse(
            enabled=enabled,
            hits=stats.get("hits", 0),
            misses=stats.get("misses", 0),
            hit_rate=stats.get("hit_rate", 0.0),
            size=stats.get("size", 0),
            entries=stats.get("entries", 0),
        )

    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/cache/clear")
async def clear_cache_endpoint(
    auth: Annotated[WriteAuth, WriteAuth],
):
    """
    Clear all cached audio files and reset cache statistics.

    Removes all stored audio files from the cache system and resets
    performance metrics counters to zero. Requires write permissions
    as this is a destructive operation.

    Parameters:
        auth (WriteAuth): Authentication context with write permissions.
            Must have administrative privileges to clear cache.

    Returns:
        Dict: Confirmation message with format:
            {"message": "Cache cleared successfully"}

    Notes:
        This operation cannot be undone and will require all audio
        synthesis requests to be processed from scratch afterward.
    """
    try:
        clear_cache()
        return {"message": "Cache cleared successfully"}

    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/cache/enabled")
async def is_cache_enabled_endpoint(
    auth: Annotated[RequiredAuth, RequiredAuth],
):
    """
    Check if cache is enabled.

    Returns cache status.
    """
    try:
        enabled = is_cache_enabled()
        return {"enabled": enabled}

    except Exception as e:
        logger.error(f"Failed to check cache status: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/formats")
async def get_supported_audio_formats(
    auth: Annotated[RequiredAuth, RequiredAuth],
):
    """
    Get supported audio formats.

    Returns list of supported audio formats.
    """
    try:
        formats = get_supported_formats()
        return {"formats": formats}

    except Exception as e:
        logger.error(f"Failed to get supported formats: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/languages")
async def get_supported_language_codes(
    auth: Annotated[RequiredAuth, RequiredAuth],
):
    """
    Get supported language codes.

    Returns list of supported language codes.
    """
    try:
        languages = get_supported_languages()
        return {"languages": languages}

    except Exception as e:
        logger.error(f"Failed to get supported languages: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/rate-limit")
async def get_rate_limit_information(
    auth: Annotated[RequiredAuth, RequiredAuth],
):
    """
    Get rate limit information.

    Returns current rate limit settings and usage.
    """
    try:
        # Use auth user_id or default to 'anonymous'
        user_id = getattr(auth, "user_id", None) if auth else None
        if not user_id:
            user_id = "anonymous"
        rate_info = await get_rate_limit_info(user_id)
        return rate_info

    except Exception as e:
        logger.error(f"Failed to get rate limit info: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/documentation")
async def get_docs(
    auth: Annotated[RequiredAuth, RequiredAuth],
):
    """
    Get project documentation.

    Returns API documentation and usage examples.
    """
    try:
        docs = get_documentation()
        return docs

    except Exception as e:
        logger.error(f"Failed to get documentation: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/metrics")
async def get_metrics(
    auth: Annotated[RequiredAuth, RequiredAuth],
):
    """
    Get system metrics.

    Returns performance metrics and statistics.
    """
    try:
        from ...config import settings
        from ...public import TTS

        tts_instance = TTS(default_lang=settings.default_lang)
        stats = tts_instance.get_stats()

        # Add system metrics
        import psutil

        system_metrics = {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage("/").percent,
            "process_count": len(psutil.pids()),
            "uptime": time.time() - start_time,
        }

        return {
            "tts_stats": stats,
            "system_metrics": system_metrics,
            "version": __version__,
        }

    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/advanced-metrics")
async def get_advanced_metrics(
    auth: Annotated[RequiredAuth, RequiredAuth],
):
    """
    Get comprehensive advanced metrics.

    Returns detailed performance analytics, engine comparison,
    language analytics, and system health metrics.
    """
    try:
        metrics_collector = get_metrics_collector()
        performance_monitor = get_performance_monitor()

        # Get comprehensive metrics
        comprehensive_metrics = await metrics_collector.get_comprehensive_metrics()
        engine_comparison = await metrics_collector.get_engine_comparison()
        language_analytics = await metrics_collector.get_language_analytics()
        performance_metrics = await performance_monitor.get_metrics()

        return {
            "comprehensive": comprehensive_metrics,
            "engine_comparison": engine_comparison,
            "language_analytics": language_analytics,
            "performance": performance_metrics,
            "timestamp": time.time(),
            "version": __version__,
        }
    except Exception as e:
        logger.error(f"Failed to get advanced metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/version")
async def get_version(
    auth: Annotated[RequiredAuth, RequiredAuth],
):
    """
    Get version information.

    Returns current version and build information.
    """
    try:
        return {
            "version": __version__,
            "service": "TTSKit API",
            "status": "running",
            "uptime": time.time() - start_time,
        }

    except Exception as e:
        logger.error(f"Failed to get version: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
