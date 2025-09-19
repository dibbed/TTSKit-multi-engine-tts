"""
Provides admin API endpoints for managing users and their API keys in the TTS kit system.

This router handles all administrative operations related to user management and API key administration, including creating, listing, updating, and deleting users and keys. It ensures that only users with admin permissions can perform these actions.
"""

from datetime import datetime
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...database.connection import get_session
from ...services.user_service import UserService
from ...utils.logging_config import get_logger
from ..dependencies import WriteAuth

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


class UserInfo(BaseModel):
    """
    Represents detailed information about a user in the TTS kit system.

    This model encapsulates user profile data used in administrative API responses, providing fields for identity, activity status, and timestamps.

    Notes:

        - User_id is the unique identifier.
        - Username and email may be None if not provided.
        - is_active indicates if the user account is currently enabled.
        - is_admin flags administrative privileges.
        - Timestamps are in ISO format strings.
    """

    user_id: str = Field(description="User ID")
    username: str | None = Field(description="Username", default=None)
    email: str | None = Field(description="Email", default=None)
    is_active: bool = Field(description="Is user active")
    is_admin: bool = Field(description="Is user admin")
    created_at: str = Field(description="Creation timestamp")
    last_login: str | None = Field(description="Last login timestamp", default=None)


class APIKeyInfo(BaseModel):
    """
    Represents detailed information about an API key in the system.

    This model is used to return API key metadata without exposing the full key value for security reasons, focusing on permissions and usage tracking.

    Notes:

        - id is the unique database identifier for the key.
        - api_key_plain is masked (e.g., "***hidden***") in responses.
        - permissions define what actions the key can perform (e.g., ["read", "write"]).
        - usage_count indicates how many API calls have been made with this key.
        - Timestamps are in ISO format.

    """

    id: int = Field(description="API Key ID")
    user_id: str = Field(description="User ID")
    api_key_plain: str = Field(description="API Key (plain text)")
    permissions: List[str] = Field(description="User permissions")
    is_active: bool = Field(description="Is API key active")
    created_at: str = Field(description="Creation timestamp")
    last_used: str | None = Field(description="Last used timestamp", default=None)
    expires_at: str | None = Field(description="Expiration timestamp", default=None)
    usage_count: int = Field(description="Usage count", default=0)


class CreateUserRequest(BaseModel):
    """
    Defines the input data for creating a new user through the admin API.

    This model validates and structures the required fields for user creation, with optional profile details.

    """

    user_id: str = Field(description="User ID", min_length=1, max_length=50)
    username: str | None = Field(description="Username", default=None, max_length=100)
    email: str | None = Field(description="Email", default=None, max_length=255)
    is_admin: bool = Field(description="Is admin user", default=False)


class CreateAPIKeyRequest(BaseModel):
    """
    Specifies the input for generating a new API key via the admin API.

    This model sets the associated user, initial permissions, and optional expiration date.

    """

    user_id: str = Field(description="User ID", min_length=1, max_length=50)
    permissions: List[str] = Field(
        default=["read", "write"], description="User permissions"
    )
    expires_at: str | None = Field(
        description="Expiration date (ISO format)", default=None
    )


class UpdateAPIKeyRequest(BaseModel):
    """
    Defines the input data for updating an existing API key via the admin API.

    This model allows modifying permissions, activation status, and expiration date selectively.

    """

    permissions: List[str] = Field(description="Updated permissions")
    is_active: bool | None = Field(description="Is API key active", default=None)
    expires_at: str | None = Field(
        description="Expiration date (ISO format)", default=None
    )


class CreateAPIKeyResponse(BaseModel):
    """
    Provides the response details after successfully creating a new API key.

    This model includes the generated API key (visible only once for security) along with its metadata.

    """

    id: int = Field(description="API Key ID")
    user_id: str = Field(description="User ID")
    api_key: str = Field(description="API Key (shown only once)")
    permissions: List[str] = Field(description="User permissions")
    created_at: str = Field(description="Creation timestamp")
    expires_at: str | None = Field(description="Expiration timestamp", default=None)


