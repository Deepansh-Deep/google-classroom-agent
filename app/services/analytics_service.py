"""
Performance Analytics Service - Rule-Based Student Assessment

Provides explainable, deterministic performance scoring.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Assignment, Submission, User, PerformanceScore, Enrollment
from app.models.schemas import PerformanceFactors, PerformanceExplanation, PerformanceScoreResponse
from app.utils.logging import get_logger

logger = get_logger(__name__)


class PerformanceAnalyticsService:
    """
    Rule-based performance analysis with full explainability.
    
    Factors (weighted):
    - Submission timeliness (30%): on-time vs late submissions
    - Consistency (25%): regular submission pattern
    - Completion rate (30%): submitted vs total assignments
    - Grade performance (15%): average grades when available
    
    Categories:
    - GOOD: score >= 80
    - MEDIUM: 50 <= score < 80
    - AT_RISK: score < 50
    """
    
    WEIGHTS = {"timeliness": 0.30, "consistency": 0.25, "completion": 0.30, "grade": 0.15}
    
    async def calculate_student_performance(
        self, db: AsyncSession, student_id: UUID, course_id: UUID
    ) -> PerformanceScoreResponse:
        """Calculate performance score for a student in a course."""
        
        # Get all assignments for the course
        assignments = (await db.execute(
            select(Assignment).where(Assignment.course_id == course_id, Assignment.state == "PUBLISHED")
        )).scalars().all()
        
        if not assignments:
            return self._empty_score(student_id, course_id)
        
        # Get student submissions
        assignment_ids = [a.id for a in assignments]
        submissions = (await db.execute(
            select(Submission).where(
                Submission.student_id == student_id,
                Submission.assignment_id.in_(assignment_ids)
            )
        )).scalars().all()
        
        # Calculate factors
        timeliness = self._calc_timeliness(submissions)
        consistency = self._calc_consistency(submissions, len(assignments))
        completion = self._calc_completion(submissions, len(assignments))
        grade_factor = self._calc_grade_factor(submissions, assignments)
        
        # Calculate weighted score
        score = (timeliness * self.WEIGHTS["timeliness"] + 
                 consistency * self.WEIGHTS["consistency"] + 
                 completion * self.WEIGHTS["completion"])
        
        if grade_factor is not None:
            score += grade_factor * self.WEIGHTS["grade"]
        else:
            # Redistribute grade weight
            score = score / (1 - self.WEIGHTS["grade"]) * 1.0
        
        score = min(100, max(0, score))
        category = "good" if score >= 80 else ("medium" if score >= 50 else "at_risk")
        
        # Build explanation
        explanation = self._build_explanation(timeliness, consistency, completion, grade_factor, category)
        
        # Store score
        await self._save_score(db, student_id, course_id, score, category, 
                              timeliness, consistency, completion, grade_factor, 
                              explanation, len(assignments))
        
        return PerformanceScoreResponse(
            student_id=student_id, course_id=course_id, score=score, category=category,
            factors=PerformanceFactors(timeliness=timeliness, consistency=consistency, 
                                       completion=completion, grade=grade_factor),
            explanation=explanation, calculated_at=datetime.utcnow(), 
            assignments_analyzed=len(assignments)
        )
    
    def _calc_timeliness(self, submissions: List[Submission]) -> float:
        """Calculate timeliness factor: % of on-time submissions."""
        turned_in = [s for s in submissions if s.state in ["TURNED_IN", "RETURNED"]]
        if not turned_in:
            return 0.0
        on_time = sum(1 for s in turned_in if not s.late)
        return (on_time / len(turned_in)) * 100
    
    def _calc_consistency(self, submissions: List[Submission], total: int) -> float:
        """Calculate consistency: regular submission pattern."""
        if total <= 1:
            return 100.0 if submissions else 0.0
        
        turned_in = [s for s in submissions if s.submitted_at and s.state in ["TURNED_IN", "RETURNED"]]
        if len(turned_in) < 2:
            return 50.0
        
        # Check for gaps in submission pattern
        dates = sorted([s.submitted_at for s in turned_in])
        gaps = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
        
        if not gaps:
            return 50.0
        
        avg_gap = sum(gaps) / len(gaps)
        variance = sum((g - avg_gap) ** 2 for g in gaps) / len(gaps)
        
        # Lower variance = more consistent
        consistency = max(0, 100 - (variance ** 0.5) * 5)
        return min(100, consistency)
    
    def _calc_completion(self, submissions: List[Submission], total: int) -> float:
        """Calculate completion rate."""
        if total == 0:
            return 0.0
        completed = sum(1 for s in submissions if s.state in ["TURNED_IN", "RETURNED"])
        return (completed / total) * 100
    
    def _calc_grade_factor(self, submissions: List[Submission], assignments: List[Assignment]) -> Optional[float]:
        """Calculate grade factor from graded submissions."""
        graded = [(s, next((a for a in assignments if a.id == s.assignment_id), None)) 
                  for s in submissions if s.grade is not None]
        
        if not graded:
            return None
        
        total_points = sum(a.max_points for s, a in graded if a and a.max_points)
        earned_points = sum(s.grade for s, a in graded if a and a.max_points)
        
        if total_points == 0:
            return None
        
        return (earned_points / total_points) * 100
    
    def _build_explanation(self, timeliness: float, consistency: float, 
                          completion: float, grade: Optional[float], category: str) -> PerformanceExplanation:
        """Build human-readable explanation in plain English (no jargon)."""
        
        # Plain language factor descriptions
        factors = {}
        
        # Timeliness in plain terms
        if timeliness >= 90:
            factors["Submission Timing"] = "You're submitting almost all your work on time - excellent!"
        elif timeliness >= 70:
            factors["Submission Timing"] = f"You submit {timeliness:.0f}% of assignments on time. Room to improve."
        elif timeliness >= 50:
            factors["Submission Timing"] = f"About half your submissions are late. Try setting reminders before deadlines."
        else:
            factors["Submission Timing"] = "Most of your work is submitted late. This is hurting your performance."
        
        # Consistency in plain terms
        if consistency >= 80:
            factors["Work Pattern"] = "You submit work regularly throughout the term - great habit!"
        elif consistency >= 60:
            factors["Work Pattern"] = "Your submission pattern is fairly regular."
        else:
            factors["Work Pattern"] = "Your submissions come in bursts. A regular schedule would help."
        
        # Completion in plain terms
        if completion >= 90:
            factors["Assignment Completion"] = "You've completed almost all your assignments."
        elif completion >= 70:
            factors["Assignment Completion"] = f"You've completed {completion:.0f}% of assignments. A few are missing."
        elif completion >= 50:
            factors["Assignment Completion"] = f"Only {completion:.0f}% of assignments submitted. You're missing quite a few."
        else:
            factors["Assignment Completion"] = "Many assignments are missing. This needs urgent attention."
        
        # Grade in plain terms
        if grade is not None:
            if grade >= 85:
                factors["Grade Performance"] = "Your grades are strong - keep it up!"
            elif grade >= 70:
                factors["Grade Performance"] = f"Your average grade is around {grade:.0f}%. Solid work."
            elif grade >= 50:
                factors["Grade Performance"] = f"Your average is around {grade:.0f}%. There's room to improve."
            else:
                factors["Grade Performance"] = "Your grades need attention. Consider asking for help."
        
        # Build recommendations based on weakest areas
        recommendations = []
        
        # Prioritize recommendations by impact
        if completion < 70:
            recommendations.append("Make completing all assignments your top priority")
        if timeliness < 60:
            recommendations.append("Set calendar reminders 2 days before each deadline")
        if consistency < 50:
            recommendations.append("Try working on coursework a little bit every day")
        if grade is not None and grade < 60:
            recommendations.append("Visit office hours or ask questions when you're stuck")
        
        # Add encouraging recommendation if doing well
        if category == "good" and not recommendations:
            recommendations.append("Keep up the excellent work!")
        elif not recommendations:
            recommendations.append("You're on the right track - stay consistent")
        
        # Plain language summary
        if category == "good":
            summary = "You're doing well in this class. Your work habits are solid."
        elif category == "medium":
            summary = "You're keeping up, but there are a few areas where you could do better."
        else:
            summary = "Your performance needs attention. The recommendations below can help."
        
        return PerformanceExplanation(summary=summary, factors=factors, recommendations=recommendations)
    
    async def _save_score(self, db: AsyncSession, student_id: UUID, course_id: UUID,
                         score: float, category: str, timeliness: float, consistency: float,
                         completion: float, grade: Optional[float], explanation: PerformanceExplanation,
                         assignments_count: int) -> None:
        """Save or update performance score."""
        existing = (await db.execute(
            select(PerformanceScore).where(
                PerformanceScore.student_id == student_id,
                PerformanceScore.course_id == course_id
            )
        )).scalar_one_or_none()
        
        if existing:
            existing.score = score
            existing.category = category
            existing.timeliness_factor = timeliness
            existing.consistency_factor = consistency
            existing.completion_factor = completion
            existing.grade_factor = grade
            existing.explanation = explanation.model_dump()
            existing.calculated_at = datetime.utcnow()
            existing.assignments_analyzed = assignments_count
        else:
            db.add(PerformanceScore(
                student_id=student_id, course_id=course_id, score=score, category=category,
                timeliness_factor=timeliness, consistency_factor=consistency,
                completion_factor=completion, grade_factor=grade,
                explanation=explanation.model_dump(), assignments_analyzed=assignments_count
            ))
        
        await db.commit()
    
    def _empty_score(self, student_id: UUID, course_id: UUID) -> PerformanceScoreResponse:
        """Return empty score when no data available."""
        return PerformanceScoreResponse(
            student_id=student_id, course_id=course_id, score=0, category="at_risk",
            factors=PerformanceFactors(timeliness=0, consistency=0, completion=0, grade=None),
            explanation=PerformanceExplanation(
                summary="No assignment data available",
                factors={"Data": "No assignments found"},
                recommendations=["Wait for course assignments"]
            ),
            calculated_at=datetime.utcnow(), assignments_analyzed=0
        )
    
    async def get_class_overview(self, db: AsyncSession, course_id: UUID) -> Dict:
        """Get class-wide performance overview."""
        enrollments = (await db.execute(
            select(Enrollment).where(Enrollment.course_id == course_id, Enrollment.role == "student")
        )).scalars().all()
        
        scores = []
        for enrollment in enrollments:
            score = await self.calculate_student_performance(db, enrollment.user_id, course_id)
            scores.append(score)
        
        if not scores:
            return {"total": 0, "good": 0, "medium": 0, "at_risk": 0, "average": 0}
        
        return {
            "total": len(scores),
            "good": sum(1 for s in scores if s.category == "good"),
            "medium": sum(1 for s in scores if s.category == "medium"),
            "at_risk": sum(1 for s in scores if s.category == "at_risk"),
            "average": sum(s.score for s in scores) / len(scores)
        }


analytics_service = PerformanceAnalyticsService()
