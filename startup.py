"""
🚀 MEFAPEX AI Chatbot - Startup Module
Handles all service initialization logic
"""
import logging
import asyncio
import time
from typing import Dict, Any

# Configuration and imports
from core.configuration import get_config, Environment

# Import middleware
from middleware import SecurityHeadersMiddleware, RateLimitMiddleware, LoggingMiddleware
from core.rate_limiter import get_rate_limiter

# Import API routes
from api.auth import router as auth_router, set_rate_limiter as set_auth_rate_limiter
from api.chat import router as chat_router, set_rate_limiter as set_chat_rate_limiter
from api.health import router as health_router

# Import services
from database.manager import db_manager
from websocket_manager import websocket_manager, message_handler
from core.websocket_middleware import setup_websocket_middleware
from auth_service import init_auth_service

logger = logging.getLogger(__name__)

class StartupManager:
    """Manages application startup sequence"""
    
    def __init__(self):
        self.config = get_config()
        self.initialized_services = []
        
    async def initialize_services(self) -> Dict[str, Any]:
        """Initialize all application services"""
        logger.info("🚀 MEFAPEX Chatbot uygulaması başlatılıyor...")
        
        try:
            # Initialize unified microservice architecture
            await self._initialize_microservice_architecture()
            
            # Initialize memory monitoring
            await self._initialize_memory_monitoring()
            
            # Initialize Turkish content system
            await self._initialize_turkish_content()
            
            # Initialize authentication service
            await self._initialize_auth_service()
            
            # Initialize cache manager
            await self._initialize_cache_manager()
            
            # Initialize WebSocket manager
            await self._initialize_websocket_manager()
            
            logger.info("✅ Tüm servisler başarıyla başlatıldı")
            
            return {
                "model_manager": self._get_model_manager(),
                "content_manager": self._get_content_manager(),
                "cache_manager_available": self._is_cache_manager_available(),
                "distributed_cache": self._get_distributed_cache()
            }
            
        except Exception as e:
            logger.error(f"❌ Application startup failed: {e}")
            raise
    
    async def _initialize_microservice_architecture(self):
        """Initialize unified microservice architecture"""
        try:
            logger.info("🏗️ Birleşik mikroservis mimarisi başlatılıyor...")
            
            # Import and initialize unified architecture
            from unified_microservice_architecture import (
                initialize_unified_architecture,
                get_unified_manager,
                MicroserviceConfig
            )
            
            await initialize_unified_architecture()
            self.initialized_services.append("microservice_architecture")
            
            # Check configuration status
            config = MicroserviceConfig.from_env()
            if config.ai_service_enabled:
                logger.info("✅ Birleşik AI Mikroservis mimarisi aktiv")
            else:
                logger.info("💻 Yerel model modu - birleşik mimari")
                
        except ImportError as e:
            logger.warning(f"⚠️ Birleşik mimari yüklenemedi: {e}")
            logger.info("🔄 Fallback olarak orijinal model manager kullanılıyor")
    
    async def _initialize_memory_monitoring(self):
        """Initialize memory monitoring with emergency manager"""
        try:
            from memory_monitor import memory_monitor
            memory_monitor.start_monitoring()
            self.initialized_services.append("memory_monitor")
            logger.info("🧠 Memory monitoring started")
        except Exception as e:
            logger.warning(f"Memory monitoring başlatılamadı: {e}")
    
    async def _initialize_turkish_content(self):
        """Initialize Enhanced Turkish content system"""
        try:
            from improved_turkish_content_manager import improved_turkish_content
            # Warm up the Turkish content system
            test_response = improved_turkish_content.get_response("test")
            if test_response:
                self.initialized_services.append("turkish_content")
                logger.info("🇹🇷 Enhanced Turkish content system ready")
        except Exception as e:
            logger.warning(f"Turkish content system initialization warning: {e}")
    
    async def _initialize_auth_service(self):
        """Initialize authentication service"""
        try:
            init_auth_service(
                secret_key=self.config.security.secret_key,
                environment=self.config.environment.value
            )
            self.initialized_services.append("auth_service")
            logger.info("🔐 Authentication service initialized")
        except Exception as e:
            logger.error(f"❌ Authentication service failed: {e}")
            raise
    
    async def _initialize_cache_manager(self):
        """Initialize cache manager"""
        try:
            # Try to import cache manager
            from cache_manager import initialize_cache_manager
            await initialize_cache_manager(self.config)
            self.initialized_services.append("cache_manager")
            logger.info("🗄️ Cache manager initialized")
        except ImportError:
            logger.info("🗄️ Using basic cache implementation")
        except Exception as e:
            logger.error(f"❌ Cache manager initialization failed: {e}")
            # Don't raise here as cache is not critical for basic functionality
    
    async def _initialize_websocket_manager(self, app=None):
        """Initialize WebSocket manager"""
        try:
            # Setup distributed WebSocket middleware if app is provided
            if app:
                setup_websocket_middleware(app, websocket_manager, cleanup_interval=300)
            
            # Set message handler for legacy compatibility
            if hasattr(websocket_manager, 'set_message_handler'):
                websocket_manager.set_message_handler(message_handler)
            
            self.initialized_services.append("websocket_manager")
            logger.info("🔌 WebSocket manager initialized with distributed support")
        except Exception as e:
            logger.warning(f"WebSocket manager warning: {e}")
    
    def _get_model_manager(self):
        """Get the appropriate model manager"""
        try:
            from unified_microservice_architecture import get_unified_manager
            return get_unified_manager()
        except ImportError:
            from model_manager import model_manager
            return model_manager
    
    def _get_content_manager(self):
        """Get content manager if available"""
        try:
            from content_manager import ContentManager
            content_manager = ContentManager()
            logger.info("✅ Content manager loaded")
            return content_manager
        except ImportError:
            logger.warning("⚠️ Content manager not available")
            return None
    
    def _is_cache_manager_available(self):
        """Check if cache manager is available"""
        try:
            from cache_manager import get_cache_manager
            return True
        except ImportError:
            return False
    
    def _get_distributed_cache(self):
        """Get distributed cache if available"""
        try:
            from distributed_cache import create_distributed_cache
            distributed_cache = create_distributed_cache(self.config)
            logger.info("✅ Basic distributed cache initialized")
            return distributed_cache
        except ImportError:
            logger.warning("⚠️ Distributed cache not available")
            return None
    
    def setup_middleware(self, app):
        """Setup application middleware"""
        # Import middleware
        from middleware import SecurityHeadersMiddleware, RateLimitMiddleware, LoggingMiddleware
        from core.configuration import Environment
        
        # Add middleware (order matters!)
        app.add_middleware(LoggingMiddleware)
        app.add_middleware(RateLimitMiddleware)  # Will be auto-initialized with distributed rate limiter
        app.add_middleware(SecurityHeadersMiddleware)

        # CORS middleware
        from fastapi.middleware.cors import CORSMiddleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config.server.allowed_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE"],
            allow_headers=["*"],
        )

        # Trusted host middleware for production
        if self.config.environment == Environment.PRODUCTION:
            from fastapi.middleware.trustedhost import TrustedHostMiddleware
            app.add_middleware(
                TrustedHostMiddleware,
                allowed_hosts=["mefapex.com", "www.mefapex.com", "api.mefapex.com"]
            )
    
    def setup_routes(self, app):
        """Setup application routes"""
        # Include API routers
        from api.auth import router as auth_router
        from api.chat import router as chat_router  
        from api.health import router as health_router
        
        app.include_router(auth_router)
        app.include_router(chat_router)
        app.include_router(health_router)
        
        # Static files
        from fastapi.staticfiles import StaticFiles
        app.mount("/static", StaticFiles(directory="static"), name="static")
    
    def get_initialized_services(self):
        """Get list of successfully initialized services"""
        return self.initialized_services.copy()
