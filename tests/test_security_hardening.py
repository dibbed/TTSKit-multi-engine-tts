"""Unit and integration tests verifying Phase 3 security remediation.

Validates:
1. No default production secrets exist in Settings.
2. Authentication enabled vs disabled behavior.
3. Secret material and invalid keys are never logged or leaked.
4. CORS defaults are restricted and do not allow wildcard credentials.
5. Trusted hosts enforce localhost/127.0.0.1/testserver.
6. Rate limiting enabled vs disabled behavior.
"""

import logging
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from ttskit.api.dependencies import (
    APIKeyAuth,
    check_rate_limit,
    require_admin_permission,
    require_auth,
    require_write_permission,
    verify_api_key,
)
from ttskit.config import Settings


def test_no_default_production_secrets():
    """Verify that default Settings contains no usable hardcoded credentials."""
    s = Settings()
    assert s.api_key is None, "Production default api_key must not be set"
    assert s.api_keys == {}, "Production default api_keys must be empty"
    assert not hasattr(s, "test_bot_token"), "test_bot_token must not exist on Settings"


def test_cors_and_host_secure_defaults():
    """Verify CORS and allowed hosts have secure non-wildcard defaults."""
    s = Settings()
    assert "*" not in s.cors_origins, "CORS origins must not default to wildcard"
    assert "*" not in s.allowed_hosts, "Allowed hosts must not default to wildcard"
    assert "localhost" in s.allowed_hosts
    assert "127.0.0.1" in s.allowed_hosts


@pytest.mark.asyncio
async def test_auth_enabled_rejects_missing_credentials(monkeypatch):
    """When enable_auth is True, missing credentials must return None (401 at require_auth)."""
    monkeypatch.setattr("ttskit.api.dependencies.settings.enable_auth", True)
    monkeypatch.setattr("ttskit.api.dependencies.settings.api_keys", {"admin": "secure-admin-pass"})

    result = await verify_api_key(None, db=MagicMock())
    assert result is None

    with pytest.raises(HTTPException) as exc_info:
        await require_auth(result)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_auth_enabled_rejects_invalid_credentials(monkeypatch, caplog):
    """When enable_auth is True, invalid credentials raise 401 and never log secrets."""
    monkeypatch.setattr("ttskit.api.dependencies.settings.enable_auth", True)
    monkeypatch.setattr("ttskit.api.dependencies.settings.api_keys", {"admin": "secure-admin-pass"})

    secret_attempt = "super_secret_unmatched_key_12345"
    with caplog.at_level(logging.WARNING):
        with pytest.raises(HTTPException) as exc_info:
            await verify_api_key(secret_attempt, db=MagicMock())
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Invalid API key"

    # Verify secret was never logged (neither whole nor sliced)
    log_text = caplog.text
    assert secret_attempt not in log_text
    assert secret_attempt[:8] not in log_text
    assert secret_attempt[:10] not in log_text


@pytest.mark.asyncio
async def test_auth_disabled_allows_development_access(monkeypatch):
    """When enable_auth is False, unauthenticated requests succeed with dev-user."""
    monkeypatch.setattr("ttskit.api.dependencies.settings.enable_auth", False)

    result = await verify_api_key(None, db=MagicMock())
    assert result is not None
    assert result.user_id == "dev-user"
    assert "admin" in result.permissions

    # require_auth succeeds
    auth = await require_auth(result)
    assert auth.user_id == "dev-user"

    # require_write_permission succeeds
    write_auth = await require_write_permission(auth)
    assert write_auth.user_id == "dev-user"


@pytest.mark.asyncio
async def test_permission_enforcement():
    """Verify write and admin permission requirements."""
    readonly_auth = APIKeyAuth(user_id="reader", permissions=["read"])
    with pytest.raises(HTTPException) as exc_info:
        await require_write_permission(readonly_auth)
    assert exc_info.value.status_code == 403

    writer_auth = APIKeyAuth(user_id="writer", permissions=["read", "write"])
    ok_write = await require_write_permission(writer_auth)
    assert ok_write == writer_auth

    with pytest.raises(HTTPException) as exc_admin:
        await require_admin_permission(writer_auth)
    assert exc_admin.value.status_code == 403

    admin_auth = APIKeyAuth(user_id="admin", permissions=["read", "write", "admin"], is_admin=True)
    ok_admin = await require_admin_permission(admin_auth)
    assert ok_admin == admin_auth


@pytest.mark.asyncio
async def test_rate_limiting_toggle(monkeypatch):
    """Test that enable_rate_limiting controls whether rate limiting runs."""
    monkeypatch.setattr("ttskit.api.dependencies.settings.enable_rate_limiting", False)

    mock_request = MagicMock()
    mock_request.client.host = "192.168.1.50"

    # Should not raise even if limit would be exceeded
    for _ in range(10):
        await check_rate_limit(mock_request)


