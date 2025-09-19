"""
Comprehensive test cases for admin panel setup functionality.

This module provides comprehensive tests for the CallbackRegistry setup functionality.
"""

from unittest.mock import Mock

import pytest

from ttskit.bot.callbacks import CallbackRegistry


class TestCallbackRegistrySetupComprehensive:
    """Comprehensive tests for CallbackRegistry setup functionality."""

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

    def test_register_default_setup(self, mock_bot):
        """Test default callback registration setup."""
        registry = CallbackRegistry()
        registry.register_default(mock_bot)

        assert "engine_" in registry._handlers
        assert "settings_" in registry._handlers

    def test_register_admin_setup(self, mock_bot):
        """Test admin callback registration setup."""
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

    def test_register_bulk_setup(self, mock_bot):
        """Test bulk callback registration setup."""
        registry = CallbackRegistry()

        async def handler1(bot, message, data):
            return "handler1"

        async def handler2(bot, message, data):
            return "handler2"

        handlers = {"test1_": handler1, "test2_": handler2}

        registry.register_bulk(handlers)
        assert "test1_" in registry._handlers
        assert "test2_" in registry._handlers
        assert registry._handlers["test1_"] == handler1
        assert registry._handlers["test2_"] == handler2

    def test_register_callback_setup(self, mock_bot):
        """Test callback registration setup."""
        registry = CallbackRegistry()

        async def test_handler(bot, message, data):
            return "test"

        registry.register_callback("test_", test_handler)
        assert "test_" in registry._handlers
        assert registry._handlers["test_"] == test_handler

    def test_register_admin_callback_setup(self, mock_bot):
        """Test admin callback registration setup."""
        registry = CallbackRegistry()

        async def admin_handler(bot, message, data):
            return "admin"

        registry.register_callback("admin_", admin_handler, admin_only=True)
        assert "admin_" in registry._admin_handlers
        assert registry._admin_handlers["admin_"] == admin_handler

    def test_register_callback_with_admin_flag(self, mock_bot):
        """Test callback registration with admin flag."""
        registry = CallbackRegistry()

        async def admin_handler(bot, message, data):
            return "admin"

        registry.register_callback("admin_", admin_handler, admin_only=True)

        assert "admin_" in registry._admin_handlers
        assert "admin_" in registry._handlers
        assert registry._admin_handlers["admin_"] == admin_handler
        assert registry._handlers["admin_"] == admin_handler

    def test_register_callback_without_admin_flag(self, mock_bot):
        """Test callback registration without admin flag."""
        registry = CallbackRegistry()

        async def normal_handler(bot, message, data):
            return "normal"

        registry.register_callback("normal_", normal_handler, admin_only=False)

        assert "normal_" in registry._handlers
        assert "normal_" not in registry._admin_handlers
        assert registry._handlers["normal_"] == normal_handler

    def test_register_callback_default_admin_flag(self, mock_bot):
        """Test callback registration with default admin flag."""
        registry = CallbackRegistry()

        async def default_handler(bot, message, data):
            return "default"

        registry.register_callback("default_", default_handler)

        assert "default_" in registry._handlers
        assert "default_" not in registry._admin_handlers
        assert registry._handlers["default_"] == default_handler
