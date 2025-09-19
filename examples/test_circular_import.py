#!/usr/bin/env python3
"""Test script to check for circular imports."""

import sys


def test_imports():
    """Tests all critical TTSKit imports to detect circular import issues.
    
    Systematically imports database, API, and core components to verify
    that no circular dependencies exist in the module structure.
    
    Returns:
        Boolean indicating whether all imports succeeded without circular dependencies
    """
    try:
        print("Testing imports...")

        print("1. Testing database.base...")
        from ttskit.database.base import Base

        print("✅ database.base imported successfully")

        print("2. Testing database.models...")
        from ttskit.database.models import APIKey, User

        print("✅ database.models imported successfully")

        print("3. Testing database.connection...")
        from ttskit.database.connection import get_engine, get_session

        print("✅ database.connection imported successfully")

        print("4. Testing database.init_db...")
        from ttskit.database.init_db import init_database

        print("✅ database.init_db imported successfully")

        print("5. Testing api.dependencies...")
        from ttskit.api.dependencies import APIKeyAuth

        print("✅ api.dependencies imported successfully")

        print("6. Testing api.app...")
        from ttskit.api.app import app

        print("✅ api.app imported successfully")

        print("\n🎉 All imports successful! No circular imports detected.")
        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
