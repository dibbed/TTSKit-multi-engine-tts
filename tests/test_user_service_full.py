"""Tests covering the full functionality of the UserService class.

This file includes exhaustive tests for both async and sync database operations,
focusing on user management, API keys, and various success/error scenarios.
We use simulated AsyncSession to ensure thorough coverage.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from sqlalchemy.orm import Session

from ttskit.database.models import APIKey, User
from ttskit.services.user_service import UserService


class _FakeResult:
    """A mock result object that mimics what AsyncSession.execute returns from a database query.

    This is used in testing to simulate the DB layer without actual queries.
    """

    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def scalars(self):
        class _Scalars:
            def __init__(self, rows):
                self._rows = rows

            def all(self):
                return list(self._rows)

        return _Scalars(self._rows)

    def scalar_one_or_none(self):
        return self._rows[0] if self._rows else None


class _FakeAsyncSession:
    """A mock AsyncSession that wraps a real sync Session for testing purposes.

    It supports the specific methods UserService uses, making async tests possible.
    """

    def __init__(self, sync_session: Session) -> None:
        self._sync = sync_session

    def add(self, obj: Any) -> None:
        self._sync.add(obj)

    async def commit(self) -> None:
        self._sync.commit()

    async def refresh(self, obj: Any) -> None:
        self._sync.refresh(obj)

    async def delete(self, obj: Any) -> None:
        self._sync.delete(obj)

    async def execute(self, stmt) -> _FakeResult:
        model = stmt.columns_clause_froms[0].entity_namespace
        rows: list[Any] = []
        if model is User:
            query = self._sync.query(User)
            for crit in getattr(stmt, "_where_criteria", []):
                if "user_id" in str(crit):
                    params = dict(stmt.compile().params)
                    value = params.get("user_id_1") or params.get("user_id")
                    if value is not None:
                        query = query.filter(User.user_id == value)
            rows = list(query.all())
        elif model is APIKey:
            query = self._sync.query(APIKey)
            for crit in getattr(stmt, "_where_criteria", []):
                s = str(crit)
                params = dict(stmt.compile().params)
                if "api_key_hash" in s:
                    value = params.get("api_key_hash_1") or params.get("api_key_hash")
                    if value is not None:
                        query = query.filter(APIKey.api_key_hash == value)
                if "user_id" in s and "api_key_hash" not in s:
                    value = params.get("user_id_1") or params.get("user_id")
                    if value is not None:
                        query = query.filter(APIKey.user_id == value)
                if "id" in s:
                    value = params.get("id_1") or params.get("id")
                    if value is not None:
                        query = query.filter(APIKey.id == value)
            rows = list(query.all())
        return _FakeResult(rows)


@pytest.mark.asyncio
async def test_user_lifecycle_sync_session(test_db: Session):
    """Tests the complete user lifecycle with a sync database session.

    This includes creating users (and checking for duplicates), retrieving users,
    updating profiles, managing API keys, and deleting users. It verifies
    proper data handling and error cases like non-existent users.

    Parameters
        test_db (Session): Database session fixture for tests.

    Returns
        None (asserts are the main goal here)
    """
    service = UserService(test_db)

    user = await service.create_user(
        "u1", username="U1", email="u1@test", is_admin=False
    )
    assert user.user_id == "u1" and user.username == "U1"

    with pytest.raises(ValueError):
        await service.create_user("u1")

    got = await service.get_user_by_id("u1")
    assert got and got.user_id == "u1"

    all_users = await service.get_all_users()
    assert any(u.user_id == "u1" for u in all_users)

    updated = await service.update_user(
        "u1", email="new@test", is_admin=True, is_active=True
    )
    assert updated and updated.email == "new@test" and updated.is_admin is True

    assert await service.update_user("missing") is None

    key_info = await service.create_api_key("u1", permissions=["read"])
    assert key_info and key_info["api_key"] and key_info["id"]

    keys = await service.get_user_api_keys("u1")
    assert len(keys) >= 1

    key_hash = keys[0].api_key_hash
    found = await service.get_api_key_by_hash(key_hash)
    assert found and found.user_id == "u1"

    updated_key = await service.update_api_key(
        "u1", keys[0].id, permissions=["read", "write"], is_active=True, expires_at=None
    )
    assert updated_key and json.loads(updated_key.permissions) == ["read", "write"]

    ok = await service.delete_api_key("u1", keys[0].id)
    assert ok is True

    assert await service.delete_api_key("u1", 99999) is False

    assert await service.verify_api_key("nonexistent") is None

    assert await service.delete_user("u1") is True

    assert await service.delete_user("u1") is False


@pytest.mark.asyncio
async def test_verify_api_key_paths_and_permissions_with_async_session(
    monkeypatch, test_db: Session
):
    """Tests API key validation and permissions with an async session setup.

    We set up an admin user with various types of API keys (valid, expired, broken) and
    check that verification works as expected. Good keys return user and perms;
    bad ones return None; weirdly formatted perms still get defaults.

    Parameters
        monkeypatch: Mocking tool for injecting our session.
        test_db (Session): Test database connection.

    Returns
        None (focuses on assertions)
    """
    user_admin = User(
        user_id="adminu", username="A", email="a@a", is_admin=True, is_active=True
    )
    test_db.add(user_admin)
    test_db.commit()

    plain = APIKey.generate_api_key()
    hashed = APIKey.hash_api_key(plain)
    key = APIKey(
        user_id="adminu",
        api_key_hash=hashed,
        permissions=json.dumps(["read"]),
        is_active=True,
    )
    test_db.add(key)
    test_db.commit()

    expired_plain = "expired_plain"
    expired = APIKey(
        user_id="adminu",
        api_key_hash=APIKey.hash_api_key(expired_plain),
        permissions='["read"]',
        is_active=True,
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    test_db.add(expired)
    test_db.commit()

    bad_plain = "badperm_plain"
    bad = APIKey(
        user_id="adminu",
        api_key_hash=APIKey.hash_api_key(bad_plain),
        permissions="not-json",
        is_active=True,
    )
    test_db.add(bad)
    test_db.commit()

    async_db = _FakeAsyncSession(test_db)

    import ttskit.services.user_service as us_mod

    class _MarkerAsyncSession(type(async_db)):
        pass

    monkeypatch.setattr(us_mod, "AsyncSession", (type(async_db)))

    service = UserService(async_db)

    verified = await service.verify_api_key(plain)
    assert (
        verified
        and verified["user_id"] == "adminu"
        and "admin" in verified["permissions"]
    )

    assert await service.verify_api_key("wrong") is None

    assert await service.verify_api_key(expired_plain) is None

    res = await service.verify_api_key(bad_plain)
    assert res and set(res["permissions"]) >= {"read", "write", "admin"}


@pytest.mark.asyncio
async def test_create_get_update_delete_user_with_async_session(
    monkeypatch, test_db: Session
):
    """Tests basic CRUD for users with an async session.

    Creates, fetches, updates, and deletes a test user, ensuring everything works smoothly.
    Also checks that deleting a non-existent user is handled gracefully.

    Parameters
        monkeypatch: Used to patch in our fake session.
        test_db (Session): Database session for the tests.

    Returns
        None (assertions confirm success)
    """
    async_db = _FakeAsyncSession(test_db)
    import ttskit.services.user_service as us_mod

    monkeypatch.setattr(us_mod, "AsyncSession", (type(async_db)))

    service = UserService(async_db)

    u = await service.create_user("ax", username=None, email=None, is_admin=False)
    assert u.user_id == "ax"

    u2 = await service.update_user("ax", username="AX", is_active=True)
    assert u2 and u2.username == "AX"

    got = await service.get_user_by_id("ax")
    assert got and got.user_id == "ax"

    lst = await service.get_all_users()
    assert any(x.user_id == "ax" for x in lst)

    assert await service.delete_user("ax") is True

    assert await service.delete_user("ax") is False


@pytest.mark.asyncio
async def test_user_service_async_success_paths_cover_commits(
    test_db: Session, monkeypatch
):
    """Tests the happy path for async operations in UserService.

    Simulates successful user and API key operations: creation, getting, updating, and deleting.
    Ensures commits are triggered and results are as expected.

    Parameters
        test_db (Session): Test DB fixture.
        monkeypatch: For setting up the mock session.

    Returns
        None (verifies through assertions)
    """
    async_db = _FakeAsyncSession(test_db)
    import ttskit.services.user_service as us_mod

    monkeypatch.setattr(us_mod, "AsyncSession", (type(async_db)))

    service = UserService(async_db)

    u = await service.create_user("au", username=None, email=None, is_admin=False)
    assert u.user_id == "au"

    key_info = await service.create_api_key("au", permissions=["read"])
    assert key_info and key_info["id"]

    keys = await service.get_user_api_keys("au")
    ak = keys[0]
    got = await service.get_api_key_by_hash(ak.api_key_hash)
    assert got and got.id == ak.id

    updated = await service.update_api_key(
        "au", ak.id, permissions=["read", "write"], is_active=True, expires_at=None
    )
    assert updated and updated.is_active is True

    ok = await service.delete_api_key("au", ak.id)
    assert ok is True


@pytest.mark.asyncio
async def test_user_service_additional_none_and_inactive_paths(
    monkeypatch, test_db: Session
):
    """Tests edge cases for API key updates and inactive users.

    Checks that trying to update keys for missing users returns None,
    and verifying keys from deactivated users also returns None.

    Parameters
        monkeypatch: Pytest's mocking helper.
        test_db (Session): Test database session.

    Returns
        None (asserts the desired None returns)
    """
    async_db = _FakeAsyncSession(test_db)
    import ttskit.services.user_service as us_mod

    monkeypatch.setattr(us_mod, "AsyncSession", (type(async_db)))
    service = UserService(async_db)

    none_update = await service.update_api_key(
        "nouser", 999, permissions=None, is_active=None, expires_at=None
    )
    assert none_update is None

    u = User(
        user_id="inactive", username=None, email=None, is_admin=False, is_active=False
    )
    test_db.add(u)
    test_db.commit()
    plain = APIKey.generate_api_key()
    hashed = APIKey.hash_api_key(plain)
    k = APIKey(
        user_id="inactive", api_key_hash=hashed, permissions='["read"]', is_active=True
    )
    test_db.add(k)
    test_db.commit()
    assert await service.verify_api_key(plain) is None


@pytest.mark.asyncio
async def test_user_service_error_branches_and_returns(monkeypatch, test_db: Session):
    """Tests error handling and fallbacks in UserService methods.

    Simulates DB errors, missing data, and async failures to confirm
    we return None gracefully or raise appropriate exceptions.

    Parameters
        monkeypatch: For patching methods during tests.
        test_db (Session): Database session fixture.

    Returns
        None (error testing focuses on exceptions and returns)
    """
    service = UserService(test_db)

    class _BadSession:
        def query(self, *a, **k):
            raise RuntimeError("bad query")

    bad_service = UserService(_BadSession())
    assert await bad_service.get_user_by_id("x") is None

    assert await bad_service.get_all_users() == []

    async def bad_get(*a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr(service, "get_user_by_id", bad_get)
    with pytest.raises(RuntimeError):
        await service.update_user("u")

    monkeypatch.setattr(service, "get_user_by_id", bad_get)
    with pytest.raises(RuntimeError):
        await service.delete_user("u")

    service2 = UserService(test_db)

    async def none_get(uid: str):
        return None

    monkeypatch.setattr(service2, "get_user_by_id", none_get)
    with pytest.raises(ValueError):
        await service2.create_api_key("nope", permissions=["read"])

    class _BadExec:
        def execute(self, *a, **k):
            raise RuntimeError("x")

    bad_async = _FakeAsyncSession(test_db)

    async def bad_execute(stmt):
        raise RuntimeError("x")

    bad_async.execute = bad_execute
    import ttskit.services.user_service as us_mod

    monkeypatch.setattr(us_mod, "AsyncSession", (type(bad_async)))
    s3 = UserService(bad_async)
    assert await s3.get_api_key_by_hash("h") is None

    assert await s3.get_user_api_keys("u") == []

    async def bad_exec2(stmt):
        raise RuntimeError("y")

    bad_async2 = _FakeAsyncSession(test_db)
    bad_async2.execute = bad_exec2
    monkeypatch.setattr(us_mod, "AsyncSession", (type(bad_async2)))
    s4 = UserService(bad_async2)
    with pytest.raises(RuntimeError):
        await s4.update_api_key("u", 1)

    with pytest.raises(RuntimeError):
        await s4.delete_api_key("u", 1)

    monkeypatch.setattr(
        APIKey, "hash_api_key", lambda *_: (_ for _ in ()).throw(RuntimeError("hash"))
    )
    s5 = UserService(test_db)
    assert await s5.verify_api_key("x") is None
