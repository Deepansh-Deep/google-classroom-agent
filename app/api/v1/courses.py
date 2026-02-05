"""
Courses API Endpoints

Handles course management, syncing, and enrollment operations.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import NotFoundError
from app.core.permissions import (
    CurrentUser,
    Permission,
    check_course_access,
    get_current_user,
    require_permission,
)
from app.integrations.google_classroom import (
    GoogleClassroomClient,
    parse_due_date,
    parse_google_datetime,
)
from app.models.database import (
    Assignment,
    Announcement,
    Course,
    Enrollment,
    Submission,
    User,
    get_db,
)
from app.models.schemas import (
    AssignmentListResponse,
    AssignmentResponse,
    CourseDetailResponse,
    CourseListResponse,
    CourseResponse,
    SyncRequest,
    SyncStatus,
)
from app.utils.logging import get_logger

router = APIRouter()
settings = get_settings()
logger = get_logger(__name__)


@router.get("", response_model=CourseListResponse)
@require_permission(Permission.VIEW_COURSES)
async def list_courses(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """
    List all courses the current user has access to.
    
    Teachers see courses they teach, students see enrolled courses.
    """
    # Get courses through enrollments
    query = (
        select(Course)
        .join(Enrollment, Course.id == Enrollment.course_id)
        .where(Enrollment.user_id == current_user.id)
        .order_by(Course.name)
        .offset(skip)
        .limit(limit)
    )
    
    result = await db.execute(query)
    courses = result.scalars().all()
    
    # Get total count
    count_query = (
        select(func.count())
        .select_from(Course)
        .join(Enrollment, Course.id == Enrollment.course_id)
        .where(Enrollment.user_id == current_user.id)
    )
    total = await db.execute(count_query)
    total_count = total.scalar() or 0
    
    return CourseListResponse(
        courses=[
            CourseResponse(
                id=c.id,
                google_course_id=c.google_course_id,
                name=c.name,
                section=c.section,
                description=c.description,
                room=c.room,
                state=c.state,
                synced_at=c.synced_at,
                created_at=c.created_at,
            )
            for c in courses
        ],
        total=total_count,
    )


@router.get("/{course_id}", response_model=CourseDetailResponse)
@require_permission(Permission.VIEW_COURSES)
async def get_course(
    course_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed information about a specific course."""
    await check_course_access(current_user, course_id, db)
    
    query = select(Course).where(Course.id == course_id)
    result = await db.execute(query)
    course = result.scalar_one_or_none()
    
    if not course:
        raise NotFoundError("Course", str(course_id))
    
    # Get counts
    student_count = await db.execute(
        select(func.count()).select_from(Enrollment).where(
            Enrollment.course_id == course_id,
            Enrollment.role == "student",
        )
    )
    
    assignment_count = await db.execute(
        select(func.count()).select_from(Assignment).where(
            Assignment.course_id == course_id,
        )
    )
    
    upcoming_deadline_count = await db.execute(
        select(func.count()).select_from(Assignment).where(
            Assignment.course_id == course_id,
            Assignment.due_date > datetime.utcnow(),
        )
    )
    
    return CourseDetailResponse(
        id=course.id,
        google_course_id=course.google_course_id,
        name=course.name,
        section=course.section,
        description=course.description,
        room=course.room,
        state=course.state,
        synced_at=course.synced_at,
        created_at=course.created_at,
        student_count=student_count.scalar() or 0,
        assignment_count=assignment_count.scalar() or 0,
        upcoming_deadline_count=upcoming_deadline_count.scalar() or 0,
    )


@router.get("/{course_id}/assignments", response_model=AssignmentListResponse)
@require_permission(Permission.VIEW_ASSIGNMENTS)
async def list_course_assignments(
    course_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    upcoming_only: bool = Query(False),
):
    """List all assignments for a course."""
    await check_course_access(current_user, course_id, db)
    
    query = (
        select(Assignment)
        .where(Assignment.course_id == course_id)
        .order_by(Assignment.due_date.desc().nullslast())
        .offset(skip)
        .limit(limit)
    )
    
    if upcoming_only:
        query = query.where(Assignment.due_date > datetime.utcnow())
    
    result = await db.execute(query)
    assignments = result.scalars().all()
    
    count_query = select(func.count()).select_from(Assignment).where(
        Assignment.course_id == course_id
    )
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


