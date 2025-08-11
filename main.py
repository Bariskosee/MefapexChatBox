from fastapi import FastAPI, HTTPException, Depends, status, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, EmailStr
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
import openai
import os
import time
import uuid
import shutil
import psutil
from dotenv import load_dotenv
import logging
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from content_manager import ContentManager
import uuid
import json
import asyncio
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

# Import unified authentication service
from auth_service import init_auth_service, get_auth_service, verify_token

# Import optimized components
from database_manager import ProductionDatabaseManager, create_database_manager
from model_manager import model_manager
from response_cache import response_cache
from websocket_manager import websocket_manager, message_handler
from security_config import security_config, input_validator

# Load environment variables
load_dotenv()

# Configure logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import production monitoring (conditionally)
try:
    from memory_monitor import memory_monitor, setup_memory_monitoring
    MEMORY_MONITORING_AVAILABLE = True
except ImportError:
    MEMORY_MONITORING_AVAILABLE = False
    logger.warning("Memory monitoring not available - install psutil for production monitoring")

# 🔒 PRODUCTION SECURITY CONFIGURATION
DEBUG_MODE = os.getenv("DEBUG", "False").lower() == "true"
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Configure logging based on environment
if ENVIRONMENT == "production":
    logging.basicConfig(
        level=logging.WARNING,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('/var/log/mefapex/app.log'),
            logging.StreamHandler()
        ]
    )
else:
    logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

# 🔐 AUTHENTICATION CONFIGURATION
# Initialize unified authentication service
SECRET_KEY = os.getenv("SECRET_KEY")
auth_service = init_auth_service(secret_key=SECRET_KEY, environment=ENVIRONMENT)

# 🎯 HYBRID CONFIGURATION
USE_OPENAI = os.getenv("USE_OPENAI", "false").lower() == "true"
USE_HUGGINGFACE = os.getenv("USE_HUGGINGFACE", "true").lower() == "true"

# Security check for production
if ENVIRONMENT == "production" and DEBUG_MODE:
    logger.error("🚨 SECURITY ALERT: DEBUG mode is enabled in production!")
    raise RuntimeError(
        "DEBUG mode must be disabled in production. Set DEBUG=False in environment variables."
    )

# Additional production checks
if ENVIRONMENT == "production":
    if not os.getenv("OPENAI_API_KEY") and USE_OPENAI:
        logger.warning("⚠️ OpenAI API key not set in production environment")

logger.info(f"🔧 Environment: {ENVIRONMENT}")
logger.info(f"🐛 Debug mode: {'ENABLED' if DEBUG_MODE else 'DISABLED'}")

# Password hashing - Use auth_service
# Removed: pwd_context and security - now handled by auth_service

# 🔒 SECURE USER STORAGE - Database-based with proper validation
users_db = {}
chat_sessions = {}

# 🚨 PRODUCTION SECURITY ALERT: Demo user handled by auth_service

# 🗄️ PRODUCTION DATABASE INITIALIZATION
logger.info(f"🔧 Environment: {ENVIRONMENT}")
logger.info(f"🐛 Debug mode: {'ENABLED' if DEBUG_MODE else 'DISABLED'}")

# Initialize production database manager
db_manager = ProductionDatabaseManager()

async def initialize_database():
    """Initialize database asynchronously"""
    success = await db_manager.initialize()
    if not success:
        logger.error("❌ Failed to initialize database")
        raise RuntimeError("Database initialization failed")
    
    # Validate database integrity
    integrity_check = await db_manager.validate_data_integrity()
    if not integrity_check.get("validation_passed", False):
        logger.warning("⚠️ Database integrity issues detected")
        for issue in integrity_check.get("issues", []):
            logger.warning(f"  - {issue}")

# For backward compatibility, create sync wrapper
class LegacyDatabaseWrapper:
    """Wrapper to maintain compatibility with existing sync code"""
    
    def __init__(self, async_manager: ProductionDatabaseManager):
        self.async_manager = async_manager
        self.created_at = datetime.utcnow()
    
    @property
    def db_path(self):
        return self.async_manager.db_path
    
    def get_or_create_session(self, user_id: str, force_new: bool = False) -> str:
        return self.async_manager.get_or_create_session(user_id, force_new)
    
    def get_current_session(self, user_id: str):
        return self.async_manager.get_current_session(user_id)
    
    def add_message(self, session_id: str, user_id: str, message: str, response: str, source: str = "ai"):
        return self.async_manager.add_message_sync(session_id, user_id, message, response, source)
    
    def get_chat_history(self, user_id: str, limit: int = 20):
        return self.async_manager.get_chat_history(user_id, limit)
    
    def get_stats(self):
        return self.async_manager.get_stats()
    
    def get_session_info(self, session_id: str):
        import asyncio
        return asyncio.run(self.async_manager.get_session(session_id))
    
    def get_chat_sessions_with_history(self, user_id: str, limit: int = 15):
        import asyncio
        return asyncio.run(self.async_manager.get_user_sessions(user_id, limit))
    
    def start_new_session(self, user_id: str) -> str:
        import asyncio
        return asyncio.run(self.async_manager.create_session(user_id))
    
    def clear_chat_history(self, user_id: str):
        # This would need to be implemented in the async manager
        logger.warning("clear_chat_history not implemented in production manager")

# Create legacy wrapper for compatibility - will be replaced after database initialization
legacy_db_manager = None

# 🔒 RATE LIMITING IMPLEMENTATION
class RateLimiter:
    def __init__(self):
        self.requests = defaultdict(list)
        self.chat_requests = defaultdict(list)
        self.max_requests_per_minute = int(os.getenv("RATE_LIMIT_REQUESTS", "200"))
        self.max_chat_requests_per_minute = int(os.getenv("RATE_LIMIT_CHAT", "100"))
        
    def is_allowed(self, client_ip: str, endpoint_type: str = "general") -> bool:
        """Check if request is allowed based on rate limits"""
        now = time.time()
        
        if endpoint_type == "chat":
            # Chat-specific rate limiting
            client_requests = self.chat_requests[client_ip]
            client_requests[:] = [req_time for req_time in client_requests if now - req_time < 60]
            
            if len(client_requests) >= self.max_chat_requests_per_minute:
                return False
            
            client_requests.append(now)
        else:
            # General rate limiting
            client_requests = self.requests[client_ip]
            client_requests[:] = [req_time for req_time in client_requests if now - req_time < 60]
            
            if len(client_requests) >= self.max_requests_per_minute:
                return False
            
            client_requests.append(now)
        
        return True

rate_limiter = RateLimiter()

# 🛡️ SECURITY HEADERS MIDDLEWARE
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
        if request.url.scheme == "https" or os.getenv("FORCE_HTTPS", "false").lower() == "true":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
        # Remove server identification
        if "server" in response.headers:
            del response.headers["server"]
        
        return response

# 🚦 RATE LIMITING MIDDLEWARE
class RateLimitingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        
        # Determine endpoint type
        endpoint_type = "general"
        if request.url.path.startswith("/chat"):
            endpoint_type = "chat"
        
        # Check rate limit
        if not rate_limiter.is_allowed(client_ip, endpoint_type):
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Please try again later.",
                    "retry_after": 60
                },
                headers={"Retry-After": "60"}
            )
        
        return await call_next(request)

app = FastAPI(
    title="MEFAPEX Chatbot API",
    description="Secure AI Chatbot API for MEFAPEX Factory",
    version="2.0.0",
    docs_url="/docs" if ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if ENVIRONMENT != "production" else None,
    openapi_url="/openapi.json" if ENVIRONMENT != "production" else None
)

# 🔒 PRODUCTION CORS CONFIGURATION - STRICT SECURITY WITH ZERO TOLERANCE
# Get allowed origins from environment with ABSOLUTE NO WILDCARDS in production
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000,http://127.0.0.1:8000").split(",")
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# 🚨 ENHANCED SECURITY: Use security_config for CORS validation
cors_origins = security_config.allowed_origins

# Environment-based CORS configuration with ZERO TOLERANCE for wildcards in production
if ENVIRONMENT == "production":
    # 🚨 PRODUCTION SECURITY AUDIT
    if "*" in cors_origins:
        logger.critical("🚨 SECURITY BREACH: Wildcard CORS detected in production!")
        raise RuntimeError(
            "CORS wildcard (*) is FORBIDDEN in production. This is a critical security vulnerability. "
            "Set specific domains in ALLOWED_ORIGINS environment variable."
        )
    
    # Additional production validation
    for origin in cors_origins:
        if not origin.startswith("https://") and origin not in ["http://localhost:8000", "http://127.0.0.1:8000"]:
            logger.warning(f"⚠️ Non-HTTPS origin in production: {origin}")
    
    cors_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    cors_headers = ["accept", "authorization", "content-type", "x-csrf-token", "x-requested-with"]
    allow_credentials = True
    
    if not cors_origins:
        logger.critical("🚨 CRITICAL SECURITY ALERT: No valid CORS origins configured for production!")
        raise RuntimeError(
            "ALLOWED_ORIGINS must be set for production with specific HTTPS domains. "
            "Wildcards (*) and HTTP (except localhost) are FORBIDDEN in production."
        )
    
    # Security audit log
    logger.info(f"🔒 Production CORS origins (validated): {cors_origins}")
    
else:
    # Development CORS (more permissive but still no global wildcards)
    if "*" in cors_origins:
        logger.warning("⚠️ Wildcard CORS detected in development - allowed but not recommended")
    
    cors_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    cors_headers = ["*"]  # More permissive for development
    allow_credentials = True
    
    logger.info(f"🔧 Development CORS origins: {cors_origins}")

# Add security middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitingMiddleware)

