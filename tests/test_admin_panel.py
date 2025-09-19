"""
Test cases for admin panel functionality.

This module tests the CallbackRegistry and admin panel functionality
that was migrated from admin_panel.py to callbacks.py.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from ttskit.bot.callbacks import CallbackRegistry


class TestCallbackRegistry:
    """Test CallbackRegistry class."""

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

    def test_register_bulk(self):
        """Test bulk callback registration."""
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


class TestCallbackRegistryIntegration:
    """Test CallbackRegistry integration with bot."""

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

    @pytest.mark.asyncio
    async def test_dispatch_non_admin_callback(self, callback_registry, mock_bot):
        """Test non-admin user trying to access admin callback."""

        async def admin_handler(bot, message, data):
            return "admin_result"

        callback_registry.register_callback("admin_", admin_handler, admin_only=True)

        message = Mock()
        message.user = Mock()
        message.user.id = 999999999

        mock_bot.is_sudo = Mock(return_value=False)

        result = await callback_registry.dispatch(mock_bot, message, "admin_data")
        assert result is False


class TestCallbackRegistryDefaultRegistration:
    """Test default callback registration."""

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


class TestAdminCallbackHandlers:
    """Test admin callback handlers."""

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
    def mock_message(self):
        """Create mock message for testing."""
        message = Mock()
        message.user = Mock()
        message.user.id = 123456789
        message.chat_id = 123456789
        return message

    @pytest.mark.asyncio
    async def test_admin_stats_callback(self, mock_bot, mock_message):
        """Test admin_stats callback handler."""
        registry = CallbackRegistry()

        registry.register_admin(mock_bot)

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
                    "performance": {"avg_response_time": 1.5, "p95_response_time": 2.0},
                    "system": {
                        "cpu_percent": 50.0,
                        "memory_mb": 512.0,
                        "memory_percent": 60.0,
                    },
                    "health": 85.0,
                }
            )

            result = await registry.dispatch(mock_bot, mock_message, "admin_stats")
            assert result is True

    @pytest.mark.asyncio
    async def test_admin_keys_callback(self, mock_bot, mock_message):
        """Test admin_keys callback handler."""
        registry = CallbackRegistry()

        registry.register_admin(mock_bot)

        result = await registry.dispatch(mock_bot, mock_message, "admin_keys")
        assert result is True

    @pytest.mark.asyncio
    async def test_admin_settings_callback(self, mock_bot, mock_message):
        """Test admin_settings callback handler."""
        registry = CallbackRegistry()

        registry.register_admin(mock_bot)

        result = await registry.dispatch(mock_bot, mock_message, "admin_settings")
        assert result is True

    @pytest.mark.asyncio
    async def test_admin_cache_callback(self, mock_bot, mock_message):
        """Test admin_cache callback handler."""
        registry = CallbackRegistry()

        registry.register_admin(mock_bot)

        with patch("ttskit.metrics.advanced.get_metrics_collector") as mock_metrics:
            mock_collector = Mock()
            mock_metrics.return_value = mock_collector
            mock_collector.get_comprehensive_metrics = AsyncMock(
                return_value={
                    "cache": {
                        "hit_rate": 85.0,
                        "total_hits": 1000,
                        "total_misses": 200,
                        "size_mb": 100.0,
                        "evictions": 10,
                    }
                }
            )

            result = await registry.dispatch(mock_bot, mock_message, "admin_cache")
            assert result is True

    @pytest.mark.asyncio
    async def test_admin_test_callback(self, mock_bot, mock_message):
        """Test admin_test callback handler."""
        registry = CallbackRegistry()

        registry.register_admin(mock_bot)

        result = await registry.dispatch(mock_bot, mock_message, "admin_test")
        assert result is True

    @pytest.mark.asyncio
    async def test_admin_performance_callback(self, mock_bot, mock_message):
        """Test admin_performance callback handler."""
        registry = CallbackRegistry()

        registry.register_admin(mock_bot)

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

            result = await registry.dispatch(
                mock_bot, mock_message, "admin_performance"
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_admin_health_callback(self, mock_bot, mock_message):
        """Test admin_health callback handler."""
        registry = CallbackRegistry()

        registry.register_admin(mock_bot)

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

            result = await registry.dispatch(mock_bot, mock_message, "admin_health")
            assert result is True

    @pytest.mark.asyncio
    async def test_admin_back_callback(self, mock_bot, mock_message):
        """Test admin_back callback handler."""
        registry = CallbackRegistry()

        registry.register_admin(mock_bot)

        result = await registry.dispatch(mock_bot, mock_message, "admin_back")
        assert result is True
