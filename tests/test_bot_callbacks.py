"""Tests for Bot Callbacks."""

from unittest.mock import AsyncMock, Mock

import pytest

from ttskit.bot.callbacks import CallbackRegistry
from ttskit.telegram.base import MessageType, TelegramMessage, TelegramUser


class TestCallbackRegistry:
    """Test cases for CallbackRegistry."""

    @pytest.fixture
    def callback_registry(self):
        """Create CallbackRegistry instance for testing."""
        return CallbackRegistry()

    @pytest.fixture
    def mock_bot(self):
        """Create mock bot for testing."""
        bot = Mock()
        bot.sudo_users = {"12345"}
        bot.awaitable = Mock(return_value=AsyncMock())
        return bot

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
            text="callback_data",
            message_type=MessageType.TEXT,
        )

    def test_initialization(self, callback_registry):
        """Test CallbackRegistry initialization."""
        assert callback_registry is not None
        assert isinstance(callback_registry.callbacks, dict)

    def test_register_callback(self, callback_registry):
        """Test registering a callback."""

        async def test_callback(bot, message, callback_data):
            return "test_response"

        callback_registry.register_callback("test", test_callback)

        assert "test" in callback_registry.callbacks
        assert callback_registry.callbacks["test"] == test_callback

    def test_register_callback_with_admin_flag(self, callback_registry):
        """Test registering an admin callback."""

        async def admin_callback(bot, message, callback_data):
            return "admin_response"

        callback_registry.register_callback("admin", admin_callback, admin_only=True)

        assert "admin" in callback_registry.callbacks
        assert callback_registry.callbacks["admin"] == admin_callback
        assert "admin" in callback_registry.admin_callbacks

    def test_dispatch_callback_success(self, callback_registry, mock_bot, mock_message):
        """Test successful callback dispatch."""

        async def test_callback(bot, message, callback_data):
            return "test_response"

        callback_registry.register_callback("callback_data", test_callback)

        import asyncio

        async def run_test():
            result = await callback_registry.dispatch(
                mock_bot, mock_message, "callback_data"
            )
            assert result is True

        asyncio.run(run_test())

    def test_dispatch_callback_not_found(
        self, callback_registry, mock_bot, mock_message
    ):
        """Test callback dispatch when callback not found."""
        import asyncio

        async def run_test():
            result = await callback_registry.dispatch(
                mock_bot, mock_message, "unknown_callback"
            )
            assert result is False

        asyncio.run(run_test())

    def test_dispatch_admin_callback_sudo_user(
        self, callback_registry, mock_bot, mock_message
    ):
        """Test dispatching admin callback for sudo user."""

        async def admin_callback(bot, message, callback_data):
            return "admin_response"

        callback_registry.register_callback(
            "admin_callback", admin_callback, admin_only=True
        )

        import asyncio

        async def run_test():
            result = await callback_registry.dispatch(
                mock_bot, mock_message, "admin_callback"
            )
            assert result is True

        asyncio.run(run_test())

    def test_dispatch_admin_callback_non_sudo_user(
        self, callback_registry, mock_bot, mock_message
    ):
        """Test dispatching admin callback for non-sudo user."""

        async def admin_callback(bot, message, callback_data):
            return "admin_response"

        callback_registry.register_callback(
            "admin_callback", admin_callback, admin_only=True
        )

        mock_message.user.id = 99999
        mock_bot.sudo_users = {"12345"}

        mock_bot.is_sudo = Mock(return_value=False)

        import asyncio

        async def run_test():
            result = await callback_registry.dispatch(
                mock_bot, mock_message, "admin_callback"
            )
            assert result is False

        asyncio.run(run_test())

    def test_register_default_callbacks(self, callback_registry, mock_bot):
        """Test registering default callbacks."""
        callback_registry.register_default(mock_bot)

        assert "engine_" in str(callback_registry.callbacks.keys())
        assert "settings_" in str(callback_registry.callbacks.keys())

    def test_register_admin_callbacks(self, callback_registry, mock_bot):
        """Test registering admin callbacks."""
        callback_registry.register_admin(mock_bot)

        assert "admin_" in str(callback_registry.callbacks.keys())

    def test_engine_selection_callback(self, callback_registry, mock_bot, mock_message):
        """Test engine selection callback."""
        callback_registry.register_default(mock_bot)

        import asyncio

        async def run_test():
            result = await callback_registry.dispatch(
                mock_bot, mock_message, "engine_gtts"
            )
            assert result is True

        asyncio.run(run_test())

    def test_settings_callback(self, callback_registry, mock_bot, mock_message):
        """Test settings callback."""
        callback_registry.register_default(mock_bot)

        import asyncio

        async def run_test():
            result = await callback_registry.dispatch(
                mock_bot, mock_message, "settings_cache_on"
            )
            assert result is True

        asyncio.run(run_test())

    def test_admin_callback(self, callback_registry, mock_bot, mock_message):
        """Test admin callback."""
        callback_registry.register_admin(mock_bot)

        import asyncio

        async def run_test():
            result = await callback_registry.dispatch(
                mock_bot, mock_message, "admin_stats"
            )
            assert result is True

        asyncio.run(run_test())

    def test_callback_with_parameters(self, callback_registry, mock_bot, mock_message):
        """Test callback with parameters."""

        async def test_callback(bot, message, callback_data):
            return f"Callback: {callback_data}"

        callback_registry.register_callback("test", test_callback)

        import asyncio

        async def run_test():
            result = await callback_registry.dispatch(
                mock_bot, mock_message, "test:param1:param2"
            )
            assert result is True

        asyncio.run(run_test())

    def test_callback_case_sensitive(self, callback_registry, mock_bot, mock_message):
        """Test callback case sensitive matching."""

        async def test_callback(bot, message, callback_data):
            return "test_response"

        callback_registry.register_callback("test", test_callback)

        import asyncio

        async def run_test():
            result = await callback_registry.dispatch(mock_bot, mock_message, "TEST")
            assert result is False

        asyncio.run(run_test())

    def test_callback_with_whitespace(self, callback_registry, mock_bot, mock_message):
        """Test callback with whitespace."""

        async def test_callback(bot, message, callback_data):
            return "test_response"

        callback_registry.register_callback("test", test_callback)

        import asyncio

        async def run_test():
            result = await callback_registry.dispatch(
                mock_bot, mock_message, "  test  "
            )
            assert result is True

        asyncio.run(run_test())

    def test_callback_with_empty_data(self, callback_registry, mock_bot, mock_message):
        """Test callback with empty data."""

        async def test_callback(bot, message, callback_data):
            return "test_response"

        callback_registry.register_callback("", test_callback)

        import asyncio

        async def run_test():
            result = await callback_registry.dispatch(mock_bot, mock_message, "")
            assert result is True

        asyncio.run(run_test())

    def test_callback_with_none_data(self, callback_registry, mock_bot, mock_message):
        """Test callback with None data."""
        import asyncio

        async def run_test():
            result = await callback_registry.dispatch(mock_bot, mock_message, None)
            assert result is False

        asyncio.run(run_test())

    def test_callback_with_special_characters(
        self, callback_registry, mock_bot, mock_message
    ):
        """Test callback with special characters."""

        async def test_callback(bot, message, callback_data):
            return "test_response"

        callback_registry.register_callback("test:with:colons", test_callback)

        import asyncio

        async def run_test():
            result = await callback_registry.dispatch(
                mock_bot, mock_message, "test:with:colons"
            )
            assert result is True

        asyncio.run(run_test())

    def test_callback_with_unicode(self, callback_registry, mock_bot, mock_message):
        """Test callback with unicode characters."""

        async def test_callback(bot, message, callback_data):
            return "test_response"

        callback_registry.register_callback("تست", test_callback)

        import asyncio

        async def run_test():
            result = await callback_registry.dispatch(mock_bot, mock_message, "تست")
            assert result is True

        asyncio.run(run_test())

    def test_callback_with_long_data(self, callback_registry, mock_bot, mock_message):
        """Test callback with long data."""

        async def test_callback(bot, message, callback_data):
            return "test_response"

        long_data = "a" * 1000
        callback_registry.register_callback(long_data, test_callback)

        import asyncio

        async def run_test():
            result = await callback_registry.dispatch(mock_bot, mock_message, long_data)
            assert result is True

        asyncio.run(run_test())

    def test_callback_with_numeric_data(
        self, callback_registry, mock_bot, mock_message
    ):
        """Test callback with numeric data."""

        async def test_callback(bot, message, callback_data):
            return "test_response"

        callback_registry.register_callback("123", test_callback)

        import asyncio

        async def run_test():
            result = await callback_registry.dispatch(mock_bot, mock_message, "123")
            assert result is True

        asyncio.run(run_test())

    def test_callback_with_mixed_data(self, callback_registry, mock_bot, mock_message):
        """Test callback with mixed data types."""

        async def test_callback(bot, message, callback_data):
            return "test_response"

        callback_registry.register_callback("test123:param:456", test_callback)

        import asyncio

        async def run_test():
            result = await callback_registry.dispatch(
                mock_bot, mock_message, "test123:param:456"
            )
            assert result is True

        asyncio.run(run_test())