# Add Trusted Host middleware for production
if ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware, 
        allowed_hosts=ALLOWED_HOSTS
    )

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=allow_credentials,
    allow_methods=cors_methods,
    allow_headers=cors_headers,
    max_age=600,  # Cache preflight requests for 10 minutes
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Startup event for database and model initialization
@app.on_event("startup")
async def startup_event():
    """Initialize database and warm up models on startup"""
    global legacy_db_manager
    
    logger.info("🚀 Starting MEFAPEX Chatbot API")
    
    try:
        # Initialize database first
        logger.info("🔥 Initializing production database...")
        await initialize_database()
        
        # Create legacy wrapper after database is initialized
        legacy_db_manager = LegacyDatabaseWrapper(db_manager)
        logger.info("✅ Database initialization completed")
        
        # Warm up models for better first-request performance
        logger.info("🔥 Starting model warmup...")
        await startup_warmup()
        logger.info("✅ Model warmup completed")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise
    
    # Start memory monitoring if available
    if MEMORY_MONITORING_AVAILABLE and ENVIRONMENT == "production":
        try:
            setup_memory_monitoring()
            logger.info("🧠 Memory monitoring started")
        except Exception as e:
            logger.warning(f"⚠️ Memory monitoring setup failed: {e}")
    
    logger.info("🔥 MEFAPEX API ready for requests")
    
    logger.info("🔥 MEFAPEX API ready for requests")

logger.info(f"🤖 OpenAI enabled: {USE_OPENAI}")
logger.info(f"🆓 Hugging Face enabled: {USE_HUGGINGFACE}")

# Initialize OpenAI client (if enabled)
if USE_OPENAI:
    try:
        openai.api_key = os.getenv("OPENAI_API_KEY")
        logger.info("✅ OpenAI initialized")
    except Exception as e:
        logger.warning(f"⚠️ OpenAI initialization failed: {e}")
        USE_OPENAI = False

# Initialize Qdrant client
qdrant_client = QdrantClient(
    host=os.getenv("QDRANT_HOST", "localhost"),
    port=int(os.getenv("QDRANT_PORT", 6333))
)

# Initialize ContentManager for static responses
content_manager = ContentManager()

# Warm up models on startup for better first-request performance
async def startup_warmup():
    """Warm up models during application startup"""
    logger.info("🔥 Starting model warmup...")
    try:
        model_manager.warmup_models()
        logger.info("✅ Model warmup completed")
    except Exception as e:
        logger.warning(f"⚠️ Model warmup failed: {e}")
    """Warm up models during application startup"""
    logger.info("🔥 Starting model warmup...")
    try:
        model_manager.warmup_models()
        logger.info("✅ Model warmup completed")
    except Exception as e:
        logger.warning(f"⚠️ Model warmup failed: {e}")

#️ DATA MODELS
class ChatMessage(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    source: str  # "openai", "huggingface", or "database"

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    success: bool
    message: str

# 🆕 NEW MODELS FOR ENHANCED FEATURES
class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UserInDB(BaseModel):
    user_id: str
    username: str
    email: str
    hashed_password: str
    full_name: Optional[str] = None
    created_at: datetime
    is_active: bool = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class ChatSession(BaseModel):
    session_id: str
    user_id: str
    messages: List[Dict]
    created_at: datetime

class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: List[Dict]
    total_messages: int

class ChatSessionResponse(BaseModel):
    session_id: str
    created_at: str
    message_count: int
    last_message_time: str
    first_message_time: str
    messages: List[Dict]
    preview: str

class ChatSessionsResponse(BaseModel):
    user_id: str
    sessions: List[ChatSessionResponse]
    total_sessions: int

# 🔐 AUTHENTICATION UTILITIES - Using unified auth_service
def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validate password strength using auth service"""
    return auth_service.validate_password_strength(password)

def verify_password(plain_password, hashed_password):
    """Verify a password against its hash"""
    return auth_service.verify_password(plain_password, hashed_password)

def get_password_hash(password):
    """Hash a password with enhanced security"""
    return auth_service.get_password_hash(password)

def get_user(username: str):
    """Get user from database"""
    return users_db.get(username)

def authenticate_user(username: str, password: str):
    """Authenticate user credentials"""
    return auth_service.authenticate_user(username, password, users_db)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token with enhanced security"""
    return auth_service.create_access_token(data, expires_delta)

# 🛡️ BRUTE FORCE PROTECTION - Using unified auth_service
# Removed: BruteForceProtection class - now handled by auth_service

async def get_current_user(current_user_data = Depends(verify_token)):
    """Get current authenticated user with enhanced security"""
    
    # Use unified auth service for token verification
    username = current_user_data.get("username")
    user_id = current_user_data.get("user_id")
    
    # Handle demo user
    if username == "demo":
        return {
            "user_id": "demo-user-id",
            "username": "demo",
            "email": "demo@mefapex.com",
            "full_name": "Demo User",
            "created_at": datetime.utcnow(),
            "is_active": True,
            "is_demo": True,
            "rate_limit": "strict"
        }
    
    # Handle regular users
    user = get_user(username=username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
        
    # Check if user is still active
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
        
    return user

def get_user_session(user_id: str, force_new: bool = False, auto_create: bool = True) -> str:
    """
    Get or create user session ID (persistent) with enhanced session management
    
    Args:
        user_id: User identifier
        force_new: Force creation of new session (default: False)
        auto_create: Automatically create session if none exists (default: True)
    
    Returns:
        session_id: Active session ID for the user
    """
    try:
        if auto_create:
            session_id = legacy_db_manager.get_or_create_session(user_id, force_new=force_new)
            logger.debug(f"Session {'created' if force_new else 'retrieved'} for user {user_id}: {session_id}")
            return session_id
        else:
            # Only get existing session, don't create
            existing_session = legacy_db_manager.get_current_session(user_id)
            if existing_session:
                return existing_session
            else:
                logger.warning(f"No existing session found for user {user_id}")
                return None
    except Exception as e:
        logger.error(f"Session management error for user {user_id}: {e}")
        # Fallback: try to create a new session
        try:
            return db_manager.get_or_create_session(user_id, force_new=True)
        except Exception as fallback_error:
            logger.error(f"Fallback session creation failed for user {user_id}: {fallback_error}")
            raise

def add_message_to_session(session_id: str, user_message: str, bot_response: str, source: str, user_id: str = None):
    """
    Add message to chat session with comprehensive security protection
    
    Args:
        session_id: Session identifier (validated UUID)
        user_message: User's input message (validated and sanitized)
        bot_response: Bot's response (validated and sanitized) 
        source: Response source (validated enum)
        user_id: User identifier (validated UUID, optional but recommended)
    """
    try:
        # 🛡️ COMPREHENSIVE INPUT VALIDATION
        if not session_id or not isinstance(session_id, str):
            raise ValueError("Invalid session_id: must be non-empty string")
        
        if not user_message or not isinstance(user_message, str):
            raise ValueError("Invalid user_message: must be non-empty string") 
            
        if not bot_response or not isinstance(bot_response, str):
            raise ValueError("Invalid bot_response: must be non-empty string")
            
        if not source or not isinstance(source, str):
            raise ValueError("Invalid source: must be non-empty string")
        
        # 🔒 SANITIZE AND VALIDATE INPUTS
        session_id = str(session_id).strip()
        user_message = str(user_message).strip()
        bot_response = str(bot_response).strip()
        source = str(source).strip()
        
        # 🔍 SECURITY VALIDATION: Check for malicious content
        is_xss, xss_pattern = input_validator.detect_xss_attempt(user_message)
        if is_xss:
            logger.warning(f"🚨 XSS attempt blocked in user message: {xss_pattern}")
            raise ValueError(f"Invalid content detected: potential XSS attempt")
        
        is_sql_injection, sql_pattern = input_validator.detect_sql_injection(user_message)
        if is_sql_injection:
            logger.warning(f"🚨 SQL injection attempt blocked: {sql_pattern}")
            raise ValueError(f"Invalid content detected: potential SQL injection")
        
        # 📝 MESSAGE VALIDATION
        is_valid_msg, msg_error = input_validator.validate_message(user_message)
        if not is_valid_msg:
            raise ValueError(f"Message validation failed: {msg_error}")
        
        # Validate UUID format for session_id
        import uuid
        try:
            uuid.UUID(session_id)
        except ValueError:
            logger.warning(f"Invalid session_id format: {session_id}")
            raise ValueError("session_id must be valid UUID format")
        
        # Validate user_id if provided
        if user_id is not None:
            user_id = str(user_id).strip()
            if user_id:  # Only validate if not empty
                try:
                    # Allow demo-user-id or UUID format
                    if user_id != "demo-user-id":
                        uuid.UUID(user_id)
                except ValueError:
                    logger.warning(f"Invalid user_id format: {user_id}")
                    raise ValueError("user_id must be valid UUID format or 'demo-user-id'")
        
        # Validate source against allowed values
        allowed_sources = ["openai", "huggingface", "database", "cache", "advanced_ai", "local_ai", "session_save", "fallback", "error"]
        if source not in allowed_sources:
            logger.warning(f"Invalid source: {source}")
            source = "unknown"
        
        # 🧹 CONTENT SANITIZATION
        user_message = input_validator.sanitize_input(user_message)
        bot_response = input_validator.sanitize_input(bot_response)
        
        # 📏 ENHANCED LENGTH VALIDATION  
        max_msg_len = security_config.max_message_length
        if len(user_message) > max_msg_len:
            user_message = user_message[:max_msg_len] + "...[truncated for security]"
            logger.warning(f"User message truncated for session {session_id}")
            
        if len(bot_response) > 5000:
            bot_response = bot_response[:5000] + "...[truncated]"
            logger.warning(f"Bot response truncated for session {session_id}")
        
        # 🔒 SQL INJECTION PROTECTION - Use parameterized queries (handled by DatabaseManager)
        db_manager.add_message(session_id, user_id, user_message, bot_response, source)
        
        logger.debug(f"✅ Message safely added to session {session_id}: user='{user_message[:50]}...', bot='{bot_response[:50]}...', source={source}")
        
    except ValueError as ve:
        logger.error(f"Validation error in add_message_to_session: {ve}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Input validation failed: {str(ve)}"
        )
    except Exception as e:
        logger.error(f"Failed to add message to session {session_id}: {e}")
        logger.error(f"Message details: user_id={user_id}, user_msg='{user_message[:100] if user_message else 'None'}', source={source}")
        # Re-raise to let caller handle the error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save message securely"
        )

@app.get("/")
async def read_root():
    return FileResponse("static/index.html", media_type="text/html; charset=utf-8")

# 🆕 USER REGISTRATION
@app.post("/register", response_model=dict)
async def register_user(user: UserRegister, request: Request):
    """Register a new user with enhanced security"""
    try:
        client_ip = request.client.host
        
        # Check rate limiting for registration
        if not rate_limiter.is_allowed(client_ip, "general"):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many registration attempts. Please try again later."
            )
        
        # Validate password strength
        is_strong, message = validate_password_strength(user.password)
        if not is_strong:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Password validation failed: {message}"
            )
        
        # Validate username (enhanced security check)
        is_valid_username, username_message = input_validator.validate_username(user.username)
        if not is_valid_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Username validation failed: {username_message}"
            )
        
        # Check if user already exists
        if user.username in users_db:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        
        # Check if email already exists
        for existing_user in users_db.values():
            if existing_user["email"] == user.email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
        
        # Create new user with enhanced security
        user_id = str(uuid.uuid4())
        hashed_password = get_password_hash(user.password)
        
        users_db[user.username] = {
            "user_id": user_id,
            "username": user.username,
            "email": user.email,
            "hashed_password": hashed_password,
            "full_name": user.full_name,
            "created_at": datetime.utcnow(),
            "is_active": True,
            "created_ip": client_ip,  # Track creation IP for security
            "last_login": None,
            "failed_login_attempts": 0
        }
        
        logger.info(f"✅ New user registered: {user.username} from IP: {client_ip}")
        
        return {
            "success": True,
            "message": "User registered successfully",
            "user_id": user_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

# 🆕 USER LOGIN WITH JWT (supports demo user)
@app.post("/login", response_model=Token)
async def login_for_access_token(form_data: LoginRequest, request: Request):
    """Authenticate user and return access token with enhanced security"""
    client_ip = request.client.host
    
    # Check if IP is blocked due to brute force attempts
    if auth_service.check_brute_force(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. IP temporarily blocked.",
            headers={"Retry-After": str(auth_service.brute_force_protection.block_duration * 60)}
        )
    
    # Rate limiting for login attempts
    if not rate_limiter.is_allowed(client_ip, "general"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later."
        )
    
    # Input validation
    if not form_data.username or not form_data.password:
        auth_service.record_failed_attempt(client_ip)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username and password are required"
        )
    
    # 🚨 SECURE DEMO USER CHECK with enhanced production protection  
    if auth_service.demo_user_enabled and form_data.username == "demo":
        # 🔒 ENHANCED DEMO USER SECURITY with input validation
        if not input_validator.validate_username(form_data.username)[0]:
            auth_service.record_failed_attempt(client_ip)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid username format"
            )
        
        demo_password = auth_service.demo_password
        
        # Validate demo password strength if it's the default weak password
        if demo_password == "1234" and ENVIRONMENT == "production":
            logger.critical("🚨 PRODUCTION SECURITY BREACH: Default weak demo password detected!")
            auth_service.record_failed_attempt(client_ip)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Demo access disabled due to security policy"
            )
        
        if form_data.password == demo_password:
            auth_service.record_successful_login(client_ip)
            
            # ⚠️ PRODUCTION WARNING
            if ENVIRONMENT == "production":
                logger.warning(f"🚨 PRODUCTION DEMO LOGIN from IP: {client_ip} - Consider disabling demo user!")
            
            # 🚀 NEW SESSION CREATION: Create new session on each login
            demo_user_id = "demo-user-id"
            try:
                session_id = db_manager.get_or_create_session(demo_user_id, force_new=True)
                logger.info(f"Demo user new session created: {session_id}")
            except Exception as e:
                logger.warning(f"Demo session creation issue: {e}")
            
            access_token_expires = timedelta(minutes=auth_service.access_token_expire_minutes)
            access_token = create_access_token(
                data={"sub": "demo", "ip": client_ip, "session_type": "demo"}, 
                expires_delta=access_token_expires
            )
            logger.info(f"Demo user login from IP: {client_ip}")
            return {"access_token": access_token, "token_type": "bearer"}
        else:
            # Wrong demo password
            auth_service.record_failed_attempt(client_ip)
            logger.warning(f"Failed demo login attempt from IP: {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    # Check regular users
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        auth_service.record_failed_attempt(client_ip)
        logger.warning(f"Failed login attempt for user: {form_data.username} from IP: {client_ip}")
        
        # Generic error message to prevent username enumeration
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user account is active
    if not user.get("is_active", True):
        auth_service.record_failed_attempt(client_ip)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )
    
    # Successful login
    auth_service.record_successful_login(client_ip)
    
    # Update user login information
    user["last_login"] = datetime.utcnow()
    user["last_login_ip"] = client_ip
    user["failed_login_attempts"] = 0
    
    # 🚀 NEW SESSION CREATION: Create new session on each login
    try:
        session_id = db_manager.get_or_create_session(user["user_id"], force_new=True)
        logger.info(f"User {user['username']} new session created: {session_id}")
    except Exception as e:
        logger.warning(f"User session creation issue for {user['username']}: {e}")
    
    access_token_expires = timedelta(minutes=auth_service.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user["username"], "ip": client_ip}, 
        expires_delta=access_token_expires
    )
    
    logger.info(f"Successful login for user: {form_data.username} from IP: {client_ip}")
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/login-legacy", response_model=LoginResponse)
async def login_legacy(request: LoginRequest, request_obj: Request):
    """
    Legacy login endpoint with enhanced security
    🚨 DEPRECATED: Use /login endpoint instead for JWT authentication
    """
    client_ip = request_obj.client.host
    
    # Apply same brute force protection
    if auth_service.check_brute_force(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="IP temporarily blocked due to too many failed attempts."
        )
    
    # Input validation
    if not request.username or not request.password:
        auth_service.record_failed_attempt(client_ip)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username and password are required"
        )
    
    # Length validation
    if len(request.username) > 100 or len(request.password) > 100:
        auth_service.record_failed_attempt(client_ip)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid input length"
        )
    
    # 🚨 SECURE DEMO USER CHECK
    if auth_service.demo_user_enabled and request.username == "demo":
        demo_password = auth_service.demo_password
        if request.password == demo_password:
            auth_service.record_successful_login(client_ip)
            logger.info(f"Legacy demo login from IP: {client_ip}")
            return LoginResponse(success=True, message="Giriş başarılı")
        else:
            auth_service.record_failed_attempt(client_ip)
            return LoginResponse(success=False, message="Kullanıcı adı veya şifre hatalı")
    
    # Check real users with proper password verification
    user = authenticate_user(request.username, request.password)
    if user:
        auth_service.record_successful_login(client_ip)
        logger.info(f"Legacy login success for user: {request.username} from IP: {client_ip}")
        return LoginResponse(success=True, message="Giriş başarılı")
    else:
        auth_service.record_failed_attempt(client_ip)
        logger.warning(f"Legacy login failed for user: {request.username} from IP: {client_ip}")
        return LoginResponse(success=False, message="Kullanıcı adı veya şifre hatalı")

