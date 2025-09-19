#!/usr/bin/env python3
"""TTSKit Database API Test.

This script tests the database API endpoints for user management and API keys, including creation, retrieval, listing, and deletion with automatic cleanup.

Notes:
- Requires the API server to be running (e.g., via 'ttskit api') and admin API key configured.
- Uses aiohttp for async HTTP requests; performs real DB operations.
- Prints detailed status; handles exceptions and timeouts.
"""

import asyncio
import sys
from pathlib import Path
from typing import Any, Dict

import aiohttp

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from ttskit.config import get_settings


class DatabaseAPITester:
    """Comprehensive tester for TTSKit database API endpoints.

    This class handles testing of user and API key CRUD operations via API calls, tracking created resources for cleanup.

    Notes:
    - Initializes with base URL and admin API key from config.
    - Tracks created users/keys for post-test deletion.
    - All methods are async and print progress with emojis for readability.
    """

    def __init__(self, base_url: str = None, api_key: str = None):
        """Initializes database API tester with configuration and authentication.

        Sets up the tester using provided or config-based URL and admin key, preparing headers for authenticated requests.

        Parameters:
        - base_url (str, optional): API server base URL (defaults to config host/port).
        - api_key (str, optional): Admin API key (defaults to config admin key; raises ValueError if missing).

        Notes:
        - Tracks created resources (users, keys) for cleanup.
        - Uses Bearer token authorization.
        """
        self.settings = get_settings()

        self.base_url = (
            base_url or f"http://{self.settings.api_host}:{self.settings.api_port}"
        )

        if api_key:
            self.api_key = api_key
        else:
            admin_key = self.settings.api_keys.get("admin")
            if not admin_key:
                raise ValueError(
                    "Admin API key not found in config. Please set API_KEYS with admin key."
                )
            self.api_key = admin_key

        self.headers = {"Authorization": f"Bearer {self.api_key}"}

        self.created_user_id = None
        self.created_api_key = None
        self.created_resources = []

    async def test_server_connection(self) -> Dict[str, Any]:
        """Tests server connection and health status with timeout handling.

        Sends a GET to /system/health and checks response.

        Returns:
        - Dict[str, Any]: Status code, health data, or error details (e.g., timeout).

        Notes:
        - 5-second timeout; prints connection status.
        - Handles non-200 responses as warnings.
        """
        print("🔌 Testing server connection...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/v1/system/health",
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ Server connection: {response.status}")
                        print(f"🏥 Health status: {data.get('status', 'unknown')}")
                        return {"status": response.status, "data": data}
                    else:
                        print(f"⚠️ Server responded with: {response.status}")
                        return {
                            "status": response.status,
                            "warning": "Server not healthy",
                        }
        except asyncio.TimeoutError:
            print("❌ Server connection timeout")
            return {"error": "Connection timeout"}
        except Exception as e:
            print(f"❌ Server connection failed: {e}")
            return {"error": str(e)}

    async def test_list_users(self) -> Dict[str, Any]:
        """Tests user listing functionality.

        Fetches all users from /admin/users and prints count/details.

        Returns:
        - Dict[str, Any]: Status code and user list data.

        Notes:
        - Prints user IDs and admin status.
        - Catches and reports any request errors.
        """
        print("👥 Testing list users...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/v1/admin/users",
                    headers=self.headers,
                ) as response:
                    data = await response.json()
                    print(f"✅ List users: {response.status}")
                    print(f"📊 Found {len(data)} users")
                    for user in data:
                        print(
                            f"  - {user['user_id']} ({'admin' if user['is_admin'] else 'user'})"
                        )
                    return {"status": response.status, "data": data}
        except Exception as e:
            print(f"❌ Error in list users test: {e}")
            return {"error": str(e)}

    async def test_create_user(self) -> Dict[str, Any]:
        """Tests user creation functionality.

        POSTs a random test user to /admin/users and tracks for cleanup.

        Returns:
        - Dict[str, Any]: Status code, created data, and user_id.

        Notes:
        - Generates random suffix for unique user_id/username/email.
        - Sets is_admin=False; prints created user details.
        - Stores user_id in self.created_user_id for later use/deletion.
        """
        print("➕ Testing create user...")
        import random
        import string

        random_suffix = "".join(
            random.choices(string.ascii_lowercase + string.digits, k=6)
        )
        test_user_id = f"test_user_{random_suffix}"

        test_data = {
            "user_id": test_user_id,
            "username": f"Test User {random_suffix}",
            "email": f"test_{random_suffix}@example.com",
            "is_admin": False,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/v1/admin/users",
                    headers=self.headers,
                    json=test_data,
                ) as response:
                    data = await response.json()
                    print(f"✅ Create user: {response.status}")
                    print(f"👤 Created user: {test_user_id}")

                    self.created_user_id = test_user_id
                    self.created_resources.append(("user", test_user_id))

                    return {
                        "status": response.status,
                        "data": data,
                        "user_id": test_user_id,
                    }
        except Exception as e:
            print(f"❌ Error in create user test: {e}")
            return {"error": str(e)}

    async def test_get_user(self) -> Dict[str, Any]:
        """Tests user retrieval functionality.

        GETs a specific user (created or default 'admin') from /admin/users/{user_id}.

        Returns:
        - Dict[str, Any]: Status code and user data.

        Notes:
        - Uses self.created_user_id if available, else 'admin'.
        - Prints user ID from response.
        """
        print("🔍 Testing get user...")
        user_id = self.created_user_id or "admin"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/v1/admin/users/{user_id}",
                    headers=self.headers,
                ) as response:
                    data = await response.json()
                    print(f"✅ Get user: {response.status}")
                    print(f"👤 User info: {data.get('user_id', 'unknown')}")
                    return {"status": response.status, "data": data}
        except Exception as e:
            print(f"❌ Error in get user test: {e}")
            return {"error": str(e)}

    async def test_create_api_key(self) -> Dict[str, Any]:
        """Tests API key creation functionality.

        POSTs API key for a user (created or 'admin') to /admin/api-keys with read/write perms.

        Returns:
        - Dict[str, Any]: Status code, key data (including plain key and ID).

        Notes:
        - Tracks key ID for cleanup; prints truncated key.
        - Stores plain key in self.created_api_key.
        """
        print("🔑 Testing create API key...")
        user_id = self.created_user_id or "admin"

        test_data = {
            "user_id": user_id,
            "permissions": ["read", "write"],
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/v1/admin/api-keys",
                    headers=self.headers,
                    json=test_data,
                ) as response:
                    data = await response.json()
                    print(f"✅ Create API key: {response.status}")
                    print(f"🔑 API key: {data.get('api_key', 'unknown')[:20]}...")

                    self.created_api_key = data.get("api_key")
                    api_key_id = data.get("id")
                    if api_key_id:
                        self.created_resources.append(("api_key", api_key_id))

                    return {"status": response.status, "data": data}
        except Exception as e:
            print(f"❌ Error in create API key test: {e}")
            return {"error": str(e)}

    async def test_list_api_keys(self) -> Dict[str, Any]:
        """Tests API keys listing functionality.

        GETs all API keys from /admin/api-keys and prints user/key details.

        Returns:
        - Dict[str, Any]: Status code and keys list data.

        Notes:
        - Prints truncated plain keys per user.
        - Catches and reports request errors.
        """
        print("📋 Testing list API keys...")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/v1/admin/api-keys",
                    headers=self.headers,
                ) as response:
                    data = await response.json()
                    print(f"✅ List API keys: {response.status}")
                    print(f"📊 Found {len(data)} API keys")
                    for api_key in data:
                        print(
                            f"  - {api_key['user_id']}: {api_key['api_key_plain'][:20]}..."
                        )
                    return {"status": response.status, "data": data}
        except Exception as e:
            print(f"❌ Error in list API keys test: {e}")
            return {"error": str(e)}

    async def test_get_current_user(self) -> Dict[str, Any]:
        """Tests retrieval of current user info.

        GETs /admin/users/me and prints user_id/permissions.

        Returns:
        - Dict[str, Any]: Status code and current user data.

        Notes:
        - Uses admin auth; reports permissions list.
        """
        print("👤 Testing get current user...")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/v1/admin/users/me",
                    headers=self.headers,
                ) as response:
                    data = await response.json()
                    print(f"✅ Get current user: {response.status}")
                    print(f"👤 Current user: {data.get('user_id', 'unknown')}")
                    print(f"🔐 Permissions: {data.get('permissions', [])}")
                    return {"status": response.status, "data": data}
        except Exception as e:
            print(f"❌ Error in get current user test: {e}")
            return {"error": str(e)}

    async def test_delete_user(self) -> Dict[str, Any]:
        """Tests user deletion functionality.

        DELETEs the created user from /admin/users/{user_id}; skips if none created.

        Returns:
        - Dict[str, Any]: Status code and response data, or skip reason.

        Notes:
        - Uses self.created_user_id; prints deletion status.
        """
        print("🗑️ Testing delete user...")
        user_id = self.created_user_id

        if not user_id:
            print("⚠️ No user to delete, skipping test")
            return {"status": "skipped", "reason": "No user created"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.delete(
                    f"{self.base_url}/api/v1/admin/users/{user_id}",
                    headers=self.headers,
                ) as response:
                    data = await response.json()
                    print(f"✅ Delete user: {response.status}")
                    print(f"🗑️ Deleted user: {user_id}")
                    return {"status": response.status, "data": data}
        except Exception as e:
            print(f"❌ Error in delete user test: {e}")
            return {"error": str(e)}

    async def cleanup_created_resources(self) -> Dict[str, Any]:
        """Cleans up all resources created during tests.

        Deletes API keys then users in reverse order, reporting per-resource success.

        Returns:
        - Dict[str, Any]: Cleanup results keyed by resource (success or error).

        Notes:
        - Clears tracking lists after; prints cleanup status.
        - Handles 404 as success (already deleted).
        """
        print("🧹 Cleaning up created resources...")
        cleanup_results = {}

        for resource_type, resource_id in reversed(self.created_resources):
            try:
                if resource_type == "api_key":
                    await self._delete_api_key(resource_id)
                elif resource_type == "user":
                    await self._delete_user(resource_id)

                cleanup_results[f"cleanup_{resource_type}_{resource_id}"] = "success"
                print(f"  ✅ Cleaned up {resource_type}: {resource_id}")

            except Exception as e:
                cleanup_results[f"cleanup_{resource_type}_{resource_id}"] = (
                    f"error: {e}"
                )
                print(f"  ❌ Failed to cleanup {resource_type} {resource_id}: {e}")

        # Clear tracking lists
        self.created_resources.clear()
        self.created_user_id = None
        self.created_api_key = None

        print("✅ Cleanup completed!")
        return cleanup_results

    async def _delete_api_key(self, api_key_id: str):
        """Deletes a specific API key internally.

        Sends DELETE to /admin/api-keys/{api_key_id}; tolerant of 404.

        Parameters:
        - api_key_id (str): The ID of the API key to delete.

        Notes:
        - Raises exception only on non-200/204/404 responses.
        """
        async with aiohttp.ClientSession() as session:
            async with session.delete(
                f"{self.base_url}/api/v1/admin/api-keys/{api_key_id}",
                headers=self.headers,
            ) as response:
                if response.status not in [
                    200,
                    204,
                    404,
                ]:  # 404 is OK (already deleted)
                    raise Exception(f"Failed to delete API key: {response.status}")

    async def _delete_user(self, user_id: str):
        """Deletes a specific user internally.

        Sends DELETE to /admin/users/{user_id}; tolerant of 404.

        Parameters:
        - user_id (str): The ID of the user to delete.

        Notes:
        - Raises exception only on non-200/204/404 responses.
        """
        async with aiohttp.ClientSession() as session:
            async with session.delete(
                f"{self.base_url}/api/v1/admin/users/{user_id}",
                headers=self.headers,
            ) as response:
                if response.status not in [
                    200,
                    204,
                    404,
                ]:  # 404 is OK (already deleted)
                    raise Exception(f"Failed to delete user: {response.status}")

    async def run_all_tests(self) -> Dict[str, Any]:
        """Runs all database API tests in sequence.

        Executes connection, list/create/get/delete ops for users/keys, and current user fetch.

        Returns:
        - Dict[str, Any]: Results per test name (success data or error).

        Notes:
        - Prints truncated admin key; catches per-test exceptions.
        """
        print(f"🚀 Running database API tests with key: {self.api_key[:10]}...")

        results = {}

        # Test sequence
        test_methods = [
            ("server_connection", self.test_server_connection),
            ("list_users", self.test_list_users),
            ("create_user", self.test_create_user),
            ("get_user", self.test_get_user),
            ("create_api_key", self.test_create_api_key),
            ("list_api_keys", self.test_list_api_keys),
            ("get_current_user", self.test_get_current_user),
            ("delete_user", self.test_delete_user),
        ]

        for test_name, test_method in test_methods:
            try:
                result = await test_method()
                results[test_name] = result
            except Exception as e:
                results[test_name] = {"error": str(e)}
                print(f"❌ Test {test_name} failed: {e}")

        return results


async def main():
    """Main function.

    Initializes tester, runs all tests with admin key, performs cleanup, and prints summary.

    Returns:
    - bool: True if all tests succeeded, False otherwise.

    Notes:
    - Displays config details (server, key, env); suggests fixes if connection fails.
    - Exits with 1 on init errors; prints troubleshooting tips.
    """
    print("🗄️ TTSKit Database API Test")
    print("=" * 60)

    try:
        # Initialize tester with config
        tester = DatabaseAPITester()

        print(f"🌐 Server address: {tester.base_url}")
        print(f"🔑 Admin key: {tester.api_key[:10]}...")
        print(
            f"⚙️ Using config from: {tester.settings.model_config.get('env_file', '.env')}"
        )
        print()

        # Test with admin key
        print("👑 Testing Database API with ADMIN key")
        print("=" * 60)

        results = await tester.run_all_tests()

        # Cleanup
        print("\n" + "=" * 60)
        print("🧹 CLEANUP PHASE")
        print("=" * 60)

        cleanup_results = await tester.cleanup_created_resources()
        results.update(cleanup_results)

        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)

        # Count test results (exclude cleanup results)
        test_results = {
            k: v for k, v in results.items() if not k.startswith("cleanup_")
        }
        successful_tests = len(
            [
                r
                for r in test_results.values()
                if isinstance(r, dict)
                and "status" in r
                and isinstance(r["status"], int)
                and 200 <= r["status"] < 300
            ]
        )
        total_tests = len(test_results)

        print(f"✅ Successful tests: {successful_tests}/{total_tests}")
        print(f"❌ Failed tests: {total_tests - successful_tests}")

        # Show failed tests
        failed_tests = [
            name
            for name, result in test_results.items()
            if not isinstance(result, dict)
            or "status" not in result
            or not isinstance(result["status"], int)
            or not (200 <= result["status"] < 300)
        ]

        if failed_tests:
            print(f"\n❌ Failed tests: {', '.join(failed_tests)}")

        # Show cleanup results
        cleanup_successful = len(
            [r for r in cleanup_results.values() if r == "success"]
        )
        cleanup_total = len(cleanup_results)
        print(f"\n🧹 Cleanup: {cleanup_successful}/{cleanup_total} resources cleaned")

        print("\n🎉 Database API testing completed!")

        # Show connection status
        if successful_tests == 0:
            print("\n💡 Note: All tests failed due to server connection issues.")
            print("   To run these tests successfully:")
            print("   1. Start the API server: ttskit api")
            print("   2. Make sure the server is running on the configured port")
            print("   3. Verify admin key is properly configured")

        # Return success status
        return successful_tests == total_tests

    except Exception as e:
        print(f"❌ Test initialization failed: {e}")
        print("💡 Make sure:")
        print("  1. API server is running")
        print("  2. Admin key is configured in API_KEYS")
        print("  3. Database is properly initialized")
        return False


if __name__ == "__main__":
    print("⚠️ This is a database API test file!")
    print("🚀 Complete test of TTSKit Database API endpoints")
    print("📋 Tests include: users, API keys, admin functions")
    print("🧹 Automatic cleanup of created resources")
    print()

    success = asyncio.run(main())
    sys.exit(0 if success else 1)
