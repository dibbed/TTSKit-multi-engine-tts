"""Provides authentication, rate limiting, and dependency injection for the TTSKit API.

This module contains FastAPI dependencies for API key verification, permission checks,
and request handling, ensuring secure and controlled access to API endpoints.
"""

import secrets
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
        api_key (str or None): Optional API key reference (plaintext secrets are not retained).
        user_id (str or None): Optional user identifier.
        permissions (list of str): Granted permissions, defaults to ['read', 'write'].
        is_admin (bool): Whether the user has admin privileges.
    """

    api_key: str | None = None
    user_id: str | None = None
    permissions: list[str] = ["read", "write"]
    is_admin: bool = False


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

    Honors settings.enable_auth:
    - If authentication is disabled (enable_auth=False), anonymous requests
      are permitted with development permissions.
    - If authentication is enabled (enable_auth=True):
      - Missing credentials return None (require_auth rejects with 401).
      - Invalid credentials raise 401 without leaking secret fragments.
      - Valid credentials return APIKeyAuth.
    """
    if not getattr(settings, "enable_auth", False):
        if not api_key:
            return APIKeyAuth(
                api_key=None,
                user_id="dev-user",
                permissions=["read", "write", "admin"],
                is_admin=True,
            )

    if not api_key:
        return None

    # 1. Config settings dictionary of keys (constant-time comparison)
    if hasattr(settings, "api_keys") and settings.api_keys:
        for user_id, stored_key in settings.api_keys.items():
            if stored_key and secrets.compare_digest(api_key, stored_key):
                permissions = ["read", "write"]
                is_admin = False
                if user_id == "admin":
                    permissions = ["read", "write", "admin"]
                    is_admin = True
                elif user_id.startswith("readonly_"):
                    permissions = ["read"]

                logger.info("API key verified from config for user: %s", user_id)
                return APIKeyAuth(
                    api_key=api_key,
                    user_id=user_id,
                    permissions=permissions,
                    is_admin=is_admin,
                )

    # 2. Config settings single key (constant-time comparison)
    if hasattr(settings, "api_key") and settings.api_key and secrets.compare_digest(api_key, settings.api_key):
        logger.info("API key verified from config (single key)")
        return APIKeyAuth(
            api_key=api_key,
            user_id="api-user",
            permissions=["read", "write"],
            is_admin=False,
        )

    # 3. Database lookup via UserService
    try:
        user_service = UserService(db)
        user_info = await user_service.verify_api_key(api_key)

        if user_info:
            logger.info(
                "API key verified from database for user: %s", user_info["user_id"]
            )
            return APIKeyAuth(
                api_key=api_key,
                user_id=user_info["user_id"],
                permissions=user_info["permissions"],
                is_admin=bool(user_info.get("is_admin", False)),
            )
    except Exception as e:
        logger.warning("Database verification failed: %s", e)

    logger.warning("Invalid API key attempted")
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


async def require_admin_permission(
    auth: Annotated[APIKeyAuth, Depends(require_auth)],
) -> APIKeyAuth:
    """Check for admin permission on privileged endpoints.

    Args:
        auth (APIKeyAuth): Authenticated user.

    Returns:
        APIKeyAuth: Same auth if admin permission present.

    Raises:
        HTTPException: If admin permission is missing.
    """
    if "admin" not in auth.permissions and not auth.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin permission required",
        )
    return auth


async def check_rate_limit(request: Request) -> None:
    """Enforce rate limiting based on client IP when enabled.

    Args:
        request (Request): Incoming request.

    Raises:
        HTTPException: If rate limit is exceeded.
    """
    if not getattr(settings, "enable_rate_limiting", True):
        return

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

AdminAuth = Annotated[APIKeyAuth, Depends(require_admin_permission)]

RateLimit = Annotated[None, Depends(check_rate_limit)]
