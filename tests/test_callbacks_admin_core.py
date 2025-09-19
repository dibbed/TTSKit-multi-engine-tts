"""
Core admin callback tests for full coverage of callbacks.py.

This file focuses on lightweight paths without heavy dependencies:
- register_admin with bot instance
- dispatch_admin various branches
- admin_stats/admin_cache/admin_performance/admin_health (with mocked metrics)
- admin_keys (both edit_message_text and send_message branches)
- admin_settings/admin_test/admin_back
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from ttskit.bot.callbacks import CallbackRegistry


def _make_bot() -> MagicMock:
    """
    Creates a mocked bot instance for testing admin callbacks.

    Returns:
        MagicMock: A bot mock with adapter, awaitable, and sudo configurations.
    """
    bot = MagicMock()
    bot.adapter = MagicMock()
    bot.adapter.send_message = AsyncMock()
    bot.adapter.edit_message_text = AsyncMock()
    bot.awaitable = MagicMock(side_effect=lambda f: f)
    bot.is_sudo = Mock(return_value=True)
    bot.sudo_users = {"111"}
    return bot


def _make_message(with_reply_markup: bool = False) -> MagicMock:
    """
    Creates a mocked message object for callback dispatch tests.

    Parameters:
        with_reply_markup: Whether to include a reply markup in the message.

    Returns:
        MagicMock: A message mock with chat, user, and optional reply markup.
    """
    msg = MagicMock()
    msg.chat_id = 42
    msg.message_id = 777
    user = MagicMock()
    user.id = 111
    msg.user = user
    if with_reply_markup:
        msg.reply_markup = object()
    return msg


class TestRegisterAndDispatchAdmin:
    """
    Tests admin callback registration and dispatch logic.
    """

    def test_register_admin_with_bot_instance_registers_defaults(self):
        """
        Verifies that register_admin with a bot instance registers default admin callbacks.
        """
        registry = CallbackRegistry()
        registry.register_admin(_make_bot())
        for key in [
            "admin_",
            "admin_callback",
            "admin_stats",
            "admin_health",
            "list_keys",
        ]:
            assert key in registry.admin_callbacks
            assert key in registry.callbacks

    @pytest.mark.asyncio
    async def test_dispatch_admin_sudo_and_non_sudo(self):
        """
        Tests dispatch_admin for both sudo and non-sudo users.

        Notes:
            Sudo dispatch succeeds and increments call count; non-sudo fails without calling handler.
        """
        registry = CallbackRegistry()
        called = {"count": 0}

        async def h(bot, m, d):
            called["count"] += 1

        registry._admin_handlers = {"admin:x": h}

        bot = _make_bot()
        msg = _make_message()

        ok = await registry.dispatch_admin(bot, msg, "admin:x:doit", is_sudo=True)
        assert ok is True and called["count"] == 1

        ok2 = await registry.dispatch_admin(bot, msg, "admin:x:doit", is_sudo=False)
        assert ok2 is False and called["count"] == 1

    @pytest.mark.asyncio
    async def test_dispatch_admin_unknown(self):
        """
        Verifies that dispatch_admin returns False for unknown admin callbacks.
        """
        registry = CallbackRegistry()
        bot = _make_bot()
        msg = _make_message()
        ok = await registry.dispatch_admin(bot, msg, "admin:unknown", is_sudo=True)
        assert ok is False


class TestAdminSimpleCallbacks:
    """
    Tests simple admin callback handlers like keys, settings, and navigation.
    """

    @pytest.mark.asyncio
    async def test_admin_keys_callback_edit_and_send(self):
        """
        Tests admin_keys callback handles both message editing (with reply markup) and sending (without).

        Notes:
            Uses awaitable to wrap adapter calls; distinguishes based on message type.
        """
        registry = CallbackRegistry()
        bot = _make_bot()
        registry.register_admin(bot)

        msg_with_reply = _make_message(with_reply_markup=True)
        handler = registry.admin_callbacks["admin_keys"]
        await handler(bot, msg_with_reply, "admin_keys")
        bot.awaitable.assert_called()
        first_called_fn = bot.awaitable.call_args_list[0].args[0]
        assert first_called_fn is bot.adapter.edit_message_text

        bot.adapter.edit_message_text.reset_mock()
        from types import SimpleNamespace

        user = SimpleNamespace(id=111)
        msg_plain = SimpleNamespace(chat_id=42, message_id=778, user=user)
        await handler(bot, msg_plain, "admin_keys")
        assert bot.awaitable.call_args_list[-1].args[0] is bot.adapter.send_message

    @pytest.mark.asyncio
    async def test_admin_settings_and_test_and_back(self):
        """
        Verifies that admin_settings, admin_test, and admin_back callbacks dispatch successfully.
        """
        registry = CallbackRegistry()
        bot = _make_bot()
        registry.register_admin(bot)
        msg = _make_message()

        for data in ["admin_settings", "admin_test", "admin_back"]:
            ok = await registry.dispatch(bot, msg, data)
            assert ok is True

    @pytest.mark.asyncio
    async def test_admin_callback_triggers_admin_clear_inner(self):
        """
        Tests direct execution of admin_callback to cover the inner admin_clear functionality.
        """
        registry = CallbackRegistry()
        bot = _make_bot()
        registry.register_admin(bot)
        msg = _make_message()
        ok = await registry.dispatch(bot, msg, "admin_callback")
        assert ok is True


class TestAdminMetricsCallbacks:
    """
    Tests admin callbacks for metrics, cache, performance, and health reporting.
    """

    @pytest.mark.asyncio
    async def test_admin_stats_success_and_error(self):
        """
        Tests admin_stats callback with successful metrics retrieval and error handling.

        Notes:
            Mocks get_metrics_collector; asserts dispatch succeeds in both cases.
        """
        registry = CallbackRegistry()
        bot = _make_bot()
        registry.register_admin(bot)
        msg = _make_message()

        with patch("ttskit.metrics.advanced.get_metrics_collector") as mock_get:
            collector = MagicMock()
            mock_get.return_value = collector
            collector.get_comprehensive_metrics = AsyncMock(
                return_value={
                    "requests": {
                        "total": 10,
                        "successful": 9,
                        "failed": 1,
                        "success_rate": 90.0,
                        "per_minute": 1.0,
                    },
                    "engines": {"edge": {"total_requests": 5, "success_rate": 95.0}},
                    "cache": {"hit_rate": 80.0, "size_mb": 12.3, "evictions": 0},
                    "performance": {"avg_response_time": 1.2, "p95_response_time": 2.1},
                    "system": {
                        "cpu_percent": 10.0,
                        "memory_mb": 256.0,
                        "memory_percent": 30.0,
                    },
                    "health": 75.0,
                }
            )
            ok = await registry.dispatch(bot, msg, "admin_stats")
            assert ok is True

        with patch(
            "ttskit.metrics.advanced.get_metrics_collector",
            side_effect=Exception("boom"),
        ):
            ok2 = await registry.dispatch(bot, msg, "admin_stats")
            assert ok2 is True

    @pytest.mark.asyncio
    async def test_admin_cache_success_and_error(self):
        """
        Tests admin_cache callback with successful cache metrics and error fallback.
        """
        registry = CallbackRegistry()
        bot = _make_bot()
        registry.register_admin(bot)
        msg = _make_message()

        with patch("ttskit.metrics.advanced.get_metrics_collector") as mock_get:
            collector = MagicMock()
            mock_get.return_value = collector
            collector.get_comprehensive_metrics = AsyncMock(
                return_value={
                    "cache": {
                        "hit_rate": 87.0,
                        "total_hits": 100,
                        "total_misses": 15,
                        "size_mb": 33.0,
                        "evictions": 2,
                    }
                }
            )
            ok = await registry.dispatch(bot, msg, "admin_cache")
            assert ok is True

        with patch(
            "ttskit.metrics.advanced.get_metrics_collector",
            side_effect=Exception("err"),
        ):
            ok2 = await registry.dispatch(bot, msg, "admin_cache")
            assert ok2 is True

    @pytest.mark.asyncio
    async def test_admin_performance_success_and_error(self):
        """
        Tests admin_performance callback for engine comparison metrics and errors.
        """
        registry = CallbackRegistry()
        bot = _make_bot()
        registry.register_admin(bot)
        msg = _make_message()

        with patch("ttskit.metrics.advanced.get_metrics_collector") as mock_get:
            collector = MagicMock()
            mock_get.return_value = collector
            collector.get_engine_comparison = AsyncMock(
                return_value={
                    "edge": {
                        "requests": 5,
                        "success_rate": 90.0,
                        "avg_response_time": 1.1,
                        "reliability_score": 80.0,
                        "performance_score": 85.0,
                    }
                }
            )
            ok = await registry.dispatch(bot, msg, "admin_performance")
            assert ok is True

        with patch(
            "ttskit.metrics.advanced.get_metrics_collector",
            side_effect=Exception("err"),
        ):
            ok2 = await registry.dispatch(bot, msg, "admin_performance")
            assert ok2 is True

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "health, cpu, mem, success, avg_resp",
        [
            (95.0, 10.0, 10.0, 99.0, 0.5),
            (80.0, 85.0, 10.0, 99.0, 0.5),
            (60.0, 10.0, 85.0, 99.0, 0.5),
            (40.0, 10.0, 10.0, 90.0, 6.0),
        ],
    )
    async def test_admin_health_various_statuses(
        self, health, cpu, mem, success, avg_resp
    ):
        """
        Tests admin_health callback across various system health scenarios.

        Parameters:
            health: Overall health score (float).
            cpu: CPU usage percentage.
            mem: Memory usage percentage.
            success: Request success rate.
            avg_resp: Average response time.

        Notes:
            Covers healthy, high-CPU, high-memory, and degraded performance cases.
        """
        registry = CallbackRegistry()
        bot = _make_bot()
        registry.register_admin(bot)
        msg = _make_message()

        with patch("ttskit.metrics.advanced.get_metrics_collector") as mock_get:
            collector = MagicMock()
            mock_get.return_value = collector
            collector.get_comprehensive_metrics = AsyncMock(
                return_value={
                    "requests": {"success_rate": success},
                    "performance": {"avg_response_time": avg_resp},
                    "system": {"cpu_percent": cpu, "memory_percent": mem},
                    "health": health,
                }
            )
            ok = await registry.dispatch(bot, msg, "admin_health")
            assert ok is True
