"""
Cache Module - Redis Caching Layer

Provides typed cache operations with TTL management.
Prevents Google Classroom API rate limits.
"""

import json
from datetime import timedelta
from typing import Any, Optional, TypeVar, Callable
import hashlib

import redis.asyncio as redis

from app.config import get_settings
from app.utils.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

T = TypeVar("T")

# Global Redis connection
_redis_client: Optional[redis.Redis] = None


async def init_cache() -> None:
    """Initialize Redis connection."""
    global _redis_client
    try:
        _redis_client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        await _redis_client.ping()
        logger.info("Redis cache connected")
    except Exception as e:
        logger.warning("Redis not available, caching disabled", error=str(e))
        _redis_client = None


async def close_cache() -> None:
    """Close Redis connection."""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None


class CacheClient:
    """
    Typed cache client with convenience methods.
    
    TTL defaults:
    - Courses: 5 minutes
    - Assignments: 5 minutes
    - Submissions: 2 minutes
    - Session: 30 minutes
    """
    
    # Default TTLs in seconds
    TTL_COURSES = 300  # 5 min
    TTL_ASSIGNMENTS = 300  # 5 min
    TTL_SUBMISSIONS = 120  # 2 min
    TTL_SESSION = 1800  # 30 min
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not _redis_client:
            return None
        try:
            value = await _redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.warning("Cache get failed", key=key, error=str(e))
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None
    ) -> bool:
        """Set value in cache with optional TTL."""
        if not _redis_client:
            return False
        try:
            await _redis_client.set(
                key, 
                json.dumps(value, default=str),
                ex=ttl,
            )
            return True
        except Exception as e:
            logger.warning("Cache set failed", key=key, error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not _redis_client:
            return False
        try:
            await _redis_client.delete(key)
            return True
        except Exception as e:
            logger.warning("Cache delete failed", key=key, error=str(e))
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern."""
        if not _redis_client:
            return 0
        try:
            keys = await _redis_client.keys(pattern)
            if keys:
                return await _redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning("Cache delete pattern failed", pattern=pattern, error=str(e))
            return 0
    
    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Any],
        ttl: Optional[int] = None,
    ) -> Optional[Any]:
        """
        Get from cache, or call factory and cache result.
        
        This enables cache-aside pattern.
        """
        cached = await self.get(key)
        if cached is not None:
            return cached
        
        value = await factory() if callable(factory) else factory
        if value is not None:
            await self.set(key, value, ttl)
        return value
    
    # Convenience methods for specific data types
    
    async def get_user_courses(self, user_id: str) -> Optional[list]:
        """Get cached courses for user."""
        return await self.get(f"user:{user_id}:courses")
    
    async def set_user_courses(self, user_id: str, courses: list) -> bool:
        """Cache user's courses."""
        return await self.set(f"user:{user_id}:courses", courses, self.TTL_COURSES)
    
    async def get_course_assignments(self, course_id: str) -> Optional[list]:
        """Get cached assignments for course."""
        return await self.get(f"course:{course_id}:assignments")
    
    async def set_course_assignments(self, course_id: str, assignments: list) -> bool:
        """Cache course assignments."""
        return await self.set(f"course:{course_id}:assignments", assignments, self.TTL_ASSIGNMENTS)
    
    async def invalidate_user_data(self, user_id: str) -> int:
        """Invalidate all cached data for a user."""
        return await self.delete_pattern(f"user:{user_id}:*")


# Global cache instance
cache = CacheClient()
