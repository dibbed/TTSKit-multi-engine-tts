"""Comprehensive tests for TTSKit FastAPI application."""

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from ttskit.api.app import app, create_app
from ttskit.api.dependencies import get_api_key, verify_api_key
from ttskit.public import AudioOut


class TestFastAPIApp:
    """Test FastAPI application creation and configuration."""

    def test_create_app(self):
        """Test FastAPI app creation."""
        test_app = create_app()

        assert test_app.title == "TTSKit API"
        assert test_app.version is not None
        assert test_app.docs_url == "/docs"
        assert test_app.redoc_url == "/redoc"
        assert test_app.openapi_url == "/openapi.json"

    def test_app_routes_registration(self):
        """Test that all routers are properly registered."""
        routes = [route.path for route in app.routes]

        assert "/" in routes
        assert "/health" in routes

        api_routes = [route for route in routes if route.startswith("/api/v1")]
        assert len(api_routes) > 0

        assert any("/api/v1/synth" in route for route in routes)
        assert any("/api/v1/synth/batch" in route for route in routes)
        assert any("/api/v1/synth/preview" in route for route in routes)

        assert any("/api/v1/engines" in route for route in routes)
        assert any("/api/v1/voices" in route for route in routes)
        assert any("/api/v1/capabilities" in route for route in routes)

        assert any("/api/v1/status" in route for route in routes)
        assert any("/api/v1/info" in route for route in routes)
        assert any("/api/v1/config" in route for route in routes)
        assert any("/api/v1/cache" in route for route in routes)

        assert any("/api/v1/admin/api-keys" in route for route in routes)


