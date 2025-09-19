"""Comprehensive tests for health module."""

import asyncio
import subprocess
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ttskit.health import (
    HealthChecker,
    HealthCheckResult,
    check_cpu_usage,
    check_disk_space,
    check_engines_health,
    check_memory_usage,
    check_network_connectivity,
    check_redis_connection,
    check_system_health,
    check_system_health_comprehensive,
    get_health_summary,
    health_checker,
)


class TestHealthCheckResult:
    """Test HealthCheckResult class."""

    def test_init_with_all_params(self):
        """Test initialization with all parameters."""
        result = HealthCheckResult(
            name="test_check",
            status=True,
            message="Test passed",
            details={"key": "value"},
        )

        assert result.name == "test_check"
        assert result.status is True
        assert result.message == "Test passed"
        assert result.details == {"key": "value"}

    def test_init_without_details(self):
        """Test initialization without details."""
        result = HealthCheckResult(
            name="test_check", status=False, message="Test failed"
        )

        assert result.name == "test_check"
        assert result.status is False
        assert result.message == "Test failed"
        assert result.details == {}

    def test_to_dict(self):
        """Test to_dict method."""
        result = HealthCheckResult(
            name="test_check",
            status=True,
            message="Test passed",
            details={"key": "value"},
        )

        expected = {
            "name": "test_check",
            "status": True,
            "message": "Test passed",
            "details": {"key": "value"},
        }

        assert result.to_dict() == expected


