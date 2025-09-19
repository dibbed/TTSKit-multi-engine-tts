"""Database connection and session management for TTSKit.

This module provides functions to create SQLAlchemy engines and session makers for both synchronous and asynchronous database operations.
It supports SQLite (default) and PostgreSQL, with configurable echoing, pooling for PostgreSQL, and proper session cleanup.
"""

import os
from typing import Any, Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from ..config import get_settings
from .base import Base


def get_database_url() -> str:
    """Get the database URL, prioritizing config settings, environment variables, and defaulting to SQLite.

    Returns:
        str: The fully constructed database URL.
    """
    settings = get_settings()

    if hasattr(settings, "database_url") and settings.database_url:
        return settings.database_url

    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return db_url

    db_path = getattr(settings, "database_path", None) or os.getenv(
        "DATABASE_PATH", "ttskit.db"
    )
    return f"sqlite:///{db_path}"


def get_async_database_url() -> str:
    """Convert the standard database URL to an async-compatible dialect.

    Supports SQLite (aiosqlite) and PostgreSQL (asyncpg); other dialects pass through unchanged.

    Returns:
        str: The async database URL.
    """
    db_url = get_database_url()
    if db_url.startswith("sqlite"):
        return db_url.replace("sqlite:///", "sqlite+aiosqlite:///")
    elif db_url.startswith("postgresql"):
        return db_url.replace("postgresql://", "postgresql+asyncpg://")
    return db_url


def get_engine() -> Any:
    """Create a synchronous SQLAlchemy engine with optional logging and pooling.

    Pooling (with pre-ping for health checks) is applied only for PostgreSQL; SQLite uses a basic engine.

    Returns:
        Engine: The configured synchronous database engine.
    """
    settings = get_settings()
    echo = (
        getattr(settings, "database_echo", False)
        or os.getenv("DATABASE_ECHO", "false").lower() == "true"
    )

    db_url = get_database_url()

    if db_url.startswith("postgresql"):
        return create_engine(
            db_url,
            echo=echo,
            pool_pre_ping=True,
            pool_size=getattr(settings, "database_pool_size", 5),
            max_overflow=getattr(settings, "database_max_overflow", 10),
        )
    else:
        return create_engine(db_url, echo=echo)


def get_async_engine() -> Any:
    """Create an asynchronous SQLAlchemy engine with optional logging and pooling.

    Pooling (with pre-ping for health checks) is applied only for PostgreSQL; SQLite uses a basic async engine.

    Returns:
        AsyncEngine: The configured asynchronous database engine.
    """
    settings = get_settings()
    echo = (
        getattr(settings, "database_echo", False)
        or os.getenv("DATABASE_ECHO", "false").lower() == "true"
    )

    db_url = get_async_database_url()

    if db_url.startswith("postgresql"):
        return create_async_engine(
            db_url,
            echo=echo,
            pool_pre_ping=True,
            pool_size=getattr(settings, "database_pool_size", 5),
            max_overflow=getattr(settings, "database_max_overflow", 10),
        )
    else:
        return create_async_engine(db_url, echo=echo)


def get_session_maker() -> Any:
    """Create a sessionmaker factory for synchronous database sessions.

    Configured with autocommit and autoflush disabled for explicit control.

    Returns:
        sessionmaker: The synchronous session factory bound to the engine.
    """
    return sessionmaker(autocommit=False, autoflush=False, bind=get_engine())


def get_async_session_maker() -> Any:
    """Create a sessionmaker factory for asynchronous database sessions.

    Uses AsyncSession class, with autocommit/autoflush disabled and no expiration on commit for performance.

    Returns:
        sessionmaker: The asynchronous session factory bound to the async engine.
    """
    engine = get_async_engine()
    return sessionmaker(
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
        bind=engine,
        expire_on_commit=False,
    )


SessionLocal = (
    get_session_maker()
)  # Global synchronous session maker for dependency injection


def get_async_session_local() -> Any:
    """Create a fresh async session maker using a new engine instance.

    Returns:
        sessionmaker: A new instance of the async session factory.
    """
    return get_async_session_maker()


AsyncSessionLocal = (
    get_async_session_local()
)  # Global async session maker for dependency injection


def get_session() -> Generator[Any, None, None]:
    """Provide a synchronous database session as a context generator with automatic cleanup.

    Ensures rollback on exceptions and always closes the session.

    Yields:
        Session: The database session for use in dependency injection.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


async def get_async_session():
    """Provide an asynchronous database session as a context generator with automatic cleanup.

    Ensures rollback on exceptions and always closes the session.

    Yields:
        AsyncSession: The async database session for use in dependency injection.
    """
    session_maker = get_async_session_local()
    session = session_maker()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_async_session_context():
    """Create an async database session with built-in exception handling for cleanup.

    Returns the session directly; on exceptions during creation or use, it rolls back and closes before re-raising.

    Returns:
        AsyncSession: The created async database session.

    Raises:
        Exception: The original exception after performing rollback and close.
    """
    session_maker = get_async_session_local()
    session = session_maker()
    try:
        return session
    except Exception:
        await session.rollback()
        await session.close()
        raise


def create_tables() -> None:
    """Synchronously create all defined database tables using the engine's metadata.

    This applies the schema from all Base-derived models.
    """
    Base.metadata.create_all(bind=get_engine())


async def create_tables_async():
    """Asynchronously create all defined database tables using the async engine.

    Uses a temporary connection for schema application and ensures engine disposal on errors.

    This applies the schema from all Base-derived models.
    """
    engine = get_async_engine()
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception:
        await engine.dispose()
        raise
    finally:
        await engine.dispose()
