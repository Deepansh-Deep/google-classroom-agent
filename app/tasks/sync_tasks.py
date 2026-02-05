"""
Sync Tasks - Background Classroom Synchronization

Jobs for fetching data from Google Classroom API:
- sync_user_classroom: Full sync for single user
- sync_all_active_users: Periodic sync for all active users
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.database import async_session_factory, User, Course, Assignment, Submission
from app.integrations.google_classroom import GoogleClassroomClient
from app.core.cache import cache
from app.core.audit import audit_log
from app.utils.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


async def sync_user_classroom(ctx: dict, user_id: str) -> dict:
    """
    Sync classroom data for a single user.
    
    Triggered:
    - After OAuth login
    - Manual sync button
    - Periodic refresh
    """
    logger.info("Starting classroom sync", user_id=user_id)
    
    async with async_session_factory() as db:
        # Get user with tokens
        result = await db.execute(select(User).where(User.id == UUID(user_id)))
        user = result.scalar_one_or_none()
        
        if not user or not user.access_token:
            logger.warning("User not found or no token", user_id=user_id)
            return {"status": "skipped", "reason": "no_token"}
        
        try:
            # Decrypt token and create client
            from app.core.security import decrypt_token
            access_token = decrypt_token(user.access_token)
            
            client = GoogleClassroomClient(access_token)
            
            # Sync courses
            courses_data = await client.get_courses()
            courses_synced = 0
            assignments_synced = 0
            
            for course_data in courses_data:
                course = await _sync_course(db, user.id, course_data)
                courses_synced += 1
                
                # Sync assignments for each course
                assignments_data = await client.get_assignments(course_data["id"])
                for assignment_data in assignments_data:
                    await _sync_assignment(db, course.id, assignment_data)
                    assignments_synced += 1
                
                # Rate limit courtesy
                await asyncio.sleep(0.1)
            
            await db.commit()
            
            # Update last sync time
            await db.execute(
                update(User).where(User.id == user.id).values(last_sync_at=datetime.utcnow())
            )
            await db.commit()
            
            # Invalidate cache
            await cache.delete(f"user:{user_id}:courses")
            
            # Log audit event
            await audit_log(
                user_id=user.id,
                action="classroom_sync",
                details={"courses": courses_synced, "assignments": assignments_synced}
            )
            
            logger.info(
                "Sync complete",
                user_id=user_id,
                courses=courses_synced,
                assignments=assignments_synced
            )
            
            return {
                "status": "success",
                "courses_synced": courses_synced,
                "assignments_synced": assignments_synced,
            }
            
        except Exception as e:
            logger.exception("Sync failed", user_id=user_id, error=str(e))
            return {"status": "failed", "error": str(e)}


async def sync_all_active_users(ctx: dict) -> dict:
    """
    Periodic sync for all active users (cron job).
    
    Active = logged in within last 24 hours.
    """
    logger.info("Starting periodic sync for all active users")
    
    async with async_session_factory() as db:
        cutoff = datetime.utcnow() - timedelta(hours=24)
        result = await db.execute(
            select(User.id).where(User.last_login_at >= cutoff)
        )
        user_ids = [str(row[0]) for row in result.fetchall()]
    
    logger.info("Found active users", count=len(user_ids))
    
    # Enqueue individual sync jobs
    from arq import create_pool
    from arq.connections import RedisSettings
    
    redis = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    
    for user_id in user_ids:
        await redis.enqueue_job("sync_user_classroom", user_id)
        await asyncio.sleep(0.5)  # Stagger jobs
    
    await redis.close()
    
    return {"status": "queued", "users": len(user_ids)}


async def _sync_course(db: AsyncSession, owner_id: UUID, data: dict) -> Course:
    """Upsert course from Google data."""
    result = await db.execute(
        select(Course).where(Course.google_course_id == data["id"])
    )
    course = result.scalar_one_or_none()
    
    if course:
        course.name = data.get("name", course.name)
        course.section = data.get("section")
        course.description = data.get("descriptionHeading")
        course.state = data.get("courseState", "ACTIVE")
        course.synced_at = datetime.utcnow()
    else:
        course = Course(
            google_course_id=data["id"],
            name=data.get("name", "Untitled"),
            section=data.get("section"),
            description=data.get("descriptionHeading"),
            owner_id=owner_id,
            state=data.get("courseState", "ACTIVE"),
            synced_at=datetime.utcnow(),
        )
        db.add(course)
    
    await db.flush()
    return course


async def _sync_assignment(db: AsyncSession, course_id: UUID, data: dict) -> Assignment:
    """Upsert assignment from Google data."""
    result = await db.execute(
        select(Assignment).where(Assignment.google_assignment_id == data["id"])
    )
    assignment = result.scalar_one_or_none()
    
    # Parse due date
    due_date = None
    if "dueDate" in data:
        due = data["dueDate"]
        due_time = data.get("dueTime", {})
        due_date = datetime(
            due.get("year", 2000),
            due.get("month", 1),
            due.get("day", 1),
            due_time.get("hours", 23),
            due_time.get("minutes", 59),
        )
    
    if assignment:
        assignment.title = data.get("title", assignment.title)
        assignment.description = data.get("description")
        assignment.due_date = due_date
        assignment.max_points = data.get("maxPoints")
        assignment.state = data.get("state", "PUBLISHED")
    else:
        assignment = Assignment(
            google_assignment_id=data["id"],
            course_id=course_id,
            title=data.get("title", "Untitled"),
            description=data.get("description"),
            due_date=due_date,
            max_points=data.get("maxPoints"),
            state=data.get("state", "PUBLISHED"),
        )
        db.add(assignment)
    
    await db.flush()
    return assignment
