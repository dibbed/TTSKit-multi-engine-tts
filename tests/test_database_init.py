"""Tests for ttskit.database.init_db module (fully mocked)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestInitDatabase:
    """Test cases for database initialization logic."""

    @pytest.mark.asyncio
    async def test_init_database_async_creates_defaults(self):
        """When admin/demo and their keys are missing, they must be created."""
        mock_session = AsyncMock()
        mock_session.close = AsyncMock()

        async def mock_get_async_session_context():
            return mock_session

        mock_user_service_cls = MagicMock()
        mock_user_service = MagicMock()
        mock_user_service.get_user_by_id = AsyncMock(side_effect=[None, None])
        mock_user_service.create_user = AsyncMock(
            side_effect=[MagicMock(user_id="admin"), MagicMock(user_id="demo-user")]
        )
        mock_user_service.get_user_api_keys = AsyncMock(side_effect=[[], []])
        mock_user_service.create_api_key = AsyncMock(
            side_effect=[{"api_key": "admin_key"}, {"api_key": "demo_key"}]
        )
        mock_user_service_cls.return_value = mock_user_service

        with (
            patch(
                "ttskit.database.init_db.create_tables_async", new=AsyncMock()
            ) as mock_create_tables,
            patch(
                "ttskit.database.init_db.get_async_session_context",
                new=mock_get_async_session_context,
            ),
            patch("ttskit.database.init_db.UserService", new=mock_user_service_cls),
        ):
            from ttskit.database.init_db import init_database_async

            await init_database_async()

            mock_create_tables.assert_awaited()
            assert mock_user_service.create_user.await_count == 2
            assert mock_user_service.create_api_key.await_count == 2
            mock_session.close.assert_awaited()

    def test_init_database_sync_wrapper_calls_async(self):
        """The sync wrapper must call asyncio.run with the coroutine."""
        with patch("ttskit.database.init_db.asyncio.run") as mock_run:
            from ttskit.database.init_db import init_database

            init_database()
            assert mock_run.call_count == 1

    @pytest.mark.asyncio
    async def test_init_database_async_existing_data(self):
        """When everything exists, no create calls should be made."""
        mock_session = AsyncMock()
        mock_session.close = AsyncMock()

        async def mock_get_async_session_context():
            return mock_session

        mock_user_service_cls = MagicMock()
        mock_user_service = MagicMock()
        mock_user_service.get_user_by_id = AsyncMock(
            side_effect=[MagicMock(user_id="admin"), MagicMock(user_id="demo-user")]
        )
        mock_user_service.get_user_api_keys = AsyncMock(
            side_effect=[[{"k": 1}], [{"k": 2}]]
        )
        mock_user_service.create_user = AsyncMock()
        mock_user_service.create_api_key = AsyncMock()
        mock_user_service_cls.return_value = mock_user_service

        with (
            patch(
                "ttskit.database.init_db.create_tables_async", new=AsyncMock()
            ) as mock_create_tables,
            patch(
                "ttskit.database.init_db.get_async_session_context",
                new=mock_get_async_session_context,
            ),
            patch("ttskit.database.init_db.UserService", new=mock_user_service_cls),
        ):
            from ttskit.database.init_db import init_database_async

            await init_database_async()

            mock_create_tables.assert_awaited()
            mock_user_service.create_user.assert_not_awaited()
            mock_user_service.create_api_key.assert_not_awaited()
            mock_session.close.assert_awaited()

    @pytest.mark.asyncio
    async def test_init_database_async_exception_flow_ensures_close(self):
        """If an exception occurs during operations, it should be raised and session closed."""
        mock_session = AsyncMock()
        mock_session.close = AsyncMock()

        async def mock_get_async_session_context():
            return mock_session

        mock_user_service_cls = MagicMock()
        mock_user_service = MagicMock()
        mock_user_service.get_user_by_id = AsyncMock(side_effect=[None])
        mock_user_service.create_user = AsyncMock(side_effect=RuntimeError("boom"))
        mock_user_service.get_user_api_keys = AsyncMock()
        mock_user_service.create_api_key = AsyncMock()
        mock_user_service_cls.return_value = mock_user_service

        with (
            patch("ttskit.database.init_db.create_tables_async", new=AsyncMock()),
            patch(
                "ttskit.database.init_db.get_async_session_context",
                new=mock_get_async_session_context,
            ),
            patch("ttskit.database.init_db.UserService", new=mock_user_service_cls),
        ):
            from ttskit.database.init_db import init_database_async

            with pytest.raises(RuntimeError):
                await init_database_async()

            mock_session.close.assert_awaited()

    def test_module_main_executes_sync_wrapper(self, monkeypatch):
        """Running module as __main__ should call the sync wrapper via asyncio.run."""
        import runpy

        called = {"count": 0}

        def fake_run(coro):
            called["count"] += 1
            return None

        monkeypatch.setattr("ttskit.database.init_db.asyncio.run", fake_run)

        runpy.run_module("ttskit.database.init_db", run_name="__main__")

        assert called["count"] == 1
