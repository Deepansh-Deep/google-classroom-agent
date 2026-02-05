"""
Q&A API Endpoints - RAG-based classroom Q&A.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CurrentUser, Permission, get_current_user, require_permission, check_course_access
from app.models.database import get_db
from app.models.schemas import QAResponse, QuestionRequest
from app.services.rag_service import rag_service
from app.utils.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post("", response_model=QAResponse)
@require_permission(Permission.USE_QA)
async def ask_question(
    request: QuestionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Ask a question about classroom content.
    
    Returns an answer with confidence score, sources, and explanation.
    """
    if request.course_id:
        await check_course_access(current_user, request.course_id, db)
    
    response = await rag_service.query(
        question=request.question,
        course_id=request.course_id,
    )
    
    logger.info(
        "Q&A query processed",
        user_id=str(current_user.id),
        confidence=response.confidence,
        sources_count=len(response.sources),
    )
    
    return response


@router.post("/index/{course_id}")
@require_permission(Permission.SYNC_COURSES)
async def index_course(
    course_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Index course content for Q&A (teachers only)."""
    await check_course_access(current_user, course_id, db, require_teacher=True)
    
    result = await rag_service.index_course_content(db, course_id)
    
    return {
        "message": "Course content indexed",
        "indexed": result,
    }
