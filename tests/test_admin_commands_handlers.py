"""
Test cases for admin command handlers.

This module tests the admin command handlers functionality.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from ttskit.bot.commands import CommandRegistry


class TestAdminCommandHandlers:
    """Test admin command handlers."""

    @pytest.fixture
    def mock_bot(self):
        """Create mock bot for testing."""
        bot = Mock()
        bot.is_sudo = Mock(return_value=True)
        bot.sudo_users = {"123456789"}

        def _awaitable_wrapper(func):
            async def _call(*args, **kwargs):
                return func(*args, **kwargs)

            return _call

        bot.awaitable = _awaitable_wrapper
        bot.adapter = Mock()
        bot.adapter.send_message = Mock()
        bot.stop = AsyncMock(return_value=None)
        return bot

    @pytest.fixture
    def mock_message(self):
        """Create mock message for testing."""
        message = Mock()
        message.text = "/test"
        message.from_user = Mock()
        message.from_user.id = 123456789
        message.chat_id = 123456789
        return message

    @pytest.mark.asyncio
    async def test_create_key_handler(self, mock_bot, mock_message):
        """Test create_key command handler."""
        registry = CommandRegistry()

        registry.register_advanced_admin(mock_bot)

        mock_message.text = "/create_key user_id:test_user permissions:read,write"

        with (
            patch("ttskit.database.connection.get_session") as mock_session,
            patch("ttskit.services.user_service.UserService") as mock_user_service,
        ):
            mock_db_session = Mock()
            mock_session.return_value.__next__ = Mock(return_value=mock_db_session)

            mock_service_instance = Mock()
            mock_user_service.return_value = mock_service_instance
            mock_service_instance.get_user_by_id = AsyncMock(return_value=None)
            mock_service_instance.create_user = AsyncMock()
            mock_service_instance.create_api_key = AsyncMock(
                return_value={"api_key": "test_key"}
            )

            result = await registry.dispatch(mock_message, mock_bot)
            assert result is True

    @pytest.mark.asyncio
    async def test_list_keys_handler(self, mock_bot, mock_message):
        """Test list_keys command handler."""
        registry = CommandRegistry()

        registry.register_advanced_admin(mock_bot)

        with (
            patch("ttskit.database.connection.get_session") as mock_session,
            patch("ttskit.services.user_service.UserService") as mock_user_service,
        ):
            mock_db_session = Mock()
            mock_session.return_value.__next__ = Mock(return_value=mock_db_session)

            mock_service_instance = Mock()
            mock_user_service.return_value = mock_service_instance
            mock_service_instance.get_all_users = AsyncMock(return_value=[])

            mock_message.text = "/list_keys"
            result = await registry.dispatch(mock_message, mock_bot)
            assert result is True

    @pytest.mark.asyncio
    async def test_system_stats_handler(self, mock_bot, mock_message):
        """Test system_stats command handler."""
        registry = CommandRegistry()

        registry.register_advanced_admin(mock_bot)

        with patch("ttskit.metrics.advanced.get_metrics_collector") as mock_metrics:
            mock_collector = Mock()
            mock_metrics.return_value = mock_collector
            mock_collector.get_comprehensive_metrics = AsyncMock(
                return_value={
                    "requests": {
                        "total": 100,
                        "successful": 95,
                        "failed": 5,
                        "success_rate": 95.0,
                        "per_minute": 10.0,
                    },
                    "engines": {"edge": {"total_requests": 50, "success_rate": 98.0}},
                    "cache": {"hit_rate": 85.0, "size_mb": 100.0, "evictions": 10},
                    "performance": {
                        "avg_response_time": 1.5,
                        "p95_response_time": 2.0,
                        "p99_response_time": 3.0,
                    },
                    "system": {
                        "cpu_percent": 50.0,
                        "memory_mb": 512.0,
                        "memory_percent": 60.0,
                        "disk_usage_percent": 70.0,
                        "network_io_mb": 5.0,
                    },
                    "health": 85.0,
                }
            )

            mock_message.text = "/system_stats"
            result = await registry.dispatch(mock_message, mock_bot)
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_handler(self, mock_bot, mock_message):
        """Test health_check command handler."""
        registry = CommandRegistry()

        registry.register_advanced_admin(mock_bot)

        with patch("ttskit.metrics.advanced.get_metrics_collector") as mock_metrics:
            mock_collector = Mock()
            mock_metrics.return_value = mock_collector
            mock_collector.get_comprehensive_metrics = AsyncMock(
                return_value={
                    "requests": {"success_rate": 95.0},
                    "performance": {"avg_response_time": 1.5},
                    "system": {"cpu_percent": 50.0, "memory_percent": 60.0},
                    "health": 85.0,
                }
            )

            mock_message.text = "/health_check"
            result = await registry.dispatch(mock_message, mock_bot)
            assert result is True

    @pytest.mark.asyncio
    async def test_performance_handler(self, mock_bot, mock_message):
        """Test performance command handler."""
        registry = CommandRegistry()

        registry.register_advanced_admin(mock_bot)

        with patch("ttskit.metrics.advanced.get_metrics_collector") as mock_metrics:
            mock_collector = Mock()
            mock_metrics.return_value = mock_collector
            mock_collector.get_engine_comparison = AsyncMock(
                return_value={
                    "edge": {
                        "requests": 50,
                        "success_rate": 98.0,
                        "avg_response_time": 1.5,
                        "reliability_score": 95.0,
                        "performance_score": 90.0,
                    }
                }
            )

            mock_message.text = "/performance"
            result = await registry.dispatch(mock_message, mock_bot)
            assert result is True

    @pytest.mark.asyncio
    async def test_monitor_handler(self, mock_bot, mock_message):
        """Test monitor command handler."""
        registry = CommandRegistry()

        registry.register_advanced_admin(mock_bot)

        with patch("ttskit.metrics.advanced.get_metrics_collector") as mock_metrics:
            mock_collector = Mock()
            mock_metrics.return_value = mock_collector
            mock_collector.get_comprehensive_metrics = AsyncMock(
                return_value={
                    "requests": {
                        "total": 100,
                        "per_minute": 10.0,
                        "success_rate": 95.0,
                    },
                    "system": {"cpu_percent": 50.0, "memory_percent": 60.0},
                    "health": 85.0,
                }
            )

            mock_message.text = "/monitor"
            result = await registry.dispatch(mock_message, mock_bot)
            assert result is True

    @pytest.mark.asyncio
    async def test_export_metrics_handler(self, mock_bot, mock_message):
        """Test export_metrics command handler."""
        registry = CommandRegistry()

        registry.register_advanced_admin(mock_bot)

        with patch("ttskit.metrics.advanced.get_metrics_collector") as mock_metrics:
            mock_collector = Mock()
            mock_metrics.return_value = mock_collector
            mock_collector.export_metrics = AsyncMock(return_value=True)

            mock_message.text = "/export_metrics"
            result = await registry.dispatch(mock_message, mock_bot)
            assert result is True

    @pytest.mark.asyncio
    async def test_clear_cache_handler(self, mock_bot, mock_message):
        """Test clear_cache command handler."""
        registry = CommandRegistry()

        registry.register_advanced_admin(mock_bot)

        mock_message.text = "/clear_cache"
        result = await registry.dispatch(mock_message, mock_bot)
        assert result is True

    @pytest.mark.asyncio
    async def test_restart_handler(self, mock_bot, mock_message):
        """Test restart command handler."""
        registry = CommandRegistry()

        registry.register_advanced_admin(mock_bot)

        mock_message.text = "/restart"
        with (
            patch("os.execv") as mock_execv,
            patch("asyncio.sleep", new=AsyncMock(return_value=None)),
        ):
            mock_execv.return_value = None
            result = await registry.dispatch(mock_message, mock_bot)
            assert result is True

    @pytest.mark.asyncio
    async def test_debug_handler(self, mock_bot, mock_message):
        """Test debug command handler."""
        registry = CommandRegistry()

        registry.register_advanced_admin(mock_bot)

        with (
            patch("platform.platform") as mock_platform_platform,
            patch("platform.python_version") as mock_python_version,
            patch("platform.architecture") as mock_architecture,
            patch("platform.processor") as mock_processor,
            patch("platform.node") as mock_node,
            patch("psutil.virtual_memory") as mock_virtual_memory,
            patch("psutil.disk_usage") as mock_disk_usage,
        ):
            mock_platform_platform.return_value = "Linux-5.4.0"
            mock_python_version.return_value = "3.11.0"
            mock_architecture.return_value = ("64bit", "ELF")
            mock_processor.return_value = "x86_64"
            mock_node.return_value = "test-host"

            mock_memory = Mock()
            mock_memory.total = 8589934592
            mock_memory.available = 4294967296
            mock_memory.used = 4294967296
            mock_memory.percent = 50.0
            mock_virtual_memory.return_value = mock_memory

            mock_disk = Mock()
            mock_disk.total = 107374182400
            mock_disk.used = 53687091200
            mock_disk.free = 53687091200
            mock_disk.percent = 50.0
            mock_disk_usage.return_value = mock_disk

            mock_message.text = "/debug"
            result = await registry.dispatch(mock_message, mock_bot)
            assert result is True

    @pytest.mark.asyncio
    async def test_test_engines_handler(self, mock_bot, mock_message):
        """Test test_engines command handler."""
        registry = CommandRegistry()

        registry.register_advanced_admin(mock_bot)

        mock_message.text = "/test_engines"
        result = await registry.dispatch(mock_message, mock_bot)
        assert result is True

    @pytest.mark.asyncio
    async def test_create_user_handler(self, mock_bot, mock_message):
        """Test create_user command handler."""
        registry = CommandRegistry()

        registry.register_advanced_admin(mock_bot)

        mock_message.text = "/create_user user_id:test_user username:Test User email:test@example.com admin:false"

        with (
            patch("ttskit.database.connection.get_session") as mock_session,
            patch("ttskit.services.user_service.UserService") as mock_user_service,
        ):
            mock_db_session = Mock()
            mock_session.return_value.__next__ = Mock(return_value=mock_db_session)

            mock_service_instance = Mock()
            mock_user_service.return_value = mock_service_instance
            mock_service_instance.create_user = AsyncMock(
                return_value=Mock(user_id="test_user")
            )

            result = await registry.dispatch(mock_message, mock_bot)
            assert result is True

    @pytest.mark.asyncio
    async def test_delete_user_handler(self, mock_bot, mock_message):
        """Test delete_user command handler."""
        registry = CommandRegistry()

        registry.register_advanced_admin(mock_bot)

        mock_message.text = "/delete_user user_id:test_user"

        with (
            patch("ttskit.database.connection.get_session") as mock_session,
            patch("ttskit.services.user_service.UserService") as mock_user_service,
        ):
            mock_db_session = Mock()
            mock_session.return_value.__next__ = Mock(return_value=mock_db_session)

            mock_service_instance = Mock()
            mock_user_service.return_value = mock_service_instance
            mock_service_instance.get_user_by_id = AsyncMock(
                return_value=Mock(user_id="test_user")
            )

            result = await registry.dispatch(mock_message, mock_bot)
            assert result is True

    @pytest.mark.asyncio
    async def test_list_users_handler(self, mock_bot, mock_message):
        """Test list_users command handler."""
        registry = CommandRegistry()

        registry.register_advanced_admin(mock_bot)

        with (
            patch("ttskit.database.connection.get_session") as mock_session,
            patch("ttskit.services.user_service.UserService") as mock_user_service,
        ):
            mock_db_session = Mock()
            mock_session.return_value.__next__ = Mock(return_value=mock_db_session)

            mock_service_instance = Mock()
            mock_user_service.return_value = mock_service_instance
            mock_service_instance.get_all_users = AsyncMock(return_value=[])

            mock_message.text = "/list_users"
            result = await registry.dispatch(mock_message, mock_bot)
            assert result is True
