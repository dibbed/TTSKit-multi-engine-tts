"""
Test cases for integration functionality.

This module tests the UnifiedTTSBot integration functionality
that was migrated from integration.py to unified_bot.py.
"""

from unittest.mock import AsyncMock, Mock

import pytest

from ttskit.bot.unified_bot import UnifiedTTSBot


class TestUnifiedTTSBotIntegration:
    """Test cases for UnifiedTTSBot integration functionality."""

    @pytest.fixture
    def mock_bot_token(self):
        """Create mock bot token for testing."""
        return "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    @pytest.fixture
    def mock_admin_ids(self):
        """Create mock admin IDs for testing."""
        return [123456789, 987654321]

    def test_unified_bot_initialization(self, mock_bot_token):
        """Test UnifiedTTSBot initialization."""
        bot = UnifiedTTSBot(
            bot_token=mock_bot_token,
            adapter_type="aiogram",
            cache_enabled=True,
            audio_processing=True,
        )

        assert isinstance(bot, UnifiedTTSBot)
        assert bot.bot_token == mock_bot_token
        assert bot.adapter_type == "aiogram"
        assert bot.cache_enabled is True
        assert bot.audio_processing is True

    def test_unified_bot_with_admin_ids(self, mock_bot_token, mock_admin_ids):
        """Test UnifiedTTSBot with admin IDs."""
        bot = UnifiedTTSBot(
            bot_token=mock_bot_token,
            adapter_type="aiogram",
            cache_enabled=True,
            audio_processing=True,
        )

        for admin_id in mock_admin_ids:
            bot.sudo_users.add(str(admin_id))

        assert str(mock_admin_ids[0]) in bot.sudo_users
        assert str(mock_admin_ids[1]) in bot.sudo_users

    def test_unified_bot_sudo_check(self, mock_bot_token, mock_admin_ids):
        """Test UnifiedTTSBot sudo user check."""
        bot = UnifiedTTSBot(
            bot_token=mock_bot_token,
            adapter_type="aiogram",
            cache_enabled=True,
            audio_processing=True,
        )

        for admin_id in mock_admin_ids:
            bot.sudo_users.add(str(admin_id))

        assert bot.is_sudo(mock_admin_ids[0]) is True
        assert bot.is_sudo(mock_admin_ids[1]) is True
        assert bot.is_sudo(999999999) is False

    @pytest.mark.asyncio
    async def test_unified_bot_start(self, mock_bot_token):
        """Test UnifiedTTSBot start method."""
        bot = UnifiedTTSBot(
            bot_token=mock_bot_token,
            adapter_type="aiogram",
            cache_enabled=True,
            audio_processing=True,
        )

        bot.adapter = Mock()
        bot.adapter.start = AsyncMock()
        bot.smart_router = Mock()

        await bot.start()
        bot.adapter.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_unified_bot_stop(self, mock_bot_token):
        """Test UnifiedTTSBot stop method."""
        bot = UnifiedTTSBot(
            bot_token=mock_bot_token,
            adapter_type="aiogram",
            cache_enabled=True,
            audio_processing=True,
        )

        bot.adapter = Mock()
        bot.adapter.stop = AsyncMock()

        await bot.stop()
        bot.adapter.stop.assert_called_once()

    def test_unified_bot_add_admin(self, mock_bot_token):
        """Test UnifiedTTSBot add admin functionality."""
        bot = UnifiedTTSBot(
            bot_token=mock_bot_token,
            adapter_type="aiogram",
            cache_enabled=True,
            audio_processing=True,
        )

        admin_id = 123456789
        bot.sudo_users.add(str(admin_id))

        assert str(admin_id) in bot.sudo_users
        assert bot.is_sudo(admin_id) is True

    def test_unified_bot_remove_admin(self, mock_bot_token):
        """Test UnifiedTTSBot remove admin functionality."""
        bot = UnifiedTTSBot(
            bot_token=mock_bot_token,
            adapter_type="aiogram",
            cache_enabled=True,
            audio_processing=True,
        )

        admin_id = 123456789
        bot.sudo_users.add(str(admin_id))
        assert str(admin_id) in bot.sudo_users

        bot.sudo_users.discard(str(admin_id))
        assert str(admin_id) not in bot.sudo_users
        assert bot.is_sudo(admin_id) is False

    def test_unified_bot_get_admin_ids(self, mock_bot_token, mock_admin_ids):
        """Test UnifiedTTSBot get admin IDs functionality."""
        bot = UnifiedTTSBot(
            bot_token=mock_bot_token,
            adapter_type="aiogram",
            cache_enabled=True,
            audio_processing=True,
        )

        for admin_id in mock_admin_ids:
            bot.sudo_users.add(str(admin_id))

        admin_ids = list(bot.sudo_users)
        assert str(mock_admin_ids[0]) in admin_ids
        assert str(mock_admin_ids[1]) in admin_ids

    def test_unified_bot_with_different_adapters(self, mock_bot_token):
        """Test UnifiedTTSBot with different adapter types."""
        bot_aiogram = UnifiedTTSBot(
            bot_token=mock_bot_token,
            adapter_type="aiogram",
            cache_enabled=True,
            audio_processing=True,
        )
        assert bot_aiogram.adapter_type == "aiogram"

        bot_telebot = UnifiedTTSBot(
            bot_token=mock_bot_token,
            adapter_type="telebot",
            cache_enabled=True,
            audio_processing=True,
        )
        assert bot_telebot.adapter_type == "telebot"

        bot_pyrogram = UnifiedTTSBot(
            bot_token=mock_bot_token,
            adapter_type="pyrogram",
            cache_enabled=True,
            audio_processing=True,
        )
        assert bot_pyrogram.adapter_type == "pyrogram"

        bot_telethon = UnifiedTTSBot(
            bot_token=mock_bot_token,
            adapter_type="telethon",
            cache_enabled=True,
            audio_processing=True,
        )
        assert bot_telethon.adapter_type == "telethon"

    def test_unified_bot_with_cache_options(self, mock_bot_token):
        """Test UnifiedTTSBot with different cache options."""
        bot_with_cache = UnifiedTTSBot(
            bot_token=mock_bot_token,
            adapter_type="aiogram",
            cache_enabled=True,
            audio_processing=True,
        )
        assert bot_with_cache.cache_enabled is True

        bot_without_cache = UnifiedTTSBot(
            bot_token=mock_bot_token,
            adapter_type="aiogram",
            cache_enabled=False,
            audio_processing=True,
        )
        assert bot_without_cache.cache_enabled is False

    def test_unified_bot_with_audio_processing_options(self, mock_bot_token):
        """Test UnifiedTTSBot with different audio processing options."""
        bot_with_audio = UnifiedTTSBot(
            bot_token=mock_bot_token,
            adapter_type="aiogram",
            cache_enabled=True,
            audio_processing=True,
        )
        assert bot_with_audio.audio_processing is True

        bot_without_audio = UnifiedTTSBot(
            bot_token=mock_bot_token,
            adapter_type="aiogram",
            cache_enabled=True,
            audio_processing=False,
        )
        assert bot_without_audio.audio_processing is False

    @pytest.mark.asyncio
    async def test_unified_bot_integration_workflow(
        self, mock_bot_token, mock_admin_ids
    ):
        """Test complete UnifiedTTSBot integration workflow."""
        bot = UnifiedTTSBot(
            bot_token=mock_bot_token,
            adapter_type="aiogram",
            cache_enabled=True,
            audio_processing=True,
        )

        for admin_id in mock_admin_ids:
            bot.sudo_users.add(str(admin_id))

        bot.adapter = Mock()
        bot.adapter.start = AsyncMock()
        bot.adapter.stop = AsyncMock()
        bot.smart_router = Mock()

        await bot.start()
        bot.adapter.start.assert_called_once()

        assert bot.is_sudo(mock_admin_ids[0]) is True
        assert bot.is_sudo(mock_admin_ids[1]) is True

        await bot.stop()
        bot.adapter.stop.assert_called_once()