@router.get("/users", response_model=List[UserInfo])
async def list_users(
    auth: Annotated[WriteAuth, WriteAuth],
    db: Annotated[Session, Depends(get_session)],
):
    """
    Retrieve a list of all users in the system.

    This endpoint provides comprehensive details about every user, including their activity, admin status, and timestamps. It requires admin permissions to prevent unauthorized access to sensitive user information.

    Parameters:
        auth (WriteAuth): Authentication context, must include admin permission.
        db (Session): Database session for querying users.

    Returns:
        List[UserInfo]: A collection of user information objects with full profile details.

    Raises:
        HTTPException: 403 if the caller lacks admin permissions, or 500 for internal errors.

    """
    try:
        if "admin" not in auth.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin permission required",
            )

        user_service = UserService(db)
        users = await user_service.get_all_users()

        return [
            UserInfo(
                user_id=user.user_id,
                username=user.username,
                email=user.email,
                is_active=user.is_active,
                is_admin=user.is_admin,
                created_at=user.created_at.isoformat(),
                last_login=user.last_login.isoformat() if user.last_login else None,
            )
            for user in users
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list users: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/users", response_model=UserInfo)
async def create_user(
    request: CreateUserRequest,
    auth: Annotated[WriteAuth, WriteAuth],
    db: Annotated[Session, Depends(get_session)],
):
    """
    Create a new user in the system via admin API.

    This endpoint allows privileged users to register new accounts, specifying optional profile details. It enforces admin permission and validates user data.

    Parameters:
        request (CreateUserRequest): User creation data, including ID, username, email, admin status.
        auth (WriteAuth): Authentication context with required admin permission.
        db (Session): Database connection for user persistence.

    Returns:
        UserInfo: Detailed information about the newly created user.

    Raises:
        HTTPException: 403 for missing admin permission, 409 for validation errors, or 500 for other issues.

    """
    try:
        if "admin" not in auth.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin permission required",
            )

        user_service = UserService(db)
        user = await user_service.create_user(
            user_id=request.user_id,
            username=request.username,
            email=request.email,
            is_admin=request.is_admin,
        )

        return UserInfo(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            is_active=user.is_active,
            is_admin=user.is_admin,
            created_at=user.created_at.isoformat(),
            last_login=user.last_login.isoformat() if user.last_login else None,
        )

    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create user: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/users/me")
async def get_current_user(
    auth: Annotated[WriteAuth, WriteAuth],
    db: Annotated[Session, Depends(get_session)],
):
    """
    Retrieve information about the currently authenticated user.

    This endpoint returns the user's profile and permission details, with fallback authentication if the user isn't stored in the database (e.g., from config settings).

    Parameters:
        auth (WriteAuth): Current authentication context providing user ID and permissions.
        db (Session): Database session to look up user details.

    Returns:
        dict: User profile including ID, name, email, admin status, permissions, timestamps, and masked API key. Includes 'note' if using fallback auth.

    Raises:
        HTTPException: 500 for database or service errors.

    """
    try:
        user_service = UserService(db)
        user = await user_service.get_user_by_id(auth.user_id)

        if user:
            return {
                "user_id": user.user_id,
                "username": user.username,
                "email": user.email,
                "is_admin": user.is_admin,
                "is_active": user.is_active,
                "permissions": auth.permissions,
                "created_at": user.created_at.isoformat(),
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "api_key": auth.api_key[:8] + "..." if len(auth.api_key) > 8 else "***",
            }
        else:
            return {
                "user_id": auth.user_id,
                "permissions": auth.permissions,
                "api_key": auth.api_key[:8] + "..." if len(auth.api_key) > 8 else "***",
                "note": "User not found in database, using fallback authentication",
            }

    except Exception as e:
        logger.error(f"Failed to get current user: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/users/{user_id}", response_model=UserInfo)
