"""
🚀 MEFAPEX AI Chatbot - Refactored Main Application
==================================================
Modular FastAPI application implementing SOLID principles with dependency injection.

Key Improvements:
- Dependency Injection Container
- Single Responsibility Principle
- Interface segregation
- Factory Pattern
- Proper separation of concerns
"""

import logging
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Core imports
from core.container.dependency_container import get_container, DependencyContainer
from core.container.service_configuration import configure_services
from core.interfaces.database_interface import IDatabaseManager
from core.interfaces.auth_interface import IAuthenticationService
from core.interfaces.model_interface import IModelManager
from core.interfaces.config_interface import IConfigurationService

# Service implementations
from services.implementations.config_service import ConfigurationService

# API routers
from api.auth import create_auth_router
from api.chat import create_chat_router
from api.health import create_health_router

# Middleware
from middleware import SecurityHeadersMiddleware, RateLimitMiddleware, LoggingMiddleware, RateLimiter

logger = logging.getLogger(__name__)


class ApplicationBootstrapper:
    """
    Application bootstrapper implementing dependency injection setup.
    Single Responsibility: Application initialization and service configuration.
    """
    
    def __init__(self):
        self.container: DependencyContainer = get_container()
        self.config_service: IConfigurationService = None
        self.services = {}
    
    def configure_logging(self):
        """Configure application logging"""
        logging.basicConfig(
            level=logging.INFO if self.config_service.is_development() else logging.WARNING,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def register_services(self):
        """Register all services in dependency container"""
        # Register configuration service first
        self.config_service = ConfigurationService()
        self.container.register_instance(IConfigurationService, self.config_service)
        
        # Configure logging based on config
        self.configure_logging()
        
        # Register other services
        configure_services(self.container)
        
        # Resolve main services for application use
        self.services = {
            'database_manager': self.container.resolve(IDatabaseManager),
            'auth_service': self.container.resolve(IAuthenticationService),
            'model_manager': self.container.resolve(IModelManager)
        }
        
        logger.info("✅ All services registered and resolved")
    
    async def initialize_services(self):
        """Initialize services that require async setup"""
        try:
            # Initialize database
            db_manager = self.services['database_manager']
            if hasattr(db_manager, 'initialize'):
                await db_manager.initialize()
            
            # Warm up AI models
            model_manager = self.services['model_manager']
            if hasattr(model_manager, 'warmup_models'):
                model_manager.warmup_models()
            
            # Setup memory monitoring if available
            try:
                from memory_monitor import setup_memory_monitoring
                setup_memory_monitoring()
                logger.info("🧠 Memory monitoring enabled")
            except ImportError:
                logger.info("Memory monitoring not available")
            
            logger.info("✅ Service initialization completed")
            
        except Exception as e:
            logger.error(f"❌ Service initialization failed: {e}")
            raise
    
    async def cleanup_services(self):
        """Cleanup services on shutdown"""
        try:
            # Close database connections
            db_manager = self.services.get('database_manager')
            if db_manager and hasattr(db_manager, 'close'):
                db_manager.close()
            
            # Cleanup model resources
            model_manager = self.services.get('model_manager')
            if model_manager and hasattr(model_manager, 'cleanup_resources'):
                model_manager.cleanup_resources()
            
            logger.info("✅ Service cleanup completed")
            
        except Exception as e:
            logger.error(f"❌ Service cleanup failed: {e}")


class ApplicationFactory:
    """
    Factory for creating FastAPI application with dependency injection.
    Single Responsibility: FastAPI application creation and configuration.
    """
    
    def __init__(self, bootstrapper: ApplicationBootstrapper):
        self.bootstrapper = bootstrapper
        self.container = bootstrapper.container
        self.config_service = bootstrapper.config_service
    
    def create_app(self) -> FastAPI:
        """Create and configure FastAPI application"""
        
        # Create lifespan context manager
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            logger.info("🚀 Starting MEFAPEX AI Chatbot")
            await self.bootstrapper.initialize_services()
            yield
            # Shutdown
            logger.info("🔄 Shutting down MEFAPEX AI Chatbot")
            await self.bootstrapper.cleanup_services()
        
        # Create FastAPI app
        app = FastAPI(
            title="MEFAPEX AI Chatbot",
            description="Advanced AI-powered chatbot with modular architecture",
            version="3.0.0",
            docs_url="/docs" if self.config_service.is_development() else None,
            redoc_url="/redoc" if self.config_service.is_development() else None,
            lifespan=lifespan
        )
        
        # Configure middleware
        self._configure_middleware(app)
        
        # Configure routes
        self._configure_routes(app)
        
        # Configure static files
        app.mount("/static", StaticFiles(directory="static"), name="static")
        
        # Root endpoint
        @app.get("/")
        async def read_root():
            return FileResponse("static/index.html", media_type="text/html; charset=utf-8")
        
        return app
    
    def _configure_middleware(self, app: FastAPI):
        """Configure application middleware"""
        # Create rate limiter
        rate_limiter = RateLimiter(
            max_requests_per_minute=self.config_service.get_int("RATE_LIMIT_REQUESTS", 200),
            max_chat_requests_per_minute=self.config_service.get_int("RATE_LIMIT_CHAT", 100)
        )
        
        # Add middleware (order matters!)
        app.add_middleware(LoggingMiddleware)
        app.add_middleware(RateLimitMiddleware, rate_limiter=rate_limiter)
        app.add_middleware(SecurityHeadersMiddleware)
        
        # CORS middleware
        cors_config = self.config_service.get_cors_config()
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_config.get('allowed_origins', ["*"]),
            allow_credentials=cors_config.get('allow_credentials', True),
            allow_methods=cors_config.get('allowed_methods', ["GET", "POST", "PUT", "DELETE"]),
            allow_headers=cors_config.get('allowed_headers', ["*"]),
        )
        
        # Trusted host middleware for production
        if self.config_service.is_production():
            security_config = self.config_service.get_security_config()
            allowed_hosts = security_config.get('allowed_hosts', ["mefapex.com", "www.mefapex.com"])
            
            app.add_middleware(
                TrustedHostMiddleware,
                allowed_hosts=allowed_hosts
            )
    
    def _configure_routes(self, app: FastAPI):
        """Configure application routes with dependency injection"""
        
        # Dependency providers
        def get_database_manager() -> IDatabaseManager:
            return self.container.resolve(IDatabaseManager)
        
        def get_auth_service() -> IAuthenticationService:
            return self.container.resolve(IAuthenticationService)
        
        def get_model_manager() -> IModelManager:
            return self.container.resolve(IModelManager)
        
        # Create routers with injected dependencies
        auth_router = create_auth_router(
            get_auth_service,
            get_database_manager
        )
        
        chat_router = create_chat_router(
            get_auth_service,
            get_database_manager,
            get_model_manager
        )
        
        health_router = create_health_router(
            get_database_manager,
            get_model_manager
        )
        
        # Include routers
        app.include_router(auth_router)
        app.include_router(chat_router)
        app.include_router(health_router)


