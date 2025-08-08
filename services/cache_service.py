"""
🗂️ Advanced Cache Service
High-performance caching with TTL, LRU eviction, and persistence
"""

import json
import time
import hashlib
import logging
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta
from threading import RLock
import os

logger = logging.getLogger(__name__)

class AdvancedCacheService:
    """Advanced caching service with multiple eviction strategies"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600, persist_file: str = None):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.persist_file = persist_file
        
        # Thread-safe storage
        self._cache = {}
        self._access_order = {}  # For LRU
        self._lock = RLock()
        
        # Statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "sets": 0,
            "size": 0
        }
        
        # Load persisted cache if available
        self._load_from_disk()
        
        logger.info(f"🗂️ AdvancedCacheService initialized (max_size={max_size}, ttl={default_ttl}s)")
    
    def _generate_key(self, key: str) -> str:
        """Generate normalized cache key"""
        if isinstance(key, str):
            return hashlib.md5(key.encode()).hexdigest()
        return str(key)
    
    def _is_expired(self, entry: Dict) -> bool:
        """Check if cache entry is expired"""
        if 'expires_at' not in entry:
            return False
        return time.time() > entry['expires_at']
    
    def _evict_expired(self):
        """Remove expired entries"""
        with self._lock:
            current_time = time.time()
            expired_keys = [
                key for key, entry in self._cache.items()
                if 'expires_at' in entry and current_time > entry['expires_at']
            ]
            
            for key in expired_keys:
                del self._cache[key]
                if key in self._access_order:
                    del self._access_order[key]
                self.stats["evictions"] += 1
    
    def _evict_lru(self, count: int = 1):
        """Evict least recently used entries"""
        with self._lock:
            if not self._access_order:
                return
            
            # Sort by access time (oldest first)
            sorted_keys = sorted(
                self._access_order.items(),
                key=lambda x: x[1]
            )
            
            for i in range(min(count, len(sorted_keys))):
                key = sorted_keys[i][0]
                if key in self._cache:
                    del self._cache[key]
                    del self._access_order[key]
                    self.stats["evictions"] += 1
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache"""
        cache_key = self._generate_key(key)
        
        with self._lock:
            entry = self._cache.get(cache_key)
            
            if entry is None:
                self.stats["misses"] += 1
                return default
            
            # Check expiration
            if self._is_expired(entry):
                del self._cache[cache_key]
                if cache_key in self._access_order:
                    del self._access_order[cache_key]
                self.stats["misses"] += 1
                self.stats["evictions"] += 1
                return default
            
            # Update access time
            self._access_order[cache_key] = time.time()
            self.stats["hits"] += 1
            
            return entry['value']
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        cache_key = self._generate_key(key)
        
        with self._lock:
            # Clean expired entries first
            self._evict_expired()
            
            # Check if we need to make space
            if len(self._cache) >= self.max_size and cache_key not in self._cache:
                # Evict 10% of cache or 1 item, whichever is larger
                evict_count = max(1, self.max_size // 10)
                self._evict_lru(evict_count)
            
            # Set TTL
            expires_at = None
            if ttl is not None:
                expires_at = time.time() + ttl
            elif self.default_ttl > 0:
                expires_at = time.time() + self.default_ttl
            
            # Store entry
            entry = {
                'value': value,
                'created_at': time.time(),
                'expires_at': expires_at
            }
            
            self._cache[cache_key] = entry
            self._access_order[cache_key] = time.time()
            self.stats["sets"] += 1
            self.stats["size"] = len(self._cache)
            
            return True
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        cache_key = self._generate_key(key)
        
        with self._lock:
            if cache_key in self._cache:
                del self._cache[cache_key]
                if cache_key in self._access_order:
                    del self._access_order[cache_key]
                self.stats["size"] = len(self._cache)
                return True
            return False
    
    def clear(self):
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
            self.stats["size"] = 0
            logger.info("🧹 Cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total_requests = self.stats["hits"] + self.stats["misses"]
            hit_rate = (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                "hit_rate": round(hit_rate, 2),
                "total_requests": total_requests,
                "current_size": len(self._cache),
                "max_size": self.max_size,
                "utilization": round(len(self._cache) / self.max_size * 100, 2),
                **self.stats
            }
    
    def get_keys(self, pattern: str = None) -> List[str]:
        """Get all keys, optionally filtered by pattern"""
        with self._lock:
            keys = list(self._cache.keys())
            
            if pattern:
                import fnmatch
                keys = [k for k in keys if fnmatch.fnmatch(k, pattern)]
            
            return keys
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """Estimate memory usage"""
        try:
            import sys
            
            with self._lock:
                total_size = 0
                for entry in self._cache.values():
                    total_size += sys.getsizeof(entry)
                    total_size += sys.getsizeof(entry.get('value', ''))
                
                return {
                    "estimated_bytes": total_size,
                    "estimated_mb": round(total_size / (1024 * 1024), 2),
                    "entries": len(self._cache)
                }
        except Exception as e:
            logger.error(f"Memory usage calculation failed: {e}")
            return {"error": str(e)}
    
    def _save_to_disk(self):
        """Save cache to disk for persistence"""
        if not self.persist_file:
            return
        
        try:
            with self._lock:
                # Only save non-expired entries
                current_time = time.time()
                persistent_data = {}
                
                for key, entry in self._cache.items():
                    if 'expires_at' not in entry or entry['expires_at'] > current_time:
                        # Make entry JSON serializable
                        persistent_entry = {
                            'value': entry['value'],
                            'created_at': entry['created_at'],
                            'expires_at': entry.get('expires_at')
                        }
                        persistent_data[key] = persistent_entry
                
                with open(self.persist_file, 'w') as f:
                    json.dump(persistent_data, f, default=str)
                
                logger.debug(f"💾 Cache saved to {self.persist_file} ({len(persistent_data)} entries)")
                
        except Exception as e:
            logger.error(f"Failed to save cache to disk: {e}")
    
    def _load_from_disk(self):
        """Load cache from disk"""
        if not self.persist_file or not os.path.exists(self.persist_file):
            return
        
        try:
            with open(self.persist_file, 'r') as f:
                persistent_data = json.load(f)
            
            with self._lock:
                current_time = time.time()
                loaded_count = 0
                
                for key, entry in persistent_data.items():
                    # Check if entry is still valid
                    if 'expires_at' not in entry or entry['expires_at'] is None or entry['expires_at'] > current_time:
                        self._cache[key] = entry
                        self._access_order[key] = entry.get('created_at', current_time)
                        loaded_count += 1
                
                self.stats["size"] = len(self._cache)
                logger.info(f"📂 Cache loaded from {self.persist_file} ({loaded_count} entries)")
                
        except Exception as e:
            logger.error(f"Failed to load cache from disk: {e}")
    
    def __del__(self):
        """Save cache on destruction"""
        self._save_to_disk()

# Global cache instance
cache_service = None

def init_cache_service(max_size: int = 1000, default_ttl: int = 3600, persist_file: str = None):
    """Initialize global cache service"""
    global cache_service
    cache_service = AdvancedCacheService(max_size, default_ttl, persist_file)
    return cache_service

def get_cache() -> AdvancedCacheService:
    """Get global cache service instance"""
    global cache_service
    if cache_service is None:
        cache_service = AdvancedCacheService()
    return cache_service
