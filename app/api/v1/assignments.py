"""
Assignments API Endpoints

Handles assignment listing, details, and submission tracking.
"""

from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.permissions import (
    CurrentUser,
    Permission,
    check_course_access,
    get_current_user,
    require_permission,
)
from app.models.database import (
    Assignment,
    Course,
    Enrollment,
    Submission,
    get_db,
)
from app.models.schemas import (
    AssignmentDetailResponse,
    AssignmentResponse,
    AssignmentListResponse,
    CourseResponse,
    SubmissionDetailResponse,
    SubmissionListResponse,
    SubmissionResponse,
    UpcomingDeadline,
    UserResponse,
)
from app.utils.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


def calculate_urgency(due_date: Optional[datetime]) -> str:
    """Calculate deadline urgency level."""
    if not due_date:
        return "upcoming"
    
    now = datetime.utcnow()
    time_remaining = due_date - now
    
    if time_remaining < timedelta(hours=24):
        return "urgent"
    elif time_remaining < timedelta(days=3):
        return "soon"
    else:
        return "upcoming"


def format_time_remaining(due_date: Optional[datetime]) -> str:
    """Format time remaining until deadline."""
    if not due_date:
        return "No deadline"
    
    now = datetime.utcnow()
    diff = due_date - now
    
    if diff.total_seconds() < 0:
        return "Overdue"
    
    days = diff.days
    hours = diff.seconds // 3600
    minutes = (diff.seconds % 3600) // 60
    
    if days > 0:
        return f"{days}d {hours}h remaining"
    elif hours > 0:
        return f"{hours}h {minutes}m remaining"
    else:
        return f"{minutes}m remaining"


