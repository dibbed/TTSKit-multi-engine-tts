"""Tests for admin router endpoints in ttskit.api.routers.admin, covering user and API key management (list/create/get/delete) with authentication, success, and error scenarios using TestClient and monkeypatching, aligned with test_api_app.py style."""

from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from ttskit.api import dependencies as deps
from ttskit.api.routers import (
    admin as admin_module,
)
from ttskit.config import settings


class _UserStub:
    """Simple stub emulating ORM User model attributes for testing admin router endpoints.

    Parameters:
    - user_id: Unique identifier for the user (str).
    - username: Optional username (str or None).
    - email: Optional email address (str or None).
    - is_admin: Whether the user has admin privileges (bool, default False).
    - is_active: User activity status (bool, default True).
    - created_at: Account creation timestamp (datetime or None, defaults to now in UTC).
    - last_login: Last login timestamp (datetime or None).

    Returns:
    None. Sets instance attributes for mocked user data.
    """

    def __init__(
        self,
        user_id: str,
        username: str | None = None,
        email: str | None = None,
        is_admin: bool = False,
        is_active: bool = True,
        created_at: datetime | None = None,
        last_login: datetime | None = None,
    ) -> None:
        self.user_id = user_id
        self.username = username
        self.email = email
        self.is_admin = is_admin
        self.is_active = is_active
        self.created_at = created_at or datetime.now(timezone.utc)
        self.last_login = last_login


class _APIKeyStub:
    """Simple stub emulating ORM APIKey model attributes for testing admin router endpoints.

    Parameters:
    - id: Unique key identifier (int).
    - user_id: Associated user ID (str).
    - permissions_json: JSON string of permissions (str).
    - is_active: Key activity status (bool, default True).
    - created_at: Creation timestamp (datetime or None, defaults to now in UTC).
    - last_used: Last usage timestamp (datetime or None).
    - expires_at: Expiration timestamp (datetime or None).
    - usage_count: Number of uses (int, default 0).

    Returns:
    None. Sets instance attributes for mocked API key data.
    """

    def __init__(
        self,
        id: int,
        user_id: str,
        permissions_json: str,
        is_active: bool = True,
        created_at: datetime | None = None,
        last_used: datetime | None = None,
        expires_at: datetime | None = None,
        usage_count: int = 0,
    ) -> None:
        self.id = id
        self.user_id = user_id
        self.permissions = permissions_json
        self.is_active = is_active
        self.created_at = created_at or datetime.now(timezone.utc)
        self.last_used = last_used
        self.expires_at = expires_at
        self.usage_count = usage_count


@pytest.fixture()
def admin_test_app() -> FastAPI:
    """Creates a minimal FastAPI app with only the admin router included, avoiding full engine initialization for isolated testing."""
    app_min = FastAPI()
    app_min.include_router(admin_module.router)
    return app_min


@pytest.fixture(autouse=True)
def _test_client(admin_test_app: FastAPI):
    """Provides a fresh TestClient instance for each test, using the minimal admin app."""
    client = TestClient(admin_test_app)
    return client


@pytest.fixture()
def admin_headers(monkeypatch) -> dict[str, str]:
    """Generates authorization headers for an admin user by patching settings.api_keys with a test admin secret."""
    test_keys = dict(settings.api_keys)
    test_keys["admin"] = "admin-secret"
    monkeypatch.setattr(settings, "api_keys", test_keys, raising=False)
    return {"Authorization": "Bearer admin-secret"}


@pytest.fixture()
def writer_headers(monkeypatch) -> dict[str, str]:
    """Generates authorization headers for a writer user (write permission but no admin) by patching settings.api_keys."""
    test_keys = dict(settings.api_keys)
    test_keys["writer"] = "writer-key"
    monkeypatch.setattr(settings, "api_keys", test_keys, raising=False)
    return {"Authorization": "Bearer writer-key"}


