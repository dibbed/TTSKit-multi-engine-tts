"""Unit tests for the HealthChecker in TTSKit's health module.

This file verifies the overall health check functionality by mocking individual checks
and ensuring the aggregated result reports success when all mocks pass.
"""

import pytest

from ttskit.health import HealthChecker


@pytest.mark.asyncio
async def test_health_run_all_checks_with_monkeypatch(monkeypatch):
    """Tests the HealthChecker's run_all_checks method under mocked successful conditions.

    Mocks all individual check methods to return True, then verifies that the overall result
    is True and all check sub-results are True.

    Parameters:
    - monkeypatch: Pytest fixture for patching methods.

    Behavior:
    - Patches check_ffmpeg, check_engines, etc., to mock_check (async returns True).
    - Runs run_all_checks and asserts overall=True and all checks pass.
    """
    hc = HealthChecker()

    async def mock_check():
        return True

    monkeypatch.setattr(hc, "check_ffmpeg", mock_check)
    monkeypatch.setattr(hc, "check_engines", mock_check)
    monkeypatch.setattr(hc, "check_redis", mock_check)
    monkeypatch.setattr(hc, "check_configuration", mock_check)
    monkeypatch.setattr(hc, "check_temp_directory", mock_check)
    monkeypatch.setattr(hc, "check_cache", mock_check)
    monkeypatch.setattr(hc, "check_metrics", mock_check)
    monkeypatch.setattr(hc, "check_performance", mock_check)

    result = await hc.run_all_checks()
    assert result["overall"] is True
    assert all(result["checks"].values())
