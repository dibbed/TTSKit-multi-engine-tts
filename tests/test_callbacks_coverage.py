"""Test coverage for ttskit/bot/callbacks.py specific functions.

Tests for functions with 0% coverage:
- CallbackRegistry.register_admin.admin_clear
- CallbackRegistry.dispatch_admin
- handle_audio_callback
- handle_callback_query
- handle_error_callback
- handle_text_callback
- handle_voice_callback
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ttskit.bot.callbacks import (
    CallbackRegistry,
    handle_audio_callback,
    handle_callback_query,
    handle_error_callback,
    handle_text_callback,
    handle_voice_callback,
)


class TestCallbackRegistryAdminCoverage:
    """Test CallbackRegistry admin functionality for coverage."""

    def test_register_admin_with_bot_instance(self):
        """Test register_admin with bot instance (admin_clear coverage)."""
        registry = CallbackRegistry()
        mock_bot = MagicMock()

        registry.register_admin(mock_bot)

        assert "admin_callback" in registry._admin_handlers
        assert "admin_" in registry._admin_handlers
        assert "admin_callback" in registry._handlers
        assert "admin_" in registry._handlers

    @pytest.mark.asyncio
    async def test_dispatch_admin_with_sudo_user(self):
        """Test dispatch_admin with sudo user (full coverage)."""
        registry = CallbackRegistry()

        admin_keys_handler = AsyncMock()
        admin_cache_handler = AsyncMock()

        registry._admin_handlers = {
            "admin:keys:": admin_keys_handler,
            "admin:cache:": admin_cache_handler,
        }

        mock_bot = MagicMock()
        mock_message = MagicMock()

        result = await registry.dispatch_admin(
            mock_bot, mock_message, "admin:keys:clear", is_sudo=True
        )

        assert result is True
        admin_keys_handler.assert_called_once_with(
            mock_bot, mock_message, "admin:keys:clear"
        )
        admin_cache_handler.assert_not_called()

    @pytest.mark.asyncio
    async def test_dispatch_admin_with_non_sudo_user(self):
        """Test dispatch_admin with non-sudo user."""
        registry = CallbackRegistry()

        admin_handler = AsyncMock()
        registry._admin_handlers = {"admin:test:": admin_handler}

        mock_bot = MagicMock()
        mock_message = MagicMock()

        result = await registry.dispatch_admin(
            mock_bot, mock_message, "admin:test:action", is_sudo=False
        )

        assert result is False
        admin_handler.assert_not_called()

    @pytest.mark.asyncio
    async def test_dispatch_admin_unknown_callback(self):
        """Test dispatch_admin with unknown callback data."""
        registry = CallbackRegistry()

        admin_handler = AsyncMock()
        registry._admin_handlers = {"admin:known:": admin_handler}

        mock_bot = MagicMock()
        mock_message = MagicMock()

        result = await registry.dispatch_admin(
            mock_bot, mock_message, "admin:unknown:action", is_sudo=True
        )

        assert result is False
        admin_handler.assert_not_called()

    @pytest.mark.asyncio
    async def test_dispatch_admin_multiple_handlers(self):
        """Test dispatch_admin with multiple matching handlers (first match wins)."""
        registry = CallbackRegistry()

        admin_keys_handler = AsyncMock()
        admin_cache_handler = AsyncMock()

        registry._admin_handlers = {
            "admin:keys:": admin_keys_handler,
            "admin:cache:": admin_cache_handler,
        }

        mock_bot = MagicMock()
        mock_message = MagicMock()

        result = await registry.dispatch_admin(
            mock_bot, mock_message, "admin:keys:list", is_sudo=True
        )

        assert result is True
        admin_keys_handler.assert_called_once_with(
            mock_bot, mock_message, "admin:keys:list"
        )
        admin_cache_handler.assert_not_called()


class TestStandaloneCallbackHandlers:
    """Test standalone callback handler functions for coverage."""

    @pytest.mark.asyncio
    async def test_handle_audio_callback(self):
        """Test handle_audio_callback function."""
        mock_bot = MagicMock()
        mock_message = MagicMock()
        mock_message.chat_id = 12345

        with patch("ttskit.bot.callbacks.CallbackRegistry") as mock_registry_class:
            mock_registry = MagicMock()
            mock_registry.dispatch = AsyncMock(return_value=True)
            mock_registry_class.return_value = mock_registry

            result = await handle_audio_callback(mock_bot, mock_message, "engine_gtts")

            assert result is True
            mock_registry.register_default.assert_called_once_with(mock_bot)
            mock_registry.dispatch.assert_called_once_with(
                mock_bot, mock_message, "engine_gtts"
            )

    @pytest.mark.asyncio
    async def test_handle_callback_query(self):
        """Test handle_callback_query function."""
        mock_bot = MagicMock()
        mock_message = MagicMock()
        mock_message.chat_id = 12345

        with patch("ttskit.bot.callbacks.CallbackRegistry") as mock_registry_class:
            mock_registry = MagicMock()
            mock_registry.dispatch = AsyncMock(return_value=False)
            mock_registry_class.return_value = mock_registry

            result = await handle_callback_query(
                mock_bot, mock_message, "settings_cache_on"
            )

            assert result is False
            mock_registry.register_default.assert_called_once_with(mock_bot)
            mock_registry.dispatch.assert_called_once_with(
                mock_bot, mock_message, "settings_cache_on"
            )

    @pytest.mark.asyncio
    async def test_handle_error_callback(self):
        """Test handle_error_callback function."""
        mock_bot = MagicMock()
        mock_bot.awaitable = MagicMock(return_value=AsyncMock())
        mock_message = MagicMock()
        mock_message.chat_id = 12345

        with patch("ttskit.bot.callbacks.t") as mock_t:
            mock_t.return_value = "Error: test_error"

            await handle_error_callback(mock_bot, mock_message, "test_error")

            mock_t.assert_called_once_with("error_prefix", error="test_error")
            mock_bot.awaitable.assert_called_once()
            mock_bot.awaitable.return_value.assert_called_once_with(
                mock_message.chat_id, "Error: test_error"
            )

    @pytest.mark.asyncio
    async def test_handle_text_callback(self):
        """Test handle_text_callback function."""
        mock_bot = MagicMock()
        mock_bot.awaitable = MagicMock(return_value=AsyncMock())
        mock_message = MagicMock()
        mock_message.chat_id = 12345

        with patch("ttskit.bot.callbacks.t") as mock_t:
            mock_t.return_value = "Text callback: test_data"

            await handle_text_callback(mock_bot, mock_message, "test_data")

            mock_t.assert_called_once_with("text_callback", data="test_data")
            mock_bot.awaitable.assert_called_once()
            mock_bot.awaitable.return_value.assert_called_once_with(
                mock_message.chat_id, "Text callback: test_data"
            )

    @pytest.mark.asyncio
    async def test_handle_voice_callback(self):
        """Test handle_voice_callback function."""
        mock_bot = MagicMock()
        mock_bot.awaitable = MagicMock(return_value=AsyncMock())
        mock_message = MagicMock()
        mock_message.chat_id = 12345

        with patch("ttskit.bot.callbacks.t") as mock_t:
            mock_t.return_value = "Voice callback: voice_data"

            await handle_voice_callback(mock_bot, mock_message, "voice_data")

            mock_t.assert_called_once_with("voice_callback", data="voice_data")
            mock_bot.awaitable.assert_called_once()
            mock_bot.awaitable.return_value.assert_called_once_with(
                mock_message.chat_id, "Voice callback: voice_data"
            )

    @pytest.mark.asyncio
    async def test_handle_error_callback_with_exception(self):
        """Test handle_error_callback with exception in awaitable."""
        mock_bot = MagicMock()
        mock_awaitable_result = AsyncMock(side_effect=Exception("Bot error"))
        mock_bot.awaitable = MagicMock(return_value=mock_awaitable_result)
        mock_message = MagicMock()
        mock_message.chat_id = 12345

        with patch("ttskit.bot.callbacks.t") as mock_t:
            mock_t.return_value = "Error: test_error"

            with pytest.raises(Exception, match="Bot error"):
                await handle_error_callback(mock_bot, mock_message, "test_error")

            mock_t.assert_called_once_with("error_prefix", error="test_error")

    @pytest.mark.asyncio
    async def test_handle_text_callback_with_exception(self):
        """Test handle_text_callback with exception in awaitable."""
        mock_bot = MagicMock()
        mock_awaitable_result = AsyncMock(side_effect=Exception("Bot error"))
        mock_bot.awaitable = MagicMock(return_value=mock_awaitable_result)
        mock_message = MagicMock()
        mock_message.chat_id = 12345

        with patch("ttskit.bot.callbacks.t") as mock_t:
            mock_t.return_value = "Text callback: test_data"

            with pytest.raises(Exception, match="Bot error"):
                await handle_text_callback(mock_bot, mock_message, "test_data")

            mock_t.assert_called_once_with("text_callback", data="test_data")

    @pytest.mark.asyncio
    async def test_handle_voice_callback_with_exception(self):
        """Test handle_voice_callback with exception in awaitable."""
        mock_bot = MagicMock()
        mock_awaitable_result = AsyncMock(side_effect=Exception("Bot error"))
        mock_bot.awaitable = MagicMock(return_value=mock_awaitable_result)
        mock_message = MagicMock()
        mock_message.chat_id = 12345

        with patch("ttskit.bot.callbacks.t") as mock_t:
            mock_t.return_value = "Voice callback: voice_data"

            with pytest.raises(Exception, match="Bot error"):
                await handle_voice_callback(mock_bot, mock_message, "voice_data")

            mock_t.assert_called_once_with("voice_callback", data="voice_data")


class TestCallbackRegistryEdgeCases:
    """Test edge cases for better coverage."""

    @pytest.mark.asyncio
    async def test_dispatch_admin_empty_handlers(self):
        """Test dispatch_admin with empty handlers."""
        registry = CallbackRegistry()
        registry._admin_handlers = {}

        mock_bot = MagicMock()
        mock_message = MagicMock()

        result = await registry.dispatch_admin(
            mock_bot, mock_message, "admin:test:action", is_sudo=True
        )

        assert result is False

    def test_register_admin_with_string_prefix_and_handler(self):
        """Test register_admin with string prefix and handler."""
        registry = CallbackRegistry()

        async def test_handler(bot, message, data):
            return "test_result"

        registry.register_admin("admin:test:", test_handler)

        assert "admin:test:" in registry._admin_handlers
        assert registry._admin_handlers["admin:test:"] == test_handler

    def test_register_admin_with_non_string_prefix(self):
        """Test register_admin with non-string prefix (should not register)."""
        registry = CallbackRegistry()

        async def test_handler(bot, message, data):
            return "test_result"

        registry.register_admin(123, test_handler)

        assert len(registry._admin_handlers) == 0

    def test_register_admin_with_none_handler(self):
        """Test register_admin with None handler."""
        registry = CallbackRegistry()

        registry.register_admin("admin:test:", None)

        assert len(registry._admin_handlers) == 0