class TestHealthChecker:
    """Test HealthChecker class."""

    def test_init(self):
        """Test HealthChecker initialization."""
        checker = HealthChecker()

        assert checker.checks == {}
        assert checker.details == {}

    @pytest.mark.asyncio
    async def test_check_ffmpeg_success(self):
        """Test successful FFmpeg check."""
        checker = HealthChecker()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "ffmpeg version 4.4.0"

            result = await checker.check_ffmpeg()

            assert result is True
            assert checker.checks["ffmpeg"] is True
            assert checker.details["ffmpeg"]["available"] is True
            assert "version" in checker.details["ffmpeg"]

    @pytest.mark.asyncio
    async def test_check_ffmpeg_failure(self):
        """Test failed FFmpeg check."""
        checker = HealthChecker()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stderr = "Command not found"

            result = await checker.check_ffmpeg()

            assert result is False
            assert checker.checks["ffmpeg"] is False
            assert checker.details["ffmpeg"]["available"] is False

    @pytest.mark.asyncio
    async def test_check_ffmpeg_file_not_found(self):
        """Test FFmpeg check when command not found."""
        checker = HealthChecker()

        with patch("subprocess.run", side_effect=FileNotFoundError()):
            result = await checker.check_ffmpeg()

            assert result is False
            assert checker.checks["ffmpeg"] is False
            assert "not found" in checker.details["ffmpeg"]["error"]

    @pytest.mark.asyncio
    async def test_check_ffmpeg_timeout(self):
        """Test FFmpeg check timeout."""
        checker = HealthChecker()

        with patch("subprocess.run", side_effect=asyncio.TimeoutError()):
            result = await checker.check_ffmpeg()

            assert result is False
            assert checker.checks["ffmpeg"] is False
            assert "timed out" in checker.details["ffmpeg"]["error"]

    @pytest.mark.asyncio
    async def test_check_engines_success(self):
        """Test successful engines check."""
        checker = HealthChecker()

        with (
            patch("ttskit.health.GTTSEngine") as mock_gtts,
            patch("ttskit.health.EDGE_AVAILABLE", True),
            patch("ttskit.health.EdgeEngine") as mock_edge,
        ):
            mock_gtts.return_value = MagicMock()
            mock_edge.return_value = MagicMock()

            result = await checker.check_engines()

            assert result is True
            assert checker.checks["engines"] is True
            assert "gtts" in checker.details["engines"]
            assert "edge" in checker.details["engines"]

    @pytest.mark.asyncio
    async def test_check_engines_gtts_failure(self):
        """Test engines check with gTTS failure."""
        checker = HealthChecker()

        with (
            patch("ttskit.health.GTTSEngine", side_effect=Exception("gTTS error")),
            patch("ttskit.health.EDGE_AVAILABLE", False),
        ):
            result = await checker.check_engines()

            assert result is False
            assert checker.checks["engines"] is False
            assert checker.details["engines"]["gtts"]["available"] is False

    @pytest.mark.asyncio
    async def test_check_redis_disabled(self):
        """Test Redis check when caching is disabled."""
        checker = HealthChecker()

        with patch("ttskit.health.settings.enable_caching", False):
            result = await checker.check_redis()

            assert result is True
            assert checker.checks["redis"] is True
            assert checker.details["redis"]["reason"] == "Caching disabled"

    @pytest.mark.asyncio
    async def test_check_redis_success(self):
        """Test successful Redis check."""
        checker = HealthChecker()

        mock_cache = MagicMock()
        mock_cache.get_stats.return_value = {"hits": 10, "misses": 5}

        with (
            patch("ttskit.health.settings.enable_caching", True),
            patch("ttskit.health.get_cache", return_value=mock_cache),
        ):
            result = await checker.check_redis()

            assert result is True
            assert checker.checks["redis"] is True
            assert checker.details["redis"]["available"] is True

    @pytest.mark.asyncio
    async def test_check_redis_failure(self):
        """Test Redis check failure."""
        checker = HealthChecker()

        with (
            patch("ttskit.health.settings.enable_caching", True),
            patch("ttskit.health.get_cache", side_effect=Exception("Redis error")),
        ):
            result = await checker.check_redis()

            assert result is False
            assert checker.checks["redis"] is False
            assert "Redis error" in checker.details["redis"]["error"]

    @pytest.mark.asyncio
    async def test_check_redis_import_error(self):
        """Test Redis check with ImportError."""
        checker = HealthChecker()

        with (
            patch("ttskit.health.settings.enable_caching", True),
            patch(
                "ttskit.health.get_cache",
                side_effect=ImportError("Redis package not installed"),
            ),
        ):
            result = await checker.check_redis()

            assert result is False
            assert checker.checks["redis"] is False
            assert "Redis package not installed" in checker.details["redis"]["error"]

    @pytest.mark.asyncio
    async def test_check_redis_with_custom_url(self):
        """Test Redis check with custom URL."""
        checker = HealthChecker()

        mock_cache = MagicMock()
        mock_cache.get_stats.return_value = {"hits": 10, "misses": 5}

        with (
            patch("ttskit.health.settings.enable_caching", True),
            patch("ttskit.health.settings.redis_url", "redis://custom:6379"),
            patch("ttskit.health.get_cache", return_value=mock_cache),
        ):
            result = await checker.check_redis()

            assert result is True
            assert checker.checks["redis"] is True
            assert checker.details["redis"]["available"] is True
            assert checker.details["redis"]["url"] == "redis://custom:6379"

    @pytest.mark.asyncio
    async def test_check_redis_with_none_url(self):
        """Test Redis check with None URL."""
        checker = HealthChecker()

        mock_cache = MagicMock()
        mock_cache.get_stats.return_value = {"hits": 10, "misses": 5}

        with (
            patch("ttskit.health.settings.enable_caching", True),
            patch("ttskit.health.settings.redis_url", None),
            patch("ttskit.health.get_cache", return_value=mock_cache),
        ):
            result = await checker.check_redis()

            assert result is True
            assert checker.checks["redis"] is True
            assert checker.details["redis"]["available"] is True
            assert checker.details["redis"]["url"] is None

    @pytest.mark.asyncio
    async def test_check_redis_cache_stats_error(self):
        """Test Redis check when cache.get_stats() fails."""
        checker = HealthChecker()

        mock_cache = MagicMock()
        mock_cache.get_stats.side_effect = Exception("Stats error")

        with (
            patch("ttskit.health.settings.enable_caching", True),
            patch("ttskit.health.get_cache", return_value=mock_cache),
        ):
            result = await checker.check_redis()

            assert result is False
            assert checker.checks["redis"] is False
            assert "Stats error" in checker.details["redis"]["error"]

    @pytest.mark.asyncio
    async def test_check_configuration_success(self):
        """Test successful configuration check."""
        checker = HealthChecker()

        with patch("ttskit.health.settings") as mock_settings:
            mock_settings.bot_token = "test_token"
            mock_settings.audio_sample_rate = 44100
            mock_settings.audio_channels = 2
            mock_settings.enable_rate_limiting = False

            result = await checker.check_configuration()

            assert result is True
            assert checker.checks["configuration"] is True
            assert checker.details["configuration"]["valid"] is True

    @pytest.mark.asyncio
    async def test_check_configuration_missing_token(self):
        """Test configuration check with missing bot token."""
        checker = HealthChecker()

        with patch("ttskit.health.settings") as mock_settings:
            mock_settings.bot_token = None

            result = await checker.check_configuration()

            assert result is False
            assert checker.checks["configuration"] is False
            assert "Bot token is required" in checker.details["configuration"]["error"]

    @pytest.mark.asyncio
    async def test_check_configuration_invalid_sample_rate(self):
        """Test configuration check with invalid sample rate."""
        checker = HealthChecker()

        with patch("ttskit.health.settings") as mock_settings:
            mock_settings.bot_token = "test_token"
            mock_settings.audio_sample_rate = 5000

            result = await checker.check_configuration()

            assert result is False
            assert checker.checks["configuration"] is False
            assert (
                "Invalid audio sample rate" in checker.details["configuration"]["error"]
            )

    @pytest.mark.asyncio
    async def test_check_configuration_invalid_channels(self):
        """Test configuration check with invalid channels."""
        checker = HealthChecker()

        with patch("ttskit.health.settings") as mock_settings:
            mock_settings.bot_token = "test_token"
            mock_settings.audio_sample_rate = 44100
            mock_settings.audio_channels = 3

            result = await checker.check_configuration()

            assert result is False
            assert checker.checks["configuration"] is False
            assert (
                "Audio channels must be 1 or 2"
                in checker.details["configuration"]["error"]
            )

    @pytest.mark.asyncio
    async def test_check_configuration_invalid_rate_limit_rpm(self):
        """Test configuration check with invalid rate limit RPM."""
        checker = HealthChecker()

        with patch("ttskit.health.settings") as mock_settings:
            mock_settings.bot_token = "test_token"
            mock_settings.audio_sample_rate = 44100
            mock_settings.audio_channels = 2
            mock_settings.enable_rate_limiting = True
            mock_settings.rate_limit_rpm = 0

            result = await checker.check_configuration()

            assert result is False
            assert checker.checks["configuration"] is False
            assert "Invalid rate limit RPM" in checker.details["configuration"]["error"]

    @pytest.mark.asyncio
    async def test_check_configuration_invalid_rate_limit_window(self):
        """Test configuration check with invalid rate limit window."""
        checker = HealthChecker()

        with patch("ttskit.health.settings") as mock_settings:
            mock_settings.bot_token = "test_token"
            mock_settings.audio_sample_rate = 44100
            mock_settings.audio_channels = 2
            mock_settings.enable_rate_limiting = True
            mock_settings.rate_limit_rpm = 60
            mock_settings.rate_limit_window = 5

            result = await checker.check_configuration()

            assert result is False
            assert checker.checks["configuration"] is False
            assert (
                "Invalid rate limit window" in checker.details["configuration"]["error"]
            )

    @pytest.mark.asyncio
    async def test_check_temp_directory_success(self):
        """Test successful temp directory check."""
        checker = HealthChecker()

        mock_temp_manager = MagicMock()
        mock_temp_manager.create_temp_file.return_value = "/tmp/test_file"

        with (
            patch("ttskit.health.TempFileManager", return_value=mock_temp_manager),
            patch("builtins.open", MagicMock()),
        ):
            result = await checker.check_temp_directory()

            assert result is True
            assert checker.checks["temp_directory"] is True
            assert checker.details["temp_directory"]["writable"] is True

    @pytest.mark.asyncio
    async def test_check_temp_directory_failure(self):
        """Test temp directory check failure."""
        checker = HealthChecker()

        with patch(
            "ttskit.health.TempFileManager", side_effect=Exception("Temp error")
        ):
            result = await checker.check_temp_directory()

            assert result is False
            assert checker.checks["temp_directory"] is False
            assert "Temp error" in checker.details["temp_directory"]["error"]

    @pytest.mark.asyncio
    async def test_check_cache_success(self):
        """Test successful cache check."""
        checker = HealthChecker()

        stored_value = None

        def mock_set(key, value, ttl=None):
            nonlocal stored_value
            stored_value = value

        def mock_get(key):
            return stored_value

        mock_cache = MagicMock()
        mock_cache.set = mock_set
        mock_cache.get = mock_get
        mock_cache.delete = MagicMock()
        mock_cache.get_stats.return_value = {"hits": 10, "misses": 5}

        with patch("ttskit.health.get_cache", return_value=mock_cache):
            result = await checker.check_cache()

            assert result is True
            assert checker.checks["cache"] is True
            assert checker.details["cache"]["available"] is True
            assert "type" in checker.details["cache"]

    @pytest.mark.asyncio
    async def test_check_cache_failure(self):
        """Test cache check failure."""
        checker = HealthChecker()

        with patch("ttskit.health.get_cache", side_effect=Exception("Cache error")):
            result = await checker.check_cache()

            assert result is False
            assert checker.checks["cache"] is False
            assert "Cache error" in checker.details["cache"]["error"]

    @pytest.mark.asyncio
    async def test_check_metrics_success(self):
        """Test successful metrics check."""
        checker = HealthChecker()

        mock_metrics = {"total_requests": 100, "success_rate": 0.95, "uptime": 3600}

        with patch("ttskit.health.get_metrics_summary", return_value=mock_metrics):
            result = await checker.check_metrics()

            assert result is True
            assert checker.checks["metrics"] is True
            assert checker.details["metrics"]["available"] is True
            assert checker.details["metrics"]["total_requests"] == 100

    @pytest.mark.asyncio
    async def test_check_metrics_failure(self):
        """Test metrics check failure."""
        checker = HealthChecker()

        with patch(
            "ttskit.health.get_metrics_summary", side_effect=Exception("Metrics error")
        ):
            result = await checker.check_metrics()

            assert result is False
            assert checker.checks["metrics"] is False
            assert "Metrics error" in checker.details["metrics"]["error"]

    @pytest.mark.asyncio
    async def test_check_performance_success(self):
        """Test successful performance check."""
        checker = HealthChecker()

        mock_psutil = MagicMock()
        mock_psutil.cpu_percent.return_value = 50.0
        mock_psutil.virtual_memory.return_value.percent = 60.0
        mock_psutil.disk_usage.return_value.percent = 70.0

        with patch("ttskit.health.psutil", mock_psutil):
            result = await checker.check_performance()

            assert result is True
            assert checker.checks["performance"] is True
            assert checker.details["performance"]["cpu_percent"] == 50.0

    @pytest.mark.asyncio
    async def test_check_performance_high_cpu(self):
        """Test performance check with high CPU usage."""
        checker = HealthChecker()

        mock_psutil = MagicMock()
        mock_psutil.cpu_percent.return_value = 85.0
        mock_psutil.virtual_memory.return_value.percent = 60.0
        mock_psutil.disk_usage.return_value.percent = 70.0

        with patch("ttskit.health.psutil", mock_psutil):
            result = await checker.check_performance()

            assert result is False
            assert checker.checks["performance"] is False
            assert checker.details["performance"]["cpu_ok"] is False

    @pytest.mark.asyncio
    async def test_check_performance_psutil_not_installed(self):
        """Test performance check when psutil is not installed."""
        checker = HealthChecker()

        with patch("ttskit.health.psutil", None):
            result = await checker.check_performance()

            assert result is True
            assert checker.checks["performance"] is True
            assert checker.details["performance"]["reason"] == "psutil not installed"

    @pytest.mark.asyncio
    async def test_run_all_checks_success(self):
        """Test running all checks successfully."""
        checker = HealthChecker()

        async def mock_check():
            return True

        checker.check_ffmpeg = mock_check
        checker.check_engines = mock_check
        checker.check_redis = mock_check
        checker.check_configuration = mock_check
        checker.check_temp_directory = mock_check
        checker.check_cache = mock_check
        checker.check_metrics = mock_check
        checker.check_performance = mock_check

        result = await checker.run_all_checks()

        assert result["overall"] is True
        assert all(result["checks"].values())
        assert len(result["checks"]) == 8

    @pytest.mark.asyncio
    async def test_run_all_checks_with_failures(self):
        """Test running all checks with some failures."""
        checker = HealthChecker()

        async def mock_check_success():
            return True

        async def mock_check_failure():
            return False

        checker.check_ffmpeg = mock_check_success
        checker.check_engines = mock_check_failure
        checker.check_redis = mock_check_success
        checker.check_configuration = mock_check_success
        checker.check_temp_directory = mock_check_success
        checker.check_cache = mock_check_success
        checker.check_metrics = mock_check_success
        checker.check_performance = mock_check_success

        result = await checker.run_all_checks()

        assert result["overall"] is False
        assert result["checks"]["ffmpeg"] is True
        assert result["checks"]["engines"] is False

    def test_get_health_summary_all_healthy(self):
        """Test health summary when all checks pass."""
        checker = HealthChecker()
        checker.checks = {
            "ffmpeg": True,
            "engines": True,
            "redis": True,
            "configuration": True,
            "temp_directory": True,
            "cache": True,
            "metrics": True,
            "performance": True,
        }

        summary = checker.get_health_summary()
        assert "✅ All systems healthy" in summary

    def test_get_health_summary_with_failures(self):
        """Test health summary when some checks fail."""
        checker = HealthChecker()
        checker.checks = {
            "ffmpeg": True,
            "engines": False,
            "redis": True,
            "configuration": False,
            "temp_directory": True,
            "cache": True,
            "metrics": True,
            "performance": True,
        }

        summary = checker.get_health_summary()
        assert "⚠️ Issues found" in summary
        assert "engines" in summary
        assert "configuration" in summary


