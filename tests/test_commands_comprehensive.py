"""Comprehensive tests for CommandRegistry and command handlers.

Tests all uncovered functions and branches in ttskit/bot/commands.py:
- CommandRegistry.registered
- CommandRegistry.register_default.cmd_stats
- CommandRegistry.register_admin.* (admin_cache_stats, admin_reload_engines, admin_cache_cleanup, admin_cache_export)
- handle_*_command functions (start, help, stats, engines, voices, config, reset)
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from ttskit.bot.commands import (
    CommandRegistry,
    handle_config_command,
    handle_engines_command,
    handle_help_command,
    handle_reset_command,
    handle_start_command,
    handle_stats_command,
    handle_voices_command,
)


class TestCommandRegistryRegistered:
    """Test CommandRegistry.registered method."""

    def test_registered_returns_handlers_dict(self):
        """Test that registered() returns the handlers dictionary."""
        registry = CommandRegistry()

        async def handler1(message, args):
            pass

        async def handler2(message, args):
            pass

        registry.register("/test1", handler1)
        registry.register("/test2", handler2, admin_only=True)

        registered = registry.registered()

        assert isinstance(registered, dict)
        assert "/test1" in registered
        assert "/test2" in registered
        assert registered["/test1"] == handler1
        assert registered["/test2"] == handler2


class TestCommandRegistryRegisterDefaultCmdStats:
    """Test CommandRegistry.register_default.cmd_stats function."""

    @pytest.fixture
    def mock_bot(self):
        """Create a mock bot with required methods."""
        bot = Mock()
        bot.get_stats.return_value = {
            "messages_processed": 100,
            "synthesis_requests": 50,
            "cache_hits": 30,
            "cache_misses": 20,
            "avg_processing_time": 1.5,
        }
        bot.awaitable = lambda func: func
        bot.adapter.send_message = AsyncMock()
        return bot

    @pytest.fixture
    def mock_message(self):
        """Create a mock message."""
        message = Mock()
        message.chat_id = 12345
        return message

    @pytest.mark.asyncio
    async def test_cmd_stats_success(self, mock_bot, mock_message):
        """Test successful stats command execution."""
        registry = CommandRegistry()
        registry.register_default(mock_bot)

        mock_message.text = "/stats"

        result = await registry.dispatch(mock_message, mock_bot)

        assert result is True
        mock_bot.get_stats.assert_called_once()
        mock_bot.adapter.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_cmd_stats_with_args(self, mock_bot, mock_message):
        """Test stats command with arguments."""
        registry = CommandRegistry()
        registry.register_default(mock_bot)

        mock_message.text = "/stats detailed"

        result = await registry.dispatch(mock_message, mock_bot)

        assert result is True
        mock_bot.get_stats.assert_called_once()

    @pytest.mark.asyncio
    async def test_cmd_stats_exception_handling(self, mock_bot, mock_message):
        """Test stats command exception handling."""
        registry = CommandRegistry()
        registry.register_default(mock_bot)

        mock_bot.get_stats.side_effect = Exception("Stats error")

        mock_message.text = "/stats"

        result = await registry.dispatch(mock_message, mock_bot)

        assert result is True


class TestCommandRegistryRegisterAdmin:
    """Test CommandRegistry.register_admin admin functions."""

    @pytest.fixture
    def mock_bot(self):
        """Create a mock bot with admin methods."""
        bot = Mock()
        bot.is_sudo = Mock(return_value=True)
        bot.awaitable = lambda func: func
        bot.adapter.send_message = AsyncMock()
        return bot

    @pytest.fixture
    def mock_message(self):
        """Create a mock message with user."""
        message = Mock()
        message.chat_id = 12345
        message.user = Mock()
        message.user.id = 12345
        return message

    @pytest.mark.asyncio
    async def test_admin_cache_stats_success(self, mock_bot, mock_message):
        """Test successful admin cache stats command."""
        registry = CommandRegistry()
        registry.register_admin(mock_bot)

        with patch("ttskit.utils.audio_manager.audio_manager") as mock_audio_manager:
            mock_audio_manager.get_cache_stats.return_value = {
                "total_files": 100,
                "total_size_mb": 50.5,
                "max_cache_size": "100MB",
                "max_file_age": "7 days",
            }

            mock_message.text = "/cachestats"
            result = await registry.dispatch(mock_message, mock_bot)

            assert result is True
            mock_audio_manager.get_cache_stats.assert_called_once()
            mock_bot.adapter.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_admin_cache_stats_exception(self, mock_bot, mock_message):
        """Test admin cache stats command with exception."""
        registry = CommandRegistry()
        registry.register_admin(mock_bot)

        with patch("ttskit.utils.audio_manager.audio_manager") as mock_audio_manager:
            mock_audio_manager.get_cache_stats.side_effect = Exception("Cache error")

            mock_message.text = "/cachestats"
            result = await registry.dispatch(mock_message, mock_bot)

            assert result is True
            assert mock_bot.adapter.send_message.call_count >= 1

    @pytest.mark.asyncio
    async def test_admin_reload_engines_success(self, mock_bot, mock_message):
        """Test successful admin reload engines command."""
        registry = CommandRegistry()
        registry.register_admin(mock_bot)

        with (
            patch("ttskit.engines.factory") as mock_factory,
            patch("ttskit.engines.registry") as mock_registry,
        ):
            mock_message.text = "/reloadengines"
            result = await registry.dispatch(mock_message, mock_bot)

            assert result is True
            mock_factory.setup_registry.assert_called_once_with(mock_registry.registry)
            mock_bot.adapter.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_admin_reload_engines_exception(self, mock_bot, mock_message):
        """Test admin reload engines command with exception."""
        registry = CommandRegistry()
        registry.register_admin(mock_bot)

        with patch("ttskit.engines.factory") as mock_factory:
            mock_factory.setup_registry.side_effect = Exception("Reload error")

            mock_message.text = "/reloadengines"
            result = await registry.dispatch(mock_message, mock_bot)

            assert result is True
            assert mock_bot.adapter.send_message.call_count >= 1

    @pytest.mark.asyncio
    async def test_admin_cache_cleanup_success(self, mock_bot, mock_message):
        """Test successful admin cache cleanup command."""
        registry = CommandRegistry()
        registry.register_admin(mock_bot)

        with patch("ttskit.utils.audio_manager.audio_manager") as mock_audio_manager:
            mock_audio_manager.get_cache_stats.side_effect = [
                {"total_files": 100, "total_size_mb": 50.0},
                {"total_files": 80, "total_size_mb": 40.0},
            ]

            mock_message.text = "/cachecleanup"
            result = await registry.dispatch(mock_message, mock_bot)

            assert result is True
            mock_audio_manager.cleanup_old_files.assert_called_once()
            mock_bot.adapter.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_admin_cache_cleanup_exception(self, mock_bot, mock_message):
        """Test admin cache cleanup command with exception."""
        registry = CommandRegistry()
        registry.register_admin(mock_bot)

        with patch("ttskit.utils.audio_manager.audio_manager") as mock_audio_manager:
            mock_audio_manager.get_cache_stats.side_effect = Exception("Cleanup error")

            mock_message.text = "/cachecleanup"
            result = await registry.dispatch(mock_message, mock_bot)

            assert result is True
            assert mock_bot.adapter.send_message.call_count >= 1

    @pytest.mark.asyncio
    async def test_admin_cache_export_success(self, mock_bot, mock_message):
        """Test successful admin cache export command."""
        registry = CommandRegistry()
        registry.register_admin(mock_bot)

        with (
            patch("ttskit.utils.audio_manager.audio_manager") as mock_audio_manager,
            patch("ttskit.utils.temp_manager.TempFileManager") as mock_temp_manager,
        ):
            mock_temp_instance = Mock()
            mock_temp_instance.create_temp_dir.return_value = "/tmp/export_123"
            mock_temp_manager.return_value = mock_temp_instance

            mock_audio_manager.get_cache_stats.return_value = {
                "total_files": 100,
                "total_size_mb": 50.0,
            }

            mock_message.text = "/cacheexport"
            result = await registry.dispatch(mock_message, mock_bot)

            assert result is True
            mock_audio_manager.export_cache.assert_called_once_with("/tmp/export_123")
            mock_bot.adapter.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_admin_cache_export_exception(self, mock_bot, mock_message):
        """Test admin cache export command with exception."""
        registry = CommandRegistry()
        registry.register_admin(mock_bot)

        with (
            patch("ttskit.utils.audio_manager.audio_manager") as mock_audio_manager,
            patch("ttskit.utils.temp_manager.TempFileManager") as mock_temp_manager,
        ):
            mock_temp_instance = Mock()
            mock_temp_instance.create_temp_dir.side_effect = Exception("Export error")
            mock_temp_manager.return_value = mock_temp_instance

            mock_message.text = "/cacheexport"
            result = await registry.dispatch(mock_message, mock_bot)

            assert result is True
            assert mock_bot.adapter.send_message.call_count >= 1

    @pytest.mark.asyncio
    async def test_admin_commands_access_denied(self, mock_bot, mock_message):
        """Test admin commands with non-sudo user."""
        registry = CommandRegistry()
        registry.register_admin(mock_bot)

        mock_bot.is_sudo.return_value = False

        mock_message.text = "/cachestats"
        result = await registry.dispatch(mock_message, mock_bot)

        assert result is False
        mock_bot.adapter.send_message.assert_not_called()


class TestHandleCommandFunctions:
    """Test standalone handle_*_command functions."""

    @pytest.fixture
    def mock_bot(self):
        """Create a mock bot."""
        bot = Mock()
        bot.awaitable = lambda func: func
        bot.adapter.send_message = AsyncMock()
        bot.get_stats.return_value = {"messages_processed": 10}
        bot.get_engine_info = AsyncMock(
            return_value={"available_engines": ["gtts", "piper"]}
        )
        return bot

    @pytest.fixture
    def mock_message(self):
        """Create a mock message."""
        message = Mock()
        message.chat_id = 12345
        return message

    @pytest.mark.asyncio
    async def test_handle_start_command(self, mock_bot, mock_message):
        """Test handle_start_command function."""
        mock_message.text = "/start"
        result = await handle_start_command(mock_bot, mock_message, "")

        assert result is True
        mock_bot.adapter.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_help_command(self, mock_bot, mock_message):
        """Test handle_help_command function."""
        mock_message.text = "/help"
        result = await handle_help_command(mock_bot, mock_message, "")

        assert result is True
        mock_bot.adapter.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_stats_command(self, mock_bot, mock_message):
        """Test handle_stats_command function."""
        mock_message.text = "/stats"
        result = await handle_stats_command(mock_bot, mock_message, "")

        assert result is True
        mock_bot.get_stats.assert_called_once()
        mock_bot.adapter.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_engines_command(self, mock_bot, mock_message):
        """Test handle_engines_command function."""
        mock_message.text = "/engines"
        result = await handle_engines_command(mock_bot, mock_message, "")

        assert result is True
        mock_bot.get_engine_info.assert_called_once()
        mock_bot.adapter.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_voices_command(self, mock_bot, mock_message):
        """Test handle_voices_command function."""
        with patch("ttskit.public.list_voices") as mock_list_voices:
            mock_list_voices.return_value = ["voice1", "voice2"]

            mock_message.text = "/voices"
            result = await handle_voices_command(mock_bot, mock_message, "")

            assert result is True
            mock_bot.adapter.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_voices_command_with_args(self, mock_bot, mock_message):
        """Test handle_voices_command with language and engine args."""
        with patch("ttskit.public.list_voices") as mock_list_voices:
            mock_list_voices.return_value = ["voice1", "voice2"]

            mock_message.text = "/voices [en] gtts"
            result = await handle_voices_command(mock_bot, mock_message, "[en] gtts")

            assert result is True
            mock_list_voices.assert_called_once_with(lang="en", engine="gtts")
            mock_bot.adapter.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_config_command(self, mock_bot, mock_message):
        """Test handle_config_command function."""
        result = await handle_config_command(mock_bot, mock_message, "")

        assert result is None
        mock_bot.adapter.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_reset_command(self, mock_bot, mock_message):
        """Test handle_reset_command function."""
        mock_bot.is_sudo.return_value = True
        mock_message.user = Mock()
        mock_message.user.id = 12345
        mock_message.text = "/resetstats"

        result = await handle_reset_command(mock_bot, mock_message, "")

        assert result is True
        mock_bot.adapter.send_message.assert_called_once()


class TestCommandRegistryRegistration:
    """Test command registration functionality."""

    def test_register_default_commands(self):
        """Test that register_default registers all expected commands."""
        registry = CommandRegistry()
        mock_bot = Mock()
        mock_bot.awaitable = lambda func: func
        mock_bot.adapter.send_message = AsyncMock()
        mock_bot.get_stats.return_value = {}
        mock_bot.get_engine_info = AsyncMock(return_value={"available_engines": []})

        registry.register_default(mock_bot)

        commands = registry.commands
        assert "start" in commands
        assert "help" in commands
        assert "stats" in commands
        assert "engines" in commands
        assert "voices" in commands
        assert "status" in commands
        assert "languages" in commands

    def test_register_admin_commands(self):
        """Test that register_admin registers all expected admin commands."""
        registry = CommandRegistry()
        mock_bot = Mock()
        mock_bot.is_sudo = Mock(return_value=True)
        mock_bot.awaitable = lambda func: func
        mock_bot.adapter.send_message = AsyncMock()

        registry.register_admin(mock_bot)

        admin_commands = registry.admin_commands
        assert "clearcache" in admin_commands
        assert "cachestats" in admin_commands
        assert "cachecleanup" in admin_commands
        assert "cacheexport" in admin_commands
        assert "reloadengines" in admin_commands
        assert "resetstats" in admin_commands
        assert "restart" in admin_commands
        assert "shutdown" in admin_commands


class TestCommandRegistryAuthRole:
    """Test authentication and role-based access control."""

    @pytest.fixture
    def mock_bot(self):
        """Create a mock bot."""
        bot = Mock()
        bot.awaitable = lambda func: func
        bot.adapter.send_message = AsyncMock()
        return bot

    @pytest.fixture
    def mock_message_non_sudo(self):
        """Create a mock message for non-sudo user."""
        message = Mock()
        message.chat_id = 12345
        message.user = Mock()
        message.user.id = 99999
        return message

    @pytest.mark.asyncio
    async def test_admin_command_non_sudo_user(self, mock_bot, mock_message_non_sudo):
        """Test admin command with non-sudo user should be denied."""
        registry = CommandRegistry()
        registry.register_admin(mock_bot)

        mock_bot.is_sudo.return_value = False

        mock_message_non_sudo.text = "/cachestats"
        result = await registry.dispatch(mock_message_non_sudo, mock_bot)

        assert result is False
        mock_bot.adapter.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_admin_command_sudo_user(self, mock_bot, mock_message_non_sudo):
        """Test admin command with sudo user should be allowed."""
        registry = CommandRegistry()
        registry.register_admin(mock_bot)

        mock_bot.is_sudo.return_value = True

        with patch("ttskit.utils.audio_manager.audio_manager") as mock_audio_manager:
            mock_audio_manager.get_cache_stats.return_value = {
                "total_files": 10,
                "total_size_mb": 5.0,
            }

            mock_message_non_sudo.text = "/cachestats"
            result = await registry.dispatch(mock_message_non_sudo, mock_bot)

            assert result is True
            mock_audio_manager.get_cache_stats.assert_called_once()


class TestCommandRegistryRouting:
    """Test command routing and handler execution."""

    @pytest.fixture
    def mock_bot(self):
        """Create a mock bot."""
        bot = Mock()
        bot.awaitable = lambda func: func
        bot.adapter.send_message = AsyncMock()
        bot.get_stats.return_value = {"messages_processed": 5}
        bot.get_engine_info = AsyncMock(return_value={"available_engines": ["gtts"]})
        return bot

    @pytest.fixture
    def mock_message(self):
        """Create a mock message."""
        message = Mock()
        message.chat_id = 12345
        return message

    @pytest.mark.asyncio
    async def test_start_command_routing(self, mock_bot, mock_message):
        """Test /start command routing and output."""
        registry = CommandRegistry()
        registry.register_default(mock_bot)

        mock_message.text = "/start"
        result = await registry.dispatch(mock_message, mock_bot)

        assert result is True
        mock_bot.adapter.send_message.assert_called_once()

        call_args = mock_bot.adapter.send_message.call_args
        assert call_args[0][0] == 12345
        assert isinstance(call_args[0][1], str)

    @pytest.mark.asyncio
    async def test_help_command_routing(self, mock_bot, mock_message):
        """Test /help command routing and output."""
        registry = CommandRegistry()
        registry.register_default(mock_bot)

        mock_message.text = "/help"
        result = await registry.dispatch(mock_message, mock_bot)

        assert result is True
        mock_bot.adapter.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_stats_command_routing(self, mock_bot, mock_message):
        """Test /stats command routing and output."""
        registry = CommandRegistry()
        registry.register_default(mock_bot)

        mock_message.text = "/stats"
        result = await registry.dispatch(mock_message, mock_bot)

        assert result is True
        mock_bot.get_stats.assert_called_once()
        mock_bot.adapter.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_reset_command_routing(self, mock_bot, mock_message):
        """Test /reset command routing (should reset user state)."""
        registry = CommandRegistry()
        registry.register_default(mock_bot)
        registry.register_admin(mock_bot)

        mock_bot.is_sudo.return_value = True

        mock_message.text = "/resetstats"
        result = await registry.dispatch(mock_message, mock_bot)

        assert result is True
        mock_bot.adapter.send_message.assert_called_once()


class TestCommandRegistryErrorBranches:
    """Test error handling branches in command handlers."""

    @pytest.fixture
    def mock_bot(self):
        """Create a mock bot."""
        bot = Mock()
        bot.awaitable = lambda func: func
        bot.adapter.send_message = AsyncMock()
        return bot

    @pytest.fixture
    def mock_message(self):
        """Create a mock message."""
        message = Mock()
        message.chat_id = 12345
        message.user = Mock()
        message.user.id = 12345
        return message

    @pytest.mark.asyncio
    async def test_admin_cache_export_error_branch(self, mock_bot, mock_message):
        """Test admin_cache_export error branch."""
        registry = CommandRegistry()
        registry.register_admin(mock_bot)
        mock_bot.is_sudo.return_value = True

        with (
            patch("ttskit.utils.audio_manager.audio_manager") as mock_audio_manager,
            patch("ttskit.utils.temp_manager.TempFileManager") as mock_temp_manager,
        ):
            mock_audio_manager.export_cache.side_effect = Exception("Export failed")
            mock_temp_instance = Mock()
            mock_temp_instance.create_temp_dir.return_value = "/tmp/export"
            mock_temp_manager.return_value = mock_temp_instance

            mock_message.text = "/cacheexport"
            result = await registry.dispatch(mock_message, mock_bot)

            assert result is True
            assert mock_bot.adapter.send_message.call_count >= 1

    @pytest.mark.asyncio
    async def test_admin_cache_cleanup_error_branch(self, mock_bot, mock_message):
        """Test admin_cache_cleanup error branch."""
        registry = CommandRegistry()
        registry.register_admin(mock_bot)
        mock_bot.is_sudo.return_value = True

        with patch("ttskit.utils.audio_manager.audio_manager") as mock_audio_manager:
            mock_audio_manager.cleanup_old_files.side_effect = Exception(
                "Cleanup failed"
            )

            mock_message.text = "/cachecleanup"
            result = await registry.dispatch(mock_message, mock_bot)

            assert result is True
            assert mock_bot.adapter.send_message.call_count >= 1

    @pytest.mark.asyncio
    async def test_admin_reload_engines_error_branch(self, mock_bot, mock_message):
        """Test admin_reload_engines error branch."""
        registry = CommandRegistry()
        registry.register_admin(mock_bot)
        mock_bot.is_sudo.return_value = True

        with patch("ttskit.engines.factory") as mock_factory:
            mock_factory.setup_registry.side_effect = Exception("Reload failed")

            mock_message.text = "/reloadengines"
            result = await registry.dispatch(mock_message, mock_bot)

            assert result is True
            assert mock_bot.adapter.send_message.call_count >= 1


class TestCommandRegistryMocking:
    """Test command handlers with mocked dependencies."""

    @pytest.fixture
    def mock_bot(self):
        """Create a mock bot with stats and engine registry."""
        bot = Mock()
        bot.awaitable = lambda func: func
        bot.adapter.send_message = AsyncMock()
        bot.get_stats.return_value = {
            "messages_processed": 100,
            "synthesis_requests": 50,
            "cache_hits": 30,
            "cache_misses": 20,
            "avg_processing_time": 1.5,
        }
        bot.get_engine_info = AsyncMock(
            return_value={"available_engines": ["gtts", "piper", "edge"]}
        )
        return bot

    @pytest.fixture
    def mock_message(self):
        """Create a mock message."""
        message = Mock()
        message.chat_id = 12345
        return message

    @pytest.mark.asyncio
    async def test_stats_with_mocked_provider(self, mock_bot, mock_message):
        """Test stats command with mocked stats provider."""
        registry = CommandRegistry()
        registry.register_default(mock_bot)

        mock_message.text = "/stats"
        result = await registry.dispatch(mock_message, mock_bot)

        assert result is True
        mock_bot.get_stats.assert_called_once()
        mock_bot.adapter.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_engines_with_mocked_registry(self, mock_bot, mock_message):
        """Test engines command with mocked engine registry."""
        registry = CommandRegistry()
        registry.register_default(mock_bot)

        mock_message.text = "/engines"
        result = await registry.dispatch(mock_message, mock_bot)

        assert result is True
        mock_bot.get_engine_info.assert_called_once()
        mock_bot.adapter.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_voices_with_mocked_list_voices(self, mock_bot, mock_message):
        """Test voices command with mocked list_voices."""
        registry = CommandRegistry()
        registry.register_default(mock_bot)

        with patch("ttskit.public.list_voices") as mock_list_voices:
            mock_list_voices.return_value = ["voice1", "voice2", "voice3"]

            mock_message.text = "/voices"
            result = await registry.dispatch(mock_message, mock_bot)

            assert result is True
            mock_list_voices.assert_called_once()
            mock_bot.adapter.send_message.assert_called_once()
