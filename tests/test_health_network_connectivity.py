"""Unit tests for network connectivity checks in TTSKit's health module.

This module tests the check_network_connectivity function, covering successful and failed ping
paths, as well as the socket-based fallback when ping is unavailable.
"""

from __future__ import annotations

import pytest


class _Proc:
    def __init__(self, rc: int):
        self._rc = rc

    async def wait(self):
        return self._rc


@pytest.mark.asyncio
async def test_network_connectivity_ping_success(monkeypatch):
    """Tests successful network connectivity via ping.

    Mocks subprocess creation to return exit code 0 (success), verifying the result status
    and details indicate connection success.

    Parameters:
    - monkeypatch: Pytest fixture for mocking.

    Behavior:
    - Patches create_subprocess_exec to return _Proc(0).
    - Runs check_network_connectivity and asserts status=True, connection_success=True.
    """
    import ttskit.health as h

    async def fake_create(*a, **k):
        return _Proc(0)

    monkeypatch.setattr(h.asyncio, "create_subprocess_exec", fake_create)
    res = await h.check_network_connectivity()
    assert res.status is True and res.details.get("connection_success") is True


@pytest.mark.asyncio
async def test_network_connectivity_ping_fail(monkeypatch):
    """Tests failed network connectivity via ping.

    Mocks subprocess to return exit code 1 (failure), ensuring status and details reflect
    connection failure.

    Parameters:
    - monkeypatch: Pytest fixture for mocking.

    Behavior:
    - Patches create_subprocess_exec to return _Proc(1).
    - Runs check_network_connectivity and asserts status=False, connection_success=False.
    """
    import ttskit.health as h

    async def fake_create(*a, **k):
        return _Proc(1)

    monkeypatch.setattr(h.asyncio, "create_subprocess_exec", fake_create)
    res = await h.check_network_connectivity()
    assert res.status is False and res.details.get("connection_success") is False


@pytest.mark.asyncio
async def test_network_connectivity_socket_fallback(monkeypatch):
    """Tests socket fallback for network connectivity when ping fails.

    Mocks ping to raise RuntimeError, then mocks socket connect_ex to return 0 (success),
    verifying overall status is True.

    Parameters:
    - monkeypatch: Pytest fixture for mocking.

    Behavior:
    - Patches create_subprocess_exec to raise error.
    - Defines _Sock mock with connect_ex=0.
    - Patches socket.socket to return _Sock(0).
    - Runs check_network_connectivity and asserts status=True.
    """
    import ttskit.health as h

    async def fake_create(*a, **k):
        raise RuntimeError("no ping")

    class _Sock:
        def __init__(self, code):
            self._code = code

        def settimeout(self, *_):
            pass

        def connect_ex(self, *_):
            return self._code

        def close(self):
            pass

    monkeypatch.setattr(h.asyncio, "create_subprocess_exec", fake_create)
    import socket as _socket

    monkeypatch.setattr(_socket, "socket", lambda *_: _Sock(0))
    res = await h.check_network_connectivity()
    assert res.status is True