class TestStandaloneHealthFunctions:
    """Test standalone health check functions."""

    def test_check_disk_space_success(self):
        """Test successful disk space check."""
        mock_psutil = MagicMock()
        mock_psutil.disk_usage.return_value.free = 1000000000
        mock_psutil.disk_usage.return_value.total = 10000000000

        with patch("ttskit.health.psutil", mock_psutil):
            result = check_disk_space()

            assert isinstance(result, HealthCheckResult)
            assert result.name == "disk_space"
            assert result.status is True
            assert "OK" in result.message

    def test_check_disk_space_low_space(self):
        """Test disk space check with low space."""
        mock_psutil = MagicMock()
        mock_psutil.disk_usage.return_value.free = 50000000
        mock_psutil.disk_usage.return_value.total = 1000000000

        with patch("ttskit.health.psutil", mock_psutil):
            result = check_disk_space()

            assert isinstance(result, HealthCheckResult)
            assert result.name == "disk_space"
            assert result.status is False
            assert "Low disk space" in result.message

    def test_check_disk_space_exception(self):
        """Test disk space check with exception."""
        with patch("ttskit.health.psutil", side_effect=Exception("Disk error")):
            result = check_disk_space()

            assert isinstance(result, HealthCheckResult)
            assert result.name == "disk_space"
            assert result.status is False
            assert "Disk space check failed" in result.message

    def test_check_memory_usage_success(self):
        """Test successful memory usage check."""
        mock_psutil = MagicMock()
        mock_psutil.virtual_memory.return_value.percent = 50.0

        with patch("ttskit.health.psutil", mock_psutil):
            result = check_memory_usage()

            assert isinstance(result, HealthCheckResult)
            assert result.name == "memory_usage"
            assert result.status is True
            assert "OK" in result.message

    def test_check_memory_usage_high_usage(self):
        """Test memory usage check with high usage."""
        mock_psutil = MagicMock()
        mock_psutil.virtual_memory.return_value.percent = 95.0

        with patch("ttskit.health.psutil", mock_psutil):
            result = check_memory_usage()

            assert isinstance(result, HealthCheckResult)
            assert result.name == "memory_usage"
            assert result.status is False
            assert "High memory usage" in result.message

    def test_check_cpu_usage_success(self):
        """Test successful CPU usage check."""
        mock_psutil = MagicMock()
        mock_psutil.cpu_percent.return_value = 50.0

        with patch("ttskit.health.psutil", mock_psutil):
            result = check_cpu_usage()

            assert isinstance(result, HealthCheckResult)
            assert result.name == "cpu_usage"
            assert result.status is True
            assert "OK" in result.message

    def test_check_cpu_usage_high_usage(self):
        """Test CPU usage check with high usage."""
        mock_psutil = MagicMock()
        mock_psutil.cpu_percent.return_value = 95.0

        with patch("ttskit.health.psutil", mock_psutil):
            result = check_cpu_usage()

            assert isinstance(result, HealthCheckResult)
            assert result.name == "cpu_usage"
            assert result.status is False
            assert "High CPU usage" in result.message

    @pytest.mark.asyncio
    async def test_check_network_connectivity_success(self):
        """Test successful network connectivity check."""
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.wait = AsyncMock(return_value=0)

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await check_network_connectivity()

            assert isinstance(result, HealthCheckResult)
            assert result.name == "network_connectivity"
            assert result.status is True
            assert "OK" in result.message

    @pytest.mark.asyncio
    async def test_check_network_connectivity_failure(self):
        """Test network connectivity check failure."""
        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.wait = AsyncMock(return_value=1)

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await check_network_connectivity()

            assert isinstance(result, HealthCheckResult)
            assert result.name == "network_connectivity"
            assert result.status is False
            assert "failed" in result.message

    @pytest.mark.asyncio
    async def test_check_redis_connection_success(self):
        """Test successful Redis connection check."""
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True

        with (
            patch("ttskit.health.REDIS_AVAILABLE", True),
            patch("redis.from_url", return_value=mock_redis),
        ):
            result = await check_redis_connection()

            assert isinstance(result, HealthCheckResult)
            assert result.name == "redis_connection"
            assert result.status is True
            assert "OK" in result.message

    @pytest.mark.asyncio
    async def test_check_redis_connection_not_available(self):
        """Test Redis connection check when Redis is not available."""
        with patch("ttskit.health.REDIS_AVAILABLE", False):
            result = await check_redis_connection()

            assert isinstance(result, HealthCheckResult)
            assert result.name == "redis_connection"
            assert result.status is False
            assert "not available" in result.message

    @pytest.mark.asyncio
    async def test_check_redis_connection_failure(self):
        """Test Redis connection check with connection failure."""
        mock_redis = MagicMock()
        mock_redis.ping.side_effect = Exception("Connection failed")

        with (
            patch("ttskit.health.REDIS_AVAILABLE", True),
            patch("redis.from_url", return_value=mock_redis),
        ):
            result = await check_redis_connection()

            assert isinstance(result, HealthCheckResult)
            assert result.name == "redis_connection"
            assert result.status is False
            assert "failed" in result.message
            assert "Connection failed" in result.details["error"]

    @pytest.mark.asyncio
    async def test_check_redis_connection_with_custom_url(self):
        """Test Redis connection check with custom URL."""
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True

        with (
            patch("ttskit.health.REDIS_AVAILABLE", True),
            patch("ttskit.health.settings.redis_url", "redis://custom:6379"),
            patch("redis.from_url", return_value=mock_redis) as mock_from_url,
        ):
            result = await check_redis_connection()

            assert isinstance(result, HealthCheckResult)
            assert result.status is True
            mock_from_url.assert_called_once_with("redis://custom:6379")

    @pytest.mark.asyncio
    async def test_check_redis_connection_with_default_url(self):
        """Test Redis connection check with default URL."""
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True

        with (
            patch("ttskit.health.REDIS_AVAILABLE", True),
            patch("ttskit.health.settings.redis_url", None),
            patch("redis.from_url", return_value=mock_redis) as mock_from_url,
        ):
            result = await check_redis_connection()

            assert isinstance(result, HealthCheckResult)
            assert result.status is True
            mock_from_url.assert_called_once_with("redis://localhost:6379")

    @pytest.mark.asyncio
    async def test_check_redis_connection_import_error(self):
        """Test Redis connection check with import error."""
        with (
            patch("ttskit.health.REDIS_AVAILABLE", True),
            patch("redis.from_url", side_effect=ImportError("Redis not installed")),
        ):
            result = await check_redis_connection()

            assert isinstance(result, HealthCheckResult)
            assert result.name == "redis_connection"
            assert result.status is False
            assert "failed" in result.message
            assert "Redis not installed" in result.details["error"]

    @pytest.mark.asyncio
    async def test_check_engines_health_success(self):
        """Test successful engines health check."""
        mock_factory = MagicMock()
        mock_factory.get_available_engines.return_value = ["gtts", "edge"]

        with patch("ttskit.health.factory", mock_factory):
            result = await check_engines_health()

            assert isinstance(result, HealthCheckResult)
            assert result.name == "engines_health"
            assert result.status is True
            assert "2 engines available" in result.message

    @pytest.mark.asyncio
    async def test_check_engines_health_no_engines(self):
        """Test engines health check with no engines."""
        mock_factory = MagicMock()
        mock_factory.get_available_engines.return_value = []

        with patch("ttskit.health.factory", mock_factory):
            result = await check_engines_health()

            assert isinstance(result, HealthCheckResult)
            assert result.name == "engines_health"
            assert result.status is False
            assert "No engines available" in result.message


