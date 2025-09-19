"""
Test cases for admin commands functionality.

This module tests the CommandRegistry and admin command functionality
that was migrated from admin_commands.py to commands.py.
"""

from unittest.mock import Mock

import pytest

from ttskit.bot.commands import CommandRegistry


class TestCommandRegistry:
    """Test CommandRegistry class."""

    def test_command_registry_initialization(self):
        """Test CommandRegistry initialization."""
        registry = CommandRegistry()
        assert isinstance(registry, CommandRegistry)
        assert hasattr(registry, "_handlers")
        assert hasattr(registry, "admin_commands")

    def test_register_command(self):
        """Test command registration."""
        registry = CommandRegistry()

        async def test_handler(message, args):
            return "test"

        registry.register("/test", test_handler)
        assert "/test" in registry._handlers
        assert registry._handlers["/test"] == test_handler

    def test_register_admin_command(self):
        """Test admin command registration."""
        registry = CommandRegistry()

        async def admin_handler(message, args):
            return "admin"

        registry.register("/admin", admin_handler, admin_only=True)
        assert "admin" in registry.admin_commands

    def test_register_bulk(self):
        """Test bulk command registration."""
        registry = CommandRegistry()

        async def handler1(message, args):
            return "handler1"

        async def handler2(message, args):
            return "handler2"

        handlers = {"/test1": handler1, "/test2": handler2}

        registry.register_bulk(handlers)
        assert "/test1" in registry._handlers
        assert "/test2" in registry._handlers
        assert registry._handlers["/test1"] == handler1
        assert registry._handlers["/test2"] == handler2


class TestCommandRegistryIntegration:
    """Test CommandRegistry integration with bot."""

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
    def command_registry(self):
        """Create CommandRegistry instance for testing."""
        return CommandRegistry()

    @pytest.mark.asyncio
    async def test_dispatch_command(self, command_registry, mock_bot):
        """Test command dispatch."""

        async def test_handler(message, args):
            return "test_result"

        command_registry.register("/test", test_handler)

        message = Mock()
        message.text = "/test"
        message.from_user = Mock()
        message.from_user.id = 123456789

        result = await command_registry.dispatch(message, "/test")
        assert result is True

    @pytest.mark.asyncio
    async def test_dispatch_admin_command(self, command_registry, mock_bot):
        """Test admin command dispatch."""

        async def admin_handler(message, args):
            return "admin_result"

        command_registry.register("/admin", admin_handler, admin_only=True)

        message = Mock()
        message.text = "/admin"
        message.from_user = Mock()
        message.from_user.id = 123456789

        result = await command_registry.dispatch(message, "/admin")
        assert result is True


class TestCommandRegistryDefaultRegistration:
    """Test default command registration."""

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
        """Test default command registration."""
        registry = CommandRegistry()
        registry.register_default(mock_bot)

        assert "/start" in registry._handlers
        assert "/help" in registry._handlers
        assert "/status" in registry._handlers

    def test_register_admin(self, mock_bot):
        """Test admin command registration (basic admin set)."""
        registry = CommandRegistry()
        registry.register_admin(mock_bot)

        expected_any = {"clear_cache", "cache_stats", "reload_engines", "reset_stats"}
        assert expected_any & registry.admin_commands

    def test_register_advanced_admin(self, mock_bot):
        """Test advanced admin command registration."""
        registry = CommandRegistry()
        registry.register_advanced_admin(mock_bot)

        assert "system_stats" in registry.admin_commands
        assert "health_check" in registry.admin_commands
        assert "performance" in registry.admin_commands
        assert "monitor" in registry.admin_commands
        assert "export_metrics" in registry.admin_commands
        assert "clear_cache" in registry.admin_commands
        assert "restart" in registry.admin_commands
        assert "debug" in registry.admin_commands
        assert "test_engines" in registry.admin_commands
        assert "create_user" in registry.admin_commands
        assert "delete_user" in registry.admin_commands
        assert "list_users" in registry.admin_commands
