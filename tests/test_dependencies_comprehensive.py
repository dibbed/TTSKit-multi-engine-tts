"""Comprehensive tests for API dependencies module."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from ttskit.api.dependencies import (
    APIKeyAuth,
    OptionalAuth,
    RequiredAuth,
    WriteAuth,
    check_rate_limit,
    get_api_key,
    get_request_info,
    require_auth,
    require_write_permission,
    verify_api_key,
)


class TestAPIKeyAuth:
    """Tests the APIKeyAuth model used for handling API key authentication data.



    Notes:

        Covers model creation with explicit values and defaults, verifying attributes like api_key, user_id, and permissions.

    """

    def test_api_key_auth_creation(self):
        """Verifies creation of APIKeyAuth with explicit parameters."""
        auth = APIKeyAuth(
            api_key="test_key", user_id="test_user", permissions=["read", "write"]
        )

        assert auth.api_key == "test_key"
        assert auth.user_id == "test_user"
        assert auth.permissions == ["read", "write"]

    def test_api_key_auth_defaults(self):
        """Verifies APIKeyAuth creation using default values for user_id and permissions."""
        auth = APIKeyAuth(api_key="test_key")

        assert auth.api_key == "test_key"
        assert auth.user_id is None
        assert auth.permissions == ["read", "write"]


class TestGetAPIKey:
    """Tests the get_api_key function for extracting API keys from HTTP credentials.



    Notes:

        Handles no credentials, invalid schemes (raises 401), and valid Bearer schemes (case-insensitive), returning the key or None.

    """

    def test_get_api_key_no_credentials(self):
        """Verifies that get_api_key returns None when no credentials are provided."""
        result = asyncio.run(get_api_key(None))
        assert result is None

    def test_get_api_key_invalid_scheme(self):
        """Verifies that get_api_key raises a 401 error for invalid authentication schemes like Basic.



        Behavior:

            Expects an HTTPException with status 401, specific detail message, and WWW-Authenticate header.
        """
        credentials = HTTPAuthorizationCredentials(scheme="Basic", credentials="test")

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(get_api_key(credentials))

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid authentication scheme" in exc_info.value.detail
        assert exc_info.value.headers["WWW-Authenticate"] == "Bearer"

    def test_get_api_key_valid_scheme(self):
        """Verifies that get_api_key extracts the key correctly for a valid Bearer scheme."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="test_key"
        )

        result = asyncio.run(get_api_key(credentials))
        assert result == "test_key"

    def test_get_api_key_case_insensitive_scheme(self):
        """Verifies that get_api_key handles Bearer scheme case-insensitively (e.g., 'bearer')."""
        credentials = HTTPAuthorizationCredentials(
            scheme="bearer",
            credentials="test_key",
        )

        result = asyncio.run(get_api_key(credentials))
        assert result == "test_key"


