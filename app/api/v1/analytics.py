"""
Analytics API Endpoints - Performance tracking and insights.
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.permissions import CurrentUser, Permission, get_current_user, require_permission, check_course_access
from app.models.database import Enrollment, User, get_db
from app.models.schemas import PerformanceScoreResponse, ClassPerformanceOverview, StudentPerformanceSummary, UserResponse
from app.services.analytics_service import analytics_service
from app.utils.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/my-performance", response_model=List[PerformanceScoreResponse])
@require_permission(Permission.VIEW_OWN_ANALYTICS)
async def get_my_performance(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's performance across all enrolled courses."""
    enrollments = (await db.execute(
        select(Enrollment).where(Enrollment.user_id == current_user.id)
    )).scalars().all()
    
    scores = []
    for enrollment in enrollments:
        score = await analytics_service.calculate_student_performance(
            db, current_user.id, enrollment.course_id
        )
        scores.append(score)
    
    return scores


@router.get("/course/{course_id}", response_model=ClassPerformanceOverview)
@require_permission(Permission.VIEW_CLASS_ANALYTICS)
async def get_class_performance(
    course_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get class-wide performance overview (teachers only)."""
    await check_course_access(current_user, course_id, db, require_teacher=True)
    
    from app.models.database import Course
    course = (await db.execute(select(Course).where(Course.id == course_id))).scalar_one_or_none()
    if not course:
        raise NotFoundError("Course", str(course_id))
    
    overview = await analytics_service.get_class_overview(db, course_id)
    
    # Get detailed student performance
    enrollments = (await db.execute(
        select(Enrollment, User).join(User).where(
            Enrollment.course_id == course_id, Enrollment.role == "student"
        )
    )).all()
    
    students = []
    for enrollment, user in enrollments:
        score = await analytics_service.calculate_student_performance(db, user.id, course_id)
        students.append(StudentPerformanceSummary(
            student=UserResponse(
                id=user.id, email=user.email, name=user.name, role=user.role,
                avatar_url=user.avatar_url, created_at=user.created_at, last_login=user.last_login
            ),
            performance=score
        ))
    
    return ClassPerformanceOverview(
        course_id=course_id, course_name=course.name,
        total_students=overview["total"], good_count=overview["good"],
        medium_count=overview["medium"], at_risk_count=overview["at_risk"],
        average_score=overview["average"], students=students
    )


@router.get("/student/{student_id}/course/{course_id}", response_model=PerformanceScoreResponse)
@require_permission(Permission.VIEW_CLASS_ANALYTICS)
async def get_student_performance(
    student_id: UUID,
    course_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get specific student's performance (teachers only)."""
    await check_course_access(current_user, course_id, db, require_teacher=True)
    return await analytics_service.calculate_student_performance(db, student_id, course_id)
