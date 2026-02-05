"""
Custom Exception Classes for the Application

Provides a consistent error handling pattern across the application.
"""

from typing import Any, Dict, Optional


class AppException(Exception):
    """Base exception for all application errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "app_error",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(AppException):
    """Raised when authentication fails."""
    
    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="authentication_error",
            status_code=401,
            details=details,
        )


class AuthorizationError(AppException):
    """Raised when user lacks permission for an action."""
    
    def __init__(self, message: str = "Permission denied", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="authorization_error",
            status_code=403,
            details=details,
        )


class NotFoundError(AppException):
    """Raised when a requested resource is not found."""
    
    def __init__(self, resource: str, identifier: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"{resource} with id '{identifier}' not found",
            error_code="not_found",
            status_code=404,
            details=details or {"resource": resource, "identifier": identifier},
        )


class ValidationError(AppException):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="validation_error",
            status_code=422,
            details=details,
        )


class RateLimitError(AppException):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, retry_after: int = 60, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Rate limit exceeded. Retry after {retry_after} seconds",
            error_code="rate_limit_exceeded",
            status_code=429,
            details=details or {"retry_after": retry_after},
        )


class ExternalServiceError(AppException):
    """Raised when an external service call fails."""
    
    def __init__(self, service: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"External service error ({service}): {message}",
            error_code="external_service_error",
            status_code=502,
            details=details or {"service": service},
        )


class GoogleAPIError(ExternalServiceError):
    """Raised when Google Classroom API calls fail."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            service="google_classroom",
            message=message,
            details=details,
        )


class DatabaseError(AppException):
    """Raised when database operations fail."""
    
    def __init__(self, message: str = "Database operation failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="database_error",
            status_code=500,
            details=details,
        )


class EmbeddingError(AppException):
    """Raised when embedding generation fails."""
    
    def __init__(self, message: str = "Failed to generate embeddings", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="embedding_error",
            status_code=500,
            details=details,
        )
