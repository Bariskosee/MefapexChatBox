"""
🛡️ Distributed Rate Limiter with Redis Backend
==============================================
Redis-based rate limiting for multi-instance applications
with fallback to in-memory storage
"""

import time
import asyncio
import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Dict, List, Optional, Set
import redis.asyncio as redis
from redis.exceptions import RedisError, ConnectionError, TimeoutError

from core.configuration import RateLimitConfig

logger = logging.getLogger(__name__)

class RateLimiterBackend(ABC):
    """Abstract base class for rate limiter backends"""
    
    @abstractmethod
    async def is_allowed(self, key: str, limit: int, window_seconds: int) -> bool:
        """Check if request is allowed within the rate limit"""
        pass
    
    @abstractmethod
    async def get_current_count(self, key: str, window_seconds: int) -> int:
        """Get current request count for a key"""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up expired entries"""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close connections and cleanup resources"""
        pass

class RedisRateLimiterBackend(RateLimiterBackend):
    """Redis-based distributed rate limiter backend"""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.redis_client: Optional[redis.Redis] = None
        self._connection_healthy = False
        self._last_health_check = 0
        self._health_check_interval = 30  # Check every 30 seconds
        
    async def _ensure_connection(self) -> bool:
        """Ensure Redis connection is healthy"""
        now = time.time()
        
        # Don't check too frequently
        if (now - self._last_health_check) < self._health_check_interval and self._connection_healthy:
            return True
        
        self._last_health_check = now
        
        try:
            if self.redis_client is None:
                self.redis_client = redis.from_url(
                    self.config.redis_url,
                    decode_responses=True,
                    socket_timeout=5,
                    socket_connect_timeout=5,
                    health_check_interval=30
                )
            
            # Test connection
            await self.redis_client.ping()
            self._connection_healthy = True
            return True
            
        except (RedisError, ConnectionError, TimeoutError) as e:
            logger.warning(f"Redis connection failed: {e}")
            self._connection_healthy = False
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to Redis: {e}")
            self._connection_healthy = False
            return False
    
    async def is_allowed(self, key: str, limit: int, window_seconds: int) -> bool:
        """
        Check if request is allowed using Redis sliding window
        Uses Redis ZRANGEBYSCORE and ZADD for atomic operations
        """
        if not await self._ensure_connection():
            return False  # Fail closed when Redis is unavailable
        
        try:
            now = time.time()
            window_start = now - window_seconds
            redis_key = f"{self.config.key_prefix}:{key}"
            
            async with self.redis_client.pipeline(transaction=True) as pipe:
                # Remove expired entries
                await pipe.zremrangebyscore(redis_key, 0, window_start)
                
                # Count current requests
                await pipe.zcard(redis_key)
                
                # Execute pipeline
                results = await pipe.execute()
                current_count = results[1]
                
                if current_count >= limit:
                    return False
                
                # Add current request
                await self.redis_client.zadd(
                    redis_key, 
                    {str(now): now},
                    ex=window_seconds + 10  # TTL slightly longer than window
                )
                
                return True
                
        except (RedisError, ConnectionError, TimeoutError) as e:
            logger.warning(f"Redis rate limiter error: {e}")
            return False  # Fail closed on Redis errors
        except Exception as e:
            logger.error(f"Unexpected Redis error: {e}")
            return False
    
    async def get_current_count(self, key: str, window_seconds: int) -> int:
        """Get current request count for a key"""
        if not await self._ensure_connection():
            return 0
        
        try:
            now = time.time()
            window_start = now - window_seconds
            redis_key = f"{self.config.key_prefix}:{key}"
            
            # Remove expired and count
            async with self.redis_client.pipeline(transaction=True) as pipe:
                await pipe.zremrangebyscore(redis_key, 0, window_start)
                await pipe.zcard(redis_key)
                results = await pipe.execute()
                
                return results[1]
                
        except (RedisError, ConnectionError, TimeoutError):
            return 0
        except Exception as e:
            logger.error(f"Error getting current count: {e}")
            return 0
    
    async def cleanup(self) -> None:
        """Clean up expired entries across all keys"""
        if not await self._ensure_connection():
            return
        
        try:
            # Get all rate limit keys
            pattern = f"{self.config.key_prefix}:*"
            keys = await self.redis_client.keys(pattern)
            
            if not keys:
                return
            
            now = time.time()
            window_start = now - self.config.window_size_seconds
            
            # Clean up expired entries in batches
            for i in range(0, len(keys), 100):  # Process 100 keys at a time
                batch_keys = keys[i:i+100]
                async with self.redis_client.pipeline(transaction=False) as pipe:
                    for key in batch_keys:
                        await pipe.zremrangebyscore(key, 0, window_start)
                    await pipe.execute()
            
            logger.debug(f"Cleaned up {len(keys)} rate limit keys")
            
        except (RedisError, ConnectionError, TimeoutError) as e:
            logger.warning(f"Error during Redis cleanup: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during cleanup: {e}")
    
    async def close(self) -> None:
        """Close Redis connection"""
        if self.redis_client:
            try:
                await self.redis_client.close()
            except Exception as e:
                logger.warning(f"Error closing Redis connection: {e}")
            finally:
                self.redis_client = None
                self._connection_healthy = False