class TestGlobalHealthFunctions:
    """Test global health functions."""

    @pytest.mark.asyncio
    async def test_check_system_health(self):
        """Test check_system_health function."""
        with patch.object(
            health_checker, "run_all_checks", return_value={"overall": True}
        ):
            result = await check_system_health()

            assert result["overall"] is True

    @pytest.mark.asyncio
    async def test_check_system_health_comprehensive(self):
        """Test comprehensive system health check."""
        with (
            patch("ttskit.health.check_disk_space") as mock_disk,
            patch("ttskit.health.check_memory_usage") as mock_memory,
            patch("ttskit.health.check_cpu_usage") as mock_cpu,
            patch("ttskit.health.check_network_connectivity") as mock_network,
            patch("ttskit.health.check_redis_connection") as mock_redis,
            patch("ttskit.health.check_engines_health") as mock_engines,
        ):
            mock_result = HealthCheckResult("test", True, "OK")
            mock_disk.return_value = mock_result
            mock_memory.return_value = mock_result
            mock_cpu.return_value = mock_result
            mock_network.return_value = mock_result
            mock_redis.return_value = mock_result
            mock_engines.return_value = mock_result

            result = await check_system_health_comprehensive()

            assert result["overall"] is True
            assert "total_duration" in result
            assert "check_durations" in result

    def test_get_health_summary(self):
        """Test get_health_summary function."""
        with patch.object(
            health_checker, "get_health_summary", return_value="✅ All systems healthy"
        ):
            result = get_health_summary()

            assert result == "✅ All systems healthy"

    @pytest.mark.asyncio
    async def test_check_ffmpeg_subprocess_timeout(self):
        """Test FFmpeg check with subprocess timeout."""
        checker = HealthChecker()

        with patch(
            "subprocess.run", side_effect=subprocess.TimeoutExpired("ffmpeg", 10)
        ):
            result = await checker.check_ffmpeg()

            assert result is False
            assert checker.checks["ffmpeg"] is False
            assert "timed out" in checker.details["ffmpeg"]["error"]

    @pytest.mark.asyncio
    async def test_check_ffmpeg_general_exception(self):
        """Test FFmpeg check with general exception."""
        checker = HealthChecker()

        with patch("subprocess.run", side_effect=Exception("General error")):
            result = await checker.check_ffmpeg()

            assert result is False
            assert checker.checks["ffmpeg"] is False
            assert "General error" in checker.details["ffmpeg"]["error"]

    @pytest.mark.asyncio
    async def test_check_engines_edge_available_false(self):
        """Test engines check when Edge is not available."""
        checker = HealthChecker()

        with (
            patch("ttskit.health.GTTSEngine") as mock_gtts,
            patch("ttskit.health.EDGE_AVAILABLE", False),
            patch("ttskit.health.EdgeEngine", None),
        ):
            mock_gtts.return_value = MagicMock()

            result = await checker.check_engines()

            assert result is False  # No engines available (Edge not available)
            assert checker.checks["engines"] is False
            assert "gtts" in checker.details["engines"]
            assert "edge" in checker.details["engines"]
            assert checker.details["engines"]["edge"]["available"] is False

    @pytest.mark.asyncio
    async def test_check_engines_edge_failure(self):
        """Test engines check with Edge engine failure."""
        checker = HealthChecker()

        with (
            patch("ttskit.health.GTTSEngine") as mock_gtts,
            patch("ttskit.health.EDGE_AVAILABLE", True),
            patch("ttskit.health.EdgeEngine") as mock_edge,
        ):
            mock_gtts.return_value = MagicMock()
            mock_edge.side_effect = Exception("Edge error")

            result = await checker.check_engines()

            assert result is False
            assert checker.checks["engines"] is False
            assert checker.details["engines"]["edge"]["available"] is False
            assert "Edge error" in checker.details["engines"]["edge"]["error"]

    @pytest.mark.asyncio
    async def test_check_temp_directory_temp_manager_none(self):
        """Test temp directory check when TempFileManager is None."""
        checker = HealthChecker()

        with patch("ttskit.health.TempFileManager", None):
            result = await checker.check_temp_directory()

            assert result is False
            assert checker.checks["temp_directory"] is False
            assert "not available" in checker.details["temp_directory"]["error"]

    @pytest.mark.asyncio
    async def test_check_temp_directory_file_write_error(self):
        """Test temp directory check with file write error."""
        checker = HealthChecker()

        mock_temp_manager = MagicMock()
        mock_temp_manager.create_temp_file.return_value = "/tmp/test_file"

        with (
            patch("ttskit.health.TempFileManager", return_value=mock_temp_manager),
            patch("builtins.open", side_effect=PermissionError("Permission denied")),
        ):
            result = await checker.check_temp_directory()

            assert result is False
            assert checker.checks["temp_directory"] is False
            assert "Permission denied" in checker.details["temp_directory"]["error"]

    @pytest.mark.asyncio
    async def test_check_metrics_none(self):
        """Test metrics check when get_metrics_summary is None."""
        checker = HealthChecker()

        with patch("ttskit.health.get_metrics_summary", None):
            result = await checker.check_metrics()

            assert result is False
            assert checker.checks["metrics"] is False
            assert "not available" in checker.details["metrics"]["error"]

    @pytest.mark.asyncio
    async def test_check_performance_exception(self):
        """Test performance check with exception."""
        checker = HealthChecker()

        mock_psutil = MagicMock()
        mock_psutil.cpu_percent.side_effect = Exception("CPU error")

        with patch("ttskit.health.psutil", mock_psutil):
            result = await checker.check_performance()

            assert result is False
            assert checker.checks["performance"] is False
            assert "CPU error" in checker.details["performance"]["error"]

    @pytest.mark.asyncio
    async def test_run_all_checks_with_exceptions(self):
        """Test running all checks with exceptions."""
        checker = HealthChecker()

        async def mock_check_exception():
            raise Exception("Check failed")

        checker.check_ffmpeg = mock_check_exception
        checker.check_engines = mock_check_exception
        checker.check_redis = mock_check_exception
        checker.check_configuration = mock_check_exception
        checker.check_temp_directory = mock_check_exception
        checker.check_cache = mock_check_exception
        checker.check_metrics = mock_check_exception
        checker.check_performance = mock_check_exception

        result = await checker.run_all_checks()

        assert result["overall"] is False
        assert all(not status for status in result["checks"].values())
        assert all(
            "Check failed" in details["error"] for details in result["details"].values()
        )

    def test_check_disk_space_psutil_none(self):
        """Test disk space check when psutil is None."""
        with patch("ttskit.health.psutil", None):
            result = check_disk_space()

            assert isinstance(result, HealthCheckResult)
            assert result.name == "disk_space"
            assert result.status is False
            assert "psutil not available" in result.message

    def test_check_memory_usage_psutil_none(self):
        """Test memory usage check when psutil is None."""
        with patch("ttskit.health.psutil", None):
            result = check_memory_usage()

            assert isinstance(result, HealthCheckResult)
            assert result.name == "memory_usage"
            assert result.status is False
            assert "psutil not available" in result.message

    def test_check_cpu_usage_psutil_none(self):
        """Test CPU usage check when psutil is None."""
        with patch("ttskit.health.psutil", None):
            result = check_cpu_usage()

            assert isinstance(result, HealthCheckResult)
            assert result.name == "cpu_usage"
            assert result.status is False
            assert "psutil not available" in result.message

    @pytest.mark.asyncio
    async def test_check_network_connectivity_socket_fallback_success(self):
        """Test network connectivity with socket fallback success."""
        with patch("asyncio.create_subprocess_exec", side_effect=Exception("No ping")):
            with patch("socket.socket") as mock_socket:
                mock_sock = MagicMock()
                mock_sock.connect_ex.return_value = 0
                mock_socket.return_value = mock_sock

                result = await check_network_connectivity()

                assert isinstance(result, HealthCheckResult)
                assert result.name == "network_connectivity"
                assert result.status is True
                assert "OK" in result.message

    @pytest.mark.asyncio
    async def test_check_network_connectivity_socket_fallback_failure(self):
        """Test network connectivity with socket fallback failure."""
        with patch("asyncio.create_subprocess_exec", side_effect=Exception("No ping")):
            with patch("socket.socket") as mock_socket:
                mock_sock = MagicMock()
                mock_sock.connect_ex.return_value = 1
                mock_socket.return_value = mock_sock

                result = await check_network_connectivity()

                assert isinstance(result, HealthCheckResult)
                assert result.name == "network_connectivity"
                assert result.status is False
                assert "failed" in result.message

    @pytest.mark.asyncio
    async def test_check_network_connectivity_general_exception(self):
        """Test network connectivity with general exception."""
        with patch(
            "asyncio.create_subprocess_exec", side_effect=Exception("Network error")
        ):
            with patch("socket.socket", side_effect=Exception("Socket error")):
                result = await check_network_connectivity()

                assert isinstance(result, HealthCheckResult)
                assert result.name == "network_connectivity"
                assert result.status is False
                assert "Socket error" in result.message

    @pytest.mark.asyncio
    async def test_check_engines_health_factory_none(self):
        """Test engines health check when factory is None."""
        with patch("ttskit.health.factory", None):
            result = await check_engines_health()

            assert isinstance(result, HealthCheckResult)
            assert result.name == "engines_health"
            assert result.status is False
            assert "Factory not available" in result.message

    @pytest.mark.asyncio
    async def test_check_engines_health_exception(self):
        """Test engines health check with exception."""
        mock_factory = MagicMock()
        mock_factory.get_available_engines.side_effect = Exception("Factory error")

        with patch("ttskit.health.factory", mock_factory):
            result = await check_engines_health()

            assert isinstance(result, HealthCheckResult)
            assert result.name == "engines_health"
            assert result.status is False
            assert "Factory error" in result.message
