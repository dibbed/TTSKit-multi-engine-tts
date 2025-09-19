"""Database migration script for TTSKit security enhancements.

This module handles migrating API keys from plain text to hashed storage, adds usage_count column if missing,
and provides security checks. Uses async operations with print statements for progress and logger for errors.
Designed for SQLite (uses PRAGMA); run once after initial setup to secure the database.
"""

import asyncio

from sqlalchemy import text

from ..utils.logging_config import get_logger
from .connection import get_async_session_context

logger = get_logger(__name__)


async def migrate_api_keys_security() -> None:
    """Migrate the API keys table to secure storage and add usage tracking.

    Removes any plain text 'api_key_plain' column data (sets to NULL, keeping hashes),
    adds 'usage_count' column if missing. Skips if table doesn't exist.
    Uses print statements for progress and logger for info/errors; commits changes only if successful.

    Notes:
        Side effects: Modifies the api_keys table structure and data irreversibly.
        Designed for SQLite (uses PRAGMA and ALTER TABLE); assumes hashed storage is already in place elsewhere.
        Run this once after detecting legacy plain text storage.
    """
    print("🔒 Starting API keys security migration...")

    db_session = await get_async_session_context()
    try:
        result = await db_session.execute(
            text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='api_keys'"
            )
        )
        table_exists = result.fetchone()

        if not table_exists:
            print("ℹ️ api_keys table does not exist yet - skipping migration")
            return

        result = await db_session.execute(text("PRAGMA table_info(api_keys)"))
        columns = [row[1] for row in result.fetchall()]

        if "api_key_plain" in columns:
            print("⚠️ Found plain text API keys in database")
            print("🔄 Migrating to hash-only storage...")

            result = await db_session.execute(
                text(
                    "SELECT id, api_key_plain FROM api_keys WHERE api_key_plain IS NOT NULL"
                )
            )
            api_keys = result.fetchall()

            if api_keys:
                print(f"📊 Found {len(api_keys)} API keys to migrate")

                for api_key_id, plain_text in api_keys:
                    if plain_text:
                        await db_session.execute(
                            text(
                                "UPDATE api_keys SET api_key_plain = NULL WHERE id = :id"
                            ),
                            {"id": api_key_id},
                        )
                        logger.info(f"Migrated API key {api_key_id}")

                await db_session.commit()
                print("✅ API keys migration completed")
            else:
                print("ℹ️ No plain text API keys found")
        else:
            print("✅ API keys already migrated (no plain text column)")

        if "usage_count" not in columns:
            print("📊 Adding usage_count column...")
            try:
                await db_session.execute(
                    text(
                        "ALTER TABLE api_keys ADD COLUMN usage_count INTEGER DEFAULT 0"
                    )
                )
                await db_session.commit()
                print("✅ usage_count column added")
            except Exception as e:
                if "duplicate column name" in str(e).lower():
                    print("ℹ️ usage_count column already exists")
                else:
                    raise
        else:
            print("✅ usage_count column already exists")

        print("🎉 Migration completed successfully!")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        await db_session.rollback()
        raise
    finally:
        await db_session.close()


async def check_database_security() -> None:
    """Inspect the API keys table for security issues and print status.

    Checks table existence, structure (columns), plain text data presence, and usage tracking column.
    Uses print statements to output details and warnings; logs errors if checks fail.

    Notes:
        Side effects: None (read-only); prints table columns and security warnings to console.
        Designed for SQLite (uses PRAGMA); helps diagnose before/after migration.
    """
    print("🔍 Checking database security status...")

    db_session = await get_async_session_context()
    try:
        result = await db_session.execute(
            text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='api_keys'"
            )
        )
        table_exists = result.fetchone()

        if not table_exists:
            print("ℹ️ api_keys table does not exist yet")
            return

        result = await db_session.execute(text("PRAGMA table_info(api_keys)"))
        columns = [row[1] for row in result.fetchall()]

        print("📋 API Keys table structure:")
        for col in columns:
            print(f"  - {col}")

        if "api_key_plain" in columns:
            result = await db_session.execute(
                text("SELECT COUNT(*) FROM api_keys WHERE api_key_plain IS NOT NULL")
            )
            plain_count = result.scalar()

            if plain_count > 0:
                print(f"⚠️ WARNING: {plain_count} API keys still have plain text!")
                print("🔒 Run migration to fix security issue")
            else:
                print("✅ No plain text API keys found")
        else:
            print("✅ Plain text column removed (secure)")

        if "usage_count" in columns:
            print("✅ Usage tracking enabled")
        else:
            print("⚠️ Usage tracking not available")

    except Exception as e:
        logger.error(f"Security check failed: {e}")
        raise
    finally:
        await db_session.close()


async def main():
    """Orchestrate the full security migration process with checks.

    Runs initial security check, performs migration if needed, then final check.
    Uses print statements for headers, progress, and warnings.

    Notes:
        Side effects: Calls migrate_api_keys_security, which modifies the database.
        Designed to be run as a standalone script; ensures complete workflow.
    """
    print("🚀 TTSKit Database Security Migration")
    print("=" * 50)

    await check_database_security()
    print()

    await migrate_api_keys_security()
    print()

    await check_database_security()

    print("\n🎉 Migration process completed!")
    print("⚠️ IMPORTANT: After migration, API keys are only stored as hashes.")
    print("   Make sure to save your API keys securely before running this migration!")


if __name__ == "__main__":
    asyncio.run(main())