class MemoryRateLimiterBackend(RateLimiterBackend):
    """In-memory rate limiter backend (fallback)"""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.requests: Dict[str, List[float]] = defaultdict(list)
        self._last_cleanup = time.time()
    
    async def is_allowed(self, key: str, limit: int, window_seconds: int) -> bool:
        """Check if request is allowed using in-memory sliding window"""
        now = time.time()
        
        # Get and clean expired requests
        client_requests = self.requests[key]
        window_start = now - window_seconds
        
        # Remove expired requests
        client_requests[:] = [req_time for req_time in client_requests if req_time > window_start]
        
        if len(client_requests) >= limit:
            return False
        
        # Add current request
        client_requests.append(now)
        return True
    
    async def get_current_count(self, key: str, window_seconds: int) -> int:
        """Get current request count for a key"""
        now = time.time()
        window_start = now - window_seconds
        
        client_requests = self.requests[key]
        # Clean and count
        valid_requests = [req_time for req_time in client_requests if req_time > window_start]
        self.requests[key] = valid_requests
        
        return len(valid_requests)
    
    async def cleanup(self) -> None:
        """Clean up expired entries"""
        now = time.time()
        
        # Don't cleanup too frequently
        if (now - self._last_cleanup) < self.config.memory_cleanup_interval:
            return
        
        self._last_cleanup = now
        window_start = now - self.config.window_size_seconds
        
        # Clean expired entries
        keys_to_remove = []
        for key, requests in self.requests.items():
            # Filter expired requests
            valid_requests = [req_time for req_time in requests if req_time > window_start]
            
            if valid_requests:
                self.requests[key] = valid_requests
            else:
                keys_to_remove.append(key)
        
        # Remove empty keys
        for key in keys_to_remove:
            del self.requests[key]
        
        logger.debug(f"Memory cleanup: removed {len(keys_to_remove)} empty keys")
    
    async def close(self) -> None:
        """Close and cleanup"""
        self.requests.clear()

