"""
Advanced Response Cache for MEFAPEX AI Assistant
Implements TTL (Time To Live) and LRU (Least Recently Used) eviction strategies
"""
import time
import hashlib
import threading
import logging
from typing import Dict, Optional, Tuple, Any
from collections import OrderedDict
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)

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

class SimpleResponseCache:
    """
    Thread-safe response cache with TTL and LRU eviction
    Features:
    - TTL (Time To Live) for automatic expiration
    - LRU (Least Recently Used) eviction when max size reached
    - Thread-safe operations
    - Cache statistics and monitoring
    - Context-aware caching (different responses for different contexts)
    """
    
    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        """
        Initialize cache
        
        Args:
            max_size: Maximum number of entries to cache
            ttl: Time to live in seconds (default: 1 hour)
        """
        self.max_size = max_size
        self.ttl = ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()  # Reentrant lock for nested operations
        self._stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'evictions': 0,
            'expirations': 0
        }
        
        # Start cleanup thread
        self._cleanup_thread = threading.Thread(target=self._periodic_cleanup, daemon=True)
        self._cleanup_thread.start()
        
        logger.info(f"🗄️ ResponseCache initialized: max_size={max_size}, ttl={ttl}s")
    
    def _get_cache_key(self, message: str, context: str = "") -> str:
        """
        Generate cache key from message and context
        
        Args:
            message: User message
            context: Optional context (e.g., database results)
            
        Returns:
            MD5 hash of normalized input
        """
        # Normalize inputs for better cache hits
        normalized_message = message.strip().lower()
        normalized_context = context.strip().lower() if context else ""
        
        # Create combined key
        combined = f"{normalized_message}:{normalized_context}"
        
        # Generate hash
        cache_key = hashlib.md5(combined.encode('utf-8')).hexdigest()
        
        return cache_key
    
    def get(self, message: str, context: str = "") -> Optional[Tuple[str, str]]:
        """
        Retrieve cached response
        
        Args:
            message: User message
            context: Optional context
            
        Returns:
            Tuple of (response, source) if found, None otherwise
        """
        cache_key = self._get_cache_key(message, context)
        
        with self._lock:
            if cache_key not in self._cache:
                self._stats['misses'] += 1
                return None
            
            entry = self._cache[cache_key]
            
            # Check if expired
            if entry.is_expired(self.ttl):
                del self._cache[cache_key]
                self._stats['expirations'] += 1
                self._stats['misses'] += 1
                return None
            
            # Update access info and move to end (most recently used)
            entry.touch()
            self._cache.move_to_end(cache_key)
            
            self._stats['hits'] += 1
            logger.debug(f"✅ Cache hit for key: {cache_key[:8]}...")
            
            return (entry.response, entry.source)
    
    def set(self, message: str, response: str, context: str = "", source: str = "cached"):
        """
        Store response in cache
        
        Args:
            message: User message
            response: AI response to cache
            context: Optional context used for generation
            source: Source of the response (e.g., "openai", "huggingface")
        """
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
            
            # Add/update entry
            self._cache[cache_key] = entry
            self._cache.move_to_end(cache_key)  # Mark as most recently used
            
            self._stats['sets'] += 1
            
            # Check if we need to evict old entries
            if len(self._cache) > self.max_size:
                self._evict_lru()
            
            logger.debug(f"💾 Cached response for key: {cache_key[:8]}...")
    
    def _evict_lru(self):
        """
        Evict least recently used entries when cache is full
        """
        while len(self._cache) > self.max_size:
            # Remove least recently used (first item in OrderedDict)
            evicted_key, _ = self._cache.popitem(last=False)
            self._stats['evictions'] += 1
            logger.debug(f"🗑️ Evicted LRU entry: {evicted_key[:8]}...")
    
    def _periodic_cleanup(self):
        """
        Periodic cleanup of expired entries (runs in background thread)
        """
        while True:
            try:
                time.sleep(300)  # Clean up every 5 minutes
                self._cleanup_expired()
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")
    
    def _cleanup_expired(self):
        """
        Remove expired entries from cache
        """
        current_time = time.time()
        expired_keys = []
        
        with self._lock:
            for key, entry in self._cache.items():
                if entry.is_expired(self.ttl):
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._cache[key]
                self._stats['expirations'] += 1
        
        if expired_keys:
            logger.info(f"🧹 Cleaned up {len(expired_keys)} expired cache entries")
    
    def clear(self):
        """
        Clear all cache entries
        """
        with self._lock:
            self._cache.clear()
            logger.info("🗑️ Cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        """
        with self._lock:
            hit_rate = (
                self._stats['hits'] / (self._stats['hits'] + self._stats['misses'])
                if (self._stats['hits'] + self._stats['misses']) > 0
                else 0
            )
            
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'ttl': self.ttl,
                'hit_rate': round(hit_rate * 100, 2),
                **self._stats,
                'memory_usage_mb': self._estimate_memory_usage()
            }
    
    def _estimate_memory_usage(self) -> float:
        """
        Estimate cache memory usage in MB
        """
        try:
            # Simple estimation based on string lengths
            total_chars = sum(
                len(entry.response) + len(entry.source)
                for entry in self._cache.values()
            )
            # Rough estimate: 1 char ≈ 1 byte, plus overhead
            estimated_bytes = total_chars * 1.5  # Add 50% overhead
            return round(estimated_bytes / (1024 * 1024), 2)
        except:
            return 0.0
    
    def get_popular_entries(self, limit: int = 10) -> list:
        """
        Get most frequently accessed cache entries
        """
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
                    'age_minutes': round((time.time() - entry.timestamp) / 60, 1)
                }
                for key, entry in sorted_entries[:limit]
            ]

# Global cache instance
response_cache = SimpleResponseCache(max_size=1000, ttl=3600)  # 1000 entries, 1 hour TTL
