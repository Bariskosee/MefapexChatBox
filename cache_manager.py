"""
🗄️ MEFAPEX Cache Manager
Centralized cache management with configuration-driven initialization
"""
import logging
import asyncio
from typing import Optional, Union, Dict, Any

logger = logging.getLogger(__name__)

class CacheManager:
    """
    Centralized cache manager for all cache instances
    Features:
    - Configuration-driven initialization
    - Health monitoring
    - Performance metrics
    - Graceful shutdown
    """
    
    def __init__(self):
        self.response_cache = None
        self.distributed_cache = None
        self.initialized = False
        
    async def initialize(self, config=None):
        """Initialize all cache instances with configuration"""
        try:
            # Import cache modules
            from response_cache import create_response_cache, initialize_response_cache
            from distributed_cache import create_distributed_cache
            
            # Get configuration
            if not config:
                try:
                    from core.configuration import get_cache_config
                    cache_config = get_cache_config()
                except ImportError:
                    # Fallback to simple config
                    from config import config as app_config
                    cache_config = app_config
            else:
                cache_config = config
            
            # Initialize response cache
            if getattr(cache_config, 'response_cache_enabled', True):
                self.response_cache = create_response_cache(cache_config)
                initialize_response_cache(cache_config)
                logger.info("✅ Response cache initialized")
            
            # Initialize distributed cache
            if getattr(cache_config, 'distributed_cache_enabled', True):
                self.distributed_cache = create_distributed_cache(cache_config)
                
                # Initialize async cache if it has an initialize method
                if hasattr(self.distributed_cache, 'initialize'):
                    await self.distributed_cache.initialize()
                
                logger.info("✅ Distributed cache initialized")
            
            self.initialized = True
            logger.info("🎯 Cache Manager initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Cache Manager initialization failed: {e}")
            raise
    
    async def shutdown(self):
        """Gracefully shutdown all cache instances"""
        try:
            if self.distributed_cache and hasattr(self.distributed_cache, 'shutdown'):
                await self.distributed_cache.shutdown()
                logger.info("🔌 Distributed cache shutdown")
            
            if self.response_cache:
                # Response cache shutdown is handled by background threads
                logger.info("🔌 Response cache shutdown")
            
            self.initialized = False
            logger.info("👋 Cache Manager shutdown complete")
            
        except Exception as e:
            logger.error(f"❌ Cache Manager shutdown error: {e}")
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get health status of all cache instances"""
        health = {
            'cache_manager': {
                'initialized': self.initialized,
                'timestamp': asyncio.get_event_loop().time()
            }
        }
        
        try:
            # Response cache health
            if self.response_cache:
                stats = self.response_cache.get_stats()
                health['response_cache'] = {
                    'enabled': True,
                    'type': stats.get('type', 'unknown'),
                    'size': stats.get('size', 0),
                    'hit_rate': stats.get('hit_rate', 0),
                    'memory_usage_mb': stats.get('memory_usage_mb', 0)
                }
            else:
                health['response_cache'] = {'enabled': False}
            
            # Distributed cache health
            if self.distributed_cache:
                if hasattr(self.distributed_cache, 'get_stats'):
                    stats = await self.distributed_cache.get_stats()
                    health['distributed_cache'] = {
                        'enabled': True,
                        'type': stats.get('type', 'unknown'),
                        'redis_available': stats.get('redis_available', False)
                    }
                    
                    # Add local cache stats if available
                    if 'local' in stats:
                        health['distributed_cache']['local'] = stats['local']
                    
                    # Add Redis stats if available
                    if 'redis' in stats:
                        health['distributed_cache']['redis'] = stats['redis']
                
                # Check health if method exists
                if hasattr(self.distributed_cache, 'health_check'):
                    health_check = await self.distributed_cache.health_check()
                    health['distributed_cache']['health_check'] = health_check
            else:
                health['distributed_cache'] = {'enabled': False}
        
        except Exception as e:
            logger.error(f"Error getting cache health status: {e}")
            health['error'] = str(e)
        
        return health
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        metrics = {
            'timestamp': asyncio.get_event_loop().time(),
            'cache_manager_initialized': self.initialized
        }
        
        try:
            # Response cache metrics
            if self.response_cache:
                response_stats = self.response_cache.get_stats()
                metrics['response_cache'] = response_stats
                
                # Add popular entries if method exists
                if hasattr(self.response_cache, 'get_popular_entries'):
                    metrics['response_cache']['popular_entries'] = self.response_cache.get_popular_entries(5)
            
            # Distributed cache metrics
            if self.distributed_cache and hasattr(self.distributed_cache, 'get_stats'):
                distributed_stats = await self.distributed_cache.get_stats()
                metrics['distributed_cache'] = distributed_stats
        
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            metrics['error'] = str(e)
        
        return metrics
    
    async def optimize_caches(self):
        """Optimize all cache instances"""
        try:
            if self.response_cache and hasattr(self.response_cache, 'optimize'):
                self.response_cache.optimize()
                logger.info("🔧 Response cache optimized")
            
            if self.distributed_cache and hasattr(self.distributed_cache, 'optimize'):
                await self.distributed_cache.optimize()
                logger.info("🔧 Distributed cache optimized")
            
            logger.info("✨ Cache optimization completed")
        
        except Exception as e:
            logger.error(f"Cache optimization error: {e}")
    
    async def clear_all_caches(self):
        """Clear all cache instances"""
        try:
            if self.response_cache:
                self.response_cache.clear()
                logger.info("🗑️ Response cache cleared")
            
            if self.distributed_cache:
                await self.distributed_cache.clear()
                logger.info("🗑️ Distributed cache cleared")
            
            logger.info("🧹 All caches cleared")
        
        except Exception as e:
            logger.error(f"Error clearing caches: {e}")
    
    def get_response_cache(self):
        """Get response cache instance"""
        return self.response_cache
    
    def get_distributed_cache(self):
        """Get distributed cache instance"""
        return self.distributed_cache

# Global cache manager instance
cache_manager = CacheManager()

async def initialize_cache_manager(config=None):
    """Initialize the global cache manager"""
    await cache_manager.initialize(config)

async def shutdown_cache_manager():
    """Shutdown the global cache manager"""
    await cache_manager.shutdown()

def get_cache_manager() -> CacheManager:
    """Get the global cache manager instance"""
    return cache_manager

async def get_cache_health() -> Dict[str, Any]:
    """Get cache health status"""
    return await cache_manager.get_health_status()

async def get_cache_metrics() -> Dict[str, Any]:
    """Get cache performance metrics"""
    return await cache_manager.get_performance_metrics()

async def optimize_all_caches():
    """Optimize all cache instances"""
    await cache_manager.optimize_caches()

async def clear_all_caches():
    """Clear all cache instances"""
    await cache_manager.clear_all_caches()

# Convenience functions for backward compatibility
def get_response_cache():
    """Get response cache instance"""
    return cache_manager.get_response_cache()

def get_distributed_cache():
    """Get distributed cache instance"""
    return cache_manager.get_distributed_cache()

if __name__ == "__main__":
    # Test the cache manager
    async def test_cache_manager():
        print("🗄️ Testing MEFAPEX Cache Manager")
        print("=" * 50)
        
        # Initialize
        await initialize_cache_manager()
        
        # Get health status
        health = await get_cache_health()
        print(f"Health Status: {health}")
        
        # Get metrics
        metrics = await get_cache_metrics()
        print(f"Metrics: {metrics}")
        
        # Shutdown
        await shutdown_cache_manager()
        print("Test completed")
    
    asyncio.run(test_cache_manager())
