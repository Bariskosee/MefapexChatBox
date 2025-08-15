"""
🚀 MEFAPEX AI Chatbot - Unified Version
Clean, modular FastAPI application with configurable database support
"""
import logging
import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from database.interface import DatabaseOperationsMixin
from database.utils import get_database_helper
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Import configuration
from core.configuration import get_config, Environment

# Import middleware
from middleware import SecurityHeadersMiddleware, RateLimitMiddleware, LoggingMiddleware, RateLimiter

# Import API routes
from api.auth import router as auth_router, set_rate_limiter as set_auth_rate_limiter
from api.chat import router as chat_router, set_rate_limiter as set_chat_rate_limiter
from api.health import router as health_router

# Import unified database manager
from database.manager import db_manager

# Import other services
from model_manager import model_manager
from websocket_manager import websocket_manager, message_handler
from auth_service import init_auth_service, get_auth_service, verify_token

# Configure logging
config = get_config()
logging.basicConfig(
    level=logging.INFO if config.server.debug else logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Content Manager import
try:
    from content_manager import ContentManager
    content_manager = ContentManager()
    logger.info("✅ Content manager loaded")
except ImportError:
    content_manager = None
    logger.warning("⚠️ Content manager not available")

# Distributed Cache import
try:
    from distributed_cache import create_distributed_cache
    distributed_cache = create_distributed_cache(config)
    logger.info("✅ Distributed cache initialized")
except ImportError as e:
    distributed_cache = None
    logger.warning(f"⚠️ Distributed cache not available: {e}")

# Global database manager already imported above
# db_manager is available globally from the import

# Initialize services
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("🚀 Starting MEFAPEX AI Chatbot (Unified Version)")
    
    global db_manager
    
    try:
        # Database manager is already initialized in database/manager.py
        logger.info("✅ Database manager ready")
        
        # Test database connection
        health = db_manager.health_check()
        logger.info(f"✅ Database health: {health.get('status', 'unknown')}")
        
        # Initialize authentication service
        logger.info("🔐 Initializing authentication...")
        init_auth_service(secret_key=config.security.secret_key, environment=config.environment.value)
        logger.info("✅ Authentication service initialized")
        
        # Initialize distributed cache
        if distributed_cache and hasattr(distributed_cache, 'initialize'):
            logger.info("🔄 Initializing distributed cache...")
            await distributed_cache.initialize()
            cache_health = await distributed_cache.health_check() if hasattr(distributed_cache, 'health_check') else {'status': 'unknown'}
            logger.info(f"✅ Distributed cache ready: {cache_health}")
        
        # Warm up models
        logger.info("🧠 Warming up AI models...")
        if hasattr(model_manager, 'warmup_models'):
            model_manager.warmup_models()
            logger.info("✅ AI models warmed up")
        
        # Start memory monitoring if available
        try:
            from memory_monitor import setup_memory_monitoring
            setup_memory_monitoring()
            logger.info("🧠 Memory monitoring enabled")
        except ImportError:
            logger.info("Memory monitoring not available")
        
        logger.info("✅ Application startup completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🔄 Shutting down MEFAPEX AI Chatbot")
    
    # Cleanup distributed cache
    if distributed_cache and hasattr(distributed_cache, 'shutdown'):
        try:
            await distributed_cache.shutdown()
            logger.info("✅ Distributed cache shutdown completed")
        except Exception as e:
            logger.error(f"❌ Cache shutdown error: {e}")
    
    # Database manager cleanup is handled automatically
    logger.info("✅ Application shutdown completed")

# Create FastAPI application
app = FastAPI(
    title="MEFAPEX AI Chatbot",
    description="Advanced AI-powered chatbot with PostgreSQL support",
    version="2.2.0",
    docs_url="/docs" if config.server.debug else None,
    redoc_url="/redoc" if config.server.debug else None,
    lifespan=lifespan
)

# Initialize rate limiter
rate_limiter = RateLimiter(
    max_requests_per_minute=config.rate_limit.requests_per_minute,
    max_chat_requests_per_minute=config.rate_limit.chat_requests_per_minute
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
    allow_origins=config.server.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Trusted host middleware for production
if config.environment == Environment.PRODUCTION:
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
        
        # Use the global db_manager for authentication
        user_data = db_manager.authenticate_user(login_data.username)
        
        if user_data and auth_service.verify_password(login_data.password, user_data.get("password_hash") or user_data.get("hashed_password", "")):
            # Update last login
            db_manager.update_last_login(login_data.username)
            
            # Create access token
            token_data = {
                "sub": login_data.username,
                "user_id": user_data.get("user_id", login_data.username),
                "username": login_data.username
            }
            
            access_token = auth_service.create_access_token(data=token_data)
            
            logger.info(f"✅ Login successful: {login_data.username}")
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "user_info": {
                    "username": login_data.username,
                    "user_id": user_data.get("user_id", login_data.username)
                }
            }
        
        logger.warning(f"❌ Login failed for {login_data.username} from {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
        
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
        
        # Use the global db_manager for authentication
        user_data = db_manager.authenticate_user(login_data.username)
        
        if user_data and auth_service.verify_password(login_data.password, user_data.get("password_hash") or user_data.get("hashed_password", "")):
            # Update last login
            db_manager.update_last_login(login_data.username)
            
            logger.info(f"✅ Legacy login successful: {login_data.username}")
            return {
                "success": True, 
                "message": "Giriş başarılı!",
                "user": {
                    "username": login_data.username,
                    "user_id": user_data.get("user_id", login_data.username)
                }
            }
        
        logger.warning(f"❌ Legacy login failed for {login_data.username} from {client_ip}")
        return {"success": False, "message": "Giriş başarısız. Kullanıcı adı ve şifreyi kontrol edin."}
        
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
        
        # Save message to database with unified helper
        db_helper = get_database_helper(db_manager)
        save_result = db_helper.save_chat_interaction(
            user_id=user_id,
            message=message,
            response=ai_response,
            source=source
        )
        
        if save_result["success"]:
            logger.info(f"Chat message saved for user {user_id} in session {save_result['session_id']}")
        else:
            logger.error(f"Database save failed: {save_result.get('error', 'Unknown error')}")
        
        return {"response": ai_response}
        
    except Exception as e:
        logger.error(f"Authenticated chat error: {e}")
        raise HTTPException(status_code=500, detail="Chat error")

@app.post("/chat/sessions/save")
async def save_session(request: Request, current_user: dict = Depends(verify_token)):
    """Save current chat session with duplicate prevention"""
    try:
        data = await request.json()
        session_id = data.get("sessionId")
        messages = data.get("messages", [])
        user_id = current_user.get("user_id")
        
        logger.info(f"📝 Save session request: {session_id}, {len(messages)} messages for user {user_id}")
        
        if not session_id:
            return {"success": True, "message": "No session ID provided"}
        
        if not messages:
            logger.info("No messages to save")
            return {"success": True, "message": "No messages to save"}
        
        # Check if this is a batch save or single message save
        is_batch_save = len(messages) > 1
        
        # Save messages to database with duplicate prevention
        saved_count = 0
        for message in messages:
            try:
                user_msg = message.get("user_message", "")
                bot_resp = message.get("bot_response", "")
                
                # Skip empty messages
                if not user_msg and not bot_resp:
                    continue
                
                # Create a simple hash to detect duplicates
                import hashlib
                message_hash = hashlib.md5(f"{session_id}:{user_msg}:{bot_resp}".encode()).hexdigest()
                
                # Check if this exact message already exists in this session
                existing_messages = db_manager.get_session_messages(session_id)
                message_exists = False
                
                for existing in existing_messages:
                    existing_hash = hashlib.md5(
                        f"{session_id}:{existing.get('message', '')}:{existing.get('response', '')}"
                        .encode()
                    ).hexdigest()
                    if existing_hash == message_hash:
                        message_exists = True
                        logger.info(f"⚠️ Duplicate message detected, skipping: {message_hash[:8]}")
                        break
                
                if not message_exists:
                    db_manager.add_message(
                        session_id=session_id,
                        user_id=user_id,
                        user_message=user_msg,
                        bot_response=bot_resp,
                        source=message.get("source", "session_save")
                    )
                    saved_count += 1
                    logger.info(f"✅ Saved new message: {message_hash[:8]}")
                
            except Exception as msg_error:
                logger.warning(f"Failed to save individual message: {msg_error}")
                # Continue with other messages
        
        # 🎯 CONVERSATION HISTORY MANAGEMENT
        # Clean up old conversations to maintain limit of 15
        try:
            # Delete old sessions beyond the limit of 15
            deleted_count = db_manager.delete_old_sessions(user_id, keep_count=15)
            if deleted_count > 0:
                logger.info(f"🧹 Cleaned up {deleted_count} old sessions for user {user_id}")
        except Exception as cleanup_error:
            logger.warning(f"⚠️ Session cleanup failed: {cleanup_error}")
            # Don't fail the save operation if cleanup fails
        
        logger.info(f"✅ Saved session {session_id} with {saved_count}/{len(messages)} messages")
        
        return {"success": True, "session_id": session_id, "messages_saved": saved_count}
        
    except Exception as e:
        logger.error(f"❌ Save session error: {e}")
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
                    "content": msg.get("message", msg.get("user_message", "")),
                    "timestamp": msg.get("timestamp", msg.get("created_at"))
                },
                {
                    "type": "assistant", 
                    "content": msg.get("response", msg.get("bot_response", "")),
                    "timestamp": msg.get("timestamp", msg.get("created_at")),
                    "source": msg.get("source", "unknown")
                }
            ])
        
        return {"messages": formatted_messages, "session_id": session_id}
        
    except Exception as e:
        logger.error(f"Get session messages error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get session messages")

