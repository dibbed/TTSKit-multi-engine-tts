"""Tests for Bot Commands."""

from unittest.mock import Mock

import pytest

from ttskit.bot.commands import CommandRegistry
from ttskit.telegram.base import MessageType, TelegramMessage, TelegramUser


class TestCommandRegistry:
    """Test cases for CommandRegistry."""

    @pytest.fixture
    def command_registry(self):
        """Create CommandRegistry instance for testing."""
        return CommandRegistry()

    @pytest.fixture
    def mock_bot(self):
        """Create mock bot for testing."""
        bot = Mock()
        bot.sudo_users = {"12345"}
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
            text="/start",
            message_type=MessageType.TEXT,
        )

    def test_initialization(self, command_registry):
        """Test CommandRegistry initialization."""
        assert command_registry is not None
        assert isinstance(command_registry.commands, dict)

    def test_register_command(self, command_registry):
        """Test registering a command."""

        async def test_command(message, bot):
            return "test_response"

        command_registry.register_command("test", test_command)

        assert "test" in command_registry.commands
        assert command_registry.commands["test"] == test_command

    def test_register_command_with_admin_flag(self, command_registry):
        """Test registering an admin command."""

        async def admin_command(message, bot):
            return "admin_response"

        command_registry.register_command("admin", admin_command, admin_only=True)

        assert "admin" in command_registry.commands
        assert command_registry.commands["admin"] == admin_command
        assert command_registry.admin_commands == {"admin"}

    def test_dispatch_command_success(self, command_registry, mock_bot, mock_message):
        """Test successful command dispatch."""

        async def test_command(message, bot):
            return "test_response"

        command_registry.register_command("start", test_command)

        import asyncio

        async def run_test():
            result = await command_registry.dispatch(mock_message, mock_bot)
            assert result is True

        asyncio.run(run_test())

    def test_dispatch_command_not_found(self, command_registry, mock_bot, mock_message):
        """Test command dispatch when command not found."""
        import asyncio

        async def run_test():
            result = await command_registry.dispatch(mock_message, mock_bot)
            assert result is False

        asyncio.run(run_test())

    def test_dispatch_admin_command_sudo_user(
        self, command_registry, mock_bot, mock_message
    ):
        """Test dispatching admin command for sudo user."""

        async def admin_command(message, bot):
            return "admin_response"

        command_registry.register_command("admin", admin_command, admin_only=True)

        mock_message.text = "/admin"

        import asyncio

        async def run_test():
            result = await command_registry.dispatch(mock_message, mock_bot)
            assert result is True

        asyncio.run(run_test())

    def test_dispatch_admin_command_non_sudo_user(
        self, command_registry, mock_bot, mock_message
    ):
        """Test dispatching admin command for non-sudo user."""

        async def admin_command(message, bot):
            return "admin_response"

        command_registry.register_command("admin", admin_command, admin_only=True)

        mock_message.text = "/admin"

        mock_message.user.id = 99999
        mock_bot.sudo_users = {"12345"}
        mock_bot.is_sudo = Mock(return_value=False)

        import asyncio

        async def run_test():
            result = await command_registry.dispatch(mock_message, mock_bot)
            assert result is False

        asyncio.run(run_test())

    def test_register_default_commands(self, command_registry, mock_bot):
        """Test registering default commands."""
        command_registry.register_default(mock_bot)

        assert "start" in command_registry.commands
        assert "help" in command_registry.commands
        assert "status" in command_registry.commands
        assert "engines" in command_registry.commands
        assert "voices" in command_registry.commands
        assert "languages" in command_registry.commands

    def test_register_admin_commands(self, command_registry, mock_bot):
        """Test registering admin commands."""
        command_registry.register_default(mock_bot)
        command_registry.register_admin(mock_bot)

        assert "stats" in command_registry.commands
        assert "reset_stats" in command_registry.commands
        assert "clear_cache" in command_registry.commands
        assert "restart" in command_registry.commands
        assert "shutdown" in command_registry.commands

    def test_start_command(self, command_registry, mock_bot, mock_message):
        """Test start command."""
        command_registry.register_default(mock_bot)

        import asyncio

        async def run_test():
            result = await command_registry.dispatch(mock_message, mock_bot)
            assert result is True

        asyncio.run(run_test())

    def test_help_command(self, command_registry, mock_bot, mock_message):
        """Test help command."""
        command_registry.register_default(mock_bot)
        mock_message.text = "/help"

        import asyncio

        async def run_test():
            result = await command_registry.dispatch(mock_message, mock_bot)
            assert result is True

        asyncio.run(run_test())

    def test_status_command(self, command_registry, mock_bot, mock_message):
        """Test status command."""
        command_registry.register_default(mock_bot)
        mock_message.text = "/status"

        import asyncio

        async def run_test():
            result = await command_registry.dispatch(mock_message, mock_bot)
            assert result is True

        asyncio.run(run_test())

    def test_engines_command(self, command_registry, mock_bot, mock_message):
        """Test engines command."""
        command_registry.register_default(mock_bot)
        mock_message.text = "/engines"

        import asyncio

        async def run_test():
            result = await command_registry.dispatch(mock_message, mock_bot)
            assert result is True

        asyncio.run(run_test())

    def test_voices_command(self, command_registry, mock_bot, mock_message):
        """Test voices command."""
        from unittest.mock import patch

        with patch("ttskit.public.list_voices") as mock_list_voices:
            mock_list_voices.return_value = ["voice1", "voice2"]

            command_registry.register_default(mock_bot)
            mock_message.text = "/voices"

            import asyncio

            async def run_test():
                result = await command_registry.dispatch(mock_message, mock_bot)
                assert result is True

            asyncio.run(run_test())

    def test_languages_command(self, command_registry, mock_bot, mock_message):
        """Test languages command."""
        command_registry.register_default(mock_bot)
        mock_message.text = "/languages"

        import asyncio

        async def run_test():
            result = await command_registry.dispatch(mock_message, mock_bot)
            assert result is True

        asyncio.run(run_test())

    def test_stats_command_admin(self, command_registry, mock_bot, mock_message):
        """Test stats command for admin user."""
        command_registry.register_default(mock_bot)
        command_registry.register_admin(mock_bot)
        mock_message.text = "/stats"
        mock_bot.is_sudo = Mock(return_value=True)

        import asyncio

        async def run_test():
            result = await command_registry.dispatch(mock_message, mock_bot)
            assert result is True

        asyncio.run(run_test())

    def test_reset_stats_command_admin(self, command_registry, mock_bot, mock_message):
        """Test reset_stats command for admin user."""
        command_registry.register_admin(mock_bot)
        mock_message.text = "/reset_stats"

        import asyncio

        async def run_test():
            result = await command_registry.dispatch(mock_message, mock_bot)
            assert result is True

        asyncio.run(run_test())

    def test_clear_cache_command_admin(self, command_registry, mock_bot, mock_message):
        """Test clear_cache command for admin user."""
        command_registry.register_admin(mock_bot)
        mock_message.text = "/clear_cache"

        import asyncio

        async def run_test():
            result = await command_registry.dispatch(mock_message, mock_bot)
            assert result is True

        asyncio.run(run_test())

    def test_restart_command_admin(self, command_registry, mock_bot, mock_message):
        """Test restart command for admin user."""
        command_registry.register_admin(mock_bot)
        mock_message.text = "/restart"

        import asyncio

        async def run_test():
            result = await command_registry.dispatch(mock_message, mock_bot)
            assert result is True

        asyncio.run(run_test())

    def test_shutdown_command_admin(self, command_registry, mock_bot, mock_message):
        """Test shutdown command for admin user."""
        command_registry.register_admin(mock_bot)
        mock_message.text = "/shutdown"

        import asyncio

        async def run_test():
            result = await command_registry.dispatch(mock_message, mock_bot)
            assert result is True

        asyncio.run(run_test())

    def test_command_with_parameters(self, command_registry, mock_bot, mock_message):
        """Test command with parameters."""

        async def test_command(message, bot):
            return f"Command: {message.text}"

        command_registry.register_command("test", test_command)
        mock_message.text = "/test param1 param2"

        import asyncio

        async def run_test():
            result = await command_registry.dispatch(mock_message, mock_bot)
            assert result is True

        asyncio.run(run_test())

    def test_command_case_insensitive(self, command_registry, mock_bot, mock_message):
        """Test command case insensitive matching."""

        async def test_command(message, bot):
            return "test_response"

        command_registry.register_command("test", test_command)
        mock_message.text = "/TEST"

        import asyncio

        async def run_test():
            result = await command_registry.dispatch(mock_message, mock_bot)
            assert result is True

        asyncio.run(run_test())

    def test_command_with_whitespace(self, command_registry, mock_bot, mock_message):
        """Test command with whitespace."""

        async def test_command(message, bot):
            return "test_response"

        command_registry.register_command("test", test_command)
        mock_message.text = "  /test  "

        import asyncio

        async def run_test():
            result = await command_registry.dispatch(mock_message, mock_bot)
            assert result is True

        asyncio.run(run_test())