# Dependency providers for route handlers
DatabaseManagerDep = Annotated[IDatabaseManager, Depends(lambda: get_container().resolve(IDatabaseManager))]
AuthServiceDep = Annotated[IAuthenticationService, Depends(lambda: get_container().resolve(IAuthenticationService))]
ModelManagerDep = Annotated[IModelManager, Depends(lambda: get_container().resolve(IModelManager))]
ConfigServiceDep = Annotated[IConfigurationService, Depends(lambda: get_container().resolve(IConfigurationService))]


def create_application() -> FastAPI:
    """
    Create application with dependency injection.
    Main entry point for application creation.
    """
    # Create and configure bootstrapper
    bootstrapper = ApplicationBootstrapper()
    bootstrapper.register_services()
    
    # Create application factory
    app_factory = ApplicationFactory(bootstrapper)
    
    # Create and return configured app
    return app_factory.create_app()


# Create application instance
app = create_application()


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Custom 404 handler"""
    return FileResponse("static/index.html", media_type="text/html; charset=utf-8")


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Custom 500 handler"""
    logger.error(f"Internal server error: {exc}")
    return {"error": "Internal server error", "detail": "Something went wrong"}


if __name__ == "__main__":
    import uvicorn
    
    # Get configuration
    config_service = get_container().resolve(IConfigurationService)
    
    uvicorn.run(
        "main_refactored:app",
        host="0.0.0.0",
        port=config_service.get_int("PORT", 8000),
        reload=config_service.is_development(),
        log_level="info" if config_service.is_development() else "warning"
    )
