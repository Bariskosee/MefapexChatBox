"""
🛑 MEFAPEX AI Chatbot - Shutdown Module
Handles all cleanup and shutdown logic
"""
import logging
from typing import List, Any

# Import services for cleanup
from database.manager import db_manager
from websocket_manager import websocket_manager
from core.rate_limiter import close_rate_limiter

logger = logging.getLogger(__name__)

class ShutdownManager:
    """Manages application shutdown sequence"""
    
    def __init__(self, initialized_services: List[str] = None):
        self.initialized_services = initialized_services or []
        
    async def cleanup_services(self, model_manager=None, cache_manager_available=False):
        """Cleanup all application services"""
        logger.info("🛑 MEFAPEX Chatbot uygulaması kapatılıyor...")
        
        try:
            # Close distributed rate limiter
            await self._cleanup_rate_limiter()
            
            # Stop memory monitoring
            await self._cleanup_memory_monitoring()
            
            # Cleanup AI models and microservices
            await self._cleanup_model_manager(model_manager)
            
            # Close WebSocket connections
            await self._cleanup_websocket_manager()
            
            # Cleanup unified microservice architecture
            await self._cleanup_microservice_architecture()
            
            # Shutdown cache manager
            await self._cleanup_cache_manager(cache_manager_available)
            
            # Close database connections
            await self._cleanup_database()
            
            logger.info("✅ Application shutdown completed")
            
        except Exception as e:
            logger.error(f"❌ General shutdown error: {e}")
    
    async def _cleanup_rate_limiter(self):
        """Cleanup rate limiter"""
        try:
            await close_rate_limiter()
            logger.info("🚦 Distributed rate limiter closed")
        except Exception as e:
            logger.warning(f"Rate limiter close warning: {e}")
    
    async def _cleanup_memory_monitoring(self):
        """Stop memory monitoring"""
        try:
            if "memory_monitor" in self.initialized_services:
                from memory_monitor import memory_monitor
                memory_monitor.stop_monitoring()
                logger.info("🧠 Memory monitoring stopped")
        except Exception as e:
            logger.warning(f"Memory monitoring stop warning: {e}")
    
    async def _cleanup_model_manager(self, model_manager):
        """Cleanup AI models and microservices"""
        try:
            if model_manager and hasattr(model_manager, 'cleanup'):
                await model_manager.cleanup()
                logger.info("🤖 AI models and services cleaned up")
        except Exception as e:
            logger.warning(f"Model manager cleanup warning: {e}")
    
    async def _cleanup_websocket_manager(self):
        """Close WebSocket connections"""
        try:
            if "websocket_manager" in self.initialized_services:
                if hasattr(websocket_manager, 'close'):
                    await websocket_manager.close()
                elif hasattr(websocket_manager, 'close_all_connections'):
                    await websocket_manager.close_all_connections()
                logger.info("🔌 WebSocket connections closed")
        except Exception as e:
            logger.warning(f"WebSocket cleanup warning: {e}")
    
    async def _cleanup_microservice_architecture(self):
        """Cleanup unified microservice architecture"""
        try:
            if "microservice_architecture" in self.initialized_services:
                from unified_microservice_architecture import cleanup_unified_architecture
                await cleanup_unified_architecture()
                logger.info("🧹 Birleşik mikroservis mimarisi temizlendi")
        except ImportError:
            pass  # Module not available
        except Exception as e:
            logger.error(f"❌ Birleşik mimari temizlik hatası: {e}")
    
    async def _cleanup_cache_manager(self, cache_manager_available):
        """Shutdown cache manager"""
        try:
            if cache_manager_available and "cache_manager" in self.initialized_services:
                from cache_manager import shutdown_cache_manager
                await shutdown_cache_manager()
                logger.info("🗄️ Cache manager shutdown")
        except ImportError:
            pass  # Module not available
        except Exception as e:
            logger.warning(f"Cache manager shutdown warning: {e}")
    
    async def _cleanup_database(self):
        """Close database connections"""
        try:
            await db_manager.close()
            logger.info("🗄️ Database connections closed")
        except Exception as e:
            logger.warning(f"Database close warning: {e}")
    
    async def emergency_cleanup(self):
        """Emergency cleanup for critical errors"""
        logger.warning("🚨 Emergency cleanup initiated...")
        
        try:
            # Force close database connections
            try:
                await db_manager.close()
                logger.info("🗄️ Emergency database close completed")
            except Exception as e:
                logger.error(f"Emergency database close failed: {e}")
            
            # Force close WebSocket connections
            try:
                if hasattr(websocket_manager, 'force_close_all'):
                    await websocket_manager.force_close_all()
                logger.info("🔌 Emergency WebSocket close completed")
            except Exception as e:
                logger.error(f"Emergency WebSocket close failed: {e}")
            
            # Force memory cleanup
            try:
                import gc
                collected = gc.collect()
                logger.info(f"🧠 Emergency garbage collection: {collected} objects")
            except Exception as e:
                logger.error(f"Emergency GC failed: {e}")
            
            logger.info("✅ Emergency cleanup completed")
            
        except Exception as e:
            logger.error(f"❌ Emergency cleanup failed: {e}")
