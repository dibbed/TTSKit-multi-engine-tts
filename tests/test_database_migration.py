"""Tests for ttskit.database.migration module (fully mocked)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestDatabaseMigration:
    """Test cases for database migration and security checks."""

    @pytest.mark.asyncio
    async def test_migrate_api_keys_security_table_missing(self):
        """If table does not exist, migration should exit early without error."""
        mock_session = AsyncMock()
        mock_session.close = AsyncMock()

        def make_execute_without_table(sql, *args, **kwargs):
            mock_result = MagicMock()
            if "sqlite_master" in str(sql):
                mock_result.fetchone.return_value = None
            return mock_result

        mock_session.execute.side_effect = make_execute_without_table

        async def mock_get_async_session_context():
            return mock_session

        with patch(
            "ttskit.database.migration.get_async_session_context",
            new=mock_get_async_session_context,
        ):
            from ttskit.database.migration import migrate_api_keys_security

            await migrate_api_keys_security()

            mock_session.close.assert_awaited()

    @pytest.mark.asyncio
    async def test_migrate_api_keys_security_with_plain_and_add_usage_count(self):
        """When plain column exists, it should be nulled and usage_count added if missing."""
        mock_session = AsyncMock()
        mock_session.close = AsyncMock()
        mock_session.commit = AsyncMock()

        result_table_exists = MagicMock()
        result_table_exists.fetchone.return_value = ("api_keys",)

        result_table_info = MagicMock()
        result_table_info.fetchall.return_value = [
            (0, "id", None, None, None, None),
            (1, "user_id", None, None, None, None),
            (2, "api_key_plain", None, None, None, None),
        ]

        result_select_plain = MagicMock()
        result_select_plain.fetchall.return_value = [
            (1, "plain1"),
            (2, "plain2"),
        ]

        generic_result = MagicMock()

        mock_session.execute.side_effect = [
            result_table_exists,
            result_table_info,
            result_select_plain,
            generic_result,
            generic_result,
            generic_result,
        ]

        async def mock_get_async_session_context():
            return mock_session

        with (
            patch(
                "ttskit.database.migration.get_async_session_context",
                new=mock_get_async_session_context,
            ),
            patch("ttskit.database.migration.get_logger") as mock_get_logger,
        ):
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            from ttskit.database.migration import migrate_api_keys_security

            await migrate_api_keys_security()

            assert mock_session.execute.call_count >= 6
            mock_session.commit.assert_awaited()
            mock_session.close.assert_awaited()

    @pytest.mark.asyncio
    async def test_migrate_api_keys_security_already_migrated_and_usage_exists(self):
        """If no plain column and usage_count exists, function should just finish."""
        mock_session = AsyncMock()
        mock_session.close = AsyncMock()
        mock_session.commit = AsyncMock()

        result_table_exists = MagicMock()
        result_table_exists.fetchone.return_value = ("api_keys",)

        result_table_info = MagicMock()
        result_table_info.fetchall.return_value = [
            (0, "id", None, None, None, None),
            (1, "user_id", None, None, None, None),
            (2, "usage_count", None, None, None, None),
        ]

        mock_session.execute.side_effect = [
            result_table_exists,
            result_table_info,
        ]

        async def mock_get_async_session_context():
            return mock_session

        with patch(
            "ttskit.database.migration.get_async_session_context",
            new=mock_get_async_session_context,
        ):
            from ttskit.database.migration import migrate_api_keys_security

            await migrate_api_keys_security()

            assert mock_session.execute.call_count == 2
            mock_session.close.assert_awaited()

    @pytest.mark.asyncio
    async def test_check_database_security_flows(self):
        """Exercise different branches of check_database_security with mocks."""
        mock_session1 = AsyncMock()
        mock_session1.close = AsyncMock()
        result_no_table = MagicMock()
        result_no_table.fetchone.return_value = None
        mock_session1.execute.side_effect = [result_no_table]

        async def get_ctx1():
            return mock_session1

        with patch("ttskit.database.migration.get_async_session_context", new=get_ctx1):
            from ttskit.database.migration import check_database_security

            await check_database_security()
            mock_session1.close.assert_awaited()

        mock_session2 = AsyncMock()
        mock_session2.close = AsyncMock()
        result_table_exists = MagicMock()
        result_table_exists.fetchone.return_value = ("api_keys",)

        result_table_info_with_plain = MagicMock()
        result_table_info_with_plain.fetchall.return_value = [
            (0, "id", None, None, None, None),
            (1, "api_key_plain", None, None, None, None),
        ]

        result_plain_count = MagicMock()
        result_plain_count.scalar.return_value = 3

        mock_session2.execute.side_effect = [
            result_table_exists,
            result_table_info_with_plain,
            result_plain_count,
        ]

        async def get_ctx2():
            return mock_session2

        with patch("ttskit.database.migration.get_async_session_context", new=get_ctx2):
            from ttskit.database.migration import check_database_security

            await check_database_security()
            mock_session2.close.assert_awaited()

    @pytest.mark.asyncio
    async def test_migrate_api_keys_security_exception_triggers_rollback(self):
        """On unexpected exception, error should be raised after rollback."""
        mock_session = AsyncMock()
        mock_session.close = AsyncMock()
        mock_session.rollback = AsyncMock()

        result_table_exists = MagicMock()
        result_table_exists.fetchone.return_value = ("api_keys",)

        result_table_info = MagicMock()
        result_table_info.fetchall.return_value = [
            (0, "id", None, None, None, None),
            (1, "api_key_plain", None, None, None, None),
        ]

        mock_session.execute.side_effect = [
            result_table_exists,
            result_table_info,
            RuntimeError("unexpected failure"),
        ]

        async def mock_get_async_session_context():
            return mock_session

        with patch(
            "ttskit.database.migration.get_async_session_context",
            new=mock_get_async_session_context,
        ):
            from ttskit.database.migration import migrate_api_keys_security

            with pytest.raises(RuntimeError):
                await migrate_api_keys_security()

            mock_session.rollback.assert_awaited()
            mock_session.close.assert_awaited()

    @pytest.mark.asyncio
    async def test_migrate_api_keys_security_handles_alter_duplicate_column(self):
        """If ALTER fails with duplicate column, it should not raise."""
        mock_session = AsyncMock()
        mock_session.close = AsyncMock()
        mock_session.commit = AsyncMock()

        result_table_exists = MagicMock()
        result_table_exists.fetchone.return_value = ("api_keys",)

        result_table_info = MagicMock()
        result_table_info.fetchall.return_value = [
            (0, "id", None, None, None, None),
            (1, "api_key_plain", None, None, None, None),
        ]

        result_select_plain = MagicMock()
        result_select_plain.fetchall.return_value = []

        async def raise_duplicate(*args, **kwargs):
            raise Exception("duplicate column name: usage_count")

        mock_session.execute.side_effect = [
            result_table_exists,
            result_table_info,
            result_select_plain,
            raise_duplicate,
        ]

        async def mock_get_async_session_context():
            return mock_session

        with patch(
            "ttskit.database.migration.get_async_session_context",
            new=mock_get_async_session_context,
        ):
            from ttskit.database.migration import migrate_api_keys_security

            await migrate_api_keys_security()

            mock_session.close.assert_awaited()

    def test_module_main_runs_all(self, monkeypatch):
        """__main__ should run main() which orchestrates calls via asyncio.run."""
        import runpy

        called = {"count": 0}

        def fake_run(coro):
            called["count"] += 1
            return None

        monkeypatch.setattr("ttskit.database.migration.asyncio.run", fake_run)

        runpy.run_module("ttskit.database.migration", run_name="__main__")

        assert called["count"] == 1

    @pytest.mark.asyncio
    async def test_migrate_api_keys_security_alter_raises_other_error(self):
        """If ALTER fails with a non-duplicate error, it should raise and rollback."""
        mock_session = AsyncMock()
        mock_session.close = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()

        result_table_exists = MagicMock()
        result_table_exists.fetchone.return_value = ("api_keys",)

        result_table_info = MagicMock()
        result_table_info.fetchall.return_value = [
            (0, "id", None, None, None, None),
            (1, "api_key_plain", None, None, None, None),
        ]

        result_select_plain = MagicMock()
        result_select_plain.fetchall.return_value = []

        mock_session.execute.side_effect = [
            result_table_exists,
            result_table_info,
            result_select_plain,
            Exception("some other error"),
        ]

        async def mock_get_async_session_context():
            return mock_session

        with patch(
            "ttskit.database.migration.get_async_session_context",
            new=mock_get_async_session_context,
        ):
            from ttskit.database.migration import migrate_api_keys_security

            with pytest.raises(Exception):
                await migrate_api_keys_security()

            mock_session.rollback.assert_awaited()
            mock_session.close.assert_awaited()
