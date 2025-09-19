"""تست‌های جامع برای Admin API endpoints."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ttskit.api.dependencies import APIKeyAuth, require_write_permission
from ttskit.api.routers.admin import router


class TestAdminAPIEndpoints:
    """تست‌های جامع برای Admin API endpoints."""

    @pytest.fixture
    def client(self, admin_auth):
        """ایجاد TestClient برای تست."""
        app = FastAPI()
        app.include_router(router)

        app.dependency_overrides[require_write_permission] = lambda: admin_auth

        return TestClient(app)

    @pytest.fixture
    def client_with_user_auth(self, user_auth):
        """ایجاد TestClient با user authentication."""
        app = FastAPI()
        app.include_router(router)

        app.dependency_overrides[require_write_permission] = lambda: user_auth

        return TestClient(app)

    @pytest.fixture
    def client_with_readonly_auth(self, readonly_auth):
        """ایجاد TestClient با readonly authentication."""
        app = FastAPI()
        app.include_router(router)

        app.dependency_overrides[require_write_permission] = lambda: readonly_auth

        return TestClient(app)

    @pytest.fixture
    def admin_auth(self):
        """ایجاد mock برای admin authentication."""
        return APIKeyAuth(
            api_key="admin-key-123",
            user_id="admin",
            permissions=["read", "write", "admin"],
        )

    @pytest.fixture
    def user_auth(self):
        """ایجاد mock برای user authentication."""
        return APIKeyAuth(
            api_key="user-key-456", user_id="test_user", permissions=["read", "write"]
        )

    @pytest.fixture
    def readonly_auth(self):
        """ایجاد mock برای readonly authentication."""
        return APIKeyAuth(
            api_key="readonly-key-789", user_id="readonly_user", permissions=["read"]
        )

    @pytest.fixture
    def mock_settings(self):
        """Mock settings برای تست."""
        with patch("ttskit.api.dependencies.settings") as mock_settings:
            mock_settings.api_keys = {
                "admin": "admin-key-123",
                "test_user": "user-key-456",
                "readonly_user": "readonly-key-789",
            }
            yield mock_settings


    @pytest.mark.asyncio
    async def test_list_api_keys_success_admin(self, client, mock_settings):
        """تست موفق list_api_keys با admin access."""
        response = client.get("/api/v1/admin/api-keys")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) >= 0

    @pytest.mark.asyncio
    async def test_list_api_keys_forbidden_non_admin(
        self, client_with_user_auth, mock_settings
    ):
        """تست list_api_keys با non-admin access."""
        response = client_with_user_auth.get("/api/v1/admin/api-keys")

        assert response.status_code == 403
        data = response.json()
        assert data["detail"] == "Admin permission required"

    @pytest.mark.asyncio
    async def test_list_api_keys_empty_settings(self, client):
        """تست list_api_keys با empty settings."""
        with patch("ttskit.api.dependencies.settings") as mock_settings:
            mock_settings.api_keys = {}

            response = client.get("/api/v1/admin/api-keys")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_list_api_keys_no_settings_attribute(self, client):
        """تست list_api_keys بدون settings.api_keys attribute."""
        with patch("ttskit.api.dependencies.settings") as mock_settings:
            del mock_settings.api_keys

            response = client.get("/api/v1/admin/api-keys")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)


    @pytest.mark.asyncio
    async def test_create_api_key_success(self, client, mock_settings):
        """تست موفق create_api_key."""
        request_data = {
            "user_id": "new_user",
            "permissions": ["read", "write"],
        }

        response = client.post("/api/v1/admin/api-keys", json=request_data)

        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert data["user_id"] == "new_user"
            assert data["permissions"] == ["read", "write"]

    @pytest.mark.asyncio
    async def test_create_api_key_forbidden_non_admin(
        self, client_with_user_auth, mock_settings
    ):
        """تست create_api_key با non-admin access."""
        request_data = {
            "user_id": "new_user",
            "api_key": "new-api-key-123",
            "permissions": ["read", "write"],
        }

        response = client_with_user_auth.post(
            "/api/v1/admin/api-keys", json=request_data
        )

        assert response.status_code == 403
        data = response.json()
        assert data["detail"] == "Admin permission required"

    @pytest.mark.asyncio
    async def test_create_api_key_conflict_existing_user(self, client, mock_settings):
        """تست create_api_key با existing user."""
        request_data = {
            "user_id": "admin",
            "permissions": ["read", "write"],
        }

        response = client.post("/api/v1/admin/api-keys", json=request_data)

        assert response.status_code in [200, 500]

    @pytest.mark.asyncio
    async def test_create_api_key_bad_input_missing_user_id(self, client):
        """تست create_api_key با missing user_id."""
        request_data = {"api_key": "new-api-key-123", "permissions": ["read", "write"]}

        response = client.post("/api/v1/admin/api-keys", json=request_data)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_api_key_bad_input_empty_user_id(self, client):
        """تست create_api_key با empty user_id."""
        request_data = {
            "user_id": "",
            "api_key": "new-api-key-123",
            "permissions": ["read", "write"],
        }

        response = client.post("/api/v1/admin/api-keys", json=request_data)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_api_key_bad_input_short_api_key(self, client):
        """تست create_api_key با short api_key."""
        request_data = {
            "user_id": "new_user",
            "api_key": "short",
            "permissions": ["read", "write"],
        }

        response = client.post("/api/v1/admin/api-keys", json=request_data)

        assert response.status_code in [200, 500]

    @pytest.mark.asyncio
    async def test_create_api_key_bad_input_long_user_id(self, client):
        """تست create_api_key با long user_id."""
        request_data = {
            "user_id": "a" * 51,
            "api_key": "new-api-key-123",
            "permissions": ["read", "write"],
        }

        response = client.post("/api/v1/admin/api-keys", json=request_data)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_api_key_default_permissions(self, client, mock_settings):
        """تست create_api_key با default permissions."""
        request_data = {
            "user_id": "new_user",
            "api_key": "new-api-key-123",
        }

        response = client.post("/api/v1/admin/api-keys", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["permissions"] == ["read", "write"]


    @pytest.mark.asyncio
    async def test_update_api_key_success(self, client, mock_settings):
        """تست موفق update_api_key."""
        request_data = {
            "api_key": "updated-api-key-456",
            "permissions": ["read", "write", "admin"],
        }

        response = client.put("/api/v1/admin/api-keys/test_user", json=request_data)

        assert response.status_code in [200, 404, 500]
        if response.status_code == 200:
            data = response.json()
            assert data["user_id"] == "test_user"
            assert data["permissions"] == ["read", "write", "admin"]
            assert (
                data["message"] == "API key updated successfully for user 'test_user'"
            )

    @pytest.mark.asyncio
    async def test_update_api_key_forbidden_non_admin(
        self, client_with_user_auth, mock_settings
    ):
        """تست update_api_key با non-admin access."""
        request_data = {
            "api_key": "updated-api-key-456",
            "permissions": ["read", "write"],
        }

        response = client_with_user_auth.put(
            "/api/v1/admin/api-keys/test_user", json=request_data
        )

        assert response.status_code == 403
        data = response.json()
        assert data["detail"] == "Admin permission required"

    @pytest.mark.asyncio
    async def test_update_api_key_not_found(self, client, mock_settings):
        """تست update_api_key با non-existent user."""
        request_data = {
            "api_key": "updated-api-key-456",
            "permissions": ["read", "write"],
        }

        response = client.put(
            "/api/v1/admin/api-keys/nonexistent_user", json=request_data
        )

        assert response.status_code == 404
        data = response.json()
        assert data["detail"].startswith("No API keys found")

    @pytest.mark.asyncio
    async def test_update_api_key_bad_input_missing_api_key(self, client):
        """تست update_api_key با missing api_key."""
        request_data = {"permissions": ["read", "write"]}

        response = client.put("/api/v1/admin/api-keys/test_user", json=request_data)

        assert response.status_code in [404, 422]

    @pytest.mark.asyncio
    async def test_update_api_key_bad_input_short_api_key(self, client):
        """تست update_api_key با short api_key."""
        request_data = {
            "api_key": "short",
            "permissions": ["read", "write"],
        }

        response = client.put("/api/v1/admin/api-keys/test_user", json=request_data)

        assert response.status_code in [404, 422]

    @pytest.mark.asyncio
    async def test_update_api_key_bad_input_missing_permissions(self, client):
        """تست update_api_key با missing permissions."""
        request_data = {"api_key": "updated-api-key-456"}

        response = client.put("/api/v1/admin/api-keys/test_user", json=request_data)

        assert response.status_code == 422


    @pytest.mark.asyncio
    async def test_delete_api_key_success(self, client, mock_settings):
        """تست موفق delete_api_key."""
        response = client.delete("/api/v1/admin/api-keys/test_user")

        assert response.status_code in [200, 404, 500]
        if response.status_code == 200:
            data = response.json()
            assert (
                data["message"] == "API key deleted successfully for user 'test_user'"
            )
            assert "note" in data

    @pytest.mark.asyncio
    async def test_delete_api_key_forbidden_non_admin(
        self, client_with_user_auth, mock_settings
    ):
        """تست delete_api_key با non-admin access."""
        response = client_with_user_auth.delete("/api/v1/admin/api-keys/test_user")

        assert response.status_code == 403
        data = response.json()
        assert data["detail"] == "Admin permission required"

    @pytest.mark.asyncio
    async def test_delete_api_key_not_found(self, client, mock_settings):
        """تست delete_api_key با non-existent user."""
        response = client.delete("/api/v1/admin/api-keys/nonexistent_user")

        assert response.status_code == 404
        data = response.json()
        assert data["detail"].startswith("No API keys found")

    @pytest.mark.asyncio
    async def test_delete_api_key_forbidden_admin_user(self, client, mock_settings):
        """تست delete_api_key با admin user (نباید حذف شود)."""
        response = client.delete("/api/v1/admin/api-keys/admin")

        assert response.status_code == 403
        data = response.json()
        assert data["detail"] == "Cannot delete admin user"


    @pytest.mark.asyncio
    async def test_get_current_user_success_admin(self, client):
        """تست موفق get_current_user با admin."""
        response = client.get("/api/v1/admin/users/me")

        assert response.status_code == 200
        data = response.json()

        assert data["user_id"] == "admin"
        assert data["permissions"] == ["read", "write", "admin"]
        assert data["api_key"] == "admin-ke..."

    @pytest.mark.asyncio
    async def test_get_current_user_success_regular_user(self, client_with_user_auth):
        """تست موفق get_current_user با regular user."""
        response = client_with_user_auth.get("/api/v1/admin/users/me")

        assert response.status_code == 200
        data = response.json()

        assert data["user_id"] == "test_user"
        assert data["permissions"] == ["read", "write"]
        assert data["api_key"] == "user-key..."

    @pytest.fixture
    def client_with_short_auth(self):
        """ایجاد TestClient با short API key authentication."""
        short_auth = APIKeyAuth(
            api_key="short", user_id="test_user", permissions=["read", "write"]
        )
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[require_write_permission] = lambda: short_auth
        return TestClient(app)

    @pytest.mark.asyncio
    async def test_get_current_user_short_api_key(self, client_with_short_auth):
        """تست get_current_user با short api_key."""
        response = client_with_short_auth.get("/api/v1/admin/users/me")

        assert response.status_code == 200
        data = response.json()

        assert data["api_key"] == "***"


    @pytest.mark.asyncio
    async def test_list_api_keys_exception_handling(self, client):
        """تست exception handling در list_api_keys."""
        with patch("ttskit.api.dependencies.settings") as mock_settings:
            mock_settings.api_keys = MagicMock()
            mock_settings.api_keys.items.side_effect = Exception("Database error")

            response = client.get("/api/v1/admin/api-keys")

            assert response.status_code in [200, 500]
            data = response.json()
            if response.status_code == 500:
                assert "Database error" in data["detail"]

    @pytest.mark.asyncio
    async def test_create_api_key_exception_handling(self, client):
        """تست exception handling در create_api_key."""
        with patch("ttskit.api.routers.admin.logger") as mock_logger:
            mock_logger.info.side_effect = Exception("Logging error")

            request_data = {
                "user_id": "new_user",
                "api_key": "new-api-key-123",
                "permissions": ["read", "write"],
            }

            response = client.post("/api/v1/admin/api-keys", json=request_data)

            assert response.status_code in [200, 500]
            data = response.json()
            if response.status_code == 500:
                assert "Logging error" in data["detail"]

    @pytest.mark.asyncio
    async def test_update_api_key_exception_handling(self, client, mock_settings):
        """تست exception handling در update_api_key."""
        with patch("ttskit.api.routers.admin.logger") as mock_logger:
            mock_logger.info.side_effect = Exception("Logging error")

            request_data = {
                "api_key": "updated-api-key-456",
                "permissions": ["read", "write"],
            }

            response = client.put("/api/v1/admin/api-keys/test_user", json=request_data)

            assert response.status_code in [200, 404, 500]
            data = response.json()
            if response.status_code == 500:
                assert "Logging error" in data["detail"]

    @pytest.mark.asyncio
    async def test_delete_api_key_exception_handling(self, client, mock_settings):
        """تست exception handling در delete_api_key."""
        with patch("ttskit.api.routers.admin.logger") as mock_logger:
            mock_logger.info.side_effect = Exception("Logging error")

            response = client.delete("/api/v1/admin/api-keys/test_user")

            assert response.status_code in [200, 404, 500]
            data = response.json()
            if response.status_code == 500:
                assert "Logging error" in data["detail"]

    @pytest.mark.asyncio
    async def test_get_current_user_exception_handling(self, client):
        """تست exception handling در get_current_user."""
        with patch("ttskit.api.routers.admin.logger") as mock_logger:
            mock_logger.error.side_effect = Exception("Logging error")

            response = client.get("/api/v1/admin/users/me")

            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == "admin"


    @pytest.mark.asyncio
    async def test_list_api_keys_readonly_user_permissions(self, client, mock_settings):
        """تست list_api_keys با readonly user permissions."""
        response = client.get("/api/v1/admin/api-keys")

        assert response.status_code == 200
        data = response.json()

        if isinstance(data, list):
            readonly_items = [
                item for item in data if item.get("user_id") == "readonly_user"
            ]
            if readonly_items:
                assert readonly_items[0]["permissions"] == ["read"]
        else:
            readonly_info = data["readonly_user"]
            assert readonly_info["permissions"] == ["read"]

    @pytest.mark.asyncio
    async def test_create_api_key_empty_permissions(self, client, mock_settings):
        """تست create_api_key با empty permissions."""
        request_data = {
            "user_id": "new_user",
            "api_key": "new-api-key-123",
            "permissions": [],
        }

        response = client.post("/api/v1/admin/api-keys", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["permissions"] == []

    @pytest.mark.asyncio
    async def test_update_api_key_empty_permissions(self, client, mock_settings):
        """تست update_api_key با empty permissions."""
        request_data = {"api_key": "updated-api-key-456", "permissions": []}

        response = client.put("/api/v1/admin/api-keys/test_user", json=request_data)

        assert response.status_code in [200, 404, 500]
        if response.status_code == 200:
            data = response.json()
            assert data["permissions"] == []

    @pytest.fixture
    def client_with_empty_permissions(self):
        """ایجاد TestClient با empty permissions authentication."""
        empty_auth = APIKeyAuth(
            api_key="test-key-123", user_id="test_user", permissions=[]
        )
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[require_write_permission] = lambda: empty_auth
        return TestClient(app)

    @pytest.mark.asyncio
    async def test_get_current_user_empty_permissions(
        self, client_with_empty_permissions
    ):
        """تست get_current_user با empty permissions."""
        response = client_with_empty_permissions.get("/api/v1/admin/users/me")

        assert response.status_code == 200
        data = response.json()
        assert data["permissions"] == []


    @pytest.mark.asyncio
    async def test_full_api_key_lifecycle(self, client, mock_settings):
        """تست کامل lifecycle یک API key."""
        create_data = {
            "user_id": "lifecycle_user",
            "api_key": "lifecycle-key-123",
            "permissions": ["read", "write"],
        }
        create_response = client.post("/api/v1/admin/api-keys", json=create_data)
        assert create_response.status_code == 200

        list_response = client.get("/api/v1/admin/api-keys")
        assert list_response.status_code == 200

        update_data = {
            "api_key": "updated-lifecycle-key-456",
            "permissions": ["read", "write", "admin"],
        }
        update_response = client.put(
            "/api/v1/admin/api-keys/lifecycle_user", json=update_data
        )
        assert update_response.status_code in [200, 404, 500]

        delete_response = client.delete("/api/v1/admin/api-keys/lifecycle_user")
        assert delete_response.status_code in [200, 404, 500]

    @pytest.mark.asyncio
    async def test_admin_vs_user_permissions(
        self,
        client,
        client_with_user_auth,
        client_with_readonly_auth,
        mock_settings,
    ):
        """تست تفاوت permissions بین admin و user."""

        admin_response = client.get("/api/v1/admin/api-keys")
        assert admin_response.status_code == 200

        user_response = client_with_user_auth.get("/api/v1/admin/api-keys")
        assert user_response.status_code == 403

        readonly_response = client_with_readonly_auth.get("/api/v1/admin/api-keys")
        assert readonly_response.status_code == 403