# Database status endpoint
@app.get("/db/status")
async def get_database_status():
    """Get database connection status"""
    try:
        stats = db_manager.get_stats()
        return {
            "status": "connected",
            "database_type": "PostgreSQL",
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Database status error: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

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

# Cache management endpoints
@app.get("/admin/cache/stats")
async def get_cache_stats(request: Request, user_id: str = Depends(verify_token)):
    """Get comprehensive cache statistics"""
    try:
        if distributed_cache:
            if hasattr(distributed_cache, 'get_stats') and asyncio.iscoroutinefunction(distributed_cache.get_stats):
                stats = await distributed_cache.get_stats()
            elif hasattr(distributed_cache, 'get_stats'):
                stats = distributed_cache.get_stats()
            else:
                stats = {"error": "No stats method available"}
            return {"status": "success", "cache_stats": stats}
        else:
            return {"status": "error", "message": "Cache not available"}
    except Exception as e:
        logger.error(f"Cache stats error: {e}")
        return {"status": "error", "error": str(e)}

@app.post("/admin/cache/clear")
async def clear_cache(request: Request, user_id: str = Depends(verify_token)):
    """Clear all cache entries"""
    try:
        if distributed_cache:
            if hasattr(distributed_cache, 'clear') and asyncio.iscoroutinefunction(distributed_cache.clear):
                await distributed_cache.clear()
            elif hasattr(distributed_cache, 'clear'):
                distributed_cache.clear()
            else:
                return {"status": "error", "message": "No clear method available"}
            logger.info(f"🗑️ Cache cleared by admin user: {user_id}")
            return {"status": "success", "message": "Cache cleared successfully"}
        else:
            return {"status": "error", "message": "Cache not available"}
    except Exception as e:
        logger.error(f"Cache clear error: {e}")
        return {"status": "error", "error": str(e)}

@app.get("/admin/cache/health")
async def get_cache_health(request: Request, user_id: str = Depends(verify_token)):
    """Check cache layer health"""
    try:
        if distributed_cache and hasattr(distributed_cache, 'health_check'):
            health = await distributed_cache.health_check()
            return {"status": "success", "cache_health": health}
        else:
            return {"status": "success", "cache_health": {"local_cache": True, "redis_cache": False}}
    except Exception as e:
        logger.error(f"Cache health check error: {e}")
        return {"status": "error", "error": str(e)}

# Health check endpoint for monitoring
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        db_status = "ok"
        try:
            stats = db_manager.get_stats()
        except Exception as e:
            db_status = f"error: {str(e)}"
        
        return {
            "status": "healthy",
            "version": "2.2.0",
            "database": db_status,
            "timestamp": "2025-08-13T00:00:00Z"
        }
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {"status": "unhealthy", "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"🚀 Starting MEFAPEX Chatbot on {config.server.host}:{config.server.port}")
    logger.info(f"🔧 Debug mode: {config.server.debug}")
    logger.info(f"🗄️ Database: PostgreSQL ({config.database.host}:{config.database.port})")
    
    uvicorn.run(
        "main:app",
        host=config.server.host,
        port=config.server.port,
        reload=False,  # Disable reload to fix connection issues
        log_level="info" if config.server.debug else "warning"
    )
