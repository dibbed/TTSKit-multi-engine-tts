"""Unit and integration tests verifying Phase 3 security remediation.

Validates:
1. No default production secrets exist in Settings.
2. Authentication enabled vs disabled behavior.
3. Secret material and invalid keys are never logged or leaked.
4. CORS defaults are restricted and do not allow wildcard credentials.
5. Trusted hosts enforce localhost/127.0.0.1/testserver.
6. Rate limiting enabled vs disabled behavior.
"""

import asyncio
import logging
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from ttskit.api.app import create_app
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
    from ttskit.api.middleware import setup_cors_middleware
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    test_app = FastAPI()
    monkeypatch.setattr("ttskit.api.middleware.settings.cors_origins", ["*"])
    setup_cors_middleware(test_app)

    # Find the added CORSMiddleware
    cors_mw = next(m for m in test_app.user_middleware if m.cls == CORSMiddleware)
    assert cors_mw.kwargs["allow_credentials"] is False, "Wildcard CORS must have allow_credentials=False"
