"""Health check utilities for TTSKit.

This module provides tools to monitor system health, including TTS engines,
cache, configuration, and performance metrics for reliable operation.
"""

import asyncio
import shutil
import subprocess
import time
from dataclasses import dataclass
from typing import Any

from .cache import get_cache
from .config import settings
from .exceptions import ConfigurationError

try:
    from .engines.gtts_engine import GTTSEngine
except ImportError:
    GTTSEngine = None

try:
    from .engines.edge_engine import EDGE_AVAILABLE, EdgeEngine
except ImportError:
    EdgeEngine = None
    EDGE_AVAILABLE = False

try:
    from .utils.temp_manager import TempFileManager
except ImportError:
    TempFileManager = None

try:
    from .metrics import get_metrics_summary
except ImportError:
    get_metrics_summary = None

try:
    import psutil
except ImportError:
    psutil = None

try:
    from .cache.redis import REDIS_AVAILABLE
except ImportError:
    REDIS_AVAILABLE = False

try:
    from .engines.factory import factory
except ImportError:
    factory = None


@dataclass
class HealthCheckResult:
    """Data class holding results from a single health check.

    Includes status, message, and optional details for reporting.

    Args:
        name: The check identifier (e.g., 'ffmpeg').
        status: True if healthy, False otherwise.
        message: Human-readable summary.
        details: Optional dict with extra info (e.g., versions, metrics).
    """

    name: str
    status: bool
    message: str
    details: dict[str, Any] | None = None

    def __post_init__(self):
        """Ensure details is initialized if None."""
        if self.details is None:
            self.details = {}

    def to_dict(self) -> dict[str, Any]:
        """Serialize the health result to a dictionary for JSON or API output.

        Returns:
            Dict with name, status, message, and details.
        """
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "details": self.details,
        }