class TestVerifyAPIKey:
    """Tests the verify_api_key function for validating API keys against settings and returning auth objects.



    Notes:

        Covers dictionary-based keys with permissions (admin, read/write, readonly), fallback to single key, invalid keys (raises 401), and None input.

    """

    @patch("ttskit.api.dependencies.settings")
    def test_verify_api_key_with_api_keys_dict(self, mock_settings):
        """Verifies verify_api_key using a dictionary of api_keys with full read/write permissions.



        Parameters:

            mock_settings: Patched settings with api_keys dict mapping users to keys.



        Behavior:

            For a matching key, returns APIKeyAuth with user_id and permissions; assumes read/write if not specified.
        """
        mock_settings.api_keys = {
            "test_user": "test_key",
            "admin": "admin_key",
            "readonly_user": "readonly_key",
        }

        result = asyncio.run(verify_api_key("test_key", db=MagicMock()))
        assert result is not None
        assert result.api_key == "test_key"
        assert result.user_id == "test_user"
        assert "read" in result.permissions
        assert "write" in result.permissions

    @patch("ttskit.api.dependencies.settings")
    def test_verify_api_key_admin_user(self, mock_settings):
        """Verifies verify_api_key for an admin user key, ensuring admin permission is included.



        Parameters:

            mock_settings: Patched settings with admin key mapping.



        Behavior:

            Returns APIKeyAuth with admin, read, and write permissions.
        """
        mock_settings.api_keys = {"admin": "admin_key"}

        result = asyncio.run(verify_api_key("admin_key", db=MagicMock()))
        assert result is not None
        assert result.user_id == "admin"
        assert "admin" in result.permissions
        assert "read" in result.permissions
        assert "write" in result.permissions

    @patch("ttskit.api.dependencies.settings")
    def test_verify_api_key_readonly_user(self, mock_settings):
        """Verifies verify_api_key for a readonly user key, limiting permissions to read only.



        Parameters:

            mock_settings: Patched settings with readonly key mapping.



        Behavior:

            Returns APIKeyAuth with only 'read' permission.
        """
        mock_settings.api_keys = {"readonly_user": "readonly_key"}

        result = asyncio.run(verify_api_key("readonly_key", db=MagicMock()))
        assert result is not None
        assert result.user_id == "readonly_user"
        assert result.permissions == ["read"]

    @patch("ttskit.api.dependencies.settings")
    def test_verify_api_key_fallback_single_key(self, mock_settings):
        """Verifies the fallback to a single api_key when api_keys dict is None.



        Parameters:

            mock_settings: Patched settings with api_keys=None and api_key set.



        Behavior:

            Returns APIKeyAuth with default 'demo-user' and full read/write permissions.
        """
        mock_settings.api_keys = None
        mock_settings.api_key = "demo-key"

        result = asyncio.run(verify_api_key("demo-key", db=MagicMock()))
        assert result is not None
        assert result.api_key == "demo-key"
        assert result.user_id == "demo-user"
        assert result.permissions == ["read", "write"]

    @patch("ttskit.api.dependencies.settings")
    def test_verify_api_key_no_api_keys_attribute(self, mock_settings):
        """Verifies fallback to single api_key even when api_keys attribute is missing.



        Parameters:

            mock_settings: Patched settings without api_keys and with api_key set.



        Behavior:

            Treats missing api_keys as None, falling back to single key logic.
        """
        del mock_settings.api_keys
        mock_settings.api_key = "demo-key"

        result = asyncio.run(verify_api_key("demo-key", db=MagicMock()))
        assert result is not None
        assert result.api_key == "demo-key"
        assert result.user_id == "demo-user"

    def test_verify_api_key_invalid_key(self):
        """Verifies that verify_api_key raises a 401 error for unmatched keys.



        Behavior:

            Expects HTTPException with 401 status, detail message, and WWW-Authenticate header.
        """
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(verify_api_key("invalid_key", db=MagicMock()))

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid API key" in exc_info.value.detail
        assert exc_info.value.headers["WWW-Authenticate"] == "Bearer"

    def test_verify_api_key_none_input(self):
        """Verifies that verify_api_key returns None for None input key."""
        result = asyncio.run(verify_api_key(None, db=MagicMock()))
        assert result is None


class TestRequireAuth:
    """Tests the require_auth function for enforcing authentication.



    Notes:

        Returns the auth object if valid, otherwise raises 401 with WWW-Authenticate header.

    """

    def test_require_auth_with_valid_auth(self):
        """Verifies that require_auth passes through a valid auth object unchanged."""
        auth = APIKeyAuth(
            api_key="test_key", user_id="test_user", permissions=["read", "write"]
        )

        result = asyncio.run(require_auth(auth))
        assert result == auth

    def test_require_auth_with_none_auth(self):
        """Verifies that require_auth raises a 401 error when auth is None.



        Behavior:

            Expects HTTPException with 401 status, specific detail, and WWW-Authenticate header.
        """
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(require_auth(None))

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Authentication required" in exc_info.value.detail
        assert exc_info.value.headers["WWW-Authenticate"] == "Bearer"


