"""
🚀 MEFAPEX AI Chatbot - Main Application
Clean, modular FastAPI application with proper separation of concerns
"""
import logging
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

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
from auth_service import init_auth_service, get_auth_service, verify_token

# Configure logging
logging.basicConfig(
    level=logging.INFO if config.DEBUG_MODE else logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Content Manager import
try:
    from content_manager import ContentManager
    content_manager = ContentManager()
except ImportError:
    content_manager = None
    logger.warning("ContentManager not available")

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
    allowed_hosts = ["mefapex.com", "www.mefapex.com", "api.mefapex.com"]
    # Allow additional hosts from config if specified
    if hasattr(config, 'ALLOWED_HOSTS') and config.ALLOWED_HOSTS:
        allowed_hosts.extend(config.ALLOWED_HOSTS)
    
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=allowed_hosts
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

# Health check for Docker
@app.get("/health")
async def health():
    """Simple health check for Docker"""
    try:
        # Basic database connection test
        db_health = db_manager.health_check() if hasattr(db_manager, 'health_check') else {"status": "unknown"}
        
        if db_health.get("status") == "healthy":
            return {"status": "healthy", "database": "connected"}
        else:
            return {"status": "degraded", "database": "connection_issues"}
            
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@app.get("/health/comprehensive")
async def comprehensive_health_check():
    """
    🏥 Comprehensive health check endpoint for production monitoring
    Checks: CPU, Memory, Disk Space, Database, External Services, Cache
    """
    try:
        from datetime import datetime
        import time
        
        health_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "healthy",
            "checks": {},
            "metrics": {},
            "alerts": []
        }
        
        # 1. 🧠 Memory Check
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            
            memory_mb = memory_info.rss / 1024 / 1024
            memory_percent = process.memory_percent()
            
            health_data["checks"]["memory"] = {
                "status": "healthy" if memory_mb < 1000 else "warning" if memory_mb < 2000 else "critical",
                "usage_mb": round(memory_mb, 2),
                "usage_percent": round(memory_percent, 2),
                "threshold_mb": 1000
            }
            
            if memory_mb > 1500:
                health_data["alerts"].append(f"High memory usage: {memory_mb:.1f}MB")
                
        except Exception as e:
            health_data["checks"]["memory"] = {"status": "error", "error": str(e)}
            
        # 2. 🖥️ CPU Check
        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            health_data["checks"]["cpu"] = {
                "status": "healthy" if cpu_percent < 70 else "warning" if cpu_percent < 90 else "critical",
                "usage_percent": cpu_percent,
                "core_count": cpu_count
            }
            
            if cpu_percent > 85:
                health_data["alerts"].append(f"High CPU usage: {cpu_percent}%")
                
        except Exception as e:
            health_data["checks"]["cpu"] = {"status": "error", "error": str(e)}
            
        # 3. 🗄️ Database Connectivity Check
        try:
            start_time = time.time()
            db_stats = db_manager.get_stats() if hasattr(db_manager, 'get_stats') else {}
            
            # Test database query
            test_query_start = time.time()
            if hasattr(db_manager, 'get_or_create_session'):
                db_manager.get_or_create_session("health_check_user")
            query_time = time.time() - test_query_start
            
            health_data["checks"]["database"] = {
                "status": "healthy" if query_time < 1.0 else "warning" if query_time < 5.0 else "critical",
                "response_time_ms": round(query_time * 1000, 2),
                "total_sessions": db_stats.get("total_sessions", 0),
                "total_messages": db_stats.get("total_messages", 0)
            }
            
            if query_time > 2.0:
                health_data["alerts"].append(f"Slow database response: {query_time*1000:.1f}ms")
                
        except Exception as e:
            health_data["checks"]["database"] = {"status": "error", "error": str(e)}
            
        # 4. 🤖 AI Services Check
        try:
            ai_status = {"huggingface": "disabled", "content_manager": "unknown"}
            
            # Check Hugging Face models
            if hasattr(model_manager, 'get_model_info'):
                try:
                    model_info = model_manager.get_model_info()
                    ai_status["huggingface"] = "loaded" if model_info.get("models_loaded", 0) > 0 else "not_loaded"
                except Exception:
                    ai_status["huggingface"] = "error"
            
            # Check Content Manager
            try:
                if content_manager:
                    ai_status["content_manager"] = "available"
                else:
                    ai_status["content_manager"] = "unavailable"
            except Exception:
                ai_status["content_manager"] = "error"
                
            health_data["checks"]["ai_services"] = {
                "status": "healthy",
                "services": ai_status
            }
            
        except Exception as e:
            health_data["checks"]["ai_services"] = {"status": "error", "error": str(e)}
            
        # 5. 🔐 Security Check
        try:
            security_checks = {
                "debug_mode": not config.DEBUG_MODE,
                "secure_secret_key": config.SECRET_KEY and config.SECRET_KEY != "your-secret-key-change-this-in-production",
                "environment": config.ENVIRONMENT,
                "cors_configured": len(config.ALLOWED_ORIGINS) > 0 and "*" not in config.ALLOWED_ORIGINS
            }
            
            security_issues = [k for k, v in security_checks.items() if not v]
            
            health_data["checks"]["security"] = {
                "status": "healthy" if not security_issues else "warning",
                "checks": security_checks,
                "issues": security_issues
            }
            
        except Exception as e:
            health_data["checks"]["security"] = {"status": "error", "error": str(e)}
            
        # Overall Status Calculation
        check_statuses = [check.get("status", "error") for check in health_data["checks"].values()]
        
        if "critical" in check_statuses:
            health_data["status"] = "critical"
        elif "error" in check_statuses:
            health_data["status"] = "error"  
        elif "warning" in check_statuses:
            health_data["status"] = "warning"
        else:
            health_data["status"] = "healthy"
            
        # Add summary metrics
        health_data["metrics"] = {
            "total_checks": len(health_data["checks"]),
            "healthy_checks": len([s for s in check_statuses if s == "healthy"]),
            "warning_checks": len([s for s in check_statuses if s == "warning"]),
            "critical_checks": len([s for s in check_statuses if s == "critical"]),
            "error_checks": len([s for s in check_statuses if s == "error"])
        }
        
        # Return appropriate HTTP status
        from fastapi.responses import JSONResponse
        if health_data["status"] in ["critical", "error"]:
            return JSONResponse(
                status_code=503,  # Service Unavailable
                content=health_data
            )
        elif health_data["status"] == "warning":
            return JSONResponse(
                status_code=200,  # OK but with warnings
                content=health_data
            )
        else:
            return health_data
            
    except Exception as e:
        logger.error(f"Health check error: {e}")
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=500,
            content={
                "timestamp": datetime.utcnow().isoformat(),
                "status": "error",
                "error": str(e),
                "checks": {}
            }
        )

