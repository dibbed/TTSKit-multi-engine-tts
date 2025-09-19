"""Tests for ttskit.database.connection without modifying source file."""

import types

import pytest

from ttskit.database import connection as db_conn


def test_get_async_database_url_sqlite_from_settings(monkeypatch):
    """Tests SQLite URL conversion from settings in get_async_database_url function."""
    monkeypatch.setattr(
        db_conn,
        "get_settings",
        lambda: types.SimpleNamespace(
            database_url="sqlite:///memory.db",
            database_path="ttskit.db",
            database_echo=False,
        ),
    )
    assert db_conn.get_async_database_url() == "sqlite+aiosqlite:///memory.db"


def test_get_async_database_url_sqlite_from_env(monkeypatch):
    """Tests SQLite URL conversion from environment variable in get_async_database_url function."""
    monkeypatch.setattr(
        db_conn,
        "get_settings",
        lambda: types.SimpleNamespace(
            database_url=None, database_path="ttskit.db", database_echo=False
        ),
    )
    monkeypatch.setenv("DATABASE_URL", "sqlite:///env.db")
    assert db_conn.get_async_database_url() == "sqlite+aiosqlite:///env.db"


def test_get_async_database_url_postgres(monkeypatch):
    """Tests PostgreSQL URL conversion in get_async_database_url function."""
    monkeypatch.setattr(
        db_conn,
        "get_settings",
        lambda: types.SimpleNamespace(
            database_url="postgresql://user:pass@localhost:5432/db",
            database_path="ttskit.db",
            database_echo=False,
        ),
    )
    assert (
        db_conn.get_async_database_url()
        == "postgresql+asyncpg://user:pass@localhost:5432/db"
    )


def test_get_async_database_url_others_passthrough(monkeypatch):
    """Tests other database URL passthrough in get_async_database_url function."""
    monkeypatch.setattr(
        db_conn,
        "get_settings",
        lambda: types.SimpleNamespace(
            database_url="mysql://user:pass@host/db",
            database_path="ttskit.db",
            database_echo=False,
        ),
    )
    assert db_conn.get_async_database_url() == "mysql://user:pass@host/db"


def test_create_tables_calls_metadata_create_all(monkeypatch):
    """Tests that create_tables function calls Base.metadata.create_all with correct engine."""
    sentinel_engine = object()
    monkeypatch.setattr(db_conn, "get_engine", lambda: sentinel_engine)

    called = {"bind": None}

    class DummyMeta:
        def create_all(self, bind=None):
            called["bind"] = bind

    monkeypatch.setattr(db_conn.Base, "metadata", DummyMeta())

    db_conn.create_tables()
    assert called["bind"] is sentinel_engine


def test_get_engine_postgres_branch(monkeypatch):
    """Tests PostgreSQL engine creation with pool settings in get_engine function."""
    monkeypatch.setattr(
        db_conn,
        "get_settings",
        lambda: types.SimpleNamespace(
            database_url="postgresql://u:p@h:5432/db",
            database_path="ttskit.db",
            database_echo=True,
            database_pool_size=7,
            database_max_overflow=3,
        ),
    )

    captured = {}

    def fake_create_engine(url, echo, pool_pre_ping, pool_size, max_overflow):
        captured.update(
            dict(
                url=url,
                echo=echo,
                pool_pre_ping=pool_pre_ping,
                pool_size=pool_size,
                max_overflow=max_overflow,
            )
        )
        return object()

    monkeypatch.setattr(db_conn, "create_engine", fake_create_engine)

    _ = db_conn.get_engine()
    assert captured["url"].startswith("postgresql://")
    assert captured["echo"] is True
    assert captured["pool_pre_ping"] is True
    assert captured["pool_size"] == 7
    assert captured["max_overflow"] == 3


@pytest.mark.asyncio
async def test_get_async_engine_postgres_branch(monkeypatch):
    """Tests PostgreSQL async engine creation with pool settings in get_async_engine function."""
    monkeypatch.setattr(
        db_conn,
        "get_settings",
        lambda: types.SimpleNamespace(
            database_url="postgresql://u:p@h:5432/db",
            database_path="ttskit.db",
            database_echo=False,
            database_pool_size=9,
            database_max_overflow=4,
        ),
    )

    captured = {}

    def fake_create_async_engine(url, echo, pool_pre_ping, pool_size, max_overflow):
        captured.update(
            dict(
                url=url,
                echo=echo,
                pool_pre_ping=pool_pre_ping,
                pool_size=pool_size,
                max_overflow=max_overflow,
            )
        )
        return object()

    monkeypatch.setattr(db_conn, "create_async_engine", fake_create_async_engine)

    _ = db_conn.get_async_engine()
    assert captured["url"].startswith("postgresql+asyncpg://") or captured[
        "url"
    ].startswith("postgresql://")
    assert captured["pool_pre_ping"] is True
    assert captured["pool_size"] == 9
    assert captured["max_overflow"] == 4


