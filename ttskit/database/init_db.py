"""Database initialization script for TTSKit.

This module sets up the database by creating tables and seeding default users (admin and demo) with API keys.
Uses async operations with print statements for progress logging; sync wrapper available for convenience.
"""

import asyncio

from ..services.user_service import UserService
from .connection import create_tables_async, get_async_session_context


async def init_database_async():
    """Asynchronously initialize the database by creating tables and seeding default data.

    Creates an admin user with full permissions API key and a demo user with basic permissions.
    Uses print statements to log progress; ensures session cleanup even on errors.

    Notes:
        This function has side effects: modifies the database by inserting records if they don't exist.
        API keys are generated and printed (save them securely as they're not re-displayed).
        Requires UserService for user/API key operations.
    """
    print("🗄️ Initializing database...")

    await create_tables_async()
    print("✅ Database tables created")

    db_session = await get_async_session_context()
    try:
        user_service = UserService(db_session)

        admin_user = await user_service.get_user_by_id("admin")
        if not admin_user:
            print("👑 Creating default admin user...")
            admin_user = await user_service.create_user(
                user_id="admin",
                username="Administrator",
                email="admin@ttskit.local",
                is_admin=True,
            )
            print(f"✅ Admin user created: {admin_user.user_id}")

        admin_api_keys = await user_service.get_user_api_keys("admin")
        if not admin_api_keys:
            print("🔑 Creating default admin API key...")
            admin_api_key_data = await user_service.create_api_key(
                user_id="admin",
                permissions=["read", "write", "admin"],
            )
            print(f"✅ Admin API key created: {admin_api_key_data['api_key']}")
            print("⚠️ IMPORTANT: Save this API key securely!")

        demo_user = await user_service.get_user_by_id("demo-user")
        if not demo_user:
            print("👤 Creating demo user...")
            demo_user = await user_service.create_user(
                user_id="demo-user",
                username="Demo User",
                email="demo@ttskit.local",
                is_admin=False,
            )
            print(f"✅ Demo user created: {demo_user.user_id}")

        demo_api_keys = await user_service.get_user_api_keys("demo-user")
        if not demo_api_keys:
            print("🔑 Creating demo API key...")
            demo_api_key_data = await user_service.create_api_key(
                user_id="demo-user",
                permissions=["read", "write"],
            )
            print(f"✅ Demo API key created: {demo_api_key_data['api_key']}")

        print("🎉 Database initialization completed!")

    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise
    finally:
        await db_session.close()


def init_database():
    """Synchronously initialize the database by running the async initialization.

    Convenience wrapper for non-async environments; calls asyncio.run on the async function.
    """
    asyncio.run(init_database_async())


if __name__ == "__main__":
    init_database()
