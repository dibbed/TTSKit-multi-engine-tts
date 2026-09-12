"""Tests for TTSKit engine probes in ttskit.engines.probe."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ttskit.engines.base import EngineCapabilities
from ttskit.engines.probe import (
    EngineProbeResult,
    probe_all_engines,
    probe_engine,
)


def _make_caps():
    return EngineCapabilities(
        offline=False,
        ssml=True,
        rate_control=True,
        pitch_control=True,
        languages=["en"],
        voices=["en_voice"],
        max_text_length=1000,
    )


@pytest.mark.asyncio
async def test_probe_engine_success():
    """Verify probe_engine succeeds with valid synthesis bytes."""
    mock_engine = MagicMock()
    mock_engine.is_available.return_value = True
    mock_engine.get_capabilities.return_value = _make_caps()
    mock_engine.synth_async = AsyncMock(return_value=b"RIFFwave_data_here")

    with patch("ttskit.engines.probe.engine_registry.get_engine", return_value=mock_engine):
        result = await probe_engine("edge")
        assert isinstance(result, EngineProbeResult)
        assert result.available is True
        assert result.status == "ok"
        assert result.bytes_produced == len(b"RIFFwave_data_here")
        assert result.latency_ms >= 0
        assert "OK" in result.message


@pytest.mark.asyncio
async def test_probe_engine_empty_bytes():
    """Verify probe_engine returns error status when engine returns empty bytes."""
    mock_engine = MagicMock()
    mock_engine.is_available.return_value = True
    mock_engine.get_capabilities.return_value = _make_caps()
    mock_engine.synth_async = AsyncMock(return_value=b"")

    with patch("ttskit.engines.probe.engine_registry.get_engine", return_value=mock_engine):
        result = await probe_engine("edge")
        assert result.available is False
        assert result.status == "error"
        assert result.error == "empty_data"


@pytest.mark.asyncio
async def test_probe_engine_unavailable():
    """Verify probe_engine handles an engine marked unavailable."""
    mock_engine = MagicMock()
    mock_engine.is_available.return_value = False

    with patch("ttskit.engines.probe.engine_registry.get_engine", return_value=mock_engine):
        result = await probe_engine("piper")
        assert result.available is False
        assert result.status == "unavailable"


@pytest.mark.asyncio
async def test_probe_engine_exception():
    """Verify probe_engine handles runtime errors gracefully."""
    mock_engine = MagicMock()
    mock_engine.is_available.return_value = True
    mock_engine.get_capabilities.return_value = _make_caps()
    mock_engine.synth_async = AsyncMock(side_effect=ConnectionError("Failed to reach service"))

    with patch("ttskit.engines.probe.engine_registry.get_engine", return_value=mock_engine):
        result = await probe_engine("gtts")
        assert result.available is False
        assert result.status == "error"
        assert "Failed to reach service" in result.error


@pytest.mark.asyncio
async def test_probe_all_engines():
    """Verify probe_all_engines queries each requested engine."""
    with patch("ttskit.engines.probe.probe_engine") as mock_probe:
        mock_probe.side_effect = lambda eng, **kwargs: EngineProbeResult(
            engine=eng,
            available=True,
            status="ok",
            latency_ms=10.0,
            bytes_produced=500,
            message=f"OK {eng}",
        )
        results = await probe_all_engines(["edge", "piper", "gtts"])
        assert len(results) == 3
        assert [r.engine for r in results] == ["edge", "piper", "gtts"]
        assert all(r.status == "ok" for r in results)
