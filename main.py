from fastapi import FastAPI, HTTPException, Depends, status, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
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
from passlib.context import CryptContext
from jose import JWTError, jwt
import uuid
import json
import asyncio
import secrets
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

# Import optimized components
from database_manager import DatabaseManager
from model_manager import model_manager
from response_cache import response_cache
from websocket_manager import websocket_manager, message_handler

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
# Generate secure SECRET_KEY if not provided
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    if ENVIRONMENT == "production":
        logger.error("🚨 SECURITY ALERT: SECRET_KEY not set in production!")
        raise RuntimeError(
            "SECRET_KEY must be set in production environment variables."
        )
    else:
        # Generate a secure random key for development
        SECRET_KEY = secrets.token_urlsafe(32)
        logger.warning("⚠️ Using auto-generated SECRET_KEY for development")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

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

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# In-memory storage (replace with database in production)
users_db = {}
chat_sessions = {}

# Initialize database manager
db_manager = DatabaseManager()

# 🔒 RATE LIMITING IMPLEMENTATION
class RateLimiter:
    def __init__(self):
        self.requests = defaultdict(list)
        self.chat_requests = defaultdict(list)
        self.max_requests_per_minute = int(os.getenv("RATE_LIMIT_REQUESTS", "60"))
        self.max_chat_requests_per_minute = int(os.getenv("RATE_LIMIT_CHAT", "20"))
        
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

# 🔒 PRODUCTION CORS CONFIGURATION
# Get allowed origins from environment with secure defaults
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# Environment-based CORS configuration
if ENVIRONMENT == "production":
    # Strict CORS for production - NO WILDCARDS
    cors_origins = [origin.strip() for origin in ALLOWED_ORIGINS if origin.strip() and origin.strip() != "*"]
    cors_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    cors_headers = ["accept", "authorization", "content-type", "x-csrf-token", "x-requested-with"]
    allow_credentials = True
    
    if not cors_origins:
        logger.error("🚨 SECURITY ALERT: No valid CORS origins configured for production!")
        raise RuntimeError("ALLOWED_ORIGINS must be set for production with specific domains (no wildcards)")
        
else:
    # More relaxed CORS for development (but still not wildcard)
    cors_origins = [origin.strip() for origin in ALLOWED_ORIGINS if origin.strip()]
    if not cors_origins:
        cors_origins = ["http://localhost:3000", "http://localhost:8000", "http://127.0.0.1:3000", "http://127.0.0.1:8000"]
    cors_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    cors_headers = ["*"]
    allow_credentials = True

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

# Startup event for model warmup
@app.on_event("startup")
async def startup_event():
    """Initialize and warm up models on startup"""
    logger.info("🚀 Starting MEFAPEX Chatbot API")
    try:
        # Warm up models for better first-request performance
        await startup_warmup()
        logger.info("✅ Startup warmup completed")
    except Exception as e:
        logger.warning(f"⚠️ Startup warmup failed: {e}")
    
    # Start memory monitoring if available
    if MEMORY_MONITORING_AVAILABLE and ENVIRONMENT == "production":
        try:
            setup_memory_monitoring()
            logger.info("🧠 Memory monitoring started")
        except Exception as e:
            logger.warning(f"⚠️ Memory monitoring setup failed: {e}")
    
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

# 🔐 AUTHENTICATION UTILITIES
def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"
    
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        return False, "Password must contain at least one special character"
    
    return True, "Password is strong"

def verify_password(plain_password, hashed_password):
    """Verify a password against its hash"""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False

def get_password_hash(password):
    """Hash a password with enhanced security"""
    try:
        return pwd_context.hash(password)
    except Exception as e:
        logger.error(f"Password hashing error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password processing failed"
        )

def get_user(username: str):
    """Get user from database"""
    return users_db.get(username)

def authenticate_user(username: str, password: str):
    """Authenticate user credentials"""
    user = get_user(username)
    if not user:
        return False
    if not verify_password(password, user["hashed_password"]):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token with enhanced security"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Add security claims
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "jti": str(uuid.uuid4()),  # Unique token ID
        "iss": "mefapex-api",  # Issuer
    })
    
    try:
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    except Exception as e:
        logger.error(f"Token creation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token creation failed"
        )

