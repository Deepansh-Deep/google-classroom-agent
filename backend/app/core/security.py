"""
Security Module - OAuth and JWT Token Management

Handles Google OAuth 2.0 flow, JWT token generation, validation,
and encryption of stored tokens.
"""

import base64
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from jose import JWTError, jwt
from cryptography.fernet import Fernet, InvalidToken
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from app.config import get_settings
from app.core.exceptions import AuthenticationError
from app.utils.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

# Token encryption cipher
_fernet: Optional[Fernet] = None


def _get_fernet() -> Fernet:
    """Get or create Fernet cipher for token encryption."""
    global _fernet
    if _fernet is None:
        # Ensure key is properly padded for Fernet (32 bytes base64 encoded)
        key = settings.token_encryption_key.encode()
        if len(key) < 32:
            key = key.ljust(32, b'0')
        key = base64.urlsafe_b64encode(key[:32])
        _fernet = Fernet(key)
    return _fernet


def encrypt_token(token: str) -> str:
    """Encrypt a token for secure storage."""
    try:
        return _get_fernet().encrypt(token.encode()).decode()
    except Exception as e:
        logger.error("Token encryption failed", error=str(e))
        raise AuthenticationError("Failed to secure token")


def decrypt_token(encrypted: str) -> str:
    """Decrypt a stored token."""
    try:
        return _get_fernet().decrypt(encrypted.encode()).decode()
    except InvalidToken:
        logger.warning("Token decryption failed - invalid token")
        raise AuthenticationError("Invalid stored token")
    except Exception as e:
        logger.error("Token decryption failed", error=str(e))
        raise AuthenticationError("Failed to decrypt token")

# Google OAuth scopes required for Classroom API
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/classroom.courses.readonly",
    "https://www.googleapis.com/auth/classroom.coursework.students.readonly",
    "https://www.googleapis.com/auth/classroom.courseworkmaterials.readonly",
    "https://www.googleapis.com/auth/classroom.announcements.readonly",
    "https://www.googleapis.com/auth/classroom.rosters.readonly",
    "https://www.googleapis.com/auth/classroom.profile.emails",
    "https://www.googleapis.com/auth/classroom.profile.photos",
    "openid",
    "email",
    "profile",
]


def create_oauth_flow(state: Optional[str] = None) -> Flow:
    """Create Google OAuth flow for authentication."""
    client_config = {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.google_redirect_uri],
        }
    }
    
    flow = Flow.from_client_config(
        client_config,
        scopes=GOOGLE_SCOPES,
        state=state,
    )
    flow.redirect_uri = settings.google_redirect_uri
    return flow


def get_google_auth_url(state: Optional[str] = None) -> str:
    """Generate Google OAuth authorization URL."""
    flow = create_oauth_flow(state)
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return auth_url


async def exchange_code_for_tokens(code: str, state: Optional[str] = None) -> dict:
    """Exchange authorization code for tokens."""
    try:
        flow = create_oauth_flow(state)
        flow.fetch_token(code=code)
        
        credentials = flow.credentials
        
        return {
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_expiry": credentials.expiry,
            "id_token": credentials.id_token,
        }
    except Exception as e:
        logger.error("Failed to exchange code for tokens", error=str(e))
        raise AuthenticationError(f"Failed to authenticate: {str(e)}")


async def get_google_user_info(access_token: str) -> dict:
    """Get user info from Google using access token."""
    try:
        credentials = Credentials(token=access_token)
        service = build("oauth2", "v2", credentials=credentials)
        user_info = service.userinfo().get().execute()
        
        return {
            "google_id": user_info.get("id"),
            "email": user_info.get("email"),
            "name": user_info.get("name"),
            "avatar_url": user_info.get("picture"),
        }
    except Exception as e:
        logger.error("Failed to get user info from Google", error=str(e))
        raise AuthenticationError("Failed to get user information")


async def refresh_google_token(refresh_token: str) -> dict:
    """Refresh expired Google access token."""
    try:
        credentials = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
        )
        
        # Force refresh
        from google.auth.transport.requests import Request
        credentials.refresh(Request())
        
        return {
            "access_token": credentials.token,
            "token_expiry": credentials.expiry,
        }
    except Exception as e:
        logger.error("Failed to refresh Google token", error=str(e))
        raise AuthenticationError("Failed to refresh authentication token")


def create_access_token(user_id: UUID, email: str, role: str) -> str:
    """Create JWT access token."""
    expire = datetime.utcnow() + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "exp": expire,
        "type": "access",
    }
    
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: UUID) -> str:
    """Create JWT refresh token."""
    expire = datetime.utcnow() + timedelta(days=settings.jwt_refresh_token_expire_days)
    
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "type": "refresh",
    }
    
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def verify_token(token: str, token_type: str = "access") -> dict:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        
        if payload.get("type") != token_type:
            raise AuthenticationError(f"Invalid token type. Expected {token_type}")
        
        return payload
    except JWTError as e:
        logger.warning("Token verification failed", error=str(e))
        raise AuthenticationError("Invalid or expired token")


def get_token_expiry_seconds() -> int:
    """Get access token expiry in seconds."""
    return settings.jwt_access_token_expire_minutes * 60
