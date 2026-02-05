"""
Vector Store Integration - ChromaDB

Handles embedding storage and semantic search for classroom content.
"""

import asyncio
from typing import Any, Dict, List, Optional
from uuid import UUID

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import get_settings
from app.core.exceptions import EmbeddingError
from app.utils.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

# Global client instance
_chroma_client: Optional[chromadb.HttpClient] = None
_collection: Optional[chromadb.Collection] = None


async def init_vector_store() -> None:
    """Initialize ChromaDB connection."""
    global _chroma_client, _collection
    
    try:
        _chroma_client = chromadb.HttpClient(
            host=settings.chroma_host,
            port=settings.chroma_port,
            settings=ChromaSettings(
                anonymized_telemetry=False,
            ),
        )
        
        # Get or create collection
        _collection = _chroma_client.get_or_create_collection(
            name=settings.chroma_collection,
            metadata={"hnsw:space": "cosine"},
        )
        
        logger.info(
            "Vector store initialized",
            host=settings.chroma_host,
            collection=settings.chroma_collection,
        )
    except Exception as e:
        logger.error("Failed to initialize vector store", error=str(e))
        # Don't raise - allow app to start without vector store
        _chroma_client = None
        _collection = None


async def check_vector_store_connection() -> bool:
    """Check if vector store is accessible."""
    if _chroma_client is None:
        return False
    
    try:
        await asyncio.to_thread(_chroma_client.heartbeat)
        return True
    except Exception:
        return False


def get_collection() -> Optional[chromadb.Collection]:
    """Get the ChromaDB collection."""
    return _collection


class VectorStore:
    """
    Vector store wrapper for classroom content.
    
    Provides methods for adding, querying, and managing embeddings.
    """
    
    def __init__(self):
        self.collection = _collection
    
    async def add_documents(
        self,
        documents: List[str],
        metadata: List[Dict[str, Any]],
        ids: List[str],
        embeddings: Optional[List[List[float]]] = None,
    ) -> None:
        """
        Add documents to the vector store.
        
        Args:
            documents: List of document texts
            metadata: List of metadata dicts for each document
            ids: Unique IDs for each document
            embeddings: Pre-computed embeddings (optional, will be computed if not provided)
        """
        if not self.collection:
            logger.warning("Vector store not initialized, skipping add")
            return
        
        try:
            if embeddings:
                await asyncio.to_thread(
                    self.collection.add,
                    documents=documents,
                    metadatas=metadata,
                    ids=ids,
                    embeddings=embeddings,
                )
            else:
                # Let ChromaDB compute embeddings using default model
                await asyncio.to_thread(
                    self.collection.add,
                    documents=documents,
                    metadatas=metadata,
                    ids=ids,
                )
            
            logger.info("Added documents to vector store", count=len(documents))
            
        except Exception as e:
            logger.error("Failed to add documents", error=str(e))
            raise EmbeddingError(f"Failed to store embeddings: {str(e)}")
    
    async def query(
        self,
        query_text: str,
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
        query_embedding: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """
        Query the vector store for similar documents.
        
        Args:
            query_text: The query text
            n_results: Number of results to return
            where: Filter conditions
            query_embedding: Pre-computed query embedding (optional)
        
        Returns:
            Dict with documents, distances, and metadata
        """
        if not self.collection:
            logger.warning("Vector store not initialized")
            return {"documents": [], "distances": [], "metadatas": [], "ids": []}
        
        try:
            kwargs = {"n_results": n_results}
            
            if query_embedding:
                kwargs["query_embeddings"] = [query_embedding]
            else:
                kwargs["query_texts"] = [query_text]
            
            if where:
                kwargs["where"] = where
            
            results = await asyncio.to_thread(
                self.collection.query,
                **kwargs,
            )
            
            # Flatten results (ChromaDB returns nested lists)
            return {
                "documents": results.get("documents", [[]])[0],
                "distances": results.get("distances", [[]])[0],
                "metadatas": results.get("metadatas", [[]])[0],
                "ids": results.get("ids", [[]])[0],
            }
            
        except Exception as e:
            logger.error("Vector query failed", error=str(e))
            return {"documents": [], "distances": [], "metadatas": [], "ids": []}
    
    async def delete_by_course(self, course_id: str) -> None:
        """Delete all documents for a course."""
        if not self.collection:
            return
        
        try:
            await asyncio.to_thread(
                self.collection.delete,
                where={"course_id": course_id},
            )
            logger.info("Deleted documents for course", course_id=course_id)
        except Exception as e:
            logger.error("Failed to delete documents", error=str(e))
    
    async def delete_by_ids(self, ids: List[str]) -> None:
        """Delete documents by their IDs."""
        if not self.collection or not ids:
            return
        
        try:
            await asyncio.to_thread(
                self.collection.delete,
                ids=ids,
            )
            logger.info("Deleted documents by IDs", count=len(ids))
        except Exception as e:
            logger.error("Failed to delete documents", error=str(e))
    
    async def get_document_count(self, course_id: Optional[str] = None) -> int:
        """Get the number of documents in the store."""
        if not self.collection:
            return 0
        
        try:
            count = await asyncio.to_thread(self.collection.count)
            return count
        except Exception:
            return 0
    
    async def update_document(
        self,
        doc_id: str,
        document: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None,
    ) -> None:
        """Update an existing document."""
        if not self.collection:
            return
        
        try:
            update_kwargs = {"ids": [doc_id]}
            if document:
                update_kwargs["documents"] = [document]
            if metadata:
                update_kwargs["metadatas"] = [metadata]
            if embedding:
                update_kwargs["embeddings"] = [embedding]
            
            await asyncio.to_thread(
                self.collection.update,
                **update_kwargs,
            )
        except Exception as e:
            logger.error("Failed to update document", error=str(e))


# Singleton instance
vector_store = VectorStore()