# 🛡️ BRUTE FORCE PROTECTION
class BruteForceProtection:
    def __init__(self):
        self.failed_attempts = defaultdict(list)
        self.blocked_ips = defaultdict(datetime)
        self.max_attempts = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
        self.block_duration = int(os.getenv("BLOCK_DURATION_MINUTES", "15"))
    
    def is_blocked(self, client_ip: str) -> bool:
        """Check if IP is currently blocked"""
        if client_ip in self.blocked_ips:
            if datetime.utcnow() < self.blocked_ips[client_ip]:
                return True
            else:
                # Unblock expired blocks
                del self.blocked_ips[client_ip]
                self.failed_attempts[client_ip] = []
        return False
    
    def record_failed_attempt(self, client_ip: str):
        """Record a failed login attempt"""
        now = datetime.utcnow()
        
        # Clean old attempts (older than 1 hour)
        self.failed_attempts[client_ip] = [
            attempt for attempt in self.failed_attempts[client_ip]
            if now - attempt < timedelta(hours=1)
        ]
        
        # Add current attempt
        self.failed_attempts[client_ip].append(now)
        
        # Check if should block
        if len(self.failed_attempts[client_ip]) >= self.max_attempts:
            self.blocked_ips[client_ip] = now + timedelta(minutes=self.block_duration)
            logger.warning(f"🚨 IP {client_ip} blocked due to too many failed login attempts")
    
    def record_successful_attempt(self, client_ip: str):
        """Record a successful login attempt"""
        # Clear failed attempts on successful login
        if client_ip in self.failed_attempts:
            del self.failed_attempts[client_ip]

brute_force_protection = BruteForceProtection()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated user with enhanced security"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
        
        # Enhanced token validation
        if not token or len(token) < 10:
            raise credentials_exception
            
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        
        if username is None:
            raise credentials_exception
            
        # Check token expiration
        exp_timestamp = payload.get("exp")
        if exp_timestamp:
            exp_datetime = datetime.fromtimestamp(exp_timestamp)
            if datetime.utcnow() > exp_datetime:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has expired",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        
        token_data = TokenData(username=username)
        
    except JWTError as e:
        logger.warning(f"JWT validation error: {e}")
        raise credentials_exception
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise credentials_exception
    
    # Handle demo user with rate limiting
    if token_data.username == "demo":
        return {
            "user_id": "demo-user-id",
            "username": "demo",
            "email": "demo@mefapex.com",
            "full_name": "Demo User",
            "created_at": datetime.utcnow(),
            "is_active": True,
            "is_demo": True,
            "rate_limit": "strict"  # Demo users have stricter limits
        }
    
    # Handle regular users
    user = get_user(username=token_data.username)
    if user is None:
        raise credentials_exception
        
    # Check if user is still active
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
        
    return user

def get_user_session(user_id: str, force_new: bool = False) -> str:
    """Get or create user session ID (persistent) with session management"""
    return db_manager.get_or_create_session(user_id, force_new=force_new)

def add_message_to_session(session_id: str, user_message: str, bot_response: str, source: str, user_id: str = None):
    """Add message to chat session (persistent)"""
    if user_id is None:
        # Try to infer user_id from session (legacy fallback)
        user_id = None
    db_manager.add_message(session_id, user_id, user_message, bot_response, source)