@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    try:
        # Check Qdrant connection
        collections = qdrant_client.get_collections()
        return {
            "status": "healthy",
            "qdrant": "connected",
            "openai_enabled": USE_OPENAI,
            "huggingface_enabled": USE_HUGGINGFACE,
            "collections": len(collections.collections)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@app.get("/health/comprehensive")
async def comprehensive_health_check():
    """
    🏥 Comprehensive health check endpoint for production monitoring
    Checks: CPU, Memory, Disk Space, Database, External Services, Cache
    """
    try:
        from memory_monitor import memory_monitor
        import psutil
        import shutil
        
        health_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "healthy",
            "checks": {},
            "metrics": {},
            "alerts": []
        }
        
        # 1. 🧠 Memory Check
        try:
            memory_stats = memory_monitor.get_stats() if hasattr(memory_monitor, 'get_stats') else {}
            process = psutil.Process()
            memory_info = process.memory_info()
            
            memory_mb = memory_info.rss / 1024 / 1024
            memory_percent = process.memory_percent()
            
            health_data["checks"]["memory"] = {
                "status": "healthy" if memory_mb < 1000 else "warning" if memory_mb < 2000 else "critical",
                "usage_mb": round(memory_mb, 2),
                "usage_percent": round(memory_percent, 2),
                "threshold_mb": 1000,
                "details": memory_stats
            }
            
            if memory_mb > 1500:
                health_data["alerts"].append(f"High memory usage: {memory_mb:.1f}MB")
                
        except Exception as e:
            health_data["checks"]["memory"] = {"status": "error", "error": str(e)}
            
        # 2. 🖥️ CPU Check
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else (0, 0, 0)
            
            health_data["checks"]["cpu"] = {
                "status": "healthy" if cpu_percent < 70 else "warning" if cpu_percent < 90 else "critical",
                "usage_percent": cpu_percent,
                "core_count": cpu_count,
                "load_average": {
                    "1min": load_avg[0],
                    "5min": load_avg[1], 
                    "15min": load_avg[2]
                }
            }
            
            if cpu_percent > 85:
                health_data["alerts"].append(f"High CPU usage: {cpu_percent}%")
                
        except Exception as e:
            health_data["checks"]["cpu"] = {"status": "error", "error": str(e)}
            
        # 3. 💾 Disk Space Check
        try:
            disk_usage = shutil.disk_usage("/")
            total_gb = disk_usage.total / (1024**3)
            free_gb = disk_usage.free / (1024**3)
            used_gb = (disk_usage.total - disk_usage.free) / (1024**3)
            usage_percent = (used_gb / total_gb) * 100
            
            health_data["checks"]["disk"] = {
                "status": "healthy" if usage_percent < 80 else "warning" if usage_percent < 95 else "critical",
                "total_gb": round(total_gb, 2),
                "used_gb": round(used_gb, 2),
                "free_gb": round(free_gb, 2),
                "usage_percent": round(usage_percent, 2)
            }
            
            if usage_percent > 90:
                health_data["alerts"].append(f"Low disk space: {usage_percent:.1f}% used")
                
        except Exception as e:
            health_data["checks"]["disk"] = {"status": "error", "error": str(e)}
            
        # 4. 🗄️ Database Connectivity Check
        try:
            start_time = time.time()
            db_stats = db_manager.get_stats()
            
            # Test database query
            test_query_start = time.time()
            db_manager.get_or_create_session("health_check_user")
            query_time = time.time() - test_query_start
            
            health_data["checks"]["database"] = {
                "status": "healthy" if query_time < 1.0 else "warning" if query_time < 5.0 else "critical",
                "response_time_ms": round(query_time * 1000, 2),
                "connection_pool": db_stats.get("pool_stats", {}),
                "total_sessions": db_stats.get("total_sessions", 0),
                "total_messages": db_stats.get("total_messages", 0)
            }
            
            if query_time > 2.0:
                health_data["alerts"].append(f"Slow database response: {query_time*1000:.1f}ms")
                
        except Exception as e:
            health_data["checks"]["database"] = {"status": "error", "error": str(e)}
            
        # 5. 🤖 AI Services Check
        try:
            ai_status = {"openai": "disabled", "huggingface": "disabled", "qdrant": "unknown"}
            
            # Check OpenAI
            if USE_OPENAI:
                try:
                    # Simple test - just check if API key is set
                    if os.getenv("OPENAI_API_KEY"):
                        ai_status["openai"] = "configured"
                    else:
                        ai_status["openai"] = "no_api_key"
                except Exception:
                    ai_status["openai"] = "error"
                    
            # Check Hugging Face models
            if USE_HUGGINGFACE:
                try:
                    model_info = model_manager.get_model_info()
                    ai_status["huggingface"] = "loaded" if model_info.get("models_loaded", 0) > 0 else "not_loaded"
                except Exception:
                    ai_status["huggingface"] = "error"
                    
            # Check Qdrant
            try:
                collections = qdrant_client.get_collections()
                ai_status["qdrant"] = "connected"
                collection_count = len(collections.collections)
            except Exception as e:
                ai_status["qdrant"] = "disconnected"
                collection_count = 0
                
            health_data["checks"]["ai_services"] = {
                "status": "healthy" if ai_status["qdrant"] == "connected" else "warning",
                "services": ai_status,
                "qdrant_collections": collection_count
            }
            
        except Exception as e:
            health_data["checks"]["ai_services"] = {"status": "error", "error": str(e)}
            
        # 6. 📊 Cache Performance Check
        try:
            cache_stats = response_cache.get_stats()
            hit_rate = (cache_stats.get("hits", 0) / max(cache_stats.get("total_requests", 1), 1)) * 100
            
            health_data["checks"]["cache"] = {
                "status": "healthy" if hit_rate > 30 else "warning" if hit_rate > 10 else "poor",
                "hit_rate_percent": round(hit_rate, 2),
                "total_entries": cache_stats.get("total_entries", 0),
                "memory_usage_mb": cache_stats.get("memory_usage_mb", 0)
            }
            
        except Exception as e:
            health_data["checks"]["cache"] = {"status": "error", "error": str(e)}
            
        # 7. 🔌 WebSocket Connections Check
        try:
            ws_stats = websocket_manager.get_connection_stats()
            active_connections = ws_stats.get("active_connections", 0)
            
            health_data["checks"]["websockets"] = {
                "status": "healthy" if active_connections < 100 else "warning",
                "active_connections": active_connections,
                "total_connections": ws_stats.get("total_connections", 0)
            }
            
        except Exception as e:
            health_data["checks"]["websockets"] = {"status": "error", "error": str(e)}
            
        # 8. 🔐 Security Check
        try:
            security_checks = {
                "debug_mode": not DEBUG_MODE,
                "secure_secret_key": SECRET_KEY != "your-secret-key-change-this-in-production",
                "environment": ENVIRONMENT,
                "cors_configured": len(cors_origins) > 0 and "*" not in cors_origins
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
            "uptime_seconds": (datetime.utcnow() - db_manager.created_at).total_seconds() if hasattr(db_manager, 'created_at') else 0,
            "total_checks": len(health_data["checks"]),
            "healthy_checks": len([s for s in check_statuses if s == "healthy"]),
            "warning_checks": len([s for s in check_statuses if s == "warning"]),
            "critical_checks": len([s for s in check_statuses if s == "critical"]),
            "error_checks": len([s for s in check_statuses if s == "error"])
        }
        
        # Return appropriate HTTP status
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
        return JSONResponse(
            status_code=500,
            content={
                "timestamp": datetime.utcnow().isoformat(),
                "status": "error",
                "error": str(e),
                "checks": {}
            }
        )

