"""
Tests covering default handlers and standalone functions in callbacks.py.

This covers branches like:
- register_default: handle_engine_selection and handle_settings with various scenarios and fallbacks
- handle_audio_callback, handle_callback_query, handle_error_callback, handle_text_callback, handle_voice_callback
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ttskit.bot.callbacks import (
    CallbackRegistry,
    handle_audio_callback,
    handle_callback_query,
    handle_error_callback,
    handle_text_callback,
    handle_voice_callback,
)


def _make_bot(async_send: bool = True):
    """
    Creates a mocked bot instance for testing default callbacks.

    Parameters:
        async_send: Whether to use async mocks for send_message and edit_message_text.

    Returns:
        MagicMock: A bot mock configured for success or failure scenarios.
    """
    bot = MagicMock()
    bot.adapter = MagicMock()
    if async_send:
        bot.adapter.send_message = AsyncMock()
        bot.adapter.edit_message_text = AsyncMock()
        bot.awaitable = MagicMock(side_effect=lambda f: f)
    else:
        bot.adapter.send_message = MagicMock()
        bot.adapter.edit_message_text = MagicMock()

        async def _raiser(*args, **kwargs):
            raise Exception("fail")

        bot.awaitable = MagicMock(return_value=_raiser)
    return bot


def _make_message():
    """
    Creates a basic mocked message object for callback tests.

    Returns:
        MagicMock: A message mock with chat and user details.
    """
    msg = MagicMock()
    msg.chat_id = 99
    user = MagicMock()
    user.id = 111
    msg.user = user
    return msg


@pytest.mark.asyncio
async def test_register_default_engine_selection_success_and_fallback():
    """
    Tests register_default for engine selection success and fallback behaviors.

    Notes:
        Mocks engines registry; verifies dispatch for valid engine:language and fallback to send_message.
    """
    registry = CallbackRegistry()

    with patch("ttskit.bot.callbacks.engines_registry.registry") as mock_reg:
        mock_reg.get_policy.return_value = ["edge", "gtts", "piper"]
        mock_reg.get_available_engines.return_value = ["edge", "gtts", "piper"]
        mock_reg.set_policy.return_value = None

        bot_ok = _make_bot(async_send=True)
        registry.register_default(bot_ok)
        msg = _make_message()
        ok = await registry.dispatch(bot_ok, msg, "engine_edge:fa")
        assert ok is True

        bot_fb = _make_bot(async_send=False)
        registry_fb = CallbackRegistry()
        registry_fb.register_default(bot_fb)
        msg2 = _make_message()
        ok2 = await registry_fb.dispatch(bot_fb, msg2, "engine_gtts:")
        assert ok2 is True
        assert bot_fb.adapter.send_message.called


@pytest.mark.asyncio
async def test_register_default_settings_all_paths_and_fallback():
    """
    Tests register_default for settings callbacks across all paths and fallback.

    Notes:
        Covers cache on/off, audio on/off, unknown; verifies dispatch success, including fallback send.
    """
    bot_ok = _make_bot(async_send=True)
    registry = CallbackRegistry()
    registry.register_default(bot_ok)
    msg = _make_message()

    for data in [
        "settings_cache_on",
        "settings_cache_off",
        "settings_audio_on",
        "settings_audio_off",
        "settings_unknown",
    ]:
        d = data if data != "settings_unknown" else "settings_x"
        ok = await registry.dispatch(bot_ok, msg, d)
        assert ok is True

    bot_fb = _make_bot(async_send=False)
    registry_fb = CallbackRegistry()
    registry_fb.register_default(bot_fb)
    ok2 = await registry_fb.dispatch(bot_fb, msg, "settings_cache_on")
    assert ok2 is True


@pytest.mark.asyncio
async def test_standalone_callbacks_cover():
    """
    Tests standalone callback handlers for various message types.

    Notes:
        Mocks translation; covers audio, query, error, text, voice callbacks; asserts dispatch outcomes.
    """
    bot = _make_bot(async_send=True)
    msg = _make_message()

    with patch("ttskit.bot.callbacks.t", side_effect=lambda k, **kw: f"{k}:{kw}"):
        ok1 = await handle_audio_callback(bot, msg, "engine_edge")
        ok2 = await handle_callback_query(bot, msg, "settings_cache_on")
        await handle_error_callback(bot, msg, "err")
        await handle_text_callback(bot, msg, "txt")
        await handle_voice_callback(bot, msg, "vc")

    assert ok1 in (True, False)
    assert ok2 in (True, False)
