"""
🚀 MEFAPEX AI Chatbot - Main Application
Clean, modular FastAPI application with proper separation of concerns
"""
import logging
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Import configuration
from config import config

# Import middleware
from middleware import SecurityHeadersMiddleware, RateLimitMiddleware, LoggingMiddleware, RateLimiter

# Import API routes
from api.auth import router as auth_router, set_rate_limiter as set_auth_rate_limiter
from api.chat import router as chat_router, set_rate_limiter as set_chat_rate_limiter
from api.health import router as health_router

# Import core services
from database_manager import db_manager
from model_manager import model_manager
from websocket_manager import websocket_manager, message_handler
from auth_service import init_auth_service

# Configure logging
logging.basicConfig(
    level=logging.INFO if config.DEBUG_MODE else logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize services
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("🚀 Starting MEFAPEX AI Chatbot")
    
    try:
        # Initialize database
        logger.info("🔥 Initializing database...")
        if hasattr(db_manager, 'initialize'):
            await db_manager.initialize()
        
        # Initialize authentication service
        logger.info("🔐 Initializing authentication...")
        init_auth_service(secret_key=config.SECRET_KEY, environment=config.ENVIRONMENT)
        
        # Warm up models
        logger.info("🧠 Warming up AI models...")
        if hasattr(model_manager, 'warmup_models'):
            model_manager.warmup_models()
        
        # Start memory monitoring if available
        try:
            from memory_monitor import setup_memory_monitoring
            setup_memory_monitoring()
            logger.info("🧠 Memory monitoring enabled")
        except ImportError:
            logger.info("Memory monitoring not available")
        
        logger.info("✅ Application startup completed")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🔄 Shutting down MEFAPEX AI Chatbot")
    # Add any cleanup code here

# Create FastAPI application
app = FastAPI(
    title="MEFAPEX AI Chatbot",
    description="Advanced AI-powered chatbot with multi-model support",
    version="2.0.0",
    docs_url="/docs" if config.DEBUG_MODE else None,
    redoc_url="/redoc" if config.DEBUG_MODE else None,
    lifespan=lifespan
)

# Initialize rate limiter
rate_limiter = RateLimiter(
    max_requests_per_minute=config.RATE_LIMIT_REQUESTS,
    max_chat_requests_per_minute=config.RATE_LIMIT_CHAT
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
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Trusted host middleware for production
if config.ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["mefapex.com", "www.mefapex.com", "api.mefapex.com"]
    )

# Include API routers
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(health_router)

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Root endpoint
@app.get("/")
async def read_root():
    """Serve the main chat interface"""
    return FileResponse("static/index.html", media_type="text/html; charset=utf-8")

# WebSocket endpoint for real-time chat
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time communication"""
    try:
        # Connect user
        await websocket_manager.connect(websocket, user_id, f"user_{user_id}")
        
        logger.info(f"🔌 WebSocket connected: {user_id}")
        
        while True:
            # Receive message
            data = await websocket.receive_text()
            
            # Process message through message handler
            await message_handler.handle_message(websocket, user_id, data)
            
    except WebSocketDisconnect:
        logger.info(f"🔌 WebSocket disconnected: {user_id}")
        websocket_manager.disconnect(websocket, user_id)
        
    except Exception as e:
        logger.error(f"WebSocket error for {user_id}: {e}")
        websocket_manager.disconnect(websocket, user_id)

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
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=config.DEBUG_MODE,
        log_level="info" if config.DEBUG_MODE else "warning"
    )
