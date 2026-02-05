"""
Report Service - Weekly/Monthly report generation with CSV export.
"""

import csv
import io
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import and_, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Assignment, Submission, User, Enrollment, Course
from app.models.schemas import ReportSummary, StudentReportEntry, FullReport, UserResponse
from app.services.analytics_service import analytics_service
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ReportService:
    """Report generation for teachers."""
    
    async def generate_report(
        self, db: AsyncSession, course_id: UUID, 
        report_type: str = "weekly", start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> FullReport:
        """Generate performance report for a course."""
        
        # Calculate date range
        now = datetime.utcnow()
        if report_type == "weekly":
            start = start_date or (now - timedelta(days=7))
            end = end_date or now
            period = f"Week of {start.strftime('%Y-%m-%d')}"
        else:
            start = start_date or now.replace(day=1)
            end = end_date or now
            period = f"{start.strftime('%B %Y')}"
        
        # Get course
        course = (await db.execute(select(Course).where(Course.id == course_id))).scalar_one_or_none()
        if not course:
            raise ValueError("Course not found")
        
        # Get assignments in range
        assignments = (await db.execute(
            select(Assignment).where(
                Assignment.course_id == course_id,
                Assignment.created_at >= start,
                Assignment.created_at <= end
            )
        )).scalars().all()
        
        # Get students
        enrollments = (await db.execute(
            select(Enrollment, User).join(User).where(
                Enrollment.course_id == course_id, Enrollment.role == "student"
            )
        )).all()
        
        student_entries = []
        total_submissions = 0
        total_on_time = 0
        total_grades = []
        
        for enrollment, user in enrollments:
            # Get submissions for this student
            submissions = (await db.execute(
                select(Submission).where(
                    Submission.student_id == user.id,
                    Submission.assignment_id.in_([a.id for a in assignments])
                )
            )).scalars().all()
            
            completed = [s for s in submissions if s.state in ["TURNED_IN", "RETURNED"]]
            on_time = sum(1 for s in completed if not s.late)
            late = sum(1 for s in completed if s.late)
            missing = len(assignments) - len(completed)
            
            grades = [s.grade for s in completed if s.grade is not None]
            avg_grade = sum(grades) / len(grades) if grades else None
            
            total_submissions += len(completed)
            total_on_time += on_time
            if grades:
                total_grades.extend(grades)
            
            performance = await analytics_service.calculate_student_performance(db, user.id, course_id)
            
            student_entries.append(StudentReportEntry(
                student=UserResponse(
                    id=user.id, email=user.email, name=user.name, role=user.role,
                    avatar_url=user.avatar_url, created_at=user.created_at, last_login=user.last_login
                ),
                assignments_completed=len(completed),
                assignments_total=len(assignments),
                on_time_submissions=on_time,
                late_submissions=late,
                missing_assignments=missing,
                average_grade=avg_grade,
                performance_category=performance.category
            ))
        
        summary = ReportSummary(
            report_id=uuid4(),
            course_name=course.name,
            report_type=report_type,
            period=period,
            generated_at=datetime.utcnow(),
            total_assignments=len(assignments),
            total_submissions=total_submissions,
            average_grade=sum(total_grades) / len(total_grades) if total_grades else None,
            on_time_rate=(total_on_time / total_submissions * 100) if total_submissions else 0,
            student_count=len(enrollments)
        )
        
        return FullReport(summary=summary, students=student_entries)
    
    def generate_csv(self, report: FullReport) -> str:
        """Generate CSV content from report."""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            "Student Name", "Email", "Completed", "Total", "On Time", "Late", 
            "Missing", "Average Grade", "Performance"
        ])
        
        # Data
        for entry in report.students:
            writer.writerow([
                entry.student.name or "Unknown",
                entry.student.email,
                entry.assignments_completed,
                entry.assignments_total,
                entry.on_time_submissions,
                entry.late_submissions,
                entry.missing_assignments,
                f"{entry.average_grade:.1f}" if entry.average_grade else "N/A",
                entry.performance_category.upper()
            ])
        
        return output.getvalue()


report_service = ReportService()