@router.post("/sync", response_model=SyncStatus)
@require_permission(Permission.SYNC_COURSES)
async def sync_courses(
    sync_request: Optional[SyncRequest] = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Sync courses from Google Classroom.
    
    Fetches all courses and their content from Google Classroom API
    and stores them in the local database.
    """
    # Get user's Google tokens
    user_query = select(User).where(User.id == current_user.id)
    result = await db.execute(user_query)
    user = result.scalar_one_or_none()
    
    if not user or not user.access_token:
        return SyncStatus(
            status="failed",
            errors=["No Google authentication found. Please re-authenticate."],
        )
    
    started_at = datetime.utcnow()
    errors = []
    courses_synced = 0
    assignments_synced = 0
    submissions_synced = 0
    
    try:
        client = GoogleClassroomClient(user.access_token, user.refresh_token)
        
        # Fetch courses
        google_courses = await client.get_courses()
        
        for gc in google_courses:
            try:
                # Check if course exists
                existing = await db.execute(
                    select(Course).where(Course.google_course_id == gc["id"])
                )
                course = existing.scalar_one_or_none()
                
                if course:
                    # Update existing course
                    course.name = gc.get("name", course.name)
                    course.section = gc.get("section")
                    course.description = gc.get("description")
                    course.room = gc.get("room")
                    course.state = gc.get("courseState", "ACTIVE")
                    course.synced_at = datetime.utcnow()
                else:
                    # Create new course
                    course = Course(
                        google_course_id=gc["id"],
                        name=gc.get("name", "Untitled Course"),
                        section=gc.get("section"),
                        description=gc.get("description"),
                        room=gc.get("room"),
                        state=gc.get("courseState", "ACTIVE"),
                        synced_at=datetime.utcnow(),
                    )
                    db.add(course)
                    await db.flush()
                
                courses_synced += 1
                
                # Check if user is teacher of this course
                teachers = await client.get_course_teachers(gc["id"])
                is_teacher = any(
                    t.get("profile", {}).get("emailAddress") == user.email
                    for t in teachers
                )
                
                # Create/update enrollment
                enrollment_query = select(Enrollment).where(
                    Enrollment.user_id == user.id,
                    Enrollment.course_id == course.id,
                )
                existing_enrollment = await db.execute(enrollment_query)
                enrollment = existing_enrollment.scalar_one_or_none()
                
                if not enrollment:
                    enrollment = Enrollment(
                        user_id=user.id,
                        course_id=course.id,
                        role="teacher" if is_teacher else "student",
                    )
                    db.add(enrollment)
                
                # Update user role if they're a teacher
                if is_teacher and user.role == "student":
                    user.role = "teacher"
                
                # Sync assignments
                google_assignments = await client.get_assignments(gc["id"])
                
                for ga in google_assignments:
                    existing_assignment = await db.execute(
                        select(Assignment).where(
                            Assignment.google_assignment_id == ga["id"]
                        )
                    )
                    assignment = existing_assignment.scalar_one_or_none()
                    
                    due_date = parse_due_date(
                        ga.get("dueDate"),
                        ga.get("dueTime"),
                    )
                    
                    if assignment:
                        assignment.title = ga.get("title", assignment.title)
                        assignment.description = ga.get("description")
                        assignment.max_points = ga.get("maxPoints")
                        assignment.due_date = due_date
                        assignment.state = ga.get("state", "PUBLISHED")
                        assignment.work_type = ga.get("workType")
                    else:
                        assignment = Assignment(
                            google_assignment_id=ga["id"],
                            course_id=course.id,
                            title=ga.get("title", "Untitled Assignment"),
                            description=ga.get("description"),
                            max_points=ga.get("maxPoints"),
                            due_date=due_date,
                            state=ga.get("state", "PUBLISHED"),
                            work_type=ga.get("workType"),
                        )
                        db.add(assignment)
                        await db.flush()
                    
                    assignments_synced += 1
                    
                    # Sync submissions (for teachers only)
                    if is_teacher:
                        google_submissions = await client.get_submissions(
                            gc["id"],
                            ga["id"],
                        )
                        
                        for gs in google_submissions:
                            # Get student user
                            student_email = gs.get("userId")
                            if not student_email:
                                continue
                            
                            existing_sub = await db.execute(
                                select(Submission).where(
                                    Submission.google_submission_id == gs["id"]
                                )
                            )
                            submission = existing_sub.scalar_one_or_none()
                            
                            # Find or create student user
                            student_query = select(User).where(
                                User.google_id == gs.get("userId")
                            )
                            student_result = await db.execute(student_query)
                            student = student_result.scalar_one_or_none()
                            
                            if not student:
                                # Create placeholder student
                                student = User(
                                    email=f"{gs.get('userId')}@placeholder.local",
                                    google_id=gs.get("userId"),
                                    role="student",
                                )
                                db.add(student)
                                await db.flush()
                            
                            submitted_at = parse_google_datetime(
                                gs.get("submissionHistory", [{}])[-1]
                                .get("stateHistory", {})
                                .get("stateTimestamp")
                            ) if gs.get("submissionHistory") else None
                            
                            is_late = False
                            if due_date and submitted_at:
                                is_late = submitted_at > due_date
                            
                            if submission:
                                submission.state = gs.get("state", submission.state)
                                submission.grade = gs.get("assignedGrade")
                                submission.draft_grade = gs.get("draftGrade")
                                submission.submitted_at = submitted_at
                                submission.late = is_late
                            else:
                                submission = Submission(
                                    google_submission_id=gs["id"],
                                    assignment_id=assignment.id,
                                    student_id=student.id,
                                    state=gs.get("state", "NEW"),
                                    grade=gs.get("assignedGrade"),
                                    draft_grade=gs.get("draftGrade"),
                                    submitted_at=submitted_at,
                                    late=is_late,
                                )
                                db.add(submission)
                            
                            submissions_synced += 1
                
                # Sync announcements
                google_announcements = await client.get_announcements(gc["id"])
                
                for gann in google_announcements:
                    existing_ann = await db.execute(
                        select(Announcement).where(
                            Announcement.google_announcement_id == gann["id"]
                        )
                    )
                    announcement = existing_ann.scalar_one_or_none()
                    
                    if not announcement:
                        announcement = Announcement(
                            google_announcement_id=gann["id"],
                            course_id=course.id,
                            text=gann.get("text"),
                            state=gann.get("state", "PUBLISHED"),
                            creator_user_id=gann.get("creatorUserId"),
                            creation_time=parse_google_datetime(gann.get("creationTime")),
                            update_time=parse_google_datetime(gann.get("updateTime")),
                        )
                        db.add(announcement)
                
            except Exception as e:
                errors.append(f"Error syncing course {gc.get('name', gc.get('id'))}: {str(e)}")
                logger.error("Course sync error", course_id=gc.get("id"), error=str(e))
        
        await db.commit()
        
        logger.info(
            "Sync completed",
            courses=courses_synced,
            assignments=assignments_synced,
            submissions=submissions_synced,
            errors=len(errors),
        )
        
        return SyncStatus(
            status="completed",
            started_at=started_at,
            completed_at=datetime.utcnow(),
            courses_synced=courses_synced,
            assignments_synced=assignments_synced,
            submissions_synced=submissions_synced,
            errors=errors,
        )
        
    except Exception as e:
        logger.error("Sync failed", error=str(e))
        return SyncStatus(
            status="failed",
            started_at=started_at,
            errors=[str(e)],
        )