@router.get("", response_model=AssignmentListResponse)
@require_permission(Permission.VIEW_ASSIGNMENTS)
async def list_assignments(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    course_id: Optional[UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    upcoming_only: bool = Query(False),
):
    """List all assignments accessible to the current user."""
    # Base query with course access check
    query = (
        select(Assignment)
        .join(Course, Assignment.course_id == Course.id)
        .join(Enrollment, Course.id == Enrollment.course_id)
        .where(Enrollment.user_id == current_user.id)
    )
    
    if course_id:
        query = query.where(Assignment.course_id == course_id)
    
    if upcoming_only:
        query = query.where(Assignment.due_date > datetime.utcnow())
    
    query = query.order_by(Assignment.due_date.asc().nullslast()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    assignments = result.scalars().all()
    
    # Get total count
    count_query = (
        select(func.count())
        .select_from(Assignment)
        .join(Course, Assignment.course_id == Course.id)
        .join(Enrollment, Course.id == Enrollment.course_id)
        .where(Enrollment.user_id == current_user.id)
    )
    if course_id:
        count_query = count_query.where(Assignment.course_id == course_id)
    if upcoming_only:
        count_query = count_query.where(Assignment.due_date > datetime.utcnow())
    
    total = await db.execute(count_query)
    
    return AssignmentListResponse(
        assignments=[
            AssignmentResponse(
                id=a.id,
                google_assignment_id=a.google_assignment_id,
                course_id=a.course_id,
                title=a.title,
                description=a.description,
                max_points=a.max_points,
                due_date=a.due_date,
                state=a.state,
                work_type=a.work_type,
                created_at=a.created_at,
            )
            for a in assignments
        ],
        total=total.scalar() or 0,
    )


@router.get("/upcoming", response_model=List[UpcomingDeadline])
@require_permission(Permission.VIEW_ASSIGNMENTS)
async def get_upcoming_deadlines(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    days: int = Query(7, ge=1, le=30),
    limit: int = Query(10, ge=1, le=50),
):
    """Get upcoming assignment deadlines."""
    deadline_cutoff = datetime.utcnow() + timedelta(days=days)
    
    query = (
        select(Assignment)
        .join(Course, Assignment.course_id == Course.id)
        .join(Enrollment, Course.id == Enrollment.course_id)
        .where(
            Enrollment.user_id == current_user.id,
            Assignment.due_date > datetime.utcnow(),
            Assignment.due_date <= deadline_cutoff,
        )
        .order_by(Assignment.due_date.asc())
        .limit(limit)
    )
    
    result = await db.execute(query)
    assignments = result.scalars().all()
    
    return [
        UpcomingDeadline(
            assignment=AssignmentResponse(
                id=a.id,
                google_assignment_id=a.google_assignment_id,
                course_id=a.course_id,
                title=a.title,
                description=a.description,
                max_points=a.max_points,
                due_date=a.due_date,
                state=a.state,
                work_type=a.work_type,
                created_at=a.created_at,
            ),
            time_remaining=format_time_remaining(a.due_date),
            urgency=calculate_urgency(a.due_date),
        )
        for a in assignments
    ]


@router.get("/{assignment_id}", response_model=AssignmentDetailResponse)
@require_permission(Permission.VIEW_ASSIGNMENTS)
async def get_assignment(
    assignment_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed information about a specific assignment."""
    query = select(Assignment).where(Assignment.id == assignment_id)
    result = await db.execute(query)
    assignment = result.scalar_one_or_none()
    
    if not assignment:
        raise NotFoundError("Assignment", str(assignment_id))
    
    # Check course access
    await check_course_access(current_user, assignment.course_id, db)
    
    # Get course
    course_query = select(Course).where(Course.id == assignment.course_id)
    course_result = await db.execute(course_query)
    course = course_result.scalar_one_or_none()
    
    # Get submission counts
    submission_count = await db.execute(
        select(func.count()).select_from(Submission).where(
            Submission.assignment_id == assignment_id
        )
    )
    
    submitted_count = await db.execute(
        select(func.count()).select_from(Submission).where(
            Submission.assignment_id == assignment_id,
            Submission.state.in_(["TURNED_IN", "RETURNED"]),
        )
    )
    
    graded_count = await db.execute(
        select(func.count()).select_from(Submission).where(
            Submission.assignment_id == assignment_id,
            Submission.grade.isnot(None),
        )
    )
    
    late_count = await db.execute(
        select(func.count()).select_from(Submission).where(
            Submission.assignment_id == assignment_id,
            Submission.late == True,
        )
    )
    
    return AssignmentDetailResponse(
        id=assignment.id,
        google_assignment_id=assignment.google_assignment_id,
        course_id=assignment.course_id,
        title=assignment.title,
        description=assignment.description,
        max_points=assignment.max_points,
        due_date=assignment.due_date,
        state=assignment.state,
        work_type=assignment.work_type,
        created_at=assignment.created_at,
        course=CourseResponse(
            id=course.id,
            google_course_id=course.google_course_id,
            name=course.name,
            section=course.section,
            description=course.description,
            room=course.room,
            state=course.state,
            synced_at=course.synced_at,
            created_at=course.created_at,
        ) if course else None,
        submission_count=submission_count.scalar() or 0,
        submitted_count=submitted_count.scalar() or 0,
        graded_count=graded_count.scalar() or 0,
        late_count=late_count.scalar() or 0,
    )


@router.get("/{assignment_id}/submissions", response_model=SubmissionListResponse)
@require_permission(Permission.VIEW_ALL_SUBMISSIONS)
async def get_assignment_submissions(
    assignment_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    state: Optional[str] = Query(None),
):
    """Get all submissions for an assignment (teachers only)."""
    # Get assignment and verify access
    assignment_query = select(Assignment).where(Assignment.id == assignment_id)
    assignment_result = await db.execute(assignment_query)
    assignment = assignment_result.scalar_one_or_none()
    
    if not assignment:
        raise NotFoundError("Assignment", str(assignment_id))
    
    await check_course_access(current_user, assignment.course_id, db, require_teacher=True)
    
    # Get submissions
    query = (
        select(Submission)
        .where(Submission.assignment_id == assignment_id)
        .order_by(Submission.submitted_at.desc().nullslast())
        .offset(skip)
        .limit(limit)
    )
    
    if state:
        query = query.where(Submission.state == state)
    
    result = await db.execute(query)
    submissions = result.scalars().all()
    
    count_query = select(func.count()).select_from(Submission).where(
        Submission.assignment_id == assignment_id
    )
    total = await db.execute(count_query)
    
    return SubmissionListResponse(
        submissions=[
            SubmissionResponse(
                id=s.id,
                google_submission_id=s.google_submission_id,
                assignment_id=s.assignment_id,
                student_id=s.student_id,
                state=s.state,
                grade=s.grade,
                late=s.late,
                submitted_at=s.submitted_at,
                returned_at=s.returned_at,
                created_at=s.created_at,
            )
            for s in submissions
        ],
        total=total.scalar() or 0,
    )


@router.get("/my-submissions/all", response_model=SubmissionListResponse)
@require_permission(Permission.VIEW_OWN_SUBMISSIONS)
async def get_my_submissions(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    course_id: Optional[UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """Get current user's submissions."""
    query = (
        select(Submission)
        .where(Submission.student_id == current_user.id)
        .order_by(Submission.submitted_at.desc().nullslast())
        .offset(skip)
        .limit(limit)
    )
    
    if course_id:
        query = query.join(Assignment).where(Assignment.course_id == course_id)
    
    result = await db.execute(query)
    submissions = result.scalars().all()
    
    count_query = select(func.count()).select_from(Submission).where(
        Submission.student_id == current_user.id
    )
    total = await db.execute(count_query)
    
    return SubmissionListResponse(
        submissions=[
            SubmissionResponse(
                id=s.id,
                google_submission_id=s.google_submission_id,
                assignment_id=s.assignment_id,
                student_id=s.student_id,
                state=s.state,
                grade=s.grade,
                late=s.late,
                submitted_at=s.submitted_at,
                returned_at=s.returned_at,
                created_at=s.created_at,
            )
            for s in submissions
        ],
        total=total.scalar() or 0,
    )
