"""
🚀 OPTIMIZED MAIN APPLICATION
Modular FastAPI application with advanced architecture
"""

import os
import sys
import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

# Add the current directory to the Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import uvicorn

# Import routers
from routers import auth, chat, health

# Import services
from services.ai_service import get_ai_service
from services.cache_service import init_cache_service
from services.performance_monitor import init_performance_monitor, get_performance_monitor
from services.websocket_service import init_websocket_manager, get_websocket_manager
from database_manager import get_database_manager

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

import os
import sys
import logging
import secrets
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# Import our modular components
from routers import auth, chat, health
from services.ai_service import LazyAIService
from database_manager import DatabaseManager
from websocket_manager import websocket_manager, message_handler

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

import time

# � ENVIRONMENT CONFIGURATION
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DEBUG_MODE = os.getenv("DEBUG", "false").lower() == "true"

# 🔐 SECURITY CONFIGURATION
import secrets
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY or SECRET_KEY == "your-secret-key-change-this-in-production":
    SECRET_KEY = secrets.token_urlsafe(32)
    logger.warning("🔒 Generated new SECRET_KEY. Set SECRET_KEY in environment for production!")

# 🔐 PRODUCTION SECURITY CHECKS
if ENVIRONMENT == "production" and DEBUG_MODE:
    logger.error("🚨 SECURITY ALERT: DEBUG mode is enabled in production!")
    raise ValueError(
        "DEBUG mode must be disabled in production. Set DEBUG=False in environment variables."
    )

# ⚙️ AI CONFIGURATION
AI_CONFIG = {
    'USE_OPENAI': os.getenv("USE_OPENAI", "false").lower() == "true",
    'USE_HUGGINGFACE': os.getenv("USE_HUGGINGFACE", "true").lower() == "true",
    'OPENAI_API_KEY': os.getenv("OPENAI_API_KEY"),
}

# 🗄️ DATABASE CONFIGURATION
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./mefapex.db")
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))

# 🌐 CORS CONFIGURATION
cors_origins = os.getenv("CORS_ORIGINS", "").split(",") if os.getenv("CORS_ORIGINS") else ["*"]

# Global components (will be initialized in lifespan)
db_manager = None
qdrant_client = None
ai_service = None
memory_monitor = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("🚀 Starting MefapexChatBox Optimized Application...")
    
    try:
        # Initialize core services
        logger.info("📊 Initializing services...")
        
        # Initialize cache service
        cache_service = init_cache_service(
            max_size=1000,
            default_ttl=3600,
            persist_file="cache.json"
        )
        
        # Initialize performance monitor
        performance_monitor = init_performance_monitor(
            collection_interval=10,
            retention_hours=24
        )
        
        # Initialize WebSocket manager
        websocket_manager = init_websocket_manager(
            heartbeat_interval=30,
            message_history_size=100
        )
        
        # Start background services
        await performance_monitor.start_monitoring()
        await websocket_manager.start_background_tasks()
        
        # Initialize database
        db_manager = get_database_manager()
        db_manager.init_database()
        
        # Warm up AI service
        ai_service = get_ai_service()
        await ai_service.warmup()
        
        logger.info("✅ All services initialized successfully!")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Startup error: {e}")
        raise
    finally:
        logger.info("🛑 Shutting down application...")
        
        # Cleanup services
        try:
            performance_monitor = get_performance_monitor()
            await performance_monitor.stop_monitoring()
            
            websocket_manager = get_websocket_manager()
            await websocket_manager.stop_background_tasks()
            
            logger.info("✅ Services shutdown completed")
        except Exception as e:
            logger.error(f"❌ Shutdown error: {e}")

# 🚀 CREATE FASTAPI APP
app = FastAPI(
    title="MEFAPEX ChatBot API",
    description="AI-powered chatbot for MEFAPEX factory management",
    version="2.0.0",
    debug=DEBUG_MODE,
    lifespan=lifespan
)

# 🛡️ SECURITY MIDDLEWARE
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' ws: wss:; "
            "object-src 'none'; "
            "base-uri 'self';"
        )
        
        # HSTS header for HTTPS
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response

# 📊 MONITORING MIDDLEWARE
class MonitoringMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = datetime.utcnow()
        
        response = await call_next(request)
        
        process_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Log slow requests
        if process_time > 2.0:  # Log requests taking more than 2 seconds
            logger.warning(f"Slow request: {request.method} {request.url} took {process_time:.2f}s")
        
        response.headers["X-Process-Time"] = str(process_time)
        return response

# 🔧 ADD MIDDLEWARE
# Middleware
@app.middleware("http")
async def performance_middleware(request: Request, call_next):
    """Performance monitoring middleware"""
    start_time = time.time()
    
    # Process request
    response = await call_next(request)
    
    # Record performance metrics
    duration = time.time() - start_time
    performance_monitor = get_performance_monitor()
    
    performance_monitor.record_request_time(
        endpoint=f"{request.method} {request.url.path}",
        duration=duration,
        status_code=response.status_code
    )
    
    # Add performance headers
    response.headers["X-Process-Time"] = str(round(duration, 4))
    
    return response

# 🌐 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 📁 STATIC FILES
app.mount("/static", StaticFiles(directory="static"), name="static")

# 🔌 WEBSOCKET
app.mount("/ws", websocket_manager)

# 📍 INCLUDE ROUTERS
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(health.router)

# 🏠 ROOT ENDPOINT
@app.get("/")
async def read_root():
    """Root endpoint with system information"""
    return {
        "message": "🚀 MEFAPEX ChatBot API",
        "version": "2.0.0",
        "environment": ENVIRONMENT,
        "debug": DEBUG_MODE,
        "ai_services": {
            "openai": AI_CONFIG['USE_OPENAI'],
            "huggingface": AI_CONFIG['USE_HUGGINGFACE']
        },
        "docs": "/docs" if DEBUG_MODE else "disabled",
        "timestamp": datetime.utcnow().isoformat()
    }

# 🎯 PERFORMANCE METRICS ENDPOINT
@app.get("/metrics")
async def get_metrics():
    """Get performance metrics"""
    try:
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": (datetime.utcnow() - db_manager.created_at).total_seconds() if db_manager else 0,
            "database": db_manager.get_stats() if db_manager else {},
            "ai_service": ai_service.get_performance_metrics() if ai_service else {},
            "websockets": websocket_manager.get_connection_stats() if websocket_manager else {}
        }
        
        if memory_monitor:
            metrics["memory"] = memory_monitor.get_memory_stats()
        
        return metrics
        
    except Exception as e:
        logger.error(f"Metrics error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to get metrics", "detail": str(e)}
        )

# 🚨 ERROR HANDLERS
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if DEBUG_MODE else "Something went wrong"
        }
    )

# 🎯 FINAL CONFIGURATION
if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"🚀 Starting server on {host}:{port}")
    logger.info(f"🐛 Debug mode: {'ENABLED' if DEBUG_MODE else 'DISABLED'}")
    logger.info(f"🌍 Environment: {ENVIRONMENT}")
    logger.info(f"🤖 AI Services: OpenAI={AI_CONFIG['USE_OPENAI']}, HuggingFace={AI_CONFIG['USE_HUGGINGFACE']}")
    
    uvicorn.run(
        "main_optimized:app",
        host=host,
        port=port,
        reload=DEBUG_MODE,
        log_level="info" if not DEBUG_MODE else "debug",
        access_log=DEBUG_MODE
    )
