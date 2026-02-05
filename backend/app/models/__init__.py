"""Models module initialization."""

from app.models.database import (
    User,
    Course,
    Enrollment,
    Assignment,
    Submission,
    Announcement,
    PerformanceScore,
    AuditLog,
    ReminderSchedule,
    get_db,
    init_db,
    close_db,
)

__all__ = [
    "User",
    "Course",
    "Enrollment",
    "Assignment",
    "Submission",
    "Announcement",
    "PerformanceScore",
    "AuditLog",
    "ReminderSchedule",
    "get_db",
    "init_db",
    "close_db",
]
