"""Tests for ttskit.database.models.UserSession and APIKey to reach 100% coverage."""

import re
from datetime import datetime, timedelta, timezone

from ttskit.database.models import APIKey, UserSession


class TestUserSessionModel:
    """Test cases for UserSession model minimal behavior."""

    def test_generate_session_id_returns_secure_token(self):
        """Ensure generate_session_id returns a non-empty urlsafe token."""
        token = UserSession.generate_session_id()

        assert isinstance(token, str)
        assert len(token) >= 32
        assert re.fullmatch(r"[A-Za-z0-9_\-]+", token) is not None

    def test_multiple_session_ids_are_unique(self):
        """Two consecutive tokens should be different with extremely high probability."""
        t1 = UserSession.generate_session_id()
        t2 = UserSession.generate_session_id()
        assert t1 != t2


class TestAPIKeyModel:
    """Test cases for APIKey static helpers and validity branches."""

    def test_generate_and_hash_and_verify(self):
        api_key = APIKey.generate_api_key()
        api_hash = APIKey.hash_api_key(api_key)
        assert isinstance(api_hash, str)
        assert APIKey.verify_api_key_hash(api_key, api_hash) is True
        assert APIKey.verify_api_key_hash(api_key + "x", api_hash) is False

    def test_is_expired_and_is_valid(self):
        key = APIKey()
        key.expires_at = None
        key.is_active = True
        assert key.is_expired() is False
        assert key.is_valid() is True

        key.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        assert key.is_expired() is True
        assert key.is_valid() is False

        key.is_active = False
        key.expires_at = None
        assert key.is_valid() is False