async def get_user(
    user_id: str,
    auth: Annotated[WriteAuth, WriteAuth],
    db: Annotated[Session, Depends(get_session)],
):
    """
    Get detailed information about a specific user by ID.

    This admin-only endpoint fetches user profiles by their unique identifier, including activity status and timestamps.

    Parameters:
        user_id (str): Unique identifier of the user to retrieve.
        auth (WriteAuth): Authentication context requiring admin permission.
        db (Session): Database session for user lookup.

    Returns:
        UserInfo: Complete user information object.

    Raises:
        HTTPException: 403 for insufficient permissions, 404 if user not found, or 500 for errors.

    """
    try:
        if "admin" not in auth.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin permission required",
            )

        user_service = UserService(db)
        user = await user_service.get_user_by_id(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{user_id}' not found",
            )

        return UserInfo(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            is_active=user.is_active,
            is_admin=user.is_admin,
            created_at=user.created_at.isoformat(),
            last_login=user.last_login.isoformat() if user.last_login else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    auth: Annotated[WriteAuth, WriteAuth],
    db: Annotated[Session, Depends(get_session)],
):
    """
    Delete a user account by ID.

    This operation permanently removes the user and their associated data, but prevents deleting the built-in admin user for system security.

    Parameters:
        user_id (str): Unique identifier of the user to delete.
        auth (WriteAuth): Authentication with admin permission required.
        db (Session): Database session for user deletion.

    Returns:
        dict: Success message confirming deletion.

    Raises:
        HTTPException: 403 for permissions or protected user, 404 if user not found, or 500 for errors.

    """
    try:
        if "admin" not in auth.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin permission required",
            )

        if user_id == "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete admin user"
            )

        user_service = UserService(db)
        success = await user_service.delete_user(user_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{user_id}' not found",
            )

        return {"message": f"User '{user_id}' deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete user: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/api-keys", response_model=List[APIKeyInfo])
async def list_api_keys(
    auth: Annotated[WriteAuth, WriteAuth],
    db: Annotated[Session, Depends(get_session)],
):
    """
    Retrieve a list of all API keys across all users.

    This admin-only endpoint collects API key information from the entire system, returning metadata with permissions, status, and usage counts. Keys are not exposed in plain text for security.

    Parameters:
        auth (WriteAuth): Authentication context requiring admin permission.
        db (Session): Database session for querying keys.

    Returns:
        List[APIKeyInfo]: Collection of API key metadata objects.

    Raises:
        HTTPException: 403 for insufficient permissions or 500 for service errors.

    """
    try:
        if "admin" not in auth.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin permission required",
            )

        user_service = UserService(db)
        users = await user_service.get_all_users()

        api_keys = []
        for user in users:
            user_api_keys = await user_service.get_user_api_keys(user.user_id)
            for api_key in user_api_keys:
                import json

                permissions = json.loads(api_key.permissions)
                api_keys.append(
                    APIKeyInfo(
                        id=api_key.id,
                        user_id=api_key.user_id,
                        api_key_plain="***hidden***",
                        permissions=permissions,
                        is_active=api_key.is_active,
                        created_at=api_key.created_at.isoformat(),
                        last_used=api_key.last_used.isoformat()
                        if api_key.last_used
                        else None,
                        expires_at=api_key.expires_at.isoformat()
                        if api_key.expires_at
                        else None,
                        usage_count=getattr(api_key, "usage_count", 0),
                    )
                )

        return api_keys

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list API keys: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/api-keys", response_model=CreateAPIKeyResponse)
async def create_api_key(
    request: CreateAPIKeyRequest,
    auth: Annotated[WriteAuth, WriteAuth],
    db: Annotated[Session, Depends(get_session)],
):
    """
    Generate a new API key for a specified user.

    This admin endpoint creates a unique API key with the given permissions and optional expiration. If the user doesn't exist, they are automatically created as a basic user with placeholder details.

    Parameters:
        request (CreateAPIKeyRequest): Details for the new key including user ID, permissions, and optional expiration.
        auth (WriteAuth): Admin authentication context.
        db (Session): Database session for key and user operations.

    Returns:
        CreateAPIKeyResponse: Details of the created key, including the key value (visible only once for security).

    Raises:
        HTTPException: 403 for permissions, 400 for invalid date format, 409 for conflicts, or 500 for errors.

    """
    try:
        if "admin" not in auth.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin permission required",
            )

        expires_at = None
        if request.expires_at:
            try:
                expires_at = datetime.fromisoformat(
                    request.expires_at.replace("Z", "+00:00")
                )
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid expiration date format. Use ISO format.",
                ) from e

        user_service = UserService(db)

        user = await user_service.get_user_by_id(request.user_id)
        if not user:
            # Create user first
            await user_service.create_user(
                user_id=request.user_id,
                username=f"API User {request.user_id}",
                email=f"{request.user_id}@api.local",
                is_admin=False,
            )

        api_key_data = await user_service.create_api_key(
            user_id=request.user_id,
            permissions=request.permissions,
            expires_at=expires_at,
        )

        if not api_key_data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create API key",
            )

        return CreateAPIKeyResponse(
            id=api_key_data["id"],
            user_id=request.user_id,
            api_key=api_key_data["api_key"],
            permissions=api_key_data["permissions"],
            created_at=api_key_data["created_at"].isoformat(),
            expires_at=api_key_data["expires_at"].isoformat()
            if api_key_data["expires_at"]
            else None,
        )

    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create API key: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.put("/api-keys/{user_id}")
