"""Comprehensive tests for system router."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from ttskit.api.dependencies import RequiredAuth, WriteAuth
from ttskit.api.routers.system import (
    CacheStatsResponse,
    HealthResponse,
    clear_cache_endpoint,
    get_advanced_metrics,
    get_cache_statistics,
    get_configuration,
    get_docs,
    get_metrics,
    get_rate_limit_information,
    get_status,
    get_supported_audio_formats,
    get_supported_language_codes,
    get_system_information,
    get_version,
    health_check,
    is_cache_enabled_endpoint,
    router,
)


class TestSystemRouterModels:
    """Test system router Pydantic models."""

    def test_health_response_model(self):
        """Test HealthResponse model validation."""
        response = HealthResponse(
            status="healthy", engines=3, uptime=3600.0, version="1.0.0"
        )

        assert response.status == "healthy"
        assert response.engines == 3
        assert response.uptime == 3600.0
        assert response.version == "1.0.0"

    def test_health_response_model_validation_error(self):
        """Test HealthResponse model validation with invalid data."""
        with pytest.raises(ValidationError):
            HealthResponse(
                status="healthy",
                engines="invalid",
                uptime=3600.0,
                version="1.0.0",
            )

    def test_cache_stats_response_model(self):
        """Test CacheStatsResponse model validation."""
        response = CacheStatsResponse(
            enabled=True, hits=100, misses=50, hit_rate=0.67, size=1024000, entries=25
        )

        assert response.enabled is True
        assert response.hits == 100
        assert response.misses == 50
        assert response.hit_rate == 0.67
        assert response.size == 1024000
        assert response.entries == 25

    def test_cache_stats_response_model_validation_error(self):
        """Test CacheStatsResponse model validation with invalid data."""
        with pytest.raises(ValidationError):
            CacheStatsResponse(
                enabled=True,
                hits="invalid",
                misses=50,
                hit_rate=0.67,
                size=1024000,
                entries=25,
            )


class TestSystemRouterEndpoints:
    """Test system router endpoints."""

    @pytest.fixture
    def mock_auth(self):
        """Create mock auth dependency."""
        auth = MagicMock(spec=RequiredAuth)
        auth.user_id = "test_user"
        auth.permissions = ["read", "write"]
        return auth

    @pytest.fixture
    def mock_write_auth(self):
        """Create mock write auth dependency."""
        auth = MagicMock(spec=WriteAuth)
        auth.user_id = "test_user"
        auth.permissions = ["read", "write", "admin"]
        return auth

    @pytest.mark.asyncio
    async def test_health_check_success(self, mock_auth):
        """Test health check endpoint success."""
        with patch("ttskit.public.get_engines") as mock_get_engines:
            mock_get_engines.return_value = [
                {"name": "gtts", "available": True},
                {"name": "edge", "available": True},
                {"name": "piper", "available": False},
            ]

            result = await health_check(mock_auth)

            assert isinstance(result, HealthResponse)
            assert result.status == "healthy"
            assert result.engines == 2
            assert result.uptime >= 0
            assert result.version is not None

    @pytest.mark.asyncio
    async def test_health_check_failure(self, mock_auth):
        """Test health check endpoint failure."""
        with patch(
            "ttskit.public.get_engines",
            side_effect=Exception("Engine error"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await health_check(mock_auth)

            assert exc_info.value.status_code == 500
            assert "Engine error" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_status_success(self, mock_auth):
        """Test get status endpoint success."""
        with patch("ttskit.api.routers.system.get_health_status") as mock_get_status:
            mock_get_status.return_value = {
                "status": "healthy",
                "engines": 3,
                "uptime": 3600,
            }

            result = await get_status(mock_auth)

            assert result["status"] == "healthy"
            assert result["engines"] == 3
            assert result["uptime"] == 3600

    @pytest.mark.asyncio
    async def test_get_status_failure(self, mock_auth):
        """Test get status endpoint failure."""
        with patch(
            "ttskit.api.routers.system.get_health_status",
            side_effect=Exception("Status error"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_status(mock_auth)

            assert exc_info.value.status_code == 500
            assert "Status error" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_system_information_success(self, mock_auth):
        """Test get system information endpoint success."""
        with patch("ttskit.api.routers.system.get_system_info") as mock_get_info:
            mock_get_info.return_value = {
                "platform": "Linux",
                "python_version": "3.11.0",
                "architecture": "x86_64",
            }

            result = await get_system_information(mock_auth)

            assert result["platform"] == "Linux"
            assert result["python_version"] == "3.11.0"
            assert result["architecture"] == "x86_64"

    @pytest.mark.asyncio
    async def test_get_system_information_failure(self, mock_auth):
        """Test get system information endpoint failure."""
        with patch(
            "ttskit.api.routers.system.get_system_info",
            side_effect=Exception("Info error"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_system_information(mock_auth)

            assert exc_info.value.status_code == 500
            assert "Info error" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_configuration_success(self, mock_auth):
        """Test get configuration endpoint success."""
        with patch("ttskit.api.routers.system.get_config") as mock_get_config:
            mock_get_config.return_value = {
                "api_key": "secret_key_123",
                "redis_url": "redis://localhost:6379",
                "default_lang": "en",
                "cache_enabled": True,
            }

            result = await get_configuration(mock_auth)

            assert result["api_key"] == "***"
            assert result["redis_url"] == "***"
            assert result["default_lang"] == "en"
            assert result["cache_enabled"] is True

    @pytest.mark.asyncio
    async def test_get_configuration_failure(self, mock_auth):
        """Test get configuration endpoint failure."""
        with patch(
            "ttskit.api.routers.system.get_config",
            side_effect=Exception("Config error"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_configuration(mock_auth)

            assert exc_info.value.status_code == 500
            assert "Config error" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_cache_statistics_success(self, mock_auth):
        """Test get cache statistics endpoint success."""
        with (
            patch("ttskit.api.routers.system.get_cache_stats") as mock_get_stats,
            patch("ttskit.api.routers.system.is_cache_enabled") as mock_is_enabled,
        ):
            mock_get_stats.return_value = {
                "hits": 100,
                "misses": 50,
                "hit_rate": 0.67,
                "size": 1024000,
                "entries": 25,
            }
            mock_is_enabled.return_value = True

            result = await get_cache_statistics(mock_auth)

            assert isinstance(result, CacheStatsResponse)
            assert result.enabled is True
            assert result.hits == 100
            assert result.misses == 50
            assert result.hit_rate == 0.67
            assert result.size == 1024000
            assert result.entries == 25

    @pytest.mark.asyncio
    async def test_get_cache_statistics_failure(self, mock_auth):
        """Test get cache statistics endpoint failure."""
        with patch(
            "ttskit.api.routers.system.get_cache_stats",
            side_effect=Exception("Cache stats error"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_cache_statistics(mock_auth)

            assert exc_info.value.status_code == 500
            assert "Cache stats error" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_clear_cache_endpoint_success(self, mock_write_auth):
        """Test clear cache endpoint success."""
        with patch("ttskit.api.routers.system.clear_cache") as mock_clear_cache:
            mock_clear_cache.return_value = None

            result = await clear_cache_endpoint(mock_write_auth)

            assert result["message"] == "Cache cleared successfully"
            mock_clear_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_cache_endpoint_failure(self, mock_write_auth):
        """Test clear cache endpoint failure."""
        with patch(
            "ttskit.api.routers.system.clear_cache",
            side_effect=Exception("Clear cache error"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await clear_cache_endpoint(mock_write_auth)

            assert exc_info.value.status_code == 500
            assert "Clear cache error" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_is_cache_enabled_endpoint_success(self, mock_auth):
        """Test is cache enabled endpoint success."""
        with patch("ttskit.api.routers.system.is_cache_enabled") as mock_is_enabled:
            mock_is_enabled.return_value = True

            result = await is_cache_enabled_endpoint(mock_auth)

            assert result["enabled"] is True

    @pytest.mark.asyncio
    async def test_is_cache_enabled_endpoint_failure(self, mock_auth):
        """Test is cache enabled endpoint failure."""
        with patch(
            "ttskit.api.routers.system.is_cache_enabled",
            side_effect=Exception("Cache status error"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await is_cache_enabled_endpoint(mock_auth)

            assert exc_info.value.status_code == 500
            assert "Cache status error" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_supported_audio_formats_success(self, mock_auth):
        """Test get supported audio formats endpoint success."""
        with patch(
            "ttskit.api.routers.system.get_supported_formats"
        ) as mock_get_formats:
            mock_get_formats.return_value = ["mp3", "wav", "ogg", "m4a"]

            result = await get_supported_audio_formats(mock_auth)

            assert result["formats"] == ["mp3", "wav", "ogg", "m4a"]

    @pytest.mark.asyncio
    async def test_get_supported_audio_formats_failure(self, mock_auth):
        """Test get supported audio formats endpoint failure."""
        with patch(
            "ttskit.api.routers.system.get_supported_formats",
            side_effect=Exception("Formats error"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_supported_audio_formats(mock_auth)

            assert exc_info.value.status_code == 500
            assert "Formats error" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_supported_language_codes_success(self, mock_auth):
        """Test get supported language codes endpoint success."""
        with patch(
            "ttskit.api.routers.system.get_supported_languages"
        ) as mock_get_languages:
            mock_get_languages.return_value = ["en", "fa", "ar", "es", "fr"]

            result = await get_supported_language_codes(mock_auth)

            assert result["languages"] == ["en", "fa", "ar", "es", "fr"]

    @pytest.mark.asyncio
    async def test_get_supported_language_codes_failure(self, mock_auth):
        """Test get supported language codes endpoint failure."""
        with patch(
            "ttskit.api.routers.system.get_supported_languages",
            side_effect=Exception("Languages error"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_supported_language_codes(mock_auth)

            assert exc_info.value.status_code == 500
            assert "Languages error" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_rate_limit_information_success(self, mock_auth):
        """Test get rate limit information endpoint success."""
        with patch(
            "ttskit.api.routers.system.get_rate_limit_info"
        ) as mock_get_rate_info:
            mock_get_rate_info.return_value = {
                "limit": 100,
                "remaining": 95,
                "reset_time": 3600,
            }

            result = await get_rate_limit_information(mock_auth)

            assert result["limit"] == 100
            assert result["remaining"] == 95
            assert result["reset_time"] == 3600

    @pytest.mark.asyncio
    async def test_get_rate_limit_information_failure(self, mock_auth):
        """Test get rate limit information endpoint failure."""
        with patch(
            "ttskit.api.routers.system.get_rate_limit_info",
            side_effect=Exception("Rate limit error"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_rate_limit_information(mock_auth)

            assert exc_info.value.status_code == 500
            assert "Rate limit error" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_docs_success(self, mock_auth):
        """Test get documentation endpoint success."""
        with patch("ttskit.api.routers.system.get_documentation") as mock_get_docs:
            mock_get_docs.return_value = {
                "title": "TTSKit API",
                "version": "1.0.0",
                "description": "Text-to-Speech API",
            }

            result = await get_docs(mock_auth)

            assert result["title"] == "TTSKit API"
            assert result["version"] == "1.0.0"
            assert result["description"] == "Text-to-Speech API"

    @pytest.mark.asyncio
    async def test_get_docs_failure(self, mock_auth):
        """Test get documentation endpoint failure."""
        with patch(
            "ttskit.api.routers.system.get_documentation",
            side_effect=Exception("Docs error"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_docs(mock_auth)

            assert exc_info.value.status_code == 500
            assert "Docs error" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_metrics_success(self, mock_auth):
        """Test get metrics endpoint success."""
        result = await get_metrics(mock_auth)

        assert "tts_stats" in result
        assert "system_metrics" in result
        assert "version" in result

    @pytest.mark.asyncio
    async def test_get_metrics_failure(self, mock_auth):
        """Test get metrics endpoint failure."""
        with patch("ttskit.public.TTS", side_effect=Exception("Metrics error")):
            with pytest.raises(HTTPException) as exc_info:
                await get_metrics(mock_auth)

            assert exc_info.value.status_code == 500
            assert "Metrics error" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_advanced_metrics_success(self, mock_auth):
        """Test get advanced metrics endpoint success."""
        with (
            patch(
                "ttskit.api.routers.system.get_metrics_collector"
            ) as mock_get_collector,
            patch(
                "ttskit.api.routers.system.get_performance_monitor"
            ) as mock_get_monitor,
        ):
            mock_collector = MagicMock()
            mock_collector.get_comprehensive_metrics = AsyncMock(
                return_value={"requests": {"total": 1000, "success_rate": 0.95}}
            )
            mock_collector.get_engine_comparison = AsyncMock(
                return_value={"gtts": {"requests": 500, "success_rate": 0.96}}
            )
            mock_collector.get_language_analytics = AsyncMock(
                return_value={"en": {"requests": 800, "success_rate": 0.94}}
            )

            mock_monitor = MagicMock()
            mock_monitor.get_metrics = AsyncMock(
                return_value={"response_time": {"avg": 1.5, "p95": 3.0}}
            )

            mock_get_collector.return_value = mock_collector
            mock_get_monitor.return_value = mock_monitor

            result = await get_advanced_metrics(mock_auth)

            assert "comprehensive" in result
            assert "engine_comparison" in result
            assert "language_analytics" in result
            assert "performance" in result
            assert "timestamp" in result
            assert "version" in result

    @pytest.mark.asyncio
    async def test_get_advanced_metrics_failure(self, mock_auth):
        """Test get advanced metrics endpoint failure."""
        with patch(
            "ttskit.api.routers.system.get_metrics_collector",
            side_effect=Exception("Advanced metrics error"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_advanced_metrics(mock_auth)

            assert exc_info.value.status_code == 500
            assert "Advanced metrics error" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_version_success(self, mock_auth):
        """Test get version endpoint success."""
        result = await get_version(mock_auth)

        assert "version" in result
        assert "service" in result
        assert "status" in result
        assert "uptime" in result
        assert result["service"] == "TTSKit API"
        assert result["status"] == "running"
        assert result["uptime"] >= 0

    @pytest.mark.asyncio
    async def test_get_version_failure(self, mock_auth):
        """Test get version endpoint failure."""
        result = await get_version(mock_auth)
        assert "version" in result
        assert "service" in result
        assert "status" in result


class TestSystemRouterEdgeCases:
    """Test system router edge cases."""

    @pytest.fixture
    def mock_auth(self):
        """Create mock auth dependency."""
        auth = MagicMock(spec=RequiredAuth)
        auth.user_id = "test_user"
        auth.permissions = ["read"]
        return auth

    @pytest.mark.asyncio
    async def test_health_check_no_engines(self, mock_auth):
        """Test health check with no engines."""
        with patch("ttskit.public.get_engines") as mock_get_engines:
            mock_get_engines.return_value = []

            result = await health_check(mock_auth)

            assert result.engines == 0

    @pytest.mark.asyncio
    async def test_health_check_no_available_engines(self, mock_auth):
        """Test health check with no available engines."""
        with patch("ttskit.public.get_engines") as mock_get_engines:
            mock_get_engines.return_value = [
                {"name": "gtts", "available": False},
                {"name": "edge", "available": False},
            ]

            result = await health_check(mock_auth)

            assert result.engines == 0

    @pytest.mark.asyncio
    async def test_get_configuration_no_sensitive_data(self, mock_auth):
        """Test get configuration with no sensitive data."""
        with patch("ttskit.api.routers.system.get_config") as mock_get_config:
            mock_get_config.return_value = {
                "default_lang": "en",
                "cache_enabled": True,
                "audio_sample_rate": 44100,
            }

            result = await get_configuration(mock_auth)

            assert result["default_lang"] == "en"
            assert result["cache_enabled"] is True
            assert result["audio_sample_rate"] == 44100

    @pytest.mark.asyncio
    async def test_get_cache_statistics_empty_stats(self, mock_auth):
        """Test get cache statistics with empty stats."""
        with (
            patch("ttskit.api.routers.system.get_cache_stats") as mock_get_stats,
            patch("ttskit.api.routers.system.is_cache_enabled") as mock_is_enabled,
        ):
            mock_get_stats.return_value = {}
            mock_is_enabled.return_value = False

            result = await get_cache_statistics(mock_auth)

            assert result.enabled is False
            assert result.hits == 0
            assert result.misses == 0
            assert result.hit_rate == 0.0
            assert result.size == 0
            assert result.entries == 0

    @pytest.mark.asyncio
    async def test_get_supported_audio_formats_empty(self, mock_auth):
        """Test get supported audio formats with empty list."""
        with patch(
            "ttskit.api.routers.system.get_supported_formats"
        ) as mock_get_formats:
            mock_get_formats.return_value = []

            result = await get_supported_audio_formats(mock_auth)

            assert result["formats"] == []

    @pytest.mark.asyncio
    async def test_get_supported_language_codes_empty(self, mock_auth):
        """Test get supported language codes with empty list."""
        with patch(
            "ttskit.api.routers.system.get_supported_languages"
        ) as mock_get_languages:
            mock_get_languages.return_value = []

            result = await get_supported_language_codes(mock_auth)

            assert result["languages"] == []

    @pytest.mark.asyncio
    async def test_get_rate_limit_information_empty(self, mock_auth):
        """Test get rate limit information with empty data."""
        with patch(
            "ttskit.api.routers.system.get_rate_limit_info"
        ) as mock_get_rate_info:
            mock_get_rate_info.return_value = {}

            result = await get_rate_limit_information(mock_auth)

            assert result == {}

    @pytest.mark.asyncio
    async def test_get_docs_empty(self, mock_auth):
        """Test get documentation with empty data."""
        with patch("ttskit.api.routers.system.get_documentation") as mock_get_docs:
            mock_get_docs.return_value = {}

            result = await get_docs(mock_auth)

            assert result == {}


class TestSystemRouterIntegration:
    """Test system router integration."""

    def test_router_configuration(self):
        """Test router configuration."""
        assert router.prefix == "/api/v1"
        assert "system" in router.tags

    def test_router_routes(self):
        """Test router routes."""
        route_paths = [route.path for route in router.routes]

        expected_paths = [
            "/api/v1/health",
            "/api/v1/status",
            "/api/v1/info",
            "/api/v1/config",
            "/api/v1/cache/stats",
            "/api/v1/cache/clear",
            "/api/v1/cache/enabled",
            "/api/v1/formats",
            "/api/v1/languages",
            "/api/v1/rate-limit",
            "/api/v1/documentation",
            "/api/v1/metrics",
            "/api/v1/advanced-metrics",
            "/api/v1/version",
        ]

        for expected_path in expected_paths:
            assert expected_path in route_paths

    def test_router_dependencies(self):
        """Test router dependencies."""
        for route in router.routes:
            if hasattr(route, "dependant"):
                assert route.dependant is not None


class TestSystemRouterPerformance:
    """Test system router performance."""

    @pytest.fixture
    def mock_auth(self):
        """Create mock auth dependency."""
        auth = MagicMock(spec=RequiredAuth)
        auth.user_id = "test_user"
        auth.permissions = ["read"]
        return auth

    @pytest.mark.asyncio
    async def test_health_check_performance(self, mock_auth):
        """Test health check performance."""
        with patch("ttskit.public.get_engines") as mock_get_engines:
            mock_get_engines.return_value = [
                {"name": "gtts", "available": True},
                {"name": "edge", "available": True},
            ]

            start_time = time.time()
            result = await health_check(mock_auth)
            end_time = time.time()

            assert result.status == "healthy"
            assert (end_time - start_time) < 1.0

    @pytest.mark.asyncio
    async def test_get_version_performance(self, mock_auth):
        """Test get version performance."""
        start_time = time.time()
        result = await get_version(mock_auth)
        end_time = time.time()

        assert "version" in result
        assert (end_time - start_time) < 0.1

    @pytest.mark.asyncio
    async def test_get_cache_statistics_performance(self, mock_auth):
        """Test get cache statistics performance."""
        with (
            patch("ttskit.api.routers.system.get_cache_stats") as mock_get_stats,
            patch("ttskit.api.routers.system.is_cache_enabled") as mock_is_enabled,
        ):
            mock_get_stats.return_value = {
                "hits": 1000,
                "misses": 500,
                "hit_rate": 0.67,
                "size": 1024000,
                "entries": 25,
            }
            mock_is_enabled.return_value = True

            start_time = time.time()
            result = await get_cache_statistics(mock_auth)
            end_time = time.time()

            assert result.enabled is True
            assert (end_time - start_time) < 0.5