@pytest.mark.asyncio
async def test_create_tables_async_success(monkeypatch):
    """Tests successful async table creation in create_tables_async function."""
    run_sync_called = {"called": False}
    dispose_calls = {"count": 0}

    class FakeConn:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def run_sync(self, fn):
            run_sync_called["called"] = True
            return None

    class FakeBeginCtx:
        def __init__(self):
            self._conn = FakeConn()

        async def __aenter__(self):
            return self._conn

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeAsyncEngine:
        def begin(self):
            return FakeBeginCtx()

        async def dispose(self):
            dispose_calls["count"] += 1

    fake_engine = FakeAsyncEngine()
    monkeypatch.setattr(db_conn, "get_async_engine", lambda: fake_engine)

    await db_conn.create_tables_async()
    assert run_sync_called["called"] is True
    assert dispose_calls["count"] == 1


@pytest.mark.asyncio
async def test_create_tables_async_exception_path(monkeypatch):
    """Tests exception handling in create_tables_async function."""
    dispose_calls = {"count": 0}

    class FakeConn:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def run_sync(self, fn):
            raise RuntimeError("boom")

    class FakeBeginCtx:
        def __init__(self):
            self._conn = FakeConn()

        async def __aenter__(self):
            return self._conn

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeAsyncEngine:
        def begin(self):
            return FakeBeginCtx()

        async def dispose(self):
            dispose_calls["count"] += 1

    fake_engine = FakeAsyncEngine()
    monkeypatch.setattr(db_conn, "get_async_engine", lambda: fake_engine)

    with pytest.raises(RuntimeError):
        await db_conn.create_tables_async()
    assert dispose_calls["count"] == 2


@pytest.mark.asyncio
async def test_get_async_session_normal_flow(monkeypatch):
    """Tests normal flow of get_async_session generator function."""
    class FakeAsyncSession:
        def __init__(self):
            self.closed = False
            self.rolled_back = False

        async def close(self):
            self.closed = True

        async def rollback(self):
            self.rolled_back = True

    def fake_sessionmaker():
        return FakeAsyncSession()

    monkeypatch.setattr(
        db_conn, "get_async_session_local", lambda: lambda: FakeAsyncSession()
    )

    agen = db_conn.get_async_session()
    session = await agen.__anext__()
    assert isinstance(session, FakeAsyncSession)
    await agen.aclose()
    assert session.closed is True
    assert session.rolled_back is False


@pytest.mark.asyncio
async def test_get_async_session_exception_flow(monkeypatch):
    """Tests exception handling flow of get_async_session generator function."""
    class FakeAsyncSession:
        def __init__(self):
            self.closed = False
            self.rolled_back = False

        async def close(self):
            self.closed = True

        async def rollback(self):
            self.rolled_back = True

    monkeypatch.setattr(
        db_conn, "get_async_session_local", lambda: lambda: FakeAsyncSession()
    )

    agen = db_conn.get_async_session()
    session = await agen.__anext__()
    with pytest.raises(RuntimeError):
        await agen.athrow(RuntimeError("fail"))
    assert session.rolled_back is True
    assert session.closed is True


@pytest.mark.asyncio
async def test_get_async_session_context_returns_session(monkeypatch):
    """Tests that get_async_session_context function returns session instance."""
    class FakeAsyncSession:
        pass

    monkeypatch.setattr(
        db_conn, "get_async_session_local", lambda: lambda: FakeAsyncSession()
    )
    session = await db_conn.get_async_session_context()
    assert isinstance(session, FakeAsyncSession)


def test_get_session_normal_and_exception_flows(monkeypatch):
    """Tests both normal and exception flows of get_session generator function."""
    class FakeSyncSession:
        def __init__(self):
            self.closed = False
            self.rolled_back = False

        def close(self):
            self.closed = True

        def rollback(self):
            self.rolled_back = True

    monkeypatch.setattr(db_conn, "SessionLocal", lambda: FakeSyncSession())

    gen = db_conn.get_session()
    session = next(gen)
    assert isinstance(session, FakeSyncSession)
    gen.close()
    assert session.closed is True
    assert session.rolled_back is False

    monkeypatch.setattr(db_conn, "SessionLocal", lambda: FakeSyncSession())
    gen2 = db_conn.get_session()
    session2 = next(gen2)
    with pytest.raises(RuntimeError):
        gen2.throw(RuntimeError("fail"))
    assert session2.rolled_back is True
    assert session2.closed is True


@pytest.mark.asyncio
async def test_get_async_session_context_exception_branch(monkeypatch):
    """Tests exception handling in get_async_session_context function."""
    def raising_session_maker():
        raise RuntimeError("maker boom")

    monkeypatch.setattr(
        db_conn, "get_async_session_local", lambda: raising_session_maker
    )

    with pytest.raises(Exception):
        await db_conn.get_async_session_context()
