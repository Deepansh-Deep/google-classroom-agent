"""
Embedding Tasks - Background Vector Generation

Jobs for creating and updating vector embeddings:
- generate_embeddings_for_course: Index course content for Q&A
"""

from uuid import UUID
from sqlalchemy import select

from app.models.database import async_session_factory, Course, Assignment, Announcement
from app.services.embedding_service import EmbeddingService
from app.integrations.vector_store import VectorStore
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def generate_embeddings_for_course(ctx: dict, course_id: str) -> dict:
    """
    Generate vector embeddings for all content in a course.
    
    Indexes:
    - Assignment titles and descriptions
    - Announcements
    - Any attached materials
    """
    logger.info("Generating embeddings", course_id=course_id)
    
    async with async_session_factory() as db:
        # Get course with assignments and announcements
        result = await db.execute(
            select(Course).where(Course.id == UUID(course_id))
        )
        course = result.scalar_one_or_none()
        
        if not course:
            return {"status": "skipped", "reason": "course_not_found"}
        
        embedding_service = EmbeddingService()
        vector_store = VectorStore()
        
        documents = []
        metadata_list = []
        ids = []
        
        # Index assignments
        assignments_result = await db.execute(
            select(Assignment).where(Assignment.course_id == course.id)
        )
        assignments = assignments_result.scalars().all()
        
        for assignment in assignments:
            content = f"Assignment: {assignment.title}"
            if assignment.description:
                content += f"\n\n{assignment.description}"
            if assignment.due_date:
                content += f"\n\nDue date: {assignment.due_date.strftime('%B %d, %Y at %I:%M %p')}"
            if assignment.max_points:
                content += f"\nPoints: {assignment.max_points}"
            
            documents.append(content)
            metadata_list.append({
                "type": "assignment",
                "title": assignment.title,
                "course_id": str(course.id),
                "course_name": course.name,
                "assignment_id": str(assignment.id),
                "due_date": assignment.due_date.isoformat() if assignment.due_date else None,
            })
            ids.append(f"assignment:{assignment.id}")
        
        # Index announcements
        announcements_result = await db.execute(
            select(Announcement).where(Announcement.course_id == course.id)
        )
        announcements = announcements_result.scalars().all()
        
        for announcement in announcements:
            content = f"Announcement: {announcement.text}"
            if announcement.created_at:
                content += f"\n\nPosted: {announcement.created_at.strftime('%B %d, %Y')}"
            
            documents.append(content)
            metadata_list.append({
                "type": "announcement",
                "title": f"Announcement from {course.name}",
                "course_id": str(course.id),
                "course_name": course.name,
                "posted_at": announcement.created_at.isoformat() if announcement.created_at else None,
            })
            ids.append(f"announcement:{announcement.id}")
        
        if not documents:
            logger.info("No content to embed", course_id=course_id)
            return {"status": "skipped", "reason": "no_content"}
        
        # Generate embeddings
        embeddings = await embedding_service.generate_embeddings(documents)
        
        # Store in vector database
        await vector_store.add_documents(
            documents=documents,
            metadata=metadata_list,
            ids=ids,
            embeddings=embeddings,
        )
        
        logger.info(
            "Embeddings generated",
            course_id=course_id,
            documents=len(documents)
        )
        
        return {
            "status": "success",
            "documents_indexed": len(documents),
            "assignments": len(assignments),
            "announcements": len(announcements),
        }
