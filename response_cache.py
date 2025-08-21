"""
Advanced Response Cache for MEFAPEX AI Assistant
Implements TTL (Time To Live) and multiple eviction strategies with memory management
"""
import time
import hashlib
import threading
import logging
import random
import psutil
import gc
from typing import Dict, Optional, Tuple, Any, Union
from collections import OrderedDict, deque
from dataclasses import dataclass
from enum import Enum
import json

logger = logging.getLogger(__name__)

class EvictionPolicy(Enum):
    """Cache eviction policies"""
    LRU = "lru"           # Least Recently Used
    FIFO = "fifo"         # First In, First Out
    LFU = "lfu"           # Least Frequently Used
    RANDOM = "random"     # Random eviction
    TTL_AWARE = "ttl_aware"  # TTL-aware eviction (evict items closest to expiration)

@dataclass
class CacheEntry:
    """
    Cache entry with timestamp and access tracking
    """
    response: str
    timestamp: float
    access_count: int
    last_accessed: float
    source: str
    
    def is_expired(self, ttl: int) -> bool:
        """Check if entry is expired based on TTL"""
        return (time.time() - self.timestamp) > ttl
    
    def touch(self):
        """Update access information"""
        self.access_count += 1
        self.last_accessed = time.time()
    
    def time_until_expiry(self, ttl: int) -> float:
        """Get time until entry expires"""
        return max(0, ttl - (time.time() - self.timestamp))
    
    def get_memory_size(self) -> int:
        """Estimate memory usage of this entry in bytes"""
        return len(self.response.encode('utf-8')) + len(self.source.encode('utf-8')) + 200  # Base overhead

