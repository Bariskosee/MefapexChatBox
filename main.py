"""
🚀 MEFAPEX AI Chatbot - Main Application
Clean, modular FastAPI application with proper separation of concerns
"""
import logging
import asyncio
from contextlib import asynccontextmanager

# Import configuration - UNIFIED SYSTEM
from core.configuration import get_config
from core.app_factory import ApplicationFactory

# Initialize unified configuration
config = get_config()

# Configure logging
logging.basicConfig(
    level=logging.INFO if config.server.debug else logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app):
    """Application lifespan management"""
    logger.info("🚀 Starting MEFAPEX Chatbot...")
    
    # Startup
    try:
        # Initialize services through factory
        factory = ApplicationFactory()
        await factory._initialize_services()
        logger.info("✅ Services initialized successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise
    finally:
        # Shutdown
        logger.info("🛑 Shutting down MEFAPEX Chatbot...")

def create_app():
    """Create FastAPI application using factory pattern"""
    try:
        factory = ApplicationFactory()
        app = factory.create_app()
        logger.info("✅ Application created successfully")
        return app
    except Exception as e:
        logger.error(f"❌ Application creation failed: {e}")
        raise

# Create the FastAPI application
app = create_app()

if __name__ == "__main__":
    import uvicorn
    
    logger.info("🌟 Starting MEFAPEX Chatbot server...")
    logger.info(f"📊 Environment: {config.environment.value}")
    logger.info(f"🐛 Debug mode: {config.server.debug}")
    logger.info(f"🌐 Server will run on: {config.server.host}:{config.server.port}")
    
    uvicorn.run(
        "main:app",
        host=config.server.host,
        port=config.server.port,
        reload=config.server.debug,
        log_level="debug" if config.server.debug else "info"
    )
