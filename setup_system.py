#!/usr/bin/env python3
"""
TTSKit System Setup Script

Provides a simple alternative to CLI or Makefile for setting up TTSKit, including environment config,
database initialization, migrations, and validation tests.
"""

import asyncio
import sys
from pathlib import Path


def setup_environment():
    """
    Creates the .env configuration file from .env.example if it doesn't exist.

    Copies the template to provide default TTSKit settings and prompts for customization.

    Returns:
        None
    """
    env_file = Path(".env")
    env_example = Path(".env.example")

    if not env_file.exists() and env_example.exists():
        print("📋 Creating .env file from .env.example...")
        env_file.write_text(env_example.read_text())
        print("✅ .env file created successfully")
        print("⚠️  Please edit .env file with your configuration")
    elif env_file.exists():
        print("✅ .env file already exists")
    else:
        print("❌ .env.example file not found")


async def init_database():
    """
    Initializes the TTSKit database schema by creating necessary tables and structures.

    Imports and calls the async init function, handling exceptions gracefully.

    Returns:
        bool: True if successful, False on failure.
    """
    try:
        print("📊 Initializing database...")
        from ttskit.database.init_db import init_database_async

        await init_database_async()
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False
    return True


async def run_migrations():
    """
    Executes database schema migrations to apply pending updates.

    Imports and runs the migration function, catching any errors.

    Returns:
        bool: True if migrations complete, False on failure.
    """
    try:
        print("🔄 Running migrations...")
        from ttskit.database.migration import migrate_api_keys_security

        await migrate_api_keys_security()
        print("✅ Migrations completed successfully")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False
    return True


def run_tests():
    """
    Runs validation tests for security and database to verify TTSKit configuration.

    Uses subprocess to execute test scripts and reports outcomes via prints.
    Handles timeouts and exceptions.

    Returns:
        None
    """
    try:
        print("🧪 Running tests...")
        import subprocess

        result = subprocess.run(
            [sys.executable, "examples/test_security.py"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0:
            print("✅ Security tests passed")
        else:
            print(f"⚠️ Security tests failed: {result.stderr}")

        result = subprocess.run(
            [sys.executable, "examples/test_database_api.py"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0:
            print("✅ Database tests passed")
        else:
            print(f"⚠️ Database tests failed: {result.stderr}")

    except subprocess.TimeoutExpired:
        print("⚠️ Tests timed out")
    except Exception as e:
        print(f"⚠️ Test execution failed: {e}")


async def main():
    """
    Orchestrates the full TTSKit system setup sequence.

    Calls environment setup, database init, migrations, and tests in order.
    Exits on failure and prints completion summary with next steps.

    Returns:
        None
    """
    print("🚀 TTSKit System Setup")
    print("=" * 50)

    setup_environment()

    if not await init_database():
        print("❌ Setup failed at database initialization")
        sys.exit(1)

    if not await run_migrations():
        print("❌ Setup failed at migrations")
        sys.exit(1)

    run_tests()

    print("\n🎉 Setup Complete!")
    print("=" * 50)
    print("✅ Environment: Configured")
    print("✅ Database: Initialized")
    print("✅ Migrations: Completed")
    print("✅ Tests: Executed")
    print("\n🚀 TTSKit is ready to use!")
    print("\nNext steps:")
    print("  • Edit .env file with your configuration")
    print("  • Start bot: python -m ttskit_cli.main start --token YOUR_BOT_TOKEN")
    print("  • Start API: python -m ttskit_cli.main api --host 0.0.0.0 --port 8000")


if __name__ == "__main__":
    asyncio.run(main())
