"""Tests for the get_async_database_url function in ttskit.database.connection.

This module covers conversions for SQLite (to aiosqlite async), PostgreSQL (to asyncpg), and passthrough for other databases like MySQL.
"""

from __future__ import annotations

import importlib


def _reload_module():
    """Reloads the ttskit.database.connection module to ensure fresh imports during tests."""

    import ttskit.database.connection as c

    importlib.reload(c)
    return c


def test_async_url_sqlite(monkeypatch):
    """Verifies that SQLite URLs are converted to use the async aiosqlite driver in get_async_database_url.



    Parameters:

        monkeypatch: Pytest fixture for mocking environment variables and attributes.



    Behavior:

        Mocks an empty DATABASE_URL and a SQLite source URL, ensuring the async version is generated correctly.

    """
    monkeypatch.setenv("DATABASE_URL", "")
    import ttskit.database.connection as c

    monkeypatch.setattr(c, "get_database_url", lambda: "sqlite:///file.db")
    assert c.get_async_database_url() == "sqlite+aiosqlite:///file.db"


def test_async_url_postgres(monkeypatch):
    """Verifies that PostgreSQL URLs are converted to use the asyncpg driver in get_async_database_url.



    Parameters:

        monkeypatch: Pytest fixture for mocking attributes.



    Behavior:

        Mocks a PostgreSQL source URL and checks that the async version starts with the correct dialect.

    """
    import ttskit.database.connection as c

    monkeypatch.setattr(c, "get_database_url", lambda: "postgresql://u:p@h/db")
    assert c.get_async_database_url().startswith("postgresql+asyncpg://")


def test_async_url_other(monkeypatch):
    """Verifies that non-SQLite/PostgreSQL URLs (like MySQL) are passed through unchanged in get_async_database_url.



    Parameters:

        monkeypatch: Pytest fixture for mocking attributes.



    Behavior:

        Mocks a MySQL source URL and ensures it remains unmodified, as it's not a supported async conversion case.

    """
    import ttskit.database.connection as c

    monkeypatch.setattr(c, "get_database_url", lambda: "mysql://u:p@h/db")
    assert c.get_async_database_url() == "mysql://u:p@h/db"
