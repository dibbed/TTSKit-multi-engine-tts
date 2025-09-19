"""
Example: TTSKit Telegram Bot with Admin Features

This example demonstrates how to use the new admin panel and performance
optimization features in TTSKit.
"""

import asyncio
import os

from ttskit.bot.unified_bot import UnifiedTTSBot
from ttskit.config import settings


async def main():
    """Starts a TTSKit Telegram bot with administrative features enabled.
    
    Configures bot token, sets up admin users, displays available admin commands,
    and runs the bot with full admin panel functionality including API key management,
    system monitoring, and performance analysis tools.
    """

    bot_token = os.getenv("BOT_TOKEN") or getattr(settings, "bot_token", None)

    if not bot_token:
        print("❌ BOT_TOKEN not found in environment variables or settings!")
        print("Please set BOT_TOKEN environment variable.")
        return

    admin_ids = [
        123456789,
        987654321,
    ]

    print("🚀 Starting TTSKit Bot with Admin Features...")
    print(f"📊 Admin users: {admin_ids}")
    print("🛠️ Available admin commands:")
    print("  /admin - Main admin panel")
    print("  /create_key - Create API key")
    print("  /list_keys - List API keys")
    print("  /delete_key - Delete API key")
    print("  /stats - System statistics")
    print("  /health - Health check")
    print("  /performance - Performance analysis")
    print("  /monitor - Real-time monitoring")
    print("  /clear_cache - Clear cache")
    print("  /debug - Debug information")
    print("  /test_engines - Test all engines")

    try:
        bot = UnifiedTTSBot(
            bot_token=bot_token,
            adapter_type="aiogram",
            cache_enabled=True,
            audio_processing=True,
        )

        for admin_id in admin_ids:
            bot.sudo_users.add(str(admin_id))

        await bot.start()

        try:
            while bot.is_running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("Bot stopped by user")
        finally:
            await bot.stop()

    except Exception as e:
        print(f"❌ Error starting bot: {e}")


if __name__ == "__main__":
    asyncio.run(main())
