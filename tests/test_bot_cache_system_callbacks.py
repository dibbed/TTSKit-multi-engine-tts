"""Tests for cache/system/test-engine callbacks in ttskit.bot.callbacks.

Covers:
- clear_cache_callback
- confirm_clear_cache_callback
- cancel_clear_cache_callback
- confirm_restart_callback
- cancel_restart_callback
- test_all_engines_callback
- test_edge_callback
- test_piper_callback
- test_gtts_callback
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

import ttskit.bot.callbacks as cb


def make_mock_bot() -> Mock:
    bot = Mock()
    bot.adapter = Mock()
    bot.adapter.send_message = AsyncMock()
    bot.awaitable = Mock(side_effect=lambda f: f)
    return bot


def make_mock_message(chat_id: int = 333) -> Mock:
    message = Mock()
    message.chat_id = chat_id
    return message


@pytest.mark.asyncio
async def test_clear_cache_callback_sends_confirmation_prompt():
    bot = make_mock_bot()
    msg = make_mock_message()
    with patch(
        "ttskit.bot.callbacks.t", return_value="confirm_clear_cache_prompt"
    ) as pt:
        await cb.clear_cache_callback(bot, msg, "clear_cache")
        pt.assert_called_once()
        bot.adapter.send_message.assert_awaited_once_with(
            msg.chat_id, "confirm_clear_cache_prompt"
        )


@pytest.mark.asyncio
async def test_confirm_clear_cache_callback_success_path():
    bot = make_mock_bot()
    msg = make_mock_message()
    with patch("ttskit.bot.callbacks.t", return_value="cache_cleared_text") as pt:
        await cb.confirm_clear_cache_callback(bot, msg, "confirm_clear_cache")
        pt.assert_called_once()
        bot.adapter.send_message.assert_awaited_once_with(
            msg.chat_id, "cache_cleared_text"
        )


@pytest.mark.asyncio
async def test_confirm_clear_cache_callback_error_path():
    bot = make_mock_bot()
    msg = make_mock_message()

    with patch(
        "ttskit.bot.callbacks.t", side_effect=["cache_cleared", "err_text"]
    ) as pt:
        bot.adapter.send_message = AsyncMock(side_effect=[Exception("e"), None])

        await cb.confirm_clear_cache_callback(bot, msg, "confirm_clear_cache")

        assert bot.adapter.send_message.await_count == 2
        last_call = bot.adapter.send_message.await_args_list[-1]
        assert last_call.kwargs == {}


@pytest.mark.asyncio
async def test_cancel_clear_cache_callback():
    bot = make_mock_bot()
    msg = make_mock_message()
    with patch("ttskit.bot.callbacks.t", return_value="cancelled_text") as pt:
        await cb.cancel_clear_cache_callback(bot, msg, "cancel_clear_cache")
        pt.assert_called_once()
        bot.adapter.send_message.assert_awaited_once_with(msg.chat_id, "cancelled_text")


@pytest.mark.asyncio
async def test_confirm_restart_callback_success():
    bot = make_mock_bot()
    msg = make_mock_message()
    with patch(
        "ttskit.bot.callbacks.t", side_effect=["restarting", "restart_complete"]
    ) as pt:
        await cb.confirm_restart_callback(bot, msg, "confirm_restart")
        assert bot.adapter.send_message.await_count == 2


@pytest.mark.asyncio
async def test_confirm_restart_callback_error():
    bot = make_mock_bot()
    msg = make_mock_message()
    with patch("ttskit.bot.callbacks.t", return_value="error_restart_text") as pt:
        bot.adapter.send_message = AsyncMock(side_effect=[Exception("boom"), None])
        await cb.confirm_restart_callback(bot, msg, "confirm_restart")
        assert bot.adapter.send_message.await_count == 2


@pytest.mark.asyncio
async def test_cancel_restart_callback():
    bot = make_mock_bot()
    msg = make_mock_message()
    with patch("ttskit.bot.callbacks.t", return_value="cancel_delete_text") as pt:
        await cb.cancel_restart_callback(bot, msg, "cancel_restart")
        pt.assert_called_once()
        bot.adapter.send_message.assert_awaited_once_with(
            msg.chat_id, "cancel_delete_text"
        )


@pytest.mark.asyncio
async def test_test_all_engines_callback_happy_path():
    bot = make_mock_bot()
    msg = make_mock_message()
    with patch("ttskit.bot.callbacks.t") as pt:
        pt.side_effect = [
            "testing_all_engines_progress",
            "engine_test_results_with_list_text",
        ]
        with patch("asyncio.sleep", new=AsyncioFastSleep()):
            await cb.test_all_engines_callback(bot, msg, "test_all_engines")

        assert bot.adapter.send_message.await_count == 2


class AsyncioFastSleep:
    def __call__(self, *args, **kwargs):
        async def _noop():
            return None

        return _noop()


@pytest.mark.asyncio
async def test_single_engine_callbacks():
    bot = make_mock_bot()
    msg = make_mock_message()
    with patch("ttskit.bot.callbacks.t") as pt:
        pt.side_effect = [
            "progress_edge",
            "complete_edge",
            "progress_piper",
            "complete_piper",
            "progress_gtts",
            "complete_gtts",
        ]

        await cb.test_edge_callback(bot, msg, "test_edge")
        await cb.test_piper_callback(bot, msg, "test_piper")
        await cb.test_gtts_callback(bot, msg, "test_gtts")

        assert bot.adapter.send_message.await_count == 6
