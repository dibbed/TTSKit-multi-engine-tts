"""Tests for the `ttskit.api.routers.system.get_version` endpoint function.

This module contains tests that directly invoke the function with a mock authentication object.
"""

from __future__ import annotations

import pytest


class _Auth:
    """Mock authentication object for testing the version endpoint.

    Provides a basic user_id attribute to simulate authenticated requests.
    """

    def __init__(self):
        self.user_id = "u"


"""Test the basic functionality of the get_version endpoint.

Verifies that the response includes the service name 'TTSKit API', a version field, and status 'running'.

Returns:
    None
"""
@pytest.mark.asyncio
async def test_get_version_basic():
    from ttskit.api.routers.system import get_version

    resp = await get_version(_Auth())
    assert (
        resp["service"] == "TTSKit API"
        and "version" in resp
        and resp["status"] == "running"
    )
