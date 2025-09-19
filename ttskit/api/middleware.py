"""FastAPI middleware components for TTSKit API security, logging, and configuration.

This module provides middleware classes that handle security headers, request/response
logging, and error handling for the TTSKit API. It also includes utility functions
for configuring CORS policies and setting up all middleware in a FastAPI application.
"""

import time
from collections.abc import Callable

from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from ..config import settings
from ..utils.logging_config import get_logger

logger = get_logger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware that adds security headers to enhance API protection.

    This middleware automatically adds various HTTP security headers to every
    outgoing response to protect against common web vulnerabilities such as
    XSS, clickjacking, and content sniffing attacks.

    The headers added include Content-Type-Options, X-Frame-Options,
    X-XSS-Protection, Strict-Transport-Security, Referrer-Policy,
    Permissions-Policy, and custom TTSKit headers.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )

        response.headers["X-API-Version"] = "1.0.0"
        response.headers["X-Service"] = "TTSKit"

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that logs incoming requests and responses for monitoring.

    This middleware automatically logs details about each HTTP request and
    its corresponding response, including timing information. It helps with
    debugging, performance monitoring, and audit trails by recording
    client IP, request method, URL path, response status, and processing time.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        client_ip = request.client.host if request.client else "unknown"
        logger.info(
            f"Request: {request.method} {request.url.path} "
            f"from {client_ip} "
            f"User-Agent: {request.headers.get('user-agent', 'unknown')}"
        )

        response = await call_next(request)

        process_time = time.time() - start_time
        logger.info(
            f"Response: {response.status_code} "
            f"for {request.method} {request.url.path} "
            f"took {process_time:.3f}s"
        )

        response.headers["X-Process-Time"] = str(process_time)

        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware that catches unhandled exceptions and returns standardized error responses.

    This middleware wraps the entire request processing pipeline in a try-catch block,
    ensuring that any unhandled exceptions are properly logged and a consistent
    JSON error response is returned to clients. This prevents raw stack traces
    from being exposed and provides better error handling for production applications.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            logger.error(f"Unhandled error in {request.method} {request.url.path}: {e}")

            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "message": "An unexpected error occurred",
                    "request_id": id(request),
                },
                headers={"X-Error-Type": "internal_error"},
            )


def setup_cors_middleware(app):
    """Setup CORS middleware with secure defaults.

    Args:
        app (FastAPI): The FastAPI application instance.
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins
        if hasattr(settings, "cors_origins")
        else ["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Process-Time", "X-API-Version", "X-Service"],
    )


def setup_security_middleware(app):
    """Setup security middleware.

    Args:
        app (FastAPI): The FastAPI application instance.
    """
    if hasattr(settings, "allowed_hosts") and settings.allowed_hosts:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)

    app.add_middleware(SecurityHeadersMiddleware)

    app.add_middleware(RequestLoggingMiddleware)

    app.add_middleware(ErrorHandlingMiddleware)


def setup_all_middleware(app):
    """Setup all middleware for the application.

    Args:
        app (FastAPI): The FastAPI application instance.
    """
    setup_cors_middleware(app)
    setup_security_middleware(app)
