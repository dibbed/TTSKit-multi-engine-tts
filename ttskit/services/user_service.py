"""User service module for TTSKit.

This module handles user and API key management, including creation, retrieval, updates, and deletions.
It supports both synchronous and asynchronous SQLAlchemy sessions for flexible database interactions.
"""

import json
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from ..database.models import APIKey, User
from ..utils.logging_config import get_logger

logger = get_logger(__name__)


class UserService:
    """Manages users and API keys for the TTSKit application.

    This class provides methods for CRUD operations on users and API keys.
    It works with both synchronous and asynchronous database sessions,
    adapting queries and commits accordingly for different environments.
    """

    def __init__(self, db_session: Session | AsyncSession):
        self.db = db_session

    async def create_user(
        self,
        user_id: str,
        username: Optional[str] = None,
        email: Optional[str] = None,
        is_admin: bool = False,
    ) -> User:
        """Creates a new user account.

        Args:
            user_id: Unique identifier for the user (str).
            username: Optional username for the user (str).
            email: Optional email address for the user (str).
            is_admin: Flag indicating if the user has admin privileges (bool, default False).

        Returns:
            The newly created User object.

        Raises:
            ValueError: If a user with the given user_id already exists.

        Notes:
            Performs an existence check before creating the user to avoid duplicates.
            Adds the user to the database session, commits the changes, and refreshes the object.
            Logs the creation success or any errors encountered.
        """
        try:
            existing_user = await self.get_user_by_id(user_id)
            if existing_user:
                raise ValueError(f"User '{user_id}' already exists")

            user = User(
                user_id=user_id,
                username=username,
                email=email,
                is_admin=is_admin,
            )

            if isinstance(self.db, AsyncSession):
                self.db.add(user)
                await self.db.commit()
                await self.db.refresh(user)
            else:
                self.db.add(user)
                self.db.commit()
                self.db.refresh(user)

            logger.info(f"User created: {user_id}")
            return user

        except Exception as e:
            logger.error(f"Failed to create user {user_id}: {e}")
            raise

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Retrieves a user by their unique ID.

        Args:
            user_id: The unique identifier of the user (str).

        Returns:
            The User object if found, or None if not found or an error occurs.

        Notes:
            Executes a database query tailored to the session type (async or sync).
            Logs any errors during retrieval.
        """
        try:
            if isinstance(self.db, AsyncSession):
                result = await self.db.execute(
                    select(User).where(User.user_id == user_id)
                )
                return result.scalar_one_or_none()
            else:
                return self.db.query(User).filter(User.user_id == user_id).first()
        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {e}")
            return None

    async def get_all_users(self) -> List[User]:
        """Retrieves all users from the database.

        Returns:
            A list of all User objects.

        Notes:
            Uses an appropriate query method based on the session type.
            Returns an empty list if an error occurs, with logging for diagnostics.
        """
        try:
            if isinstance(self.db, AsyncSession):
                result = await self.db.execute(select(User))
                return list(result.scalars().all())
            else:
                return self.db.query(User).all()
        except Exception as e:
            logger.error(f"Failed to get all users: {e}")
            return []

    async def update_user(
        self,
        user_id: str,
        username: Optional[str] = None,
        email: Optional[str] = None,
        is_admin: Optional[bool] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[User]:
        """Updates user information with provided fields.

        Args:
            user_id: The unique identifier of the user to update (str).
            username: New username if provided (str, optional).
            email: New email if provided (str, optional).
            is_admin: New admin status if provided (bool, optional).
            is_active: New active status if provided (bool, optional).

        Returns:
            The updated User object, or None if the user is not found.

        Raises:
            Exception: If an error occurs during the update process.

        Notes:
            Only updates fields that are explicitly provided.
            Sets the updated_at timestamp to the current UTC time.
            Commits changes and refreshes the user object from the database.
            Logs the update success or any errors.
        """
        try:
            user = await self.get_user_by_id(user_id)
            if not user:
                return None

            if username is not None:
                user.username = username
            if email is not None:
                user.email = email
            if is_admin is not None:
                user.is_admin = is_admin
            if is_active is not None:
                user.is_active = is_active

            user.updated_at = datetime.now(timezone.utc)

            if isinstance(self.db, AsyncSession):
                await self.db.commit()
                await self.db.refresh(user)
            else:
                self.db.commit()
                self.db.refresh(user)

            logger.info(f"User updated: {user_id}")
            return user

        except Exception as e:
            logger.error(f"Failed to update user {user_id}: {e}")
            raise

    async def delete_user(self, user_id: str) -> bool:
        """Deletes a user and associated data.

        Args:
            user_id: The unique identifier of the user to delete (str).

        Returns:
            True if the user was successfully deleted, False if not found.

        Raises:
            Exception: If an error occurs during deletion.

        Notes:
            Retrieves the user first to confirm existence.
            Deletes the user from the database session and commits the change.
            Logs the deletion success or any errors.
        """
        try:
            user = await self.get_user_by_id(user_id)
            if not user:
                return False

            if isinstance(self.db, AsyncSession):
                await self.db.delete(user)
                await self.db.commit()
            else:
                self.db.delete(user)
                self.db.commit()

            logger.info(f"User deleted: {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete user {user_id}: {e}")
            raise

    async def create_api_key(
        self,
        user_id: str,
        permissions: List[str],
        expires_at: Optional[datetime] = None,
    ) -> Optional[dict]:
        """Creates a new API key for a specified user.

        Args:
            user_id: The unique identifier of the user (str).
            permissions: List of permissions for the API key (List[str]).
            expires_at: Optional expiration datetime for the key (datetime).

        Returns:
            A dictionary containing the plain API key (for one-time use), ID, permissions, expiration, and creation time.
            None if an error occurs.

        Raises:
            ValueError: If the user is not found.

        Notes:
            Verifies user existence before proceeding.
            Generates a secure API key, hashes it for storage, and saves only the hash in the database for security.
            Stores permissions as JSON and commits the record.
            Returns the plain key only once; subsequent access uses the hash.
            Logs creation success or errors.
        """
        try:
            user = await self.get_user_by_id(user_id)
            if not user:
                raise ValueError(f"User '{user_id}' not found")

            api_key_plain = APIKey.generate_api_key()
            api_key_hash = APIKey.hash_api_key(api_key_plain)

            api_key = APIKey(
                user_id=user_id,
                api_key_hash=api_key_hash,
                permissions=json.dumps(permissions),
                expires_at=expires_at,
            )

            if isinstance(self.db, AsyncSession):
                self.db.add(api_key)
                await self.db.commit()
                await self.db.refresh(api_key)
            else:
                self.db.add(api_key)
                self.db.commit()
                self.db.refresh(api_key)

            logger.info(f"API key created for user: {user_id}")

            return {
                "api_key": api_key_plain,
                "id": api_key.id,
                "permissions": permissions,
                "expires_at": expires_at,
                "created_at": api_key.created_at,
            }

        except Exception as e:
            logger.error(f"Failed to create API key for {user_id}: {e}")
            raise

    async def get_api_key_by_hash(self, api_key_hash: str) -> Optional[APIKey]:
        """Retrieves an API key by its hashed value.

        Args:
            api_key_hash: The hashed representation of the API key (str).

        Returns:
            The APIKey object if found, or None if not found or an error occurs.

        Notes:
            Performs a database lookup using the provided hash.
            Adapts the query to the session type and logs any retrieval errors.
        """
        try:
            if isinstance(self.db, AsyncSession):
                result = await self.db.execute(
                    select(APIKey).where(APIKey.api_key_hash == api_key_hash)
                )
                return result.scalar_one_or_none()
            else:
                return (
                    self.db.query(APIKey)
                    .filter(APIKey.api_key_hash == api_key_hash)
                    .first()
                )
        except Exception as e:
            logger.error(f"Failed to get API key by hash: {e}")
            return None

    async def get_user_api_keys(self, user_id: str) -> List[APIKey]:
        """Retrieves all API keys associated with a user.

        Args:
            user_id: The unique identifier of the user (str).

        Returns:
            A list of APIKey objects for the user.
            An empty list if an error occurs or no keys found.

        Notes:
            Queries the database for keys linked to the user_id.
            Handles both async and sync sessions, with error logging.
        """
        try:
            if isinstance(self.db, AsyncSession):
                result = await self.db.execute(
                    select(APIKey).where(APIKey.user_id == user_id)
                )
                return list(result.scalars().all())
            else:
                return self.db.query(APIKey).filter(APIKey.user_id == user_id).all()
        except Exception as e:
            logger.error(f"Failed to get API keys for {user_id}: {e}")
            return []

    async def update_api_key(
        self,
        user_id: str,
        api_key_id: int,
        permissions: Optional[List[str]] = None,
        is_active: Optional[bool] = None,
        expires_at: Optional[datetime] = None,
    ) -> Optional[APIKey]:
        """Updates an existing API key for a user.

        Args:
            user_id: The unique identifier of the owning user (str).
            api_key_id: The ID of the API key to update (int).
            permissions: New permissions list if provided (List[str], optional).
            is_active: New active status if provided (bool, optional).
            expires_at: New expiration datetime if provided (datetime, optional).

        Returns:
            The updated APIKey object, or None if not found.

        Raises:
            Exception: If an error occurs during the update.

        Notes:
            Verifies the key belongs to the specified user before updating.
            Only modifies fields that are provided.
            Serializes permissions to JSON for storage.
            Updates the updated_at timestamp and commits changes.
            Logs the update success or errors.
        """
        try:
            if isinstance(self.db, AsyncSession):
                result = await self.db.execute(
                    select(APIKey).where(
                        APIKey.id == api_key_id, APIKey.user_id == user_id
                    )
                )
                api_key = result.scalar_one_or_none()
            else:
                api_key = (
                    self.db.query(APIKey)
                    .filter(APIKey.id == api_key_id, APIKey.user_id == user_id)
                    .first()
                )

            if not api_key:
                return None

            if permissions is not None:
                api_key.permissions = json.dumps(permissions)
            if is_active is not None:
                api_key.is_active = is_active
            if expires_at is not None:
                api_key.expires_at = expires_at

            api_key.updated_at = datetime.now(timezone.utc)

            if isinstance(self.db, AsyncSession):
                await self.db.commit()
                await self.db.refresh(api_key)
            else:
                self.db.commit()
                self.db.refresh(api_key)

            logger.info(f"API key updated for user: {user_id}")
            return api_key

        except Exception as e:
            logger.error(f"Failed to update API key for {user_id}: {e}")
            raise

    async def delete_api_key(self, user_id: str, api_key_id: int) -> bool:
        """Deletes a specific API key for a user.

        Args:
            user_id: The unique identifier of the owning user (str).
            api_key_id: The ID of the API key to delete (int).

        Returns:
            True if the key was successfully deleted, False if not found.

        Raises:
            Exception: If an error occurs during deletion.

        Notes:
            Confirms the key belongs to the user before deletion.
            Removes the key from the database and commits the change.
            Logs the deletion success or any errors.
        """
        try:
            if isinstance(self.db, AsyncSession):
                result = await self.db.execute(
                    select(APIKey).where(
                        APIKey.id == api_key_id, APIKey.user_id == user_id
                    )
                )
                api_key = result.scalar_one_or_none()
            else:
                api_key = (
                    self.db.query(APIKey)
                    .filter(APIKey.id == api_key_id, APIKey.user_id == user_id)
                    .first()
                )

            if not api_key:
                return False

            if isinstance(self.db, AsyncSession):
                await self.db.delete(api_key)
                await self.db.commit()
            else:
                self.db.delete(api_key)
                self.db.commit()

            logger.info(f"API key deleted for user: {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete API key for {user_id}: {e}")
            raise

    async def verify_api_key(self, api_key_plain: str) -> Optional[dict]:
        """Verifies an API key and returns associated user information.

        Args:
            api_key_plain: The plain (unhashed) API key to verify (str).

        Returns:
            A dictionary with user details, permissions, and usage info if valid.
            None if the key is invalid, expired, inactive, or user issues occur.

        Notes:
            Hashes the provided key for secure lookup without storing plaintext.
            Validates the key's activity and expiration status.
            Tracks usage by updating last_used and incrementing usage_count on success.
            Retrieves and verifies the associated user is active.
            Parses stored permissions from JSON, with fallback defaults.
            Augments permissions with 'admin' if the user has admin rights.
            Logs verification attempts, successes, and failures for security auditing.
        """
        try:
            api_key_hash = APIKey.hash_api_key(api_key_plain)

            api_key = await self.get_api_key_by_hash(api_key_hash)
            if not api_key:
                logger.warning(f"Invalid API key attempted: {api_key_plain[:10]}...")
                return None

            if not api_key.is_valid():
                logger.warning(f"Invalid API key (expired/inactive): {api_key.id}")
                return None

            api_key.last_used = datetime.now(timezone.utc)
            api_key.usage_count += 1

            if isinstance(self.db, AsyncSession):
                await self.db.commit()
            else:
                self.db.commit()

            user = await self.get_user_by_id(api_key.user_id)
            if not user or not user.is_active:
                logger.warning(f"User not found or inactive: {api_key.user_id}")
                return None

            try:
                permissions = json.loads(api_key.permissions)
            except json.JSONDecodeError:
                permissions = ["read", "write"]

            if user.is_admin and "admin" not in permissions:
                permissions.append("admin")

            logger.info(f"API key verified successfully for user: {user.user_id}")
            return {
                "user_id": user.user_id,
                "username": user.username,
                "email": user.email,
                "is_admin": user.is_admin,
                "permissions": permissions,
                "api_key_id": api_key.id,
                "usage_count": api_key.usage_count,
                "last_used": api_key.last_used,
            }

        except Exception as e:
            logger.error(f"Failed to verify API key: {e}")
            return None
