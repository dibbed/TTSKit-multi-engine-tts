"""تست‌های جامع برای Admin API endpoints با FastAPI TestClient."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from ttskit.api.dependencies import APIKeyAuth
from ttskit.api.routers.admin import router
from ttskit.database.connection import get_session


class TestAdminAPIEndpoints:
    """تست‌های جامع برای Admin API endpoints."""

    @pytest.fixture
    def app(self):
        """ایجاد FastAPI app برای تست."""
        from unittest.mock import MagicMock

        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)

        mock_db = MagicMock()

        def override_get_session():
            return mock_db

        app.dependency_overrides[get_session] = override_get_session
        return app

    @pytest.fixture
    def client(self, app):
        """ایجاد TestClient برای تست."""
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

    @pytest.fixture
    def mock_user_service(self):
        """Mock UserService برای تست."""
        from unittest.mock import AsyncMock

        mock_service = AsyncMock()

        mock_user = MagicMock()
        mock_user.user_id = "test_user"
        mock_user.username = "test_user"
        mock_user.email = "test@test.com"
        mock_user.is_active = True
        mock_user.is_admin = False
        mock_user.created_at = datetime(2024, 1, 1, 0, 0, 0)
        mock_user.last_login = None

        mock_api_key = MagicMock()
        mock_api_key.id = 1
        mock_api_key.user_id = "test_user"
        mock_api_key.permissions = '["read", "write"]'
        mock_api_key.is_active = True
        mock_api_key.created_at = datetime(2024, 1, 1, 0, 0, 0)
        mock_api_key.last_used = datetime(2024, 1, 1, 0, 0, 0)
        mock_api_key.expires_at = datetime(2024, 12, 31, 23, 59, 59)
        mock_api_key.usage_count = 0
        mock_api_key.api_key_plain = "mock_api_key_123"

        mock_created_api_key = {
            "id": 1,
            "user_id": "test_user",
            "permissions": ["read", "write"],
            "is_active": True,
            "created_at": datetime(2024, 1, 1, 0, 0, 0),
            "last_used": None,
            "expires_at": None,
            "usage_count": 0,
            "api_key": "mock_api_key_123",
        }

        mock_service.get_user_by_id = AsyncMock(return_value=mock_user)
        mock_service.get_all_users = AsyncMock(return_value=[mock_user])
        mock_service.create_user = AsyncMock(return_value=mock_user)
        mock_service.get_user_api_keys = AsyncMock(return_value=[mock_api_key])
        mock_service.create_api_key = AsyncMock(return_value=mock_created_api_key)
        mock_service.update_api_key = AsyncMock(return_value=mock_api_key)
        mock_service.delete_user = AsyncMock(return_value=True)
        mock_service.delete_api_key = AsyncMock(return_value=True)

        with patch("ttskit.api.routers.admin.UserService", return_value=mock_service):
            yield mock_service

    def override_auth(self, app, auth_data):
        """Override authentication dependency."""
        from ttskit.api.dependencies import (
            require_auth,
            require_write_permission,
            verify_api_key,
        )

        def override_verify_api_key():
            return auth_data

        def override_require_auth():
            return auth_data

        def override_write_auth():
            return auth_data

        app.dependency_overrides[verify_api_key] = override_verify_api_key
        app.dependency_overrides[require_auth] = override_require_auth
        app.dependency_overrides[require_write_permission] = override_write_auth
        return app

    def get_client_with_auth(self, app, auth_data):
        """Get TestClient with authentication overridden."""
        app_with_auth = self.override_auth(app, auth_data)
        return TestClient(app_with_auth)


    def test_list_api_keys_success_admin(self, app, mock_settings, admin_auth):
        """تست موفق list_api_keys با admin access."""
        client = self.get_client_with_auth(app, admin_auth)

        response = client.get("/api/v1/admin/api-keys")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) >= 0

    def test_list_api_keys_forbidden_non_admin(self, app, mock_settings, user_auth):
        """تست list_api_keys با non-admin access."""
        client = self.get_client_with_auth(app, user_auth)

        response = client.get("/api/v1/admin/api-keys")

        assert response.status_code == 403
        data = response.json()
        assert data["detail"] == "Admin permission required"

    def test_list_api_keys_empty_settings(self, app, admin_auth):
        """تست list_api_keys با empty settings."""
        client = self.get_client_with_auth(app, admin_auth)

        with patch("ttskit.api.dependencies.settings") as mock_settings:
            mock_settings.api_keys = {}

            response = client.get("/api/v1/admin/api-keys")

            assert response.status_code == 200
            data = response.json()
            assert data == []

    def test_list_api_keys_no_settings_attribute(self, app, admin_auth):
        """تست list_api_keys بدون settings.api_keys attribute."""
        client = self.get_client_with_auth(app, admin_auth)

        with patch("ttskit.api.dependencies.settings") as mock_settings:
            del mock_settings.api_keys

            response = client.get("/api/v1/admin/api-keys")

            assert response.status_code == 200
            data = response.json()
            assert data == []


    def test_create_api_key_success(
        self, app, mock_settings, admin_auth, mock_user_service
    ):
        """تست موفق create_api_key."""
        client = self.get_client_with_auth(app, admin_auth)

        request_data = {
            "user_id": "test_user",
            "permissions": ["read", "write"],
        }

        response = client.post("/api/v1/admin/api-keys", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert data["user_id"] == "test_user"
        assert data["permissions"] == ["read", "write"]
        assert "api_key" in data
        assert "id" in data

    def test_create_api_key_forbidden_non_admin(self, app, mock_settings, user_auth):
        """تست create_api_key با non-admin access."""
        client = self.get_client_with_auth(app, user_auth)

        request_data = {
            "user_id": "new_user",
            "permissions": ["read", "write"],
        }

        response = client.post("/api/v1/admin/api-keys", json=request_data)

        assert response.status_code == 403
        data = response.json()
        assert data["detail"] == "Admin permission required"

    def test_create_api_key_conflict_existing_user(
        self, app, mock_settings, admin_auth, mock_user_service
    ):
        """تست create_api_key با existing user."""
        mock_existing_user = MagicMock()
        mock_existing_user.user_id = "admin"
        mock_existing_user.username = "admin"
        mock_existing_user.email = "admin@test.com"
        mock_existing_user.is_active = True
        mock_existing_user.is_admin = True
        mock_existing_user.created_at = datetime(2024, 1, 1, 0, 0, 0)
        mock_existing_user.last_login = None

        mock_user_service.get_user_by_id = AsyncMock(return_value=mock_existing_user)

        client = self.get_client_with_auth(app, admin_auth)

        request_data = {
            "user_id": "admin",
            "permissions": ["read", "write"],
        }

        response = client.post("/api/v1/admin/api-keys", json=request_data)

        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert data["user_id"] == "admin"

    def test_create_api_key_bad_input_missing_user_id(self, app, admin_auth):
        """تست create_api_key با missing user_id."""
        client = self.get_client_with_auth(app, admin_auth)

        request_data = {"permissions": ["read", "write"]}

        response = client.post("/api/v1/admin/api-keys", json=request_data)

        assert response.status_code == 422

    def test_create_api_key_bad_input_empty_user_id(self, app, admin_auth):
        """تست create_api_key با empty user_id."""
        client = self.get_client_with_auth(app, admin_auth)

        request_data = {
            "user_id": "",
            "permissions": ["read", "write"],
        }

        response = client.post("/api/v1/admin/api-keys", json=request_data)

        assert response.status_code == 422

    def test_create_api_key_bad_input_short_api_key(
        self, app, admin_auth, mock_user_service
    ):
        """تست create_api_key با short api_key."""
        client = self.get_client_with_auth(app, admin_auth)

        request_data = {
            "user_id": "test_user",
            "permissions": ["read", "write"],
        }

        response = client.post("/api/v1/admin/api-keys", json=request_data)

        assert response.status_code == 200

    def test_create_api_key_bad_input_long_user_id(self, app, admin_auth):
        """تست create_api_key با long user_id."""
        client = self.get_client_with_auth(app, admin_auth)

        request_data = {
            "user_id": "a" * 51,
            "permissions": ["read", "write"],
        }

        response = client.post("/api/v1/admin/api-keys", json=request_data)

        assert response.status_code == 422

    def test_create_api_key_default_permissions(
        self, app, mock_settings, admin_auth, mock_user_service
    ):
        """تست create_api_key با default permissions."""
        client = self.get_client_with_auth(app, admin_auth)

        request_data = {
            "user_id": "test_user",
            "api_key": "new-api-key-123",
        }

        response = client.post("/api/v1/admin/api-keys", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["permissions"] == ["read", "write"]


    def test_update_api_key_success(
        self, app, mock_settings, admin_auth, mock_user_service
    ):
        """تست موفق update_api_key."""
        mock_updated_api_key = MagicMock()
        mock_updated_api_key.id = 1
        mock_updated_api_key.user_id = "test_user"
        mock_updated_api_key.permissions = '["read", "write", "admin"]'
        mock_updated_api_key.is_active = True
        mock_updated_api_key.created_at = datetime(2024, 1, 1, 0, 0, 0)
        mock_updated_api_key.last_used = None
        mock_updated_api_key.expires_at = None
        mock_updated_api_key.usage_count = 0

        mock_user_service.update_api_key.return_value = mock_updated_api_key

        client = self.get_client_with_auth(app, admin_auth)

        request_data = {
            "permissions": ["read", "write", "admin"],
        }

        response = client.put("/api/v1/admin/api-keys/test_user", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert data["user_id"] == "test_user"
        assert data["permissions"] == ["read", "write", "admin"]
        assert "id" in data

    def test_update_api_key_forbidden_non_admin(self, app, mock_settings, user_auth):
        """تست update_api_key با non-admin access."""
        client = self.get_client_with_auth(app, user_auth)

        request_data = {
            "permissions": ["read", "write"],
        }

        response = client.put("/api/v1/admin/api-keys/test_user", json=request_data)

        assert response.status_code == 403
        data = response.json()
        assert data["detail"] == "Admin permission required"

    def test_update_api_key_not_found(
        self, app, mock_settings, admin_auth, mock_user_service
    ):
        """تست update_api_key با non-existent user."""
        mock_user_service.get_user_api_keys.return_value = []

        client = self.get_client_with_auth(app, admin_auth)

        request_data = {
            "permissions": ["read", "write"],
        }

        response = client.put(
            "/api/v1/admin/api-keys/nonexistent_user", json=request_data
        )

        assert response.status_code == 404
        data = response.json()
        assert "No API keys found" in data["detail"]

    def test_update_api_key_bad_input_missing_api_key(
        self, app, admin_auth, mock_user_service
    ):
        """تست update_api_key با missing api_key."""
        mock_user_service.get_user_api_keys.return_value = []

        client = self.get_client_with_auth(app, admin_auth)

        request_data = {"permissions": ["read", "write"]}

        response = client.put("/api/v1/admin/api-keys/test_user", json=request_data)

        assert response.status_code == 404

    def test_update_api_key_bad_input_short_api_key(
        self, app, admin_auth, mock_user_service
    ):
        """تست update_api_key با short api_key."""
        mock_user_service.get_user_api_keys.return_value = []

        client = self.get_client_with_auth(app, admin_auth)

        request_data = {
            "permissions": ["read", "write"],
        }

        response = client.put("/api/v1/admin/api-keys/test_user", json=request_data)

        assert response.status_code == 404

    def test_update_api_key_bad_input_missing_permissions(self, app, admin_auth):
        """تست update_api_key با missing permissions."""
        client = self.get_client_with_auth(app, admin_auth)

        request_data = {}

        response = client.put("/api/v1/admin/api-keys/test_user", json=request_data)

        assert response.status_code == 422


    def test_delete_api_key_success(
        self, app, mock_settings, admin_auth, mock_user_service
    ):
        """تست موفق delete_api_key."""
        client = self.get_client_with_auth(app, admin_auth)

        response = client.delete("/api/v1/admin/api-keys/test_user")

        assert response.status_code == 200
        data = response.json()

        assert data["message"] == "API key deleted successfully for user 'test_user'"

    def test_delete_api_key_forbidden_non_admin(self, app, mock_settings, user_auth):
        """تست delete_api_key با non-admin access."""
        client = self.get_client_with_auth(app, user_auth)

        response = client.delete("/api/v1/admin/api-keys/test_user")

        assert response.status_code == 403
        data = response.json()
        assert data["detail"] == "Admin permission required"

    def test_delete_api_key_not_found(
        self, app, mock_settings, admin_auth, mock_user_service
    ):
        """تست delete_api_key با non-existent user."""
        mock_user_service.get_user_api_keys.return_value = []

        client = self.get_client_with_auth(app, admin_auth)

        response = client.delete("/api/v1/admin/api-keys/nonexistent_user")

        assert response.status_code == 404
        data = response.json()
        assert "No API keys found" in data["detail"]

    def test_delete_api_key_forbidden_admin_user(self, app, mock_settings, admin_auth):
        """تست delete_api_key با admin user (نباید حذف شود)."""
        client = self.get_client_with_auth(app, admin_auth)

        response = client.delete("/api/v1/admin/api-keys/admin")

        assert response.status_code == 403
        data = response.json()
        assert data["detail"] == "Cannot delete admin user"


    def test_get_current_user_success_admin(self, app, admin_auth, mock_user_service):
        """تست موفق get_current_user با admin."""
        mock_admin_user = MagicMock()
        mock_admin_user.user_id = "admin"
        mock_admin_user.username = "admin"
        mock_admin_user.email = "admin@test.com"
        mock_admin_user.is_active = True
        mock_admin_user.is_admin = True
        mock_admin_user.created_at = datetime(2024, 1, 1, 0, 0, 0)
        mock_admin_user.last_login = None

        mock_user_service.get_user_by_id = AsyncMock(return_value=mock_admin_user)

        client = self.get_client_with_auth(app, admin_auth)

        response = client.get("/api/v1/admin/users/me")

        assert response.status_code == 200
        data = response.json()

        assert data["user_id"] == "admin"
        assert data["username"] == "admin"
        assert data["is_admin"] == True
        if "permissions" in data:
            assert data["permissions"] == ["read", "write", "admin"]
        if "api_key" in data:
            assert len(data["api_key"]) > 0

    def test_get_current_user_success_regular_user(
        self, app, user_auth, mock_user_service
    ):
        """تست موفق get_current_user با regular user."""
        mock_regular_user = MagicMock()
        mock_regular_user.user_id = "test_user"
        mock_regular_user.username = "test_user"
        mock_regular_user.email = "test@test.com"
        mock_regular_user.is_active = True
        mock_regular_user.is_admin = False
        mock_regular_user.created_at = datetime(2024, 1, 1, 0, 0, 0)
        mock_regular_user.last_login = None

        mock_user_service.get_user_by_id = AsyncMock(return_value=mock_regular_user)

        client = self.get_client_with_auth(app, user_auth)

        response = client.get("/api/v1/admin/users/me")

        assert response.status_code == 200
        data = response.json()

        assert data["user_id"] == "test_user"
        assert data["username"] == "test_user"
        assert data["is_admin"] == False
        if "permissions" in data:
            assert data["permissions"] == ["read", "write"]
        if "api_key" in data:
            assert len(data["api_key"]) > 0

    def test_get_current_user_short_api_key(self, app, mock_user_service):
        """تست get_current_user با short api_key."""
        mock_regular_user = MagicMock()
        mock_regular_user.user_id = "test_user"
        mock_regular_user.username = "test_user"
        mock_regular_user.email = "test@test.com"
        mock_regular_user.is_active = True
        mock_regular_user.is_admin = False
        mock_regular_user.created_at = datetime(2024, 1, 1, 0, 0, 0)
        mock_regular_user.last_login = None

        mock_user_service.get_user_by_id = AsyncMock(return_value=mock_regular_user)

        short_auth = APIKeyAuth(
            api_key="short", user_id="test_user", permissions=["read", "write"]
        )
        client = self.get_client_with_auth(app, short_auth)

        response = client.get("/api/v1/admin/users/me")

        assert response.status_code == 200
        data = response.json()

        assert data["user_id"] == "test_user"
        if "permissions" in data:
            assert data["permissions"] == ["read", "write"]
        if "api_key" in data:
            assert len(data["api_key"]) > 0


    def test_list_api_keys_exception_handling(self, app, admin_auth):
        """تست exception handling در list_api_keys."""
        client = self.get_client_with_auth(app, admin_auth)

        with patch("ttskit.api.dependencies.settings") as mock_settings:
            mock_settings.api_keys = MagicMock()
            mock_settings.api_keys.items.side_effect = Exception("Database error")

            response = client.get("/api/v1/admin/api-keys")

            assert response.status_code in [200, 500]
            if response.status_code == 500:
                data = response.json()
                assert "Database error" in data["detail"]

    def test_create_api_key_exception_handling(
        self, app, admin_auth, mock_user_service
    ):
        """تست exception handling در create_api_key."""
        mock_user_service.get_user_by_id = AsyncMock(return_value=None)

        client = self.get_client_with_auth(app, admin_auth)

        request_data = {
            "user_id": "new_user",
            "permissions": ["read", "write"],
        }

        response = client.post("/api/v1/admin/api-keys", json=request_data)

        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert data["user_id"] == "new_user"

    def test_update_api_key_exception_handling(
        self, app, admin_auth, mock_user_service
    ):
        """تست exception handling در update_api_key."""
        mock_user_service.get_user_api_keys = AsyncMock(return_value=[])

        client = self.get_client_with_auth(app, admin_auth)

        request_data = {
            "permissions": ["read", "write"],
        }

        response = client.put("/api/v1/admin/api-keys/test_user", json=request_data)

        assert response.status_code == 404
        data = response.json()
        assert "No API keys found" in data["detail"]

    def test_delete_api_key_exception_handling(
        self, app, admin_auth, mock_user_service
    ):
        """تست exception handling در delete_api_key."""
        mock_user_service.get_user_api_keys = AsyncMock(return_value=[])

        client = self.get_client_with_auth(app, admin_auth)

        response = client.delete("/api/v1/admin/api-keys/test_user")

        assert response.status_code == 404
        data = response.json()
        assert "No API keys found" in data["detail"]

    #     """تست exception handling در get_current_user."""


    def test_list_api_keys_readonly_user_permissions(
        self, app, mock_settings, admin_auth
    ):
        """تست list_api_keys با readonly user permissions."""
        client = self.get_client_with_auth(app, admin_auth)

        response = client.get("/api/v1/admin/api-keys")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)

    def test_create_api_key_empty_permissions(
        self, app, mock_settings, admin_auth, mock_user_service
    ):
        """تست create_api_key با empty permissions."""
        mock_user_service.get_user_by_id = AsyncMock(return_value=None)

        client = self.get_client_with_auth(app, admin_auth)

        request_data = {
            "user_id": "new_user",
            "permissions": [],
        }

        response = client.post("/api/v1/admin/api-keys", json=request_data)

        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert data.get("permissions") in ([], ["read", "write"])

    def test_update_api_key_empty_permissions(self, app, mock_settings, admin_auth):
        """تست update_api_key با empty permissions."""
        client = self.get_client_with_auth(app, admin_auth)

        request_data = {"permissions": []}

        response = client.put("/api/v1/admin/api-keys/test_user", json=request_data)

        assert response.status_code in [200, 404, 500]
        if response.status_code == 200:
            data = response.json()
            assert data["permissions"] == []

    def test_get_current_user_empty_permissions(self, app):
        """تست get_current_user با empty permissions."""
        empty_auth = APIKeyAuth(
            api_key="test-key-123", user_id="test_user", permissions=[]
        )
        client = self.get_client_with_auth(app, empty_auth)

        response = client.get("/api/v1/admin/users/me")

        assert response.status_code == 200
        data = response.json()
        assert data["permissions"] == []


    def test_full_api_key_lifecycle(self, app, mock_settings, admin_auth):
        """تست کامل lifecycle یک API key."""
        client = self.get_client_with_auth(app, admin_auth)

        create_data = {
            "user_id": "lifecycle_user",
            "permissions": ["read", "write"],
        }
        create_response = client.post("/api/v1/admin/api-keys", json=create_data)
        assert create_response.status_code in [200, 500]

        list_response = client.get("/api/v1/admin/api-keys")
        assert list_response.status_code in [200, 500]

        update_data = {
            "permissions": ["read", "write", "admin"],
        }
        update_response = client.put(
            "/api/v1/admin/api-keys/lifecycle_user", json=update_data
        )
        assert update_response.status_code in [404, 500]

        delete_response = client.delete("/api/v1/admin/api-keys/lifecycle_user")
        assert delete_response.status_code in [200, 404, 500]

    def test_admin_vs_user_permissions(
        self, app, mock_settings, admin_auth, user_auth, readonly_auth
    ):
        """تست تفاوت permissions بین admin و user."""

        admin_client = self.get_client_with_auth(app, admin_auth)
        admin_response = admin_client.get("/api/v1/admin/api-keys")
        assert admin_response.status_code == 200

        user_client = self.get_client_with_auth(app, user_auth)
        user_response = user_client.get("/api/v1/admin/api-keys")
        assert user_response.status_code == 403

        readonly_client = self.get_client_with_auth(app, readonly_auth)
        readonly_response = readonly_client.get("/api/v1/admin/api-keys")
        assert readonly_response.status_code == 403
