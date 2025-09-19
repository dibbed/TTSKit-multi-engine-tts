"""Comprehensive tests for the AiogramAdapter in ttskit.telegram, covering message sending/receiving, parsing, start/stop, and handlers using mocks from conftest (e.g., aiogram.Bot)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from ttskit.telegram.aiogram_adapter import AiogramAdapter


class _Msg:
    """Minimal mock for aiogram.types.Message used in tests to simulate various message structures for adapter parsing."""

    def __init__(self):
        self.message_id = 10
        self.chat = SimpleNamespace(id=20)
        self.from_user = SimpleNamespace(
            id=30,
            username="u",
            first_name="f",
            last_name="l",
            language_code="en",
            is_bot=False,
            is_premium=False,
        )
        self.text = "hi"
        self.date = None
        self.edit_date = None
        self.media_group_id = None
        self.caption = None
        self.entities = []
        self.voice = None
        self.audio = None
        self.document = None
        self.photo = None
        self.video = None
        self.sticker = None
        self.location = None
        self.contact = None
        self.poll = None
        self.reply_to_message = None

    def model_dump(self):
        return {"message_id": self.message_id}


class _Callback:
    """Mock for aiogram.types.CallbackQuery used in handler tests to simulate callback data and user context."""

    def __init__(self):
        self.data = "cbdata"
        self.message = SimpleNamespace(message_id=11, chat=SimpleNamespace(id=21))
        self.from_user = SimpleNamespace(
            id=31,
            username="cu",
            first_name="cf",
            last_name="cl",
            language_code="en",
            is_bot=False,
            is_premium=False,
        )

    def model_dump(self):
        return {"data": self.data}


"""Tests message sending, editing, deletion, chat and user retrieval in AiogramAdapter.

Verifies successful operations and fallback user info retrieval when get_chat_member fails,
using mocked bot methods for send_message, edit_message_text, delete_message, get_chat, and get_chat_member.
"""

@pytest.mark.asyncio
async def test_send_message_parsing_and_methods(monkeypatch):
    adapter = AiogramAdapter("token:1")

    msg = _Msg()

    async def _send_message(*args, **kwargs):
        return msg

    async def _edit_message_text(*args, **kwargs):
        m = _Msg()
        m.text = kwargs.get("text", "edited")
        return m

    async def _delete_message(*a, **k):
        return True

    async def _get_chat(*a, **k):
        return SimpleNamespace(
            id=50,
            type="private",
            title="t",
            username="un",
            first_name="fn",
            last_name="ln",
            description="d",
            invite_link="link",
        )

    async def _get_chat_member(*a, **k):
        return SimpleNamespace(user=msg.from_user)

    mock_bot = Mock()
    mock_bot.send_message = _send_message
    mock_bot.edit_message_text = _edit_message_text
    mock_bot.delete_message = _delete_message
    mock_bot.get_chat = _get_chat
    mock_bot.get_chat_member = _get_chat_member

    monkeypatch.setattr(
        "ttskit.telegram.aiogram_adapter.Bot", MagicMock(return_value=mock_bot)
    )

    parsed = await adapter.send_message(1, "hi")
    assert parsed.id == msg.message_id and parsed.chat_id == 20 and parsed.text == "hi"

    edited = await adapter.edit_message_text(1, parsed.id, "new")
    assert edited.text == "new"

    ok = await adapter.delete_message(1, parsed.id)
    assert ok is True

    chat = await adapter.get_chat(50)
    assert chat.id == 50 and chat.type == "private"

    user = await adapter.get_user(30)
    assert user.id == 30 and user.username == "u"

    mock_bot2 = Mock()

    async def _get_member_fail(*a, **k):
        raise RuntimeError("no member")

    async def _get_chat_ok(*a, **k):
        return SimpleNamespace(
            id=30,
            username="u",
            first_name="f",
            last_name="l",
            language_code="en",
            is_bot=False,
            is_premium=False,
        )

    mock_bot2.get_chat_member = _get_member_fail
    mock_bot2.get_chat = _get_chat_ok
    monkeypatch.setattr(
        "ttskit.telegram.aiogram_adapter.Bot", MagicMock(return_value=mock_bot2)
    )
    adapter.bot = mock_bot2
    user2 = await adapter.get_user(30)
    assert user2.id == 30


"""Tests sending voice, audio, and document messages in AiogramAdapter.