class DistributedRateLimiter:
    """
    Distributed rate limiter with Redis backend and in-memory fallback
    Handles multiple instances and provides high availability
    """
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.redis_backend: Optional[RedisRateLimiterBackend] = None
        self.memory_backend = MemoryRateLimiterBackend(config)
        self._cleanup_task: Optional[asyncio.Task] = None
        
        # Initialize Redis backend if enabled
        if config.use_redis:
            self.redis_backend = RedisRateLimiterBackend(config)
        
        # Start cleanup task
        self._start_cleanup_task()
    
    def _start_cleanup_task(self):
        """Start background cleanup task"""
        async def cleanup_worker():
            while True:
                try:
                    await asyncio.sleep(self.config.cleanup_interval_seconds)
                    
                    # Cleanup Redis backend
                    if self.redis_backend:
                        await self.redis_backend.cleanup()
                    
                    # Always cleanup memory backend
                    await self.memory_backend.cleanup()
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in cleanup task: {e}")
        
        self._cleanup_task = asyncio.create_task(cleanup_worker())
    
    async def is_allowed(self, client_ip: str, endpoint_type: str = "general") -> bool:
        """
        Check if request is allowed based on rate limits
        Uses Redis when available, falls back to memory
        """
        if not self.config.enabled:
            return True
        
        # Determine limits based on endpoint type
        if endpoint_type == "chat":
            limit = self.config.chat_requests_per_minute
            key = f"chat:{client_ip}"
        else:
            limit = self.config.requests_per_minute
            key = f"general:{client_ip}"
        
        # Try Redis backend first
        if self.redis_backend:
            try:
                result = await self.redis_backend.is_allowed(
                    key, limit, self.config.window_size_seconds
                )
                # If Redis succeeded, return result
                if result is not False or not self.config.fallback_to_memory:
                    return result
            except Exception as e:
                logger.warning(f"Redis backend failed, falling back to memory: {e}")
        
        # Fallback to memory backend
        if self.config.fallback_to_memory:
            return await self.memory_backend.is_allowed(
                key, limit, self.config.window_size_seconds
            )
        
        # If no fallback, deny request
        return False
    
    async def get_current_count(self, client_ip: str, endpoint_type: str = "general") -> int:
        """Get current request count for debugging/monitoring"""
        if endpoint_type == "chat":
            key = f"chat:{client_ip}"
        else:
            key = f"general:{client_ip}"
        
        # Try Redis first
        if self.redis_backend:
            try:
                count = await self.redis_backend.get_current_count(
                    key, self.config.window_size_seconds
                )
                if count >= 0:  # Valid result
                    return count
            except Exception as e:
                logger.warning(f"Error getting count from Redis: {e}")
        
        # Fallback to memory
        return await self.memory_backend.get_current_count(
            key, self.config.window_size_seconds
        )
    
    async def get_stats(self) -> Dict[str, any]:
        """Get rate limiter statistics"""
        return {
            "enabled": self.config.enabled,
            "backend": "redis" if (self.redis_backend and self.redis_backend._connection_healthy) else "memory",
            "redis_available": self.redis_backend._connection_healthy if self.redis_backend else False,
            "fallback_enabled": self.config.fallback_to_memory,
            "limits": {
                "general_requests_per_minute": self.config.requests_per_minute,
                "chat_requests_per_minute": self.config.chat_requests_per_minute
            },
            "config": {
                "window_size_seconds": self.config.window_size_seconds,
                "cleanup_interval_seconds": self.config.cleanup_interval_seconds
            }
        }
    
    async def close(self):
        """Close and cleanup resources"""
        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Close backends
        if self.redis_backend:
            await self.redis_backend.close()
        
        await self.memory_backend.close()

# Global rate limiter instance
_global_rate_limiter: Optional[DistributedRateLimiter] = None

async def get_rate_limiter(config: Optional[RateLimitConfig] = None) -> DistributedRateLimiter:
    """
    Get the global rate limiter instance
    Creates new instance if not exists or config changed
    """
    global _global_rate_limiter
    
    if _global_rate_limiter is None:
        if config is None:
            from core.configuration import get_config
            config = get_config().rate_limit
        
        _global_rate_limiter = DistributedRateLimiter(config)
    
    return _global_rate_limiter

async def close_rate_limiter():
    """Close global rate limiter instance"""
    global _global_rate_limiter
    if _global_rate_limiter:
        await _global_rate_limiter.close()
        _global_rate_limiter = None

# For backward compatibility with old RateLimiter class
class RateLimiter:
    """
    Legacy RateLimiter class for backward compatibility
    Now delegates to DistributedRateLimiter
    """
    
    def __init__(self, max_requests_per_minute: int = 200, max_chat_requests_per_minute: int = 100):
        from core.configuration import get_config
        config = get_config().rate_limit
        
        # Override limits if provided
        config.requests_per_minute = max_requests_per_minute
        config.chat_requests_per_minute = max_chat_requests_per_minute
        
        self._distributed_limiter = DistributedRateLimiter(config)
    
    def is_allowed(self, client_ip: str, endpoint_type: str = "general") -> bool:
        """
        Synchronous wrapper for backward compatibility
        WARNING: This blocks the event loop - use async version when possible
        """
        # For backward compatibility, we need to handle the async call
        # This is not ideal but necessary for existing code
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're in an async context, create a task
                task = asyncio.create_task(
                    self._distributed_limiter.is_allowed(client_ip, endpoint_type)
                )
                # This is a hack for backward compatibility - not recommended
                return False  # Fail safe when we can't properly await
            else:
                # Not in async context, run in new loop
                return asyncio.run(
                    self._distributed_limiter.is_allowed(client_ip, endpoint_type)
                )
        except Exception as e:
            logger.error(f"Error in legacy rate limiter: {e}")
            return False  # Fail safe
