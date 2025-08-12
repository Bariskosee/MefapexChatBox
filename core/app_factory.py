"""
🏗️ Application Factory
=====================
Factory pattern for creating FastAPI application with proper dependency injection
and modular architecture
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles

from core.configuration import get_config
from core.services.config_service import get_config_service
from middleware import SecurityHeadersMiddleware, RateLimitMiddleware, LoggingMiddleware, RateLimiter

# Import API routes
from api.auth import router as auth_router, set_rate_limiter as set_auth_rate_limiter
from api.chat import router as chat_router, set_rate_limiter as set_chat_rate_limiter
from api.health import router as health_router

# Import core services
from database_manager import db_manager
from model_manager import model_manager
from websocket_manager import websocket_manager
from auth_service import init_auth_service

logger = logging.getLogger(__name__)

class ApplicationFactory:
    """
    Factory for creating and configuring FastAPI application
    """
    
    def __init__(self):
        self.config = get_config()
        self.config_service = get_config_service()
        self._configure_logging()
    
    def _configure_logging(self):
        """Configure application logging"""
        logging.basicConfig(
            level=logging.INFO if self.config.server.debug else logging.WARNING,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    async def _initialize_services(self):
        """Initialize application services during startup"""
        try:
            # Initialize authentication service
            init_auth_service(
                secret_key=self.config.security.secret_key,
                environment=self.config.environment.value
            )
            logger.info("✅ Authentication service initialized")
            
            # Initialize database
            await self._initialize_database()
            
            # Initialize AI models
            await self._initialize_ai_models()
            
            logger.info("🚀 All services initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Service initialization failed: {e}")
            raise
    
    async def _initialize_database(self):
        """Initialize database connection"""
        try:
            if hasattr(db_manager, 'health_check'):
                health = db_manager.health_check()
                if health.get("status") == "healthy":
                    logger.info("✅ Database connection established")
                else:
                    logger.warning("⚠️ Database connection issues detected")
            else:
                logger.warning("⚠️ Database health check not available")
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise
    
    async def _initialize_ai_models(self):
        """Initialize AI models"""
        try:
            if hasattr(model_manager, 'initialize'):
                await model_manager.initialize()
                logger.info("✅ AI models initialized")
            else:
                logger.info("ℹ️ AI models will be loaded on demand")
        except Exception as e:
            logger.warning(f"⚠️ AI model initialization warning: {e}")
    
    async def _cleanup_services(self):
        """Cleanup services during shutdown"""
        try:
            # Cleanup AI models
            if hasattr(model_manager, 'cleanup'):
                await model_manager.cleanup()
                logger.info("🧹 AI models cleaned up")
            
            # Close database connections
            if hasattr(db_manager, 'close'):
                await db_manager.close()
                logger.info("🧹 Database connections closed")
            
            logger.info("✅ Application cleanup completed")
            
        except Exception as e:
            logger.error(f"❌ Cleanup error: {e}")
    
    @asynccontextmanager
    async def lifespan(self, app: FastAPI):
        """Application lifespan management"""
        # Startup
        logger.info("🚀 Starting MEFAPEX application...")
        await self._initialize_services()
        yield
        # Shutdown
        logger.info("🛑 Shutting down MEFAPEX application...")
        await self._cleanup_services()
    
    def _setup_middleware(self, app: FastAPI):
        """Setup application middleware"""
        # Initialize rate limiter
        rate_limiter = RateLimiter(
            max_requests_per_minute=self.config.rate_limit.requests_per_minute,
            max_chat_requests_per_minute=self.config.rate_limit.chat_requests_per_minute
        )
        
        # Set rate limiter for API routes
        set_auth_rate_limiter(rate_limiter)
        set_chat_rate_limiter(rate_limiter)
        
        # Add middleware (order matters!)
        app.add_middleware(LoggingMiddleware)
        app.add_middleware(RateLimitMiddleware, rate_limiter=rate_limiter)
        app.add_middleware(SecurityHeadersMiddleware)
        
        # CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config.server.allowed_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["*"],
        )
        
        # Trusted host middleware for production
        if self.config.is_production():
            allowed_hosts = ["mefapex.com", "www.mefapex.com", "api.mefapex.com"]
            if self.config.server.allowed_hosts:
                allowed_hosts.extend(self.config.server.allowed_hosts)
            
            app.add_middleware(
                TrustedHostMiddleware,
                allowed_hosts=allowed_hosts
            )
        
        logger.info("✅ Middleware configured")
    
    def _setup_routes(self, app: FastAPI):
        """Setup application routes"""
        # Import route handlers
        from core.http_handlers import HTTPRouteHandlers
        from core.websocket_handlers import WebSocketHandlers
        
        # Include API routes
        app.include_router(health_router, prefix="/api")
        app.include_router(auth_router, prefix="/api")
        app.include_router(chat_router, prefix="/api")
        
        # HTTP Routes
        app.get("/")(HTTPRouteHandlers.read_root)
        app.get("/health")(HTTPRouteHandlers.health)
        app.get("/health/comprehensive")(HTTPRouteHandlers.comprehensive_health_check)
        app.post("/login")(HTTPRouteHandlers.login_user_simple)
        app.post("/login_legacy")(HTTPRouteHandlers.login_legacy)
        app.get("/me")(HTTPRouteHandlers.get_current_user)
        app.post("/chat")(HTTPRouteHandlers.chat_simple)
        app.post("/chat_authenticated")(HTTPRouteHandlers.chat_authenticated)
        app.post("/save_session")(HTTPRouteHandlers.save_session)
        app.get("/user/{user_id}/sessions")(HTTPRouteHandlers.get_user_sessions)
        app.get("/session/{session_id}/messages")(HTTPRouteHandlers.get_session_messages)
        app.get("/chat_history")(HTTPRouteHandlers.get_chat_history)
        
        # WebSocket Routes
        app.websocket("/ws/{connection_id}")(WebSocketHandlers.websocket_endpoint)
        app.websocket("/ws/chat")(WebSocketHandlers.websocket_chat)
        app.websocket("/ws/admin")(WebSocketHandlers.websocket_admin)
        
        # Exception handlers
        app.add_exception_handler(404, HTTPRouteHandlers.not_found_handler)
        
        # Static files
        app.mount("/static", StaticFiles(directory="static"), name="static")
        
        logger.info("✅ Routes configured")
    
    def create_app(self) -> FastAPI:
        """Create and configure FastAPI application"""
        app = FastAPI(
            title="MEFAPEX AI Chatbot",
            description="Advanced AI-powered chatbot with multi-model support",
            version="2.0.0",
            docs_url="/docs" if self.config.server.debug else None,
            redoc_url="/redoc" if self.config.server.debug else None,
            lifespan=self.lifespan
        )
        
        # Setup middleware
        self._setup_middleware(app)
        
        # Setup routes
        self._setup_routes(app)
        
        logger.info(f"✅ FastAPI application created for {self.config.environment.value} environment")
        
        return app

# Factory function
def create_app() -> FastAPI:
    """Create application using factory pattern"""
    factory = ApplicationFactory()
    return factory.create_app()