def test_cors_wildcard_disallows_credentials(monkeypatch):
    """Wildcard CORS origins must not be paired with allow_credentials=True."""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    from ttskit.api.middleware import setup_cors_middleware

    test_app = FastAPI()
    monkeypatch.setattr("ttskit.api.middleware.settings.cors_origins", ["*"])
    setup_cors_middleware(test_app)

    # Find the added CORSMiddleware
    cors_mw = next(m for m in test_app.user_middleware if m.cls == CORSMiddleware)
    assert cors_mw.kwargs["allow_credentials"] is False, "Wildcard CORS must have allow_credentials=False"


@pytest.mark.asyncio
async def test_verify_api_key_does_not_retain_plaintext_secret(monkeypatch):
    """Verify that verify_api_key does not retain the plaintext API key in APIKeyAuth."""
    monkeypatch.setattr("ttskit.api.dependencies.settings.enable_auth", True)
    monkeypatch.setattr("ttskit.api.dependencies.settings.api_keys", {"admin": "test-secret-key-12345"})

    auth = await verify_api_key("test-secret-key-12345", db=MagicMock())
    assert auth is not None
    assert auth.user_id == "admin"
    assert auth.api_key is None, "Plaintext API key must not be retained in APIKeyAuth"


def test_users_me_masks_key_without_leaking_fragment():
    """Verify that /admin/users/me returns masked '***' and never leaks secret fragments."""
    from unittest.mock import AsyncMock, patch
    from fastapi import FastAPI
    from ttskit.api.routers.admin import router
    from ttskit.api.dependencies import require_write_permission

    app = FastAPI()
    app.include_router(router)

    # 1. Test when user is in database
    mock_auth = APIKeyAuth(user_id="alice", permissions=["read", "write", "admin"], is_admin=True)
    app.dependency_overrides[require_write_permission] = lambda: mock_auth

    with patch("ttskit.api.routers.admin.UserService") as mock_service_cls:
        mock_service = MagicMock()
        mock_user = MagicMock()
        mock_user.user_id = "alice"
        mock_user.username = "alice"
        mock_user.email = "alice@example.com"
        mock_user.is_admin = True
        mock_user.is_active = True
        mock_user.created_at.isoformat.return_value = "2026-01-01T00:00:00"
        mock_user.last_login = None
        mock_service.get_user_by_id = AsyncMock(return_value=mock_user)
        mock_service_cls.return_value = mock_service

        client = TestClient(app)
        res = client.get("/api/v1/admin/users/me")
        assert res.status_code == 200
        data = res.json()
        assert data["api_key"] == "***"

        # 2. Test fallback when user is not in database (e.g. dev-user with api_key=None)
        mock_service.get_user_by_id = AsyncMock(return_value=None)
        res2 = client.get("/api/v1/admin/users/me")
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["api_key"] == "***"
        assert "note" in data2


def test_admin_endpoints_sanitize_500_exceptions():
    """Verify that unexpected exceptions do not leak raw exception text to clients."""
    from unittest.mock import AsyncMock, patch
    from fastapi import FastAPI
    from ttskit.api.routers.admin import router
    from ttskit.api.dependencies import require_write_permission

    app = FastAPI()
    app.include_router(router)

    mock_auth = APIKeyAuth(user_id="admin", permissions=["read", "write", "admin"], is_admin=True)
    app.dependency_overrides[require_write_permission] = lambda: mock_auth

    with patch("ttskit.api.routers.admin.UserService") as mock_service_cls:
        mock_service = MagicMock()
        mock_service.get_all_users = AsyncMock(side_effect=RuntimeError("SECRET_INTERNAL_DB_CRASH_INFO"))
        mock_service_cls.return_value = mock_service

        client = TestClient(app)
        res = client.get("/api/v1/admin/users")
        assert res.status_code == 500
        assert "SECRET_INTERNAL_DB_CRASH_INFO" not in res.text
        assert res.json()["detail"] == "Internal server error"


def test_ttskit_prefixed_environment_variables(monkeypatch):
    """Verify that TTSKIT_ prefixed environment variables configure Settings properly."""
    from ttskit.config import Settings

    monkeypatch.setenv("TTSKIT_BOT_TOKEN", "123456789:ABCdefGHIjklMNOpqrsTUVwxyz123456789")
    monkeypatch.setenv("TTSKIT_RATE_LIMITING", "true")
    monkeypatch.setenv("TTSKIT_CACHE_ENABLED", "false")
    monkeypatch.setenv("TTSKIT_LOG_LEVEL", "warning")
    monkeypatch.setenv("TTSKIT_API_PORT", "9090")

    s = Settings()
    assert s.bot_token == "123456789:ABCdefGHIjklMNOpqrsTUVwxyz123456789"
    assert s.enable_rate_limiting is True
    assert s.cache_enabled is False
    assert s.enable_caching is False
    assert s.log_level == "WARNING"
    assert s.api_port == 9090