@app.get("/")
async def read_root():
    return FileResponse("static/index.html")

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
        
        # Validate username (security check)
        if len(user.username) < 3 or len(user.username) > 50:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username must be between 3 and 50 characters"
            )
        
        # Check for prohibited usernames
        prohibited_usernames = ["admin", "root", "system", "api", "test", "demo"]
        if user.username.lower() in prohibited_usernames:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username not allowed"
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
    if brute_force_protection.is_blocked(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. IP temporarily blocked.",
            headers={"Retry-After": str(brute_force_protection.block_duration * 60)}
        )
    
    # Rate limiting for login attempts
    if not rate_limiter.is_allowed(client_ip, "general"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later."
        )
    
    # Input validation
    if not form_data.username or not form_data.password:
        brute_force_protection.record_failed_attempt(client_ip)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username and password are required"
        )
    
    # Check for demo user first (with rate limiting)
    if form_data.username == "demo" and form_data.password == "1234":
        brute_force_protection.record_successful_attempt(client_ip)
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": "demo", "ip": client_ip}, expires_delta=access_token_expires
        )
        logger.info(f"Demo user login from IP: {client_ip}")
        return {"access_token": access_token, "token_type": "bearer"}
    
    # Check regular users
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        brute_force_protection.record_failed_attempt(client_ip)
        logger.warning(f"Failed login attempt for user: {form_data.username} from IP: {client_ip}")
        
        # Generic error message to prevent username enumeration
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user account is active
    if not user.get("is_active", True):
        brute_force_protection.record_failed_attempt(client_ip)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )
    
    # Successful login
    brute_force_protection.record_successful_attempt(client_ip)
    
    # Update user login information
    user["last_login"] = datetime.utcnow()
    user["last_login_ip"] = client_ip
    user["failed_login_attempts"] = 0
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"], "ip": client_ip}, 
        expires_delta=access_token_expires
    )
    
    logger.info(f"Successful login for user: {form_data.username} from IP: {client_ip}")
    return {"access_token": access_token, "token_type": "bearer"}

