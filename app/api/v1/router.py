"""
API v1 Router - Aggregates all endpoint routers

Central routing configuration for the v1 API.
"""

from fastapi import APIRouter

from app.api.v1 import auth, courses, assignments, qa, analytics, reminders, reports

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"],
)

api_router.include_router(
    courses.router,
    prefix="/courses",
    tags=["Courses"],
)

api_router.include_router(
    assignments.router,
    prefix="/assignments",
    tags=["Assignments"],
)

api_router.include_router(
    qa.router,
    prefix="/qa",
    tags=["Q&A"],
)

api_router.include_router(
    analytics.router,
    prefix="/analytics",
    tags=["Analytics"],
)

api_router.include_router(
    reminders.router,
    prefix="/reminders",
    tags=["Reminders"],
)

api_router.include_router(
    reports.router,
    prefix="/reports",
    tags=["Reports"],
)
