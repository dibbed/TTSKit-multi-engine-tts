"""Provides authentication, rate limiting, and dependency injection for the TTSKit API.

This module contains FastAPI dependencies for API key verification, permission checks,
and request handling, ensuring secure and controlled access to API endpoints.
"""

import time
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..config import settings
from ..database.connection import get_session
from ..services.user_service import UserService
from ..utils.logging_config import get_logger
from ..utils.rate_limiter import RateLimiter

logger = get_logger(__name__)

security = HTTPBearer(auto_error=False)

rate_limiter = RateLimiter(max_requests=settings.api_rate_limit, window_seconds=60)


class APIKeyAuth(BaseModel):
    """Model for API key authentication with user details and permissions.

    Attributes:
        api_key (str): The API key string.
        user_id (str or None): Optional user identifier.
        permissions (list of str): Granted permissions, defaults to ['read', 'write'].
    """

    api_key: str
    user_id: str | None = None
    permissions: list[str] = ["read", "write"]


async def get_api_key(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> str | None:
    """Extract API key from HTTP Authorization header.

    Args:
        credentials (HTTPAuthorizationCredentials or None): Authorization data from request.

    Returns:
        str or None: The API key if Bearer authentication is used, else None.

    Raises:
        HTTPException: If authentication scheme is not Bearer.
    """
    if not credentials:
        return None

    if credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication scheme",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return credentials.credentials


async def verify_api_key(
    api_key: Annotated[str | None, Depends(get_api_key)],
    db: Annotated[Session, Depends(get_session)],
) -> APIKeyAuth | None:
    """Verifies an API key using configuration or database fallback.

    This function checks the provided API key against multiple sources
    in a specific priority order for flexible authentication setup.

    Args:
        api_key (str or None): The API key extracted from the request header.
        db (Session): Database session for user verification.

    Returns:
        APIKeyAuth or None: An APIKeyAuth object with user details and permissions
        if verification succeeds, or None if no API key provided.

    Raises:
        HTTPException: If the API key is invalid or cannot be verified.

    Notes:
        Verification follows this priority order:
        1. Config settings (api_keys dictionary or single api_key)
        2. Database lookup via UserService
        Permission defaults are ['read', 'write'] with admin variations.
    """
    if not api_key:
        return None

    if hasattr(settings, "api_keys") and settings.api_keys:
        for user_id, stored_key in settings.api_keys.items():
            if api_key == stored_key:
                permissions = ["read", "write"]
                if user_id == "admin":
                    permissions = ["read", "write", "admin"]
                elif user_id.startswith("readonly_"):
                    permissions = ["read"]

                logger.info(f"API key verified from config for user: {user_id}")
                return APIKeyAuth(
                    api_key=api_key, user_id=user_id, permissions=permissions
                )

    if hasattr(settings, "api_key") and api_key == settings.api_key:
        logger.info("API key verified from config (single key)")
        return APIKeyAuth(
            api_key=api_key, user_id="demo-user", permissions=["read", "write"]
        )

    try:
        user_service = UserService(db)
        user_info = await user_service.verify_api_key(api_key)

        if user_info:
            logger.info(
                f"API key verified from database for user: {user_info['user_id']}"
            )
            return APIKeyAuth(
                api_key=api_key,
                user_id=user_info["user_id"],
                permissions=user_info["permissions"],
            )
    except Exception as e:
        logger.warning(f"Database verification failed: {e}")

    logger.warning(f"Invalid API key attempted: {api_key[:10]}...")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def require_auth(
    auth: Annotated[APIKeyAuth | None, Depends(verify_api_key)],
) -> APIKeyAuth:
    """Enforce authentication for protected API endpoints.

    Args:
        auth (APIKeyAuth or None): Authentication result from dependency.

    Returns:
        APIKeyAuth: Validated authentication object.

    Raises:
        HTTPException: If authentication is missing.
    """
    if not auth:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return auth


async def require_write_permission(
    auth: Annotated[APIKeyAuth, Depends(require_auth)],
) -> APIKeyAuth:
    """Check for write permission on modification endpoints.

    Args:
        auth (APIKeyAuth): Authenticated user.

    Returns:
        APIKeyAuth: Same auth if write permission present.

    Raises:
        HTTPException: If write permission is missing.
    """
    if "write" not in auth.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write permission required",
        )
    return auth


async def check_rate_limit(request: Request) -> None:
    """Enforce rate limiting based on client IP.

    Args:
        request (Request): Incoming request.

    Raises:
        HTTPException: If rate limit is exceeded.
    """
    client_ip = request.client.host if request.client else "unknown"

    allowed, message = await rate_limiter.is_allowed(client_ip)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=message,
            headers={"Retry-After": "60"},
        )


async def get_request_info(request: Request) -> dict:
    """Extracts key HTTP request details for logging and monitoring.

    This utility function gathers essential request information that can be
    useful for request tracking, debugging, and audit trails.

    Args:
        request (Request): The incoming Starlette/FastAPI Request object.

    Returns:
        dict: A dictionary with the following keys:
            'method' (str): HTTP method (GET, POST, etc.)
            'url' (str): Full request URL as string
            'client_ip' (str): Client's IP address or 'unknown'
            'user_agent' (str): User-Agent header value or 'unknown'
            'timestamp' (float): Unix timestamp of extraction time
    """
    return {
        "method": request.method,
        "url": str(request.url),
        "client_ip": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", "unknown"),
        "timestamp": time.time(),
    }


OptionalAuth = Annotated[APIKeyAuth | None, Depends(verify_api_key)]

RequiredAuth = Annotated[APIKeyAuth, Depends(require_auth)]

WriteAuth = Annotated[APIKeyAuth, Depends(require_write_permission)]

RateLimit = Annotated[None, Depends(check_rate_limit)]
