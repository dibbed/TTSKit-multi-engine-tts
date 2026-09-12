"""Database initialization script for TTSKit.

This module sets up the database by creating tables and seeding default users (admin and demo) with API keys.
Uses async operations with print statements for progress logging; sync wrapper available for convenience.
"""

import asyncio

from ..services.user_service import UserService
from ..utils.logging_config import get_logger
from .connection import create_tables_async, get_async_session_context

logger = get_logger(__name__)


async def init_database_async() -> dict[str, str | None]:
    """Asynchronously initialize the database by creating tables and seeding default data.

    Creates an admin user with full permissions API key and a demo user with basic permissions.
    Uses structured logger to track progress without leaking raw secret credentials.

    Returns:
        dict[str, Optional[str]]: Dictionary containing any freshly created API keys.
    """
    logger.info("Initializing database...")

    await create_tables_async()
    logger.info("Database tables created successfully")

    created_keys: dict[str, str | None] = {
        "admin_api_key": None,
        "demo_api_key": None,
    }

    db_session = await get_async_session_context()
    try:
        user_service = UserService(db_session)

        admin_user = await user_service.get_user_by_id("admin")
        if not admin_user:
            logger.info("Creating default admin user...")
            admin_user = await user_service.create_user(
                user_id="admin",
                username="Administrator",
                email="admin@ttskit.local",
                is_admin=True,
            )
            logger.info(f"Admin user created: {admin_user.user_id}")

        admin_api_keys = await user_service.get_user_api_keys("admin")
        if not admin_api_keys:
            logger.info("Creating default admin API key...")
            admin_api_key_data = await user_service.create_api_key(
                user_id="admin",
                permissions=["read", "write", "admin"],
            )
            created_keys["admin_api_key"] = (
                admin_api_key_data.get("api_key") if admin_api_key_data else None
            )
            logger.info("Admin API key created successfully (user_id=admin)")

        demo_user = await user_service.get_user_by_id("demo-user")
        if not demo_user:
            logger.info("Creating demo user...")
            demo_user = await user_service.create_user(
                user_id="demo-user",
                username="Demo User",
                email="demo@ttskit.local",
                is_admin=False,
            )
            logger.info(f"Demo user created: {demo_user.user_id}")

        demo_api_keys = await user_service.get_user_api_keys("demo-user")
        if not demo_api_keys:
            logger.info("Creating demo API key...")
            demo_api_key_data = await user_service.create_api_key(
                user_id="demo-user",
                permissions=["read", "write"],
            )
            created_keys["demo_api_key"] = (
                demo_api_key_data.get("api_key") if demo_api_key_data else None
            )
            logger.info("Demo API key created successfully (user_id=demo-user)")

        logger.info("Database initialization completed successfully")
        return created_keys

    except Exception as e:
        logger.error(f"Database initialization failed: {e}", exc_info=True)
        raise
    finally:
        await db_session.close()


def init_database() -> dict[str, str | None]:
    """Synchronously initialize the database by running the async initialization.

    Convenience wrapper for non-async environments; calls asyncio.run on the async function.
    """
    return asyncio.run(init_database_async())


if __name__ == "__main__":
    init_database()
