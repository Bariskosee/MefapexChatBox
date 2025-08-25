"""
🚀 MEFAPEX AI Chatbot - Refactored Main Module
Clean, modular FastAPI application with configurable database support
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

# Import configuration
from core.configuration import get_config

# Import modular components
from startup import StartupManager
from shutdown import ShutdownManager
from routes import setup_routes

# Configure logging
main_config = get_config()
logging.basicConfig(
    level=logging.INFO if main_config.server.debug else logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Set specific loggers to reduce noise
logging.getLogger('improved_turkish_content_manager').setLevel(logging.WARNING)
logging.getLogger('TurkishMorphAnalyzer').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Global managers and services
startup_manager = StartupManager()
shutdown_manager = None
app_services = {}

# Initialize services
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager with modular startup/shutdown"""
    global shutdown_manager, app_services
    
    try:
        # Initialize all services using the startup manager
        app_services = await startup_manager.initialize_services()
        
        # Setup WebSocket middleware after app is created
        await startup_manager._initialize_websocket_manager(app)
        
        # Create shutdown manager with initialized services list
        shutdown_manager = ShutdownManager(startup_manager.get_initialized_services())
        
        # Setup additional routes with initialized services
        setup_routes(app, app_services)
        logger.info("🛤️ Additional routes setup completed")
        
        logger.info("✅ All services initialized successfully")
        
        # Application is running
        yield
        
    except Exception as e:
        logger.error(f"❌ Application startup failed: {e}")
        raise
    finally:
        # Shutdown sequence using shutdown manager
        if shutdown_manager:
            await shutdown_manager.cleanup_services(
                model_manager=app_services.get('model_manager'),
                cache_manager_available=app_services.get('cache_manager_available')
            )

# Create FastAPI application
def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    app = FastAPI(
        title="MEFAPEX AI Chatbot",
        description="Advanced AI-powered chatbot with PostgreSQL support",
        version="2.2.0",
        docs_url="/docs",  # Always enable docs
        redoc_url="/redoc",  # Always enable redoc
        openapi_url="/openapi.json",  # Ensure OpenAPI URL is set
        lifespan=lifespan
    )

    # Setup middleware using startup manager
    startup_manager.setup_middleware(app)
    
    # Setup basic routes using startup manager (API routers and static files)
    startup_manager.setup_routes(app)
    
    return app

# Create the application instance
app = create_app()

# Routes will be set up during lifespan startup instead of using deprecated @app.on_event

# =============================================================================
# APPLICATION STARTUP
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"🚀 Starting MEFAPEX Chatbot on {main_config.server.host}:{main_config.server.port}")
    logger.info(f"🔧 Debug mode: {main_config.server.debug}")
    logger.info(f"🗄️ Database: PostgreSQL ({main_config.database.host}:{main_config.database.port})")
    
    uvicorn.run(
        "main:app",
        host=main_config.server.host,
        port=main_config.server.port,
        reload=False,  # Disable reload to fix connection issues
        log_level="info" if main_config.server.debug else "warning"
    )