class TestRootEndpoints:
    """Test root-level endpoints."""

    def setup_method(self):
        """Setup test client."""
        self.client = TestClient(app)

    def test_root_endpoint(self):
        """Test root endpoint."""
        response = self.client.get("/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["service"] == "TTSKit API"
        assert data["status"] == "running"
        assert "version" in data
        assert data["docs"] == "/docs"
        assert data["api"] == "/api/v1"

    def test_health_endpoint(self):
        """Test public health endpoint."""
        response = self.client.get("/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "status" in data
        assert "engines" in data
        assert "uptime" in data
        assert "version" in data
        assert isinstance(data["engines"], int)
        assert isinstance(data["uptime"], (int, float))


class TestSynthesisEndpoints:
    """Test synthesis-related endpoints."""

    def setup_method(self):
        """Setup test client and mocks."""
        self.client = TestClient(app)
        self.mock_audio_output = AudioOut(
            data=b"fake_audio_data", format="ogg", duration=2.5, size=1024
        )

    @patch("ttskit.api.routers.synthesis.tts")
    def test_synth_endpoint_success(self, mock_tts):
        """Test successful synthesis."""
        mock_tts_instance = MagicMock()
        mock_tts_instance.synth_async.return_value = self.mock_audio_output
        mock_tts.return_value = mock_tts_instance

        import ttskit.api.routers.synthesis as synthesis_module

        synthesis_module.tts = mock_tts_instance

        request_data = {"text": "Hello world", "lang": "en", "format": "ogg"}

        response = self.client.post("/api/v1/synth", json=request_data)

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "audio/ogg"
        assert "X-Audio-Duration" in response.headers
        assert "X-Audio-Size" in response.headers
        assert "X-Engine-Used" in response.headers

    def test_synth_endpoint_validation_error(self):
        """Test synthesis with validation errors."""
        request_data = {"text": "", "lang": "en"}
        response = self.client.post("/api/v1/synth", json=request_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        request_data = {"text": "Hello", "format": "invalid"}
        response = self.client.post("/api/v1/synth", json=request_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        request_data = {"text": "Hello", "rate": 5.0}
        response = self.client.post("/api/v1/synth", json=request_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @patch("ttskit.api.routers.synthesis.tts")
    def test_batch_synth_endpoint(self, mock_tts):
        """Test batch synthesis endpoint."""
        mock_tts_instance = MagicMock()
        mock_tts_instance.synth_async.return_value = self.mock_audio_output
        mock_tts.return_value = mock_tts_instance

        import ttskit.api.routers.synthesis as synthesis_module

        synthesis_module.tts = mock_tts_instance

        request_data = {"texts": ["Hello", "World"], "lang": "en", "format": "ogg"}

        response = self.client.post("/api/v1/synth/batch", json=request_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["success"] is True
        assert data["total_texts"] == 2
        assert data["successful"] == 2
        assert data["failed"] == 0
        assert len(data["results"]) == 2

        for result in data["results"]:
            assert result["success"] is True
            assert "audio_base64" in result
            assert result["duration"] == 2.5
            assert result["size"] == 1024

    def test_preview_synthesis_endpoint(self):
        """Test preview synthesis endpoint."""
        response = self.client.get(
            "/api/v1/synth/preview", params={"text": "Hello world", "lang": "en"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["success"] is True
        assert "text_preview" in data
        assert "text_length" in data
        assert "language" in data
        assert "estimated_duration" in data
        assert "available_engines" in data


class TestEnginesEndpoints:
    """Test engines-related endpoints."""

    def setup_method(self):
        """Setup test client."""
        self.client = TestClient(app)

    @patch("ttskit.api.routers.engines.get_engines")
    @patch("ttskit.api.routers.engines.engine_registry")
    def test_list_engines(self, mock_registry, mock_get_engines):
        """Test listing engines."""
        mock_get_engines.return_value = [
            {"name": "gtts", "available": True},
            {"name": "piper", "available": False},
        ]

        mock_engine = MagicMock()
        mock_capabilities = MagicMock()
        mock_capabilities.offline = False
        mock_capabilities.ssml = False
        mock_capabilities.rate_control = True
        mock_capabilities.pitch_control = False
        mock_capabilities.max_text_length = 5000
        mock_capabilities.languages = ["en", "fa"]
        mock_capabilities.voices = ["default"]

        mock_engine.get_capabilities.return_value = mock_capabilities
        mock_engine.is_available.return_value = True
        mock_registry.get_engine.return_value = mock_engine

        response = self.client.get("/api/v1/engines")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert len(data) >= 1
        engine = data[0]
        assert "name" in engine
        assert "available" in engine
        assert "capabilities" in engine
        assert "languages" in engine
        assert "voices" in engine
        assert "offline" in engine

    def test_list_engines_available_only(self):
        """Test listing only available engines."""
        response = self.client.get("/api/v1/engines?available_only=true")
        assert response.status_code == status.HTTP_200_OK

    @patch("ttskit.api.routers.engines.engine_registry")
    def test_get_engine_info(self, mock_registry):
        """Test getting specific engine info."""
        mock_engine = MagicMock()
        mock_capabilities = MagicMock()
        mock_capabilities.offline = False
        mock_capabilities.ssml = False
        mock_capabilities.rate_control = True
        mock_capabilities.pitch_control = False
        mock_capabilities.max_text_length = 5000
        mock_capabilities.languages = ["en"]
        mock_capabilities.voices = ["default"]

        mock_engine.get_capabilities.return_value = mock_capabilities
        mock_engine.is_available.return_value = True
        mock_registry.get_engine.return_value = mock_engine

        response = self.client.get("/api/v1/engines/gtts")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["name"] == "gtts"
        assert data["available"] is True
        assert "capabilities" in data
        assert "languages" in data
        assert "voices" in data

    def test_get_engine_info_not_found(self):
        """Test getting non-existent engine info."""
        response = self.client.get("/api/v1/engines/nonexistent")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("ttskit.api.routers.engines.engine_registry")
    def test_list_engine_voices(self, mock_registry):
        """Test listing voices for specific engine."""
        mock_engine = MagicMock()
        mock_engine.is_available.return_value = True
        mock_engine.list_voices.return_value = [
            "en_US-lessac-medium",
            "fa_IR-amir-medium",
        ]
        mock_registry.get_engine.return_value = mock_engine

        response = self.client.get("/api/v1/engines/piper/voices")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert len(data) == 2
        for voice in data:
            assert "name" in voice
            assert "engine" in voice
            assert "language" in voice
            assert voice["engine"] == "piper"

    def test_list_engine_voices_not_found(self):
        """Test listing voices for non-existent engine."""
        response = self.client.get("/api/v1/engines/nonexistent/voices")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("ttskit.api.routers.engines.get_engines")
    @patch("ttskit.api.routers.engines.engine_registry")
    def test_list_all_voices(self, mock_registry, mock_get_engines):
        """Test listing all voices across engines."""
        mock_get_engines.return_value = [
            {"name": "gtts", "available": True},
            {"name": "piper", "available": True},
        ]

        mock_engine = MagicMock()
        mock_engine.is_available.return_value = True
        mock_engine.list_voices.return_value = ["default"]
        mock_registry.get_engine.return_value = mock_engine

        response = self.client.get("/api/v1/voices")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data, list)
        for voice in data:
            assert "name" in voice
            assert "engine" in voice
            assert "language" in voice

    @patch("ttskit.api.routers.engines.engine_registry")
    @patch("ttskit.public.TTS")
    def test_test_engine(self, mock_tts_class, mock_registry):
        """Test engine testing endpoint."""
        mock_engine = MagicMock()
        mock_engine.is_available.return_value = True
        mock_registry.get_engine.return_value = mock_engine

        mock_tts_instance = MagicMock()
        mock_audio_output = AudioOut(
            data=b"test_audio", format="wav", duration=1.0, size=512
        )
        mock_tts_instance.synth_async.return_value = mock_audio_output
        mock_tts_class.return_value = mock_tts_instance

        response = self.client.get("/api/v1/engines/gtts/test")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["success"] is True
        assert data["engine"] == "gtts"
        assert data["test_text"] == "Hello, world!"
        assert data["language"] == "en"
        assert data["duration"] == 1.0
        assert data["size"] == 512

    @patch("ttskit.api.routers.engines.get_engine_capabilities")
    def test_get_capabilities(self, mock_get_capabilities):
        """Test getting engine capabilities."""
        mock_get_capabilities.return_value = {
            "gtts": {"offline": False, "languages": ["en", "fa"]},
            "piper": {"offline": True, "languages": ["en", "fa", "ar"]},
        }

        response = self.client.get("/api/v1/capabilities")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "gtts" in data
        assert "piper" in data


class TestSystemEndpoints:
    """Test system-related endpoints."""

    def setup_method(self):
        """Setup test client."""
        self.client = TestClient(app)

    def test_system_health_check_unauthorized(self):
        """Test system health check without auth."""
        response = self.client.get("/api/v1/health")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_system_status_unauthorized(self):
        """Test system status without auth."""
        response = self.client.get("/api/v1/status")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_system_info_unauthorized(self):
        """Test system info without auth."""
        response = self.client.get("/api/v1/info")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_config_unauthorized(self):
        """Test config endpoint without auth."""
        response = self.client.get("/api/v1/config")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_cache_stats_unauthorized(self):
        """Test cache stats without auth."""
        response = self.client.get("/api/v1/cache/stats")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_cache_clear_unauthorized(self):
        """Test cache clear without auth."""
        response = self.client.post("/api/v1/cache/clear")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_cache_enabled_unauthorized(self):
        """Test cache enabled check without auth."""
        response = self.client.get("/api/v1/cache/enabled")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_formats_unauthorized(self):
        """Test supported formats without auth."""
        response = self.client.get("/api/v1/formats")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_languages_unauthorized(self):
        """Test supported languages without auth."""
        response = self.client.get("/api/v1/languages")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_rate_limit_unauthorized(self):
        """Test rate limit info without auth."""
        response = self.client.get("/api/v1/rate-limit")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_documentation_unauthorized(self):
        """Test documentation without auth."""
        response = self.client.get("/api/v1/documentation")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_metrics_unauthorized(self):
        """Test metrics without auth."""
        response = self.client.get("/api/v1/metrics")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_advanced_metrics_unauthorized(self):
        """Test advanced metrics without auth."""
        response = self.client.get("/api/v1/advanced-metrics")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_version_unauthorized(self):
        """Test version without auth."""
        response = self.client.get("/api/v1/version")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestAdminEndpoints:
    """Test admin-related endpoints."""

    def setup_method(self):
        """Setup test client."""
        self.client = TestClient(app)

    def test_list_api_keys_unauthorized(self):
        """Test listing API keys without auth."""
        response = self.client.get("/api/v1/admin/api-keys")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_api_key_unauthorized(self):
        """Test creating API key without auth."""
        request_data = {
            "user_id": "test_user",
            "api_key": "test_key_123",
            "permissions": ["read", "write"],
        }
        response = self.client.post("/api/v1/admin/api-keys", json=request_data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_api_key_unauthorized(self):
        """Test updating API key without auth."""
        request_data = {"api_key": "new_key_123", "permissions": ["read"]}
        response = self.client.put(
            "/api/v1/admin/api-keys/test_user", json=request_data
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_delete_api_key_unauthorized(self):
        """Test deleting API key without auth."""
        response = self.client.delete("/api/v1/admin/api-keys/test_user")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user_unauthorized(self):
        """Test getting current user without auth."""
        response = self.client.get("/api/v1/admin/users/me")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestDependencies:
    """Test API dependencies."""

    def test_get_api_key_no_credentials(self):
        """Test getting API key with no credentials."""
        result = asyncio.run(get_api_key(None))
        assert result is None

    def test_get_api_key_invalid_scheme(self):
        """Test getting API key with invalid scheme."""
        from fastapi.security import HTTPAuthorizationCredentials

        credentials = HTTPAuthorizationCredentials(scheme="Basic", credentials="test")

        with pytest.raises(Exception):
            asyncio.run(get_api_key(credentials))

    def test_get_api_key_valid_scheme(self):
        """Test getting API key with valid scheme."""
        from fastapi.security import HTTPAuthorizationCredentials

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="test_key"
        )
        result = asyncio.run(get_api_key(credentials))

        assert result == "test_key"

    @patch("ttskit.api.dependencies.settings")
    def test_verify_api_key_valid(self, mock_settings):
        """Test verifying valid API key."""
        mock_settings.api_keys = {"test_user": "test_key"}

        from unittest.mock import MagicMock

        result = asyncio.run(verify_api_key("test_key", db=MagicMock()))

        assert result is not None
        assert result.api_key == "test_key"
        assert result.user_id == "test_user"
        assert "read" in result.permissions
        assert "write" in result.permissions

    @patch("ttskit.api.dependencies.settings")
    def test_verify_api_key_admin(self, mock_settings):
        """Test verifying admin API key."""
        mock_settings.api_keys = {"admin": "admin_key"}

        from unittest.mock import MagicMock

        result = asyncio.run(verify_api_key("admin_key", db=MagicMock()))

        assert result is not None
        assert result.user_id == "admin"
        assert "admin" in result.permissions

    @patch("ttskit.api.dependencies.settings")
    def test_verify_api_key_readonly(self, mock_settings):
        """Test verifying readonly API key."""
        mock_settings.api_keys = {"readonly_user": "readonly_key"}

        from unittest.mock import MagicMock

        result = asyncio.run(verify_api_key("readonly_key", db=MagicMock()))

        assert result is not None
        assert result.user_id == "readonly_user"
        assert result.permissions == ["read"]

    def test_verify_api_key_invalid(self):
        """Test verifying invalid API key."""
        with pytest.raises(Exception):
            asyncio.run(verify_api_key("invalid_key"))


class TestMiddleware:
    """Test API middleware."""

    def test_security_headers_middleware(self):
        """Test security headers middleware."""
        client = TestClient(app)
        response = client.get("/")

        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-XSS-Protection" in response.headers
        assert "Strict-Transport-Security" in response.headers
        assert "Referrer-Policy" in response.headers
        assert "Permissions-Policy" in response.headers

        assert "X-API-Version" in response.headers
        assert "X-Service" in response.headers

    def test_request_logging_middleware(self):
        """Test request logging middleware."""
        client = TestClient(app)
        response = client.get("/")

        assert "X-Process-Time" in response.headers
        process_time = float(response.headers["X-Process-Time"])
        assert process_time >= 0

    def test_cors_middleware(self):
        """Test CORS middleware."""
        client = TestClient(app)

        response = client.get("/", headers={"Origin": "http://localhost:3000"})
        assert response.status_code == status.HTTP_200_OK

        assert (
            "Access-Control-Allow-Origin" in response.headers
            or "access-control-allow-origin" in response.headers
        )


class TestErrorHandling:
    """Test error handling."""

    def setup_method(self):
        """Setup test client."""
        self.client = TestClient(app)

    def test_validation_error_handler(self):
        """Test validation error handling."""
        response = self.client.post(
            "/api/v1/synth",
            content="invalid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "detail" in data

    def test_not_found_error(self):
        """Test 404 error handling."""
        response = self.client.get("/nonexistent-endpoint")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_method_not_allowed(self):
        """Test 405 error handling."""
        response = self.client.delete("/")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


class TestRateLimiting:
    """Test rate limiting functionality."""

    def setup_method(self):
        """Setup test client."""
        self.client = TestClient(app)

    @patch("ttskit.api.dependencies.rate_limiter")
    def test_rate_limit_exceeded(self, mock_rate_limiter):
        """Test rate limit exceeded scenario."""

        async def mock_is_allowed(user_id):
            return False, "Rate limit exceeded"

        mock_rate_limiter.is_allowed = mock_is_allowed

        response = self.client.post("/api/v1/synth", json={"text": "test"})

        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "Retry-After" in response.headers

    @patch("ttskit.api.dependencies.rate_limiter")
    def test_rate_limit_allowed(self, mock_rate_limiter):
        """Test rate limit allowed scenario."""

        async def mock_is_allowed(user_id):
            return True, "Request allowed"

        mock_rate_limiter.is_allowed = mock_is_allowed

        response = self.client.post("/api/v1/synth", json={"text": "test"})

        assert response.status_code != status.HTTP_429_TOO_MANY_REQUESTS


class TestAuthenticationFlow:
    """Test complete authentication flow."""

    def setup_method(self):
        """Setup test client."""
        self.client = TestClient(app)

    def test_public_endpoints_no_auth(self):
        """Test that public endpoints work without authentication."""
        response = self.client.get("/")
        assert response.status_code == status.HTTP_200_OK

        response = self.client.get("/health")
        assert response.status_code == status.HTTP_200_OK

        response = self.client.post("/api/v1/synth", json={"text": "test"})
        assert response.status_code != status.HTTP_401_UNAUTHORIZED

    def test_protected_endpoints_require_auth(self):
        """Test that protected endpoints require authentication."""
        protected_endpoints = [
            "/api/v1/status",
            "/api/v1/info",
            "/api/v1/config",
            "/api/v1/cache/stats",
            "/api/v1/admin/api-keys",
        ]

        for endpoint in protected_endpoints:
            response = self.client.get(endpoint)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_write_endpoints_require_write_permission(self):
        """Test that write endpoints require write permission."""
        write_endpoints = [
            ("POST", "/api/v1/cache/clear"),
            ("POST", "/api/v1/admin/api-keys"),
            ("PUT", "/api/v1/admin/api-keys/test"),
            ("DELETE", "/api/v1/admin/api-keys/test"),
        ]

        for method, endpoint in write_endpoints:
            if method == "POST":
                response = self.client.post(endpoint, json={})
            elif method == "PUT":
                response = self.client.put(endpoint, json={})
            elif method == "DELETE":
                response = self.client.delete(endpoint)

            assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestOpenAPIDocumentation:
    """Test OpenAPI documentation generation."""

    def setup_method(self):
        """Setup test client."""
        self.client = TestClient(app)

    def test_openapi_schema(self):
        """Test OpenAPI schema generation."""
        response = self.client.get("/openapi.json")

        assert response.status_code == status.HTTP_200_OK
        schema = response.json()

        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema
        assert schema["info"]["title"] == "TTSKit API"

    def test_docs_endpoint(self):
        """Test Swagger UI docs endpoint."""
        response = self.client.get("/docs")
        assert response.status_code == status.HTTP_200_OK

    def test_redoc_endpoint(self):
        """Test ReDoc endpoint."""
        response = self.client.get("/redoc")
        assert response.status_code == status.HTTP_200_OK


class TestPerformanceAndConcurrency:
    """Test performance and concurrency aspects."""

    def setup_method(self):
        """Setup test client."""
        self.client = TestClient(app)

    def test_concurrent_requests(self):
        """Test handling concurrent requests."""
        import threading
        import time

        results = []

        def make_request():
            start_time = time.time()
            response = self.client.get("/")
            end_time = time.time()
            results.append(
                {
                    "status_code": response.status_code,
                    "response_time": end_time - start_time,
                }
            )

        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        assert len(results) == 5
        for result in results:
            assert result["status_code"] == status.HTTP_200_OK
            assert result["response_time"] < 1.0

    def test_response_times(self):
        """Test response times for different endpoints."""
        endpoints = [
            ("/", "GET"),
            ("/health", "GET"),
            ("/api/v1/engines", "GET"),
            ("/api/v1/synth/preview", "GET"),
        ]

        for endpoint, method in endpoints:
            start_time = time.time()

            if method == "GET":
                if endpoint == "/api/v1/synth/preview":
                    response = self.client.get(endpoint, params={"text": "test"})
                else:
                    response = self.client.get(endpoint)

            end_time = time.time()
            response_time = end_time - start_time

            assert response_time < 2.0, (
                f"Endpoint {endpoint} took too long: {response_time}s"
            )

            assert response.status_code in [200, 401, 422], (
                f"Unexpected status for {endpoint}"
            )


if __name__ == "__main__":
    pytest.main([__file__])
