"""Tests for ProcessLifecycleManager in ttskit.services.lifecycle."""

from unittest.mock import MagicMock

import pytest

from ttskit.services.lifecycle import (
    LifecycleMode,
    ProcessLifecycleManager,
)


def test_detect_mode_standalone(monkeypatch):
    """Test standalone mode detection when no supervisor env vars are present."""
    monkeypatch.delenv("TTSKIT_SUPERVISED", raising=False)
    monkeypatch.delenv("SUPERVISED_MODE", raising=False)
    monkeypatch.delenv("INVOCATION_ID", raising=False)
    monkeypatch.delenv("JOURNAL_STREAM", raising=False)
    monkeypatch.delenv("SUPERVISOR_ENABLED", raising=False)
    monkeypatch.delenv("KUBERNETES_SERVICE_HOST", raising=False)

    mgr = ProcessLifecycleManager()
    assert mgr.detect_mode() == LifecycleMode.STANDALONE


def test_detect_mode_supervised(monkeypatch):
    """Test supervised mode detection via environment variables."""
    monkeypatch.setenv("TTSKIT_SUPERVISED", "true")
    mgr = ProcessLifecycleManager()
    assert mgr.detect_mode() == LifecycleMode.SUPERVISED

    monkeypatch.delenv("TTSKIT_SUPERVISED")
    monkeypatch.setenv("INVOCATION_ID", "abc-123")
    assert mgr.detect_mode() == LifecycleMode.SUPERVISED


@pytest.mark.asyncio
async def test_shutdown_hooks_execution():
    """Verify sync and async hooks run and failures don't halt subsequent hooks."""
    called = []

    def sync_hook():
        called.append("sync")

    async def async_hook():
        called.append("async")

    def failing_hook():
        raise RuntimeError("boom")

    mgr = ProcessLifecycleManager()
    mgr.register_shutdown_hook(sync_hook)
    mgr.register_shutdown_hook(failing_hook)
    mgr.register_shutdown_hook(async_hook)

    await mgr.run_shutdown_hooks()
    assert called == ["sync", "async"]

    mgr.unregister_shutdown_hook(sync_hook)
    called.clear()
    await mgr.run_shutdown_hooks()
    assert called == ["async"]


@pytest.mark.asyncio
async def test_request_restart_supervised(monkeypatch):
    """Verify request_restart in supervised mode triggers exit handler with 0."""
    monkeypatch.setenv("SUPERVISED_MODE", "true")
    exit_handler = MagicMock()
    mgr = ProcessLifecycleManager(exit_handler=exit_handler)

    res = await mgr.request_restart()
    assert res["supported"] is True
    assert res["mode"] == LifecycleMode.SUPERVISED.value
    exit_handler.assert_called_once_with(0)


@pytest.mark.asyncio
async def test_request_restart_standalone_no_execv(monkeypatch):
    """Verify request_restart in standalone mode without execv reports unsupported."""
    monkeypatch.delenv("TTSKIT_SUPERVISED", raising=False)
    monkeypatch.delenv("SUPERVISED_MODE", raising=False)
    monkeypatch.delenv("INVOCATION_ID", raising=False)
    monkeypatch.delenv("JOURNAL_STREAM", raising=False)
    monkeypatch.delenv("SUPERVISOR_ENABLED", raising=False)
    monkeypatch.delenv("KUBERNETES_SERVICE_HOST", raising=False)

    exit_handler = MagicMock()
    mgr = ProcessLifecycleManager(exit_handler=exit_handler)

    res = await mgr.request_restart(use_execv_fallback=False)
    assert res["supported"] is False
    assert res["mode"] == LifecycleMode.STANDALONE.value
    exit_handler.assert_not_called()


@pytest.mark.asyncio
async def test_request_shutdown():
    """Verify request_shutdown runs hooks and calls exit handler."""
    called = []
    exit_handler = MagicMock()
    mgr = ProcessLifecycleManager(exit_handler=exit_handler)
    mgr.register_shutdown_hook(lambda: called.append("hook"))

    res = await mgr.request_shutdown()
    assert res["supported"] is True
    assert called == ["hook"]
    exit_handler.assert_called_once_with(0)