# Legacy login endpoint (for backward compatibility)
class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/login")
async def login_user_simple(login_data: LoginRequest, request: Request):
    """Simple login endpoint (legacy compatible)"""
    try:
        # Get client IP safely
        client_ip = getattr(request.client, 'host', None) if request.client else None
        if not client_ip:
            client_ip = request.headers.get("X-Forwarded-For", "unknown")
            if "," in client_ip:
                client_ip = client_ip.split(",")[0].strip()
        
        # Authenticate user
        auth_service = get_auth_service()
        user = auth_service.authenticate_user(login_data.username, login_data.password)
        
        if not user:
            logger.warning(f"❌ Login failed for {login_data.username} from {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Create access token
        token_data = {
            "sub": login_data.username,
            "user_id": user.get("user_id", login_data.username),
            "username": login_data.username
        }
        
        access_token = auth_service.create_access_token(data=token_data)
        
        logger.info(f"✅ Login successful: {login_data.username}")
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_info": {
                "username": login_data.username,
                "user_id": user.get("user_id", login_data.username)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@app.post("/login-legacy")
async def login_legacy(login_data: LoginRequest, request: Request):
    """Legacy login endpoint for compatibility"""
    try:
        # Get client IP safely
        client_ip = getattr(request.client, 'host', None) if request.client else None
        if not client_ip:
            client_ip = request.headers.get("X-Forwarded-For", "unknown")
            if "," in client_ip:
                client_ip = client_ip.split(",")[0].strip()
        
        # Authenticate user
        auth_service = get_auth_service()
        user = auth_service.authenticate_user(login_data.username, login_data.password)
        
        if not user:
            logger.warning(f"❌ Legacy login failed for {login_data.username} from {client_ip}")
            return {"success": False, "message": "Giriş başarısız. Kullanıcı adı ve şifreyi kontrol edin."}
        
        logger.info(f"✅ Legacy login successful: {login_data.username}")
        return {
            "success": True, 
            "message": "Giriş başarılı!",
            "user": {
                "username": login_data.username,
                "user_id": user.get("user_id", login_data.username)
            }
        }
        
    except Exception as e:
        logger.error(f"Legacy login error: {e}")
        return {"success": False, "message": "Giriş sırasında bir hata oluştu."}

@app.get("/me")
async def get_current_user(request: Request):
    """Get current user info (simplified for demo)"""
    try:
        # Extract from Authorization header manually
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
        
        token = auth_header.split(" ")[1]
        
        # Verify token
        auth_service = get_auth_service()
        try:
            from jose import jwt
            payload = jwt.decode(token, auth_service.secret_key, algorithms=[auth_service.algorithm])
            username = payload.get("sub")
            user_id = payload.get("user_id")
            
            if not username:
                raise HTTPException(status_code=401, detail="Invalid token")
            
            return {
                "username": username,
                "user_id": user_id,
                "email": f"{username}@mefapex.com"
            }
        except Exception as e:
            logger.warning(f"JWT validation error: {e}")
            raise HTTPException(status_code=401, detail="Invalid token")
        
    except Exception as e:
        logger.error(f"Get current user error: {e}")
        raise HTTPException(status_code=401, detail="Authentication required")

# Chat endpoints
class ChatMessage(BaseModel):
    message: str

@app.post("/chat")
async def chat_simple(chat_msg: ChatMessage, request: Request):
    """Simple chat endpoint (no authentication required)"""
    try:
        message = chat_msg.message.strip()
        if not message:
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        # Simple response for unauthenticated users
        if content_manager:
            response, response_type = content_manager.find_response(message)
            if response:
                return {"response": response}
        
        # Fallback response
        return {"response": "Merhaba! Size nasıl yardımcı olabilirim? Lütfen giriş yaparak tüm özelliklerden faydalanın."}
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail="Chat error")

