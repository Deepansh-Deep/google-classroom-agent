"""
Google Classroom Smart Assistant - Configuration Module

Environment-based configuration with validation using Pydantic Settings.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application
    app_name: str = "classroom-assistant"
    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    secret_key: str = Field(..., min_length=32)
    
    # Database
    database_url: str = Field(..., description="PostgreSQL connection URL")
    database_pool_size: int = Field(default=20, ge=5, le=100)
    database_max_overflow: int = Field(default=10, ge=0, le=50)
    
    # Vector Database
    chroma_host: str = "localhost"
    chroma_port: int = 8000
    chroma_collection: str = "classroom_embeddings"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # Google OAuth
    google_client_id: str = Field(..., description="Google OAuth Client ID")
    google_client_secret: str = Field(..., description="Google OAuth Client Secret")
    google_redirect_uri: str = "http://localhost:8080/api/v1/auth/callback"
    
    # JWT
    jwt_secret_key: str = Field(..., min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15  # Shortened from 30 for security
    jwt_refresh_token_expire_days: int = 7
    
    # Token Encryption (for storing Google tokens at rest)
    token_encryption_key: str = Field(..., min_length=32, description="Fernet key for encrypting stored tokens")
    
    # Embedding
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = 384
    
    # Email
    email_provider: Literal["mock", "smtp", "sendgrid", "ses"] = "mock"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = "noreply@classroom-assistant.com"
    
    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60
    
    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: Literal["json", "text"] = "json"
    
    # Frontend
    frontend_url: str = "http://localhost:3000"
    
    @property
    def is_production(self) -> bool:
        return self.app_env == "production"
    
    @property
    def cors_origins(self) -> list[str]:
        if self.is_production:
            return [self.frontend_url]
        return ["http://localhost:3000", "http://127.0.0.1:3000"]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
