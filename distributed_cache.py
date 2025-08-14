"""
🔄 Distributed Response Cache for MEFAPEX AI Assistant
Redis-based distributed cache with fallback to local memory cache
"""
import json
import time
import hashlib
import logging
import asyncio
from typing import Dict, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

from response_cache import SimpleResponseCache, CacheEntry

logger = logging.getLogger(__name__)

@dataclass
class DistributedCacheEntry:
    """
    Distributed cache entry with serialization support
    """
    response: str
    timestamp: float
    access_count: int
    last_accessed: float
    source: str
    node_id: str = "local"
    
    def is_expired(self, ttl: int) -> bool:
        """Check if entry is expired based on TTL"""
        return (time.time() - self.timestamp) > ttl
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'DistributedCacheEntry':
        """Create instance from dictionary"""
        return cls(**data)

class BaseCacheInterface(ABC):
    """Abstract base class for cache implementations"""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[DistributedCacheEntry]:
        pass
    
    @abstractmethod
    async def set(self, key: str, entry: DistributedCacheEntry, ttl: int = None):
        pass
    
    @abstractmethod
    async def delete(self, key: str):
        pass
    
    @abstractmethod
    async def clear(self):
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        pass

class RedisDistributedCache(BaseCacheInterface):
    """
    Redis-based distributed cache implementation
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379", 
                 key_prefix: str = "mefapex:cache:", node_id: str = "node1"):
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self.node_id = node_id
        self.redis_client = None
        self._stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'errors': 0
        }
        
    async def connect(self):
        """Initialize Redis connection"""
        if not REDIS_AVAILABLE:
            raise ImportError("redis package not available")
        
        try:
            self.redis_client = redis.from_url(
                self.redis_url, 
                encoding="utf-8", 
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            # Test connection
            await self.redis_client.ping()
            logger.info(f"✅ Redis connected: {self.redis_url}")
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            raise
    
    async def disconnect(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("🔌 Redis disconnected")
    
    def _make_key(self, key: str) -> str:
        """Create prefixed cache key"""
        return f"{self.key_prefix}{key}"
    
    async def get(self, key: str) -> Optional[DistributedCacheEntry]:
        """Get entry from Redis"""
        if not self.redis_client:
            return None
        
        try:
            redis_key = self._make_key(key)
            data = await self.redis_client.get(redis_key)
            
            if data is None:
                self._stats['misses'] += 1
                return None
            
            # Deserialize
            entry_dict = json.loads(data)
            entry = DistributedCacheEntry.from_dict(entry_dict)
            
            # Update access info
            entry.access_count += 1
            entry.last_accessed = time.time()
            
            # Update in Redis (fire and forget)
            asyncio.create_task(self.set(key, entry))
            
            self._stats['hits'] += 1
            return entry
            
        except Exception as e:
            logger.error(f"Redis get error for key {key}: {e}")
            self._stats['errors'] += 1
            return None
    
    async def set(self, key: str, entry: DistributedCacheEntry, ttl: int = None):
        """Set entry in Redis"""
        if not self.redis_client:
            return
        
        try:
            redis_key = self._make_key(key)
            entry.node_id = self.node_id
            data = json.dumps(entry.to_dict())
            
            if ttl:
                await self.redis_client.setex(redis_key, ttl, data)
            else:
                await self.redis_client.set(redis_key, data)
            
            self._stats['sets'] += 1
            
        except Exception as e:
            logger.error(f"Redis set error for key {key}: {e}")
            self._stats['errors'] += 1
    
    async def delete(self, key: str):
        """Delete entry from Redis"""
        if not self.redis_client:
            return
        
        try:
            redis_key = self._make_key(key)
            await self.redis_client.delete(redis_key)
            self._stats['deletes'] += 1
            
        except Exception as e:
            logger.error(f"Redis delete error for key {key}: {e}")
            self._stats['errors'] += 1
    
    async def clear(self):
        """Clear all cache entries"""
        if not self.redis_client:
            return
        
        try:
            pattern = f"{self.key_prefix}*"
            keys = await self.redis_client.keys(pattern)
            if keys:
                await self.redis_client.delete(*keys)
            logger.info(f"🗑️ Cleared {len(keys)} Redis cache entries")
            
        except Exception as e:
            logger.error(f"Redis clear error: {e}")
            self._stats['errors'] += 1
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get Redis cache statistics"""
        try:
            info = await self.redis_client.info("memory") if self.redis_client else {}
            
            return {
                'type': 'redis',
                'node_id': self.node_id,
                'connected': self.redis_client is not None,
                'memory_used_mb': round(info.get('used_memory', 0) / (1024 * 1024), 2),
                'memory_peak_mb': round(info.get('used_memory_peak', 0) / (1024 * 1024), 2),
                **self._stats
            }
        except Exception as e:
            logger.error(f"Redis stats error: {e}")
            return {'type': 'redis', 'error': str(e), **self._stats}

