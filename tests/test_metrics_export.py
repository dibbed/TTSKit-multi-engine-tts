"""Tests for the export_metrics function in ttskit.metrics.

This module provides unit tests for the different output formats (JSON, Prometheus, and fallback)
of the export_metrics function, using monkeypatching to mock get_metrics and verify serialization.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_metrics_file_module():
    project_root = Path(__file__).resolve().parents[1]
    target = project_root / "ttskit" / "metrics.py"
    spec = importlib.util.spec_from_file_location("ttskit_metrics_file", str(target))
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_export_metrics_json_branch(monkeypatch):
    """Test the JSON export branch of the export_metrics function.

    Parameters:
        monkeypatch (pytest.MonkeyPatch): Fixture for mocking attributes.

    Notes:
        Mocks get_metrics to return a sample list and verifies the JSON output parses correctly.
    """
    m = _load_metrics_file_module()

    monkeypatch.setattr(m, "get_metrics", lambda: [{"ok": True, "n": 1}])

    out = m.export_metrics(format="json")
    data = json.loads(out)
    assert isinstance(data, list) and data[0]["ok"] is True and data[0]["n"] == 1


def test_export_metrics_prometheus_branch(monkeypatch):
    """Test the Prometheus export branch of the export_metrics function.

    Parameters:
        monkeypatch (pytest.MonkeyPatch): Fixture for mocking attributes.

    Notes:
        Mocks get_metrics to return a dict with metrics and verifies Prometheus-formatted lines,
        ensuring non-metric fields like 'note' are excluded.
    """
    m = _load_metrics_file_module()

    monkeypatch.setattr(
        m, "get_metrics", lambda: {"total_requests": 5, "avg": 1.23, "note": "x"}
    )

    out = m.export_metrics(format="prometheus")
    lines = [line.strip() for line in out.split("\n") if line.strip()]
    assert "ttskit_total_requests 5" in lines
    assert any(l.startswith("ttskit_avg ") for l in lines)
    assert not any("note" in l for l in lines)


def test_export_metrics_fallback_branch(monkeypatch):
    """Test the fallback export branch of the export_metrics function.

    Parameters:
        monkeypatch (pytest.MonkeyPatch): Fixture for mocking attributes.

    Notes:
        Mocks get_metrics to return a simple list and verifies the fallback string representation.
    """
    m = _load_metrics_file_module()

    monkeypatch.setattr(m, "get_metrics", lambda: [1, 2, 3])

    out = m.export_metrics(format="custom")
    assert out == "[1, 2, 3]"
