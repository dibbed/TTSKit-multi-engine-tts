"""
Extended test cases for admin panel functionality.

This module provides extended tests for the CallbackRegistry and admin panel functionality.
"""

from unittest.mock import Mock

import pytest

from ttskit.bot.callbacks import CallbackRegistry


class TestCallbackRegistryExtended:
    """Extended tests for CallbackRegistry class."""

    def test_callback_registry_initialization(self):
        """Test CallbackRegistry initialization."""
        registry = CallbackRegistry()
        assert isinstance(registry, CallbackRegistry)
        assert hasattr(registry, "_handlers")
        assert hasattr(registry, "_admin_handlers")

    def test_register_callback(self):
        """Test callback registration."""
        registry = CallbackRegistry()

        async def test_handler(bot, message, data):
            return "test"

        registry.register_callback("test_", test_handler)
        assert "test_" in registry._handlers
        assert registry._handlers["test_"] == test_handler

    def test_register_admin_callback(self):
        """Test admin callback registration."""
        registry = CallbackRegistry()

        async def admin_handler(bot, message, data):
            return "admin"

        registry.register_callback("admin_", admin_handler, admin_only=True)
        assert "admin_" in registry._admin_handlers
        assert registry._admin_handlers["admin_"] == admin_handler


class TestCallbackRegistryIntegrationExtended:
    """Extended tests for CallbackRegistry integration with bot."""

    @pytest.fixture
    def mock_bot(self):
        """Create mock bot for testing."""
        bot = Mock()
        bot.is_sudo = Mock(return_value=True)
        bot.sudo_users = {"123456789"}
        bot.awaitable = Mock(return_value=lambda func: func)
        bot.adapter = Mock()
        bot.adapter.send_message = Mock()
        return bot

    @pytest.fixture
    def callback_registry(self):
        """Create CallbackRegistry instance for testing."""
        return CallbackRegistry()

    @pytest.mark.asyncio
    async def test_dispatch_callback(self, callback_registry, mock_bot):
        """Test callback dispatch."""

        async def test_handler(bot, message, data):
            return "test_result"

        callback_registry.register_callback("test_", test_handler)

        message = Mock()
        message.user = Mock()
        message.user.id = 123456789

        result = await callback_registry.dispatch(mock_bot, message, "test_data")
        assert result is True

    @pytest.mark.asyncio
    async def test_dispatch_admin_callback(self, callback_registry, mock_bot):
        """Test admin callback dispatch."""

        async def admin_handler(bot, message, data):
            return "admin_result"

        callback_registry.register_callback("admin_", admin_handler, admin_only=True)

        message = Mock()
        message.user = Mock()
        message.user.id = 123456789

        result = await callback_registry.dispatch(mock_bot, message, "admin_data")
        assert result is True


class TestCallbackRegistryDefaultRegistrationExtended:
    """Extended tests for default callback registration."""

    @pytest.fixture
    def mock_bot(self):
        """Create mock bot for testing."""
        bot = Mock()
        bot.is_sudo = Mock(return_value=True)
        bot.sudo_users = {"123456789"}
        bot.awaitable = Mock(return_value=lambda func: func)
        bot.adapter = Mock()
        bot.adapter.send_message = Mock()
        return bot

    def test_register_default(self, mock_bot):
        """Test default callback registration."""
        registry = CallbackRegistry()
        registry.register_default(mock_bot)

        assert "engine_" in registry._handlers
        assert "settings_" in registry._handlers

    def test_register_admin(self, mock_bot):
        """Test admin callback registration."""
        registry = CallbackRegistry()
        registry.register_admin(mock_bot)

        assert "admin_stats" in registry._admin_handlers
        assert "admin_keys" in registry._admin_handlers
        assert "admin_settings" in registry._admin_handlers
        assert "admin_cache" in registry._admin_handlers
        assert "admin_test" in registry._admin_handlers
        assert "admin_performance" in registry._admin_handlers
        assert "admin_health" in registry._admin_handlers
        assert "admin_back" in registry._admin_handlers
        assert "create_key" in registry._admin_handlers
        assert "list_keys" in registry._admin_handlers
        assert "delete_key" in registry._admin_handlers
        assert "create_key_user" in registry._admin_handlers
        assert "create_key_writer" in registry._admin_handlers
        assert "create_key_admin" in registry._admin_handlers
        assert "delete_key_confirm_" in registry._admin_handlers
        assert "clear_cache" in registry._admin_handlers
        assert "confirm_clear_cache" in registry._admin_handlers
        assert "cancel_clear_cache" in registry._admin_handlers
        assert "confirm_restart" in registry._admin_handlers
        assert "cancel_restart" in registry._admin_handlers
        assert "test_all_engines" in registry._admin_handlers
        assert "test_edge" in registry._admin_handlers
        assert "test_piper" in registry._admin_handlers
        assert "test_gtts" in registry._admin_handlers
