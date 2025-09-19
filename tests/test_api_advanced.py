"""Advanced and comprehensive tests for TTSKit FastAPI application.

This file covers edge cases, advanced scenarios, integration tests,
and deeper functionality testing that wasn't covered in the basic tests.
"""

import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from ttskit.api.app import app
from ttskit.public import AudioOut


class TestAdvancedSynthesisEndpoints:
    """Advanced tests for synthesis endpoints with edge cases."""

    def setup_method(self):
        """Setup test client and mocks."""
        self.client = TestClient(app)
        self.mock_audio_output = AudioOut(
            data=b"fake_audio_data", format="ogg", duration=2.5, size=1024
        )

    @patch("ttskit.api.routers.synthesis.tts")
    def test_synth_with_all_parameters(self, mock_tts):
        """Test synthesis with all possible parameters."""
        mock_tts_instance = MagicMock()
        mock_tts_instance.synth_async.return_value = self.mock_audio_output
        mock_tts.return_value = mock_tts_instance

        import ttskit.api.routers.synthesis as synthesis_module

        synthesis_module.tts = mock_tts_instance

        request_data = {
            "text": "Hello world! This is a test.",
            "lang": "en",
            "voice": "en-US-AriaNeural",
            "engine": "edge",
            "rate": 1.5,
            "pitch": 2.0,
            "format": "mp3",
        }

        response = self.client.post("/api/v1/synth", json=request_data)

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "audio/mpeg"
        assert "X-Audio-Duration" in response.headers
        assert "X-Audio-Size" in response.headers
        assert "X-Engine-Used" in response.headers

    @patch("ttskit.api.routers.synthesis.tts")
    def test_synth_with_minimal_parameters(self, mock_tts):
        """Test synthesis with minimal required parameters."""
        mock_tts_instance = MagicMock()
        mock_tts_instance.synth_async.return_value = self.mock_audio_output
        mock_tts.return_value = mock_tts_instance

        import ttskit.api.routers.synthesis as synthesis_module

        synthesis_module.tts = mock_tts_instance

        request_data = {"text": "Hi"}

        response = self.client.post("/api/v1/synth", json=request_data)

        assert response.status_code == status.HTTP_200_OK

    def test_synth_with_extreme_values(self):
        """Test synthesis with extreme parameter values."""
        request_data = {
            "text": "A" * 5000,
            "lang": "en",
        }
        response = self.client.post("/api/v1/synth", json=request_data)
        assert response.status_code != status.HTTP_422_UNPROCESSABLE_ENTITY

        request_data = {
            "text": "Hello",
            "rate": 0.1,
        }
        response = self.client.post("/api/v1/synth", json=request_data)
        assert response.status_code != status.HTTP_422_UNPROCESSABLE_ENTITY

        request_data = {
            "text": "Hello",
            "rate": 3.0,
        }
        response = self.client.post("/api/v1/synth", json=request_data)
        assert response.status_code != status.HTTP_422_UNPROCESSABLE_ENTITY

        request_data = {
            "text": "Hello",
            "pitch": 12.0,
        }
        response = self.client.post("/api/v1/synth", json=request_data)
        assert response.status_code != status.HTTP_422_UNPROCESSABLE_ENTITY

        request_data = {
            "text": "Hello",
            "pitch": -12.0,
        }
        response = self.client.post("/api/v1/synth", json=request_data)
        assert response.status_code != status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_synth_with_invalid_values(self):
        """Test synthesis with invalid parameter values."""
        request_data = {
            "text": "A" * 5001,
            "lang": "en",
        }
        response = self.client.post("/api/v1/synth", json=request_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        request_data = {
            "text": "Hello",
            "rate": 0.05,
        }
        response = self.client.post("/api/v1/synth", json=request_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        request_data = {
            "text": "Hello",
            "rate": 5.0,
        }
        response = self.client.post("/api/v1/synth", json=request_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        request_data = {
            "text": "Hello",
            "pitch": 15.0,
        }
        response = self.client.post("/api/v1/synth", json=request_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        request_data = {
            "text": "Hello",
            "pitch": -15.0,
        }
        response = self.client.post("/api/v1/synth", json=request_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        request_data = {
            "text": "Hello",
            "format": "avi",
        }
        response = self.client.post("/api/v1/synth", json=request_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_synth_with_special_characters(self):
        """Test synthesis with special characters and Unicode."""
        special_texts = [
            "Hello! @#$%^&*()",
            "مرحبا بالعالم! 🌍",
            "こんにちは世界！🎌",
        ]

        for text in special_texts:
            request_data = {"text": text, "lang": "en"}
            response = self.client.post("/api/v1/synth", json=request_data)
            assert response.status_code != status.HTTP_422_UNPROCESSABLE_ENTITY

    @patch("ttskit.api.routers.synthesis.tts")
    def test_batch_synth_with_mixed_results(self, mock_tts):
        """Test batch synthesis with some failures."""
        mock_tts_instance = MagicMock()
        mock_tts_instance.synth_async.return_value = self.mock_audio_output
        mock_tts.return_value = mock_tts_instance

        import ttskit.api.routers.synthesis as synthesis_module

        synthesis_module.tts = mock_tts_instance

        request_data = {
            "texts": [
                "Hello",
                "A" * 5001,
                "World",
                "",
                "Test",
            ],
            "lang": "en",
        }

        response = self.client.post("/api/v1/synth/batch", json=request_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["success"] is True
        assert data["total_texts"] == 5
        assert data["successful"] >= 1
        assert data["failed"] >= 1
        assert len(data["results"]) == 5

        results = data["results"]
        assert len(results) == 5
        for result in results:
            assert "success" in result

    def test_preview_with_different_languages(self):
        """Test preview synthesis with different languages."""
        languages = [
            "en",
            "fa",
            "ar",
            "es",
            "fr",
            "de",
            "it",
            "pt",
            "ru",
            "ja",
            "ko",
            "zh",
        ]

        for lang in languages:
            response = self.client.get(
                "/api/v1/synth/preview",
                params={"text": f"Hello in {lang}", "lang": lang},
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert data["success"] is True
            assert data["language"] == lang
            assert "text_preview" in data
            assert "estimated_duration" in data

    def test_preview_with_different_engines(self):
        """Test preview synthesis with different engines."""
        engines = ["gtts", "edge", "piper"]

        for engine in engines:
            response = self.client.get(
                "/api/v1/synth/preview",
                params={"text": "Hello world", "lang": "en", "engine": engine},
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert data["success"] is True
            assert data["engine"] == engine


class TestAdvancedEnginesEndpoints:
    """Advanced tests for engines endpoints."""

    def setup_method(self):
        """Setup test client."""
        self.client = TestClient(app)

    def test_list_engines_with_filters(self):
        """Test listing engines with various filters."""
        response = self.client.get("/api/v1/engines?available_only=true")
        assert response.status_code == status.HTTP_200_OK

        response = self.client.get("/api/v1/engines?available_only=false")
        assert response.status_code == status.HTTP_200_OK

        response = self.client.get("/api/v1/engines?available_only=invalid")
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]

    def test_list_voices_with_filters(self):
        """Test listing voices with various filters."""
        response = self.client.get("/api/v1/voices?language=en")
        assert response.status_code == status.HTTP_200_OK

        response = self.client.get("/api/v1/voices?language=fa")
        assert response.status_code == status.HTTP_200_OK

        response = self.client.get("/api/v1/voices?engine=gtts")
        assert response.status_code == status.HTTP_200_OK

        response = self.client.get("/api/v1/voices?engine=edge")
        assert response.status_code == status.HTTP_200_OK

        response = self.client.get("/api/v1/voices?engine=gtts&language=en")
        assert response.status_code == status.HTTP_200_OK

        response = self.client.get("/api/v1/voices?engine=nonexistent")
        assert response.status_code == status.HTTP_200_OK

        response = self.client.get("/api/v1/voices?language=nonexistent")
        assert response.status_code == status.HTTP_200_OK

    def test_engine_voices_with_filters(self):
        """Test engine-specific voices with filters."""
        engines = ["gtts", "edge", "piper"]

        for engine in engines:
            response = self.client.get(f"/api/v1/engines/{engine}/voices")
            assert response.status_code in [
                status.HTTP_200_OK,
                status.HTTP_404_NOT_FOUND,
                status.HTTP_503_SERVICE_UNAVAILABLE,
            ]

            response = self.client.get(f"/api/v1/engines/{engine}/voices?language=en")
            assert response.status_code in [
                status.HTTP_200_OK,
                status.HTTP_404_NOT_FOUND,
                status.HTTP_503_SERVICE_UNAVAILABLE,
            ]

            response = self.client.get(
                f"/api/v1/engines/{engine}/voices?language=nonexistent"
            )
            assert response.status_code in [
                status.HTTP_200_OK,
                status.HTTP_404_NOT_FOUND,
                status.HTTP_503_SERVICE_UNAVAILABLE,
            ]

    def test_engine_test_with_parameters(self):
        """Test engine testing with different parameters."""
        test_cases = [
            ("gtts", "Hello", "en"),
            ("edge", "مرحبا", "fa"),
        ]

        try:
            from ttskit.engines.piper_engine import PIPER_AVAILABLE

            if PIPER_AVAILABLE:
                test_cases.append(("piper", "Hello", "en"))
        except ImportError:
            pass

        for engine, text, lang in test_cases:
            response = self.client.get(
                f"/api/v1/engines/{engine}/test",
                params={"text": text, "language": lang},
            )
            assert response.status_code != status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_engine_info_edge_cases(self):
        """Test engine info with edge cases."""
        response = self.client.get("/api/v1/engines/gtts%20engine")
        assert response.status_code == status.HTTP_404_NOT_FOUND

        long_name = "a" * 100
        response = self.client.get(f"/api/v1/engines/{long_name}")
        assert response.status_code == status.HTTP_404_NOT_FOUND

        response = self.client.get("/api/v1/engines/")
        assert response.status_code in [
            status.HTTP_404_NOT_FOUND,
            status.HTTP_307_TEMPORARY_REDIRECT,
            status.HTTP_200_OK,
        ]


class TestAdvancedSystemEndpoints:
    """Advanced tests for system endpoints."""

    def setup_method(self):
        """Setup test client."""
        self.client = TestClient(app)

    def test_system_endpoints_without_auth(self):
        """Test that system endpoints properly require authentication."""
        system_endpoints = [
            "/api/v1/health",
            "/api/v1/status",
            "/api/v1/info",
            "/api/v1/config",
            "/api/v1/cache/stats",
            "/api/v1/cache/enabled",
            "/api/v1/formats",
            "/api/v1/languages",
            "/api/v1/rate-limit",
            "/api/v1/documentation",
            "/api/v1/metrics",
            "/api/v1/advanced-metrics",
            "/api/v1/version",
        ]

        for endpoint in system_endpoints:
            response = self.client.get(endpoint)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_cache_endpoints_without_auth(self):
        """Test cache endpoints require proper authentication."""
        response = self.client.post("/api/v1/cache/clear")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        response = self.client.get("/api/v1/cache/stats")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        response = self.client.get("/api/v1/cache/enabled")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_system_endpoints_with_invalid_auth(self):
        """Test system endpoints with invalid authentication."""
        headers = {"Authorization": "Bearer invalid_token"}

        system_endpoints = [
            "/api/v1/health",
            "/api/v1/status",
            "/api/v1/info",
            "/api/v1/config",
        ]

        for endpoint in system_endpoints:
            response = self.client.get(endpoint, headers=headers)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_system_endpoints_with_malformed_auth(self):
        """Test system endpoints with malformed authentication headers."""
        malformed_headers = [
            {"Authorization": "invalid_token"},
            {"Authorization": "Basic invalid_token"},
            {"Authorization": "Bearer"},
            {"Authorization": ""},
            {"Authorization": "Bearer "},
        ]

        for headers in malformed_headers:
            response = self.client.get("/api/v1/health", headers=headers)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestAdvancedAdminEndpoints:
    """Advanced tests for admin endpoints."""

    def setup_method(self):
        """Setup test client."""
        self.client = TestClient(app)

    def test_admin_endpoints_without_auth(self):
        """Test admin endpoints require authentication."""
        admin_endpoints = [
            ("GET", "/api/v1/admin/api-keys"),
            ("POST", "/api/v1/admin/api-keys"),
            ("PUT", "/api/v1/admin/api-keys/test_user"),
            ("DELETE", "/api/v1/admin/api-keys/test_user"),
            ("GET", "/api/v1/admin/users/me"),
        ]

        for method, endpoint in admin_endpoints:
            if method == "GET":
                response = self.client.get(endpoint)
            elif method == "POST":
                response = self.client.post(endpoint, json={})
            elif method == "PUT":
                response = self.client.put(endpoint, json={})
            elif method == "DELETE":
                response = self.client.delete(endpoint)

            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_api_key_validation(self):
        """Test API key creation with various validation scenarios."""
        headers = {"Authorization": "Bearer admin_key"}

        valid_request = {
            "user_id": "test_user",
            "api_key": "test_key_123",
            "permissions": ["read", "write"],
        }
        response = self.client.post(
            "/api/v1/admin/api-keys", json=valid_request, headers=headers
        )
        assert response.status_code != status.HTTP_422_UNPROCESSABLE_ENTITY

        invalid_request = {
            "user_id": "",
            "api_key": "test_key_123",
            "permissions": ["read", "write"],
        }
        response = self.client.post(
            "/api/v1/admin/api-keys", json=invalid_request, headers=headers
        )
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_401_UNAUTHORIZED,
        ]

        invalid_request = {
            "user_id": "a" * 51,
            "api_key": "test_key_123",
            "permissions": ["read", "write"],
        }
        response = self.client.post(
            "/api/v1/admin/api-keys", json=invalid_request, headers=headers
        )
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_401_UNAUTHORIZED,
        ]

        invalid_request = {
            "user_id": "test_user",
            "api_key": "short",
            "permissions": ["read", "write"],
        }
        response = self.client.post(
            "/api/v1/admin/api-keys", json=invalid_request, headers=headers
        )
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_401_UNAUTHORIZED,
        ]

        invalid_request = {
            "user_id": "test_user",
            "api_key": "a" * 101,
            "permissions": ["read", "write"],
        }
        response = self.client.post(
            "/api/v1/admin/api-keys", json=invalid_request, headers=headers
        )
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_401_UNAUTHORIZED,
        ]

        invalid_request = {
            "user_id": "test_user",
            "api_key": "test_key_123",
            "permissions": "invalid",
        }
        response = self.client.post(
            "/api/v1/admin/api-keys", json=invalid_request, headers=headers
        )
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_401_UNAUTHORIZED,
        ]

    def test_update_api_key_validation(self):
        """Test API key update with various validation scenarios."""
        headers = {"Authorization": "Bearer admin_key"}

        valid_request = {"api_key": "new_key_123", "permissions": ["read"]}
        response = self.client.put(
            "/api/v1/admin/api-keys/test_user", json=valid_request, headers=headers
        )
        assert response.status_code != status.HTTP_422_UNPROCESSABLE_ENTITY

        invalid_request = {"api_key": "short", "permissions": ["read"]}
        response = self.client.put(
            "/api/v1/admin/api-keys/test_user", json=invalid_request, headers=headers
        )
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_401_UNAUTHORIZED,
        ]

        invalid_request = {"api_key": "a" * 101, "permissions": ["read"]}
        response = self.client.put(
            "/api/v1/admin/api-keys/test_user", json=invalid_request, headers=headers
        )
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_401_UNAUTHORIZED,
        ]


class TestAdvancedErrorHandling:
    """Advanced error handling tests."""

    def setup_method(self):
        """Setup test client."""
        self.client = TestClient(app)

    def test_malformed_json_requests(self):
        """Test handling of malformed JSON requests."""
        response = self.client.post(
            "/api/v1/synth",
            content='{"text": "hello", "lang": "en"',
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        response = self.client.post(
            "/api/v1/synth", content="{}", headers={"Content-Type": "application/json"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        response = self.client.post(
            "/api/v1/synth",
            content='{"text": "hello", "lang": "en",}',
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_unsupported_content_types(self):
        """Test handling of unsupported content types."""
        response = self.client.post(
            "/api/v1/synth",
            content="<text>hello</text>",
            headers={"Content-Type": "application/xml"},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        response = self.client.post(
            "/api/v1/synth", content="hello", headers={"Content-Type": "text/plain"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_large_request_bodies(self):
        """Test handling of large request bodies."""
        large_text = "A" * 10000
        request_data = {"text": large_text, "lang": "en"}

        response = self.client.post("/api/v1/synth", json=request_data)
        assert response.status_code != status.HTTP_413_REQUEST_ENTITY_TOO_LARGE

    def test_invalid_query_parameters(self):
        """Test handling of invalid query parameters."""
        response = self.client.get("/api/v1/engines?available_only=maybe")
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]

        response = self.client.get("/api/v1/engines?limit=not_a_number")
        assert response.status_code == status.HTTP_200_OK

    def test_special_characters_in_urls(self):
        """Test handling of special characters in URLs."""
        response = self.client.get("/api/v1/engines/test%20engine")
        assert response.status_code == status.HTTP_404_NOT_FOUND

        response = self.client.get("/api/v1/engines/test@engine")
        assert response.status_code == status.HTTP_404_NOT_FOUND

        response = self.client.get("/api/v1/engines/test#engine")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_concurrent_requests(self):
        """Test handling of concurrent requests."""
        import threading
        import time

        results = []
        errors = []

        def make_request():
            try:
                start_time = time.time()
                response = self.client.get("/")
                end_time = time.time()
                results.append(
                    {
                        "status_code": response.status_code,
                        "response_time": end_time - start_time,
                    }
                )
            except Exception as e:
                errors.append(str(e))

        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 10
        for result in results:
            assert result["status_code"] == status.HTTP_200_OK
            assert result["response_time"] < 5.0


class TestAdvancedAuthentication:
    """Advanced authentication tests."""

    def setup_method(self):
        """Setup test client."""
        self.client = TestClient(app)

    def test_authentication_header_variations(self):
        """Test various authentication header formats."""
        headers = {"Authorization": "Bearer valid_token"}
        response = self.client.get("/api/v1/health", headers=headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        headers = {"Authorization": "Bearer  valid_token  "}
        response = self.client.get("/api/v1/health", headers=headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        headers = {"Authorization": "Bearer token-with-special-chars_123"}
        response = self.client.get("/api/v1/health", headers=headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


    def test_case_sensitivity(self):
        """Test case sensitivity of authentication headers."""
        variations = [
            "bearer valid_token",
            "BEARER valid_token",
            "Bearer valid_token",
            "bEaReR valid_token",
        ]

        for auth_header in variations:
            headers = {"Authorization": auth_header}
            response = self.client.get("/api/v1/health", headers=headers)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_multiple_authorization_headers(self):
        """Test handling of multiple authorization headers."""
        headers = {
            "Authorization": "Bearer token1",
            "authorization": "Bearer token2",
        }
        response = self.client.get("/api/v1/health", headers=headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authentication_with_query_parameters(self):
        """Test authentication via query parameters (should not work)."""
        response = self.client.get("/api/v1/health?token=valid_token")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        response = self.client.get("/api/v1/health?api_key=valid_key")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestAdvancedRateLimiting:
    """Advanced rate limiting tests."""

    def setup_method(self):
        """Setup test client."""
        self.client = TestClient(app)

    @patch("ttskit.api.dependencies.rate_limiter")
    def test_rate_limiting_with_different_ips(self, mock_rate_limiter):
        """Test rate limiting with different client IPs."""

        async def mock_is_allowed(user_id):
            return False, "Rate limit exceeded"

        mock_rate_limiter.is_allowed = mock_is_allowed

        response = self.client.post("/api/v1/synth", json={"text": "test"})
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    @patch("ttskit.api.dependencies.rate_limiter")
    def test_rate_limiting_with_different_endpoints(self, mock_rate_limiter):
        """Test rate limiting across different endpoints."""

        async def mock_is_allowed(user_id):
            return False, "Rate limit exceeded"

        mock_rate_limiter.is_allowed = mock_is_allowed

        endpoints = [
            ("POST", "/api/v1/synth", {"text": "test"}),
            ("POST", "/api/v1/synth/batch", {"texts": ["test"]}),
            ("GET", "/api/v1/synth/preview", {"text": "test"}),
        ]

        for method, endpoint, data in endpoints:
            if method == "POST":
                response = self.client.post(endpoint, json=data)
            else:
                response = self.client.get(endpoint, params=data)

            assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS


class TestAdvancedMiddleware:
    """Advanced middleware tests."""

    def setup_method(self):
        """Setup test client."""
        self.client = TestClient(app)

    def test_security_headers_comprehensive(self):
        """Test comprehensive security headers."""
        response = self.client.get("/")

        security_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Strict-Transport-Security",
            "Referrer-Policy",
            "Permissions-Policy",
        ]

        for header in security_headers:
            assert header in response.headers, f"Missing security header: {header}"

        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        assert "max-age=" in response.headers["Strict-Transport-Security"]

    def test_cors_headers_comprehensive(self):
        """Test comprehensive CORS headers."""
        response = self.client.get("/", headers={"Origin": "http://localhost:3000"})

        cors_headers = [
            "Access-Control-Allow-Origin",
            "Access-Control-Allow-Methods",
            "Access-Control-Allow-Headers",
            "Access-Control-Expose-Headers",
        ]

        cors_present = any(header in response.headers for header in cors_headers)
        assert cors_present, "No CORS headers found"

    def test_request_logging_headers(self):
        """Test request logging headers."""
        response = self.client.get("/")

        assert "X-Process-Time" in response.headers
        process_time = float(response.headers["X-Process-Time"])
        assert process_time >= 0
        assert process_time < 10.0

        assert "X-API-Version" in response.headers
        assert "X-Service" in response.headers

    def test_error_response_headers(self):
        """Test error response headers."""
        response = self.client.get("/nonexistent-endpoint")

        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers

        assert "X-Process-Time" in response.headers


class TestAdvancedPerformance:
    """Advanced performance tests."""

    def setup_method(self):
        """Setup test client."""
        self.client = TestClient(app)

    def test_response_times_comprehensive(self):
        """Test comprehensive response times for all endpoints."""
        endpoints = [
            ("GET", "/"),
            ("GET", "/health"),
            ("GET", "/api/v1/engines"),
            ("GET", "/api/v1/synth/preview", {"text": "test"}),
            ("GET", "/docs"),
            ("GET", "/redoc"),
            ("GET", "/openapi.json"),
        ]

        for endpoint_info in endpoints:
            if len(endpoint_info) == 2:
                method, endpoint = endpoint_info
                params = {}
            else:
                method, endpoint, params = endpoint_info

            start_time = time.time()

            if method == "GET":
                response = self.client.get(endpoint, params=params)

            end_time = time.time()
            response_time = end_time - start_time

            assert response_time < 5.0, (
                f"Endpoint {endpoint} took too long: {response_time:.3f}s"
            )

            assert response.status_code in [200, 401, 422], (
                f"Unexpected status for {endpoint}: {response.status_code}"
            )

    def test_memory_usage_stability(self):
        """Test memory usage stability across multiple requests."""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        for _ in range(100):
            response = self.client.get("/")
            assert response.status_code == status.HTTP_200_OK

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        assert memory_increase < 50 * 1024 * 1024, (
            f"Memory increased too much: {memory_increase / 1024 / 1024:.2f}MB"
        )

    def test_concurrent_load_handling(self):
        """Test handling of concurrent load."""
        import threading
        import time

        results = []
        errors = []

        def make_requests():
            try:
                for _ in range(10):
                    start_time = time.time()
                    response = self.client.get("/")
                    end_time = time.time()

                    results.append(
                        {
                            "status_code": response.status_code,
                            "response_time": end_time - start_time,
                        }
                    )
            except Exception as e:
                errors.append(str(e))

        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_requests)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 50

        avg_response_time = sum(r["response_time"] for r in results) / len(results)
        assert avg_response_time < 2.0, (
            f"Average response time too high: {avg_response_time:.3f}s"
        )

        for result in results:
            assert result["status_code"] == status.HTTP_200_OK


class TestAdvancedIntegration:
    """Advanced integration tests."""

    def setup_method(self):
        """Setup test client."""
        self.client = TestClient(app)

    def test_end_to_end_synthesis_flow(self):
        """Test complete end-to-end synthesis flow."""
        response = self.client.get("/api/v1/engines")
        assert response.status_code == status.HTTP_200_OK
        engines = response.json()
        assert len(engines) > 0

        response = self.client.get("/api/v1/voices")
        assert response.status_code == status.HTTP_200_OK
        voices = response.json()
        assert isinstance(voices, list)

        response = self.client.get(
            "/api/v1/synth/preview", params={"text": "Hello world", "lang": "en"}
        )
        assert response.status_code == status.HTTP_200_OK
        preview = response.json()
        assert preview["success"] is True

        response = self.client.get("/api/v1/capabilities")
        assert response.status_code == status.HTTP_200_OK
        capabilities = response.json()
        assert isinstance(capabilities, dict)

    def test_api_versioning_consistency(self):
        """Test API versioning consistency."""
        response = self.client.get("/api/v1/engines")
        assert response.status_code == status.HTTP_200_OK

        response = self.client.get("/api/v1/synth/preview", params={"text": "test"})
        assert response.status_code == status.HTTP_200_OK

        response = self.client.get("/api/v1/capabilities")
        assert response.status_code == status.HTTP_200_OK

        response = self.client.get("/")
        assert response.status_code == status.HTTP_200_OK

        response = self.client.get("/health")
        assert response.status_code == status.HTTP_200_OK

    def test_openapi_schema_completeness(self):
        """Test OpenAPI schema completeness."""
        response = self.client.get("/openapi.json")
        assert response.status_code == status.HTTP_200_OK

        schema = response.json()

        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema
        assert "components" in schema

        assert schema["info"]["title"] == "TTSKit API"
        assert "version" in schema["info"]

        paths = schema["paths"]
        expected_paths = [
            "/",
            "/health",
            "/api/v1/synth",
            "/api/v1/synth/batch",
            "/api/v1/synth/preview",
            "/api/v1/engines",
            "/api/v1/voices",
            "/api/v1/capabilities",
        ]

        for path in expected_paths:
            assert path in paths, f"Path {path} not documented in OpenAPI schema"

    def test_error_response_consistency(self):
        """Test error response consistency."""
        response = self.client.get("/nonexistent")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "application/json" in response.headers["content-type"]

        response = self.client.delete("/")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert "application/json" in response.headers["content-type"]

        response = self.client.post("/api/v1/synth", json={"text": ""})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "application/json" in response.headers["content-type"]

        for resp in [response]:
            if resp.status_code >= 400:
                data = resp.json()
                assert "detail" in data or "message" in data


if __name__ == "__main__":
    pytest.main([__file__])
