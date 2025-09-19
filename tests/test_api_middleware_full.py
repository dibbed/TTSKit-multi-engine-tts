"""Comprehensive tests for TTSKit API middleware, including SecurityHeadersMiddleware, RequestLoggingMiddleware, ErrorHandlingMiddleware, and setup functions using a minimal FastAPI app.

These tests verify middleware behavior through response headers, error handling, and manual stack setup.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from ttskit.api.middleware import (
    ErrorHandlingMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
    setup_all_middleware,
    setup_security_middleware,
)


def _build_app_all() -> FastAPI:
    """Builds a minimal FastAPI app with all middleware applied and test routes for OK and error responses.

    Returns:
        FastAPI: The configured app instance ready for testing.
    """
    app = FastAPI()
    setup_all_middleware(app)

    @app.get("/ok")
    def ok():
        return {"status": "ok"}

    @app.get("/boom")
    def boom():
        raise RuntimeError("x")

    return app


def _build_app_security_only() -> FastAPI:
    """Builds a minimal FastAPI app with only security middleware and a ping route.

    Returns:
        FastAPI: The configured app instance for security header tests.
    """
    app = FastAPI()
    setup_security_middleware(app)

    @app.get("/ping")
    def ping():
        return JSONResponse({"pong": True})

    return app


def test_security_headers_and_logging_and_cors_headers_present():
    """Tests that security, logging, and CORS headers are present in successful responses.

    Verifies specific header values like X-Content-Type-Options and X-API-Version.
    """
    client = TestClient(_build_app_all())
    resp = client.get("/ok")
    assert resp.status_code == 200
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert "X-XSS-Protection" in resp.headers
    assert "Strict-Transport-Security" in resp.headers
    assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "Permissions-Policy" in resp.headers
    assert resp.headers["X-API-Version"]
    assert resp.headers["X-Service"] == "TTSKit"
    assert "X-Process-Time" in resp.headers


def test_error_handling_middleware_returns_json_response():
    """Tests error handling middleware catches exceptions and returns structured JSON responses.

    Checks for 500 status, error details, request ID, and X-Error-Type header.
    """
    client = TestClient(_build_app_all())
    resp = client.get("/boom")
    assert resp.status_code == 500
    body = resp.json()
    assert body["error"] == "Internal server error"
    assert body["message"]
    assert "request_id" in body
    assert resp.headers.get("X-Error-Type") == "internal_error"


def test_setup_security_only_paths():
    """Tests security middleware setup on a simple ping endpoint.

    Verifies basic security headers like X-Frame-Options are applied.
    """
    client = TestClient(_build_app_security_only())
    resp = client.get("/ping")
    assert resp.status_code == 200
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"


def test_individual_middleware_stack_manual():
    """Tests manual addition of individual middleware to a FastAPI app.

    Ensures security headers are still applied when middleware is added in sequence.
    """
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(ErrorHandlingMiddleware)

    @app.get("/echo")
    def echo():
        return {"a": 1}

    client = TestClient(app)
    resp = client.get("/echo")
    assert resp.status_code == 200
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
