"""
Audit Module - Security Logging

Logs sensitive actions for compliance and debugging:
- Login/logout
- Token refresh
- Data sync
- Report generation
- Permission denied events
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import select

from app.models.database import async_session_factory, AuditLog
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def audit_log(
    user_id: Optional[UUID],
    action: str,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    """
    Log an audit event to database.
    
    Actions logged:
    - user_login
    - user_logout
    - token_refresh
    - classroom_sync
    - report_generated
    - permission_denied
    - data_export
    - reminder_sent
    """
    try:
        async with async_session_factory() as db:
            log_entry = AuditLog(
                user_id=user_id,
                action=action,
                details=details or {},
                ip_address=ip_address,
                user_agent=user_agent,
            )
            db.add(log_entry)
            await db.commit()
            
        logger.info(
            "Audit event logged",
            action=action,
            user_id=str(user_id) if user_id else None,
        )
    except Exception as e:
        # Don't fail the request if audit logging fails
        logger.warning("Failed to write audit log", action=action, error=str(e))


async def get_audit_logs(
    user_id: Optional[UUID] = None,
    action: Optional[str] = None,
    since: Optional[datetime] = None,
    limit: int = 100,
) -> list:
    """
    Retrieve audit logs with optional filters.
    
    For admin and compliance review.
    """
    async with async_session_factory() as db:
        query = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
        
        if user_id:
            query = query.where(AuditLog.user_id == user_id)
        if action:
            query = query.where(AuditLog.action == action)
        if since:
            query = query.where(AuditLog.created_at >= since)
        
        result = await db.execute(query)
        logs = result.scalars().all()
        
        return [
            {
                "id": str(log.id),
                "user_id": str(log.user_id) if log.user_id else None,
                "action": log.action,
                "details": log.details,
                "ip_address": log.ip_address,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ]


def mask_token(token: str) -> str:
    """Mask a token for safe logging (show first 8 chars only)."""
    if not token or len(token) < 12:
        return "***"
    return f"{token[:8]}...{token[-4:]}"