def generate_embedding(text: str) -> list:
    """Generate embedding using ModelManager with caching"""
    try:
        return model_manager.generate_embedding(text)
    except Exception as e:
        logger.error(f"Embedding generation error: {e}")
        
        # Fallback to OpenAI if available
        if USE_OPENAI:
            try:
                response = openai.embeddings.create(
                    model="text-embedding-ada-002",
                    input=text
                )
                return response.data[0].embedding
            except Exception as e2:
                logger.error(f"OpenAI embedding fallback error: {e2}")
        
        raise HTTPException(status_code=500, detail="No embedding service available")

def generate_response_openai(context: str, user_message: str) -> str:
    """Generate response using OpenAI"""
    try:
        if context:
            # Use context from database
            system_prompt = """Sen MEFAPEX fabrikasının Türkçe AI asistanısın. 
            ÖNEMLI: Sadece Türkçe yanıt ver, asla İngilizce kullanma.
            Verilen bilgileri kullanarak Türkçe, kısa ve net cevaplar ver.
            Bilgileri doğru bir şekilde kullan ve kullanıcıya Türkçe yardımcı ol.
            Tüm yanıtların Türkiye Türkçesi ile olmalıdır."""
            
            user_prompt = f"Bağlam: {context}\n\nSoru: {user_message}"
        else:
            # No context found - use general knowledge
            system_prompt = """Sen MEFAPEX fabrikasının Türkçe AI asistanısın. 
            ÖNEMLI: Sadece Türkçe yanıt ver, hiç İngilizce kelime kullanma.
            
            Fabrika ile ilgili genel sorulara Türkçe yardımcı ol. Eğer spesifik fabrika verisi gerekmiyorsa,
            genel bilginle Türkçe yanıt verebilirsin. Yanıtını kısa, yararlı ve tamamen Türkçe tut.
            
            MEFAPEX hakkında genel bilgi: Türkiye'deki bir üretim fabrikası, çalışan hakları ve 
            güvenlik kurallarına önem verir.
            
            Eğer fabrika-spesifik veri gerekliyse, kullanıcıyı yönetime yönlendir.
            Tüm yanıtların Türkiye Türkçesi ile olmalıdır."""
            
            user_prompt = f"Soru: {user_message}\n\nBu konuda fabrika veritabanında spesifik bilgi bulunamadı. Genel bilginle yardımcı olabilir misin?"
        
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=200,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"OpenAI response error: {e}")
        raise

