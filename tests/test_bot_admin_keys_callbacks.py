"""Tests for admin API key callbacks in ttskit.bot.callbacks.

Covers:
- delete_key_callback
- create_key_user_callback
- create_key_writer_callback
- create_key_admin_callback
- _create_api_key_with_permissions (via public wrappers)
- delete_key_confirm_callback (all branches)
"""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from ttskit.bot.callbacks import (
    create_key_admin_callback,
    create_key_user_callback,
    create_key_writer_callback,
    delete_key_callback,
    delete_key_confirm_callback,
)


def make_mock_bot() -> Mock:
    bot = Mock()
    bot.adapter = Mock()
    bot.adapter.send_message = AsyncMock()
    bot.awaitable = Mock(side_effect=lambda f: f)
    return bot


def make_mock_message(user_id: int = 111, chat_id: int = 222) -> Mock:
    message = Mock()
    message.user = Mock()
    message.user.id = user_id
    message.chat_id = chat_id
    return message


@pytest.mark.asyncio
async def test_delete_key_callback_sends_prompt():
    bot = make_mock_bot()
    msg = make_mock_message()
    with patch("ttskit.bot.callbacks.t", return_value="delete_key_title_text") as pt:
        await delete_key_callback(bot, msg, "delete_key")
        pt.assert_called_once()
        bot.adapter.send_message.assert_awaited_once_with(
            msg.chat_id, "delete_key_title_text"
        )


@pytest.mark.parametrize(
    "func,perms",
    [
        (create_key_user_callback, ["read"]),
        (create_key_writer_callback, ["read", "write"]),
        (create_key_admin_callback, ["read", "write", "admin"]),
    ],
)
@pytest.mark.asyncio
async def test_create_key_callbacks_success(func, perms):
    bot = make_mock_bot()
    msg = make_mock_message(user_id=999)

    with (
        patch("ttskit.database.connection.get_session") as p_sess,
        patch("ttskit.services.user_service.UserService") as p_usvc,
        patch("ttskit.bot.callbacks.t", return_value="created_text") as pt,
    ):
        db = MagicMock()
        p_sess.return_value = iter([db])

        user_service = AsyncMock()
        user_service.create_user = AsyncMock(return_value=None)
        user_service.create_api_key = AsyncMock(return_value={"api_key": "API123"})
        p_usvc.return_value = user_service

        await func(bot, msg, "cb")

        user_service.create_user.assert_awaited()
        user_service.create_api_key.assert_awaited()
        pt.assert_called()
        bot.adapter.send_message.assert_awaited_once_with(msg.chat_id, "created_text")


@pytest.mark.asyncio
async def test_create_key_callbacks_exception_path():
    bot = make_mock_bot()
    msg = make_mock_message()

    with (
        patch("ttskit.database.connection.get_session") as p_sess,
        patch("ttskit.services.user_service.UserService") as p_usvc,
    ):
        db = MagicMock()
        p_sess.return_value = iter([db])

        user_service = AsyncMock()
        user_service.create_user = AsyncMock(side_effect=Exception("boom"))
        p_usvc.return_value = user_service

        await create_key_user_callback(bot, msg, "cb")
        assert bot.adapter.send_message.await_count == 1


@pytest.mark.asyncio
async def test_delete_key_confirm_no_keys_branch():
    bot = make_mock_bot()
    msg = make_mock_message()

    with (
        patch("ttskit.database.connection.get_session") as p_sess,
        patch("ttskit.services.user_service.UserService") as p_usvc,
        patch("ttskit.bot.callbacks.t", return_value="no_keys_text") as pt,
    ):
        db = MagicMock()
        p_sess.return_value = iter([db])

        user_service = AsyncMock()
        user_service.get_user_api_keys = AsyncMock(return_value=[])
        p_usvc.return_value = user_service

        data = "delete_key_confirm_userX"
        await delete_key_confirm_callback(bot, msg, data)

        user_service.get_user_api_keys.assert_awaited_once_with("userX")
        pt.assert_called()
        bot.adapter.send_message.assert_awaited_once_with(msg.chat_id, "no_keys_text")


@pytest.mark.asyncio
async def test_delete_key_confirm_success_branch():
    bot = make_mock_bot()
    msg = make_mock_message()

    with (
        patch("ttskit.database.connection.get_session") as p_sess,
        patch("ttskit.services.user_service.UserService") as p_usvc,
        patch("ttskit.bot.callbacks.t", return_value="deleted_text") as pt,
    ):
        db = MagicMock()
        p_sess.return_value = iter([db])

        api_key_obj = Mock()
        api_key_obj.id = 1

        user_service = AsyncMock()
        user_service.get_user_api_keys = AsyncMock(return_value=[api_key_obj])
        user_service.delete_api_key = AsyncMock(return_value=True)
        p_usvc.return_value = user_service

        await delete_key_confirm_callback(bot, msg, "delete_key_confirm_userY")

        user_service.delete_api_key.assert_awaited_once_with("userY", 1)
        pt.assert_called()
        bot.adapter.send_message.assert_awaited_once_with(msg.chat_id, "deleted_text")


@pytest.mark.asyncio
async def test_delete_key_confirm_failure_branch():
    bot = make_mock_bot()
    msg = make_mock_message()

    with (
        patch("ttskit.database.connection.get_session") as p_sess,
        patch("ttskit.services.user_service.UserService") as p_usvc,
        patch("ttskit.bot.callbacks.t", return_value="error_text") as pt,
    ):
        db = MagicMock()
        p_sess.return_value = iter([db])

        api_key_obj = Mock()
        api_key_obj.id = 7

        user_service = AsyncMock()
        user_service.get_user_api_keys = AsyncMock(return_value=[api_key_obj])
        user_service.delete_api_key = AsyncMock(return_value=False)
        p_usvc.return_value = user_service

        await delete_key_confirm_callback(bot, msg, "delete_key_confirm_userZ")

        user_service.delete_api_key.assert_awaited_once_with("userZ", 7)
        pt.assert_called()
        bot.adapter.send_message.assert_awaited_once_with(msg.chat_id, "error_text")


@pytest.mark.asyncio
async def test_delete_key_confirm_exception_branch():
    bot = make_mock_bot()
    msg = make_mock_message()

    with (
        patch("ttskit.database.connection.get_session") as p_sess,
        patch("ttskit.services.user_service.UserService") as p_usvc,
    ):
        db = MagicMock()
        p_sess.return_value = iter([db])

        user_service = AsyncMock()
        user_service.get_user_api_keys = AsyncMock(side_effect=Exception("x"))
        p_usvc.return_value = user_service

        await delete_key_confirm_callback(bot, msg, "delete_key_confirm_U")
        assert bot.adapter.send_message.await_count == 1