# 🆕 LEGACY LOGIN (for backward compatibility)
@app.post("/login-legacy", response_model=LoginResponse)
async def login_legacy(request: LoginRequest):
    """Legacy login endpoint for demo purposes"""
    # Keep demo login for testing
    if request.username == "demo" and request.password == "1234":
        return LoginResponse(success=True, message="Giriş başarılı")
    
    # Check real users
    user = authenticate_user(request.username, request.password)
    if user:
        return LoginResponse(success=True, message="Giriş başarılı")
    else:
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
    """Generate AI response using enhanced local intelligence"""
    # Convert to lowercase for analysis
    msg_lower = user_message.lower().strip()
    
    # Türkçe öncelikli selamlama ve basit sorular
    turkish_greetings = [
        "merhaba", "selam", "selamun aleyküm", "selamünaleyküm", 
        "günaydın", "iyi günler", "iyi akşamlar", "iyi geceler",
        "nasılsın", "nasilsin", "nasıl gidiyor", "naber", "ne haber",
        "hoş geldin", "hoşgeldin", "selam olsun",
        # İngilizce selamlamalar (düşük öncelik)
        "hello", "hi", "hey"
    ]
    
    if any(word in msg_lower for word in turkish_greetings):
        return """👋 **Merhaba! Hoş geldiniz!**

Ben MEFAPEX fabrikasının AI asistanıyım. Size yardımcı olmaktan mutluluk duyarım!

**Size yardımcı olabileceğim konular:**
• Fabrika ile ilgili sorular (çalışma saatleri, kurallar vb.)
• Genel bilgi soruları
• Teknoloji ve AI konuları
• Basit hesaplamalar
• Ve daha fazlası...

Nasıl yardımcı olabilirim? 😊"""
    
    # Python ve Programlama Soruları - Türkçe öncelikli
    turkish_programming_terms = [
        "python", "programlama", "kod", "yazılım", "kodlama", "yazılım geliştirme",
        "bilgisayar programcılığı", "uygulama geliştirme", "web geliştirme",
        "mobil uygulama", "veri tabanı", "algoritma", "değişken", "fonksiyon",
        # İngilizce terimler (düşük öncelik)
        "programming", "coding", "software", "development"
    ]
    
    if any(word in msg_lower for word in turkish_programming_terms):
        return """🐍 **Python ve Programlama Hakkında**

Python, öğrenmesi kolay ve güçlü bir programlama dilidir.

**Başlangıç için öneriler:**
• Python.org'dan ücretsiz indirebilirsiniz
• Online kurslar: Codecademy, Python.org tutorials
• Temel konular: değişkenler, döngüler, fonksiyonlar
• Pratik projeler yaparak öğrenin

**Kullanım alanları:**
• Web geliştirme (Django, Flask)
• Veri analizi (Pandas, NumPy)
• Yapay zeka (TensorFlow, scikit-learn)
• Otomasyon ve scripting

Hangi alanda odaklanmak istiyorsunuz? 🚀"""

    # Teknoloji Genel - Türkçe öncelikli
    elif any(word in msg_lower for word in [
        "teknoloji", "bilgisayar", "internet", "dijital", "elektronik",
        "yazılım", "donanım", "ağ", "wifi", "bluetooth", "akıllı telefon",
        "tablet", "laptop", "masaüstü", "veri", "bulut", "siber güvenlik",
        "mobil", "uygulama", "web sitesi", "sosyal medya",
        # İngilizce terimler (düşük öncelik)
        "technology", "computer", "software", "hardware"
    ]):
        return """💻 **Modern Teknoloji**

Teknoloji hayatımızı sürekli şekillendiriyor.

**Güncel Trendler:**
• **Bulut Bilişim**: Her yerden erişilebilir veriler
• **Mobil Teknolojiler**: Akıllı telefonlar ve uygulamalar
• **Nesnelerin İnterneti (IoT)**: Bağlı cihazlar
• **Siber Güvenlik**: Dijital koruma
• **Blockchain**: Güvenli veri paylaşımı

**Öğrenme Kaynakları:**
• Online platformlar (Coursera, Udemy)
• YouTube eğitim kanalları
• Teknoloji blogları ve podcastler

Hangi teknoloji alanı sizi ilgilendiriyor? 🌐"""

    # Öğrenme ve Eğitim
    elif any(word in msg_lower for word in ["öğren", "eğitim", "ders", "kurs", "learn", "study"]):
        return """📚 **Öğrenme ve Gelişim**

Sürekli öğrenmek modern dünyanın anahtarıdır.

**Etkili Öğrenme Yöntemleri:**
• **Aktif Öğrenme**: Sadece okumak değil, pratik yapmak
• **Proje Tabanlı**: Gerçek projelerle öğrenmek
• **Topluluk**: Online forumlar ve gruplar
• **Düzenli Tekrar**: Spaced repetition tekniği

**Ücretsiz Kaynaklar:**
• Khan Academy, Coursera (audit)
• YouTube eğitim kanalları
• GitHub açık kaynak projeleri
• Stack Overflow (programlama)

Hangi konuda gelişmek istiyorsunuz? 🎓"""

    # İş ve Kariyer
    elif any(word in msg_lower for word in ["iş", "kariyer", "job", "career", "work", "meslek"]):
        return """💼 **Kariyer ve İş Dünyası**

Modern iş dünyası sürekli değişiyor.

**Gelecekteki Beceriler:**
• **Dijital Okuryazarlık**: Teknoloji kullanımı
• **Problem Çözme**: Analitik düşünme
• **İletişim**: Hem yazılı hem sözlü
• **Uyum Yeteneği**: Değişime açık olma
• **İşbirliği**: Takım çalışması

**Kariyer Tavsiyeleri:**
• LinkedIn profilinizi güncel tutun
• Sürekli yeni beceriler edinin
• Network oluşturun ve güçlendirin
• Kişisel projeler geliştirin

Hangi sektörde çalışmayı hedefliyorsunuz? 🚀"""

    # Sağlık ve Yaşam
    elif any(word in msg_lower for word in ["sağlık", "health", "yaşam", "life", "beslenme", "spor"]):
        return """🏥 **Sağlık ve Yaşam Kalitesi**

Sağlıklı yaşam, hem fiziksel hem mental iyilik hali gerektirir.

**Temel Prensipler:**
• **Dengeli Beslenme**: Çeşitli besin grupları
• **Düzenli Egzersiz**: Haftada en az 150 dakika
• **Yeterli Uyku**: 7-9 saat kaliteli uyku
• **Stres Yönetimi**: Meditasyon, hobi aktiviteleri
• **Sosyal Bağlantılar**: Aile ve arkadaş ilişkileri

**Dijital Sağlık:**
• Sağlık uygulamaları kullanın
• Düzenli kontroller yaptırın
• Güvenilir kaynaklardan bilgi alın

Not: Sağlık konularında mutlaka uzman görüşü alın! 🌟"""

    # Genel selamlama ve tanışma
    elif any(word in msg_lower for word in ["merhaba", "selam", "hi", "hello", "hey", "nasılsın", "kimsin", "sen kim"]):
        return """👋 **Merhaba! Tanışmak güzel!**

Ben MEFAPEX fabrikasının AI asistanıyım. Size yardımcı olmak için buradayım!

**Size yardımcı olabileceğim konular:**
• 🏭 Fabrika ile ilgili sorular
• 💻 Teknoloji ve programlama
• 🤖 Yapay zeka ve AI
• 📚 Öğrenme ve gelişim tavsiyeleri
• 💼 Kariyer ve iş dünyası
• 🔢 Basit matematik hesaplamaları

**Nasıl çalışırım:**
• Sorularınızı anlayıp uygun yanıtlar vermeye çalışırım
• Fabrika veritabanını tarayabilir, genel bilgilerimi kullanabilirim
• Sürekli öğrenmeye ve gelişmeye odaklıyım

Hangi konuda size yardımcı olabilirim? 😊"""

    # Teşekkür ve veda
    elif any(word in msg_lower for word in ["teşekkür", "thanks", "sağol", "görüşürüz", "bye", "hoşça kal"]):
        return """🙏 **Rica ederim!**

Size yardımcı olabildiysem ne mutlu bana! 

**Unutmayın:**
• Her zaman burada olmaya devam edeceğim
• Yeni sorularınız için sormaktan çekinmeyin
• Sürekli öğrenmeye devam edin

İyi günler dilerim! Tekrar görüşmek üzere! 🌟"""

    # Fabrika ve MEFAPEX
    elif any(word in msg_lower for word in ["mefapex", "fabrika", "factory", "üretim", "işçi", "çalışan"]):
        return """🏭 **MEFAPEX Fabrikası**

MEFAPEX, modern üretim teknolojileri ile kaliteli ürünler üreten bir fabrikadır.

**Fabrika Değerleri:**
• 🛡️ **Güvenlik**: Çalışan güvenliği öncelik
• 🌟 **Kalite**: Yüksek standartlarda üretim
• 🌱 **Sürdürülebilirlik**: Çevreye duyarlı üretim
• 👥 **İnsan Odaklı**: Çalışan refahı önemli
• 🔧 **İnovasyon**: Sürekli gelişim ve teknoloji

**Size yardımcı olabileceğim fabrika konuları:**
• Çalışma saatleri ve vardiyalar
• Güvenlik kuralları ve prosedürler
• İzin ve tatil prosedürleri
• Genel fabrika bilgileri

Spesifik bir konu hakkında soru sormak ister misiniz? 🤝"""

    # Zamana dayalı sorular
    elif any(word in msg_lower for word in ["saat", "zaman", "time", "ne zaman", "when"]):
        return """⏰ **Zaman ve Zamanlama**

Zamanlama konularında size yardımcı olmaya çalışayım.

**Genel Zaman Bilgileri:**
• Standart çalışma saatleri: Genellikle 08:00-17:00
• Mola saatleri: Öğle arası ve çay molaları
• Vardiya sistemleri: Bazı bölümlerde 24 saat üretim

**Daha spesifik bilgi için şunları sorabilirsiniz:**
• "Çalışma saatleri nedir?"
• "Mola saatleri ne zaman?"
• "Vardiya değişim saatleri nedir?"
• "Fabrika ne zaman açık?"

Hangi zaman konusunda bilgi almak istiyorsunuz? 📅"""

    # Matematiksel sorular
    elif any(word in msg_lower for word in ["hesapla", "matematik", "math", "sayı", "number", "hesap"]):
        return """🔢 **Matematik ve Hesaplama**

Basit matematik işlemlerinde size yardımcı olabilirim!

**Yapabileceğim hesaplamalar:**
• ➕ Toplama: "15 + 27"
• ➖ Çıkarma: "100 - 35" 
• ✖️ Çarpma: "8 × 12" veya "8 x 12"
• ➗ Bölme: "144 ÷ 12"
• 📊 Yüzde: "200'nin %15'i"

**Örnek kullanım:**
• "25 + 17 kaç eder?"
• "120'nin %20'si nedir?"
• "15 x 8 = ?"

Hesaplamanızı yukarıdaki formatlardan birinde yazabilir misiniz? 📱"""

    # Yardım ve rehberlik
    elif any(word in msg_lower for word in ["yardım", "help", "nasıl", "how", "rehber"]):
        return """🆘 **Yardım ve Rehberlik**

Size en iyi şekilde yardımcı olmak istiyorum!

**Bana şunları sorabilirsiniz:**
• 🏭 **Fabrika konuları**: Çalışma saatleri, kurallar, prosedürler
• 💻 **Teknoloji**: Python, AI, programlama, bilgisayar
• 📚 **Öğrenme**: Eğitim kaynakları, beceri geliştirme
• 🔢 **Hesaplama**: Basit matematik işlemleri
• 💼 **Kariyer**: İş dünyası, beceriler, tavsiyelr

**Daha iyi yanıt almak için:**
• Sorularınızı net ve açık yazın
• Spesifik konular belirtin
• Örnek vererek detaylandırın

Hangi konuda yardıma ihtiyacınız var? 💪"""

    # Default: Akıllı genel yanıt
    else:
        # Türkçe öncelikli soru kelimesi tespiti
        turkish_question_words = [
            # Temel Türkçe soru kelimeleri
            "ne", "nedir", "nesi", "neyi", "neye", "neden", "nedeni",
            "nasıl", "nasıl", "niçin", "niye", "neden dolayı",
            "hangi", "hangisi", "hangisini", "hangisine",
            "kim", "kimi", "kimin", "kimle", "kimden",
            "nerede", "neresi", "nereye", "nereden",
            "ne zaman", "nezaman", "kaçta", "saat kaçta",
            "kaç", "kaçar", "kaç tane", "ne kadar",
            "var mı", "mevcut mu", "bulunuyor mu",
            # Ek Türkçe soru kalıpları
            "acaba", "yoksa", "şu an", "şimdi",
            "bugün", "yarın", "dün", "hafta",
            # İngilizce soru kelimeler (düşük öncelik)
            "what", "how", "when", "where", "why", "which", "who"
        ]
        is_question = any(word in msg_lower for word in turkish_question_words) or "?" in user_message
        
        if is_question:
            return f"""🤔 **'{user_message}' hakkında Mefapex bilgi tabanımızda hazır bir kayıt bulamadım.**

**Daha iyi yardım için şunları deneyebilirsiniz:**
• Soruyu daha detaylandırın
• Hangi alanda bilgi istediğinizi belirtin
• Fabrika ile ilgili sorular için spesifik konular sorun

**Daha hızlı ilerlemek için şunları paylaşabilirsiniz:**
• **Konu:** üretim hattı / ekipman / yazılım / sipariş / kalite
• **Hangi hat veya ekipman etkilendi?**
• **Kısa açıklama** veya varsa hata kodu/ekran görüntüsü
• **Tesis adı ve tarih/saat**"""
        else:
            return f"""💬 **'{user_message}' konusunda...**

Bu konuyu anlıyorum ve size yardımcı olmaya çalışıyorum. 

**Size şunları önerebilirim:**
• Bu konuda daha spesifik sorular sorabilirsiniz
• Hangi açıdan yaklaşmak istediğinizi belirtebilirsiniz
• İlgili diğer konular hakkında soru sorabilirsiniz

**Ben şu konularda uzmanım:**
• 🏭 MEFAPEX fabrika bilgileri • 💻 Teknoloji ve programlama 
• 🤖 Yapay zeka • 📚 Eğitim ve öğrenme • 🔢 Matematik

Hangi açıdan size yardımcı olabilirim? 🎯"""

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

