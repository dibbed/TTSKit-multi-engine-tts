#!/usr/bin/env python3
"""TTSKit Telegram Database Test.

This script tests Telegram-integrated database operations for user and API key management using UserService.

Notes:
- Simulates Telegram commands; requires DB initialized.
- Async methods perform real creates/lists/deletes with tracking and cleanup.
- Prints results; handles exceptions per test.
"""

import asyncio

from ttskit.database.connection import get_session
from ttskit.services.user_service import UserService


class TelegramDatabaseTester:
    """Tests Telegram database integration functionality.

    Initializes DB session and UserService; tracks created users/keys for cleanup; simulates Telegram commands.

    Notes:
    - Uses sync get_session() for simplicity; all methods async.
    - Cleanup runs in finally block of main, deleting tracked items.
    - Focuses on CRUD via service layer as if from Telegram bot.
    """

    def __init__(self):
        self.db_session = next(get_session())
        self.user_service = UserService(self.db_session)
        self.created_users = []
        self.created_api_keys = []

    async def test_create_user(self):
        """Tests user creation via Telegram interface.

        Creates a random test user via UserService.create_user.

        Returns:
        - dict: Success status, user_id, or error.

        Notes:
        - Generates random suffix for uniqueness; sets is_admin=False.
        - Tracks user_id for cleanup; prints creation status.
        """
        print("👤 Testing create user via Telegram...")

        try:
            import random
            import string

            random_suffix = "".join(
                random.choices(string.ascii_lowercase + string.digits, k=6)
            )
            user_id = f"telegram_user_{random_suffix}"

            created_user = await self.user_service.create_user(
                user_id=user_id,
                username=f"Telegram User {random_suffix}",
                email=f"{user_id}@telegram.local",
                is_admin=False,
            )

            self.created_users.append(user_id)
            print(f"✅ User created: {created_user.user_id}")
            return {"status": "success", "user_id": user_id}

        except Exception as e:
            print(f"❌ Error creating user: {e}")
            return {"status": "error", "error": str(e)}

    async def test_create_api_key(self):
        """Tests API key creation via Telegram interface.

        Creates API key for a user (created or 'admin') with read/write perms.

        Returns:
        - dict: Success status, truncated api_key, or error.

        Notes:
        - Tracks plain key; prints truncated version.
        - Uses first created user if available.
        """
        print("🔑 Testing create API key via Telegram...")

        try:
            user_id = self.created_users[0] if self.created_users else "admin"

            api_key_data = await self.user_service.create_api_key(
                user_id=user_id,
                permissions=["read", "write"],
            )

            api_key_plain = api_key_data["api_key"]
            self.created_api_keys.append(api_key_plain)
            print(f"✅ API key created: {api_key_plain[:20]}...")
            return {"status": "success", "api_key": api_key_plain}

        except Exception as e:
            print(f"❌ Error creating API key: {e}")
            return {"status": "error", "error": str(e)}

    async def test_list_users(self):
        """Tests user listing functionality.

        Fetches all users via UserService.get_all_users and prints count/roles.

        Returns:
        - dict: Success status and user count, or error.

        Notes:
        - Prints user IDs and admin status.
        """
        print("👥 Testing list users...")

        try:
            users = await self.user_service.get_all_users()

            print(f"✅ Found {len(users)} users:")
            for user in users:
                print(f"  - {user.user_id} ({'admin' if user.is_admin else 'user'})")

            return {"status": "success", "count": len(users)}

        except Exception as e:
            print(f"❌ Error listing users: {e}")
            return {"status": "error", "error": str(e)}

    async def test_list_api_keys(self):
        """Tests API keys listing functionality.

        Fetches and counts keys per user via get_user_api_keys.

        Returns:
        - dict: Success status and total key count, or error.

        Notes:
        - Prints per-user key counts; aggregates total.
        """
        print("📋 Testing list API keys...")

        try:
            users = await self.user_service.get_all_users()
            total_keys = 0

            for user in users:
                api_keys = await self.user_service.get_user_api_keys(user.user_id)
                total_keys += len(api_keys)
                print(f"  - {user.user_id}: {len(api_keys)} keys")

            print(f"✅ Total API keys: {total_keys}")
            return {"status": "success", "count": total_keys}

        except Exception as e:
            print(f"❌ Error listing API keys: {e}")
            return {"status": "error", "error": str(e)}

    async def test_delete_user(self):
        """Tests user deletion functionality.

        Deletes first created user via UserService.delete_user; skips if none.

        Returns:
        - dict: Success status, user_id, or error/skip reason.

        Notes:
        - Removes from tracking list on success; prints status.
        """
        print("🗑️ Testing delete user...")

        if not self.created_users:
            print("⚠️ No users to delete, skipping test")
            return {"status": "skipped", "reason": "No users created"}

        try:
            user_id = self.created_users[0]
            success = await self.user_service.delete_user(user_id)

            if success:
                print(f"✅ User deleted: {user_id}")
                self.created_users.remove(user_id)
                return {"status": "success", "user_id": user_id}
            else:
                print(f"❌ Failed to delete user: {user_id}")
                return {"status": "error", "error": "Delete failed"}

        except Exception as e:
            print(f"❌ Error deleting user: {e}")
            return {"status": "error", "error": str(e)}

    async def test_telegram_commands_simulation(self):
        """Simulates Telegram commands.

        Maps /commands to corresponding test methods (list/create/delete) and runs them.

        Returns:
        - dict: Results per command (status from sub-tests).

        Notes:
        - Hardcoded command list with descriptions; prints command and result.
        - Delegates to self.test_* methods for execution.
        """
        print("🤖 Testing Telegram commands simulation...")

        commands = [
            ("/list_users", "لیست کاربران"),
            (
                "/create_user user_id:test_user username:Test User email:test@example.com admin:false",
                "ایجاد کاربر",
            ),
            ("/create_key user_id:test_user permissions:read,write", "ایجاد API key"),
            ("/list_keys", "لیست API keys"),
            ("/delete_user user_id:test_user", "حذف کاربر"),
        ]

        results = {}

        for command, description in commands:
            print(f"📱 Command: {command}")
            print(f"📝 Description: {description}")

            # Simulate command execution
            if command.startswith("/list_users"):
                result = await self.test_list_users()
            elif command.startswith("/create_user"):
                result = await self.test_create_user()
            elif command.startswith("/create_key"):
                result = await self.test_create_api_key()
            elif command.startswith("/list_keys"):
                result = await self.test_list_api_keys()
            elif command.startswith("/delete_user"):
                result = await self.test_delete_user()
            else:
                result = {"status": "unknown", "error": "Unknown command"}

            results[command] = result
            print(f"📊 Result: {result['status']}")
            print()

        return results

    async def run_all_tests(self):
        """Runs all Telegram database tests in sequence.

        Executes list/create/key/list/delete and command simulation.

        Returns:
        - dict: Results per test name (success data or error).

        Notes:
        - Catches per-test exceptions; prints failures.
        """
        print("🚀 Running Telegram Database Tests")
        print("=" * 50)

        results = {}

        # Test sequence
        test_methods = [
            ("list_users", self.test_list_users),
            ("create_user", self.test_create_user),
            ("create_api_key", self.test_create_api_key),
            ("list_api_keys", self.test_list_api_keys),
            ("delete_user", self.test_delete_user),
            ("telegram_commands", self.test_telegram_commands_simulation),
        ]

        for test_name, test_method in test_methods:
            try:
                result = await test_method()
                results[test_name] = result
            except Exception as e:
                results[test_name] = {"status": "error", "error": str(e)}
                print(f"❌ Test {test_name} failed: {e}")

        return results

    def cleanup(self):
        """Cleans up test data.

        Deletes tracked users via UserService (sync asyncio.run); closes DB session.

        Notes:
        - Runs delete_user for each created user_id.
        - Prints per-user cleanup status; handles exceptions.
        """
        print("🧹 Cleaning up test data...")
        try:
            for user_id in self.created_users:
                try:
                    asyncio.run(self.user_service.delete_user(user_id))
                    print(f"🗑️ Cleaned up user: {user_id}")
                except Exception as e:
                    print(f"⚠️ Failed to cleanup user {user_id}: {e}")

            self.db_session.close()
            print("✅ Cleanup completed")

        except Exception as e:
            print(f"❌ Cleanup failed: {e}")


async def main():
    """Main function.

    Creates tester, runs all tests, prints summary of successes/failures, and cleans up.

    Notes:
    - Always cleans up in finally; prints test counts and failed names.
    - No explicit return; focuses on console output.
    """
    print("🤖 TTSKit Telegram Database Test")
    print("=" * 50)

    tester = TelegramDatabaseTester()

    try:
        # Run tests
        results = await tester.run_all_tests()

        # Summary
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)

        successful_tests = len(
            [r for r in results.values() if r.get("status") == "success"]
        )
        total_tests = len(results)

        print(f"✅ Successful tests: {successful_tests}/{total_tests}")
        print(f"❌ Failed tests: {total_tests - successful_tests}")

        # Show failed tests
        failed_tests = [
            name
            for name, result in results.items()
            if result.get("status") not in ["success", "skipped"]
        ]

        if failed_tests:
            print(f"\n❌ Failed tests: {', '.join(failed_tests)}")

        print("\n🎉 Telegram Database testing completed!")

    finally:
        # Cleanup
        tester.cleanup()


if __name__ == "__main__":
    print("⚠️ This is a Telegram database test file!")
    print("🚀 Complete test of TTSKit Telegram Database integration")
    print()
    asyncio.run(main())
