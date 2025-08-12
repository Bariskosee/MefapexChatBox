"""
🗄️ Cache Service Interface
===========================
Abstract base class for caching operations following Single Responsibility Principle.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, List
from datetime import timedelta


class ICacheService(ABC):
    """
    Interface for caching operations.
    Single Responsibility: Data caching and retrieval.
    """
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, expire: Optional[timedelta] = None) -> bool:
        """Set value in cache with optional expiration"""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        pass
    
    @abstractmethod
    async def clear(self) -> bool:
        """Clear all cache entries"""
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        pass


class ISessionCacheService(ABC):
    """
    Session-specific caching service.
    Single Responsibility: Session data caching.
    """
    
    @abstractmethod
    async def cache_session(self, session_id: str, session_data: Dict[str, Any], expire: Optional[timedelta] = None) -> bool:
        """Cache session data"""
        pass
    
    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get cached session data"""
        pass
    
    @abstractmethod
    async def invalidate_session(self, session_id: str) -> bool:
        """Invalidate session cache"""
        pass
    
    @abstractmethod
    async def invalidate_user_sessions(self, user_id: str) -> bool:
        """Invalidate all sessions for a user"""
        pass


class IResponseCacheService(ABC):
    """
    Response caching service.
    Single Responsibility: Response caching for performance optimization.
    """
    
    @abstractmethod
    async def cache_response(self, query: str, response: str, source: str, expire: Optional[timedelta] = None) -> bool:
        """Cache AI response"""
        pass
    
    @abstractmethod
    async def get_cached_response(self, query: str) -> Optional[Dict[str, Any]]:
        """Get cached response"""
        pass
    
    @abstractmethod
    async def invalidate_responses_by_source(self, source: str) -> bool:
        """Invalidate responses from specific source"""
        pass


class IRateLimitCacheService(ABC):
    """
    Rate limiting cache service.
    Single Responsibility: Rate limiting data storage.
    """
    
    @abstractmethod
    async def increment_request_count(self, client_id: str, window: timedelta) -> int:
        """Increment request count for client in time window"""
        pass
    
    @abstractmethod
    async def get_request_count(self, client_id: str, window: timedelta) -> int:
        """Get request count for client in time window"""
        pass
    
    @abstractmethod
    async def is_rate_limited(self, client_id: str, limit: int, window: timedelta) -> bool:
        """Check if client is rate limited"""
        pass
    
    @abstractmethod
    async def reset_client_limits(self, client_id: str) -> bool:
        """Reset rate limits for client"""
        pass
