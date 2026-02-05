"""
Embedding Service - Text Processing and Vector Generation

Handles text cleaning, chunking, and embedding generation for RAG.
"""

import asyncio
import re
from typing import Any, Dict, List, Optional, Tuple

from sentence_transformers import SentenceTransformer

from app.config import get_settings
from app.core.exceptions import EmbeddingError
from app.utils.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

# Global model instance (lazy loaded)
_model: Optional[SentenceTransformer] = None


def get_embedding_model() -> SentenceTransformer:
    """Get or initialize the embedding model."""
    global _model
    if _model is None:
        logger.info("Loading embedding model", model=settings.embedding_model)
        _model = SentenceTransformer(settings.embedding_model)
        logger.info("Embedding model loaded")
    return _model


class TextProcessor:
    """
    Text processing utilities for cleaning and normalizing content.
    """
    
    # Patterns to clean
    URL_PATTERN = re.compile(r'https?://\S+|www\.\S+')
    EMAIL_PATTERN = re.compile(r'\S+@\S+\.\S+')
    HTML_PATTERN = re.compile(r'<[^>]+>')
    WHITESPACE_PATTERN = re.compile(r'\s+')
    SPECIAL_CHARS_PATTERN = re.compile(r'[^\w\s.,!?;:\'"()-]')
    
    @classmethod
    def clean_text(cls, text: str) -> str:
        """
        Clean and normalize text for embedding.
        
        Args:
            text: Raw text to clean
        
        Returns:
            Cleaned and normalized text
        """
        if not text:
            return ""
        
        # Remove HTML tags
        text = cls.HTML_PATTERN.sub(' ', text)
        
        # Replace URLs with placeholder
        text = cls.URL_PATTERN.sub('[URL]', text)
        
        # Replace emails with placeholder
        text = cls.EMAIL_PATTERN.sub('[EMAIL]', text)
        
        # Remove special characters (keep basic punctuation)
        text = cls.SPECIAL_CHARS_PATTERN.sub(' ', text)
        
        # Normalize whitespace
        text = cls.WHITESPACE_PATTERN.sub(' ', text)
        
        # Strip and lowercase
        text = text.strip()
        
        return text
    
    @classmethod
    def extract_keywords(cls, text: str, max_keywords: int = 10) -> List[str]:
        """Extract key terms from text."""
        if not text:
            return []
        
        # Simple keyword extraction based on word frequency
        words = text.lower().split()
        
        # Filter short words and common stopwords
        stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to',
            'for', 'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were',
            'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
            'will', 'would', 'could', 'should', 'may', 'might', 'must',
            'shall', 'can', 'this', 'that', 'these', 'those', 'it', 'its',
        }
        
        filtered_words = [
            w for w in words 
            if len(w) > 3 and w not in stopwords and w.isalpha()
        ]
        
        # Count frequency
        word_freq = {}
        for word in filtered_words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # Sort by frequency and return top keywords
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, _ in sorted_words[:max_keywords]]


class TextChunker:
    """
    Intelligent text chunking for optimal embedding context.
    """
    
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        min_chunk_size: int = 100,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
    
    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into overlapping chunks.
        
        Args:
            text: Text to chunk
        
        Returns:
            List of text chunks
        """
        if not text or len(text) < self.min_chunk_size:
            return [text] if text else []
        
        chunks = []
        sentences = self._split_into_sentences(text)
        
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            if current_length + sentence_length > self.chunk_size and current_chunk:
                # Save current chunk
                chunk_text = ' '.join(current_chunk)
                chunks.append(chunk_text)
                
                # Start new chunk with overlap
                overlap_text = ' '.join(current_chunk[-2:]) if len(current_chunk) > 1 else ''
                current_chunk = [overlap_text] if overlap_text else []
                current_length = len(overlap_text)
            
            current_chunk.append(sentence)
            current_length += sentence_length + 1
        
        # Add final chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            if len(chunk_text) >= self.min_chunk_size:
                chunks.append(chunk_text)
            elif chunks:
                # Merge with previous chunk if too small
                chunks[-1] += ' ' + chunk_text
        
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitting on period, question mark, exclamation
        pattern = r'(?<=[.!?])\s+'
        sentences = re.split(pattern, text)
        return [s.strip() for s in sentences if s.strip()]


class EmbeddingService:
    """
    Service for generating and managing text embeddings.
    """
    
    def __init__(self):
        self.processor = TextProcessor()
        self.chunker = TextChunker()
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
        
        Returns:
            List of floats representing the embedding
        """
        try:
            cleaned_text = self.processor.clean_text(text)
            if not cleaned_text:
                raise EmbeddingError("Empty text after cleaning")
            
            model = get_embedding_model()
            
            # Run in thread pool to avoid blocking
            embedding = await asyncio.to_thread(
                model.encode,
                cleaned_text,
                convert_to_numpy=True,
            )
            
            return embedding.tolist()
            
        except Exception as e:
            logger.error("Embedding generation failed", error=str(e))
            raise EmbeddingError(f"Failed to generate embedding: {str(e)}")
    
    async def generate_embeddings(
        self,
        texts: List[str],
        batch_size: int = 32,
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing
        
        Returns:
            List of embeddings
        """
        try:
            # Clean all texts
            cleaned_texts = [self.processor.clean_text(t) for t in texts]
            
            # Filter empty texts
            valid_texts = [(i, t) for i, t in enumerate(cleaned_texts) if t]
            
            if not valid_texts:
                return [[] for _ in texts]
            
            model = get_embedding_model()
            
            # Generate embeddings in batches
            all_embeddings = []
            for i in range(0, len(valid_texts), batch_size):
                batch = [t for _, t in valid_texts[i:i + batch_size]]
                
                embeddings = await asyncio.to_thread(
                    model.encode,
                    batch,
                    convert_to_numpy=True,
                    show_progress_bar=False,
                )
                
                all_embeddings.extend(embeddings.tolist())
            
            # Reconstruct results with empty embeddings for filtered texts
            results = [[] for _ in texts]
            for (orig_idx, _), embedding in zip(valid_texts, all_embeddings):
                results[orig_idx] = embedding
            
            return results
            
        except Exception as e:
            logger.error("Batch embedding generation failed", error=str(e))
            raise EmbeddingError(f"Failed to generate embeddings: {str(e)}")
    
    async def process_document(
        self,
        text: str,
        metadata: Dict[str, Any],
    ) -> List[Tuple[str, List[float], Dict[str, Any]]]:
        """
        Process a document: clean, chunk, and embed.
        
        Args:
            text: Document text
            metadata: Base metadata for the document
        
        Returns:
            List of (chunk_text, embedding, chunk_metadata) tuples
        """
        # Clean text
        cleaned_text = self.processor.clean_text(text)
        if not cleaned_text:
            return []
        
        # Chunk text
        chunks = self.chunker.chunk_text(cleaned_text)
        
        if not chunks:
            return []
        
        # Generate embeddings
        embeddings = await self.generate_embeddings(chunks)
        
        # Extract keywords for each chunk
        results = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            if not embedding:
                continue
            
            chunk_metadata = {
                **metadata,
                "chunk_index": i,
                "chunk_count": len(chunks),
                "keywords": self.processor.extract_keywords(chunk),
            }
            
            results.append((chunk, embedding, chunk_metadata))
        
        return results


# Singleton instance
embedding_service = EmbeddingService()
