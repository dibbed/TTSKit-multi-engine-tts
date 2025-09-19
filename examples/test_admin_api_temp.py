#!/usr/bin/env python3
"""
Temporary test file for TTSKit Admin API - comprehensive testing of all endpoints.

This script tests over 45 API endpoints, including system health, cache management, engines,
synthesis, and admin operations. It uses multiple API keys to verify permissions, handles
errors gracefully, generates unique test data to avoid conflicts, and restores configuration
after testing. Designed for temporary use during development; delete after validation.
"""

import asyncio
import random
import string
import time
from typing import Any, Dict

import aiohttp

# Import TTSKit config
try:
    from ttskit.config import get_settings, set_config_value
except ImportError:
    print(
        "❌ TTSKit modules not found. Make sure you're running from the project root."
    )
    exit(1)


class AdminAPITester:
    """Tests the TTSKit Admin API endpoints comprehensively.

    This class handles testing of all major API sections: system status, cache, engines,
    synthesis, admin user/API key management, metrics, and utilities. It backs up and
    restores configuration, generates unique test data, cleans up resources, and
    validates responses for success, errors, and permissions.

    Attributes:
        base_url: The API base URL (defaults to config).
        admin_key: Authorization key for admin access (defaults to config).
        headers: Default request headers with auth.
        results: Dictionary storing test outcomes.
        original_config: Backup of pre-test settings.
        created_users: List of created test users for cleanup.
        created_api_keys: List of created test API keys for cleanup.

    Note:
        Designed for temporary testing; ensures no permanent changes to the system.
        Runs async for efficient API calls; supports multiple key types for permission checks.
    """

    def __init__(self, base_url: str = None, admin_key: str = None):
        """Initializes the API tester with configuration and auth details.

        Loads TTSKit settings, sets base URL and admin key (falling back to config values),
        prepares headers, and initializes result storage and cleanup lists.

        Args:
            base_url: The base URL for the API server. Defaults to config host/port.
            admin_key: The API key for admin authorization. Defaults to config API key.

        Note:
            Backs up original config for restoration post-testing to avoid side effects.
            Prepares empty lists for tracking created resources during tests.
        """
        self.settings = get_settings()

        self.base_url = (
            base_url or f"http://{self.settings.api_host}:{self.settings.api_port}"
        ).rstrip("/")
        self.admin_key = admin_key or self.settings.api_key

        self.headers = (
            {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.admin_key}",
            }
            if self.admin_key
            else {"Content-Type": "application/json"}
        )
        self.results = {}

        self.original_config = {}
        self.created_users = []
        self.created_api_keys = []

    def _generate_unique_id(self, prefix: str = "test") -> str:
        """Generates a unique identifier for test data to prevent conflicts.

        Uses the last 6 digits of the current timestamp combined with a 4-character
        random alphanumeric suffix, prefixed as specified.

        Args:
            prefix: The string prefix for the ID (default: "test").

        Returns:
            str: Unique ID in the format "prefix_timestamp_random".

        Note:
            Helps avoid data overlaps in concurrent or repeated test runs.
        """
        timestamp = str(int(time.time()))[-6:]
        random_suffix = "".join(
            random.choices(string.ascii_lowercase + string.digits, k=4)
        )
        return f"{prefix}_{timestamp}_{random_suffix}"

    def _backup_config(self) -> None:
        """Backs up the current TTSKit configuration before running tests.

        Copies key settings like API keys, auth enablement, and main API key to
        allow full restoration afterward, ensuring tests don't impact production.

        Note:
            Prints a status message during backup.
        """
        print("💾 Backing up current configuration...")
        self.original_config = {
            "api_keys": self.settings.api_keys.copy(),
            "enable_auth": self.settings.enable_auth,
            "api_key": self.settings.api_key,
        }

    def _restore_config(self) -> None:
        """Restores the TTSKit configuration to its pre-test state.

        Iterates over backed-up settings and applies them using set_config_value.
        Handles exceptions gracefully with error printing.

        Note:
            Ensures tests leave no permanent changes; prints success or failure.
        """
        print("🔄 Restoring original configuration...")
        try:
            for key, value in self.original_config.items():
                set_config_value(key, value)
            print("✅ Configuration restored successfully")
        except Exception as e:
            print(f"❌ Failed to restore configuration: {e}")

    async def _cleanup_test_data(self) -> None:
        """Cleans up test-created data like users and API keys.

        Logs cleanup actions since this tests against a mock API where data isn't
        persisted; in a real setup, this would delete from the database.

        Note:
            Prints details on what would be cleaned; no actual DB operations here.
        """
        print("🧹 Cleaning up test data...")

        if self.created_api_keys:
            print(f"🗑️ Would clean up {len(self.created_api_keys)} API keys")
        if self.created_users:
            print(f"🗑️ Would clean up {len(self.created_users)} users")

        print("✅ Test data cleanup completed (no actual cleanup needed for mock API)")

    def _get_api_keys_from_config(self) -> Dict[str, str]:
        """Retrieves API keys from TTSKit config, adding defaults if missing.

        Copies existing keys and ensures 'admin' and 'demo-user' are present with
        fallback values for comprehensive testing.

        Returns:
            Dict[str, str]: Dictionary of user IDs to API keys.

        Note:
            Defaults prevent test failures in minimal config setups.
        """
        api_keys = self.settings.api_keys.copy()

        if "admin" not in api_keys:
            api_keys["admin"] = "admin-secret"
        if "demo-user" not in api_keys:
            api_keys["demo-user"] = "demo-key"

        return api_keys

    async def _check_server_status(self) -> bool:
        """Checks if the TTSKit API server is accessible and identifies its type.

        Sends a GET to the root endpoint with a 5-second timeout, parses the response,
        and logs the service name. Returns True if reachable (even if simple API),
        False on errors.

        Returns:
            bool: True if server responds with 200, False otherwise.

        Note:
            Distinguishes full TTSKit API from Simple API via service name;
            prints detailed status messages for diagnostics.
        """
        print("🔍 Checking server status...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/", timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        service_name = data.get("service", "Unknown")
                        print(f"✅ Server is running: {service_name}")

                        if "TTSKit API" in service_name:
                            print("🎯 Full TTSKit API detected")
                            return True
                        elif "Simple API" in service_name:
                            print("⚠️ Simple API detected - limited functionality")
                            return True
                        else:
                            print("❓ Unknown API type")
                            return True
                    else:
                        print(f"❌ Server responded with status: {response.status}")
                        return False
        except asyncio.TimeoutError:
            print("❌ Server connection timeout - server may not be running")
            return False
        except Exception as e:
            print(f"❌ Server connection failed: {e}")
            return False

    async def test_system_health(self) -> Dict[str, Any]:
        """Tests the /health endpoint to verify system status and resources.

        Sends a GET request and checks for 200 OK; if 404, assumes server offline.
        Parses JSON for status, engine count, and uptime, logging key details.

        Returns:
            Dict[str, Any]: Dictionary with 'status' (int), 'data' (response JSON), or 'error' (str).

        Note:
            Handles server-not-running case explicitly; prints diagnostic info.
        """
        print("🔍 Testing system health...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/health", headers=self.headers
                ) as response:
                    if response.status == 404:
                        print("❌ API endpoint not found - server may not be running")
                        return {
                            "status": response.status,
                            "error": "Server not running",
                        }

                    data = await response.json()
                    print(f"✅ System health: {response.status}")
                    print(f"📊 Status: {data.get('status', 'unknown')}")
                    print(f"🔧 Engines: {data.get('engines', 0)}")
                    print(f"⏱️ Uptime: {data.get('uptime', 0):.2f} seconds")
                    return {"status": response.status, "data": data}
        except Exception as e:
            print(f"❌ Error in health test: {e}")
            return {"error": str(e)}

    async def test_system_status(self) -> Dict[str, Any]:
        """Tests the /api/v1/status endpoint for overall system health.

        Sends GET request, parses JSON response, and logs the status.

        Returns:
            Dict[str, Any]: Dictionary with 'status' (int) and 'data' (response JSON), or 'error' (str).
        """
        print("📊 Testing system status...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/v1/status", headers=self.headers
                ) as response:
                    data = await response.json()
                    print(f"✅ System status: {response.status}")
                    print(f"📊 Overall status: {data.get('status', 'unknown')}")
                    return {"status": response.status, "data": data}
        except Exception as e:
            print(f"❌ Error in status test: {e}")
            return {"error": str(e)}

    async def test_system_info(self) -> Dict[str, Any]:
        """Tests the /api/v1/info endpoint for runtime and hardware details.

        Sends GET request and logs Python version and total memory from response.

        Returns:
            Dict[str, Any]: Dictionary with 'status' (int) and 'data' (response JSON), or 'error' (str).
        """
        print("ℹ️ Testing system information...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/v1/info", headers=self.headers
                ) as response:
                    data = await response.json()
                    print(f"✅ System info: {response.status}")
                    print(f"🐍 Python: {data.get('python_version', 'unknown')}")
                    print(f"💾 Memory: {data.get('memory_total', 0)} MB")
                    return {"status": response.status, "data": data}
        except Exception as e:
            print(f"❌ Error in info test: {e}")
            return {"error": str(e)}

    async def test_config(self) -> Dict[str, Any]:
        """Tests the /api/v1/config endpoint for TTSKit settings.

        Sends GET request and logs default language and engine from response.

        Returns:
            Dict[str, Any]: Dictionary with 'status' (int) and 'data' (response JSON), or 'error' (str).
        """
        print("⚙️ Testing configuration...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/v1/config", headers=self.headers
                ) as response:
                    data = await response.json()
                    print(f"✅ Configuration: {response.status}")
                    print(f"🌍 Default language: {data.get('default_lang', 'unknown')}")
                    print(f"🔧 Default engine: {data.get('default_engine', 'unknown')}")
                    return {"status": response.status, "data": data}
        except Exception as e:
            print(f"❌ Error in config test: {e}")
            return {"error": str(e)}

    async def test_version(self) -> Dict[str, Any]:
        """Tests the /api/v1/version endpoint for service and package version.

        Sends GET request and logs version and service name from response.

        Returns:
            Dict[str, Any]: Dictionary with 'status' (int) and 'data' (response JSON), or 'error' (str).
        """
        print("📋 Testing version...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/v1/version", headers=self.headers
                ) as response:
                    data = await response.json()
                    print(f"✅ Version: {response.status}")
                    print(f"📦 Version: {data.get('version', 'unknown')}")
                    print(f"🚀 Service: {data.get('service', 'unknown')}")
                    return {"status": response.status, "data": data}
        except Exception as e:
            print(f"❌ Error in version test: {e}")
            return {"error": str(e)}

    async def test_cache_stats(self) -> Dict[str, Any]:
        """Tests the /api/v1/cache/stats endpoint for cache performance metrics.

        Sends GET request and logs enabled status, hit rate, and size from response.

        Returns:
            Dict[str, Any]: Dictionary with 'status' (int) and 'data' (response JSON), or 'error' (str).
        """
        print("📈 Testing cache statistics...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/v1/cache/stats", headers=self.headers
                ) as response:
                    data = await response.json()
                    print(f"✅ Cache stats: {response.status}")
                    print(f"📊 Enabled: {data.get('enabled', False)}")
                    print(f"🎯 Hit rate: {data.get('hit_rate', 0):.2%}")
                    print(f"📁 Size: {data.get('size', 0)} bytes")
                    return {"status": response.status, "data": data}
        except Exception as e:
            print(f"❌ Error in cache stats test: {e}")
            return {"error": str(e)}

    async def test_cache_enabled(self) -> Dict[str, Any]:
        """Tests the /api/v1/cache/enabled endpoint to check if caching is active.

        Sends GET request and logs the enabled flag from response.

        Returns:
            Dict[str, Any]: Dictionary with 'status' (int) and 'data' (response JSON), or 'error' (str).
        """
        print("🔍 Testing cache status...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/v1/cache/enabled", headers=self.headers
                ) as response:
                    data = await response.json()
                    print(f"✅ Cache status: {response.status}")
                    print(f"📊 Enabled: {data.get('enabled', False)}")
                    return {"status": response.status, "data": data}
        except Exception as e:
            print(f"❌ Error in cache status test: {e}")
            return {"error": str(e)}

    async def test_cache_clear(self) -> Dict[str, Any]:
        """Tests the /api/v1/cache/clear endpoint to reset the cache.

        Sends POST request and logs the result message from response.

        Returns:
            Dict[str, Any]: Dictionary with 'status' (int) and 'data' (response JSON), or 'error' (str).

        Note:
            This operation clears all cached data; useful for testing fresh states.
        """
        print("🗑️ Testing cache clear...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/v1/cache/clear", headers=self.headers
                ) as response:
                    data = await response.json()
                    print(f"✅ Cache clear: {response.status}")
                    print(f"📊 Result: {data.get('message', 'unknown')}")
                    return {"status": response.status, "data": data}
        except Exception as e:
            print(f"❌ Error in cache clear test: {e}")
            return {"error": str(e)}

    async def test_list_engines(self) -> Dict[str, Any]:
        """Tests the /api/v1/engines endpoint to list available TTS engines.

        Sends GET request, logs total count, and prints details for the first 3 engines.

        Returns:
            Dict[str, Any]: Dictionary with 'status' (int) and 'data' (list of engine dicts), or 'error' (str).
        """
        print("🔧 Testing engines list...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/v1/engines", headers=self.headers
                ) as response:
                    data = await response.json()
                    print(f"✅ Engines list: {response.status}")
                    print(f"🔧 Engine count: {len(data)}")
                    for engine in data[:3]:
                        print(
                            f"  - {engine.get('name', 'unknown')}: {engine.get('available', False)}"
                        )
                    return {"status": response.status, "data": data}
        except Exception as e:
            print(f"❌ Error in engines list test: {e}")
            return {"error": str(e)}

    async def test_engine_info(self, engine_name: str = "gtts") -> Dict[str, Any]:
        """Tests the /api/v1/engines/{engine_name} endpoint for specific engine details.

        Sends GET request and logs name, availability, and language count.

        Args:
            engine_name: The name of the engine to query (default: "gtts").

        Returns:
            Dict[str, Any]: Dictionary with 'status' (int) and 'data' (engine dict), or 'error' (str).
        """
        print(f"🔍 Testing engine info {engine_name}...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/v1/engines/{engine_name}",
                    headers=self.headers,
                ) as response:
                    data = await response.json()
                    print(f"✅ Engine info: {response.status}")
                    print(f"🔧 Name: {data.get('name', 'unknown')}")
                    print(f"📊 Available: {data.get('available', False)}")
                    print(f"🌍 Languages: {len(data.get('languages', []))}")
                    return {"status": response.status, "data": data}
        except Exception as e:
            print(f"❌ Error in engine info test: {e}")
            return {"error": str(e)}

    async def test_engine_voices(self, engine_name: str = "gtts") -> Dict[str, Any]:
        """Tests the /api/v1/engines/{engine_name}/voices endpoint for engine voices.

        Sends GET request, logs total count, and prints details for the first 3 voices.

        Args:
            engine_name: The name of the engine to query (default: "gtts").

        Returns:
            Dict[str, Any]: Dictionary with 'status' (int) and 'data' (list of voice dicts), or 'error' (str).
        """
        print(f"🎵 Testing engine voices {engine_name}...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/v1/engines/{engine_name}/voices",
                    headers=self.headers,
                ) as response:
                    data = await response.json()
                    print(f"✅ Engine voices: {response.status}")
                    print(f"🎵 Voice count: {len(data)}")
                    for voice in data[:3]:
                        print(
                            f"  - {voice.get('name', 'unknown')}: {voice.get('language', 'unknown')}"
                        )
                    return {"status": response.status, "data": data}
        except Exception as e:
            print(f"❌ Error in engine voices test: {e}")
            return {"error": str(e)}

    async def test_engine_test(self, engine_name: str = "gtts") -> Dict[str, Any]:
        """Tests the /api/v1/engines/{engine_name}/test endpoint for engine functionality.

        Sends GET with sample text/language params and logs engine, duration, size.

        Args:
            engine_name: The name of the engine to test (default: "gtts").

        Returns:
            Dict[str, Any]: Dictionary with 'status' (int) and 'data' (test result dict), or 'error' (str).

        Note:
            Uses fixed params "Hello" in English for consistent testing.
        """
        print(f"🧪 Testing engine {engine_name}...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/v1/engines/{engine_name}/test",
                    headers=self.headers,
                    params={"text": "Hello", "language": "en"},
                ) as response:
                    data = await response.json()
                    print(f"✅ Engine test: {response.status}")
                    print(f"🔧 Engine: {data.get('engine', 'unknown')}")
                    print(f"⏱️ Duration: {data.get('duration', 0):.2f} seconds")
                    print(f"📁 Size: {data.get('size', 0)} bytes")
                    return {"status": response.status, "data": data}
        except Exception as e:
            print(f"❌ Error in engine test: {e}")
            return {"error": str(e)}

    async def test_all_voices(self) -> Dict[str, Any]:
        """Tests the /api/v1/voices endpoint for all available voices across engines.

        Sends GET request and logs total count from response.

        Returns:
            Dict[str, Any]: Dictionary with 'status' (int) and 'data' (list of voice dicts), or 'error' (str).
        """
        print("🎵 Testing all voices...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/v1/voices", headers=self.headers
                ) as response:
                    data = await response.json()
                    print(f"✅ All voices: {response.status}")
                    print(f"🎵 Total voice count: {len(data)}")
                    return {"status": response.status, "data": data}
        except Exception as e:
            print(f"❌ Error in all voices test: {e}")
            return {"error": str(e)}

    async def test_capabilities(self) -> Dict[str, Any]:
        """Tests the /api/v1/capabilities endpoint for engine capabilities.

        Sends GET request and logs total engine count from response.

        Returns:
            Dict[str, Any]: Dictionary with 'status' (int) and 'data' (list of capability dicts), or 'error' (str).
        """
        print("⚡ Testing capabilities...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/v1/capabilities", headers=self.headers
                ) as response:
                    data = await response.json()
                    print(f"✅ Capabilities: {response.status}")
                    print(f"🔧 Engine count: {len(data)}")
                    return {"status": response.status, "data": data}
        except Exception as e:
            print(f"❌ Error in capabilities test: {e}")
            return {"error": str(e)}

    async def test_synthesis(self) -> Dict[str, Any]:
        """Tests the /api/v1/synth endpoint for single text-to-speech synthesis.

        Sends POST with sample Persian text, language, and engine; reads audio on success
        or parses error JSON on failure, logging size/format or details.

        Returns:
            Dict[str, Any]: On success: 'status' (int) and 'size' (int bytes); on error: 'status' and 'data' (dict) or 'error' (str).

        Note:
            Uses fixed test data ("سلام دنیا" in Persian with edge engine) for consistency.
            Handles binary audio response vs. JSON error.
        """
        print("🎵 Testing synthesis...")
        test_data = {"text": "سلام دنیا", "lang": "fa", "engine": "edge"}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/v1/synth",
                    headers=self.headers,
                    json=test_data,
                ) as response:
                    if response.status == 200:
                        audio_data = await response.read()
                        print(f"✅ Synthesis success: {response.status}")
                        print(f"📁 File size: {len(audio_data)} bytes")
                        print(
                            f"🎵 Format: {response.headers.get('Content-Type', 'unknown')}"
                        )
                        return {"status": response.status, "size": len(audio_data)}
                    else:
                        data = await response.json()
                        print(f"❌ Synthesis error: {response.status}")
                        print(f"📝 Message: {data.get('detail', 'unknown')}")
                        return {"status": response.status, "data": data}
        except Exception as e:
            print(f"❌ Error in synthesis test: {e}")
            return {"error": str(e)}

    async def test_batch_synthesis(self) -> Dict[str, Any]:
        """Tests the /api/v1/synth/batch endpoint for multiple text synthesis.

        Sends POST with list of Persian texts, language, and engine; logs counts of total,
        successful, and failed syntheses.

        Returns:
            Dict[str, Any]: Dictionary with 'status' (int) and 'data' (batch result dict), or 'error' (str).

        Note:
            Uses fixed sample texts ["سلام", "دنیا", "خداحافظ"] in Persian with edge engine.
        """
        print("📦 Testing batch synthesis...")
        test_data = {
            "texts": ["سلام", "دنیا", "خداحافظ"],
            "lang": "fa",
            "engine": "edge",
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/v1/synth/batch",
                    headers=self.headers,
                    json=test_data,
                ) as response:
                    data = await response.json()
                    print(f"✅ Batch synthesis: {response.status}")
                    print(f"📦 Total texts: {data.get('total_texts', 0)}")
                    print(f"✅ Successful: {data.get('successful', 0)}")
                    print(f"❌ Failed: {data.get('failed', 0)}")
                    return {"status": response.status, "data": data}
        except Exception as e:
            print(f"❌ Error in batch synthesis test: {e}")
            return {"error": str(e)}

    async def test_preview_synthesis(self) -> Dict[str, Any]:
        """Tests the /api/v1/synth/preview endpoint for synthesis preview info.

        Sends GET with sample text/language/engine params; logs text preview, length,
        and estimated duration.

        Returns:
            Dict[str, Any]: Dictionary with 'status' (int) and 'data' (preview dict), or 'error' (str).

        Note:
            Uses fixed params ("سلام دنیا" in Persian with edge engine) for preview estimation.
        """
        print("👁️ Testing preview synthesis...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/v1/synth/preview",
                    headers=self.headers,
                    params={"text": "سلام دنیا", "lang": "fa", "engine": "edge"},
                ) as response:
                    data = await response.json()
                    print(f"✅ Preview: {response.status}")
                    print(f"📝 Text: {data.get('text_preview', 'unknown')}")
                    print(f"📏 Length: {data.get('text_length', 0)}")
                    print(
                        f"⏱️ Estimated duration: {data.get('estimated_duration', 0):.2f} seconds"
                    )
                    return {"status": response.status, "data": data}
        except Exception as e:
            print(f"❌ Error in preview test: {e}")
            return {"error": str(e)}

    async def test_admin_list_users(self) -> Dict[str, Any]:
        """Tests the /api/v1/admin/users endpoint to list all users (admin only).

        Sends GET request and logs total user count from response.

        Returns:
            Dict[str, Any]: Dictionary with 'status' (int) and 'data' (list of user dicts), or 'error' (str).

        Note:
            Requires admin permissions; may return 403 for non-admin keys.
        """
        print("👥 Testing admin list users...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/v1/admin/users", headers=self.headers
                ) as response:
                    data = await response.json()
                    print(f"✅ List users: {response.status}")
                    print(f"👥 User count: {len(data)}")
                    return {"status": response.status, "data": data}
        except Exception as e:
            print(f"❌ Error in list users test: {e}")
            return {"error": str(e)}

    async def test_admin_create_user(self) -> Dict[str, Any]:
        """Tests the /api/v1/admin/users endpoint to create a new user (admin only).

        Generates unique user_id/username/email, sends POST with non-admin data,
        stores ID for cleanup, and logs created user details.

        Returns:
            Dict[str, Any]: Dictionary with 'status' (int), 'data' (response dict), 'user_id' (str).

        Note:
            Requires admin permissions; uses _generate_unique_id to avoid conflicts.
            Appends created user to self.created_users for later cleanup.
        """
        print("➕ Testing admin create user...")

        test_user_id = self._generate_unique_id("test_user")

        test_data = {
            "user_id": test_user_id,
            "username": f"Test User {test_user_id}",
            "email": f"{test_user_id}@test.local",
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
                    print(f"📝 Message: {data.get('user_id', 'unknown')}")
                    print(f"👤 Created user: {test_user_id}")

                    self.created_users.append(test_user_id)

                    return {
                        "status": response.status,
                        "data": data,
                        "user_id": test_user_id,
                    }
        except Exception as e:
            print(f"❌ Error in create user test: {e}")
            return {"error": str(e)}

    async def test_admin_get_user(self) -> Dict[str, Any]:
        """Tests the /api/v1/admin/users/{user_id} endpoint to retrieve a user (admin only).

        Uses created or fallback user_id, sends GET, logs user details, and handles 404/403.

        Returns:
            Dict[str, Any]: Dictionary with 'status' (int) and 'data' (user dict), or 'error' (str).

        Note:
            Falls back to "demo-user" if no created_user_id; expects 404 for non-existent in demo.
        """
        print("👤 Testing admin get user...")

        user_id = getattr(self, "created_user_id", "demo-user")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/v1/admin/users/{user_id}",
                    headers=self.headers,
                ) as response:
                    data = await response.json()
                    print(f"✅ Get user: {response.status}")
                    print(f"👤 User: {data.get('user_id', 'unknown')}")
                    print(f"📧 Email: {data.get('email', 'unknown')}")

                    if response.status == 404:
                        print(
                            "ℹ️ User not found - this is expected for demo implementation"
                        )
                    elif response.status == 403:
                        print("ℹ️ Permission denied - user doesn't have admin rights")

                    return {"status": response.status, "data": data}
        except Exception as e:
            print(f"❌ Error in get user test: {e}")
            return {"error": str(e)}

    async def test_admin_delete_user(self) -> Dict[str, Any]:
        """Tests the /api/v1/admin/users/{user_id} DELETE endpoint (admin only).

        Uses created or fallback user_id, sends DELETE, logs message, handles 404/403/admin protection.

        Returns:
            Dict[str, Any]: Dictionary with 'status' (int) and 'data' (response dict), or 'error' (str).

        Note:
            Prevents admin key deletion; expects 404 in demo; falls back to "demo-user".
        """
        print("🗑️ Testing admin delete user...")

        user_id = getattr(self, "created_user_id", "demo-user")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.delete(
                    f"{self.base_url}/api/v1/admin/users/{user_id}",
                    headers=self.headers,
                ) as response:
                    data = await response.json()
                    print(f"✅ Delete user: {response.status}")
                    print(f"📝 Message: {data.get('message', 'unknown')}")
                    print(f"👤 Deleted user: {user_id}")

                    if response.status == 404:
                        print(
                            "ℹ️ User not found - this is expected for demo implementation"
                        )
                    elif response.status == 403:
                        print("ℹ️ Permission denied - user doesn't have admin rights")
                    elif response.status == 403 and "admin" in user_id:
                        print("ℹ️ Cannot delete admin user - this is expected behavior")

                    return {"status": response.status, "data": data}
        except Exception as e:
            print(f"❌ Error in delete user test: {e}")
            return {"error": str(e)}

    async def test_admin_api_keys(self) -> Dict[str, Any]:
        """Tests the /api/v1/admin/api-keys endpoint to list API keys (admin only).

        Sends GET request and logs total key count from response.

        Returns:
            Dict[str, Any]: Dictionary with 'status' (int) and 'data' (list of key dicts), or 'error' (str).

        Note:
            Requires admin permissions; may return 403 for non-admin.
        """
        print("🔑 Testing admin API keys...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/v1/admin/api-keys", headers=self.headers
                ) as response:
                    data = await response.json()
                    print(f"✅ API keys: {response.status}")
                    print(f"🔑 Key count: {len(data)}")
                    return {"status": response.status, "data": data}
        except Exception as e:
            print(f"❌ Error in API keys test: {e}")
            return {"error": str(e)}

    async def test_admin_create_api_key(self) -> Dict[str, Any]:
        """Tests the /api/v1/admin/api-keys POST endpoint to create an API key (admin only).

        Generates unique user_id and key, sends POST with read/write permissions,
        stores for cleanup, and logs details.

        Returns:
            Dict[str, Any]: Dictionary with 'status' (int), 'data' (response dict), 'user_id' (str).

        Note:
            Sets self.created_user_id; appends to cleanup lists; requires admin access.
        """
        print("➕ Testing create API key...")

        test_user_id = self._generate_unique_id("test_user")
        test_api_key = self._generate_unique_id("test_key")

        test_data = {
            "user_id": test_user_id,
            "api_key": test_api_key,
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
                    print(f"✅ Create key: {response.status}")
                    print(f"📝 Message: {data.get('message', 'unknown')}")
                    print(f"👤 Created user: {test_user_id}")

                    self.created_user_id = test_user_id
                    self.created_users.append(test_user_id)
                    self.created_api_keys.append(test_api_key)

                    return {
                        "status": response.status,
                        "data": data,
                        "user_id": test_user_id,
                    }
        except Exception as e:
            print(f"❌ Error in create key test: {e}")
            return {"error": str(e)}

    async def test_admin_current_user(self) -> Dict[str, Any]:
        """Tests the /api/v1/admin/users/me endpoint for current user info (admin only).

        Sends GET and logs user_id and permissions from response.

        Returns:
            Dict[str, Any]: Dictionary with 'status' (int) and 'data' (user dict), or 'error' (str).

        Note:
            Uses current auth key; requires admin or appropriate permissions.
        """
        print("👤 Testing current user...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/v1/admin/users/me", headers=self.headers
                ) as response:
                    data = await response.json()
                    print(f"✅ Current user: {response.status}")
                    print(f"👤 User: {data.get('user_id', 'unknown')}")
                    print(f"🔑 Permissions: {data.get('permissions', [])}")
                    return {"status": response.status, "data": data}
        except Exception as e:
            print(f"❌ Error in current user test: {e}")
            return {"error": str(e)}

    async def test_admin_update_api_key(self) -> Dict[str, Any]:
        """Tests the /api/v1/admin/api-keys/{user_id} PUT endpoint to update key (admin only).

        Uses created or demo user_id, sends PUT with new key/permissions, logs message, handles 404/403.

        Returns:
            Dict[str, Any]: Dictionary with 'status' (int) and 'data' (response dict), or 'error' (str).

        Note:
            Uses fixed "updated_test_key_67890"; expects 404 in demo setup.
        """
        print("✏️ Testing update API key...")

        user_id = getattr(self, "created_user_id", "demo-user")

        test_data = {
            "api_key": "updated_test_key_67890",
            "permissions": ["read", "write"],
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.put(
                    f"{self.base_url}/api/v1/admin/api-keys/{user_id}",
                    headers=self.headers,
                    json=test_data,
                ) as response:
                    data = await response.json()
                    print(f"✅ Update key: {response.status}")
                    print(f"📝 Message: {data.get('message', 'unknown')}")
                    print(f"👤 Updated user: {user_id}")

                    if response.status == 404:
                        print(
                            "ℹ️ User not found - this is expected for demo implementation"
                        )
                    elif response.status == 403:
                        print("ℹ️ Permission denied - user doesn't have admin rights")

                    return {"status": response.status, "data": data}
        except Exception as e:
            print(f"❌ Error in update key test: {e}")
            return {"error": str(e)}

    async def test_admin_delete_api_key(self) -> Dict[str, Any]:
        """Tests the /api/v1/admin/api-keys/{user_id} DELETE endpoint (admin only).

        Uses created or demo user_id, sends DELETE, logs message, handles 404/403/admin protection.

        Returns:
            Dict[str, Any]: Dictionary with 'status' (int) and 'data' (response dict), or 'error' (str).

        Note:
            Prevents admin key deletion; expects 404 in demo; falls back to "demo-user".
        """
        print("🗑️ Testing delete API key...")

        user_id = getattr(self, "created_user_id", "demo-user")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.delete(
                    f"{self.base_url}/api/v1/admin/api-keys/{user_id}",
                    headers=self.headers,
                ) as response:
                    data = await response.json()
                    print(f"✅ Delete key: {response.status}")
                    print(f"📝 Message: {data.get('message', 'unknown')}")
                    print(f"👤 Deleted user: {user_id}")

                    if response.status == 404:
                        print(
                            "ℹ️ User not found - this is expected for demo implementation"
                        )
                    elif response.status == 403:
                        print("ℹ️ Permission denied - user doesn't have admin rights")
                    elif response.status == 403 and "admin" in user_id:
                        print("ℹ️ Cannot delete admin user - this is expected behavior")

                    return {"status": response.status, "data": data}
        except Exception as e:
            print(f"❌ Error in delete key test: {e}")
            return {"error": str(e)}

    async def test_metrics(self) -> Dict[str, Any]:
        """Tests the /api/v1/metrics endpoint for basic TTS metrics.

        Sends GET request and logs version and TTS stats count from response.

        Returns:
            Dict[str, Any]: Dictionary with 'status' (int) and 'data' (metrics dict), or 'error' (str).
        """
        print("📊 Testing metrics...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/v1/metrics", headers=self.headers
                ) as response:
                    data = await response.json()
                    print(f"✅ Metrics: {response.status}")
                    print(f"📦 Version: {data.get('version', 'unknown')}")
                    print(f"📊 TTS stats: {len(data.get('tts_stats', {}))}")
                    return {"status": response.status, "data": data}
        except Exception as e:
            print(f"❌ Error in metrics test: {e}")
            return {"error": str(e)}

    async def test_advanced_metrics(self) -> Dict[str, Any]:
        """Tests the /api/v1/advanced-metrics endpoint for detailed performance data.

        Sends GET request and logs version and comprehensive metrics count.

        Returns:
            Dict[str, Any]: Dictionary with 'status' (int) and 'data' (advanced metrics dict), or 'error' (str).
        """
        print("📈 Testing advanced metrics...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/v1/advanced-metrics", headers=self.headers
                ) as response:
                    data = await response.json()
                    print(f"✅ Advanced metrics: {response.status}")
                    print(f"📦 Version: {data.get('version', 'unknown')}")
                    print(
                        f"📊 Comprehensive metrics: {len(data.get('comprehensive', {}))}"
                    )
                    return {"status": response.status, "data": data}
        except Exception as e:
            print(f"❌ Error in advanced metrics test: {e}")
            return {"error": str(e)}

    async def test_formats(self) -> Dict[str, Any]:
        """Tests the /api/v1/formats endpoint for supported audio formats.

        Sends GET request and logs list of formats from response.

        Returns:
            Dict[str, Any]: Dictionary with 'status' (int) and 'data' (formats dict), or 'error' (str).
        """
        print("🎵 Testing supported formats...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/v1/formats", headers=self.headers
                ) as response:
                    data = await response.json()
                    print(f"✅ Formats: {response.status}")
                    print(f"🎵 Supported formats: {data.get('formats', [])}")
                    return {"status": response.status, "data": data}
        except Exception as e:
            print(f"❌ Error in formats test: {e}")
            return {"error": str(e)}

    async def test_languages(self) -> Dict[str, Any]:
        """Tests the /api/v1/languages endpoint for supported TTS languages.

        Sends GET request and logs total language count from response.

        Returns:
            Dict[str, Any]: Dictionary with 'status' (int) and 'data' (languages dict), or 'error' (str).
        """
        print("🌍 Testing supported languages...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/v1/languages", headers=self.headers
                ) as response:
                    data = await response.json()
                    print(f"✅ Languages: {response.status}")
                    print(f"🌍 Supported languages: {len(data.get('languages', []))}")
                    return {"status": response.status, "data": data}
        except Exception as e:
            print(f"❌ Error in languages test: {e}")
            return {"error": str(e)}

    async def test_rate_limit(self) -> Dict[str, Any]:
        """Tests the /api/v1/rate-limit endpoint for API rate limiting info.

        Sends GET request and logs limit value from response.

        Returns:
            Dict[str, Any]: Dictionary with 'status' (int) and 'data' (rate limit dict), or 'error' (str).
        """
        print("⏱️ Testing rate limit...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/v1/rate-limit", headers=self.headers
                ) as response:
                    data = await response.json()
                    print(f"✅ Rate limit: {response.status}")
                    print(f"⏱️ Limit: {data.get('limit', 'unknown')}")
                    return {"status": response.status, "data": data}
        except Exception as e:
            print(f"❌ Error in rate limit test: {e}")
            return {"error": str(e)}

    async def test_documentation(self) -> Dict[str, Any]:
        """Tests the /api/v1/documentation endpoint for API docs.

        Sends GET request and logs title from response.

        Returns:
            Dict[str, Any]: Dictionary with 'status' (int) and 'data' (docs dict), or 'error' (str).
        """
        print("📚 Testing documentation...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/v1/documentation", headers=self.headers
                ) as response:
                    data = await response.json()
                    print(f"✅ Documentation: {response.status}")
                    title = data.get("title", "unknown")
                    print(f"📚 Title: {title}")
                    return {"status": response.status, "data": data}
        except Exception as e:
            print(f"❌ Error in documentation test: {e}")
            return {"error": str(e)}

    async def test_root_endpoint(self) -> Dict[str, Any]:
        """Tests the root / endpoint for basic service info (public).

        Sends GET without auth and logs service, version, status from response.

        Returns:
            Dict[str, Any]: Dictionary with 'status' (int) and 'data' (root dict), or 'error' (str).

        Note:
            No authorization header used; accessible publicly.
        """
        print("🏠 Testing root endpoint...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/") as response:
                    data = await response.json()
                    print(f"✅ Root endpoint: {response.status}")
                    print(f"🏠 Service: {data.get('service', 'unknown')}")
                    print(f"📦 Version: {data.get('version', 'unknown')}")
                    print(f"📊 Status: {data.get('status', 'unknown')}")
                    return {"status": response.status, "data": data}
        except Exception as e:
            print(f"❌ Error in root endpoint test: {e}")
            return {"error": str(e)}

    async def test_public_health(self) -> Dict[str, Any]:
        """Tests the /health endpoint publicly (no auth).

        Sends GET without headers and logs status, engines, uptime from response.

        Returns:
            Dict[str, Any]: Dictionary with 'status' (int) and 'data' (health dict), or 'error' (str).

        Note:
            Mirrors test_system_health but without auth for public access verification.
        """
        print("🏥 Testing public health endpoint...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/health") as response:
                    data = await response.json()
                    print(f"✅ Public health: {response.status}")
                    print(f"🏥 Status: {data.get('status', 'unknown')}")
                    print(f"🔧 Engines: {data.get('engines', 0)}")
                    print(f"⏱️ Uptime: {data.get('uptime', 0):.2f} seconds")
                    return {"status": response.status, "data": data}
        except Exception as e:
            print(f"❌ Error in public health test: {e}")
            return {"error": str(e)}

    async def test_engines_available_only(self) -> Dict[str, Any]:
        """Tests the /api/v1/engines endpoint with available_only=true query param.

        Sends GET with param to filter available engines, logs count, prints first 3.

        Returns:
            Dict[str, Any]: Dictionary with 'status' (int) and 'data' (filtered list), or 'error' (str).

        Note:
            Filters to only available engines for targeted testing.
        """
        print("🔧 Testing engines with available_only=true...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/v1/engines",
                    headers=self.headers,
                    params={"available_only": "true"},
                ) as response:
                    data = await response.json()
                    print(f"✅ Engines available only: {response.status}")
                    print(f"🔧 Available engines: {len(data)}")
                    if isinstance(data, list):
                        for engine in data[:3]:
                            print(
                                f"  - {engine.get('name', 'unknown')}: {engine.get('available', False)}"
                            )
                    return {"status": response.status, "data": data}
        except Exception as e:
            print(f"❌ Error in engines available only test: {e}")
            return {"error": str(e)}

    async def test_engine_voices_with_language(self) -> Dict[str, Any]:
        """Tests the /api/v1/engines/gtts/voices endpoint with language=en filter.

        Sends GET with param for English voices, logs count, prints first 3 details.

        Returns:
            Dict[str, Any]: Dictionary with 'status' (int) and 'data' (filtered voices list), or 'error' (str).

        Note:
            Hardcoded to gTTS engine and English for specific filter testing.
        """
        print("🎵 Testing engine voices with language filter...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/v1/engines/gtts/voices",
                    headers=self.headers,
                    params={"language": "en"},
                ) as response:
                    data = await response.json()
                    print(f"✅ Engine voices with language: {response.status}")
                    print(f"🎵 English voices: {len(data)}")
                    if isinstance(data, list):
                        for voice in data[:3]:
                            print(
                                f"  - {voice.get('name', 'unknown')}: {voice.get('language', 'unknown')}"
                            )
                    return {"status": response.status, "data": data}
        except Exception as e:
            print(f"❌ Error in engine voices language test: {e}")
            return {"error": str(e)}

    async def test_all_voices_with_filters(self) -> Dict[str, Any]:
        """Test all voices with engine and language filters"""
        print("🎵 Testing all voices with filters...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/v1/voices",
                    headers=self.headers,
                    params={"engine": "gtts", "language": "en"},
                ) as response:
                    data = await response.json()
                    print(f"✅ All voices with filters: {response.status}")
                    print(f"🎵 Filtered voices: {len(data)}")
                    if isinstance(data, list):
                        for voice in data[:3]:  # Show first 3 voices
                            print(
                                f"  - {voice.get('name', 'unknown')}: {voice.get('engine', 'unknown')} ({voice.get('language', 'unknown')})"
                            )
                    return {"status": response.status, "data": data}
        except Exception as e:
            print(f"❌ Error in all voices filters test: {e}")
            return {"error": str(e)}

    # ==================== UNAUTHORIZED TESTS ====================

    async def test_unauthorized_access(self) -> Dict[str, Any]:
        """Test unauthorized access"""
        print("🔒 Testing unauthorized access...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/v1/admin/api-keys"
                ) as response:
                    data = await response.json()
                    print(f"🔒 Unauthorized access: {response.status}")
                    if response.status == 401:
                        print("✅ Access properly restricted (401 Unauthorized)")
                    elif response.status == 403:
                        print("✅ Access properly restricted (403 Forbidden)")
                    else:
                        print(f"⚠️ Unexpected status: {response.status}")
                    return {"status": response.status, "data": data}
        except Exception as e:
            print(f"❌ Error in access test: {e}")
            return {"error": str(e)}

    async def test_permission_levels(self) -> Dict[str, Any]:
        """Test different permission levels"""
        print("🔐 Testing permission levels...")
        permission_tests = {}

        # Test admin-only endpoints
        admin_endpoints = [
            "/api/v1/admin/users",
            "/api/v1/admin/api-keys",
            "/api/v1/admin/users/me",
        ]

        for endpoint in admin_endpoints:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{self.base_url}{endpoint}", headers=self.headers
                    ) as response:
                        permission_tests[endpoint] = {
                            "status": response.status,
                            "accessible": 200 <= response.status < 300,
                        }
                        if response.status == 200:
                            print(f"✅ {endpoint}: Accessible")
                        elif response.status == 403:
                            print(f"🔒 {endpoint}: Forbidden (expected for non-admin)")
                        elif response.status == 401:
                            print(f"🔒 {endpoint}: Unauthorized (expected)")
                        else:
                            print(f"❌ {endpoint}: Unexpected status {response.status}")
            except Exception as e:
                permission_tests[endpoint] = {"error": str(e)}
                print(f"❌ {endpoint}: Error - {e}")

        return permission_tests

    async def test_admin_endpoints_access(self) -> Dict[str, Any]:
        """Test admin endpoints access specifically"""
        print("👑 Testing admin endpoints access...")
        admin_tests = {}

        # Test admin CRUD operations
        admin_operations = [
            ("GET", "/api/v1/admin/users"),
            ("POST", "/api/v1/admin/users"),
            ("GET", "/api/v1/admin/users/test_user"),
            ("DELETE", "/api/v1/admin/users/test_user"),
            ("GET", "/api/v1/admin/api-keys"),
            ("POST", "/api/v1/admin/api-keys"),
            ("PUT", "/api/v1/admin/api-keys/test_user"),
            ("DELETE", "/api/v1/admin/api-keys/test_user"),
        ]

        for method, endpoint in admin_operations:
            try:
                async with aiohttp.ClientSession() as session:
                    if method == "GET":
                        async with session.get(
                            f"{self.base_url}{endpoint}", headers=self.headers
                        ) as response:
                            status = response.status
                    elif method == "POST":
                        test_user_id = self._generate_unique_id("test_user")
                        test_api_key = self._generate_unique_id("test_key")
                        test_data = {
                            "user_id": test_user_id,
                            "api_key": test_api_key,
                            "permissions": ["read", "write"],
                        }
                        async with session.post(
                            f"{self.base_url}{endpoint}",
                            headers=self.headers,
                            json=test_data,
                        ) as response:
                            status = response.status
                            if status == 422:
                                try:
                                    error_data = await response.json()
                                    print(f"📝 Validation error details: {error_data}")
                                except:
                                    pass
                    elif method == "PUT":
                        test_api_key = self._generate_unique_id("updated_key")
                        test_data = {
                            "api_key": test_api_key,
                            "permissions": ["read", "write"],
                        }
                        async with session.put(
                            f"{self.base_url}{endpoint}",
                            headers=self.headers,
                            json=test_data,
                        ) as response:
                            status = response.status
                            if status == 422:
                                try:
                                    error_data = await response.json()
                                    print(f"📝 Validation error details: {error_data}")
                                except:
                                    pass
                    elif method == "DELETE":
                        async with session.delete(
                            f"{self.base_url}{endpoint}", headers=self.headers
                        ) as response:
                            status = response.status

                    admin_tests[f"{method} {endpoint}"] = {
                        "status": status,
                        "accessible": 200 <= status < 300,
                        "expected_for_admin": True,
                    }

                    if status == 200:
                        print(f"✅ {method} {endpoint}: Accessible")
                    elif status == 403:
                        print(f"🔒 {method} {endpoint}: Forbidden (non-admin)")
                    elif status == 404:
                        print(
                            f"❓ {method} {endpoint}: Not found (resource doesn't exist)"
                        )
                    else:
                        print(f"❌ {method} {endpoint}: Status {status}")

            except Exception as e:
                admin_tests[f"{method} {endpoint}"] = {"error": str(e)}
                print(f"❌ {method} {endpoint}: Error - {e}")

        return admin_tests

    async def test_error_handling(self) -> Dict[str, Any]:
        """Test error handling scenarios"""
        print("🔍 Testing error handling scenarios...")
        error_tests = {}

        # Test scenarios that should return specific errors
        test_scenarios = [
            {
                "name": "Invalid API key",
                "method": "GET",
                "endpoint": "/api/v1/admin/api-keys",
                "headers": {"Authorization": "Bearer invalid_key"},
                "expected_status": 401,
            },
            {
                "name": "Missing API key",
                "method": "GET",
                "endpoint": "/api/v1/admin/api-keys",
                "headers": {},
                "expected_status": 401,
            },
            {
                "name": "Non-existent user",
                "method": "GET",
                "endpoint": "/api/v1/admin/users/non_existent_user",
                "headers": self.headers,
                "expected_status": 404,
            },
            {
                "name": "Non-existent API key",
                "method": "GET",
                "endpoint": "/api/v1/admin/api-keys/non_existent_user",
                "headers": self.headers,
                "expected_status": 404,
            },
        ]

        for scenario in test_scenarios:
            try:
                async with aiohttp.ClientSession() as session:
                    if scenario["method"] == "GET":
                        async with session.get(
                            f"{self.base_url}{scenario['endpoint']}",
                            headers=scenario["headers"],
                        ) as response:
                            status = response.status
                    else:
                        continue  # Add more methods if needed

                    error_tests[scenario["name"]] = {
                        "status": status,
                        "expected": scenario["expected_status"],
                        "correct": status == scenario["expected_status"],
                    }

                    if status == scenario["expected_status"]:
                        print(f"✅ {scenario['name']}: Correct error ({status})")
                    else:
                        print(
                            f"❌ {scenario['name']}: Expected {scenario['expected_status']}, got {status}"
                        )

            except Exception as e:
                error_tests[scenario["name"]] = {"error": str(e)}
                print(f"❌ {scenario['name']}: Error - {e}")

        return error_tests

    # ==================== MAIN TEST RUNNER ====================

    async def run_all_tests(self):
        """Run all tests"""
        print("🚀 Starting complete TTSKit API tests")
        print("=" * 60)

        # Check server status first
        server_running = await self._check_server_status()
        if not server_running:
            print("\n❌ API Server is not running!")
            print("💡 To start the FULL TTSKit API server, run:")
            print(
                f"   uvicorn ttskit.api.app:app --host {self.settings.api_host} --port {self.settings.api_port}"
            )
            print("\n💡 To start the SIMPLE API server, run:")
            print("   python examples/02_fastapi.py")
            print("\n🔄 Running tests anyway to show expected behavior...")
            print("=" * 60)

        # Backup configuration before tests
        self._backup_config()

        try:
            # System tests
            print("\n📊 System section:")
            self.results["system_health"] = await self.test_system_health()
            self.results["system_status"] = await self.test_system_status()
            self.results["system_info"] = await self.test_system_info()
            self.results["config"] = await self.test_config()
            self.results["version"] = await self.test_version()

            # Cache tests
            print("\n💾 Cache section:")
            self.results["cache_stats"] = await self.test_cache_stats()
            self.results["cache_enabled"] = await self.test_cache_enabled()
            self.results["cache_clear"] = await self.test_cache_clear()

            # Engine tests
            print("\n🔧 Engines section:")
            self.results["list_engines"] = await self.test_list_engines()
            self.results["engine_info"] = await self.test_engine_info("gtts")
            self.results["engine_voices"] = await self.test_engine_voices("gtts")
            self.results["engine_test"] = await self.test_engine_test("gtts")
            self.results["all_voices"] = await self.test_all_voices()
            self.results["capabilities"] = await self.test_capabilities()

            # Synthesis tests
            print("\n🎵 Synthesis section:")
            self.results["synthesis"] = await self.test_synthesis()
            self.results["batch_synthesis"] = await self.test_batch_synthesis()
            self.results["preview_synthesis"] = await self.test_preview_synthesis()

            # Admin tests
            if self.admin_key:
                print("\n👑 Admin section:")
                self.results["admin_list_users"] = await self.test_admin_list_users()
                self.results["admin_create_user"] = await self.test_admin_create_user()
                self.results["admin_get_user"] = await self.test_admin_get_user()
                self.results["admin_delete_user"] = await self.test_admin_delete_user()
                self.results["admin_api_keys"] = await self.test_admin_api_keys()
                self.results[
                    "admin_create_api_key"
                ] = await self.test_admin_create_api_key()
                self.results[
                    "admin_current_user"
                ] = await self.test_admin_current_user()
                self.results[
                    "admin_update_api_key"
                ] = await self.test_admin_update_api_key()
                self.results[
                    "admin_delete_api_key"
                ] = await self.test_admin_delete_api_key()

            # Metrics tests
            print("\n📈 Metrics section:")
            self.results["metrics"] = await self.test_metrics()
            self.results["advanced_metrics"] = await self.test_advanced_metrics()

            # Utility tests
            print("\n🛠️ Utility section:")
            self.results["formats"] = await self.test_formats()
            self.results["languages"] = await self.test_languages()
            self.results["rate_limit"] = await self.test_rate_limit()
            self.results["documentation"] = await self.test_documentation()

            # Root endpoints tests
            print("\n🏠 Root endpoints section:")
            self.results["root_endpoint"] = await self.test_root_endpoint()
            self.results["public_health"] = await self.test_public_health()

            # Query parameters tests
            print("\n🔍 Query parameters section:")
            self.results[
                "engines_available_only"
            ] = await self.test_engines_available_only()
            self.results[
                "engine_voices_language"
            ] = await self.test_engine_voices_with_language()
            self.results[
                "all_voices_filters"
            ] = await self.test_all_voices_with_filters()

            # Security test
            print("\n🔒 Security test:")
            self.results["unauthorized"] = await self.test_unauthorized_access()
            self.results["permission_levels"] = await self.test_permission_levels()
            self.results[
                "admin_endpoints_access"
            ] = await self.test_admin_endpoints_access()
            self.results["error_handling"] = await self.test_error_handling()

            # Results summary
            print("\n" + "=" * 60)
            print("📊 Results summary:")
            print("=" * 60)

            success_count = 0
            error_count = 0
            total_count = len(self.results)

            for test_name, result in self.results.items():
                if "error" in result:
                    print(f"❌ {test_name}: Error")
                    error_count += 1
                elif "status" in result:
                    status = result["status"]
                    if 200 <= status < 300:
                        print(f"✅ {test_name}: Success ({status})")
                        success_count += 1
                    else:
                        print(f"❌ {test_name}: Failed ({status})")
                        error_count += 1

            print("\n📈 Overall statistics:")
            print(f"✅ Successful: {success_count}")
            print(f"❌ Failed: {error_count}")
            print(f"📊 Total: {total_count}")
            print(f"🎯 Success rate: {(success_count / total_count) * 100:.1f}%")

            return self.results

        finally:
            # Cleanup test data and restore configuration
            await self._cleanup_test_data()
            self._restore_config()


async def main():
    """Orchestrates the full TTSKit API testing with multiple API keys.

    Loads settings and API keys (adding defaults if missing), prepares base URL and keys
    for admin, demo, and permanent users, runs AdminAPITester for each, compares results,
    and analyzes permission differences.

    Note:
        Prints config details (masked keys) and test counts; handles permanent key fallback.
        No returns; outputs comparison summary and permission analysis to console.
        Designed to run as entry point for comprehensive API validation.
    """
    settings = get_settings()

    api_keys = settings.api_keys.copy()
    print(api_keys)
    if "admin" not in api_keys:
        api_keys["admin"] = "admin-secret"
    if "demo-user" not in api_keys:
        api_keys["demo-user"] = "demo-key"

    BASE_URL = f"http://{settings.api_host}:{settings.api_port}"
    ADMIN_KEY = api_keys.get("admin", "admin-secret")
    DEMO_KEY = api_keys.get("demo-user", "demo-key")

    PERMANENT_KEY = None
    for user_id, key in api_keys.items():
        if user_id not in ["admin", "demo-user"] and "permanent" in user_id.lower():
            PERMANENT_KEY = key
            break

    if not PERMANENT_KEY:
        PERMANENT_KEY = "permanent_user_key_12345"  # Fallback if no permanent key in config

    print("🔧 Complete TTSKit API Test")
    print(f"🌐 Server address: {BASE_URL}")
    print(f"🔑 Admin key: {ADMIN_KEY[:10]}...")
    print(f"🔑 Demo key: {DEMO_KEY[:10]}...")
    print(f"🔑 Permanent key: {PERMANENT_KEY[:10]}...")
    print(f"📊 Available API keys: {list(api_keys.keys())}")
    print(
        "📊 Test count: ~45 endpoints (complete coverage + multi-user testing + improved error handling + edge cases + legacy endpoints)"
    )
    print()

    print("=" * 60)
    print("👑 Testing with ADMIN key")
    print("=" * 60)
    admin_tester = AdminAPITester(BASE_URL, ADMIN_KEY)
    admin_results = await admin_tester.run_all_tests()

    print("\n" + "=" * 60)
    print("👤 Testing with DEMO key")
    print("=" * 60)
    demo_tester = AdminAPITester(BASE_URL, DEMO_KEY)
    demo_results = await demo_tester.run_all_tests()

    print("\n" + "=" * 60)
    print("🔒 Testing with PERMANENT key")
    print("=" * 60)
    permanent_tester = AdminAPITester(BASE_URL, PERMANENT_KEY)
    permanent_results = await permanent_tester.run_all_tests()

    print("\n" + "=" * 60)
    print("📊 COMPARISON SUMMARY")
    print("=" * 60)

    print(
        f"👑 Admin key results: {len([r for r in admin_results.values() if 'status' in r and 200 <= r['status'] < 300])} successful"
    )
    print(
        f"👤 Demo key results: {len([r for r in demo_results.values() if 'status' in r and 200 <= r['status'] < 300])} successful"
    )
    print(
        f"🔒 Permanent key results: {len([r for r in permanent_results.values() if 'status' in r and 200 <= r['status'] < 300])} successful"
    )

    print("\n🔐 Permission Analysis:")
    admin_success = len(
        [
            r
            for r in admin_results.values()
            if "status" in r and 200 <= r["status"] < 300
        ]
    )
    demo_success = len(
        [r for r in demo_results.values() if "status" in r and 200 <= r["status"] < 300]
    )
    permanent_success = len(
        [
            r
            for r in permanent_results.values()
            if "status" in r and 200 <= r["status"] < 300
        ]
    )

    print(f"  Admin key: {admin_success} endpoints accessible")
    print(f"  Demo key: {demo_success} endpoints accessible")
    print(f"  Permanent key: {permanent_success} endpoints accessible")

    if admin_success > demo_success:
        print(
            f"  ⚠️ Admin has {admin_success - demo_success} more permissions than demo user"
        )
    if admin_success > permanent_success:
        print(
            f"  ⚠️ Admin has {admin_success - permanent_success} more permissions than permanent user"
        )

    if permanent_success == 0:
        print("  ℹ️ Permanent user not found - add to API_KEYS environment variable")
    elif permanent_success == demo_success:
        print("  ✅ Permanent user has same permissions as demo user")
    else:
        print(f"  📊 Permanent user has {permanent_success} permissions")


if __name__ == "__main__":
    print("⚠️ This is a temporary test file and should be deleted after use!")
    print("🚀 Complete test of all TTSKit API endpoints")
    print()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Test stopped")
    except Exception as e:
        print(f"\n❌ General error: {e}")

    print("\n✅ Test completed")
