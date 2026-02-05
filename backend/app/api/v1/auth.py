"""
Authentication API Endpoints

Handles Google OAuth flow, token management, and user authentication.
"""

import secrets
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import AuthenticationError, NotFoundError
from app.core.permissions import CurrentUser, get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    encrypt_token,
    decrypt_token,
    exchange_code_for_tokens,
    get_google_auth_url,
    get_google_user_info,
    get_token_expiry_seconds,
    refresh_google_token,
    verify_token,
)
from app.core.audit import audit_log
from app.models.database import User, get_db
from app.models.schemas import (
    GoogleAuthCallback,
    GoogleAuthURL,
    TokenResponse,
    UserDetailResponse,
    UserResponse,
    UserUpdate,
)
from app.utils.logging import get_logger

router = APIRouter()
settings = get_settings()
logger = get_logger(__name__)


@router.get("/google", response_model=GoogleAuthURL)
async def get_google_login_url():
    """
    Get Google OAuth authorization URL.
    
    Returns the URL to redirect users to for Google authentication.
    """
    state = secrets.token_urlsafe(32)
    auth_url = get_google_auth_url(state)
    
    logger.info("Generated Google auth URL", state=state[:8])
    
    return GoogleAuthURL(auth_url=auth_url)


@router.get("/callback", response_model=TokenResponse)
async def google_callback(
    request: Request,
    code: str = Query(..., description="Authorization code from Google"),
    state: Optional[str] = Query(None, description="State parameter for CSRF protection"),
    db: AsyncSession = Depends(get_db),
):
    """
    Handle Google OAuth callback.
    
    Exchanges the authorization code for tokens, creates or updates the user,
    triggers background sync, and returns JWT tokens for API authentication.
    """
    # Exchange code for tokens
    tokens = await exchange_code_for_tokens(code, state)
    
    # Get user info from Google
    user_info = await get_google_user_info(tokens["access_token"])
    
    # Encrypt tokens before storage
    encrypted_access = encrypt_token(tokens["access_token"])
    encrypted_refresh = encrypt_token(tokens["refresh_token"]) if tokens.get("refresh_token") else None
    
    # Check if user exists
    query = select(User).where(User.google_id == user_info["google_id"])
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    is_new_user = user is None
    
    if user:
        # Update existing user with encrypted tokens
        user.access_token = encrypted_access
        user.refresh_token = encrypted_refresh or user.refresh_token
        user.token_expiry = tokens.get("token_expiry")
        user.last_login_at = datetime.utcnow()
        user.name = user_info.get("name") or user.name
        user.avatar_url = user_info.get("avatar_url") or user.avatar_url
        
        logger.info("User logged in", user_id=str(user.id), email=user.email)
    else:
        # Determine role based on Google Classroom data
        # Default to student, teacher role assigned when syncing courses
        role = "student"
        
        # Create new user with encrypted tokens
        user = User(
            email=user_info["email"],
            name=user_info.get("name"),
            google_id=user_info["google_id"],
            avatar_url=user_info.get("avatar_url"),
            role=role,
            access_token=encrypted_access,
            refresh_token=encrypted_refresh,
            token_expiry=tokens.get("token_expiry"),
            last_login_at=datetime.utcnow(),
        )
        db.add(user)
        
        logger.info("New user created", email=user_info["email"], role=role)
    
    await db.commit()
    await db.refresh(user)
    
    # Audit log the login event
    await audit_log(
        user_id=user.id,
        action="user_login",
        details={"new_user": is_new_user},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    
    # Trigger background classroom sync
    try:
        from arq import create_pool
        from arq.connections import RedisSettings
        redis = await create_pool(RedisSettings.from_dsn(settings.redis_url))
        await redis.enqueue_job("sync_user_classroom", str(user.id))
        await redis.close()
        logger.info("Sync job queued", user_id=str(user.id))
    except Exception as e:
        logger.warning("Failed to queue sync job", error=str(e))
    
    # Create JWT tokens
    access_token = create_access_token(user.id, user.email, user.role)
    refresh_token = create_refresh_token(user.id)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=get_token_expiry_seconds(),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Refresh access token using refresh token.
    
    Expects the refresh token in the Authorization header.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise AuthenticationError("Refresh token required")
    
    token = auth_header.split()[1]
    payload = verify_token(token, token_type="refresh")
    
    # Get user
    user_id = UUID(payload["sub"])
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise AuthenticationError("User not found")
    
    # Optionally refresh Google token if expired
    if user.token_expiry and user.token_expiry < datetime.utcnow():
        if user.refresh_token:
            try:
                new_tokens = await refresh_google_token(user.refresh_token)
                user.access_token = new_tokens["access_token"]
                user.token_expiry = new_tokens["token_expiry"]
                await db.commit()
            except Exception as e:
                logger.warning("Failed to refresh Google token", error=str(e))
    
    # Create new JWT tokens
    access_token = create_access_token(user.id, user.email, user.role)
    refresh_token = create_refresh_token(user.id)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=get_token_expiry_seconds(),
    )


@router.get("/me", response_model=UserDetailResponse)
async def get_current_user_info(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current authenticated user's profile."""
    query = select(User).where(User.id == current_user.id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise NotFoundError("User", str(current_user.id))
    
    return UserDetailResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        avatar_url=user.avatar_url,
        created_at=user.created_at,
        last_login=user.last_login,
        reminder_email=user.reminder_email,
        reminder_push=user.reminder_push,
        reminder_hours_before=user.reminder_hours_before,
    )


@router.patch("/me", response_model=UserDetailResponse)
async def update_current_user(
    update_data: UserUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update current user's profile and preferences."""
    query = select(User).where(User.id == current_user.id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise NotFoundError("User", str(current_user.id))
    
    # Update only provided fields
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(user, field, value)
    
    user.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(user)
    
    logger.info("User updated", user_id=str(user.id))
    
    return UserDetailResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        avatar_url=user.avatar_url,
        created_at=user.created_at,
        last_login=user.last_login,
        reminder_email=user.reminder_email,
        reminder_push=user.reminder_push,
        reminder_hours_before=user.reminder_hours_before,
    )


@router.post("/logout")
async def logout(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Logout current user.
    
    Note: JWT tokens are stateless, so we just return success.
    Client should discard the tokens.
    """
    # Audit log the logout
    await audit_log(
        user_id=current_user.id,
        action="user_logout",
        ip_address=request.client.host if request.client else None,
    )
    
    logger.info("User logged out", user_id=str(current_user.id))
    return {"message": "Logged out successfully"}