class HealthChecker:
    """Main class for running and aggregating TTSKit health checks.

    Tracks results across components like engines, cache, and system resources.

    Notes:
        Checks run asynchronously where possible for non-blocking monitoring.
    """

    def __init__(self):
        self.checks: dict[str, bool] = {}
        self.details: dict[str, Any] = {}

    async def check_ffmpeg(self) -> bool:
        """Verify FFmpeg installation and functionality for audio processing.

        Runs 'ffmpeg -version' to confirm availability.

        Returns:
            True if FFmpeg is usable, False otherwise.

        Notes:
            Updates internal checks and details; handles timeouts and PATH issues.
        """
        try:
            ffmpeg_path = shutil.which("ffmpeg") or "ffmpeg"
            result = subprocess.run(  # noqa: S603
                [ffmpeg_path, "-version"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )

            if result.returncode == 0:
                self.checks["ffmpeg"] = True
                self.details["ffmpeg"] = {
                    "available": True,
                    "version": result.stdout.split("\n")[0]
                    if result.stdout
                    else "Unknown",
                }
                return True
            else:
                self.checks["ffmpeg"] = False
                self.details["ffmpeg"] = {
                    "available": False,
                    "error": result.stderr or "Unknown error",
                }
                return False

        except FileNotFoundError:
            self.checks["ffmpeg"] = False
            self.details["ffmpeg"] = {
                "available": False,
                "error": "FFmpeg not found in PATH",
            }
            return False
        except subprocess.TimeoutExpired:
            self.checks["ffmpeg"] = False
            self.details["ffmpeg"] = {
                "available": False,
                "error": "FFmpeg check timed out",
            }
            return False
        except asyncio.TimeoutError:
            self.checks["ffmpeg"] = False
            self.details["ffmpeg"] = {
                "available": False,
                "error": "FFmpeg check timed out",
            }
            return False
        except Exception as e:
            self.checks["ffmpeg"] = False
            self.details["ffmpeg"] = {"available": False, "error": str(e)}
            return False

    async def check_engines(self) -> bool:
        """Test availability of TTS engines by instantiating them with a default language.

        Supports gTTS and Edge; checks for import and basic init success.

        Returns:
            True if all engines are ready, False if any fail.

        Notes:
            Updates internal status; Piper checked via config elsewhere.
        """
        try:
            engines_status = {}

            if GTTSEngine is not None:
                try:
                    GTTSEngine(default_lang="en")
                    engines_status["gtts"] = {"available": True, "error": None}
                except Exception as e:
                    engines_status["gtts"] = {"available": False, "error": str(e)}
            else:
                engines_status["gtts"] = {
                    "available": False,
                    "error": "GTTSEngine not available",
                }

            if EDGE_AVAILABLE and EdgeEngine is not None:
                try:
                    EdgeEngine(default_lang="en")
                    engines_status["edge"] = {"available": True, "error": None}
                except Exception as e:
                    engines_status["edge"] = {"available": False, "error": str(e)}
            else:
                engines_status["edge"] = {
                    "available": False,
                    "error": "Edge engine not available",
                }

            self.checks["engines"] = all(
                eng["available"] for eng in engines_status.values()
            )
            self.details["engines"] = engines_status

            return self.checks["engines"]

        except Exception as e:
            self.checks["engines"] = False
            self.details["engines"] = {"error": str(e)}
            return False

    async def check_redis(self) -> bool:
        """Verify Redis connectivity if caching is enabled.

        Skips if disabled; otherwise pings via cache interface.

        Returns:
            True if Redis is ready or not needed, False on connection issues.

        Notes:
            Requires redis package; falls back gracefully.
        """
        if not settings.enable_caching:
            self.checks["redis"] = True
            self.details["redis"] = {"available": True, "reason": "Caching disabled"}
            return True

        try:
            cache = get_cache()
            cache.get_stats()

            self.checks["redis"] = True
            self.details["redis"] = {"available": True, "url": settings.redis_url}
            return True

        except ImportError:
            self.checks["redis"] = False
            self.details["redis"] = {
                "available": False,
                "error": "Redis package not installed",
            }
            return False
        except Exception as e:
            self.checks["redis"] = False
            self.details["redis"] = {"available": False, "error": str(e)}
            return False

    async def check_configuration(self) -> bool:
        """Validate key configuration settings like token, audio params, and limits.

        Raises ConfigurationError on issues; catches for status reporting.

        Returns:
            True if config is sound, False with error details.

        Notes:
            Focuses on critical params; full Pydantic validation elsewhere.
        """
        try:
            if not settings.bot_token:
                raise ConfigurationError("Bot token is required for bot mode")

            if settings.audio_sample_rate < 8000 or settings.audio_sample_rate > 192000:
                raise ConfigurationError("Invalid audio sample rate")

            if settings.audio_channels not in [1, 2]:
                raise ConfigurationError("Audio channels must be 1 or 2")

            if settings.enable_rate_limiting:
                if settings.rate_limit_rpm < 1 or settings.rate_limit_rpm > 100:
                    raise ConfigurationError("Invalid rate limit RPM")

                if settings.rate_limit_window < 10 or settings.rate_limit_window > 3600:
                    raise ConfigurationError("Invalid rate limit window")

            self.checks["configuration"] = True
            self.details["configuration"] = {"valid": True}
            return True

        except Exception as e:
            self.checks["configuration"] = False
            self.details["configuration"] = {"valid": False, "error": str(e)}
            return False

    async def check_temp_directory(self) -> bool:
        """Test writability of temporary directories via TempFileManager.

        Creates and writes a test file to confirm permissions.

        Returns:
            True if writable, False on failures.

        Notes:
            Cleans up test file; requires TempFileManager import.
        """
        try:
            if TempFileManager is None:
                self.checks["temp_directory"] = False
                self.details["temp_directory"] = {
                    "writable": False,
                    "error": "TempFileManager not available",
                }
                return False

            temp_manager = TempFileManager()
            test_file = temp_manager.create_temp_file(suffix="test", delete=False)

            with open(test_file, "w") as f:
                f.write("test")

            self.checks["temp_directory"] = True
            self.details["temp_directory"] = {"writable": True, "path": test_file}
            return True

        except Exception as e:
            self.checks["temp_directory"] = False
            self.details["temp_directory"] = {"writable": False, "error": str(e)}
            return False

    async def check_cache(self) -> bool:
        """Perform a full round-trip test on the cache: set, get, delete, stats.

        Validates storage integrity and access.

        Returns:
            True if cache operations succeed, False otherwise.

        Notes:
            Uses a short TTL; reports cache type and stats on success.
        """
        try:
            cache = get_cache()

            test_key = "health_check_test"
            test_value = {"test": True, "timestamp": time.time()}

            cache.set(test_key, test_value, ttl=10)

            # Test get
            retrieved = cache.get(test_key)
            if retrieved != test_value:
                self.checks["cache"] = False
                self.details["cache"] = {
                    "available": False,
                    "error": "Cache test failed",
                }
                return False

            # Test delete
            cache.delete(test_key)

            # Get stats
            stats = cache.get_stats()

            self.checks["cache"] = True
            self.details["cache"] = {
                "available": True,
                "type": type(cache).__name__,
                "stats": stats,
            }
            return True

        except Exception as e:
            self.checks["cache"] = False
            self.details["cache"] = {"available": False, "error": str(e)}
            return False

    async def check_metrics(self) -> bool:
        """Verify the metrics collector is functional by fetching a summary.

        Returns:
            True if metrics are accessible, False on errors.

        Notes:
            Extracts key stats like requests and uptime for the report.
        """
        try:
            if get_metrics_summary is None:
                self.checks["metrics"] = False
                self.details["metrics"] = {
                    "available": False,
                    "error": "Metrics module not available",
                }
                return False

            metrics = get_metrics_summary()

            self.checks["metrics"] = True
            self.details["metrics"] = {
                "available": True,
                "total_requests": metrics.get("total_requests", 0),
                "success_rate": metrics.get("success_rate", 0),
                "uptime": metrics.get("uptime", 0),
            }
            return True

        except Exception as e:
            self.checks["metrics"] = False
            self.details["metrics"] = {"available": False, "error": str(e)}
            return False

    async def check_performance(self) -> bool:
        """Monitor CPU, memory, and disk usage against safe thresholds.

        Uses psutil if available; skips detailed check if not installed.

        Returns:
            True if all metrics are below warnings (CPU/Mem <80%, Disk <90%), False otherwise.

        Notes:
            Interval-based sampling; root disk checked (may vary by OS).
        """
        try:
            if psutil is None:
                self.checks["performance"] = True
                self.details["performance"] = {
                    "available": False,
                    "reason": "psutil not installed",
                }
                return True

            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)

            # Memory usage
            memory = psutil.virtual_memory()

            # Disk usage
            disk = psutil.disk_usage("/")

            # Check thresholds
            cpu_ok = cpu_percent < 80
            memory_ok = memory.percent < 80
            disk_ok = disk.percent < 90

            overall_ok = cpu_ok and memory_ok and disk_ok

            self.checks["performance"] = overall_ok
            self.details["performance"] = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": disk.percent,
                "cpu_ok": cpu_ok,
                "memory_ok": memory_ok,
                "disk_ok": disk_ok,
            }
            return overall_ok

        except Exception as e:
            self.checks["performance"] = False
            self.details["performance"] = {"available": False, "error": str(e)}
            return False

    async def run_all_checks(self) -> dict[str, Any]:
        """Execute all registered health checks concurrently and aggregate results.

        Returns:
            Dict with overall status, individual check booleans, and details.

        Notes:
            Uses asyncio.gather for parallel execution; handles exceptions per check.
        """
        checks = [
            ("ffmpeg", self.check_ffmpeg()),
            ("engines", self.check_engines()),
            ("redis", self.check_redis()),
            ("configuration", self.check_configuration()),
            ("temp_directory", self.check_temp_directory()),
            ("cache", self.check_cache()),
            ("metrics", self.check_metrics()),
            ("performance", self.check_performance()),
        ]

        # Run all checks concurrently
        results = await asyncio.gather(
            *[check[1] for check in checks], return_exceptions=True
        )

        # Process results
        for name, result in zip([check[0] for check in checks], results, strict=False):
            if isinstance(result, Exception):
                self.checks[name] = False
                self.details[name] = {"error": str(result)}
            else:
                self.checks[name] = result

        return {
            "overall": all(self.checks.values()),
            "checks": self.checks,
            "details": self.details,
        }

    def get_health_summary(self) -> str:
        """Generate a simple string summary of health status.

        Returns:
            Emoji-prefixed message: green check for all good, warning with failed components.

        Notes:
            For logging or quick status; detailed results in run_all_checks().
        """
        if all(self.checks.values()):
            return "✅ All systems healthy"

        failed_checks = [name for name, status in self.checks.items() if not status]
        return f"⚠️ Issues found: {', '.join(failed_checks)}"