@pytest.fixture()
def patch_admin_auth(monkeypatch, request, admin_test_app: FastAPI):
    """Overrides FastAPI dependency for authentication as an admin user with read/write/admin permissions; auto-cleans up after test."""

    async def _override():
        return deps.APIKeyAuth(
            api_key="admin-secret",
            user_id="admin",
            permissions=["read", "write", "admin"],
        )

    admin_test_app.dependency_overrides[deps.require_write_permission] = _override

    def _finalizer():
        admin_test_app.dependency_overrides.pop(deps.require_write_permission, None)

    request.addfinalizer(_finalizer)
    return True


@pytest.fixture()
def patch_writer_auth(monkeypatch, request, admin_test_app: FastAPI):
    """Overrides FastAPI dependency for authentication as a writer user (read/write permissions, no admin); auto-cleans up after test."""

    async def _override():
        return deps.APIKeyAuth(
            api_key="writer-key", user_id="writer", permissions=["read", "write"]
        )

    admin_test_app.dependency_overrides[deps.require_write_permission] = _override

    def _finalizer():
        admin_test_app.dependency_overrides.pop(deps.require_write_permission, None)

    request.addfinalizer(_finalizer)
    return True


def _patch_userservice(monkeypatch, **methods: Any) -> None:
    """Patches the UserService class in the admin router with fake implementations for specified async methods; uncalled methods raise errors."""

    class _FakeUserService:
        def __init__(self, db):
            self._db = db

    for name, impl in methods.items():
        setattr(_FakeUserService, name, staticmethod(impl))

    monkeypatch.setattr("ttskit.api.routers.admin.UserService", _FakeUserService)


