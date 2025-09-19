"""Tests for TTS Engine async synthesis success and failure cases.

Ensures metrics and performance are recorded properly for both good and bad synthesis attempts.
"""

from __future__ import annotations

import asyncio
import pytest


class _DummyMetrics:
    """Mock metrics collector for test verification.

    Keeps lists of recorded requests (success/error) and errors for checking in tests.
    """

    def __init__(self):
        self.requests = []
        self.errors = []

    async def record_request(
        self,
        engine: str,
        lang: str,
        duration: float,
        success: bool,
        error_type: str | None = None,
    ):
        self.requests.append((engine, lang, duration, success, error_type))

    async def record_error(self, etype: str, msg: str):
        self.errors.append((etype, msg))


class _DummyPerf:
    """Mock performance monitor for tests.

    Tracks recorded requests with engine, lang, duration, success in a list.
    """

    def __init__(self):
        self.requests = []

    async def record_request(
        self, engine: str, lang: str, duration: float, success: bool
    ):
        self.requests.append((engine, lang, duration, success))


def _install_monitors(monkeypatch, metrics: _DummyMetrics, perf: _DummyPerf):
    """Set up mocks for metrics and performance monitoring in tests.

    Patches the base module to use the provided mock instances.

    Parameters
        monkeypatch: Pytest fixture for applying patches.
        metrics (_DummyMetrics): The mock metrics instance.
        perf (_DummyPerf): The mock performance monitor.
    """
    import ttskit.engines.base as base

    monkeypatch.setattr(base, "get_metrics_collector", lambda: metrics)
    monkeypatch.setattr(base, "get_performance_monitor", lambda: perf)


def _make_engine(success: bool):
    """Creates a mock TTS Engine for testing based on success/failure.

    Overrides _synth_async_impl to either return audio bytes or raise an error.

    Parameters
        success (bool): If True, synthesis succeeds; if False, it raises RuntimeError.

    Returns
        E: Instantiated mock engine ready for use.
    """
    import ttskit.engines.base as base

    class E(base.BaseEngine):
        def __init__(self):
            super().__init__(default_lang="en")

        def synth_to_mp3(self, text: str, lang: str | None = None) -> str:
            return "path.mp3"

        async def synth_async(self, text, lang=None, voice=None, rate=1.0, pitch=0.0):
            return await super().synth_async(text, lang, voice, rate, pitch)

        async def _synth_async_impl(
            self, text, lang=None, voice=None, rate=1.0, pitch=0.0
        ):
            if success:
                return b"audio"
            raise RuntimeError("boom")

        def list_voices(self, lang: str | None = None):
            return []

    return E()


@pytest.mark.asyncio
async def test_synth_async_success_records(monkeypatch):
    """Tests that successful TTS synthesis records metrics correctly.

    Checks that audio is returned and both metrics and perf monitors log the successful request.

    Parameters
        monkeypatch: For patching modules in tests.

    Returns
        None (asserts the expected behavior)
    """
    metrics = _DummyMetrics()
    perf = _DummyPerf()
    _install_monitors(monkeypatch, metrics, perf)

    eng = _make_engine(True)
    out = await eng.synth_async("hi", "en", "v", 1.0, 0.0)
    assert out == b"audio"
    assert perf.requests and perf.requests[0][3] is True
    assert metrics.requests and metrics.requests[0][3] is True


@pytest.mark.asyncio
async def test_synth_async_failure_records_and_raises(monkeypatch):
    """Tests that failed TTS synthesis records errors and re-raises exceptions.

    Verifies the original exception is raised while metrics and perf record the failure, including error type.

    Parameters
        monkeypatch: For setting up test mocks.

    Returns
        None (asserts outside the with block confirm error recording)
    """
    metrics = _DummyMetrics()
    perf = _DummyPerf()
    _install_monitors(monkeypatch, metrics, perf)

    eng = _make_engine(False)
    with pytest.raises(RuntimeError):
        await eng.synth_async("hi", "en", "v", 1.0, 0.0)

    assert perf.requests and perf.requests[0][3] is False
    assert metrics.requests and metrics.requests[0][3] is False
    assert metrics.errors and metrics.errors[0][0] == "RuntimeError"