Covers successful media uploads with metadata (title, performer, filename) and error handling on send failures,
using mocked send_voice, send_audio, and send_document methods.
"""

@pytest.mark.asyncio
async def test_send_voice_audio_document_paths(monkeypatch):
    adapter = AiogramAdapter("token:1")
    msg = _Msg()

    async def _ret(*a, **k):
        return msg

    mock_bot = Mock()
    mock_bot.send_voice = _ret
    mock_bot.send_audio = _ret
    mock_bot.send_document = _ret
    monkeypatch.setattr(
        "ttskit.telegram.aiogram_adapter.Bot", MagicMock(return_value=mock_bot)
    )

    v = await adapter.send_voice(1, b"v")
    assert v.id == msg.message_id

    a = await adapter.send_audio(1, b"a", title="t", performer="p")
    assert a.id == msg.message_id

    d = await adapter.send_document(1, b"d", filename="f.bin")
    assert d.id == msg.message_id

    mock_bot2 = Mock()

    async def _raise(*a, **k):
        raise RuntimeError("send failed")

    mock_bot2.send_message = _raise
    monkeypatch.setattr(
        "ttskit.telegram.aiogram_adapter.Bot", MagicMock(return_value=mock_bot2)
    )
    adapter.bot = mock_bot2
    with pytest.raises(RuntimeError):
        await adapter.send_message(1, "x")


"""Tests message type parsing, callback handling, and error propagation in AiogramAdapter.

Sets up message, callback, and error handlers; simulates various message types (e.g., voice) and callbacks;
verifies handler invocation and error catching via mocked Dispatcher.
"""

@pytest.mark.asyncio
async def test_parse_message_types_and_callback_and_handlers(monkeypatch):
    adapter = AiogramAdapter("token:1")

    seen = {"msg": None, "cb": None, "err": None}

    async def on_msg(m):
        seen["msg"] = m.message_type.name

    async def on_cb(m):
        seen["cb"] = m.text

    async def on_err(e, raw):
        seen["err"] = str(e)

    adapter.set_message_handler(on_msg)
    adapter.set_callback_handler(on_cb)
    adapter.set_error_handler(on_err)

    class _Disp:
        def __init__(self):
            self._message_cb = None
            self._callback_cb = None

        def message(self):
            def _wrap(fn):
                self._message_cb = fn
                return fn

            return _wrap

        def callback_query(self):
            def _wrap(fn):
                self._callback_cb = fn
                return fn

            return _wrap

        def start_polling(self, bot):
            async def _dummy():
                return None

            return _dummy()

    mock_dp = _Disp()
    monkeypatch.setattr(
        "ttskit.telegram.aiogram_adapter.Dispatcher", MagicMock(return_value=mock_dp)
    )

    adapter.dp = mock_dp
    adapter._setup_handlers()

    m = _Msg()
    m.voice = True
    await mock_dp._message_cb(m)
    assert seen["msg"] == "VOICE"

    cb = _Callback()
    await mock_dp._callback_cb(cb)
    assert seen["cb"] == "cbdata"

    async def bad_handler(_):
        raise RuntimeError("boom")

    adapter.set_message_handler(bad_handler)
    await mock_dp._message_cb(_Msg())
    assert "boom" in (seen["err"] or "")


"""Tests adapter start/stop polling and message type parsing for media/non-text types.

Verifies _running state toggles correctly with mocked Dispatcher.start_polling and Bot;
parses various message types (audio, document, photo, video, sticker, location, contact, poll) using _parse_message.
"""

@pytest.mark.asyncio
async def test_start_and_stop_paths(monkeypatch):
    adapter = AiogramAdapter("token:1")

    class _Disp:
        def __init__(self):
            self._started = False

        def start_polling(self, bot):
            async def _dummy():
                self._started = True
                return None

            return _dummy()

    monkeypatch.setattr(
        "ttskit.telegram.aiogram_adapter.Dispatcher", MagicMock(return_value=_Disp())
    )

    class _FakeBot:
        def __init__(self, token):
            self.token = token
            self.session = SimpleNamespace(close=AsyncMock())

    monkeypatch.setattr("ttskit.telegram.aiogram_adapter.Bot", _FakeBot)

    m = _Msg()
    m.audio = True
    assert adapter._parse_message(m).message_type.name == "AUDIO"
    m = _Msg()
    m.document = True
    assert adapter._parse_message(m).message_type.name == "DOCUMENT"
    m = _Msg()
    m.photo = True
    assert adapter._parse_message(m).message_type.name == "PHOTO"
    m = _Msg()
    m.video = True
    assert adapter._parse_message(m).message_type.name == "VIDEO"
    m = _Msg()
    m.sticker = True
    assert adapter._parse_message(m).message_type.name == "STICKER"
    m = _Msg()
    m.location = True
    assert adapter._parse_message(m).message_type.name == "LOCATION"
    m = _Msg()
    m.contact = True
    assert adapter._parse_message(m).message_type.name == "CONTACT"
    m = _Msg()
    m.poll = True
    assert adapter._parse_message(m).message_type.name == "POLL"

    await adapter.start()
    assert adapter._running is True

    await adapter.stop()
    assert adapter._running is False
