"""
Database Models and Connection Management

SQLAlchemy async models for PostgreSQL with proper relationship definitions.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.config import get_settings

settings = get_settings()

# Async engine for PostgreSQL
engine = create_async_engine(
    settings.database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    echo=settings.debug,
)

# Session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class UserRole(str, Enum):
    """User role enumeration."""
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"


class User(Base):
    """User model with OAuth token storage."""
    
    __tablename__ = "users"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="student")
    google_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # OAuth tokens (encrypted in production)
    access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    token_expiry: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Reminder preferences
    reminder_email: Mapped[bool] = mapped_column(Boolean, default=True)
    reminder_push: Mapped[bool] = mapped_column(Boolean, default=True)
    reminder_hours_before: Mapped[int] = mapped_column(Integer, default=24)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    courses_owned = relationship("Course", back_populates="owner", lazy="selectin")
    enrollments = relationship("Enrollment", back_populates="user", lazy="selectin")
    submissions = relationship("Submission", back_populates="student", lazy="selectin")
    performance_scores = relationship("PerformanceScore", back_populates="student", lazy="selectin")


class Course(Base):
    """Course model synced from Google Classroom."""
    
    __tablename__ = "courses"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    google_course_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    section: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    room: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    state: Mapped[str] = mapped_column(String(50), default="ACTIVE")
    
    # Sync metadata
    synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    owner = relationship("User", back_populates="courses_owned", lazy="selectin")
    enrollments = relationship("Enrollment", back_populates="course", lazy="selectin", cascade="all, delete-orphan")
    assignments = relationship("Assignment", back_populates="course", lazy="selectin", cascade="all, delete-orphan")
    announcements = relationship("Announcement", back_populates="course", lazy="selectin", cascade="all, delete-orphan")


class Enrollment(Base):
    """User enrollment in a course."""
    
    __tablename__ = "enrollments"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    course_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)  # "teacher" or "student"
    google_enrollment_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="enrollments", lazy="selectin")
    course = relationship("Course", back_populates="enrollments", lazy="selectin")
    
    __table_args__ = (
        UniqueConstraint("user_id", "course_id", name="unique_enrollment"),
    )


class Assignment(Base):
    """Assignment model with deadline tracking."""
    
    __tablename__ = "assignments"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    google_assignment_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    course_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False)
    
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    max_points: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    due_time: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    state: Mapped[str] = mapped_column(String(50), default="PUBLISHED")
    work_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Embedding status
    embedded: Mapped[bool] = mapped_column(Boolean, default=False)
    embedded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    course = relationship("Course", back_populates="assignments", lazy="selectin")
    submissions = relationship("Submission", back_populates="assignment", lazy="selectin", cascade="all, delete-orphan")


class Submission(Base):
    """Student assignment submission."""
    
    __tablename__ = "submissions"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    google_submission_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    assignment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assignments.id"), nullable=False)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    state: Mapped[str] = mapped_column(String(50), nullable=False)  # NEW, CREATED, TURNED_IN, RETURNED, etc.
    grade: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    draft_grade: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    returned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    late: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    assignment = relationship("Assignment", back_populates="submissions", lazy="selectin")
    student = relationship("User", back_populates="submissions", lazy="selectin")


class Announcement(Base):
    """Course announcement."""
    
    __tablename__ = "announcements"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    google_announcement_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    course_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False)
    
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    state: Mapped[str] = mapped_column(String(50), default="PUBLISHED")
    creator_user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Embedding status
    embedded: Mapped[bool] = mapped_column(Boolean, default=False)
    embedded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    creation_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    update_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    course = relationship("Course", back_populates="announcements", lazy="selectin")


class PerformanceScore(Base):
    """Student performance score with explainable factors."""
    
    __tablename__ = "performance_scores"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    course_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False)
    
    # Overall score (0-100)
    score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # "good", "medium", "at_risk"
    
    # Individual factors (0-100 each)
    timeliness_factor: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    consistency_factor: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    completion_factor: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    grade_factor: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    
    # Detailed explanation
    explanation: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    
    # Calculation metadata
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    assignments_analyzed: Mapped[int] = mapped_column(Integer, default=0)
    
    # Relationships
    student = relationship("User", back_populates="performance_scores", lazy="selectin")
    
    __table_args__ = (
        UniqueConstraint("student_id", "course_id", name="unique_student_course_score"),
    )


class AuditLog(Base):
    """Audit log for tracking important actions."""
    
    __tablename__ = "audit_logs"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    details: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)


class ReminderSchedule(Base):
    """Scheduled reminders for assignments."""
    
    __tablename__ = "reminder_schedules"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    assignment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assignments.id"), nullable=False)
    
    reminder_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "upcoming", "deadline", "overdue"
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    sent: Mapped[bool] = mapped_column(Boolean, default=False)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    channel: Mapped[str] = mapped_column(String(50), default="email")  # "email", "push", "webhook"
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


# Database initialization functions
async def init_db() -> None:
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()


async def get_db() -> AsyncSession:
    """Get a database session."""
    async with async_session_factory() as session:
        yield session


async def check_db_connection() -> bool:
    """Check if database is accessible."""
    try:
        async with async_session_factory() as session:
            await session.execute("SELECT 1")
        return True
    except Exception:
        return False
