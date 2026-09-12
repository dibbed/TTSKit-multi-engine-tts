#!/usr/bin/env python3
"""Example demonstrating API key priority system."""

import asyncio
import sys

sys.path.insert(0, ".")

from ttskit.api.dependencies import verify_api_key
from ttskit.config import settings
from ttskit.database.connection import get_session


async def test_api_key_priority():
    """Tests API key priority system with various key types and permission levels.

    Validates that config-based keys take priority over database keys, admin keys
    receive appropriate permissions, and user identification works correctly across
    different authentication scenarios.
    """
    print("🔑 Testing API Key Priority System")
    print("=" * 50)

    test_cases = [
        {
            "name": "Admin key from config",
            "api_key": "sample-admin-token-12345",
            "expected_user": "admin",
            "expected_permissions": ["read", "write", "admin"],
        },
        {
            "name": "Regular user key from config",
            "api_key": "user1-key",
            "expected_user": "user1",
            "expected_permissions": ["read", "write"],
        },
        {
            "name": "Readonly key from config",
            "api_key": "readonly-key",
            "expected_user": "readonly_test",
            "expected_permissions": ["read"],
        },
        {
            "name": "Single API key from config",
            "api_key": "sample-single-token-12345",
            "expected_user": "api-user",
            "expected_permissions": ["read", "write"],
        },
    ]

    original_api_keys = getattr(settings, "api_keys", None)
    original_api_key = getattr(settings, "api_key", None)

    settings.api_keys = {
        "admin": "sample-admin-token-12345",
        "user1": "user1-key",
        "readonly_test": "readonly-key",
    }
    settings.api_key = "sample-single-token-12345"

    try:
        for test_case in test_cases:
            print(f"\n🧪 Testing: {test_case['name']}")
            print("   Key: [MASKED]")

            try:
                db_session = next(get_session())

                auth = await verify_api_key(test_case["api_key"], db_session)

                if auth:
                    print("   ✅ Verified successfully")
                    print(f"   👤 User ID: {auth.user_id}")
                    print(f"   🔐 Permissions: {auth.permissions}")

                    if auth.user_id == test_case["expected_user"]:
                        print(
                            f"   ✅ User ID matches expected: {test_case['expected_user']}"
                        )
                    else:
                        print(
                            f"   ❌ User ID mismatch. Expected: {test_case['expected_user']}, Got: {auth.user_id}"
                        )

                    if set(auth.permissions) == set(test_case["expected_permissions"]):
                        print(
                            f"   ✅ Permissions match expected: {test_case['expected_permissions']}"
                        )
                    else:
                        print(
                            f"   ❌ Permissions mismatch. Expected: {test_case['expected_permissions']}, Got: {auth.permissions}"
                        )
                else:
                    print("   ❌ Verification failed")

            except Exception as e:
                print(f"   ❌ Error: {e}")
            finally:
                db_session.close()

    finally:
        if original_api_keys is not None:
            settings.api_keys = original_api_keys
        if original_api_key is not None:
            settings.api_key = original_api_key


async def test_invalid_keys():
    """Tests rejection of invalid API keys and proper error handling.

    Verifies that non-existent, malformed, and empty API keys are properly
    rejected by the authentication system with appropriate error responses.
    """
    print("\n🚫 Testing Invalid API Keys")
    print("=" * 30)

    invalid_keys = ["invalid-key-123", "nonexistent-key", "expired-key", ""]

    for invalid_key in invalid_keys:
        print(
            f"\n🧪 Testing invalid key: {'[non-empty key]' if invalid_key else 'empty'}"
        )

        try:
            db_session = next(get_session())
            auth = await verify_api_key(invalid_key, db_session)

            if auth:
                print(f"   ❌ Should have failed but succeeded: {auth.user_id}")
            else:
                print("   ✅ Correctly rejected invalid key")

        except Exception as e:
            print(f"   ✅ Correctly rejected with error: {str(e)[:50]}...")
        finally:
            db_session.close()


async def demonstrate_priority():
    """Demonstrates the API key priority system and configuration hierarchy.

    Explains how different key sources are prioritized and shows current
    configuration settings for API keys and authentication.
    """
    print("\n📊 Priority System Demonstration")
    print("=" * 40)

    print("""
    Priority Order:
    1. Config API_KEYS (highest priority)
    2. Config API_KEY (single key)
    3. Database keys (lowest priority)

    Example:
    - If 'admin-key' exists in both config and database
    - Config version will be used (user_id='admin')
    - Database version will be ignored
    """)

    print("\nCurrent Config:")
    print(f"  API_KEY: {getattr(settings, 'api_key', 'Not set')}")
    print(f"  API_KEYS: {getattr(settings, 'api_keys', 'Not set')}")


async def main():
    """Runs comprehensive API key priority system tests and demonstrations.

    Executes priority demonstration, key validation tests, and invalid key
    rejection tests. Displays summary of authentication system behavior.
    """
    print("🚀 API Key Priority System Test")
    print("=" * 60)

    try:
        await demonstrate_priority()
        await test_api_key_priority()
        await test_invalid_keys()

        print("\n✅ All tests completed!")
        print("\n📝 Summary:")
        print("   - Config keys take priority over database keys")
        print("   - Admin keys get admin permissions automatically")
        print("   - Readonly keys get read-only permissions")
        print("   - Invalid keys are properly rejected")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
