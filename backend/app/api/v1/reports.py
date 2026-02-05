"""
Reports API Endpoints - Generate and export reports.
"""

from typing import Optional
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CurrentUser, Permission, get_current_user, require_permission, check_course_access
from app.models.database import get_db
from app.models.schemas import ReportRequest, FullReport
from app.services.report_service import report_service

router = APIRouter()


@router.post("/{course_id}", response_model=FullReport)
@require_permission(Permission.GENERATE_REPORTS)
async def generate_report(
    course_id: UUID,
    report_type: str = Query("weekly", regex="^(weekly|monthly)$"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate performance report for a course."""
    await check_course_access(current_user, course_id, db, require_teacher=True)
    return await report_service.generate_report(db, course_id, report_type)


@router.get("/{course_id}/csv")
@require_permission(Permission.EXPORT_DATA)
async def export_csv(
    course_id: UUID,
    report_type: str = Query("weekly", regex="^(weekly|monthly)$"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export report as CSV."""
    await check_course_access(current_user, course_id, db, require_teacher=True)
    
    report = await report_service.generate_report(db, course_id, report_type)
    csv_content = report_service.generate_csv(report)
    
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=report_{course_id}_{report_type}.csv"}
    )
