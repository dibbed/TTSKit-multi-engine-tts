"""Tests for Unified TTS Bot callback coverage.

This module tests the callback-related methods that are currently not covered:
- _handle_callback
- _handle_error
- is_sudo
- _handle_engine_selection
- _handle_settings_callback
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from ttskit.bot.unified_bot import UnifiedTTSBot
from ttskit.telegram.base import MessageType, TelegramMessage, TelegramUser


class TestUnifiedTTSBotCallbackCoverage:
    """Test UnifiedTTSBot callback coverage methods."""

    @pytest.fixture
    def bot(self):
        """Create bot instance for testing."""
        return UnifiedTTSBot(
            bot_token="123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi",
            adapter_type="aiogram",
            cache_enabled=False,
            audio_processing=False,
        )

    @pytest.fixture
    def mock_message(self):
        """Create mock message for testing."""
        user = TelegramUser(
            id=12345, username="testuser", first_name="Test", last_name="User"
        )

        return TelegramMessage(
            id=1,
            chat_id=12345,
            user=user,
            text="engine_edge",
            message_type=MessageType.TEXT,
        )

    @pytest.fixture
    def mock_callback_message(self):
        """Create mock callback message for testing."""
        user = TelegramUser(
            id=12345, username="testuser", first_name="Test", last_name="User"
        )

        return TelegramMessage(
            id=1,
            chat_id=12345,
            user=user,
            text="engine_edge:fa",
            message_type=MessageType.TEXT,
        )

    @pytest.mark.asyncio
    async def test_handle_callback_engine_selection(self, bot, mock_callback_message):
        """Test _handle_callback with engine selection data."""
        with patch.object(bot, "_cb_registry") as mock_registry:
            with patch.object(bot, "_handle_error") as mock_error_handler:
                mock_registry.dispatch = AsyncMock(return_value=True)

                await bot._handle_callback(mock_callback_message)

                mock_registry.dispatch.assert_called_once_with(
                    bot, mock_callback_message, "engine_edge:fa"
                )
                mock_error_handler.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_callback_settings(self, bot):
        """Test _handle_callback with settings data."""
        user = TelegramUser(id=12345, username="testuser")
        settings_message = TelegramMessage(
            id=1,
            chat_id=12345,
            user=user,
            text="settings_cache_on",
            message_type=MessageType.TEXT,
        )

        with patch.object(bot, "_cb_registry") as mock_registry:
            with patch.object(bot, "_handle_error") as mock_error_handler:
                mock_registry.dispatch = AsyncMock(return_value=True)

                await bot._handle_callback(settings_message)

                mock_registry.dispatch.assert_called_once_with(
                    bot, settings_message, "settings_cache_on"
                )
                mock_error_handler.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_callback_admin(self, bot):
        """Test _handle_callback with admin data."""
        user = TelegramUser(id=12345, username="testuser")
        admin_message = TelegramMessage(
            id=1,
            chat_id=12345,
            user=user,
            text="admin_stats",
            message_type=MessageType.TEXT,
        )

        with patch.object(bot, "_cb_registry") as mock_registry:
            with patch.object(bot, "_handle_error") as mock_error_handler:
                mock_registry.dispatch = AsyncMock(return_value=True)

                await bot._handle_callback(admin_message)

                mock_registry.dispatch.assert_called_once_with(
                    bot, admin_message, "admin_stats"
                )
                mock_error_handler.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_callback_unknown_data(self, bot):
        """Test _handle_callback with unknown data."""
        user = TelegramUser(id=12345, username="testuser")
        unknown_message = TelegramMessage(
            id=1,
            chat_id=12345,
            user=user,
            text="unknown_callback_data",
            message_type=MessageType.TEXT,
        )

        with patch.object(bot, "_cb_registry") as mock_registry:
            with patch("ttskit.bot.unified_bot.logger") as mock_logger:
                mock_registry.dispatch = AsyncMock(return_value=False)

                await bot._handle_callback(unknown_message)

                mock_registry.dispatch.assert_called_once_with(
                    bot, unknown_message, "unknown_callback_data"
                )
                mock_logger.debug.assert_called_once_with(
                    "Unknown callback: unknown_callback_data"
                )

    @pytest.mark.asyncio
    async def test_handle_callback_exception(self, bot, mock_callback_message):
        """Test _handle_callback with exception."""
        with patch.object(bot, "_cb_registry") as mock_registry:
            with patch.object(bot, "_handle_error") as mock_error_handler:
                mock_registry.dispatch = AsyncMock(side_effect=Exception("Test error"))

                await bot._handle_callback(mock_callback_message)

                mock_error_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_error_with_context(self, bot):
        """Test _handle_error with message context."""
        user = TelegramUser(id=12345, username="testuser")
        context_message = TelegramMessage(
            id=1,
            chat_id=12345,
            user=user,
            text="test",
            message_type=MessageType.TEXT,
        )

        test_error = Exception("Test error")

        with patch("ttskit.bot.unified_bot.logger") as mock_logger:
            with patch.object(bot, "_send_error_message") as mock_send_error:
                await bot._handle_error(test_error, context_message)

                mock_logger.error.assert_called_once_with("Bot error: Test error")

                assert bot.stats["engine_failures"] == 1

                mock_send_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_error_without_context(self, bot):
        """Test _handle_error without context."""
        test_error = Exception("Test error")

        with patch("ttskit.bot.unified_bot.logger") as mock_logger:
            with patch.object(bot, "_send_error_message") as mock_send_error:
                await bot._handle_error(test_error, None)

                mock_logger.error.assert_called_once_with("Bot error: Test error")

                assert bot.stats["engine_failures"] == 1

                mock_send_error.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_error_with_non_message_context(self, bot):
        """Test _handle_error with context that doesn't have chat_id."""
        test_error = Exception("Test error")
        context_without_chat_id = {"some": "data"}

        with patch("ttskit.bot.unified_bot.logger") as mock_logger:
            with patch.object(bot, "_send_error_message") as mock_send_error:
                await bot._handle_error(test_error, context_without_chat_id)

                mock_logger.error.assert_called_once_with("Bot error: Test error")

                assert bot.stats["engine_failures"] == 1

                mock_send_error.assert_not_called()

    def test_is_sudo_with_valid_user_id(self, bot):
        """Test is_sudo with valid user ID in sudo list."""
        bot.sudo_users.add("12345")

        assert bot.is_sudo("12345") is True

        assert bot.is_sudo(12345) is True

    def test_is_sudo_with_invalid_user_id(self, bot):
        """Test is_sudo with user ID not in sudo list."""
        assert bot.is_sudo("99999") is False

        assert bot.is_sudo(99999) is False

    def test_is_sudo_with_invalid_input(self, bot):
        """Test is_sudo with invalid input."""
        assert bot.is_sudo(None) is False

        class InvalidUser:
            def __str__(self):
                raise Exception("Cannot convert to string")

        assert bot.is_sudo(InvalidUser()) is False

    @pytest.mark.asyncio
    async def test_handle_engine_selection_valid_engine(
        self, bot, mock_callback_message
    ):
        """Test _handle_engine_selection with valid engine."""
        with patch("ttskit.engines.registry.registry") as mock_registry:
            with patch.object(bot, "adapter") as mock_adapter:
                mock_registry.get_policy.return_value = ["gtts", "edge", "piper"]
                mock_registry.get_available_engines.return_value = [
                    "gtts",
                    "edge",
                    "piper",
                ]

                mock_adapter.send_message = AsyncMock(return_value=Mock())

                bot.awaitable = lambda func: func

                await bot._handle_engine_selection(
                    mock_callback_message, "engine_edge:fa"
                )

                mock_registry.set_policy.assert_called()

                mock_adapter.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_engine_selection_invalid_engine_token(
        self, bot, mock_callback_message
    ):
        """Test _handle_engine_selection with invalid engine token."""
        with patch("ttskit.engines.registry.registry") as mock_registry:
            with patch.object(bot, "adapter") as mock_adapter:
                mock_adapter.send_message = AsyncMock(return_value=Mock())

                bot.awaitable = lambda func: func

                await bot._handle_engine_selection(
                    mock_callback_message, "invalid_token:fa"
                )

                mock_registry.set_policy.assert_not_called()

                mock_adapter.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_engine_selection_exception(self, bot, mock_callback_message):
        """Test _handle_engine_selection with exception."""
        with patch("ttskit.engines.registry.registry") as mock_registry:
            with patch.object(bot, "adapter") as mock_adapter:
                mock_registry.get_policy.side_effect = Exception("Registry error")

                mock_adapter.send_message = AsyncMock(return_value=Mock())

                bot.awaitable = lambda func: func

                await bot._handle_engine_selection(
                    mock_callback_message, "engine_edge:fa"
                )

                mock_adapter.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_engine_selection_without_language(
        self, bot, mock_callback_message
    ):
        """Test _handle_engine_selection without specific language."""
        with patch("ttskit.engines.registry.registry") as mock_registry:
            with patch.object(bot, "adapter") as mock_adapter:
                mock_registry.get_policy.return_value = ["gtts", "edge", "piper"]
                mock_registry.get_available_engines.return_value = [
                    "gtts",
                    "edge",
                    "piper",
                ]

                mock_adapter.send_message = AsyncMock(return_value=Mock())

                bot.awaitable = lambda func: func

                await bot._handle_engine_selection(mock_callback_message, "engine_edge")

                assert mock_registry.set_policy.call_count == 3

                mock_adapter.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_settings_callback_cache_on(self, bot, mock_callback_message):
        """Test _handle_settings_callback with cache on."""
        with patch.object(bot, "adapter") as mock_adapter:
            mock_adapter.send_message = AsyncMock(return_value=Mock())

            bot.awaitable = lambda func: func

            await bot._handle_settings_callback(
                mock_callback_message, "settings_cache_on"
            )

            assert bot.cache_enabled is True

            mock_adapter.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_settings_callback_cache_off(self, bot, mock_callback_message):
        """Test _handle_settings_callback with cache off."""
        bot.cache_enabled = True

        with patch.object(bot, "adapter") as mock_adapter:
            mock_adapter.send_message = AsyncMock(return_value=Mock())

            bot.awaitable = lambda func: func

            await bot._handle_settings_callback(
                mock_callback_message, "settings_cache_off"
            )

            assert bot.cache_enabled is False

            mock_adapter.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_settings_callback_audio_on(self, bot, mock_callback_message):
        """Test _handle_settings_callback with audio processing on."""
        with patch.object(bot, "adapter") as mock_adapter:
            mock_adapter.send_message = AsyncMock(return_value=Mock())

            bot.awaitable = lambda func: func

            await bot._handle_settings_callback(
                mock_callback_message, "settings_audio_on"
            )

            assert bot.audio_processing is True

            mock_adapter.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_settings_callback_audio_off(self, bot, mock_callback_message):
        """Test _handle_settings_callback with audio processing off."""
        bot.audio_processing = True

        with patch.object(bot, "adapter") as mock_adapter:
            mock_adapter.send_message = AsyncMock(return_value=Mock())

            bot.awaitable = lambda func: func

            await bot._handle_settings_callback(
                mock_callback_message, "settings_audio_off"
            )

            assert bot.audio_processing is False

            mock_adapter.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_settings_callback_unknown_setting(
        self, bot, mock_callback_message
    ):
        """Test _handle_settings_callback with unknown setting."""
        with patch.object(bot, "adapter") as mock_adapter:
            mock_adapter.send_message = AsyncMock(return_value=Mock())

            bot.awaitable = lambda func: func

            await bot._handle_settings_callback(
                mock_callback_message, "unknown_setting"
            )

            mock_adapter.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_settings_callback_exception(self, bot, mock_callback_message):
        """Test _handle_settings_callback with exception."""
        with patch.object(bot, "adapter") as mock_adapter:
            mock_adapter.send_message = AsyncMock(side_effect=Exception("Send error"))

            bot.awaitable = lambda func: func

            try:
                await bot._handle_settings_callback(
                    mock_callback_message, "settings_cache_on"
                )
            except Exception:
                pass

            assert (
                mock_adapter.send_message.call_count == 2
            )

    def test_sudo_users_initialization(self, bot):
        """Test sudo users initialization from settings."""
        assert isinstance(bot.sudo_users, set)

        bot.sudo_users.add("12345")
        assert "12345" in bot.sudo_users

        bot.sudo_users.remove("12345")
        assert "12345" not in bot.sudo_users

    @pytest.mark.asyncio
    async def test_handle_callback_registry_dispatch_called_with_correct_params(
        self, bot, mock_callback_message
    ):
        """Test that callback registry dispatch is called with correct parameters."""
        with patch.object(bot, "_cb_registry") as mock_registry:
            mock_registry.dispatch = AsyncMock(return_value=True)

            await bot._handle_callback(mock_callback_message)

            mock_registry.dispatch.assert_called_once_with(
                bot, mock_callback_message, "engine_edge:fa"
            )

    @pytest.mark.asyncio
    async def test_handle_error_stats_increment(self, bot):
        """Test that _handle_error increments engine_failures stats."""
        initial_failures = bot.stats["engine_failures"]
        test_error = Exception("Test error")

        await bot._handle_error(test_error, None)

        assert bot.stats["engine_failures"] == initial_failures + 1

    def test_is_sudo_string_conversion_edge_cases(self, bot):
        """Test is_sudo with edge cases for string conversion."""
        assert bot.is_sudo("") is False

        bot.sudo_users.add("  12345  ")
        assert bot.is_sudo("12345") is False

        bot.sudo_users.add("12345")
        assert bot.is_sudo("12345") is True