class TestRequireWritePermission:
    """Tests the require_write_permission function for enforcing write access.



    Notes:

        Returns auth if it has 'write' or 'admin' permission; raises 403 otherwise.

    """

    def test_require_write_permission_with_write_permission(self):
        """Verifies that require_write_permission passes through auth with 'write' permission."""
        auth = APIKeyAuth(
            api_key="test_key", user_id="test_user", permissions=["read", "write"]
        )

        result = asyncio.run(require_write_permission(auth))
        assert result == auth

    def test_require_write_permission_without_write_permission(self):
        """Verifies that require_write_permission raises 403 for auth without 'write' permission.



        Behavior:

            Expects HTTPException with 403 status and specific detail message.
        """
        auth = APIKeyAuth(
            api_key="test_key", user_id="readonly_user", permissions=["read"]
        )

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(require_write_permission(auth))

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Write permission required" in exc_info.value.detail

    def test_require_write_permission_with_admin_permission(self):
        """Verifies that require_write_permission allows auth with 'admin' permission as a write override."""
        auth = APIKeyAuth(
            api_key="admin_key", user_id="admin", permissions=["read", "write", "admin"]
        )

        result = asyncio.run(require_write_permission(auth))
        assert result == auth


class TestCheckRateLimit:
    """Tests the check_rate_limit function for enforcing rate limits on requests.



    Notes:

        Integrates with rate_limiter; allows if under limit, raises 429 with Retry-After if exceeded; handles missing client info.

    """

    @patch("ttskit.api.dependencies.rate_limiter")
    async def test_check_rate_limit_allowed(self, mock_rate_limiter):
        """Verifies that check_rate_limit allows requests under the rate limit.



        Parameters:

            mock_rate_limiter: Patched rate_limiter with is_allowed returning True.



        Behavior:

            No exception raised; mock call verified.
        """
        async def mock_is_allowed(client_ip):
            return True, "Request allowed"

        mock_rate_limiter.is_allowed = mock_is_allowed

        request = MagicMock()
        request.client.host = "192.168.1.1"

        await check_rate_limit(request)

        assert mock_rate_limiter.is_allowed == mock_is_allowed

    @patch("ttskit.api.dependencies.rate_limiter")
    async def test_check_rate_limit_exceeded(self, mock_rate_limiter):
        """Verifies that check_rate_limit raises 429 when the rate limit is exceeded.



        Parameters:

            mock_rate_limiter: Patched rate_limiter with is_allowed returning False.



        Behavior:

            Expects HTTPException with 429 status, detail message, and Retry-After header (60 seconds).
        """
        async def mock_is_allowed(client_ip):
            return False, "Rate limit exceeded"

        mock_rate_limiter.is_allowed = mock_is_allowed

        request = MagicMock()
        request.client.host = "192.168.1.1"

        with pytest.raises(HTTPException) as exc_info:
            await check_rate_limit(request)

        assert exc_info.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert exc_info.value.detail == "Rate limit exceeded"
        assert exc_info.value.headers["Retry-After"] == "60"

    @patch("ttskit.api.dependencies.rate_limiter")
    async def test_check_rate_limit_no_client(self, mock_rate_limiter):
        """Verifies that check_rate_limit handles requests without client info (uses default IP).



        Parameters:

            mock_rate_limiter: Patched rate_limiter with is_allowed returning True.



        Behavior:

            Proceeds without raising an error, assuming a default client IP for limiting.
        """
        async def mock_is_allowed(client_ip):
            return True, "Request allowed"

        mock_rate_limiter.is_allowed = mock_is_allowed

        request = MagicMock()
        request.client = None

        await check_rate_limit(request)

        assert mock_rate_limiter.is_allowed == mock_is_allowed