def generate_response_huggingface(context: str, user_message: str) -> str:
    """Generate response using Hugging Face with improved AI capabilities"""
    
    # Eğer veritabanında context varsa kullan
    if context and "Answer:" in context:
        lines = context.split('\n')
        for line in lines:
            if 'Answer:' in line:
                answer = line.split(':', 1)[-1].strip()
                if answer:
                    return f"📋 {answer}\n\n💡 Bu bilgi MEFAPEX fabrika veritabanından alınmıştır."
    
    # Veritabanında bilgi yoksa, genel AI yanıtı üret
    user_lower = user_message.lower().strip()
    
    # MEFAPEX soruları için öncelikli kontrol
    if any(word in user_lower for word in ["mefapex", "nedir", "ne", "what"]) and "mefapex" in user_lower:
        return """🏭 **MEFAPEX Fabrikası Hakkında**

MEFAPEX, Türkiye'de faaliyet gösteren modern bir üretim fabrikasıdır.

**Fabrika Özellikleri:**
• 🏗️ **Modern Üretim**: En son teknoloji ile donatılmış tesisler
• 🛡️ **Güvenlik Odaklı**: Çalışan güvenliği birinci öncelik
• 🌟 **Kalite**: Uluslararası standartlarda üretim
• 👥 **İnsan Kaynakları**: Deneyimli ve eğitimli çalışan kadrosu
• 🌱 **Sürdürülebilirlik**: Çevre dostu üretim süreçleri

**Faaliyet Alanları:**
• Endüstriyel üretim ve imalat
• Kalite kontrol ve test süreçleri
• Ar-Ge ve inovasyon çalışmaları
• İş güvenliği ve çalışan eğitimleri

**Misyonumuz:**
Yüksek kaliteli ürünlerle hem yerel hem de global pazarda güvenilir bir üretici olmak.

Size MEFAPEX hakkında başka hangi konularda bilgi verebilirim? 🤝"""
    
    # Yapay Zeka Soruları - Türkçe öncelikli
    turkish_ai_terms = [
        "yapay zeka", "yapay zekâ", "makine öğrenmesi", "makine öğrenimi",
        "derin öğrenme", "sinir ağları", "algoritma", "robot", "otomasyon",
        "akıllı sistem", "veri bilimi", "büyük veri", "analitik",
        # İngilizce ve diğer diller (düşük öncelik)
        "ia", "ai", "artificial intelligence", "IA nedir"
    ]
    
    if any(word in user_lower for word in turkish_ai_terms):
        return """🤖 **IA (Intelligence Artificielle) / Yapay Zeka Nedir?**

IA veya AI (Artificial Intelligence), makinelerin insan benzeri zeka göstermesini sağlayan teknolojilerin genel adıdır.

**Temel Özellikler:**
• Öğrenme ve adaptasyon yeteneği
• Problem çözme ve karar verme
• Doğal dil işleme ve anlama
• Görüntü ve ses tanıma
• Otonom hareket ve planlama

**Kullanım Alanları:**
• Sağlık: Hastalık teşhisi, ilaç keşfi
• Finans: Risk analizi, dolandırıcılık tespiti
• Üretim: Kalite kontrol, tahmine dayalı bakım
• Eğitim: Kişiselleştirilmiş öğrenme
• Günlük hayat: Sesli asistanlar, öneri sistemleri

Ben de bir AI asistanıyım ve size MEFAPEX fabrikası hakkında yardımcı olmak için buradayım! 🎯"""

    # ChatGPT hakkında sorular
    elif any(word in user_lower for word in ["chatgpt", "gpt", "openai"]):
        return """💬 **ChatGPT Nedir?**

ChatGPT, OpenAI tarafından geliştirilen gelişmiş bir dil modelidir. GPT (Generative Pre-trained Transformer) teknolojisini kullanır.

**Yetenekleri:**
• Doğal dil anlama ve üretme
• Çok dilli destek (100+ dil)
• Kod yazma ve debugging
• Yaratıcı içerik üretimi
• Analiz ve problem çözme

**Nasıl Çalışır:**
• Milyarlarca parametreli sinir ağı
• Transformer mimarisi
• Bağlamsal anlama ve tahmin
• Sürekli öğrenme ve gelişme

Ben de benzer teknolojiler kullanıyorum! Size nasıl yardımcı olabilirim? 🚀"""

    # Python hakkında sorular
    elif any(word in user_lower for word in ["python", "programlama", "kod", "yazılım"]):
        return """🐍 **Python Programlama Dili**

Python, yüksek seviyeli, yorumlanabilir ve çok amaçlı bir programlama dilidir.

**Özellikleri:**
• Kolay ve okunabilir sözdizimi
• Geniş kütüphane desteği
• Platform bağımsız
• Açık kaynak ve ücretsiz
• Dinamik tip sistemi

**Kullanım Alanları:**
• Web geliştirme (Django, Flask)
• Veri bilimi (Pandas, NumPy)
• Yapay zeka (TensorFlow, PyTorch)
• Otomasyon ve scripting
• Oyun geliştirme

Bu chatbot da Python ile geliştirilmiştir! 🎯"""

    # Teknoloji genel soruları
    elif any(word in user_lower for word in ["teknoloji", "bilgisayar", "internet", "dijital"]):
        return """💻 **Teknoloji ve Dijital Dönüşüm**

Modern teknoloji, hayatımızın her alanını dönüştürüyor.

**Önemli Teknoloji Trendleri:**
• Yapay Zeka ve Makine Öğrenmesi
• Bulut Bilişim (Cloud Computing)
• Nesnelerin İnterneti (IoT)
• Blockchain ve Kripto
• 5G ve Bağlantı Teknolojileri
• Sanal ve Artırılmış Gerçeklik

**Fabrikada Teknoloji:**
MEFAPEX fabrikamız da modern teknolojileri kullanarak üretim verimliliğini artırıyor.

Teknoloji hakkında spesifik sorularınız varsa, sormaktan çekinmeyin! 🚀"""

    # Matematik/Hesaplama soruları
    elif any(word in user_lower for word in ["hesapla", "matematik", "toplam", "çarp", "böl", "eksi", "artı"]):
        return """🔢 **Matematik ve Hesaplama**

Matematik sorunuz için size yardımcı olmaya çalışayım!

Basit hesaplamalar yapabilirim:
• Toplama, çıkarma, çarpma, bölme
• Yüzde hesaplamaları
• Oran ve orantı
• Basit denklemler

Lütfen hesaplamanızı net bir şekilde yazın. Örnek:
- "15 + 27 kaç eder?"
- "120'nin %15'i nedir?"
- "8 x 12 = ?"

Not: Karmaşık hesaplamalar için hesap makinesi kullanmanızı öneririm. 📊"""

    # Genel selamlama
    elif any(word in user_lower for word in ["merhaba", "selam", "günaydın", "iyi günler", "hey", "hello"]):
        return """👋 **Merhaba! Hoş geldiniz!**

Ben MEFAPEX fabrikasının AI asistanıyım. Size yardımcı olmaktan mutluluk duyarım!

**Size yardımcı olabileceğim konular:**
• Fabrika ile ilgili sorular (çalışma saatleri, kurallar vb.)
• Genel bilgi soruları
• Teknoloji ve AI konuları
• Basit hesaplamalar
• Ve daha fazlası...

Nasıl yardımcı olabilirim? 😊"""

    # Teşekkür mesajları
    elif any(word in user_lower for word in ["teşekkür", "sağol", "eyvallah", "thanks"]):
        return """� **Rica ederim!**

Yardımcı olabildiysem ne mutlu bana! 

Başka sorularınız olursa her zaman buradayım. Size yardımcı olmak benim için bir zevk.

İyi günler dilerim! 🌟"""

    # Veda mesajları
    elif any(word in user_lower for word in ["görüşürüz", "hoşçakal", "bye", "iyi akşamlar", "iyi geceler"]):
        return """👋 **Görüşmek üzere!**

Size yardımcı olabildiğim için mutluyum. 

Tekrar görüşmek üzere! Başka sorularınız olduğunda ben burada olacağım.

İyi günler dilerim! 🌟"""

    # Fabrika dışı genel sorular için
    else:
        # DialoGPT çok tutarsız sonuçlar üretiyor, sadece local intelligent responses kullan
        return generate_ai_response_local(user_message)
        # Fallback: Genel yardımcı yanıt
        return f"""🤖 **'{user_message}' hakkında:**

Bu konu hakkında size yardımcı olmaya çalışıyorum. 

Sorunuz fabrika veritabanımızda bulunmamakla birlikte, genel bilgilerimle yanıt vermeye çalışabilirim.

**Daha iyi yardım için:**
• Sorunuzu daha detaylı yazabilirsiniz
• Fabrika ile ilgili konularda daha spesifik sorular sorabilirsiniz
• Veya farklı bir konu hakkında soru sorabilirsiniz

Size başka nasıl yardımcı olabilirim? 💭"""

def generate_advanced_ai_response(user_message: str) -> str:
    """Generate response using ModelManager with caching"""
    try:
        # Check cache first
        cached_response = response_cache.get(user_message, "")
        if cached_response:
            response_text, source = cached_response
            logger.info(f"🎯 Cache hit for message: {user_message[:30]}...")
            return response_text
        
        # Use ModelManager for text generation
        if model_manager.text_generator is not None:
            conversation_prompt = f"Kullanıcı: {user_message}\nAsistan:"
            generated = model_manager.generate_text_response(conversation_prompt, max_length=100)
            
            # Clean up response
            if "Asistan:" in generated:
                response_text = generated.split("Asistan:")[-1].strip()
            else:
                response_text = generated
            
            # Additional cleanup
            response_text = response_text.replace("\\n", " ").strip()
            response_text = response_text.split("Kullanıcı:")[0].strip()
            
            if len(response_text) >= 5:
                # Cache successful response
                response_cache.set(user_message, response_text, "", source="advanced_ai")
                return response_text
            else:
                raise Exception("Generated response too short")
                
        else:
            raise Exception("Text generator not available")
            
    except Exception as e:
        logger.warning(f"Advanced AI generation failed: {e}")
        # Fallback to local AI response
        response = generate_ai_response_local(user_message)
        response_cache.set(user_message, response, "", source="local_ai")
        return response

def generate_ai_response_local(user_message: str) -> str:
    """Generate AI response using enhanced local intelligence - Factory focused fallback"""
    # Convert to lowercase for analysis
    msg_lower = user_message.lower().strip()
    
    # Temel selamlama kalıpları
    greetings = [
        "merhaba", "selam", "selamun aleyküm", "selamünaleyküm", 
        "günaydın", "iyi günler", "iyi akşamlar", "iyi geceler",
        "nasılsın", "nasilsin", "nasıl gidiyor", "naber", "ne haber",
        "hoş geldin", "hoşgeldin", "hello", "hi", "hey"
    ]
    
    if any(word in msg_lower for word in greetings):
        return """👋 **Merhaba! Hoş geldiniz!**

Ben MEFAPEX fabrikasının AI asistanıyım. Size yardımcı olmaktan mutluluk duyarım!

**Size yardımcı olabileceğim konular:**
• 🏭 Fabrika operasyonları ve süreçleri
• 🛡️ İş güvenliği kuralları
• ⏰ Çalışma saatleri ve vardiyalar
• 📋 Prosedürler ve yönergeler
• 🔧 Genel fabrika bilgileri

Nasıl yardımcı olabilirim? 😊"""

    # Teşekkür ve veda mesajları
    elif any(word in msg_lower for word in ["teşekkür", "thanks", "sağol", "görüşürüz", "bye", "hoşça kal"]):
        return """� **Rica ederim!**

Size yardımcı olabildiysem ne mutlu bana! 

Başka sorularınız olduğunda her zaman buradayım.
İyi çalışmalar dilerim! 🌟"""

    # MEFAPEX ve fabrika soruları
    elif any(word in msg_lower for word in ["mefapex", "fabrika", "factory", "üretim", "işçi", "çalışan", "personel"]):
        return """🏭 **MEFAPEX Fabrikası Hakkında**

MEFAPEX, modern üretim teknolojileri ile kaliteli ürünler üreten bir fabrikadır.

**Temel Bilgiler:**
• 🛡️ **Güvenlik**: Çalışan güvenliği birinci öncelik
• 🌟 **Kalite**: Yüksek standartlarda üretim
• � **İnsan Kaynakları**: Deneyimli çalışan kadrosu
• 🔧 **Modern Teknoloji**: Güncel üretim sistemleri

**Detaylı bilgi için şunları sorabilirsiniz:**
• Çalışma saatleri ve vardiya sistemi
• Güvenlik kuralları ve prosedürler
• İzin ve tatil düzenlemeleri
• Departman yapısı ve organizasyon

Size hangi konuda yardımcı olabilirim? 🤝"""

    # Zaman ve vardiya soruları
    elif any(word in msg_lower for word in ["saat", "zaman", "vardiya", "mesai", "çalışma saati", "time", "ne zaman"]):
        return """⏰ **Çalışma Saatleri ve Vardiya Bilgileri**

**Genel Çalışma Düzeni:**
• Standart mesai: 08:00-17:00 (Pazartesi-Cuma)
• Öğle molası: 12:00-13:00
• Çay molaları: Sabah 10:00 ve öğleden sonra 15:00

**Vardiya Sistemleri:**
Bazı üretim hatlarında 24 saat sürekli üretim için vardiya sistemi uygulanmaktadır.

**Detaylı bilgi için:**
• İnsan Kaynakları departmanına başvurabilirsiniz
• Vardiya programları departman bazında farklılık gösterebilir

Spesifik bir departman veya vardiya hakkında bilgi mi istiyorsunuz? �"""

    # Güvenlik kuralları
    elif any(word in msg_lower for word in ["güvenlik", "kural", "prosedür", "safety", "regulation"]):
        return """�️ **İş Güvenliği ve Kurallar**

**Temel Güvenlik Kuralları:**
• Kişisel koruyucu ekipman kullanımı zorunludur
• Güvenlik eğitimlerine katılım şarttır
• Acil durum prosedürlerine uygun hareket edilmelidir
• İş kazası veya yakın kaçış durumları rapor edilmelidir

**Güvenlik Ekipmanları:**
• Baret, güvenlik gözlüğü, eldiven
• İş ayakkabısı ve reflektörlü yelek
• Departmana özel koruyucu ekipmanlar

**Acil Durumlar:**
• Acil çıkış yollarını bilin
• Yangın alarm sistemlerine dikkat edin
• İlk yardım noktalarının yerini öğrenin

Hangi güvenlik konusu hakkında detaylı bilgi almak istiyorsunuz? �"""

    # İzin ve personel konuları
    elif any(word in msg_lower for word in ["izin", "tatil", "rapor", "özür", "leave", "holiday"]):
        return """� **İzin ve Personel İşlemleri**

**İzin Türleri:**
• Yıllık izin hakkı
• Hastalık izni (rapor)
• Mazeret izni
• Doğum izni
• Babalık izni

**İzin Başvuru Süreci:**
• Önceden üst yöneticinize bilgi verin
• Resmi izin formunu doldurun
• İnsan Kaynakları onayı alın
• İş devrini düzenleyin

**Önemli Notlar:**
• Acil durumlar dışında izinler önceden planlanmalı
• Uzun süreli izinler için erken başvuru gerekli

İzin konusunda spesifik bir durumunuz mu var? """

    # Akıllı AI yanıt sistemi - Otomatik analiz
    else:
        # Her durumda aynı standart fallback yanıtı
        return f"""🤔 **'{user_message}' hakkında MEFAPEX bilgi tabanımızda hazır bir kayıt bulamadım.**

**Daha iyi yardım için şunları deneyebilirsiniz:**
• Soruyu daha detaylandırın
• Hangi alanda bilgi istediğinizi belirtin
• Fabrika ile ilgili sorular için spesifik konular sorun

**Hızlı erişim için:**
• 📞 Santral: [Fabrika telefon numarası]
• 📧 Genel bilgi: [İletişim e-posta]
• 🏢 İnsan Kaynakları departmanı

**Alternatif olarak şunları sorabilirsiniz:**
• Çalışma saatleri ve vardiya bilgileri
• Güvenlik kuralları ve prosedürler
• İzin ve tatil işlemleri
• Genel fabrika bilgileri

Size başka nasıl yardımcı olabilirim? 💬"""