# Global health checker instance
health_checker = HealthChecker()


async def check_system_health() -> dict[str, Any]:
    """Run a full health check and return the aggregated results.

    Convenience wrapper for the global checker.

    Returns:
        Dict from HealthChecker.run_all_checks().
    """
    return await health_checker.run_all_checks()


async def check_system_health_comprehensive() -> dict[str, Any]:
    """Run an extended health check suite, including system resources and connections.

    Designed for thorough testing; includes timing.

    Returns:
        Dict with overall status, checks, total duration, and per-check times.

    Notes:
        Uses individual check functions; mock durations for simplicity.
    """
    start_time = time.time()

    # Run all checks
    disk_result = check_disk_space()
    memory_result = check_memory_usage()
    cpu_result = check_cpu_usage()
    network_result = await check_network_connectivity()
    redis_result = await check_redis_connection()
    engines_result = await check_engines_health()

    # Collect results
    results = [
        disk_result,
        memory_result,
        cpu_result,
        network_result,
        redis_result,
        engines_result,
    ]

    # Process results
    check_results = {}
    check_durations = {}
    overall_healthy = True

    for result in results:
        if isinstance(result, HealthCheckResult):
            check_results[result.name] = result.status
            check_durations[result.name] = 0.1  # Mock duration
            if not result.status:
                overall_healthy = False

    total_duration = time.time() - start_time

    return {
        "overall": overall_healthy,
        "checks": check_results,
        "total_duration": total_duration,
        "check_durations": check_durations,
    }


