"""Tests for TTS bot's request processing method.

This covers different paths like cache hits/misses, successful synthesis, and various error cases.
It ensures the bot handles scenarios gracefully.
"""

from __future__ import annotations

import types

import pytest


class _Msg:
    """A simple mock Telegram message class for tests.

    Contains basic fields like chat_id, id, text, user, and message_type to simulate real messages.
    """

    def __init__(self):
        self.chat_id = 1
        self.id = 11
        self.text = "Hello"
        self.user = types.SimpleNamespace(id=99)
        self.message_type = types.SimpleNamespace(value="text")


class _Adapter:
    """A mock bot adapter that tracks sent messages and voices for verification.

    It records actions like sending messages, deleting, and sending voice in self.sent list for test assertions.
    """

    def __init__(self):
        self.sent = []

    def send_message(self, chat_id, text):
        self.sent.append(("msg", chat_id, text))
        return types.SimpleNamespace(id=123)

    def delete_message(self, chat_id, mid):
        self.sent.append(("del", chat_id, mid))

    def send_voice(self, chat_id, data, caption, reply_to_message_id=None):
        self.sent.append(("voice", chat_id, data, caption, reply_to_message_id))


class _Smart:
    """Mock TTS smart router for testing synthesis outcomes.

    Supports different behavior modes: 'ok' for success, 'fail' for all engines fail, 'notfound' for engine not found.
    """

    def __init__(self, behavior="ok"):
        self.behavior = behavior

    async def synth_async(self, text, lang, requirements=None):
        if self.behavior == "ok":
            return b"A", "edge"
        if self.behavior == "fail":
            from ttskit.exceptions import AllEnginesFailedError

            raise AllEnginesFailedError("x")
        if self.behavior == "notfound":
            from ttskit.exceptions import EngineNotFoundError

            raise EngineNotFoundError("x")
        return b"B", "gtts"


@pytest.mark.asyncio
async def test_process_tts_request_cache_hit(monkeypatch):
    """Tests what happens when there's a cache hit for TTS.

    The bot should send the cached audio as a voice message and delete the original user message.

    Parameters
        monkeypatch: For mocking dependencies.

    Returns
        None (uses assertions to check behavior)
    """
    from ttskit.bot.unified_bot import UnifiedTTSBot

    bot = UnifiedTTSBot("t")
    bot.adapter = _Adapter()
    bot.smart_router = _Smart("ok")

    import ttskit.utils.audio_manager as am

    monkeypatch.setattr(am.audio_manager, "get_audio", lambda *a, **k: b"CACHED")

    m = _Msg()
    await bot._process_tts_request(m, "hello", "en")

    ops = [x[0] for x in bot.adapter.sent]
    assert "voice" in ops and "del" in ops


@pytest.mark.asyncio
async def test_process_tts_request_cache_miss_then_synth(monkeypatch):
    """Tests TTS when the cache is missing but synthesis succeeds.

    Should generate new audio and send it as a voice message.

    Parameters
        monkeypatch: Used for dependency mocking.

    Returns
        None (validates via assertions)
    """
    from ttskit.bot.unified_bot import UnifiedTTSBot

    bot = UnifiedTTSBot("t")
    bot.adapter = _Adapter()
    bot.smart_router = _Smart("ok")

    import ttskit.utils.audio_manager as am

    monkeypatch.setattr(am.audio_manager, "get_audio", lambda *a, **k: None)

    m = _Msg()
    await bot._process_tts_request(m, "hello", "en")
    ops = [x[0] for x in bot.adapter.sent]
    assert "voice" in ops


@pytest.mark.asyncio
async def test_process_tts_request_all_engines_failed(monkeypatch):
    """Tests error handling when all TTS engines fail.

    The bot should send an error message instead of a voice.

    Parameters
        monkeypatch: For setting up mock failures.

    Returns
        None (checks that no voice is sent, but an error message is)
    """
    from ttskit.bot.unified_bot import UnifiedTTSBot

    bot = UnifiedTTSBot("t")
    bot.adapter = _Adapter()
    bot.smart_router = _Smart("fail")

    import ttskit.utils.audio_manager as am

    monkeypatch.setattr(am.audio_manager, "get_audio", lambda *a, **k: None)

    m = _Msg()
    await bot._process_tts_request(m, "hello", "en")
    kinds = [k for k, *_ in bot.adapter.sent]
    assert "voice" not in kinds
    assert any(k == "msg" for k in kinds)


@pytest.mark.asyncio
async def test_process_tts_request_engine_not_found(monkeypatch):
    """Tests what happens when the requested engine is not available.

    The bot should send an error message and not a voice.

    Parameters
        monkeypatch: For mocking the engine not found case.

    Returns
        None (verifies error message sent, no voice)
    """
    from ttskit.bot.unified_bot import UnifiedTTSBot

    bot = UnifiedTTSBot("t")
    bot.adapter = _Adapter()
    bot.smart_router = _Smart("notfound")

    import ttskit.utils.audio_manager as am

    monkeypatch.setattr(am.audio_manager, "get_audio", lambda *a, **k: None)

    m = _Msg()
    await bot._process_tts_request(m, "hello", "zz")
    kinds = [k for k, *_ in bot.adapter.sent]
    assert "voice" not in kinds and any(k == "msg" for k in kinds)