# 🆕 NEW SESSION-BASED HISTORY ENDPOINTS
@app.get("/chat/sessions/{user_id}")
async def get_chat_sessions(user_id: str, current_user: dict = Depends(get_current_user)):
    """Get chat sessions with history (max 15 sessions per user)"""
    try:
        if current_user["user_id"] != user_id and not current_user.get("is_admin", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        sessions = db_manager.get_chat_sessions_with_history(user_id, limit=15)
        return {
            "user_id": user_id,
            "sessions": sessions,
            "total_sessions": len(sessions)
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
    """Start a new chat session for the user"""
    try:
        if current_user["user_id"] != user_id and not current_user.get("is_admin", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        new_session_id = db_manager.start_new_session(user_id)
        return {
            "success": True,
            "message": "New chat session started",
            "session_id": new_session_id
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

@app.get("/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user information"""
    return {
        "user_id": current_user["user_id"],
        "username": current_user["username"],
        "email": current_user["email"],
        "full_name": current_user.get("full_name"),
        "created_at": current_user["created_at"].isoformat() if isinstance(current_user["created_at"], datetime) else current_user["created_at"]
    }

@app.post("/chat", response_model=ChatResponse)
async def chat(message: ChatMessage, request: Request):
    """
    Hybrid chat endpoint with enhanced security:
    1. Search in Qdrant database using available embedding method
    2. Generate response using OpenAI or Hugging Face
    3. Fallback mechanism for reliability
    4. Rate limiting and input validation
    """
    try:
        client_ip = request.client.host
        
        # Rate limiting for chat
        if not rate_limiter.is_allowed(client_ip, "chat"):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many chat requests. Please slow down.",
                headers={"Retry-After": "60"}
            )
        
        user_message = message.message.strip()
        
        # Input validation and sanitization
        if not user_message:
            raise HTTPException(status_code=400, detail="Mesaj boş olamaz")
        
        if len(user_message) > 1000:  # Prevent extremely long messages
            raise HTTPException(
                status_code=400, 
                detail="Mesaj çok uzun. Lütfen 1000 karakterden kısa bir mesaj gönderin."
            )
        
        # Basic XSS prevention
        if any(tag in user_message.lower() for tag in ['<script', '<iframe', '<object', '<embed']):
            raise HTTPException(
                status_code=400,
                detail="Güvenlik nedeniyle mesajınız kabul edilemedi."
            )
        
        logger.info(f"User message from IP {client_ip}: {user_message[:50]}...")
        
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
                    logger.info("Using Hugging Face as fallback")
                else:
                    response_text = "🤖 Üzgünüm, bir hata oluştu. Lütfen tekrar deneyin."
                    source = "error"
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {fallback_error}")
                response_text = "🤖 Sistem geçici olarak kullanılamıyor. Lütfen daha sonra tekrar deneyin."
                source = "error"
        
        return ChatResponse(response=response_text, source=source)
        
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        return ChatResponse(
            response="🤖 Bir hata oluştu. Lütfen tekrar deneyin.",
            source="error"
        )

# 🆕 AUTHENTICATED CHAT WITH SESSION MANAGEMENT
@app.post("/chat/authenticated", response_model=ChatResponse)
async def chat_authenticated(message: ChatMessage, current_user: dict = Depends(get_current_user)):
    """
    Authenticated chat endpoint with session management:
    1. Search in Qdrant database using available embedding method
    2. Generate response using OpenAI or Hugging Face
    3. Save to user's chat session
    4. Fallback mechanism for reliability
    """
    try:
        user_message = message.message.strip()
        
        if not user_message:
            raise HTTPException(status_code=400, detail="Mesaj boş olamaz")
        
        logger.info(f"User {current_user['username']} message: {user_message}")
        
        # Get or create user session
        session_id = get_user_session(current_user["user_id"])
        
        # Generate embedding for search
        try:
            user_embedding = generate_embedding(user_message)
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            response_text = "🤖 Sistem geçici olarak kullanılamıyor. Lütfen daha sonra tekrar deneyin."
            source = "error"
            add_message_to_session(session_id, user_message, response_text, source, user_id=current_user["user_id"])
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
        add_message_to_session(session_id, user_message, response_text, source, user_id=current_user["user_id"])
        
        return ChatResponse(response=response_text, source=source)
        
    except Exception as e:
        logger.error(f"Authenticated chat endpoint error: {e}")
        response_text = "🤖 Bir hata oluştu. Lütfen tekrar deneyin."
        source = "error"
        
        # Try to save to session even on error
        try:
            session_id = get_user_session(current_user["user_id"])
            add_message_to_session(session_id, user_message, response_text, source, user_id=current_user["user_id"])
        except:
            pass
            
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