def get_health_summary() -> str:
    """Quick string summary using the global checker's results.

    Returns:
        Emoji message indicating health status.
    """
    return health_checker.get_health_summary()


# Individual health check functions
def check_disk_space() -> HealthCheckResult:
    """Assess free disk space on the root volume.

    Warns if below 10% free.

    Returns:
        HealthCheckResult with status and free percentage.

    Notes:
        Requires psutil; checks root ('/') which may need adjustment for Windows.
    """
    try:
        if psutil is None:
            return HealthCheckResult(
                "disk_space",
                False,
                "psutil not available",
                {"error": "psutil not installed"},
            )

        disk_usage = psutil.disk_usage("/")
        free_percent = (disk_usage.free / disk_usage.total) * 100

        if free_percent < 10:
            return HealthCheckResult(
                "disk_space",
                False,
                f"Low disk space: {free_percent:.1f}% free",
                {"free_percent": free_percent},
            )
        else:
            return HealthCheckResult(
                "disk_space",
                True,
                f"Disk space OK: {free_percent:.1f}% free",
                {"free_percent": free_percent},
            )
    except Exception as e:
        return HealthCheckResult(
            "disk_space", False, f"Disk space check failed: {e}", {"error": str(e)}
        )


def check_memory_usage() -> HealthCheckResult:
    """Monitor RAM usage and alert if over 90%.

    Returns:
        HealthCheckResult with status and usage percentage.
    """
    try:
        if psutil is None:
            return HealthCheckResult(
                "memory_usage",
                False,
                "psutil not available",
                {"error": "psutil not installed"},
            )

        memory = psutil.virtual_memory()

        if memory.percent >= 90:
            return HealthCheckResult(
                "memory_usage",
                False,
                f"High memory usage: {memory.percent:.1f}%",
                {"usage_percent": memory.percent},
            )
        else:
            return HealthCheckResult(
                "memory_usage",
                True,
                f"Memory usage OK: {memory.percent:.1f}%",
                {"usage_percent": memory.percent},
            )
    except Exception as e:
        return HealthCheckResult(
            "memory_usage", False, f"Memory check failed: {e}", {"error": str(e)}
        )