class HybridDistributedCache:
    """
    Hybrid cache implementation with Redis (L1) and local memory (L2) fallback
    Features:
    - Redis for distributed caching across multiple instances
    - Local memory cache as fallback when Redis is unavailable
    - Automatic failover and recovery
    - Cache warming and synchronization
    """
    
    def __init__(self, 
                 redis_url: str = "redis://localhost:6379",
                 local_max_size: int = 500,
                 local_ttl: int = 1800,  # 30 minutes for local cache
                 redis_ttl: int = 3600,  # 1 hour for Redis cache
                 node_id: str = "node1"):
        """
        Initialize hybrid cache
        
        Args:
            redis_url: Redis connection URL
            local_max_size: Maximum entries in local cache
            local_ttl: TTL for local cache (shorter than Redis)
            redis_ttl: TTL for Redis cache
            node_id: Unique identifier for this node
        """
        self.redis_ttl = redis_ttl
        self.local_ttl = local_ttl
        self.node_id = node_id
        
        # Initialize local cache as fallback
        self.local_cache = SimpleResponseCache(max_size=local_max_size, ttl=local_ttl)
        
        # Initialize Redis cache
        self.redis_cache = None
        self.redis_available = False
        
        if REDIS_AVAILABLE:
            self.redis_cache = RedisDistributedCache(redis_url, node_id=node_id)
        
        logger.info(f"🔄 HybridDistributedCache initialized: node_id={node_id}")
    
    async def initialize(self):
        """Initialize Redis connection"""
        if self.redis_cache:
            try:
                await self.redis_cache.connect()
                self.redis_available = True
                logger.info("✅ Distributed cache: Redis enabled")
            except Exception as e:
                logger.warning(f"⚠️ Redis unavailable, using local cache only: {e}")
                self.redis_available = False
        else:
            logger.warning("⚠️ Redis not available, using local cache only")
    
    async def shutdown(self):
        """Cleanup resources"""
        if self.redis_cache:
            await self.redis_cache.disconnect()
    
    def _get_cache_key(self, message: str, context: str = "") -> str:
        """Generate cache key from message and context"""
        normalized_message = message.strip().lower()
        normalized_context = context.strip().lower() if context else ""
        combined = f"{normalized_message}:{normalized_context}"
        return hashlib.md5(combined.encode('utf-8')).hexdigest()
    
    async def get(self, message: str, context: str = "") -> Optional[Tuple[str, str]]:
        """
        Retrieve cached response with multi-level caching
        
        Strategy:
        1. Try local cache first (fastest)
        2. Try Redis if local miss
        3. Warm local cache if Redis hit
        """
        cache_key = self._get_cache_key(message, context)
        
        # Try local cache first
        local_result = self.local_cache.get(message, context)
        if local_result:
            logger.debug(f"🎯 Local cache hit: {cache_key[:8]}...")
            return local_result
        
        # Try Redis if available
        if self.redis_available and self.redis_cache:
            try:
                redis_entry = await self.redis_cache.get(cache_key)
                if redis_entry and not redis_entry.is_expired(self.redis_ttl):
                    # Warm local cache
                    self.local_cache.set(message, redis_entry.response, context, redis_entry.source)
                    logger.debug(f"🌐 Redis cache hit, warmed local: {cache_key[:8]}...")
                    return (redis_entry.response, redis_entry.source)
                    
            except Exception as e:
                logger.error(f"Redis get error: {e}")
                self.redis_available = False  # Mark as unavailable for this request
        
        return None
    
    async def set(self, message: str, response: str, context: str = "", source: str = "cached"):
        """
        Store response in both local and Redis cache
        """
        cache_key = self._get_cache_key(message, context)
        
        # Always store in local cache
        self.local_cache.set(message, response, context, source)
        
        # Store in Redis if available
        if self.redis_available and self.redis_cache:
            try:
                entry = DistributedCacheEntry(
                    response=response,
                    timestamp=time.time(),
                    access_count=1,
                    last_accessed=time.time(),
                    source=source,
                    node_id=self.node_id
                )
                await self.redis_cache.set(cache_key, entry, self.redis_ttl)
                logger.debug(f"💾 Cached in both local and Redis: {cache_key[:8]}...")
                
            except Exception as e:
                logger.error(f"Redis set error: {e}")
                self.redis_available = False
    
    async def clear(self):
        """Clear both local and Redis cache"""
        self.local_cache.clear()
        
        if self.redis_available and self.redis_cache:
            try:
                await self.redis_cache.clear()
            except Exception as e:
                logger.error(f"Redis clear error: {e}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        local_stats = self.local_cache.get_stats()
        
        stats = {
            'type': 'hybrid',
            'node_id': self.node_id,
            'local': local_stats,
            'redis_available': self.redis_available
        }
        
        if self.redis_available and self.redis_cache:
            try:
                redis_stats = await self.redis_cache.get_stats()
                stats['redis'] = redis_stats
            except Exception as e:
                stats['redis'] = {'error': str(e)}
        
        return stats
    
    async def health_check(self) -> Dict[str, bool]:
        """Check health of cache layers"""
        health = {
            'local_cache': True,  # Local cache is always available
            'redis_cache': False
        }
        
        if self.redis_cache:
            try:
                await self.redis_cache.redis_client.ping()
                health['redis_cache'] = True
                self.redis_available = True
            except Exception:
                health['redis_cache'] = False
                self.redis_available = False
        
        return health

# Factory function to create appropriate cache instance
def create_distributed_cache(config=None) -> Union[HybridDistributedCache, SimpleResponseCache]:
    """
    Factory function to create appropriate cache instance based on configuration
    """
    if not config:
        from config import config as app_config
        config = app_config
    
    # Check if Redis is configured and available
    redis_host = getattr(config, 'REDIS_HOST', None)
    redis_port = getattr(config, 'REDIS_PORT', 6379)
    
    if redis_host and REDIS_AVAILABLE:
        redis_url = f"redis://{redis_host}:{redis_port}"
        return HybridDistributedCache(
            redis_url=redis_url,
            local_max_size=getattr(config, 'CACHE_LOCAL_SIZE', 500),
            local_ttl=getattr(config, 'CACHE_LOCAL_TTL', 1800),
            redis_ttl=getattr(config, 'CACHE_REDIS_TTL', 3600),
            node_id=getattr(config, 'NODE_ID', 'node1')
        )
    else:
        logger.warning("Redis not configured or unavailable, using local cache only")
        return SimpleResponseCache(
            max_size=getattr(config, 'CACHE_SIZE', 1000),
            ttl=getattr(config, 'CACHE_TTL', 3600)
        )
