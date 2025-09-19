"""
Admin database, key management, and system operation tests for callbacks.py.

Scenarios covered:
- list_keys: without users, with users and multiple keys
- create_key_*: creating users and keys with various permissions
- delete_key_confirm: no-key branch and with key + success/failure
- clear_cache flow: confirm/cancel
- restart flow: confirm/cancel
- test_all_engines and individual engine tests
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
    bot.awaitable = MagicMock(side_effect=lambda f: f)
    bot.is_sudo = Mock(return_value=True)
    bot.sudo_users = {"111"}
    return bot


def _make_message() -> MagicMock:
    """
    Creates a basic mocked message object for callback dispatch tests.

    Returns:
        MagicMock: A message mock with chat and user details.
    """
    msg = MagicMock()
    msg.chat_id = 77
    user = MagicMock()
    user.id = 111
    msg.user = user
    return msg


@pytest.mark.asyncio
async def test_list_keys_no_users():
    """
    Tests list_keys callback when no users exist in the database.

    Notes:
        Mocks UserService to return empty user list; verifies message is sent.
    """
    registry = CallbackRegistry()
    bot = _make_bot()
    registry.register_admin(bot)
    msg = _make_message()

    with (
        patch("ttskit.database.connection.get_session") as mock_get_sess,
        patch("ttskit.services.user_service.UserService") as mock_us_cls,
    ):
        mock_get_sess.return_value = iter([MagicMock()])
        us = MagicMock()
        us.get_all_users = AsyncMock(return_value=[])
        mock_us_cls.return_value = us

        ok = await registry.dispatch(bot, msg, "list_keys")
        assert ok is True
        bot.adapter.send_message.assert_awaited()


@pytest.mark.asyncio
async def test_list_keys_with_users_and_keys():
    """
    Tests list_keys callback when users and API keys are present.

    Notes:
        Mocks UserService to return users with active/inactive keys; verifies message sent.
    """
    registry = CallbackRegistry()
    bot = _make_bot()
    registry.register_admin(bot)
    msg = _make_message()

    fake_user = MagicMock()
    fake_user.user_id = "u1"

    class _Key:
        def __init__(self, id_: int, is_active: bool, created_at):
            self.id = id_
            self.is_active = is_active
            self.created_at = created_at

    import datetime as _dt

    k1 = _Key(1, True, _dt.datetime(2024, 1, 1, 12, 0))
    k2 = _Key(2, False, _dt.datetime(2024, 1, 2, 12, 0))

    with (
        patch("ttskit.database.connection.get_session") as mock_get_sess,
        patch("ttskit.services.user_service.UserService") as mock_us_cls,
        patch("json.loads", return_value=["read", "write"]) as _json_loads,
    ):
        mock_get_sess.return_value = iter([MagicMock()])
        us = MagicMock()
        us.get_all_users = AsyncMock(return_value=[fake_user])
        us.get_user_api_keys = AsyncMock(side_effect=[[k1, k2]])
        mock_us_cls.return_value = us

        ok = await registry.dispatch(bot, msg, "list_keys")
        assert ok is True
        bot.adapter.send_message.assert_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "permissions, data_prefix",
    [
        (["read"], "create_key_user"),
        (["read", "write"], "create_key_writer"),
        (["read", "write", "admin"], "create_key_admin"),
    ],
)
async def test_create_key_flows(permissions, data_prefix):
    """
    Tests creation flows for API keys with different permission levels.

    Parameters:
        permissions: List of permissions for the key (e.g., ["read"]).
        data_prefix: Callback data prefix for the specific flow.

    Notes:
        Mocks UserService create_user and create_api_key; verifies message sent for each permission set.
    """
    registry = CallbackRegistry()
    bot = _make_bot()
    registry.register_admin(bot)
    msg = _make_message()

    with (
        patch("ttskit.database.connection.get_session") as mock_get_sess,
        patch("ttskit.services.user_service.UserService") as mock_us_cls,
    ):
        mock_get_sess.return_value = iter([MagicMock()])
        us = MagicMock()
        us.create_user = AsyncMock(return_value=MagicMock(user_id="x"))
        us.create_api_key = AsyncMock(return_value={"api_key": "KEY"})
        mock_us_cls.return_value = us

        ok = await registry.dispatch(bot, msg, data_prefix)
        assert ok is True
        bot.adapter.send_message.assert_awaited()


@pytest.mark.asyncio
async def test_delete_key_confirm_no_keys_then_success_and_fail():
    """
    Tests delete_key_confirm callback for no keys, successful deletion, and failure scenarios.

    Notes:
        Progresses through empty keys (shows message), then delete success, and delete failure branches.
    """
    registry = CallbackRegistry()
    bot = _make_bot()
    registry.register_admin(bot)
    msg = _make_message()

    with (
        patch("ttskit.database.connection.get_session") as mock_get_sess,
        patch("ttskit.services.user_service.UserService") as mock_us_cls,
    ):
        mock_get_sess.return_value = iter([MagicMock()])
        us = MagicMock()
        mock_us_cls.return_value = us

        us.get_user_api_keys = AsyncMock(return_value=[])
        ok1 = await registry.dispatch(bot, msg, "delete_key_confirm_u1")
        assert ok1 is True

        class _Key:
            def __init__(self, id_):
                self.id = id_

        us.get_user_api_keys = AsyncMock(return_value=[_Key(10)])
        us.delete_api_key = AsyncMock(return_value=True)
        ok2 = await registry.dispatch(bot, msg, "delete_key_confirm_u1")
        assert ok2 is True

        us.get_user_api_keys = AsyncMock(return_value=[_Key(11)])
        us.delete_api_key = AsyncMock(return_value=False)
        ok3 = await registry.dispatch(bot, msg, "delete_key_confirm_u1")
        assert ok3 is True


@pytest.mark.asyncio
async def test_clear_cache_flow_confirm_and_cancel():
    """
    Tests the clear_cache confirmation and cancellation flow.

    Notes:
        Dispatches initial clear_cache, then confirm and cancel branches.
    """
    registry = CallbackRegistry()
    bot = _make_bot()
    registry.register_admin(bot)
    msg = _make_message()

    ok1 = await registry.dispatch(bot, msg, "clear_cache")
    assert ok1 is True
    ok2 = await registry.dispatch(bot, msg, "confirm_clear_cache")
    assert ok2 is True
    ok3 = await registry.dispatch(bot, msg, "cancel_clear_cache")
    assert ok3 is True


@pytest.mark.asyncio
async def test_restart_flow_confirm_and_cancel():
    """
    Tests the restart confirmation and cancellation flow.

    Notes:
        Dispatches confirm_restart and cancel_restart branches.
    """
    registry = CallbackRegistry()
    bot = _make_bot()
    registry.register_admin(bot)
    msg = _make_message()

    ok1 = await registry.dispatch(bot, msg, "confirm_restart")
    assert ok1 is True
    ok2 = await registry.dispatch(bot, msg, "cancel_restart")
    assert ok2 is True


@pytest.mark.asyncio
async def test_engines_tests_all_and_individual():
    """
    Tests engine testing callbacks for all engines and individual ones.

    Notes:
        Mocks asyncio.sleep; verifies dispatch success for test_all_engines and specific engines (edge, piper, gtts).
    """
    registry = CallbackRegistry()
    bot = _make_bot()
    registry.register_admin(bot)
    msg = _make_message()

    with patch("asyncio.sleep", new=AsyncMock(return_value=None)):
        ok_all = await registry.dispatch(bot, msg, "test_all_engines")
    assert ok_all is True

    for single in ["test_edge", "test_piper", "test_gtts"]:
        ok = await registry.dispatch(bot, msg, single)
        assert ok is True