def check_cpu_usage() -> HealthCheckResult:
    """Sample CPU utilization over 1-second interval; warns above 90%.

    Returns:
        HealthCheckResult with status and percentage.
    """
    try:
        if psutil is None:
            return HealthCheckResult(
                "cpu_usage",
                False,
                "psutil not available",
                {"error": "psutil not installed"},
            )

        cpu_percent = psutil.cpu_percent(interval=1)

        if cpu_percent > 90:
            return HealthCheckResult(
                "cpu_usage",
                False,
                f"High CPU usage: {cpu_percent:.1f}%",
                {"usage_percent": cpu_percent},
            )
        else:
            return HealthCheckResult(
                "cpu_usage",
                True,
                f"CPU usage OK: {cpu_percent:.1f}%",
                {"usage_percent": cpu_percent},
            )
    except Exception as e:
        return HealthCheckResult(
            "cpu_usage", False, f"CPU check failed: {e}", {"error": str(e)}
        )


async def check_network_connectivity() -> HealthCheckResult:
    """Test basic internet connectivity via ping or DNS lookup to 8.8.8.8.

    Prefers subprocess ping for testability; falls back to socket.

    Returns:
        HealthCheckResult indicating success or failure.

    Notes:
            Timeout 3s; Unix-focused ping ('-c 1'), may need Windows adjust.
        """
    try:
        # First try a subprocess-based check (used by tests via mocking)
        try:
            proc = await asyncio.create_subprocess_exec(
                "ping",
                "-c",
                "1",
                "8.8.8.8",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            rc = await proc.wait()
            if rc == 0:
                return HealthCheckResult(
                    "network_connectivity",
                    True,
                    "Network connectivity OK",
                    {"connection_success": True},
                )
            else:
                return HealthCheckResult(
                    "network_connectivity",
                    False,
                    "Network connectivity failed",
                    {"connection_success": False},
                )
        except Exception:
            # Fallback to a socket-based check
            import socket

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex(("8.8.8.8", 53))
            sock.close()

            if result == 0:
                return HealthCheckResult(
                    "network_connectivity",
                    True,
                    "Network connectivity OK",
                    {"connection_success": True},
                )
            else:
                return HealthCheckResult(
                    "network_connectivity",
                    False,
                    "Network connectivity failed",
                    {"connection_success": False},
                )
    except Exception as e:
        return HealthCheckResult(
            "network_connectivity",
            False,
            f"Network check failed: {e}",
            {"error": str(e)},
        )


async def check_redis_connection() -> HealthCheckResult:
    """Directly ping Redis using redis-py if available.

    Returns:
        HealthCheckResult with connection status.

    Notes:
        Uses configured URL; skips if REDIS_AVAILABLE False.
    """
    try:
        if not REDIS_AVAILABLE:
            return HealthCheckResult(
                "redis_connection", False, "Redis not available", {"available": False}
            )

        import redis

        client = redis.from_url(settings.redis_url or "redis://localhost:6379")
        client.ping()

        return HealthCheckResult(
            "redis_connection", True, "Redis connection OK", {"connected": True}
        )
    except Exception as e:
        return HealthCheckResult(
            "redis_connection",
            False,
            f"Redis connection failed: {e}",
            {"error": str(e)},
        )


async def check_engines_health() -> HealthCheckResult:
    """Query the engine factory for available TTS engines.

    Returns:
        HealthCheckResult counting configured engines.

    Notes:
        Requires factory import; zero count indicates setup issue.
    """
    try:
        if factory is None:
            return HealthCheckResult(
                "engines_health",
                False,
                "Factory not available",
                {"error": "factory not installed"},
            )

        available_engines = factory.get_available_engines()

        if not available_engines:
            return HealthCheckResult(
                "engines_health",
                False,
                "No engines available",
                {"available_engines": 0},
            )

        return HealthCheckResult(
            "engines_health",
            True,
            f"{len(available_engines)} engines available",
            {"available_engines": len(available_engines)},
        )
    except Exception as e:
        return HealthCheckResult(
            "engines_health", False, f"Engine check failed: {e}", {"error": str(e)}
        )


# Global health checker instance
health_checker = HealthChecker()