def generate_rule_based_response(user_message: str) -> str:
    """Fallback rule-based responses"""
    msg_lower = user_message.lower()
    
    # Greetings
    greetings = ["merhaba", "selam", "hi", "hello", "hey"]
    if any(greeting in msg_lower for greeting in greetings):
        return "👋 Merhaba! MEFAPEX fabrika asistanınızım. Size nasıl yardımcı olabilirim?"
    
    # Goodbyes
    goodbyes = ["görüşürüz", "bye", "hoşça kal", "iyi günler"]
    if any(goodbye in msg_lower for goodbye in goodbyes):
        return "👋 İyi günler! Başka sorularınız olduğunda yardımcı olmaktan mutluluk duyarım."
    
    # Default response
    return "🤖 Bu konuda detaylı bilgim bulunmuyor, ancak size yardımcı olmaya çalışabilirim. Sorunuzu biraz daha detaylandırabilir misiniz? Veya fabrika ile ilgili spesifik bir konu hakkında soru sorabilirsiniz."

# =============================
# 📚 CHAT HISTORY SECTION
# =============================

# 🆕 CHAT HISTORY ENDPOINTS
@app.get("/chat/history/{user_id}", response_model=ChatHistoryResponse)
async def get_chat_history(user_id: str, current_user: dict = Depends(get_current_user)):
    """Get chat history for a user (last 20 messages, persistent)"""
    try:
        if current_user["user_id"] != user_id and not current_user.get("is_admin", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        session_id = db_manager.get_or_create_session(user_id)
        messages = db_manager.get_chat_history(user_id, limit=20)
        return ChatHistoryResponse(
            session_id=session_id,
            messages=messages,
            total_messages=len(messages)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching chat history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch chat history"
        )

@app.delete("/chat/history/{user_id}")
async def clear_chat_history(user_id: str, current_user: dict = Depends(get_current_user)):
    """Clear chat history for a user (persistent)"""
    try:
        if current_user["user_id"] != user_id and not current_user.get("is_admin", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        db_manager.clear_chat_history(user_id)
        return {"success": True, "message": "Chat history cleared"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing chat history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear chat history"
        )

# 🆕 SESSION-BASED HISTORY ENDPOINTS WITH OPTIMIZATION
@app.get("/chat/session/current")
async def get_current_session_info(current_user: dict = Depends(get_current_user)):
    """Get current active session info for user (optimized for quick access)"""
    try:
        # Ensure user has an active session
        session_id = get_user_session(current_user["user_id"], force_new=False, auto_create=True)
        
        # Get session info with recent messages
        session_info = db_manager.get_session_info(session_id)
        recent_messages = db_manager.get_chat_history(current_user["user_id"], limit=5)
        
        return {
            "success": True,
            "session_id": session_id,
            "user_id": current_user["user_id"],
            "session_info": session_info,
            "recent_messages": recent_messages,
            "total_recent": len(recent_messages),
            "session_ready": True
        }
    except Exception as e:
        logger.error(f"Error getting current session for user {current_user['username']}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get current session info"
        )

@app.get("/chat/sessions/{user_id}")
async def get_chat_sessions(user_id: str, current_user: dict = Depends(get_current_user)):
    """Get chat sessions with history (max 15 sessions per user) - optimized"""
    try:
        if current_user["user_id"] != user_id and not current_user.get("is_admin", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # 🚀 ENSURE ACTIVE SESSION: Make sure user has current session
        current_session_id = get_user_session(user_id, force_new=False, auto_create=True)
        
        sessions = db_manager.get_chat_sessions_with_history(user_id, limit=15)
        return {
            "user_id": user_id,
            "sessions": sessions,
            "total_sessions": len(sessions),
            "current_session_id": current_session_id,
            "session_ready": True
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching chat sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch chat sessions"
        )

@app.post("/chat/sessions/{user_id}/new")
async def start_new_chat_session(user_id: str, current_user: dict = Depends(get_current_user)):
    """Start a new chat session for the user (optimized for immediate use)"""
    try:
        if current_user["user_id"] != user_id and not current_user.get("is_admin", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # 🚀 FORCE NEW SESSION: Always create a fresh session
        new_session_id = db_manager.start_new_session(user_id)
        
        # Verify session was created successfully
        session_info = db_manager.get_session_info(new_session_id)
        
        logger.info(f"New session created for user {current_user['username']}: {new_session_id}")
        
        return {
            "success": True,
            "message": "New chat session started and ready",
            "session_id": new_session_id,
            "session_info": session_info,
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error starting new session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start new session"
        )

@app.get("/chat/sessions/info/{session_id}")
async def get_session_info(session_id: str, current_user: dict = Depends(get_current_user)):
    """Get information about a specific session"""
    try:
        session_info = db_manager.get_session_info(session_id)
        if not session_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        # Check if user owns this session
        if session_info["user_id"] != current_user["user_id"] and not current_user.get("is_admin", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        return session_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching session info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch session info"
        )

@app.get("/chat/sessions/{session_id}/messages")
async def get_session_messages(session_id: str, current_user: dict = Depends(get_current_user)):
    """Get all messages for a specific session"""
    try:
        # Get session info to verify ownership
        session_info = db_manager.get_session_info(session_id)
        if not session_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        # Check if user owns this session
        if session_info["user_id"] != current_user["user_id"] and not current_user.get("is_admin", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Get messages for this session
        messages = db_manager.get_chat_messages(session_id)
        
        return {
            "session_id": session_id,
            "messages": messages,
            "message_count": len(messages)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching session messages: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch session messages"
        )

# 🎯 MAIN SESSION SAVE ENDPOINT
@app.post("/chat/sessions/save")
async def save_chat_session(
    session_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Save a chat session to history with 15-session limit enforcement"""
    try:
        user_id = current_user.get("user_id") or current_user.get("username", "unknown")
        session_id = session_data.get("sessionId")
        messages = session_data.get("messages", [])
        started_at = session_data.get("startedAt")
        
        if not session_id or not messages:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid session data: missing sessionId or messages"
            )
        
        # Save each message to the database
        for message in messages:
            user_message = message.get("user_message", "")
            bot_response = message.get("bot_response", "")
            timestamp = message.get("timestamp", datetime.now().isoformat())
            
            if user_message and bot_response:
                db_manager.add_message(
                    session_id=session_id,
                    user_id=user_id,
                    user_message=user_message,
                    bot_response=bot_response,
                    source="session_save"
                )
        
        # Create session record
        db_manager.save_chat_session(
            user_id=user_id,
            session_id=session_id,
            started_at=started_at,
            message_count=len(messages)
        )
        
        # Enforce 15-session limit per user
        db_manager.trim_user_sessions(user_id, max_sessions=15)
        
        logger.info(f"💾 Session saved successfully: {session_id} ({len(messages)} messages)")
        
        return {
            "success": True,
            "session_id": session_id,
            "message_count": len(messages),
            "message": "Session saved successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving chat session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save session: {str(e)}"
        )

# 🚨 BEACON ENDPOINT FOR EMERGENCY SESSION SAVES
@app.post("/chat/sessions/save-beacon")
async def save_session_beacon(request: Request):
    """Emergency session save endpoint for page unload beacon API"""
    try:
        body = await request.body()
        if body:
            data = json.loads(body.decode())
            session_id = data.get("session_id")
            user_id = data.get("user_id", "demo-user-id")
            
            if session_id:
                # Save the session to database
                db_manager.save_chat_session_emergency(user_id, session_id)
                logger.info(f"🚨 Emergency beacon save for session {session_id[:8]}...")
        
        return {"status": "saved"}
    except Exception as e:
        logger.error(f"Beacon save error: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user information with session status"""
    try:
        # Ensure user has an active session
        session_id = get_user_session(current_user["user_id"], force_new=False, auto_create=True)
        
        # Get session info
        session_info = None
        try:
            session_info = db_manager.get_session_info(session_id)
        except Exception as e:
            logger.warning(f"Could not get session info for user {current_user['username']}: {e}")
        
        return {
            "user_id": current_user["user_id"],
            "username": current_user["username"],
            "email": current_user["email"],
            "full_name": current_user.get("full_name"),
            "created_at": current_user["created_at"].isoformat() if isinstance(current_user["created_at"], datetime) else current_user["created_at"],
            "session_id": session_id,
            "session_ready": True,
            "session_info": session_info
        }
    except Exception as e:
        logger.error(f"Error getting user info for {current_user.get('username', 'unknown')}: {e}")
        return {
            "user_id": current_user["user_id"],
            "username": current_user["username"],
            "email": current_user["email"],
            "full_name": current_user.get("full_name"),
            "created_at": current_user["created_at"].isoformat() if isinstance(current_user["created_at"], datetime) else current_user["created_at"],
            "session_ready": False,
            "error": "Session setup failed"
        }

@app.post("/chat", response_model=ChatResponse)
async def chat(message: ChatMessage, request: Request, current_user_data = Depends(auth_service.verify_token) if auth_service else None):
    """
    🔒 SECURE Hybrid chat endpoint with optional authentication:
    1. Optional authentication (works with or without token)
    2. Input validation and sanitization
    3. SQL injection protection
    4. XSS prevention
    5. Rate limiting
    6. Search in Qdrant database using available embedding method
    7. Generate response using OpenAI or Hugging Face
    8. Fallback mechanism for reliability
    """
    try:
        client_ip = request.client.host
        
        # Handle optional authentication
        current_user = None
        user_id = "anonymous"
        
        if current_user_data:
            try:
                # Authenticated user
                current_user = current_user_data
                user_id = current_user.get("user_id", "anonymous")
                logger.info(f"Authenticated user: {current_user.get('username', 'unknown')}")
            except Exception:
                # Authentication failed, continue as anonymous
                logger.info("Authentication failed, continuing as anonymous user")
                pass
        
        # For demo users or legacy login, use a default session
        if user_id == "anonymous":
            user_id = "demo-user-id"  # Use the standard demo user ID for consistency
        
        # 🛡️ ENHANCED RATE LIMITING for chat
        if not rate_limiter.is_allowed(client_ip, "chat"):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many chat requests. Please slow down.",
                headers={"Retry-After": "60"}
            )
        
        # 🔒 COMPREHENSIVE INPUT VALIDATION using security config
        if not message or not hasattr(message, 'message'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid message format"
            )
        
        user_message = message.message
        
        # Type validation
        if not isinstance(user_message, str):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message must be a string"
            )
        
        # Validate message using security config
        is_valid_message, message_error = input_validator.validate_message(user_message)
        if not is_valid_message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message_error
            )
        
        # 🛡️ SECURITY THREAT DETECTION
        # Check for XSS attempts
        is_xss, xss_pattern = input_validator.detect_xss_attempt(user_message)
        if is_xss:
            logger.warning(f"🚨 XSS attempt detected from IP {client_ip}, user {user_id}: {xss_pattern}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Güvenlik nedeniyle mesajınız kabul edilemedi."
            )
        
        # Check for SQL injection attempts
        is_sql_injection, sql_pattern = input_validator.detect_sql_injection(user_message)
        if is_sql_injection:
            logger.warning(f"🚨 SQL injection attempt detected from IP {client_ip}, user {user_id}: {sql_pattern}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Güvenlik nedeniyle mesajınız kabul edilemedi."
            )
        
        # 🧹 SANITIZE INPUT
        user_message = input_validator.sanitize_input(user_message)
        
        username = current_user.get('username', 'anonymous') if current_user else 'anonymous'
        logger.info(f"Secure chat request from user {username} (IP: {client_ip}): {user_message[:50]}...")
        
        # Get or create user session
        session_id = get_user_session(user_id, force_new=False, auto_create=True)
        
        # Generate embedding for search
        try:
            user_embedding = generate_embedding(user_message)
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return ChatResponse(
                response="🤖 Sistem geçici olarak kullanılamıyor. Lütfen daha sonra tekrar deneyin.",
                source="error"
            )
        
        # Search in Qdrant
        try:
            search_results = qdrant_client.search(
                collection_name="mefapex_faq",
                query_vector=user_embedding,
                limit=3,
                with_payload=True
            )
            
            # Process search results
            best_match = None
            if search_results and len(search_results) > 0:
                best_score = search_results[0].score
                logger.info(f"Best match score: {best_score}")
                
                if best_score > 0.85:  # Higher confidence threshold for exact matches
                    best_match = search_results[0].payload
                    context = f"Question: {best_match['question']}\nAnswer: {best_match['answer']}"
                    logger.info(f"Using database context with score: {best_score}")
                else:
                    context = ""
                    logger.info("No relevant database context found")
            else:
                context = ""
                logger.info("No search results found")
                
        except Exception as e:
            logger.error(f"Qdrant search error: {e}")
            context = ""
        
        # Generate response using available method
        try:
            if USE_OPENAI:
                response_text = generate_response_openai(context, user_message)
                source = "openai"
                logger.info("Response generated using OpenAI")
            elif USE_HUGGINGFACE:
                response_text = generate_response_huggingface(context, user_message)
                source = "huggingface"
                logger.info("Response generated using Hugging Face")
            else:
                response_text = "🤖 Sistem geçici olarak kullanılamıyor. Lütfen daha sonra tekrar deneyin."
                source = "error"
                
        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            # Fallback to alternative method
            try:
                if USE_HUGGINGFACE and source != "huggingface":
                    response_text = generate_response_huggingface(context, user_message)
                    source = "huggingface_fallback"
                else:
                    response_text = generate_rule_based_response(user_message)
                    source = "fallback"
            except Exception as e2:
                logger.error(f"Fallback response failed: {e2}")
                response_text = "🤖 Sistem geçici olarak kullanılamıyor. Lütfen daha sonra tekrar deneyin."
                source = "error"
        
        # 🔒 SECURE MESSAGE STORAGE with validation
        try:
            add_message_to_session(session_id, user_message, response_text, source, user_id)
        except Exception as e:
            logger.error(f"Failed to save message securely: {e}")
            # Don't fail the response if storage fails, but log it
        
        username = current_user.get('username', 'anonymous') if current_user else 'anonymous'
        logger.info(f"Secure chat response sent to user {username}, source: {source}")
        
        return ChatResponse(response=response_text, source=source)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in secure chat endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

# 🆕 AUTHENTICATED CHAT WITH SESSION MANAGEMENT  
@app.post("/chat/authenticated", response_model=ChatResponse)
async def chat_authenticated(message: ChatMessage, current_user: dict = Depends(get_current_user)):
    """
    Authenticated chat endpoint with optimized session management:
    1. Auto-ensure user has active session (create if needed)
    2. Search in Qdrant database using available embedding method
    3. Generate response using OpenAI or Hugging Face
    4. Save to user's chat session immediately
    5. Fallback mechanism for reliability
    """
    try:
        user_message = message.message.strip()
        
        if not user_message:
            raise HTTPException(status_code=400, detail="Mesaj boş olamaz")
        
        logger.info(f"User {current_user['username']} message: {user_message}")
        
        # 🚀 OPTIMIZED SESSION MANAGEMENT: Ensure session exists before processing
        try:
            session_id = get_user_session(current_user["user_id"], force_new=False, auto_create=True)
            if not session_id:
                # Force create new session if something went wrong
                session_id = get_user_session(current_user["user_id"], force_new=True, auto_create=True)
            logger.debug(f"Using session {session_id} for user {current_user['username']}")
        except Exception as session_error:
            logger.error(f"Critical session error for user {current_user['username']}: {session_error}")
            # Continue with fallback error response
            response_text = "🤖 Oturum yönetimi hatası. Lütfen çıkış yapıp tekrar giriş yapın."
            return ChatResponse(response=response_text, source="session_error")
        
        # Generate embedding for search
        try:
            user_embedding = generate_embedding(user_message)
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            response_text = "🤖 Sistem geçici olarak kullanılamıyor. Lütfen daha sonra tekrar deneyin."
            source = "error"
            # 🚀 IMMEDIATE SESSION SAVE: Save even on errors
            try:
                add_message_to_session(session_id, user_message, response_text, source, user_id=current_user["user_id"])
            except Exception as save_error:
                logger.error(f"Failed to save error message to session: {save_error}")
            return ChatResponse(response=response_text, source=source)
        
        # Search in Qdrant
        try:
            search_results = qdrant_client.search(
                collection_name="mefapex_faq",
                query_vector=user_embedding,
                limit=3,
                with_payload=True
            )
            
            # Process search results
            best_match = None
            if search_results and len(search_results) > 0:
                best_score = search_results[0].score
                logger.info(f"Best match score: {best_score}")
                
                if best_score > 0.85:  # Higher confidence threshold for exact matches
                    best_match = search_results[0].payload
                    context = f"Question: {best_match['question']}\nAnswer: {best_match['answer']}"
                    logger.info(f"Using database context with score: {best_score}")
                else:
                    context = ""
                    logger.info("No relevant database context found")
            else:
                context = ""
                logger.info("No search results found")
                
        except Exception as e:
            logger.error(f"Qdrant search error: {e}")
            context = ""
        
        # Generate response using available method
        try:
            if USE_OPENAI:
                response_text = generate_response_openai(context, user_message)
                source = "openai"
                logger.info("Response generated using OpenAI")
            elif USE_HUGGINGFACE:
                response_text = generate_response_huggingface(context, user_message)
                source = "huggingface"
                logger.info("Response generated using Hugging Face")
            else:
                response_text = "🤖 Sistem geçici olarak kullanılamıyor. Lütfen daha sonra tekrar deneyin."
                source = "error"
                
        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            # Fallback to alternative method
            try:
                if USE_HUGGINGFACE and source != "huggingface":
                    response_text = generate_response_huggingface(context, user_message)
                    source = "huggingface_fallback"
                    logger.info("Using Hugging Face as fallback")
                else:
                    response_text = "🤖 Üzgünüm, bir hata oluştu. Lütfen tekrar deneyin."
                    source = "error"
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {fallback_error}")
                response_text = "🤖 Sistem geçici olarak kullanılamıyor. Lütfen daha sonra tekrar deneyin."
                source = "error"
        
        # Save to session
        try:
            add_message_to_session(session_id, user_message, response_text, source, user_id=current_user["user_id"])
            logger.debug(f"Message saved to session {session_id} for user {current_user['username']}")
        except Exception as save_error:
            logger.error(f"Failed to save message to session for user {current_user['username']}: {save_error}")
            # Don't fail the request, just log the error
        
        return ChatResponse(response=response_text, source=source)
        
    except Exception as e:
        logger.error(f"Authenticated chat endpoint error: {e}")
        response_text = "🤖 Bir hata oluştu. Lütfen tekrar deneyin."
        source = "error"
        
        # Try to save to session even on error with enhanced error handling
        try:
            if 'session_id' not in locals():
                session_id = get_user_session(current_user["user_id"], force_new=False, auto_create=True)
            add_message_to_session(session_id, user_message if 'user_message' in locals() else "Hata", response_text, source, user_id=current_user["user_id"])
            logger.debug(f"Error message saved to session for user {current_user['username']}")
        except Exception as save_error:
            logger.error(f"Critical: Failed to save error message to session for user {current_user['username']}: {save_error}")
            
        return ChatResponse(response=response_text, source=source)

@app.get("/system/status")
async def system_status():
    """Get current system configuration"""
    model_info = model_manager.get_model_info()
    cache_stats = response_cache.get_stats()
    db_stats = db_manager.get_stats()
    
    return {
        "openai_enabled": USE_OPENAI,
        "huggingface_enabled": USE_HUGGINGFACE,
        "embedding_method": "huggingface" if USE_HUGGINGFACE else "openai",
        "response_method": "openai" if USE_OPENAI else "huggingface",
        "model_info": model_info,
        "cache_stats": cache_stats,
        "database_stats": db_stats,
        "websocket_stats": websocket_manager.get_connection_stats(),
        "version": "optimized_v3.0_with_caching_and_websockets"
    }

@app.get("/ai/models")
async def available_models():
    """Get available AI models information"""
    model_info = model_manager.get_model_info()
    return {
        "current_config": model_info,
        "available_models": {
            "microsoft/DialoGPT-small": {
                "size": "117M parameters",
                "description": "Fast, good conversations",
                "download_size": "~351MB",
                "speed": "Fast"
            },
            "microsoft/DialoGPT-medium": {
                "size": "354M parameters", 
                "description": "Better quality conversations",
                "download_size": "~2GB",
                "speed": "Medium"
            },
            "facebook/blenderbot_small-90M": {
                "size": "90M parameters",
                "description": "Chatbot optimized",
                "download_size": "~400MB", 
                "speed": "Very Fast"
            },
            "google/flan-t5-small": {
                "size": "80M parameters",
                "description": "Instruction following",
                "download_size": "~300MB",
                "speed": "Fast"
            },
            "gpt2": {
                "size": "124M parameters",
                "description": "General text generation", 
                "download_size": "~500MB",
                "speed": "Fast"
            }
        },
        "performance_optimization": {
            "model_caching": "✅ Enabled",
            "response_caching": "✅ Enabled", 
            "database_pooling": "✅ Enabled",
            "websocket_support": "✅ Enabled"
        },
        "instructions": "Change model in .env file: HUGGINGFACE_MODEL=model_name"
    }

# 🔌 WEBSOCKET ENDPOINTS
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """
    WebSocket endpoint for real-time chat communication
    """
    try:
        # For demo purposes, accept any user_id
        # In production, you should validate the user_id with proper authentication
        username = f"user_{user_id}" if user_id != "demo" else "demo"
        
        await websocket_manager.connect(websocket, user_id, username)
        logger.info(f"🔌 WebSocket connected: {username}")
        
        try:
            while True:
                # Receive message from client
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                # Handle different message types
                message_type = message_data.get('type', 'chat_message')
                
                if message_type == 'chat_message':
                    await handle_websocket_chat_message(websocket, user_id, message_data)
                elif message_type == 'ping':
                    await websocket_manager.send_personal_message({
                        'type': 'pong',
                        'timestamp': datetime.utcnow().isoformat()
                    }, websocket)
                elif message_type == 'get_history':
                    await handle_websocket_get_history(websocket, user_id)
                else:
                    await message_handler.handle_message(websocket, message_data)
                    
        except WebSocketDisconnect:
            logger.info(f"🔌 WebSocket disconnected: {username}")
        except Exception as e:
            logger.error(f"WebSocket error for {username}: {e}")
            await websocket_manager.send_personal_message({
                'type': 'error',
                'message': f'Server error: {str(e)}',
                'timestamp': datetime.utcnow().isoformat()
            }, websocket)
    
    finally:
        websocket_manager.disconnect(websocket)

async def handle_websocket_chat_message(websocket: WebSocket, user_id: str, message_data: dict):
    """
    Handle chat message received via WebSocket
    """
    try:
        user_message = message_data.get('message', '').strip()
        
        if not user_message:
            await websocket_manager.send_personal_message({
                'type': 'error',
                'message': 'Message cannot be empty',
                'timestamp': datetime.utcnow().isoformat()
            }, websocket)
            return
        
        # Send typing indicator
        await websocket_manager.send_personal_message({
            'type': 'bot_typing',
            'typing': True,
            'timestamp': datetime.utcnow().isoformat()
        }, websocket)
        
        # Generate embedding for search
        try:
            user_embedding = generate_embedding(user_message)
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            await websocket_manager.send_personal_message({
                'type': 'chat_response',
                'response': "🤖 Sistem geçici olarak kullanılamıyor. Lütfen daha sonra tekrar deneyin.",
                'source': "error",
                'timestamp': datetime.utcnow().isoformat()
            }, websocket)
            return
        
        # Search in Qdrant
        context = ""
        try:
            search_results = qdrant_client.search(
                collection_name="mefapex_faq",
                query_vector=user_embedding,
                limit=3,
                with_payload=True
            )
            
            if search_results and len(search_results) > 0:
                best_score = search_results[0].score
                if best_score > 0.85:
                    best_match = search_results[0].payload
                    context = f"Question: {best_match['question']}\nAnswer: {best_match['answer']}"
                else:
                    context = ""
            else:
                context = ""
        except Exception as e:
            logger.error(f"Qdrant search error: {e}")
        
        # Generate response
        try:
            if USE_OPENAI:
                response_text = generate_response_openai(context, user_message)
                source = "openai"
            elif USE_HUGGINGFACE:
                response_text = generate_response_huggingface(context, user_message)
                source = "huggingface"
            else:
                response_text = generate_ai_response_local(user_message)
                source = "local"
        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            response_text = "🤖 Üzgünüm, bir hata oluştu. Lütfen tekrar deneyin."
            source = "error"
        
        # Save to database (for authenticated users)
        try:
            session_id = get_user_session(user_id)
            add_message_to_session(session_id, user_message, response_text, source, user_id=user_id)
        except Exception as e:
            logger.error(f"Failed to save message to database: {e}")
        
        # Stop typing indicator and send response
        await websocket_manager.send_personal_message({
            'type': 'bot_typing',
            'typing': False,
            'timestamp': datetime.utcnow().isoformat()
        }, websocket)
        
        await websocket_manager.send_personal_message({
            'type': 'chat_response',
            'response': response_text,
            'source': source,
            'timestamp': datetime.utcnow().isoformat(),
            'cached': 'cached' in response_text.lower()
        }, websocket)
        
    except Exception as e:
        logger.error(f"Error handling WebSocket chat message: {e}")
        await websocket_manager.send_personal_message({
            'type': 'error',
            'message': f'Failed to process message: {str(e)}',
            'timestamp': datetime.utcnow().isoformat()
        }, websocket)

async def handle_websocket_get_history(websocket: WebSocket, user_id: str):
    """
    Handle request to get chat history via WebSocket
    """
    try:
        # Get last 10 messages from database
        messages = db_manager.get_chat_history(user_id, limit=10)
        
        await websocket_manager.send_personal_message({
            'type': 'chat_history',
            'messages': messages,
            'total_messages': len(messages),
            'timestamp': datetime.utcnow().isoformat()
        }, websocket)
        
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        await websocket_manager.send_personal_message({
            'type': 'error',
            'message': f'Failed to get chat history: {str(e)}',
            'timestamp': datetime.utcnow().isoformat()
        }, websocket)

async def handle_websocket_get_history(websocket: WebSocket, user_id: str):
    """
    Handle request for chat history via WebSocket
    """
    try:
        messages = db_manager.get_chat_history(user_id, limit=20)
        
        await websocket_manager.send_personal_message({
            'type': 'chat_history',
            'messages': messages,
            'timestamp': datetime.utcnow().isoformat()
        }, websocket)
        
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        await websocket_manager.send_personal_message({
            'type': 'error',
            'message': f'Failed to get chat history: {str(e)}',
            'timestamp': datetime.utcnow().isoformat()
        }, websocket)

# 📊 PERFORMANCE AND MONITORING ENDPOINTS
@app.get("/performance/cache")
async def get_cache_performance():
    """Get cache performance statistics"""
    return {
        "response_cache": response_cache.get_stats(),
        "model_cache": model_manager.get_model_info()["cache_info"] if "cache_info" in model_manager.get_model_info() else {},
        "popular_queries": response_cache.get_popular_entries(10)
    }

@app.post("/performance/cache/clear")
async def clear_caches():
    """Clear all caches for performance testing"""
    response_cache.clear()
    model_manager.clear_caches()
    
    return {
        "message": "All caches cleared",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/performance/database")
async def get_database_performance():
    """Get database performance statistics"""
    return db_manager.get_stats()

@app.get("/performance/websockets")
async def get_websocket_performance():
    """Get WebSocket connection statistics"""
    return websocket_manager.get_connection_stats()

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting MEFAPEX Chatbot")
    print(f"🤖 OpenAI: {'✅ Enabled' if USE_OPENAI else '❌ Disabled'}")
    print(f"🆓 Hugging Face: {'✅ Enabled' if USE_HUGGINGFACE else '❌ Disabled'}")
    print("🌐 Visit: http://localhost:8000")
    print("🔑 Login: demo / 1234")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