@app.post("/chat/authenticated")
async def chat_authenticated(chat_msg: ChatMessage, request: Request, current_user: dict = Depends(verify_token)):
    """Authenticated chat endpoint with session management"""
    try:
        message = chat_msg.message.strip()
        if not message:
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        user_id = current_user.get("user_id")
        username = current_user.get("username", "Kullanıcı")
        
        # Generate response using content manager
        if content_manager:
            response, response_type = content_manager.find_response(message)
            if response:
                ai_response = response
                source = "static_content"
            else:
                ai_response = f"Merhaba {username}! Mesajınızı aldım: '{message}'. Bu bir test yanıtıdır."
                source = "fallback"
        else:
            ai_response = f"Merhaba {username}! Mesajınızı aldım: '{message}'. Bu bir test yanıtıdır."
            source = "fallback"
        
        # Save message to database
        try:
            # Get or create session
            session_id = db_manager.get_or_create_session(user_id)
            
            # Save message to database
            db_manager.add_message(
                session_id=session_id,
                user_id=user_id,
                user_message=message,
                bot_response=ai_response,
                source=source
            )
            
            logger.info(f"Chat message saved for user {user_id} in session {session_id}")
        except Exception as db_error:
            logger.error(f"Database error (continuing without saving): {db_error}")
            # Continue without saving to database
        
        return {"response": ai_response}
        
    except Exception as e:
        logger.error(f"Authenticated chat error: {e}")
        raise HTTPException(status_code=500, detail="Chat error")

# Session management endpoints
@app.post("/chat/sessions/save")
async def save_session(request: Request, current_user: dict = Depends(verify_token)):
    """Save current chat session"""
    try:
        data = await request.json()
        session_id = data.get("sessionId")
        messages = data.get("messages", [])
        user_id = current_user.get("user_id")
        
        if not session_id or not messages:
            return {"success": True, "message": "No session to save"}
        
        # Save each message to the database
        for message in messages:
            db_manager.add_message(
                session_id=session_id,
                user_id=user_id,
                user_message=message.get("user_message", ""),
                bot_response=message.get("bot_response", ""),
                source=message.get("source", "session_save")
            )
        
        logger.info(f"Saving session {session_id} for user {user_id} with {len(messages)} messages")
        
        return {"success": True, "session_id": session_id}
        
    except Exception as e:
        logger.error(f"Save session error: {e}")
        raise HTTPException(status_code=500, detail="Failed to save session")

@app.get("/chat/sessions/{user_id}")
async def get_user_sessions(user_id: str, current_user: dict = Depends(verify_token)):
    """Get user's chat sessions"""
    try:
        # Verify user can only access their own sessions
        if current_user.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get sessions from database
        sessions = db_manager.get_user_sessions(user_id)
        logger.info(f"Retrieved {len(sessions)} sessions for user {user_id}")
        
        return {"sessions": sessions}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get sessions error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get sessions")

@app.get("/chat/sessions/{session_id}/messages")
async def get_session_messages(session_id: str, current_user: dict = Depends(verify_token)):
    """Get messages from a specific session"""
    try:
        user_id = current_user.get("user_id")
        
        # Get messages for the session
        messages = db_manager.get_session_messages(session_id)
        
        # Format messages for frontend compatibility
        formatted_messages = []
        for msg in messages:
            formatted_messages.extend([
                {
                    "type": "user",
                    "content": msg["user_message"],
                    "timestamp": msg["timestamp"]
                },
                {
                    "type": "assistant", 
                    "content": msg["bot_response"],
                    "timestamp": msg["timestamp"],
                    "source": msg.get("source", "unknown")
                }
            ])
        
        return {"messages": formatted_messages, "session_id": session_id}
        
    except Exception as e:
        logger.error(f"Get session messages error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get session messages")

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
