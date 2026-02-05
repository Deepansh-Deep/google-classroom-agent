"""
Role-Based Access Control (RBAC) and Permission Management

Provides decorators and utilities for enforcing access control.
"""

from enum import Enum
from functools import wraps
from typing import Callable, List, Optional
from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError, AuthenticationError
from app.core.security import verify_token
from app.models.database import get_db, User, Enrollment
from app.utils.logging import get_logger

logger = get_logger(__name__)


class Role(str, Enum):
    """User roles with hierarchical permissions."""
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"


class Permission(str, Enum):
    """Granular permissions for specific actions."""
    # Course permissions
    VIEW_COURSES = "view_courses"
    MANAGE_COURSES = "manage_courses"
    SYNC_COURSES = "sync_courses"
    
    # Student/User permissions
    VIEW_STUDENTS = "view_students"
    VIEW_ALL_STUDENTS = "view_all_students"
    
    # Assignment permissions
    VIEW_ASSIGNMENTS = "view_assignments"
    MANAGE_ASSIGNMENTS = "manage_assignments"
    
    # Submission permissions
    VIEW_OWN_SUBMISSIONS = "view_own_submissions"
    VIEW_ALL_SUBMISSIONS = "view_all_submissions"
    GRADE_SUBMISSIONS = "grade_submissions"
    
    # Analytics permissions
    VIEW_OWN_ANALYTICS = "view_own_analytics"
    VIEW_CLASS_ANALYTICS = "view_class_analytics"
    
    # Report permissions
    GENERATE_REPORTS = "generate_reports"
    EXPORT_DATA = "export_data"
    
    # Q&A permissions
    USE_QA = "use_qa"
    
    # Reminder permissions
    MANAGE_OWN_REMINDERS = "manage_own_reminders"
    
    # Admin permissions
    MANAGE_USERS = "manage_users"
    VIEW_AUDIT_LOGS = "view_audit_logs"
    SYSTEM_CONFIG = "system_config"


# Role to permissions mapping
ROLE_PERMISSIONS = {
    Role.ADMIN: [p for p in Permission],  # Admin has all permissions
    
    Role.TEACHER: [
        Permission.VIEW_COURSES,
        Permission.MANAGE_COURSES,
        Permission.SYNC_COURSES,
        Permission.VIEW_STUDENTS,
        Permission.VIEW_ALL_STUDENTS,
        Permission.VIEW_ASSIGNMENTS,
        Permission.MANAGE_ASSIGNMENTS,
        Permission.VIEW_ALL_SUBMISSIONS,
        Permission.GRADE_SUBMISSIONS,
        Permission.VIEW_CLASS_ANALYTICS,
        Permission.GENERATE_REPORTS,
        Permission.EXPORT_DATA,
        Permission.USE_QA,
        Permission.MANAGE_OWN_REMINDERS,
    ],
    
    Role.STUDENT: [
        Permission.VIEW_COURSES,
        Permission.VIEW_ASSIGNMENTS,
        Permission.VIEW_OWN_SUBMISSIONS,
        Permission.VIEW_OWN_ANALYTICS,
        Permission.USE_QA,
        Permission.MANAGE_OWN_REMINDERS,
    ],
}


def has_permission(role: str, permission: Permission) -> bool:
    """Check if a role has a specific permission."""
    try:
        role_enum = Role(role)
        return permission in ROLE_PERMISSIONS.get(role_enum, [])
    except ValueError:
        return False


def get_role_permissions(role: str) -> List[Permission]:
    """Get all permissions for a role."""
    try:
        role_enum = Role(role)
        return ROLE_PERMISSIONS.get(role_enum, [])
    except ValueError:
        return []


class CurrentUser:
    """Represents the currently authenticated user."""
    
    def __init__(self, user_id: UUID, email: str, role: str):
        self.id = user_id
        self.email = email
        self.role = role
    
    def has_permission(self, permission: Permission) -> bool:
        return has_permission(self.role, permission)
    
    def is_admin(self) -> bool:
        return self.role == Role.ADMIN.value
    
    def is_teacher(self) -> bool:
        return self.role in [Role.ADMIN.value, Role.TEACHER.value]
    
    def is_student(self) -> bool:
        return self.role == Role.STUDENT.value


async def get_current_user(request: Request) -> CurrentUser:
    """Extract and validate current user from request."""
    auth_header = request.headers.get("Authorization")
    
    if not auth_header:
        raise AuthenticationError("Authorization header missing")
    
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthenticationError("Invalid authorization header format")
    
    token = parts[1]
    payload = verify_token(token, token_type="access")
    
    return CurrentUser(
        user_id=UUID(payload["sub"]),
        email=payload["email"],
        role=payload["role"],
    )


def require_permission(permission: Permission):
    """Decorator to require a specific permission for an endpoint."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current user from kwargs or find it
            current_user = kwargs.get("current_user")
            if not current_user:
                # Try to find it in the request
                request = kwargs.get("request")
                if request:
                    current_user = await get_current_user(request)
                    kwargs["current_user"] = current_user
            
            if not current_user:
                raise AuthenticationError("User not authenticated")
            
            if not current_user.has_permission(permission):
                logger.warning(
                    "Permission denied",
                    user_id=str(current_user.id),
                    permission=permission.value,
                )
                raise AuthorizationError(
                    f"Permission '{permission.value}' required",
                    details={"required_permission": permission.value},
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_role(*roles: Role):
    """Decorator to require specific role(s) for an endpoint."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get("current_user")
            if not current_user:
                request = kwargs.get("request")
                if request:
                    current_user = await get_current_user(request)
                    kwargs["current_user"] = current_user
            
            if not current_user:
                raise AuthenticationError("User not authenticated")
            
            role_values = [r.value for r in roles]
            if current_user.role not in role_values:
                logger.warning(
                    "Role access denied",
                    user_id=str(current_user.id),
                    user_role=current_user.role,
                    required_roles=role_values,
                )
                raise AuthorizationError(
                    f"Access requires one of these roles: {', '.join(role_values)}",
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


async def check_course_access(
    user: CurrentUser,
    course_id: UUID,
    db: AsyncSession,
    require_teacher: bool = False,
) -> bool:
    """
    Check if user has access to a specific course.
    
    Args:
        user: Current authenticated user
        course_id: Course to check access for
        db: Database session
        require_teacher: If True, user must be a teacher of the course
    
    Returns:
        True if user has access
    
    Raises:
        AuthorizationError if access is denied
    """
    from sqlalchemy import select
    
    # Admins have access to all courses
    if user.is_admin():
        return True
    
    # Check enrollment
    query = select(Enrollment).where(
        Enrollment.user_id == user.id,
        Enrollment.course_id == course_id,
    )
    
    result = await db.execute(query)
    enrollment = result.scalar_one_or_none()
    
    if not enrollment:
        raise AuthorizationError("You do not have access to this course")
    
    if require_teacher and enrollment.role != "teacher":
        raise AuthorizationError("Teacher access required for this action")
    
    return True
