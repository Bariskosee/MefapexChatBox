"""
🔄 Distributed Response Cache for MEFAPEX AI Assistant
Redis-based distributed cache with fallback to local memory cache
Enhanced with configurable TTL, size limits, and eviction policies
"""
import json
import time
import hashlib
import logging
import asyncio
import gc
import psutil
from typing import Dict, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

from response_cache import AdvancedResponseCache, CacheEntry, EvictionPolicy

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
    
    def get_memory_size(self) -> int:
        """Estimate memory usage in bytes"""
        return len(self.response.encode('utf-8')) + len(self.source.encode('utf-8')) + \
               len(self.node_id.encode('utf-8')) + 200  # Base overhead

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
    
    @abstractmethod
    async def get_size(self) -> int:
        pass
    
    @abstractmethod
    async def enforce_limits(self):
        pass

class RedisDistributedCache(BaseCacheInterface):
    """
    Redis-based distributed cache implementation with size and memory limits
    """
    
    def __init__(self, 
                 redis_url: str = "redis://localhost:6379", 
                 key_prefix: str = "mefapex:cache:", 
                 node_id: str = "node1",
                 max_entries: int = 10000,
                 max_memory_mb: int = 100,
                 eviction_policy: str = "lru"):
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self.node_id = node_id
        self.max_entries = max_entries
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.eviction_policy = eviction_policy
        self.redis_client = None
        self._stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'evictions': 0,
            'errors': 0,
            'memory_evictions': 0
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
    
    def _make_meta_key(self, key: str) -> str:
        """Create metadata key for tracking"""
        return f"{self.key_prefix}meta:{key}"
    
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
            asyncio.create_task(self._update_entry_metadata(key, entry))
            
            self._stats['hits'] += 1
            return entry
            
        except Exception as e:
            logger.error(f"Redis get error for key {key}: {e}")
            self._stats['errors'] += 1
            return None
    
    async def set(self, key: str, entry: DistributedCacheEntry, ttl: int = None):
        """Set entry in Redis with size limit enforcement"""
        if not self.redis_client:
            return
        
        try:
            # Check size limits before setting
            await self.enforce_limits()
            
            redis_key = self._make_key(key)
            entry.node_id = self.node_id
            data = json.dumps(entry.to_dict())
            
            if ttl:
                await self.redis_client.setex(redis_key, ttl, data)
            else:
                await self.redis_client.set(redis_key, data)
            
            # Store metadata for eviction tracking
            await self._store_entry_metadata(key, entry)
            
            self._stats['sets'] += 1
            
        except Exception as e:
            logger.error(f"Redis set error for key {key}: {e}")
            self._stats['errors'] += 1
    
    async def _store_entry_metadata(self, key: str, entry: DistributedCacheEntry):
        """Store entry metadata for eviction policies"""
        try:
            meta_key = self._make_meta_key(key)
            metadata = {
                'timestamp': entry.timestamp,
                'last_accessed': entry.last_accessed,
                'access_count': entry.access_count,
                'memory_size': entry.get_memory_size()
            }
            await self.redis_client.hset(f"{self.key_prefix}metadata", key, json.dumps(metadata))
        except Exception as e:
            logger.error(f"Error storing metadata for key {key}: {e}")
    
    async def _update_entry_metadata(self, key: str, entry: DistributedCacheEntry):
        """Update entry metadata for access tracking"""
        try:
            metadata = {
                'timestamp': entry.timestamp,
                'last_accessed': entry.last_accessed,
                'access_count': entry.access_count,
                'memory_size': entry.get_memory_size()
            }
            await self.redis_client.hset(f"{self.key_prefix}metadata", key, json.dumps(metadata))
        except Exception as e:
            logger.error(f"Error updating metadata for key {key}: {e}")
    
    async def delete(self, key: str):
        """Delete entry from Redis"""
        if not self.redis_client:
            return
        
        try:
            redis_key = self._make_key(key)
            await self.redis_client.delete(redis_key)
            # Remove metadata
            await self.redis_client.hdel(f"{self.key_prefix}metadata", key)
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
    
    async def get_size(self) -> int:
        """Get current cache size"""
        try:
            pattern = f"{self.key_prefix}*"
            keys = await self.redis_client.keys(pattern)
            return len([k for k in keys if not k.endswith(':metadata')])
        except Exception:
            return 0
    
    async def enforce_limits(self):
        """Enforce size and memory limits"""
        if not self.redis_client:
            return
        
        try:
            current_size = await self.get_size()
            
            # Check size limit
            if current_size >= self.max_entries:
                await self._evict_entries_by_policy()
            
            # Check memory limit (basic implementation)
            memory_info = await self.redis_client.info("memory")
            used_memory = memory_info.get('used_memory', 0)
            
            if used_memory > self.max_memory_bytes:
                await self._evict_by_memory()
        
        except Exception as e:
            logger.error(f"Error enforcing limits: {e}")
    
    async def _evict_entries_by_policy(self):
        """Evict entries based on configured policy"""
        try:
            # Get all metadata
            metadata_hash = f"{self.key_prefix}metadata"
            all_metadata = await self.redis_client.hgetall(metadata_hash)
            
            if not all_metadata:
                return
            
            # Parse metadata and sort by eviction policy
            entries_with_meta = []
            for key, meta_json in all_metadata.items():
                try:
                    meta = json.loads(meta_json)
                    entries_with_meta.append((key, meta))
                except json.JSONDecodeError:
                    continue
            
            # Sort based on eviction policy
            if self.eviction_policy.lower() == "lru":
                entries_with_meta.sort(key=lambda x: x[1].get('last_accessed', 0))
            elif self.eviction_policy.lower() == "lfu":
                entries_with_meta.sort(key=lambda x: x[1].get('access_count', 0))
            elif self.eviction_policy.lower() == "fifo":
                entries_with_meta.sort(key=lambda x: x[1].get('timestamp', 0))
            else:  # Random or default
                import random
                random.shuffle(entries_with_meta)
            
            # Evict 10% of entries or at least 1
            evict_count = max(1, len(entries_with_meta) // 10)
            
            for i in range(min(evict_count, len(entries_with_meta))):
                key_to_evict = entries_with_meta[i][0]
                await self.delete(key_to_evict)
                self._stats['evictions'] += 1
            
            logger.info(f"🗑️ Evicted {evict_count} entries using {self.eviction_policy} policy")
        
        except Exception as e:
            logger.error(f"Error in policy-based eviction: {e}")
    
    async def _evict_by_memory(self):
        """Evict entries to reduce memory usage"""
        try:
            # Simple memory-based eviction - remove 20% of entries
            all_keys = await self.redis_client.keys(f"{self.key_prefix}*")
            cache_keys = [k for k in all_keys if not k.endswith(':metadata') and not k.endswith('metadata')]
            
            evict_count = max(1, len(cache_keys) // 5)  # Remove 20%
            
            for i in range(min(evict_count, len(cache_keys))):
                key_to_remove = cache_keys[i].replace(self.key_prefix, "")
                await self.delete(key_to_remove)
                self._stats['memory_evictions'] += 1
            
            logger.info(f"🧹 Memory eviction completed: removed {evict_count} entries")
        
        except Exception as e:
            logger.error(f"Error in memory eviction: {e}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get Redis cache statistics"""
        try:
            info = await self.redis_client.info("memory") if self.redis_client else {}
            current_size = await self.get_size()
            
            return {
                'type': 'redis',
                'node_id': self.node_id,
                'connected': self.redis_client is not None,
                'size': current_size,
                'max_entries': self.max_entries,
                'memory_used_mb': round(info.get('used_memory', 0) / (1024 * 1024), 2),
                'memory_peak_mb': round(info.get('used_memory_peak', 0) / (1024 * 1024), 2),
                'memory_limit_mb': round(self.max_memory_bytes / (1024 * 1024), 2),
                'eviction_policy': self.eviction_policy,
                **self._stats
            }
        except Exception as e:
            logger.error(f"Redis stats error: {e}")
            return {'type': 'redis', 'error': str(e), **self._stats}

class EnhancedHybridDistributedCache:
    """
    Enhanced Hybrid cache implementation with Redis (L1) and local memory (L2) fallback
    Features:
    - Configurable size and TTL limits
    - Multiple eviction policies
    - Memory usage monitoring
    - Auto-scaling capabilities
    - Comprehensive statistics
    """
    
    def __init__(self, 
                 redis_url: str = "redis://localhost:6379",
                 local_max_size: int = 500,
                 local_ttl: int = 1800,
                 redis_ttl: int = 3600,
                 redis_max_entries: int = 10000,
                 max_memory_mb: int = 100,
                 eviction_policy: str = "lru",
                 node_id: str = "node1",
                 auto_scale: bool = True):
        """
        Initialize enhanced hybrid cache
        """
        self.redis_ttl = redis_ttl
        self.local_ttl = local_ttl
        self.node_id = node_id
        self.auto_scale = auto_scale
        
        # Initialize local cache with advanced features
        self.local_cache = AdvancedResponseCache(
            max_size=local_max_size, 
            ttl=local_ttl,
            eviction_policy=eviction_policy,
            max_memory_mb=max_memory_mb // 2,  # Reserve half memory for local cache
            auto_scale=auto_scale
        )
        
        # Initialize Redis cache
        self.redis_cache = None
        self.redis_available = False
        
        if REDIS_AVAILABLE:
            self.redis_cache = RedisDistributedCache(
                redis_url, 
                node_id=node_id,
                max_entries=redis_max_entries,
                max_memory_mb=max_memory_mb // 2,  # Reserve half memory for Redis cache
                eviction_policy=eviction_policy
            )
        
        logger.info(f"🔄 EnhancedHybridDistributedCache initialized: node_id={node_id}, "
                   f"local_size={local_max_size}, redis_max={redis_max_entries}")
    
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
        """
        cache_key = self._get_cache_key(message, context)
        
        # Try local cache first (fastest)
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
                self.redis_available = False
        
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
            'type': 'enhanced_hybrid',
            'node_id': self.node_id,
            'local': local_stats,
            'redis_available': self.redis_available,
            'auto_scale_enabled': self.auto_scale
        }
        
        if self.redis_available and self.redis_cache:
            try:
                redis_stats = await self.redis_cache.get_stats()
                stats['redis'] = redis_stats
            except Exception as e:
                stats['redis'] = {'error': str(e)}
        
        return stats
    
    async def optimize(self):
        """Optimize both cache layers"""
        # Optimize local cache
        self.local_cache.optimize()
        
        # Optimize Redis cache if available
        if self.redis_available and self.redis_cache:
            try:
                await self.redis_cache.enforce_limits()
            except Exception as e:
                logger.error(f"Redis optimization error: {e}")
    
    async def health_check(self) -> Dict[str, bool]:
        """Check health of cache layers"""
        health = {
            'local_cache': True,
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

# Maintain backward compatibility
class HybridDistributedCache(EnhancedHybridDistributedCache):
    """Backward compatibility wrapper"""
    
    def __init__(self, 
                 redis_url: str = "redis://localhost:6379",
                 local_max_size: int = 500,
                 local_ttl: int = 1800,
                 redis_ttl: int = 3600,
                 node_id: str = "node1"):
        super().__init__(
            redis_url=redis_url,
            local_max_size=local_max_size,
            local_ttl=local_ttl,
            redis_ttl=redis_ttl,
            redis_max_entries=10000,
            max_memory_mb=100,
            eviction_policy="lru",
            node_id=node_id,
            auto_scale=True
        )

# Factory function to create appropriate cache instance
def create_distributed_cache(config=None) -> Union[EnhancedHybridDistributedCache, AdvancedResponseCache]:
    """
    Factory function to create appropriate cache instance based on configuration
    """
    if not config:
        try:
            from core.configuration import get_cache_config
            cache_config = get_cache_config()
        except ImportError:
            from config import config as app_config
            cache_config = app_config
    else:
        cache_config = config
    
    # Check if Redis is configured and available
    redis_host = getattr(cache_config, 'redis_host', getattr(cache_config, 'REDIS_HOST', None))
    redis_port = getattr(cache_config, 'redis_port', getattr(cache_config, 'REDIS_PORT', 6379))
    
    if redis_host and REDIS_AVAILABLE:
        redis_url = getattr(cache_config, 'redis_url', f"redis://{redis_host}:{redis_port}")
        
        return EnhancedHybridDistributedCache(
            redis_url=redis_url,
            local_max_size=getattr(cache_config, 'local_cache_max_size', 
                                 getattr(cache_config, 'CACHE_LOCAL_SIZE', 500)),
            local_ttl=getattr(cache_config, 'local_cache_ttl', 
                           getattr(cache_config, 'CACHE_LOCAL_TTL', 1800)),
            redis_ttl=getattr(cache_config, 'redis_cache_ttl', 
                           getattr(cache_config, 'CACHE_REDIS_TTL', 3600)),
            redis_max_entries=getattr(cache_config, 'max_cache_size', 10000),
            max_memory_mb=getattr(cache_config, 'max_memory_usage_mb', 100),
            eviction_policy=getattr(cache_config, 'response_cache_eviction_policy', 'lru'),
            node_id=getattr(cache_config, 'NODE_ID', 'node1'),
            auto_scale=getattr(cache_config, 'auto_scale_enabled', True)
        )
    else:
        logger.warning("Redis not configured or unavailable, using local cache only")
        from response_cache import create_response_cache
        return create_response_cache(cache_config)
