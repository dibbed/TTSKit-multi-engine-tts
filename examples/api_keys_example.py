#!/usr/bin/env python3
"""Example of using multiple API keys with TTSKit API."""

import asyncio
import json

import httpx


class TTSKitAPIClient:
    """HTTP client for TTSKit API with multiple API key authentication support.
    
    Provides methods for synthesis, user management, and admin operations
    with different permission levels based on API key configuration.
    """

    def __init__(
        self, base_url: str = "http://localhost:8000", api_key: str = "demo-key"
    ):
        """Initializes API client with authentication credentials.
        
        Args:
            base_url: TTSKit API server base URL
            api_key: API key for authentication and authorization
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    async def synthesize(self, text: str, lang: str = "en") -> bytes:
        """Synthesizes text to speech using authenticated API access.
        
        Args:
            text: Text to synthesize
            lang: Language code for synthesis
            
        Returns:
            Raw audio data as bytes
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/synth",
                headers=self.headers,
                json={"text": text, "lang": lang, "format": "wav"},
            )
            response.raise_for_status()
            return response.content

    async def get_current_user(self) -> dict:
        """Retrieves current user information based on API key.
        
        Returns:
            Dictionary with user ID, permissions, and account details
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/admin/users/me",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    async def list_api_keys(self) -> dict:
        """Lists all API keys in the system (requires admin permissions).
        
        Returns:
            Dictionary with API key information and metadata
            
        Raises:
            HTTPStatusError: If user lacks admin permissions (403)
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/admin/api-keys",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()


async def test_multiple_api_keys():
    """Tests different API keys with varying permission levels and access rights.
    
    Demonstrates how different users (admin, regular, readonly) can access
    different API endpoints based on their key permissions. Shows synthesis
    access and admin function restrictions.
    """

    print("🔐 Testing Multiple API Keys")
    print("=" * 50)

    api_keys = {
        "ali": "ali-secret-key",
        "admin": "admin-secret",
        "readonly_user": "readonly-key",
        "demo-user": "demo-key",
    }

    for user_id, api_key in api_keys.items():
        print(f"\n👤 Testing as user: {user_id}")
        print("-" * 30)

        try:
            client = TTSKitAPIClient(api_key=api_key)

            user_info = await client.get_current_user()
            print(f"✅ User ID: {user_info['user_id']}")
            print(f"✅ Permissions: {user_info['permissions']}")

            audio_data = await client.synthesize("Hello, world!", "en")
            print(f"✅ Synthesis successful: {len(audio_data)} bytes")

            try:
                api_keys_list = await client.list_api_keys()
                print(f"✅ Admin access: {len(api_keys_list)} API keys found")
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 403:
                    print("❌ Admin access denied (expected for non-admin)")
                else:
                    print(f"❌ Admin access failed: {e}")

        except Exception as e:
            print(f"❌ Failed: {e}")

    print("\n🎉 API Keys test completed!")


async def test_environment_config():
    """Demonstrates environment variable configuration for API keys and settings.
    
    Shows how to configure multiple API keys, authentication settings, and
    rate limits using environment variables or .env files.
    """

    print("\n🔧 Environment Configuration Example")
    print("=" * 50)

    env_example = {
        "TTSKIT_API_KEYS": json.dumps(
            {
                "ali": "ali-secret-key",
                "admin": "admin-secret",
                "readonly_user": "readonly-key",
                "demo-user": "demo-key",
            }
        ),
        "TTSKIT_ENABLE_AUTH": "true",
        "TTSKIT_API_RATE_LIMIT": "100",
    }

    print("Environment variables to set:")
    for key, value in env_example.items():
        print(f"export {key}='{value}'")

    print("\nOr create a .env file:")
    print('TTSKIT_API_KEYS={"ali": "ali-secret-key", "admin": "admin-secret"}')
    print("TTSKIT_ENABLE_AUTH=true")
    print("TTSKIT_API_RATE_LIMIT=100")


async def main():
    """Runs API key examples and configuration demonstrations.
    
    Executes multi-user API key testing and shows environment configuration
    options for TTSKit authentication and authorization setup.
    """
    await test_multiple_api_keys()
    await test_environment_config()


if __name__ == "__main__":
    asyncio.run(main())
