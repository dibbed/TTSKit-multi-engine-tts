"""Complete coverage tests for ttskit.bot.callbacks.

This file covers all remaining functions and branches to achieve 100% coverage.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

import ttskit.bot.callbacks as cb


def make_mock_bot() -> Mock:
    bot = Mock()
    bot.adapter = Mock()
    bot.adapter.send_message = AsyncMock()
    bot.adapter.edit_message_text = AsyncMock()
    bot.awaitable = Mock(side_effect=lambda f: f)
    bot.is_sudo = Mock(return_value=True)
    bot.sudo_users = {"12345"}
    bot.cache_enabled = True
    bot.audio_processing = True
    return bot


def make_mock_message(user_id: int = 12345, chat_id: int = 12345) -> Mock:
    message = Mock()
    message.user = Mock()
    message.user.id = user_id
    message.chat_id = chat_id
    message.message_id = 1
    message.reply_markup = None
    return message


class TestCallbackRegistryComplete:
    """Test CallbackRegistry for complete coverage."""

    def test_callback_registry_init(self):
        """Test CallbackRegistry initialization."""
        registry = cb.CallbackRegistry()
        assert isinstance(registry._handlers, dict)
        assert isinstance(registry._admin_handlers, dict)

    def test_register_method(self):
        """Test register method."""
        registry = cb.CallbackRegistry()

        async def handler(bot, message, data):
            return "test"

        registry.register("test_", handler)
        assert "test_" in registry._handlers
        assert registry._handlers["test_"] == handler

    def test_register_callback_admin_only_true(self):
        """Test register_callback with admin_only=True."""
        registry = cb.CallbackRegistry()

        async def admin_handler(bot, message, data):
            return "admin"

        registry.register_callback("admin_", admin_handler, admin_only=True)
        assert "admin_" in registry._handlers
        assert "admin_" in registry._admin_handlers

    def test_register_callback_admin_only_false(self):
        """Test register_callback with admin_only=False."""
        registry = cb.CallbackRegistry()

        async def normal_handler(bot, message, data):
            return "normal"

        registry.register_callback("normal_", normal_handler, admin_only=False)
        assert "normal_" in registry._handlers
        assert "normal_" not in registry._admin_handlers

    def test_register_admin_with_bot_instance(self):
        """Test register_admin with bot instance (default admin callbacks)."""
        registry = cb.CallbackRegistry()
        mock_bot = Mock()

        registry.register_admin(mock_bot)

        assert "admin_stats" in registry._admin_handlers
        assert "admin_keys" in registry._admin_handlers
        assert "create_key_user" in registry._admin_handlers

    def test_register_admin_with_string_prefix(self):
        """Test register_admin with string prefix and handler."""
        registry = cb.CallbackRegistry()

        async def test_handler(bot, message, data):
            return "test"

        registry.register_admin("test_admin_", test_handler)
        assert "test_admin_" in registry._admin_handlers

    def test_register_admin_with_non_string_prefix(self):
        """Test register_admin with non-string prefix (should not register)."""
        registry = cb.CallbackRegistry()

        async def test_handler(bot, message, data):
            return "test"

        registry.register_admin(123, test_handler)
        assert len(registry._admin_handlers) == 0

    def test_register_admin_with_none_handler(self):
        """Test register_admin with None handler (should not register)."""
        registry = cb.CallbackRegistry()

        registry.register_admin("test_admin_", None)
        assert len(registry._admin_handlers) == 0

    def test_register_bulk(self):
        """Test register_bulk method."""
        registry = cb.CallbackRegistry()

        async def handler1(bot, message, data):
            return "handler1"

        async def handler2(bot, message, data):
            return "handler2"

        handlers = {"test1_": handler1, "test2_": handler2}
        registry.register_bulk(handlers)

        assert "test1_" in registry._handlers
        assert "test2_" in registry._handlers

    @pytest.mark.asyncio
    async def test_dispatch_success(self):
        """Test successful dispatch."""
        registry = cb.CallbackRegistry()
        bot = make_mock_bot()
        message = make_mock_message()

        async def test_handler(bot, message, data):
            return "success"

        registry.register("test_", test_handler)

        result = await registry.dispatch(bot, message, "test_data")
        assert result is True

    @pytest.mark.asyncio
    async def test_dispatch_admin_callback_sudo_user(self):
        """Test dispatch admin callback for sudo user."""
        registry = cb.CallbackRegistry()
        bot = make_mock_bot()
        message = make_mock_message()

        async def admin_handler(bot, message, data):
            return "admin"

        registry.register_callback("admin_", admin_handler, admin_only=True)

        result = await registry.dispatch(bot, message, "admin_data")
        assert result is True

    @pytest.mark.asyncio
    async def test_dispatch_admin_callback_non_sudo_user(self):
        """Test dispatch admin callback for non-sudo user."""
        registry = cb.CallbackRegistry()
        bot = make_mock_bot()
        bot.is_sudo = Mock(return_value=False)
        message = make_mock_message()

        async def admin_handler(bot, message, data):
            return "admin"

        registry.register_callback("admin_", admin_handler, admin_only=True)

        result = await registry.dispatch(bot, message, "admin_data")
        assert result is False

    @pytest.mark.asyncio
    async def test_dispatch_admin_callback_exception(self):
        """Test dispatch admin callback with exception."""
        registry = cb.CallbackRegistry()
        bot = make_mock_bot()
        bot.is_sudo = Mock(side_effect=Exception("Error"))

        message = make_mock_message()

        async def admin_handler(bot, message, data):
            return "admin"

        registry.register_callback("admin_", admin_handler, admin_only=True)

        result = await registry.dispatch(bot, message, "admin_data")
        assert result is False

    @pytest.mark.asyncio
    async def test_dispatch_not_found(self):
        """Test dispatch when callback not found."""
        registry = cb.CallbackRegistry()
        bot = make_mock_bot()
        message = make_mock_message()

        result = await registry.dispatch(bot, message, "unknown_callback")
        assert result is False

    @pytest.mark.asyncio
    async def test_dispatch_admin_method(self):
        """Test dispatch_admin method."""
        registry = cb.CallbackRegistry()
        bot = make_mock_bot()
        message = make_mock_message()

        async def admin_handler(bot, message, data):
            return "admin"

        registry._admin_handlers["admin_"] = admin_handler

        result = await registry.dispatch_admin(bot, message, "admin_data", is_sudo=True)
        assert result is True

    @pytest.mark.asyncio
    async def test_dispatch_admin_method_non_sudo(self):
        """Test dispatch_admin method with non-sudo user."""
        registry = cb.CallbackRegistry()
        bot = make_mock_bot()
        message = make_mock_message()

        result = await registry.dispatch_admin(
            bot, message, "admin_data", is_sudo=False
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_dispatch_admin_method_not_found(self):
        """Test dispatch_admin method when callback not found."""
        registry = cb.CallbackRegistry()
        bot = make_mock_bot()
        message = make_mock_message()

        result = await registry.dispatch_admin(
            bot, message, "unknown_admin", is_sudo=True
        )
        assert result is False

    def test_callbacks_property(self):
        """Test callbacks property."""
        registry = cb.CallbackRegistry()

        async def handler(bot, message, data):
            return "test"

        registry.register("test_", handler)

        callbacks = registry.callbacks
        assert "test_" in callbacks
        assert callbacks is not registry._handlers

    def test_admin_callbacks_property(self):
        """Test admin_callbacks property."""
        registry = cb.CallbackRegistry()

        async def admin_handler(bot, message, data):
            return "admin"

        registry.register_callback("admin_", admin_handler, admin_only=True)

        admin_callbacks = registry.admin_callbacks
        assert "admin_" in admin_callbacks
        assert admin_callbacks is not registry._admin_handlers


class TestDefaultCallbacks:
    """Test default callback registration and handlers."""

    @pytest.mark.asyncio
    async def test_register_default_engine_selection(self):
        """Test engine selection callback."""
        registry = cb.CallbackRegistry()
        bot = make_mock_bot()
        message = make_mock_message()

        registry.register_default(bot)

        with patch("ttskit.bot.callbacks.engines_registry") as mock_registry:
            mock_registry.registry.get_policy = Mock(return_value=["gtts", "edge"])
            mock_registry.registry.get_available_engines = Mock(
                return_value=["gtts", "edge", "piper"]
            )
            mock_registry.registry.set_policy = Mock()

            result = await registry.dispatch(bot, message, "engine_piper")
            assert result is True

    @pytest.mark.asyncio
    async def test_register_default_engine_selection_with_lang(self):
        """Test engine selection callback with forced language."""
        registry = cb.CallbackRegistry()
        bot = make_mock_bot()
        message = make_mock_message()

        registry.register_default(bot)

        with patch("ttskit.bot.callbacks.engines_registry") as mock_registry:
            mock_registry.registry.get_policy = Mock(return_value=["gtts"])
            mock_registry.registry.get_available_engines = Mock(
                return_value=["gtts", "edge"]
            )
            mock_registry.registry.set_policy = Mock()

            result = await registry.dispatch(bot, message, "engine_edge:fa")
            assert result is True

    @pytest.mark.asyncio
    async def test_register_default_engine_selection_exception(self):
        """Test engine selection callback with exception."""
        registry = cb.CallbackRegistry()
        bot = make_mock_bot()
        message = make_mock_message()

        registry.register_default(bot)

        with patch("ttskit.bot.callbacks.engines_registry") as mock_registry:
            mock_registry.registry.get_policy = Mock(side_effect=Exception("Error"))

            result = await registry.dispatch(bot, message, "engine_edge")
            assert result is True

    @pytest.mark.asyncio
    async def test_register_default_settings_cache_on(self):
        """Test settings cache on callback."""
        registry = cb.CallbackRegistry()
        bot = make_mock_bot()
        message = make_mock_message()

        registry.register_default(bot)

        result = await registry.dispatch(bot, message, "settings_cache_on")
        assert result is True
        assert bot.cache_enabled is True

    @pytest.mark.asyncio
    async def test_register_default_settings_cache_off(self):
        """Test settings cache off callback."""
        registry = cb.CallbackRegistry()
        bot = make_mock_bot()
        message = make_mock_message()

        registry.register_default(bot)

        result = await registry.dispatch(bot, message, "settings_cache_off")
        assert result is True
        assert bot.cache_enabled is False

    @pytest.mark.asyncio
    async def test_register_default_settings_audio_on(self):
        """Test settings audio on callback."""
        registry = cb.CallbackRegistry()
        bot = make_mock_bot()
        message = make_mock_message()

        registry.register_default(bot)

        result = await registry.dispatch(bot, message, "settings_audio_on")
        assert result is True
        assert bot.audio_processing is True

    @pytest.mark.asyncio
    async def test_register_default_settings_audio_off(self):
        """Test settings audio off callback."""
        registry = cb.CallbackRegistry()
        bot = make_mock_bot()
        message = make_mock_message()

        registry.register_default(bot)

        result = await registry.dispatch(bot, message, "settings_audio_off")
        assert result is True
        assert bot.audio_processing is False

    @pytest.mark.asyncio
    async def test_register_default_settings_unknown(self):
        """Test settings unknown callback."""
        registry = cb.CallbackRegistry()
        bot = make_mock_bot()
        message = make_mock_message()

        registry.register_default(bot)

        result = await registry.dispatch(bot, message, "settings_unknown")
        assert result is True

    @pytest.mark.asyncio
    async def test_register_default_settings_exception(self):
        """Test settings callback with exception."""
        registry = cb.CallbackRegistry()
        bot = make_mock_bot()
        bot.adapter.send_message = AsyncMock(side_effect=Exception("Error"))
        message = make_mock_message()

        registry.register_default(bot)

        result = await registry.dispatch(bot, message, "settings_cache_on")
        assert result is True


class TestStandaloneHandlers:
    """Test standalone callback handler functions."""

    @pytest.mark.asyncio
    async def test_handle_audio_callback(self):
        """Test handle_audio_callback function."""
        bot = make_mock_bot()
        message = make_mock_message()

        with patch("ttskit.bot.callbacks.CallbackRegistry") as mock_registry_class:
            mock_registry = Mock()
            mock_registry.dispatch = AsyncMock(return_value=True)
            mock_registry_class.return_value = mock_registry

            result = await cb.handle_audio_callback(bot, message, "engine_gtts")
            assert result is True

    @pytest.mark.asyncio
    async def test_handle_callback_query(self):
        """Test handle_callback_query function."""
        bot = make_mock_bot()
        message = make_mock_message()

        with patch("ttskit.bot.callbacks.CallbackRegistry") as mock_registry_class:
            mock_registry = Mock()
            mock_registry.dispatch = AsyncMock(return_value=False)
            mock_registry_class.return_value = mock_registry

            result = await cb.handle_callback_query(bot, message, "settings_cache_on")
            assert result is False

    @pytest.mark.asyncio
    async def test_handle_error_callback(self):
        """Test handle_error_callback function."""
        bot = make_mock_bot()
        message = make_mock_message()

        with patch(
            "ttskit.bot.callbacks.t", return_value="Error: test_error"
        ) as mock_t:
            await cb.handle_error_callback(bot, message, "test_error")
            mock_t.assert_called_once_with("error_prefix", error="test_error")

    @pytest.mark.asyncio
    async def test_handle_text_callback(self):
        """Test handle_text_callback function."""
        bot = make_mock_bot()
        message = make_mock_message()

        with patch(
            "ttskit.bot.callbacks.t", return_value="Text callback: test_data"
        ) as mock_t:
            await cb.handle_text_callback(bot, message, "test_data")
            mock_t.assert_called_once_with("text_callback", data="test_data")

    @pytest.mark.asyncio
    async def test_handle_voice_callback(self):
        """Test handle_voice_callback function."""
        bot = make_mock_bot()
        message = make_mock_message()

        with patch(
            "ttskit.bot.callbacks.t", return_value="Voice callback: voice_data"
        ) as mock_t:
            await cb.handle_voice_callback(bot, message, "voice_data")
            mock_t.assert_called_once_with("voice_callback", data="voice_data")


class TestAdminCallbacksComplete:
    """Test admin callback functions for complete coverage."""

    @pytest.mark.asyncio
    async def test_admin_stats_callback_success(self):
        """Test admin_stats_callback with successful metrics."""
        bot = make_mock_bot()
        message = make_mock_message()

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

            await cb.admin_stats_callback(bot, message, "admin_stats")
            bot.adapter.send_message.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_admin_stats_callback_exception(self):
        """Test admin_stats_callback with exception."""
        bot = make_mock_bot()
        message = make_mock_message()

        with patch(
            "ttskit.metrics.advanced.get_metrics_collector",
            side_effect=Exception("Error"),
        ):
            await cb.admin_stats_callback(bot, message, "admin_stats")
            bot.adapter.send_message.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_admin_keys_callback_with_reply_markup(self):
        """Test admin_keys_callback with reply_markup."""
        bot = make_mock_bot()
        message = make_mock_message()
        message.reply_markup = Mock()

        with patch("ttskit.bot.callbacks.t", return_value="admin_keys_menu"):
            await cb.admin_keys_callback(bot, message, "admin_keys")
            bot.adapter.edit_message_text.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_admin_keys_callback_without_reply_markup(self):
        """Test admin_keys_callback without reply_markup."""
        bot = make_mock_bot()
        message = make_mock_message()
        delattr(message, "reply_markup")

        with patch("ttskit.bot.callbacks.t", return_value="admin_keys_menu"):
            await cb.admin_keys_callback(bot, message, "admin_keys")
            bot.adapter.send_message.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_admin_settings_callback(self):
        """Test admin_settings_callback."""
        bot = make_mock_bot()
        message = make_mock_message()

        with (
            patch("ttskit.config.settings") as mock_settings,
            patch("ttskit.bot.callbacks.t", return_value="settings_text") as mock_t,
        ):
            mock_settings.api_rate_limit = 100
            mock_settings.max_text_length = 1000
            mock_settings.cache_ttl = 3600
            mock_settings.default_engine = "gtts"
            mock_settings.default_language = "en"
            mock_settings.audio_format = "mp3"
            mock_settings.cache_enabled = True
            mock_settings.cache_type = "memory"
            mock_settings.cache_max_size = 100

            await cb.admin_settings_callback(bot, message, "admin_settings")
            mock_t.assert_called_once()
            bot.adapter.send_message.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_admin_cache_callback_success(self):
        """Test admin_cache_callback with successful metrics."""
        bot = make_mock_bot()
        message = make_mock_message()

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

            await cb.admin_cache_callback(bot, message, "admin_cache")
            bot.adapter.send_message.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_admin_cache_callback_exception(self):
        """Test admin_cache_callback with exception."""
        bot = make_mock_bot()
        message = make_mock_message()

        with patch(
            "ttskit.metrics.advanced.get_metrics_collector",
            side_effect=Exception("Error"),
        ):
            await cb.admin_cache_callback(bot, message, "admin_cache")
            bot.adapter.send_message.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_admin_test_callback(self):
        """Test admin_test_callback."""
        bot = make_mock_bot()
        message = make_mock_message()

        with patch("ttskit.bot.callbacks.t", return_value="admin_test_menu"):
            await cb.admin_test_callback(bot, message, "admin_test")
            bot.adapter.send_message.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_admin_performance_callback_success(self):
        """Test admin_performance_callback with successful metrics."""
        bot = make_mock_bot()
        message = make_mock_message()

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

            await cb.admin_performance_callback(bot, message, "admin_performance")
            bot.adapter.send_message.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_admin_performance_callback_exception(self):
        """Test admin_performance_callback with exception."""
        bot = make_mock_bot()
        message = make_mock_message()

        with patch(
            "ttskit.metrics.advanced.get_metrics_collector",
            side_effect=Exception("Error"),
        ):
            await cb.admin_performance_callback(bot, message, "admin_performance")
            bot.adapter.send_message.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_admin_health_callback_high_health(self):
        """Test admin_health_callback with high health score."""
        bot = make_mock_bot()
        message = make_mock_message()

        with patch("ttskit.metrics.advanced.get_metrics_collector") as mock_metrics:
            mock_collector = Mock()
            mock_metrics.return_value = mock_collector
            mock_collector.get_comprehensive_metrics = AsyncMock(
                return_value={
                    "requests": {"success_rate": 98.0},
                    "performance": {"avg_response_time": 1.0},
                    "system": {"cpu_percent": 30.0, "memory_percent": 40.0},
                    "health": 95.0,
                }
            )

            await cb.admin_health_callback(bot, message, "admin_health")
            bot.adapter.send_message.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_admin_health_callback_medium_health(self):
        """Test admin_health_callback with medium health score."""
        bot = make_mock_bot()
        message = make_mock_message()

        with patch("ttskit.metrics.advanced.get_metrics_collector") as mock_metrics:
            mock_collector = Mock()
            mock_metrics.return_value = mock_collector
            mock_collector.get_comprehensive_metrics = AsyncMock(
                return_value={
                    "requests": {"success_rate": 80.0},
                    "performance": {"avg_response_time": 3.0},
                    "system": {"cpu_percent": 70.0, "memory_percent": 75.0},
                    "health": 60.0,
                }
            )

            await cb.admin_health_callback(bot, message, "admin_health")
            bot.adapter.send_message.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_admin_health_callback_low_health(self):
        """Test admin_health_callback with low health score."""
        bot = make_mock_bot()
        message = make_mock_message()

        with patch("ttskit.metrics.advanced.get_metrics_collector") as mock_metrics:
            mock_collector = Mock()
            mock_metrics.return_value = mock_collector
            mock_collector.get_comprehensive_metrics = AsyncMock(
                return_value={
                    "requests": {"success_rate": 70.0},
                    "performance": {"avg_response_time": 8.0},
                    "system": {"cpu_percent": 90.0, "memory_percent": 85.0},
                    "health": 30.0,
                }
            )

            await cb.admin_health_callback(bot, message, "admin_health")
            bot.adapter.send_message.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_admin_health_callback_exception(self):
        """Test admin_health_callback with exception."""
        bot = make_mock_bot()
        message = make_mock_message()

        with patch(
            "ttskit.metrics.advanced.get_metrics_collector",
            side_effect=Exception("Error"),
        ):
            await cb.admin_health_callback(bot, message, "admin_health")
            bot.adapter.send_message.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_admin_back_callback(self):
        """Test admin_back_callback."""
        bot = make_mock_bot()
        message = make_mock_message()

        with patch("ttskit.bot.callbacks.t", return_value="admin_back_menu"):
            await cb.admin_back_callback(bot, message, "admin_back")
            bot.adapter.send_message.assert_awaited_once()


class TestApiKeyCallbacksComplete:
    """Test API key callback functions for complete coverage."""

    @pytest.mark.asyncio
    async def test_create_key_callback(self):
        """Test create_key_callback."""
        bot = make_mock_bot()
        message = make_mock_message()

        with patch("ttskit.bot.callbacks.t", return_value="create_key_title"):
            await cb.create_key_callback(bot, message, "create_key")
            bot.adapter.send_message.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_list_keys_callback_success(self):
        """Test list_keys_callback with users."""
        bot = make_mock_bot()
        message = make_mock_message()

        with (
            patch("ttskit.database.connection.get_session") as mock_sess,
            patch("ttskit.services.user_service.UserService") as mock_usvc,
            patch("ttskit.bot.callbacks.t") as mock_t,
        ):
            db = Mock()
            mock_sess.return_value = iter([db])

            user_service = AsyncMock()
            user = Mock()
            user.user_id = "test_user"
            user_service.get_all_users = AsyncMock(return_value=[user])

            api_key = Mock()
            api_key.id = "key123"
            api_key.permissions = '["read", "write"]'
            api_key.created_at = Mock()
            api_key.created_at.strftime = Mock(return_value="2023-01-01 12:00")
            api_key.is_active = True
            user_service.get_user_api_keys = AsyncMock(return_value=[api_key])

            mock_usvc.return_value = user_service
            mock_t.side_effect = ["api_keys_list_header", "no_api_keys"]

            await cb.list_keys_callback(bot, message, "list_keys")
            bot.adapter.send_message.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_list_keys_callback_no_users(self):
        """Test list_keys_callback with no users."""
        bot = make_mock_bot()
        message = make_mock_message()

        with (
            patch("ttskit.database.connection.get_session") as mock_sess,
            patch("ttskit.services.user_service.UserService") as mock_usvc,
            patch("ttskit.bot.callbacks.t", return_value="no_api_keys") as mock_t,
        ):
            db = Mock()
            mock_sess.return_value = iter([db])

            user_service = AsyncMock()
            user_service.get_all_users = AsyncMock(return_value=[])
            mock_usvc.return_value = user_service

            await cb.list_keys_callback(bot, message, "list_keys")
            mock_t.assert_called_once_with("no_api_keys")
            bot.adapter.send_message.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_list_keys_callback_exception(self):
        """Test list_keys_callback with exception."""
        bot = make_mock_bot()
        message = make_mock_message()

        with (
            patch("ttskit.database.connection.get_session") as mock_sess,
            patch("ttskit.services.user_service.UserService") as mock_usvc,
        ):
            db = Mock()
            mock_sess.return_value = iter([db])

            user_service = AsyncMock()
            user_service.get_all_users = AsyncMock(side_effect=Exception("Error"))
            mock_usvc.return_value = user_service

            await cb.list_keys_callback(bot, message, "list_keys")
            bot.adapter.send_message.assert_awaited_once()