class TestAdminUsers:
    """Tests for user management endpoints (list, create, get, delete) in the admin router, focusing on authentication and error handling."""


    def test_list_users_success(
        self, _test_client, admin_headers, patch_admin_auth, monkeypatch
    ):
        """Verifies successful listing of users for an admin, returning a list of user data including IDs and creation times."""
        async def get_all_users():
            return [
                _UserStub("u1", "User One", "u1@example.com", False),
                _UserStub("u2", "User Two", "u2@example.com", True),
            ]

        _patch_userservice(monkeypatch, get_all_users=get_all_users)

        resp = _test_client.get("/api/v1/admin/users", headers=admin_headers)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert isinstance(data, list) and len(data) == 2
        assert data[0]["user_id"] == "u1"
        assert "created_at" in data[0]

    def test_list_users_forbidden_without_admin(
        self, _test_client, writer_headers, patch_writer_auth, monkeypatch
    ):
        """Ensures listing users returns 403 Forbidden for non-admin users (e.g., writer role)."""
        async def get_all_users():
            return []

        _patch_userservice(monkeypatch, get_all_users=get_all_users)

        resp = _test_client.get("/api/v1/admin/users", headers=writer_headers)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_list_users_internal_error(
        self, _test_client, admin_headers, patch_admin_auth, monkeypatch
    ):
        """Tests that internal errors during user listing result in 500 Internal Server Error for admins."""
        async def get_all_users():
            raise RuntimeError("db failed")

        _patch_userservice(monkeypatch, get_all_users=get_all_users)

        resp = _test_client.get("/api/v1/admin/users", headers=admin_headers)
        assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_get_current_user_found(self, _test_client, patch_admin_auth, monkeypatch):
        """Verifies retrieval of current user details succeeds when user exists in DB, including admin status and permissions."""
        async def get_user_by_id(user_id: str):
            return _UserStub(user_id, "uname", "u@example.com", True)

        _patch_userservice(monkeypatch, get_user_by_id=get_user_by_id)

        resp = _test_client.get("/api/v1/admin/users/me")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["user_id"] == "admin"
        assert data["is_admin"] is True
        assert "permissions" in data

    def test_get_current_user_fallback(
        self, _test_client, patch_admin_auth, monkeypatch
    ):
        """Tests fallback response for current user when not found in DB, returning basic auth info with a note."""
        async def get_user_by_id(user_id: str):
            return None

        _patch_userservice(monkeypatch, get_user_by_id=get_user_by_id)

        resp = _test_client.get("/api/v1/admin/users/me")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["user_id"] == "admin"
        assert "note" in data

    def test_create_user_success(
        self, _test_client, admin_headers, patch_admin_auth, monkeypatch
    ):
        """Verifies successful user creation by admin, returning the new user object with provided details."""
        async def create_user(
            user_id: str, username: str | None, email: str | None, is_admin: bool
        ):
            return _UserStub(user_id, username, email, is_admin)

        _patch_userservice(monkeypatch, create_user=create_user)

        payload = {
            "user_id": "new_user",
            "username": "New User",
            "email": "new@example.com",
            "is_admin": False,
        }
        resp = _test_client.post(
            "/api/v1/admin/users", headers=admin_headers, json=payload
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["user_id"] == "new_user"
        assert data["is_admin"] is False

    def test_create_user_conflict(
        self, _test_client, admin_headers, patch_admin_auth, monkeypatch
    ):
        """Ensures 409 Conflict is returned when attempting to create a duplicate user ID."""
        async def create_user(
            user_id: str, username: str | None, email: str | None, is_admin: bool
        ):
            raise ValueError(f"User '{user_id}' already exists")

        _patch_userservice(monkeypatch, create_user=create_user)

        payload = {"user_id": "dup", "username": None, "email": None, "is_admin": False}
        resp = _test_client.post(
            "/api/v1/admin/users", headers=admin_headers, json=payload
        )
        assert resp.status_code == status.HTTP_409_CONFLICT

    def test_create_user_internal_error(
        self, _test_client, admin_headers, patch_admin_auth, monkeypatch
    ):
        """Tests that unexpected errors during user creation result in 500 Internal Server Error."""
        async def create_user(
            user_id: str, username: str | None, email: str | None, is_admin: bool
        ):
            raise RuntimeError("unexpected")

        _patch_userservice(monkeypatch, create_user=create_user)

        payload = {"user_id": "x", "username": None, "email": None, "is_admin": False}
        resp = _test_client.post(
            "/api/v1/admin/users", headers=admin_headers, json=payload
        )
        assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_get_user_success(
        self, _test_client, admin_headers, patch_admin_auth, monkeypatch
    ):
        """Verifies successful retrieval of a specific user by ID for an admin, returning user details."""
        async def get_user_by_id(user_id: str):
            return _UserStub(user_id, "Name", "n@example.com", False)

        _patch_userservice(monkeypatch, get_user_by_id=get_user_by_id)

        resp = _test_client.get("/api/v1/admin/users/u42", headers=admin_headers)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["user_id"] == "u42"

    def test_get_user_not_found(
        self, _test_client, admin_headers, patch_admin_auth, monkeypatch
    ):
        """Ensures 404 Not Found is returned when the requested user does not exist."""
        async def get_user_by_id(user_id: str):
            return None

        _patch_userservice(monkeypatch, get_user_by_id=get_user_by_id)

        resp = _test_client.get("/api/v1/admin/users/unknown", headers=admin_headers)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_get_user_forbidden_without_admin(
        self, _test_client, writer_headers, patch_writer_auth, monkeypatch
    ):
        """Tests that non-admin users receive 403 Forbidden when trying to get another user's details."""
        async def get_user_by_id(user_id: str):
            return _UserStub(user_id)

        _patch_userservice(monkeypatch, get_user_by_id=get_user_by_id)

        resp = _test_client.get("/api/v1/admin/users/u1", headers=writer_headers)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_get_user_internal_error(
        self, _test_client, admin_headers, patch_admin_auth, monkeypatch
    ):
        """Verifies that internal errors during user retrieval result in 500 Internal Server Error."""
        async def get_user_by_id(user_id: str):
            raise RuntimeError("boom")

        _patch_userservice(monkeypatch, get_user_by_id=get_user_by_id)

        resp = _test_client.get("/api/v1/admin/users/u1", headers=admin_headers)
        assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_delete_user_success(
        self, _test_client, admin_headers, patch_admin_auth, monkeypatch
    ):
        """Confirms successful user deletion by admin, returning a success message."""
        async def delete_user(user_id: str):
            return True

        _patch_userservice(monkeypatch, delete_user=delete_user)

        resp = _test_client.delete("/api/v1/admin/users/u99", headers=admin_headers)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert "deleted successfully" in data.get("message", "")

    def test_delete_user_not_found(
        self, _test_client, admin_headers, patch_admin_auth, monkeypatch
    ):
        """Ensures 404 Not Found when attempting to delete a non-existent user."""
        async def delete_user(user_id: str):
            return False

        _patch_userservice(monkeypatch, delete_user=delete_user)

        resp = _test_client.delete("/api/v1/admin/users/missing", headers=admin_headers)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_admin_forbidden(
        self, _test_client, admin_headers, patch_admin_auth, monkeypatch
    ):
        """Prevents deletion of the admin user itself, returning 403 Forbidden even for admins."""
        async def delete_user(user_id: str):
            return True

        _patch_userservice(monkeypatch, delete_user=delete_user)

        resp = _test_client.delete("/api/v1/admin/users/admin", headers=admin_headers)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_user_forbidden_without_admin(
        self, _test_client, writer_headers, patch_writer_auth, monkeypatch
    ):
        """Ensures non-admin users cannot delete users, returning 403 Forbidden."""
        async def delete_user(user_id: str):
            return True

        _patch_userservice(monkeypatch, delete_user=delete_user)

        resp = _test_client.delete("/api/v1/admin/users/u1", headers=writer_headers)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_user_internal_error(
        self, _test_client, admin_headers, patch_admin_auth, monkeypatch
    ):
        """Tests that errors during user deletion result in 500 Internal Server Error for admins."""
        async def delete_user(user_id: str):
            raise RuntimeError("err")

        _patch_userservice(monkeypatch, delete_user=delete_user)

        resp = _test_client.delete("/api/v1/admin/users/u1", headers=admin_headers)
        assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR




class TestAdminApiKeys:
    """Tests for API key management endpoints (list, create, update, delete) in the admin router, including permission and expiration handling."""

    def test_list_api_keys_success(self, _test_client, patch_admin_auth, monkeypatch):
        """Verifies successful listing of all API keys across users for admin, with plain keys hidden for security."""
        import json

        async def get_all_users():
            return [_UserStub("u1"), _UserStub("u2")]

        async def get_user_api_keys(user_id: str):
            return [_APIKeyStub(1, user_id, json.dumps(["read"]))]

        _patch_userservice(
            monkeypatch,
            get_all_users=get_all_users,
            get_user_api_keys=get_user_api_keys,
        )

        resp = _test_client.get("/api/v1/admin/api-keys")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert isinstance(data, list) and len(data) >= 2
        assert data[0]["api_key_plain"] == "***hidden***"

    def test_list_api_keys_forbidden(
        self, _test_client, patch_writer_auth, monkeypatch
    ):
        """Ensures non-admin users cannot list API keys, returning 403 Forbidden."""
        async def get_all_users():
            return []

        _patch_userservice(monkeypatch, get_all_users=get_all_users)

        resp = _test_client.get("/api/v1/admin/api-keys")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_create_api_key_success(self, _test_client, patch_admin_auth, monkeypatch):
        """Tests successful API key creation for a user (creating user if needed), returning key details including plain key."""
        from datetime import datetime, timezone

        async def get_user_by_id(user_id: str):
            return None

        async def create_user(
            user_id: str, username: str | None, email: str | None, is_admin: bool
        ):
            return _UserStub(user_id, username, email, is_admin)

        async def create_api_key(user_id: str, permissions: list[str], expires_at):
            return {
                "id": 10,
                "api_key": "plain-key",
                "permissions": permissions,
                "expires_at": None,
                "created_at": datetime.now(timezone.utc),
            }

        _patch_userservice(
            monkeypatch,
            get_user_by_id=get_user_by_id,
            create_user=create_user,
            create_api_key=create_api_key,
        )

        payload = {"user_id": "u1", "permissions": ["read"], "expires_at": None}
        resp = _test_client.post("/api/v1/admin/api-keys", json=payload)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["id"] == 10 and data["api_key"] == "plain-key"

    def test_create_api_key_invalid_expires(
        self, _test_client, patch_admin_auth, monkeypatch
    ):
        """Validates that invalid expiration dates in payload cause 400 Bad Request."""
        async def get_user_by_id(user_id: str):
            return _UserStub(user_id)

        _patch_userservice(monkeypatch, get_user_by_id=get_user_by_id)

        payload = {"user_id": "u1", "permissions": ["read"], "expires_at": "bad-date"}
        resp = _test_client.post("/api/v1/admin/api-keys", json=payload)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_update_api_key_success(self, _test_client, patch_admin_auth, monkeypatch):
        """Verifies successful update of an API key's permissions, activity, and expiration for a user."""
        import json

        async def get_user_api_keys(user_id: str):
            return [_APIKeyStub(3, user_id, json.dumps(["read"]))]

        async def update_api_key(
            user_id: str, api_key_id: int, permissions, is_active, expires_at
        ):
            return _APIKeyStub(api_key_id, user_id, json.dumps(permissions), True)

        _patch_userservice(
            monkeypatch,
            get_user_api_keys=get_user_api_keys,
            update_api_key=update_api_key,
        )

        payload = {
            "permissions": ["read", "write"],
            "is_active": True,
            "expires_at": None,
        }
        resp = _test_client.put("/api/v1/admin/api-keys/u1", json=payload)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["id"] == 3 and data["user_id"] == "u1"

    def test_update_api_key_not_found(
        self, _test_client, patch_admin_auth, monkeypatch
    ):
        """Returns 404 Not Found when updating a non-existent API key for the user."""
        async def get_user_api_keys(user_id: str):
            return []

        _patch_userservice(monkeypatch, get_user_api_keys=get_user_api_keys)

        payload = {"permissions": ["read"]}
        resp = _test_client.put("/api/v1/admin/api-keys/u1", json=payload)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_api_key_success(self, _test_client, patch_admin_auth, monkeypatch):
        """Confirms successful deletion of a user's API key, returning a success message."""
        import json

        async def get_user_api_keys(user_id: str):
            return [_APIKeyStub(7, user_id, json.dumps(["read"]))]

        async def delete_api_key(user_id: str, api_key_id: int):
            return True

        _patch_userservice(
            monkeypatch,
            get_user_api_keys=get_user_api_keys,
            delete_api_key=delete_api_key,
        )

        resp = _test_client.delete("/api/v1/admin/api-keys/u1")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert "deleted successfully" in data.get("message", "")

    def test_delete_api_key_not_found(
        self, _test_client, patch_admin_auth, monkeypatch
    ):
        """Returns 404 Not Found when deleting a non-existent API key for the user."""
        async def get_user_api_keys(user_id: str):
            return []

        _patch_userservice(monkeypatch, get_user_api_keys=get_user_api_keys)

        resp = _test_client.delete("/api/v1/admin/api-keys/u1")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_api_key_forbidden_admin(
        self, _test_client, patch_admin_auth, monkeypatch
    ):
        """Prevents deletion of API keys for the admin user, returning 403 Forbidden."""
        async def get_user_api_keys(user_id: str):
            return []

        _patch_userservice(monkeypatch, get_user_api_keys=get_user_api_keys)

        resp = _test_client.delete("/api/v1/admin/api-keys/admin")
        assert resp.status_code == status.HTTP_403_FORBIDDEN
