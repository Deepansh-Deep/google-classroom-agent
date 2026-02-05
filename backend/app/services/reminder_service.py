"""
Reminder Service - Multi-level reminder scheduling.
"""

from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Assignment, ReminderSchedule, User, Enrollment
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ReminderService:
    """Reminder scheduling with anti-spam logic."""
    
    REMINDER_TYPES = {
        "upcoming": timedelta(days=3),
        "deadline": timedelta(hours=24),
        "overdue": timedelta(hours=-1),
    }
    
    async def schedule_reminders(self, db: AsyncSession, user_id: UUID) -> int:
        """Schedule reminders for user's upcoming assignments."""
        user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if not user or not user.reminder_email:
            return 0
        
        # Get enrolled courses
        enrollments = (await db.execute(
            select(Enrollment).where(Enrollment.user_id == user_id)
        )).scalars().all()
        
        course_ids = [e.course_id for e in enrollments]
        if not course_ids:
            return 0
        
        # Get upcoming assignments
        now = datetime.utcnow()
        assignments = (await db.execute(
            select(Assignment).where(
                Assignment.course_id.in_(course_ids),
                Assignment.due_date > now,
                Assignment.due_date < now + timedelta(days=7)
            )
        )).scalars().all()
        
        scheduled = 0
        for assignment in assignments:
            for reminder_type, offset in self.REMINDER_TYPES.items():
                scheduled_time = assignment.due_date - offset if offset.total_seconds() > 0 else assignment.due_date + abs(offset)
                
                if scheduled_time < now:
                    continue
                
                # Check if already scheduled
                existing = (await db.execute(
                    select(ReminderSchedule).where(
                        ReminderSchedule.user_id == user_id,
                        ReminderSchedule.assignment_id == assignment.id,
                        ReminderSchedule.reminder_type == reminder_type
                    )
                )).scalar_one_or_none()
                
                if not existing:
                    db.add(ReminderSchedule(
                        user_id=user_id, assignment_id=assignment.id,
                        reminder_type=reminder_type, scheduled_for=scheduled_time,
                        channel="email"
                    ))
                    scheduled += 1
        
        await db.commit()
        return scheduled
    
    async def get_pending_reminders(self, db: AsyncSession) -> List[ReminderSchedule]:
        """Get reminders that need to be sent."""
        now = datetime.utcnow()
        return (await db.execute(
            select(ReminderSchedule).where(
                ReminderSchedule.scheduled_for <= now,
                ReminderSchedule.sent == False
            )
        )).scalars().all()
    
    async def mark_sent(self, db: AsyncSession, reminder_id: UUID) -> None:
        """Mark reminder as sent."""
        reminder = (await db.execute(
            select(ReminderSchedule).where(ReminderSchedule.id == reminder_id)
        )).scalar_one_or_none()
        if reminder:
            reminder.sent = True
            reminder.sent_at = datetime.utcnow()
            await db.commit()


reminder_service = ReminderService()
