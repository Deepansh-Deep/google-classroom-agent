"""
RAG Service - Retrieval-Augmented Generation for Q&A

STRICT NO-HALLUCINATION POLICY:
- Answers ONLY from indexed classroom content
- Minimum confidence threshold enforced
- Every answer includes source excerpts
- Clear "I don't know" when below threshold
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.integrations.vector_store import vector_store
from app.models.database import Assignment, Announcement, Course
from app.models.schemas import QAResponse, Source
from app.services.embedding_service import embedding_service
from app.utils.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class RAGService:
    """
    RAG service with strict no-hallucination guardrails.
    
    Guardrails:
    1. MINIMUM_CONFIDENCE: Below 0.5, refuse to answer
    2. Every answer cites sources with excerpts
    3. Confidence score shown to user
    4. Clear explanation of where answer came from
    """
    
    # Confidence thresholds
    MINIMUM_CONFIDENCE = 0.5  # Below this, refuse to answer
    HIGH_CONFIDENCE = 0.75    # User can trust this answer
    MIN_RELEVANCE = 0.35      # Minimum similarity for a source to count
    
    def __init__(self):
        self.embedding_service = embedding_service
    
    async def index_course_content(self, db: AsyncSession, course_id: UUID) -> Dict[str, int]:
        """Index all content for a course."""
        indexed = {"assignments": 0, "announcements": 0}
        
        course_query = select(Course).where(Course.id == course_id)
        course = (await db.execute(course_query)).scalar_one_or_none()
        if not course:
            return indexed
        
        # Index assignments
        assignments = (await db.execute(
            select(Assignment).where(Assignment.course_id == course_id, Assignment.embedded == False)
        )).scalars().all()
        
        for a in assignments:
            if a.description:
                content = f"Assignment: {a.title}\n\n{a.description}"
                if a.due_date:
                    content += f"\n\nDue date: {a.due_date.strftime('%B %d, %Y at %I:%M %p')}"
                if a.max_points:
                    content += f"\nPoints: {a.max_points}"
                    
                chunks = await self.embedding_service.process_document(content, {
                    "type": "assignment", 
                    "course_id": str(course_id),
                    "course_name": course.name,
                    "assignment_id": str(a.id), 
                    "title": a.title,
                    "due_date": a.due_date.isoformat() if a.due_date else None,
                    "posted_date": a.created_at.isoformat() if a.created_at else None,
                })
                if chunks:
                    await vector_store.add_documents(
                        documents=[c[0] for c in chunks],
                        embeddings=[c[1] for c in chunks],
                        metadata=[c[2] for c in chunks],
                        ids=[f"assignment_{a.id}_{i}" for i in range(len(chunks))],
                    )
                    a.embedded = True
                    a.embedded_at = datetime.utcnow()
                    indexed["assignments"] += 1
        
        # Index announcements
        announcements = (await db.execute(
            select(Announcement).where(Announcement.course_id == course_id, Announcement.embedded == False)
        )).scalars().all()
        
        for ann in announcements:
            if ann.text:
                chunks = await self.embedding_service.process_document(ann.text, {
                    "type": "announcement", 
                    "course_id": str(course_id),
                    "course_name": course.name,
                    "announcement_id": str(ann.id),
                    "posted_date": ann.created_at.isoformat() if ann.created_at else None,
                })
                if chunks:
                    await vector_store.add_documents(
                        documents=[c[0] for c in chunks],
                        embeddings=[c[1] for c in chunks],
                        metadata=[c[2] for c in chunks],
                        ids=[f"announcement_{ann.id}_{i}" for i in range(len(chunks))],
                    )
                    ann.embedded = True
                    ann.embedded_at = datetime.utcnow()
                    indexed["announcements"] += 1
        
        await db.commit()
        return indexed
    
    async def query(self, question: str, course_id: Optional[UUID] = None, n_results: int = 5) -> QAResponse:
        """
        Answer a question using RAG with strict guardrails.
        
        Returns:
        - Answer derived ONLY from indexed content
        - Confidence score (0-1)
        - Source excerpts with context
        - Clear explanation
        """
        query_embedding = await self.embedding_service.generate_embedding(question)
        
        where_filter = {"course_id": str(course_id)} if course_id else None
        results = await vector_store.query(question, n_results, where_filter, query_embedding)
        
        # No results at all
        if not results["documents"]:
            return self._no_answer_response(question, "no_indexed_content")
        
        # Calculate similarities (ChromaDB returns distances, lower is better)
        similarities = [max(0, 1 - d) for d in results.get("distances", [])]
        
        # Filter to only relevant sources (above minimum threshold)
        relevant = []
        for doc, meta, sim in zip(results["documents"], results["metadatas"], similarities):
            if sim >= self.MIN_RELEVANCE:
                relevant.append((doc, meta, sim))
        
        # Not enough relevant content
        if not relevant:
            return self._no_answer_response(question, "low_relevance")
        
        # Calculate weighted confidence
        # Higher weight to top results
        weights = [1 / (i + 1) for i in range(len(relevant))]
        sims = [s for _, _, s in relevant]
        confidence = sum(w * s for w, s in zip(weights, sims)) / sum(weights)
        
        # GUARDRAIL: Below minimum confidence, refuse to answer
        if confidence < self.MINIMUM_CONFIDENCE:
            return self._low_confidence_response(question, confidence, relevant)
        
        # Build answer from top sources
        answer = self._build_answer(question, relevant)
        
        # Format sources with excerpts
        sources = self._format_sources(relevant)
        
        # Build explanation
        explanation = self._build_explanation(relevant, confidence)
        
        logger.info(
            "RAG query answered",
            question=question[:50],
            confidence=f"{confidence:.2f}",
            sources=len(sources),
        )
        
        return QAResponse(
            question=question,
            answer=answer,
            confidence=confidence,
            sources=sources,
            explanation=explanation,
            answered_at=datetime.utcnow(),
        )
    
    def _build_answer(self, question: str, relevant: List) -> str:
        """Build answer from relevant sources."""
        top_doc, top_meta, top_sim = relevant[0]
        
        # Extract the most relevant part
        answer_text = top_doc[:500] if len(top_doc) > 500 else top_doc
        
        # Format based on source type
        source_type = top_meta.get("type", "content")
        source_title = top_meta.get("title", "classroom content")
        
        if source_type == "assignment":
            prefix = f"According to the assignment '{source_title}':\n\n"
        elif source_type == "announcement":
            prefix = f"From a class announcement:\n\n"
        else:
            prefix = f"Based on classroom content:\n\n"
        
        return prefix + answer_text
    
    def _format_sources(self, relevant: List) -> List[Source]:
        """Format sources with excerpts and dates."""
        sources = []
        seen_titles = set()
        
        for doc, meta, sim in relevant:
            title = meta.get("title", "Content")
            if title in seen_titles:
                continue
            seen_titles.add(title)
            
            # Clean excerpt (first 200 chars, ending at word boundary)
            excerpt = doc[:200]
            if len(doc) > 200:
                last_space = excerpt.rfind(" ")
                if last_space > 100:
                    excerpt = excerpt[:last_space] + "..."
                else:
                    excerpt += "..."
            
            # Format posted date if available
            posted = meta.get("posted_date") or meta.get("due_date")
            if posted:
                try:
                    date_obj = datetime.fromisoformat(posted)
                    posted = date_obj.strftime("%B %d, %Y")
                except:
                    pass
            
            sources.append(Source(
                type=meta.get("type", "content"),
                title=title,
                excerpt=excerpt,
                relevance_score=sim,
                posted=posted,
                course_name=meta.get("course_name"),
            ))
        
        return sources[:5]  # Max 5 sources
    
    def _build_explanation(self, relevant: List, confidence: float) -> str:
        """Build human-readable explanation."""
        count = len(relevant)
        
        if confidence >= self.HIGH_CONFIDENCE:
            confidence_text = "high confidence"
        elif confidence >= self.MINIMUM_CONFIDENCE:
            confidence_text = "moderate confidence"
        else:
            confidence_text = "low confidence"
        
        # List source types
        source_types = {}
        for _, meta, _ in relevant:
            t = meta.get("type", "content")
            source_types[t] = source_types.get(t, 0) + 1
        
        type_list = []
        if source_types.get("assignment"):
            type_list.append(f"{source_types['assignment']} assignment(s)")
        if source_types.get("announcement"):
            type_list.append(f"{source_types['announcement']} announcement(s)")
        
        sources_text = " and ".join(type_list) if type_list else f"{count} source(s)"
        
        return f"This answer is based on {sources_text} from your classroom ({confidence_text}, {confidence:.0%} match)."
    
    def _no_answer_response(self, question: str, reason: str) -> QAResponse:
        """Generate clear 'I don't know' response."""
        if reason == "no_indexed_content":
            message = ("I don't have any indexed classroom content to answer this question. "
                      "Try syncing your courses first to index assignments and announcements.")
        else:
            message = ("I couldn't find relevant information to answer this question in your "
                      "classroom materials. This question might be outside the scope of your "
                      "indexed course content.")
        
        return QAResponse(
            question=question,
            answer=message,
            confidence=0.0,
            sources=[],
            explanation="No matching content was found in indexed classroom materials.",
            answered_at=datetime.utcnow(),
        )
    
    def _low_confidence_response(self, question: str, confidence: float, relevant: List) -> QAResponse:
        """When we found something but confidence is too low."""
        message = (f"I found some related content, but I'm not confident enough to give "
                  f"a definitive answer ({confidence:.0%} confidence). Here's what I found, "
                  f"but please verify with your instructor:")
        
        if relevant:
            top_doc = relevant[0][0][:300]
            message += f"\n\n---\n\n{top_doc}..."
        
        return QAResponse(
            question=question,
            answer=message,
            confidence=confidence,
            sources=self._format_sources(relevant[:2]),
            explanation=f"Confidence ({confidence:.0%}) is below the minimum threshold of 50%. "
                       f"The answer may not be accurate.",
            answered_at=datetime.utcnow(),
        )


# Global instance
rag_service = RAGService()