class TestGetRequestInfo:
    """Tests the get_request_info function for extracting request metadata.



    Notes:

        Captures method, URL, client IP, user agent, and timestamp; defaults 'unknown' for missing client or headers.

    """

    def test_get_request_info_with_client(self):
        """Verifies get_request_info extracts full metadata when client and headers are present."""
        request = MagicMock()
        request.method = "POST"
        request.url = "https://example.com/api/v1/synth"
        request.client.host = "192.168.1.1"
        request.headers = {"user-agent": "test-agent/1.0"}

        result = asyncio.run(get_request_info(request))

        assert result["method"] == "POST"
        assert result["url"] == "https://example.com/api/v1/synth"
        assert result["client_ip"] == "192.168.1.1"
        assert result["user_agent"] == "test-agent/1.0"
        assert "timestamp" in result
        assert isinstance(result["timestamp"], float)

    def test_get_request_info_without_client(self):
        """Verifies get_request_info uses defaults for missing client info."""
        request = MagicMock()
        request.method = "GET"
        request.url = "https://example.com/health"
        request.client = None
        request.headers = {}

        result = asyncio.run(get_request_info(request))

        assert result["method"] == "GET"
        assert result["url"] == "https://example.com/health"
        assert result["client_ip"] == "unknown"
        assert result["user_agent"] == "unknown"
        assert "timestamp" in result

    def test_get_request_info_without_user_agent(self):
        """Verifies get_request_info defaults user_agent to 'unknown' when header is missing."""
        request = MagicMock()
        request.method = "PUT"
        request.url = "https://example.com/api/v1/config"
        request.client.host = "10.0.0.1"
        request.headers = {}

        result = asyncio.run(get_request_info(request))

        assert result["method"] == "PUT"
        assert result["url"] == "https://example.com/api/v1/config"
        assert result["client_ip"] == "10.0.0.1"
        assert result["user_agent"] == "unknown"


class TestDependencyTypes:
    """Basic tests confirming the existence of dependency type aliases.



    Notes:

        Ensures OptionalAuth, RequiredAuth, and WriteAuth are defined (non-None).

    """

    def test_optional_auth_type(self):
        """Verifies that OptionalAuth type is defined."""
        assert OptionalAuth is not None

    def test_required_auth_type(self):
        """Verifies that RequiredAuth type is defined."""
        assert RequiredAuth is not None

    def test_write_auth_type(self):
        """Verifies that WriteAuth type is defined."""
        assert WriteAuth is not None


class TestIntegrationScenarios:
    """Integration tests combining multiple dependency functions in auth flows.



    Notes:

        Covers full auth chain for valid/read-only users and unauthorized cases.

    """

    @patch("ttskit.api.dependencies.settings")
    def test_complete_auth_flow(self, mock_settings):
        """Verifies the full authentication pipeline for a valid user with write access.



        Parameters:

            mock_settings: Patched with api_keys for the test user.



        Behavior:

            Chains get_api_key -> verify_api_key -> require_auth -> require_write_permission, all succeeding.
        """
        mock_settings.api_keys = {"test_user": "test_key"}

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="test_key"
        )
        api_key = asyncio.run(get_api_key(credentials))
        assert api_key == "test_key"

        auth = asyncio.run(verify_api_key(api_key, db=MagicMock()))
        assert auth is not None
        assert auth.user_id == "test_user"

        result_auth = asyncio.run(require_auth(auth))
        assert result_auth == auth

        write_auth = asyncio.run(require_write_permission(result_auth))
        assert write_auth == auth

    @patch("ttskit.api.dependencies.settings")
    def test_readonly_user_flow(self, mock_settings):
        """Verifies the auth pipeline for a readonly user, failing at write permission.



        Parameters:

            mock_settings: Patched with api_keys for readonly user.



        Behavior:

            Succeeds through verify/require_auth but raises 403 on require_write_permission.
        """
        mock_settings.api_keys = {"readonly_user": "readonly_key"}

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="readonly_key"
        )
        api_key = asyncio.run(get_api_key(credentials))
        assert api_key == "readonly_key"

        auth = asyncio.run(verify_api_key(api_key, db=MagicMock()))
        assert auth is not None
        assert auth.user_id == "readonly_user"
        assert auth.permissions == ["read"]

        result_auth = asyncio.run(require_auth(auth))
        assert result_auth == auth

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(require_write_permission(result_auth))

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthorized_flow(self):
        """Verifies failure paths for unauthorized scenarios.



        Behavior:

            get_api_key(None) returns None; invalid key and None auth raise HTTPExceptions.
        """
        api_key = asyncio.run(get_api_key(None))
        assert api_key is None

        with pytest.raises(HTTPException):
            asyncio.run(verify_api_key("invalid_key", db=MagicMock()))

        with pytest.raises(HTTPException):
            asyncio.run(require_auth(None))


if __name__ == "__main__":
    pytest.main([__file__])
