"""
Reminder Tasks - Background Notification Scheduling

Jobs for reminder management:
- schedule_reminders: Create reminder entries for upcoming deadlines
- send_pending_reminders: Deliver notifications that are due
"""

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select, and_

from app.models.database import async_session_factory, Assignment, User, ReminderSchedule
from app.core.audit import audit_log
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def schedule_reminders(ctx: dict) -> dict:
    """
    Create reminder entries for upcoming deadlines (hourly cron).
    
    Reminder levels:
    - 3 days before: "upcoming" reminder
    - 24 hours before: "deadline" reminder
    - After due date: "overdue" reminder (once)
    """
    logger.info("Scheduling reminders")
    
    async with async_session_factory() as db:
        now = datetime.utcnow()
        
        # Find assignments due in next 3 days
        upcoming_cutoff = now + timedelta(days=3)
        
        result = await db.execute(
            select(Assignment).where(
                and_(
                    Assignment.due_date.isnot(None),
                    Assignment.due_date <= upcoming_cutoff,
                    Assignment.due_date >= now - timedelta(hours=24),  # Not more than 24h overdue
                )
            )
        )
        assignments = result.scalars().all()
        
        scheduled_count = 0
        
        for assignment in assignments:
            # Get enrolled students (via course enrollments)
            from app.models.database import Enrollment
            enrollments_result = await db.execute(
                select(Enrollment.user_id).where(Enrollment.course_id == assignment.course_id)
            )
            student_ids = [row[0] for row in enrollments_result.fetchall()]
            
            for student_id in student_ids:
                # Determine reminder type based on time remaining
                time_until_due = assignment.due_date - now
                
                if time_until_due < timedelta(hours=0):
                    reminder_type = "overdue"
                    scheduled_for = now  # Send immediately
                elif time_until_due < timedelta(hours=24):
                    reminder_type = "deadline"
                    scheduled_for = now  # Send immediately
                else:
                    reminder_type = "upcoming"
                    # Schedule for 3 days before
                    scheduled_for = assignment.due_date - timedelta(days=3)
                    if scheduled_for < now:
                        scheduled_for = now
                
                # Check if reminder already exists (anti-spam)
                existing = await db.execute(
                    select(ReminderSchedule).where(
                        and_(
                            ReminderSchedule.assignment_id == assignment.id,
                            ReminderSchedule.user_id == student_id,
                            ReminderSchedule.reminder_type == reminder_type,
                        )
                    )
                )
                if existing.scalar_one_or_none():
                    continue  # Skip duplicate
                
                # Create reminder
                reminder = ReminderSchedule(
                    assignment_id=assignment.id,
                    user_id=student_id,
                    reminder_type=reminder_type,
                    scheduled_for=scheduled_for,
                    channel="email",
                )
                db.add(reminder)
                scheduled_count += 1
        
        await db.commit()
    
    logger.info("Reminders scheduled", count=scheduled_count)
    return {"status": "success", "scheduled": scheduled_count}


async def send_pending_reminders(ctx: dict) -> dict:
    """
    Send reminders that are due (every 5 minutes cron).
    """
    logger.info("Sending pending reminders")
    
    async with async_session_factory() as db:
        now = datetime.utcnow()
        
        result = await db.execute(
            select(ReminderSchedule).where(
                and_(
                    ReminderSchedule.scheduled_for <= now,
                    ReminderSchedule.sent_at.is_(None),
                )
            ).limit(50)  # Batch size
        )
        reminders = result.scalars().all()
        
        sent_count = 0
        
        for reminder in reminders:
            # Get assignment and user details
            assignment_result = await db.execute(
                select(Assignment).where(Assignment.id == reminder.assignment_id)
            )
            assignment = assignment_result.scalar_one_or_none()
            
            user_result = await db.execute(
                select(User).where(User.id == reminder.user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if not assignment or not user:
                continue
            
            # Send notification (channel abstraction)
            try:
                await _send_notification(
                    channel=reminder.channel,
                    user=user,
                    assignment=assignment,
                    reminder_type=reminder.reminder_type,
                )
                
                reminder.sent_at = now
                sent_count += 1
                
                await audit_log(
                    user_id=user.id,
                    action="reminder_sent",
                    details={
                        "assignment": assignment.title,
                        "type": reminder.reminder_type,
                    }
                )
                
            except Exception as e:
                logger.warning(
                    "Failed to send reminder",
                    user_id=str(user.id),
                    error=str(e)
                )
        
        await db.commit()
    
    logger.info("Reminders sent", count=sent_count)
    return {"status": "success", "sent": sent_count}


async def _send_notification(channel: str, user: User, assignment: Assignment, reminder_type: str) -> None:
    """
    Send notification via specified channel.
    
    Currently supports:
    - email: Email notification (placeholder)
    - webhook: HTTP webhook (placeholder)
    
    In production, integrate with SendGrid, AWS SES, etc.
    """
    logger.info(
        "Sending notification",
        channel=channel,
        user_id=str(user.id),
        assignment=assignment.title,
        type=reminder_type,
    )
    
    # Build message
    if reminder_type == "overdue":
        subject = f"⚠️ Overdue: {assignment.title}"
        message = f"Your assignment '{assignment.title}' is overdue. Please submit as soon as possible."
    elif reminder_type == "deadline":
        subject = f"⏰ Due Soon: {assignment.title}"
        message = f"Your assignment '{assignment.title}' is due in less than 24 hours!"
    else:
        subject = f"📅 Upcoming: {assignment.title}"
        message = f"Reminder: '{assignment.title}' is due on {assignment.due_date.strftime('%B %d, %Y')}."
    
    # Channel-specific delivery
    if channel == "email":
        # TODO: Integrate email service (SendGrid, SES, etc.)
        logger.info("Email would be sent", to=user.email, subject=subject)
    elif channel == "webhook":
        # TODO: Send HTTP POST to configured webhook
        logger.info("Webhook would be triggered", user_id=str(user.id))
    else:
        logger.warning("Unknown notification channel", channel=channel)
