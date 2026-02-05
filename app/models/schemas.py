"""
Pydantic Schemas for API Request/Response Validation

Provides type-safe data transfer objects for all API endpoints.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


# ============= Base Schemas =============

class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    
    class Config:
        from_attributes = True
        populate_by_name = True


# ============= User Schemas =============

class UserBase(BaseSchema):
    email: EmailStr
    name: Optional[str] = None
    role: str = "student"


class UserCreate(UserBase):
    google_id: str


class UserUpdate(BaseSchema):
    name: Optional[str] = None
    reminder_email: Optional[bool] = None
    reminder_push: Optional[bool] = None
    reminder_hours_before: Optional[int] = Field(None, ge=1, le=168)


class UserResponse(UserBase):
    id: UUID
    avatar_url: Optional[str] = None
    created_at: datetime
    last_login: Optional[datetime] = None


class UserDetailResponse(UserResponse):
    reminder_email: bool
    reminder_push: bool
    reminder_hours_before: int


# ============= Auth Schemas =============

class TokenResponse(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenPayload(BaseSchema):
    sub: str  # User ID
    email: str
    role: str
    exp: int


class GoogleAuthURL(BaseSchema):
    auth_url: str


class GoogleAuthCallback(BaseSchema):
    code: str
    state: Optional[str] = None


# ============= Course Schemas =============

class CourseBase(BaseSchema):
    name: str
    section: Optional[str] = None
    description: Optional[str] = None
    room: Optional[str] = None


class CourseResponse(CourseBase):
    id: UUID
    google_course_id: str
    state: str
    synced_at: Optional[datetime] = None
    created_at: datetime


class CourseDetailResponse(CourseResponse):
    owner: Optional[UserResponse] = None
    student_count: int = 0
    assignment_count: int = 0
    upcoming_deadline_count: int = 0


class CourseListResponse(BaseSchema):
    courses: List[CourseResponse]
    total: int


# ============= Assignment Schemas =============

class AssignmentBase(BaseSchema):
    title: str
    description: Optional[str] = None
    max_points: Optional[float] = None
    due_date: Optional[datetime] = None


class AssignmentResponse(AssignmentBase):
    id: UUID
    google_assignment_id: str
    course_id: UUID
    state: str
    work_type: Optional[str] = None
    created_at: datetime


class AssignmentDetailResponse(AssignmentResponse):
    course: Optional[CourseResponse] = None
    submission_count: int = 0
    submitted_count: int = 0
    graded_count: int = 0
    late_count: int = 0


class AssignmentListResponse(BaseSchema):
    assignments: List[AssignmentResponse]
    total: int


class UpcomingDeadline(BaseSchema):
    assignment: AssignmentResponse
    time_remaining: str
    urgency: str  # "urgent", "soon", "upcoming"


# ============= Submission Schemas =============

class SubmissionBase(BaseSchema):
    state: str
    grade: Optional[float] = None
    late: bool = False


class SubmissionResponse(SubmissionBase):
    id: UUID
    google_submission_id: str
    assignment_id: UUID
    student_id: UUID
    submitted_at: Optional[datetime] = None
    returned_at: Optional[datetime] = None
    created_at: datetime


class SubmissionDetailResponse(SubmissionResponse):
    student: Optional[UserResponse] = None
    assignment: Optional[AssignmentResponse] = None


class SubmissionListResponse(BaseSchema):
    submissions: List[SubmissionResponse]
    total: int


# ============= Announcement Schemas =============

class AnnouncementResponse(BaseSchema):
    id: UUID
    google_announcement_id: str
    course_id: UUID
    text: Optional[str] = None
    state: str
    creation_time: Optional[datetime] = None


class AnnouncementListResponse(BaseSchema):
    announcements: List[AnnouncementResponse]
    total: int


# ============= Performance Analytics Schemas =============

class PerformanceFactors(BaseSchema):
    timeliness: float = Field(..., ge=0, le=100, description="On-time submission rate")
    consistency: float = Field(..., ge=0, le=100, description="Regular submission pattern")
    completion: float = Field(..., ge=0, le=100, description="Assignment completion rate")
    grade: Optional[float] = Field(None, ge=0, le=100, description="Average grade performance")


class PerformanceExplanation(BaseSchema):
    summary: str
    factors: Dict[str, str]
    recommendations: List[str]


class PerformanceScoreResponse(BaseSchema):
    student_id: UUID
    course_id: UUID
    score: float = Field(..., ge=0, le=100)
    category: str  # "good", "medium", "at_risk"
    factors: PerformanceFactors
    explanation: PerformanceExplanation
    calculated_at: datetime
    assignments_analyzed: int


class StudentPerformanceSummary(BaseSchema):
    student: UserResponse
    performance: PerformanceScoreResponse


class ClassPerformanceOverview(BaseSchema):
    course_id: UUID
    course_name: str
    total_students: int
    good_count: int
    medium_count: int
    at_risk_count: int
    average_score: float
    students: List[StudentPerformanceSummary]


# ============= Q&A Schemas =============

class QuestionRequest(BaseSchema):
    question: str = Field(..., min_length=3, max_length=1000)
    course_id: Optional[UUID] = None


class Source(BaseSchema):
    type: str  # "assignment", "announcement", "course_material"
    title: str
    excerpt: str
    relevance_score: float


class QAResponse(BaseSchema):
    question: str
    answer: str
    confidence: float = Field(..., ge=0, le=1)
    sources: List[Source]
    explanation: str
    answered_at: datetime


class ChatMessage(BaseSchema):
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime


class ChatSession(BaseSchema):
    session_id: UUID
    course_id: Optional[UUID] = None
    messages: List[ChatMessage]
    created_at: datetime


# ============= Reminder Schemas =============

class ReminderSettings(BaseSchema):
    email_enabled: bool = True
    push_enabled: bool = True
    hours_before_deadline: int = Field(24, ge=1, le=168)


class ReminderResponse(BaseSchema):
    id: UUID
    assignment_id: UUID
    reminder_type: str
    scheduled_for: datetime
    sent: bool
    channel: str


class UpcomingReminder(BaseSchema):
    assignment: AssignmentResponse
    reminder_type: str
    scheduled_for: datetime


# ============= Report Schemas =============

class ReportRequest(BaseSchema):
    course_id: UUID
    report_type: str = "weekly"  # "weekly", "monthly", "custom"
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class ReportSummary(BaseSchema):
    report_id: UUID
    course_name: str
    report_type: str
    period: str
    generated_at: datetime
    total_assignments: int
    total_submissions: int
    average_grade: Optional[float] = None
    on_time_rate: float
    student_count: int


class StudentReportEntry(BaseSchema):
    student: UserResponse
    assignments_completed: int
    assignments_total: int
    on_time_submissions: int
    late_submissions: int
    missing_assignments: int
    average_grade: Optional[float] = None
    performance_category: str


class FullReport(BaseSchema):
    summary: ReportSummary
    students: List[StudentReportEntry]
    download_url: Optional[str] = None


# ============= Sync Schemas =============

class SyncRequest(BaseSchema):
    course_ids: Optional[List[str]] = None
    sync_type: str = "full"  # "full", "incremental"


class SyncStatus(BaseSchema):
    status: str  # "pending", "in_progress", "completed", "failed"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    courses_synced: int = 0
    assignments_synced: int = 0
    submissions_synced: int = 0
    errors: List[str] = []


# ============= Dashboard Schemas =============

class TeacherDashboard(BaseSchema):
    user: UserResponse
    courses: List[CourseDetailResponse]
    at_risk_students: List[StudentPerformanceSummary]
    upcoming_deadlines: List[UpcomingDeadline]
    recent_submissions: List[SubmissionDetailResponse]
    sync_status: Optional[SyncStatus] = None


class StudentDashboard(BaseSchema):
    user: UserResponse
    enrolled_courses: List[CourseResponse]
    upcoming_deadlines: List[UpcomingDeadline]
    recent_submissions: List[SubmissionDetailResponse]
    performance_summary: Optional[PerformanceScoreResponse] = None
    upcoming_reminders: List[UpcomingReminder]
