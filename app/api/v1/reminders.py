"""
Reminders API Endpoints.
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CurrentUser, Permission, get_current_user, require_permission
from app.models.database import ReminderSchedule, Assignment, get_db
from app.models.schemas import ReminderSettings, ReminderResponse, UpcomingReminder, AssignmentResponse
from app.services.reminder_service import reminder_service

router = APIRouter()


@router.get("/upcoming", response_model=List[UpcomingReminder])
@require_permission(Permission.MANAGE_OWN_REMINDERS)
async def get_upcoming_reminders(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get upcoming reminders for current user."""
    reminders = (await db.execute(
        select(ReminderSchedule, Assignment)
        .join(Assignment)
        .where(ReminderSchedule.user_id == current_user.id, ReminderSchedule.sent == False)
        .order_by(ReminderSchedule.scheduled_for)
    )).all()
    
    return [
        UpcomingReminder(
            assignment=AssignmentResponse(
                id=a.id, google_assignment_id=a.google_assignment_id,
                course_id=a.course_id, title=a.title, description=a.description,
                max_points=a.max_points, due_date=a.due_date, state=a.state,
                work_type=a.work_type, created_at=a.created_at
            ),
            reminder_type=r.reminder_type,
            scheduled_for=r.scheduled_for
        )
        for r, a in reminders
    ]


@router.post("/schedule")
@require_permission(Permission.MANAGE_OWN_REMINDERS)
async def schedule_reminders(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Schedule reminders for upcoming assignments."""
    count = await reminder_service.schedule_reminders(db, current_user.id)
    return {"scheduled": count}