async def update_api_key(
    user_id: str,
    request: UpdateAPIKeyRequest,
    auth: Annotated[WriteAuth, WriteAuth],
    db: Annotated[Session, Depends(get_session)],
):
    """
    Modify an existing API key's settings.

    This updates permissions, activation status, and/or expiration for the first API key associated with the user. Currently targets the first key found, but could be enhanced to allow key specification.

    Parameters:
        user_id (str): Identifier of the user owning the key to update.
        request (UpdateAPIKeyRequest): Update parameters.
        auth (WriteAuth): Admin authentication required.
        db (Session): Database session for updates.

    Returns:
        APIKeyInfo: Updated API key metadata.

    Raises:
        HTTPException: 403 for permissions, 404 if no key found, 400 for invalid date, or 500 for errors.

    """
    try:
        if "admin" not in auth.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin permission required",
            )

        expires_at = None
        if request.expires_at:
            try:
                expires_at = datetime.fromisoformat(
                    request.expires_at.replace("Z", "+00:00")
                )
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid expiration date format. Use ISO format.",
                ) from e

        user_service = UserService(db)
        user_api_keys = await user_service.get_user_api_keys(user_id)

        if not user_api_keys:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No API keys found for user '{user_id}'",
            )

        api_key = user_api_keys[0]
        updated_api_key = await user_service.update_api_key(
            user_id=user_id,
            api_key_id=api_key.id,
            permissions=request.permissions,
            is_active=request.is_active,
            expires_at=expires_at,
        )

        if not updated_api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"API key not found for user '{user_id}'",
            )

        import json

        permissions = json.loads(updated_api_key.permissions)

        return APIKeyInfo(
            id=updated_api_key.id,
            user_id=updated_api_key.user_id,
            api_key_plain="***hidden***",
            permissions=permissions,
            is_active=updated_api_key.is_active,
            created_at=updated_api_key.created_at.isoformat(),
            last_used=updated_api_key.last_used.isoformat()
            if updated_api_key.last_used
            else None,
            expires_at=updated_api_key.expires_at.isoformat()
            if updated_api_key.expires_at
            else None,
            usage_count=getattr(updated_api_key, "usage_count", 0),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update API key: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/api-keys/{user_id}")
async def delete_api_key(
    user_id: str,
    auth: Annotated[WriteAuth, WriteAuth],
    db: Annotated[Session, Depends(get_session)],
):
    """
    Remove an API key from the system.

    This admin operation deletes the first API key linked to the specified user, preventing deletion of keys for protected users like 'admin'.

    Parameters:
        user_id (str): Owner of the API key to delete.
        auth (WriteAuth): Admin authentication context.
        db (Session): Database session for deletion.

    Returns:
        dict: Confirmation message of successful deletion.

    Raises:
        HTTPException: 403 for permissions or protected user, 404 if no key found, or 500 for errors.

    """
    try:
        if "admin" not in auth.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin permission required",
            )

        if user_id == "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete admin user"
            )

        user_service = UserService(db)
        user_api_keys = await user_service.get_user_api_keys(user_id)

        if not user_api_keys:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No API keys found for user '{user_id}'",
            )

        api_key = user_api_keys[0]
        success = await user_service.delete_api_key(user_id, api_key.id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"API key not found for user '{user_id}'",
            )

        return {"message": f"API key deleted successfully for user '{user_id}'"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete API key: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
