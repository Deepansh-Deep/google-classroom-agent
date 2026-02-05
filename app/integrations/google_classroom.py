"""
Google Classroom API Integration

Production-ready client with pagination, rate limiting, and error handling.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import get_settings
from app.core.exceptions import GoogleAPIError, RateLimitError
from app.utils.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class GoogleClassroomClient:
    """
    Google Classroom API client with production-ready features.
    
    Features:
    - Automatic pagination handling
    - Exponential backoff for rate limits
    - Graceful error handling
    - Partial data recovery
    """
    
    def __init__(self, access_token: str, refresh_token: Optional[str] = None):
        self.credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
        )
        self._service = None
    
    @property
    def service(self):
        """Lazy initialization of Classroom service."""
        if self._service is None:
            self._service = build(
                "classroom",
                "v1",
                credentials=self.credentials,
                cache_discovery=False,
            )
        return self._service
    
    def _handle_api_error(self, error: HttpError, context: str) -> None:
        """Handle Google API errors with appropriate exceptions."""
        status = error.resp.status
        
        if status == 429:
            logger.warning("Rate limit exceeded", context=context)
            raise RateLimitError(retry_after=60)
        elif status == 401:
            logger.error("Authentication failed", context=context)
            raise GoogleAPIError("Authentication expired. Please re-authenticate.")
        elif status == 403:
            logger.error("Permission denied", context=context)
            raise GoogleAPIError("Permission denied. Check API scopes.")
        elif status == 404:
            logger.warning("Resource not found", context=context)
            raise GoogleAPIError(f"Resource not found: {context}")
        else:
            logger.error("API error", context=context, status=status, error=str(error))
            raise GoogleAPIError(f"Google API error: {str(error)}")
    
    @retry(
        retry=retry_if_exception_type(RateLimitError),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        stop=stop_after_attempt(5),
    )
    async def _paginated_request(
        self,
        request_func,
        items_key: str,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """
        Execute a paginated API request.
        
        Args:
            request_func: The API request method to call
            items_key: Key containing the items in the response
            **kwargs: Additional arguments for the request
        
        Returns:
            List of all items across all pages
        """
        all_items = []
        page_token = None
        
        while True:
            try:
                request = request_func(pageToken=page_token, **kwargs)
                response = await asyncio.to_thread(request.execute)
                
                items = response.get(items_key, [])
                all_items.extend(items)
                
                page_token = response.get("nextPageToken")
                if not page_token:
                    break
                    
            except HttpError as e:
                self._handle_api_error(e, f"paginated request for {items_key}")
        
        return all_items
    
    async def get_courses(self, states: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Fetch all courses the user has access to.
        
        Args:
            states: Filter by course states (ACTIVE, ARCHIVED, etc.)
        
        Returns:
            List of course objects
        """
        try:
            course_states = states or ["ACTIVE"]
            
            courses = await self._paginated_request(
                self.service.courses().list,
                "courses",
                courseStates=course_states,
                pageSize=100,
            )
            
            logger.info("Fetched courses", count=len(courses))
            return courses
            
        except HttpError as e:
            self._handle_api_error(e, "get_courses")
            return []
    
    async def get_course(self, course_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single course by ID."""
        try:
            request = self.service.courses().get(id=course_id)
            course = await asyncio.to_thread(request.execute)
            return course
        except HttpError as e:
            self._handle_api_error(e, f"get_course({course_id})")
            return None
    
    async def get_course_students(self, course_id: str) -> List[Dict[str, Any]]:
        """Fetch all students enrolled in a course."""
        try:
            students = await self._paginated_request(
                self.service.courses().students().list,
                "students",
                courseId=course_id,
                pageSize=100,
            )
            
            logger.info("Fetched students", course_id=course_id, count=len(students))
            return students
            
        except HttpError as e:
            self._handle_api_error(e, f"get_students({course_id})")
            return []
    
    async def get_course_teachers(self, course_id: str) -> List[Dict[str, Any]]:
        """Fetch all teachers for a course."""
        try:
            teachers = await self._paginated_request(
                self.service.courses().teachers().list,
                "teachers",
                courseId=course_id,
                pageSize=100,
            )
            
            return teachers
            
        except HttpError as e:
            self._handle_api_error(e, f"get_teachers({course_id})")
            return []
    
    async def get_assignments(
        self,
        course_id: str,
        states: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch all assignments (coursework) for a course.
        
        Args:
            course_id: The course ID
            states: Filter by states (PUBLISHED, DRAFT, etc.)
        
        Returns:
            List of assignment objects
        """
        try:
            kwargs = {"courseId": course_id, "pageSize": 100}
            if states:
                kwargs["courseWorkStates"] = states
            
            assignments = await self._paginated_request(
                self.service.courses().courseWork().list,
                "courseWork",
                **kwargs,
            )
            
            logger.info("Fetched assignments", course_id=course_id, count=len(assignments))
            return assignments
            
        except HttpError as e:
            self._handle_api_error(e, f"get_assignments({course_id})")
            return []
    
    async def get_submissions(
        self,
        course_id: str,
        assignment_id: str,
        states: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch all submissions for an assignment.
        
        Args:
            course_id: The course ID
            assignment_id: The assignment ID
            states: Filter by states (TURNED_IN, RETURNED, etc.)
        
        Returns:
            List of submission objects
        """
        try:
            kwargs = {
                "courseId": course_id,
                "courseWorkId": assignment_id,
                "pageSize": 100,
            }
            if states:
                kwargs["states"] = states
            
            submissions = await self._paginated_request(
                self.service.courses().courseWork().studentSubmissions().list,
                "studentSubmissions",
                **kwargs,
            )
            
            logger.info(
                "Fetched submissions",
                course_id=course_id,
                assignment_id=assignment_id,
                count=len(submissions),
            )
            return submissions
            
        except HttpError as e:
            self._handle_api_error(e, f"get_submissions({course_id}, {assignment_id})")
            return []
    
    async def get_all_course_submissions(
        self,
        course_id: str,
    ) -> List[Dict[str, Any]]:
        """Fetch all submissions for all assignments in a course."""
        assignments = await self.get_assignments(course_id)
        all_submissions = []
        
        for assignment in assignments:
            submissions = await self.get_submissions(
                course_id,
                assignment["id"],
            )
            # Add assignment reference to each submission
            for sub in submissions:
                sub["_assignment"] = assignment
            all_submissions.extend(submissions)
        
        return all_submissions
    
    async def get_announcements(
        self,
        course_id: str,
        states: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch all announcements for a course.
        
        Args:
            course_id: The course ID
            states: Filter by states (PUBLISHED, DRAFT, etc.)
        
        Returns:
            List of announcement objects
        """
        try:
            kwargs = {"courseId": course_id, "pageSize": 100}
            if states:
                kwargs["announcementStates"] = states
            
            announcements = await self._paginated_request(
                self.service.courses().announcements().list,
                "announcements",
                **kwargs,
            )
            
            logger.info("Fetched announcements", course_id=course_id, count=len(announcements))
            return announcements
            
        except HttpError as e:
            self._handle_api_error(e, f"get_announcements({course_id})")
            return []
    
    async def get_course_materials(self, course_id: str) -> List[Dict[str, Any]]:
        """Fetch all course materials."""
        try:
            materials = await self._paginated_request(
                self.service.courses().courseWorkMaterials().list,
                "courseWorkMaterial",
                courseId=course_id,
                pageSize=100,
            )
            
            return materials
            
        except HttpError as e:
            # Materials API might not be available
            logger.warning("Failed to fetch materials", error=str(e))
            return []
    
    async def sync_course_data(self, course_id: str) -> Dict[str, Any]:
        """
        Sync all data for a course.
        
        Returns a comprehensive data structure with all course data.
        """
        try:
            # Fetch all data concurrently where possible
            course_task = self.get_course(course_id)
            students_task = self.get_course_students(course_id)
            teachers_task = self.get_course_teachers(course_id)
            assignments_task = self.get_assignments(course_id)
            announcements_task = self.get_announcements(course_id)
            
            course, students, teachers, assignments, announcements = await asyncio.gather(
                course_task,
                students_task,
                teachers_task,
                assignments_task,
                announcements_task,
                return_exceptions=True,
            )
            
            # Handle any exceptions in the results
            errors = []
            if isinstance(course, Exception):
                errors.append(f"course: {str(course)}")
                course = None
            if isinstance(students, Exception):
                errors.append(f"students: {str(students)}")
                students = []
            if isinstance(teachers, Exception):
                errors.append(f"teachers: {str(teachers)}")
                teachers = []
            if isinstance(assignments, Exception):
                errors.append(f"assignments: {str(assignments)}")
                assignments = []
            if isinstance(announcements, Exception):
                errors.append(f"announcements: {str(announcements)}")
                announcements = []
            
            # Fetch submissions for each assignment
            all_submissions = []
            for assignment in assignments:
                try:
                    submissions = await self.get_submissions(course_id, assignment["id"])
                    for sub in submissions:
                        sub["_assignment_id"] = assignment["id"]
                    all_submissions.extend(submissions)
                except Exception as e:
                    errors.append(f"submissions({assignment['id']}): {str(e)}")
            
            return {
                "course": course,
                "students": students,
                "teachers": teachers,
                "assignments": assignments,
                "submissions": all_submissions,
                "announcements": announcements,
                "synced_at": datetime.utcnow().isoformat(),
                "errors": errors,
            }
            
        except Exception as e:
            logger.error("Failed to sync course data", course_id=course_id, error=str(e))
            raise GoogleAPIError(f"Failed to sync course: {str(e)}")


def parse_google_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    """Parse Google API datetime string to Python datetime."""
    if not dt_str:
        return None
    
    try:
        # Google uses RFC 3339 format
        if dt_str.endswith("Z"):
            dt_str = dt_str[:-1] + "+00:00"
        return datetime.fromisoformat(dt_str)
    except (ValueError, TypeError):
        return None


def parse_due_date(due_date: Optional[Dict], due_time: Optional[Dict] = None) -> Optional[datetime]:
    """Parse Google Classroom due date object to Python datetime."""
    if not due_date:
        return None
    
    try:
        year = due_date.get("year")
        month = due_date.get("month")
        day = due_date.get("day")
        
        if not all([year, month, day]):
            return None
        
        hour = minute = 0
        if due_time:
            hour = due_time.get("hours", 23)
            minute = due_time.get("minutes", 59)
        else:
            # Default to end of day if no time specified
            hour, minute = 23, 59
        
        return datetime(year, month, day, hour, minute, 0)
    except (ValueError, TypeError):
        return None
