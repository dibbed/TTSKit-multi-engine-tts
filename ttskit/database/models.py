"""Database models for TTSKit using SQLAlchemy ORM.

Defines the User, APIKey, and UserSession models with relationships, security features (e.g., hashed API keys), and tracking fields.
Supports SQLite and PostgreSQL via declarative base.
"""

import hashlib
import secrets
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class User(Base):
    """Represents a user in the TTSKit system.

    Includes authentication details, admin status, timestamps, and relationships to API keys and sessions.
    Automatically manages creation/update timestamps and supports optional fields like username and email.

    Attributes:
        id: Primary key.
        user_id: Unique identifier (str).
        username: Optional display name.
        email: Optional contact email.
        is_active: Default True.
        is_admin: Default False.
        created_at: Auto-set on creation.
        updated_at: Auto-updated on changes.
        last_login: Optional timestamp.
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    api_keys: Mapped[list["APIKey"]] = relationship(
        "APIKey", back_populates="user", cascade="all, delete-orphan"
    )
    sessions: Mapped[list["UserSession"]] = relationship(
        "UserSession", back_populates="user", cascade="all, delete-orphan"
    )


class APIKey(Base):
    """Represents an API key for user authentication with security best practices.

    Stores only hashed keys (no plain text), supports permissions (JSON), expiration, usage tracking, and relationships to users.
    Includes methods for generation, hashing, verification, and validity checks.

    Attributes:
        id: Primary key.
        user_id: Foreign key to User.
        api_key_hash: Unique SHA-256 hash with salt.
        permissions: JSON string of allowed actions.
        is_active: Default True.
        created_at: Auto-set.
        updated_at: Auto-updated.
        last_used: Optional timestamp.
        expires_at: Optional expiration.
        usage_count: Default 0, increments on use.
    """
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("users.user_id"), index=True
    )
    api_key_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    permissions: Mapped[str] = mapped_column(Text)  # JSON string
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )
    last_used: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    usage_count: Mapped[int] = mapped_column(default=0)  # Track usage for security

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="api_keys")

    @staticmethod
    def generate_api_key() -> str:
        """Generate a secure, random API key prefixed with 'ttskit_'.

        Uses URL-safe tokens for compatibility.

        Returns:
            str: The generated API key.
        """
        return f"ttskit_{secrets.token_urlsafe(32)}"

    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """Hash the API key using SHA-256 with a fixed salt for secure storage.

        Args:
            api_key: The plain text API key to hash.

        Returns:
            str: The hexadecimal hash.
        """
        salt = "ttskit_salt_2024"
        return hashlib.sha256(f"{api_key}{salt}".encode()).hexdigest()

    @staticmethod
    def verify_api_key_hash(api_key: str, stored_hash: str) -> bool:
        """Verify if the provided API key matches the stored hash.

        Args:
            api_key: The plain text API key to verify.
            stored_hash: The hashed value from the database.

        Returns:
            bool: True if they match, False otherwise.
        """
        return stored_hash == APIKey.hash_api_key(api_key)

    def verify_api_key(self, api_key: str) -> bool:
        """Verify the provided API key against this instance's stored hash.

        Args:
            api_key: The plain text API key to check.

        Returns:
            bool: True if valid for this key, False otherwise.
        """
        return self.verify_api_key_hash(api_key, self.api_key_hash)

    def is_expired(self) -> bool:
        """Check if this API key has expired.

        Returns:
            bool: True if expired (or no expiration set), False if valid.
        """
        if not self.expires_at:
            return False
        return self.expires_at < datetime.now(timezone.utc)

    def is_valid(self) -> bool:
        """Check if this API key is currently valid (active and not expired).

        Returns:
            bool: True if usable, False otherwise.
        """
        return self.is_active and not self.is_expired()


class UserSession(Base):
    """Represents a user session for tracking activity and usage in TTSKit.

    Captures session details like ID, IP, user agent, timestamps, and links to the user.
    Supports optional fields and automatic timestamps.

    Attributes:
        id: Primary key.
        user_id: Foreign key to User.
        session_id: Unique identifier.
        ip_address: Optional IPv4/IPv6.
        user_agent: Optional string.
        created_at: Auto-set.
        last_activity: Auto-set on creation, update as needed.
        is_active: Default True.
    """
    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("users.user_id"), index=True
    )
    session_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    last_activity: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="sessions")

    @staticmethod
    def generate_session_id() -> str:
        """Generate a secure, random session ID.

        Uses URL-safe tokens for compatibility.

        Returns:
            str: The generated session ID.
        """
        return secrets.token_urlsafe(32)
