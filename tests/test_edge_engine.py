"""Unit tests for EdgeEngine voice selection and synthesis path (mocked)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest


def _stub_edge_module(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sets up mocks for the Edge TTS module to simulate availability and synthesis without real dependencies.

    Parameters:
        monkeypatch: Pytest fixture for patching module attributes.

    Behavior:
        Mocks EDGE_AVAILABLE as True and replaces edge_tts.Communicate with a dummy class that writes placeholder audio bytes.
    """
    import ttskit.engines.edge_engine as edge_engine_module

    class DummyCommunicate:
        def __init__(self, text: str, voice: str) -> None:
            self.text = text
            self.voice = voice

        async def save(self, path: str) -> None:
            Path(path).write_bytes(b"ID3\x03\x00\x00\x00\x00\x00\x21dummy")

    monkeypatch.setattr(edge_engine_module, "EDGE_AVAILABLE", True, raising=True)
    monkeypatch.setattr(
        edge_engine_module,
        "edge_tts",
        type("X", (), {"Communicate": DummyCommunicate}),
        raising=True,
    )


@pytest.mark.asyncio
async def test_edge_pick_voice_and_synth(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests voice selection for various languages and mocked synthesis to MP3 file in EdgeEngine.

    Parameters:
        monkeypatch: Pytest fixture for setting up Edge module stubs.

    Behavior:
        Verifies _pick_voice returns valid voices for English, Persian, and Arabic; ensures synth_to_mp3 creates a file (mocked).
    """
    _stub_edge_module(monkeypatch)
    from ttskit.engines.edge_engine import EdgeEngine

    engine = EdgeEngine(default_lang="en")
    assert engine._pick_voice("en")
    assert engine._pick_voice("en-US").startswith("en-")
    assert engine._pick_voice("fa").startswith("fa-")
    assert engine._pick_voice("ar").startswith("ar-")

    mp3_path = engine.synth_to_mp3("hello", "en")
    assert os.path.exists(mp3_path)


def test_edge_voice_override_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests environment variable override for voice selection in EdgeEngine.

    Parameters:
        monkeypatch: Pytest fixture for setting up Edge module stubs and environment variables.

    Behavior:
        Sets EDGE_VOICE_fa env var and verifies _pick_voice for 'fa' uses a voice starting with 'fa-' (influenced by override).
    """
    _stub_edge_module(monkeypatch)
    from ttskit.engines.edge_engine import EdgeEngine

    monkeypatch.setenv("EDGE_VOICE_fa", "fa-IR-FaridNeural")

    e = EdgeEngine(default_lang="en")
    assert e._pick_voice("fa").startswith("fa-")