class AdvancedResponseCache:
    """
    Thread-safe response cache with configurable TTL, size limits, and eviction policies
    Features:
    - Multiple eviction policies (LRU, FIFO, LFU, Random, TTL-aware)
    - Memory usage monitoring and limits
    - Auto-scaling based on usage patterns
    - Thread-safe operations with performance optimization
    - Comprehensive statistics and monitoring
    - Context-aware caching
    """
    
    def __init__(self, 
                 max_size: int = 1000, 
                 ttl: int = 3600,
                 eviction_policy: Union[str, EvictionPolicy] = EvictionPolicy.LRU,
                 max_memory_mb: int = 100,
                 auto_scale: bool = True,
                 cleanup_interval: int = 300):
        """
        Initialize advanced cache
        
        Args:
            max_size: Maximum number of entries to cache
            ttl: Time to live in seconds (default: 1 hour)
            eviction_policy: Eviction policy to use
            max_memory_mb: Maximum memory usage in MB
            auto_scale: Enable auto-scaling based on usage
            cleanup_interval: Cleanup interval in seconds
        """
        self.max_size = max_size
        self.original_max_size = max_size  # Store original for auto-scaling
        self.ttl = ttl
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.auto_scale = auto_scale
        self.cleanup_interval = cleanup_interval
        
        # Set eviction policy
        if isinstance(eviction_policy, str):
            self.eviction_policy = EvictionPolicy(eviction_policy.lower())
        else:
            self.eviction_policy = eviction_policy
        
        # Cache storage based on eviction policy
        if self.eviction_policy in [EvictionPolicy.LRU, EvictionPolicy.TTL_AWARE]:
            self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        else:
            self._cache: Dict[str, CacheEntry] = {}
        
        # FIFO queue for FIFO policy
        if self.eviction_policy == EvictionPolicy.FIFO:
            self._fifo_queue: deque = deque()
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Statistics
        self._stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'evictions': 0,
            'expirations': 0,
            'memory_evictions': 0,
            'auto_scale_events': 0
        }
        
        # Memory tracking
        self._current_memory_usage = 0
        self._last_memory_check = time.time()
        
        # Start background threads
        self._start_background_tasks()
        
        logger.info(f"🗄️ AdvancedResponseCache initialized: max_size={max_size}, ttl={ttl}s, "
                   f"policy={self.eviction_policy.value}, max_memory={max_memory_mb}MB")
    
    def _start_background_tasks(self):
        """Start background cleanup and monitoring threads"""
        # Cleanup thread
        self._cleanup_thread = threading.Thread(target=self._periodic_cleanup, daemon=True)
        self._cleanup_thread.start()
        
        # Memory monitoring thread
        if self.auto_scale:
            self._memory_thread = threading.Thread(target=self._memory_monitor, daemon=True)
            self._memory_thread.start()
    
    def _get_cache_key(self, message: str, context: str = "") -> str:
        """Generate cache key from message and context"""
        normalized_message = message.strip().lower()
        normalized_context = context.strip().lower() if context else ""
        combined = f"{normalized_message}:{normalized_context}"
        return hashlib.md5(combined.encode('utf-8')).hexdigest()
    
    def get(self, message: str, context: str = "") -> Optional[Tuple[str, str]]:
        """Retrieve cached response with policy-aware access tracking"""
        cache_key = self._get_cache_key(message, context)
        
        with self._lock:
            if cache_key not in self._cache:
                self._stats['misses'] += 1
                return None
            
            entry = self._cache[cache_key]
            
            # Check if expired
            if entry.is_expired(self.ttl):
                self._remove_entry(cache_key)
                self._stats['expirations'] += 1
                self._stats['misses'] += 1
                return None
            
            # Update access info
            entry.touch()
            
            # Handle LRU policy
            if self.eviction_policy == EvictionPolicy.LRU and isinstance(self._cache, OrderedDict):
                self._cache.move_to_end(cache_key)
            
            self._stats['hits'] += 1
            logger.debug(f"✅ Cache hit for key: {cache_key[:8]}... (policy: {self.eviction_policy.value})")
            
            return (entry.response, entry.source)
    
    def set(self, message: str, response: str, context: str = "", source: str = "cached"):
        """Store response in cache with policy-aware eviction"""
        cache_key = self._get_cache_key(message, context)
        
        with self._lock:
            current_time = time.time()
            
            # Create cache entry
            entry = CacheEntry(
                response=response,
                timestamp=current_time,
                access_count=1,
                last_accessed=current_time,
                source=source
            )
            
            # Check memory impact
            entry_size = entry.get_memory_size()
            
            # Handle existing entry
            if cache_key in self._cache:
                old_entry = self._cache[cache_key]
                self._current_memory_usage -= old_entry.get_memory_size()
            
            # Add new entry
            self._cache[cache_key] = entry
            self._current_memory_usage += entry_size
            
            # Handle FIFO queue
            if self.eviction_policy == EvictionPolicy.FIFO and cache_key not in self._cache:
                self._fifo_queue.append(cache_key)
            
            # Handle LRU ordering
            if self.eviction_policy == EvictionPolicy.LRU and isinstance(self._cache, OrderedDict):
                self._cache.move_to_end(cache_key)
            
            self._stats['sets'] += 1
            
            # Check if we need to evict
            self._enforce_limits()
            
            logger.debug(f"💾 Cached response for key: {cache_key[:8]}... "
                        f"(size: {len(self._cache)}/{self.max_size}, memory: {self._current_memory_usage//1024}KB)")
    
    def _enforce_limits(self):
        """Enforce size and memory limits"""
        # Memory limit enforcement
        if self._current_memory_usage > self.max_memory_bytes:
            self._evict_by_memory()
        
        # Size limit enforcement
        while len(self._cache) > self.max_size:
            self._evict_one()
    
    def _evict_one(self):
        """Evict one entry based on the configured policy"""
        if not self._cache:
            return
        
        if self.eviction_policy == EvictionPolicy.LRU:
            self._evict_lru()
        elif self.eviction_policy == EvictionPolicy.FIFO:
            self._evict_fifo()
        elif self.eviction_policy == EvictionPolicy.LFU:
            self._evict_lfu()
        elif self.eviction_policy == EvictionPolicy.RANDOM:
            self._evict_random()
        elif self.eviction_policy == EvictionPolicy.TTL_AWARE:
            self._evict_ttl_aware()
    
    def _evict_lru(self):
        """Evict least recently used entry"""
        if isinstance(self._cache, OrderedDict):
            evicted_key, _ = self._cache.popitem(last=False)
        else:
            # Fallback for non-OrderedDict
            evicted_key = min(self._cache.keys(), 
                            key=lambda k: self._cache[k].last_accessed)
            del self._cache[evicted_key]
        
        self._current_memory_usage -= self._cache.get(evicted_key, CacheEntry("", 0, 0, 0, "")).get_memory_size()
        self._stats['evictions'] += 1
        logger.debug(f"🗑️ LRU evicted: {evicted_key[:8]}...")
    
    def _evict_fifo(self):
        """Evict first in, first out entry"""
        if hasattr(self, '_fifo_queue') and self._fifo_queue:
            evicted_key = self._fifo_queue.popleft()
            if evicted_key in self._cache:
                entry = self._cache[evicted_key]
                self._current_memory_usage -= entry.get_memory_size()
                del self._cache[evicted_key]
                self._stats['evictions'] += 1
                logger.debug(f"�️ FIFO evicted: {evicted_key[:8]}...")
    
    def _evict_lfu(self):
        """Evict least frequently used entry"""
        evicted_key = min(self._cache.keys(), 
                         key=lambda k: self._cache[k].access_count)
        entry = self._cache[evicted_key]
        self._current_memory_usage -= entry.get_memory_size()
        del self._cache[evicted_key]
        self._stats['evictions'] += 1
        logger.debug(f"🗑️ LFU evicted: {evicted_key[:8]}...")
    
    def _evict_random(self):
        """Evict random entry"""
        evicted_key = random.choice(list(self._cache.keys()))
        entry = self._cache[evicted_key]
        self._current_memory_usage -= entry.get_memory_size()
        del self._cache[evicted_key]
        self._stats['evictions'] += 1
        logger.debug(f"🗑️ Random evicted: {evicted_key[:8]}...")
    
    def _evict_ttl_aware(self):
        """Evict entry closest to expiration"""
        evicted_key = min(self._cache.keys(), 
                         key=lambda k: self._cache[k].time_until_expiry(self.ttl))
        entry = self._cache[evicted_key]
        self._current_memory_usage -= entry.get_memory_size()
        del self._cache[evicted_key]
        self._stats['evictions'] += 1
        logger.debug(f"🗑️ TTL-aware evicted: {evicted_key[:8]}...")
    
    def _evict_by_memory(self):
        """Evict entries until memory usage is under limit"""
        target_memory = self.max_memory_bytes * 0.8  # Target 80% of max memory
        
        while self._current_memory_usage > target_memory and self._cache:
            self._evict_one()
            self._stats['memory_evictions'] += 1
        
        # Force garbage collection after memory eviction
        gc.collect()
        
        logger.info(f"🧹 Memory eviction completed. Usage: {self._current_memory_usage//1024}KB/{self.max_memory_bytes//1024}KB")
    
    def _remove_entry(self, cache_key: str):
        """Remove entry and update memory tracking"""
        if cache_key in self._cache:
            entry = self._cache[cache_key]
            self._current_memory_usage -= entry.get_memory_size()
            del self._cache[cache_key]
            
            # Remove from FIFO queue if applicable
            if self.eviction_policy == EvictionPolicy.FIFO and hasattr(self, '_fifo_queue'):
                try:
                    self._fifo_queue.remove(cache_key)
                except ValueError:
                    pass  # Key not in queue
    
    def _periodic_cleanup(self):
        """Periodic cleanup of expired entries"""
        while True:
            try:
                time.sleep(self.cleanup_interval)
                self._cleanup_expired()
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")
    
    def _cleanup_expired(self):
        """Remove expired entries from cache"""
        current_time = time.time()
        expired_keys = []
        
        with self._lock:
            for key, entry in self._cache.items():
                if entry.is_expired(self.ttl):
                    expired_keys.append(key)
            
            for key in expired_keys:
                self._remove_entry(key)
                self._stats['expirations'] += 1
        
        if expired_keys:
            logger.info(f"🧹 Cleaned up {len(expired_keys)} expired cache entries")
    
    def _memory_monitor(self):
        """Monitor memory usage and auto-scale if needed"""
        while True:
            try:
                time.sleep(60)  # Check every minute
                
                with self._lock:
                    # Get system memory info
                    memory_info = psutil.virtual_memory()
                    system_memory_percent = memory_info.percent
                    
                    # Calculate cache usage ratio
                    usage_ratio = len(self._cache) / self.max_size if self.max_size > 0 else 0
                    memory_ratio = self._current_memory_usage / self.max_memory_bytes if self.max_memory_bytes > 0 else 0
                    
                    # Auto-scale based on usage patterns
                    if usage_ratio > 0.9 and memory_ratio < 0.7 and system_memory_percent < 80:
                        # Scale up
                        new_size = min(self.max_size * 2, self.original_max_size * 10)
                        if new_size != self.max_size:
                            self.max_size = new_size
                            self._stats['auto_scale_events'] += 1
                            logger.info(f"📈 Auto-scaled cache up to {new_size} entries")
                    
                    elif usage_ratio < 0.5 and self.max_size > self.original_max_size:
                        # Scale down
                        new_size = max(self.max_size // 2, self.original_max_size)
                        if new_size != self.max_size:
                            self.max_size = new_size
                            self._stats['auto_scale_events'] += 1
                            logger.info(f"📉 Auto-scaled cache down to {new_size} entries")
                
            except Exception as e:
                logger.error(f"Memory monitoring error: {e}")
    
    def clear(self):
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
            if hasattr(self, '_fifo_queue'):
                self._fifo_queue.clear()
            self._current_memory_usage = 0
            logger.info("🗑️ Cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        with self._lock:
            hit_rate = (
                self._stats['hits'] / (self._stats['hits'] + self._stats['misses'])
                if (self._stats['hits'] + self._stats['misses']) > 0
                else 0
            )
            
            # Memory usage
            memory_usage_mb = self._current_memory_usage / (1024 * 1024)
            memory_limit_mb = self.max_memory_bytes / (1024 * 1024)
            
            return {
                'type': 'advanced_response_cache',
                'size': len(self._cache),
                'max_size': self.max_size,
                'original_max_size': self.original_max_size,
                'ttl': self.ttl,
                'eviction_policy': self.eviction_policy.value,
                'hit_rate': round(hit_rate * 100, 2),
                'memory_usage_mb': round(memory_usage_mb, 2),
                'memory_limit_mb': round(memory_limit_mb, 2),
                'memory_usage_percent': round((memory_usage_mb / memory_limit_mb * 100), 2) if memory_limit_mb > 0 else 0,
                'auto_scale_enabled': self.auto_scale,
                **self._stats
            }
    
    def get_popular_entries(self, limit: int = 10) -> list:
        """Get most frequently accessed cache entries"""
        with self._lock:
            sorted_entries = sorted(
                self._cache.items(),
                key=lambda x: x[1].access_count,
                reverse=True
            )
            
            return [
                {
                    'key': key[:8] + '...',
                    'access_count': entry.access_count,
                    'response_preview': entry.response[:100] + '...' if len(entry.response) > 100 else entry.response,
                    'source': entry.source,
                    'age_minutes': round((time.time() - entry.timestamp) / 60, 1),
                    'memory_size_kb': round(entry.get_memory_size() / 1024, 2),
                    'time_until_expiry_minutes': round(entry.time_until_expiry(self.ttl) / 60, 1)
                }
                for key, entry in sorted_entries[:limit]
            ]
    
    def optimize(self):
        """Manual optimization: cleanup expired entries and defragment"""
        with self._lock:
            # Clean expired entries
            self._cleanup_expired()
            
            # Force garbage collection
            gc.collect()
            
            # Rebuild cache structure for OrderedDict efficiency
            if isinstance(self._cache, OrderedDict) and len(self._cache) > 100:
                # Rebuild to optimize internal structure
                items = list(self._cache.items())
                self._cache.clear()
                for key, entry in items:
                    self._cache[key] = entry
            
            logger.info(f"🔧 Cache optimized: {len(self._cache)} entries, {self._current_memory_usage//1024}KB memory")

# Maintain backward compatibility
class SimpleResponseCache(AdvancedResponseCache):
    """Backward compatibility wrapper"""
    
    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        super().__init__(
            max_size=max_size,
            ttl=ttl,
            eviction_policy=EvictionPolicy.LRU,
            max_memory_mb=100,
            auto_scale=False,
            cleanup_interval=300
        )

# Factory function to create cache with configuration
def create_response_cache(config=None) -> AdvancedResponseCache:
    """Factory function to create response cache with configuration"""
    if not config:
        try:
            from core.configuration import get_cache_config
            cache_config = get_cache_config()
        except ImportError:
            # Fallback to simple config
            from config import config as app_config
            return AdvancedResponseCache(
                max_size=getattr(app_config, 'CACHE_SIZE', 1000),
                ttl=getattr(app_config, 'CACHE_TTL', 3600),
                eviction_policy=EvictionPolicy.LRU
            )
    else:
        cache_config = config
    
    return AdvancedResponseCache(
        max_size=cache_config.response_cache_max_size,
        ttl=cache_config.response_cache_ttl,
        eviction_policy=cache_config.response_cache_eviction_policy,
        max_memory_mb=cache_config.max_memory_usage_mb,
        auto_scale=cache_config.auto_scale_enabled,
        cleanup_interval=cache_config.cleanup_interval
    )

# Global cache instance - will be replaced with factory-created instance
response_cache = AdvancedResponseCache(max_size=1000, ttl=3600)

def get_response_cache() -> AdvancedResponseCache:
    """Get the global response cache instance"""
    return response_cache

def initialize_response_cache(config=None):
    """Initialize global response cache with configuration"""
    global response_cache
    response_cache = create_response_cache(config)
