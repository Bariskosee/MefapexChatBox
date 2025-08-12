"""
🚀 FastAPI Best Practices Implementation
======================================
Modern FastAPI application with proper middleware, error handling, and API structure.
"""

import logging
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Depends, status, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, Field
import time
import uuid

from core.container.dependency_container import DependencyContainer
from core.interfaces.config_interface import IConfigurationService
from core.interfaces.auth_interface import IAuthenticationService
from core.interfaces.database_interface import IDatabaseManager
from services.implementations.sqlalchemy_async_service import (
    UserCreate, UserResponse, SessionResponse, MessageResponse
)

logger = logging.getLogger(__name__)

# ================================
# Response Models
# ================================

class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    timestamp: str
    version: str
    environment: str
    services: Dict[str, str]


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    detail: Optional[str] = None
    timestamp: str
    request_id: Optional[str] = None


class SuccessResponse(BaseModel):
    """Success response model"""
    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: str


class PaginatedResponse(BaseModel):
    """Paginated response model"""
    items: List[Any]
    total: int
    page: int
    size: int
    pages: int


class APIResponse(BaseModel):
    """Generic API response wrapper"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    message: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    request_id: Optional[str] = None


# ================================
# Middleware Components
# ================================

class RequestLoggingMiddleware:
    """Custom request logging middleware"""
    
    def __init__(self, app: FastAPI):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive)
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        # Add request ID to scope
        scope["request_id"] = request_id
        
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                # Add custom headers
                headers = dict(message.get("headers", []))
                headers[b"x-request-id"] = request_id.encode()
                headers[b"x-api-version"] = b"v1"
                message["headers"] = list(headers.items())
            
            await send(message)
        
        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            # Log request
            process_time = time.time() - start_time
            logger.info(
                f"Request completed: {request.method} {request.url.path} "
                f"- {process_time:.3f}s - ID: {request_id}"
            )


class SecurityHeadersMiddleware:
    """Security headers middleware"""
    
    def __init__(self, app: FastAPI):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))
                
                # Security headers
                headers[b"x-content-type-options"] = b"nosniff"
                headers[b"x-frame-options"] = b"DENY"
                headers[b"x-xss-protection"] = b"1; mode=block"
                headers[b"strict-transport-security"] = b"max-age=31536000; includeSubDomains"
                headers[b"referrer-policy"] = b"strict-origin-when-cross-origin"
                headers[b"permissions-policy"] = b"geolocation=(), microphone=(), camera=()"
                
                message["headers"] = list(headers.items())
            
            await send(message)
        
        await self.app(scope, receive, send_wrapper)


# ================================
# Exception Handlers
# ================================

async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler"""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            detail=getattr(exc, "detail", None),
            timestamp=datetime.now(timezone.utc).isoformat(),
            request_id=request_id
        ).dict()
    )


async def general_exception_handler(request: Request, exc: Exception):
    """General exception handler"""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Internal server error",
            detail="An unexpected error occurred",
            timestamp=datetime.now(timezone.utc).isoformat(),
            request_id=request_id
        ).dict()
    )


# ================================
# Dependency Injection
# ================================

def get_config_service() -> IConfigurationService:
    """Get configuration service dependency"""
    container = DependencyContainer.get_instance()
    return container.resolve(IConfigurationService)


def get_auth_service() -> IAuthenticationService:
    """Get authentication service dependency"""
    container = DependencyContainer.get_instance()
    return container.resolve(IAuthenticationService)


def get_database_service() -> IDatabaseManager:
    """Get database service dependency"""
    container = DependencyContainer.get_instance()
    return container.resolve(IDatabaseManager)


# ================================
# Authentication Dependencies
# ================================

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: IAuthenticationService = Depends(get_auth_service)
):
    """Get current authenticated user"""
    try:
        # Validate JWT token
        payload = auth_service.validate_token(credentials.credentials)
        username = payload.get("sub")
        
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Get user from database
        db_service = get_database_service()
        user = db_service.authenticate_user(username)
        
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return user
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_user(
    request: Request,
    auth_service: IAuthenticationService = Depends(get_auth_service)
):
    """Get current user if authenticated, otherwise None"""
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header.split(" ")[1]
        payload = auth_service.validate_token(token)
        username = payload.get("sub")
        
        if username:
            db_service = get_database_service()
            return db_service.authenticate_user(username)
        
        return None
        
    except Exception:
        return None


# ================================
# Application Lifespan Management
# ================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("🚀 Starting MEFAPEX ChatBox application...")
    
    try:
        # Initialize dependency container
        container = DependencyContainer.get_instance()
        
        # Initialize database
        db_service = container.resolve(IDatabaseManager)
        await db_service.initialize()
        
        logger.info("✅ Application startup completed")
        
        yield
        
    finally:
        # Shutdown
        logger.info("🔄 Shutting down application...")
        
        try:
            # Close database connections
            db_service = container.resolve(IDatabaseManager)
            db_service.close()
            
            # Clear container
            container.clear()
            
            logger.info("✅ Application shutdown completed")
            
        except Exception as e:
            logger.error(f"❌ Error during shutdown: {e}")


# ================================
# FastAPI Application Factory
# ================================

def create_fastapi_application() -> FastAPI:
    """Create and configure FastAPI application with best practices"""
    
    # Get configuration
    container = DependencyContainer.get_instance()
    config_service = container.resolve(IConfigurationService)
    app_config = config_service.get_application_config()
    
    # Create FastAPI app
    app = FastAPI(
        title="MEFAPEX ChatBox API",
        description="Modern AI-powered chat application with enterprise features",
        version="2.0.0",
        docs_url="/docs" if app_config.get("debug") else None,
        redoc_url="/redoc" if app_config.get("debug") else None,
        openapi_url="/openapi.json" if app_config.get("debug") else None,
        lifespan=lifespan,
        generate_unique_id_function=lambda route: f"{route.tags[0]}-{route.name}" if route.tags else route.name
    )
    
    # ================================
    # Middleware Configuration
    # ================================
    
    # Security Headers (first)
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Trusted Host
    if not app_config.get("debug"):
        allowed_hosts = app_config.get("allowed_hosts", ["*"])
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_config.get("cors_origins", ["*"]),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["x-request-id", "x-api-version"]
    )
    
    # GZip Compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Request Logging (last)
    app.add_middleware(RequestLoggingMiddleware)
    
    # ================================
    # Exception Handlers
    # ================================
    
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
    
    # ================================
    # API Routes
    # ================================
    
    @app.get("/", response_model=APIResponse, tags=["Root"])
    async def root():
        """Root endpoint"""
        return APIResponse(
            success=True,
            message="MEFAPEX ChatBox API v2.0 - Modern AI Chat Application",
            data={
                "version": "2.0.0",
                "status": "operational",
                "features": [
                    "Modern FastAPI architecture",
                    "Async SQLAlchemy operations",
                    "Pydantic configuration management",
                    "Dependency injection container",
                    "Enterprise security features"
                ]
            }
        )
    
    @app.get("/health", response_model=HealthResponse, tags=["Health"])
    async def health_check(
        db_service: IDatabaseManager = Depends(get_database_service),
        config_service: IConfigurationService = Depends(get_config_service)
    ):
        """Health check endpoint"""
        try:
            # Check database health
            db_health = db_service.health_check()
            
            # Check configuration
            app_config = config_service.get_application_config()
            
            services = {
                "database": db_health.get("status", "unknown"),
                "configuration": "healthy",
                "authentication": "healthy"
            }
            
            return HealthResponse(
                status="healthy" if all(s == "healthy" for s in services.values()) else "degraded",
                timestamp=datetime.now(timezone.utc).isoformat(),
                version="2.0.0",
                environment=app_config.get("environment", "unknown"),
                services=services
            )
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable"
            )
    
    @app.get("/api/v1/users/me", response_model=UserResponse, tags=["Users"])
    async def get_current_user_info(
        current_user: dict = Depends(get_current_user)
    ):
        """Get current user information"""
        return UserResponse(**current_user)
    
    @app.get("/api/v1/sessions", response_model=List[SessionResponse], tags=["Sessions"])
    async def get_user_sessions(
        current_user: dict = Depends(get_current_user),
        db_service: IDatabaseManager = Depends(get_database_service),
        limit: int = 15
    ):
        """Get user's chat sessions"""
        sessions = db_service.get_user_sessions(current_user["user_id"], limit)
        return [SessionResponse(**session) for session in sessions]
    
    @app.get("/api/v1/sessions/{session_id}/messages", response_model=List[MessageResponse], tags=["Messages"])
    async def get_session_messages(
        session_id: str,
        current_user: dict = Depends(get_current_user),
        db_service: IDatabaseManager = Depends(get_database_service)
    ):
        """Get messages for a specific session"""
        # Verify session belongs to user
        session = db_service.get_session_by_id(session_id)
        if not session or session["user_id"] != current_user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        messages = db_service.get_session_messages(session_id)
        return [MessageResponse(**message) for message in messages]
    
    @app.get("/api/v1/stats", response_model=APIResponse, tags=["Statistics"])
    async def get_application_stats(
        current_user: dict = Depends(get_current_user),
        db_service: IDatabaseManager = Depends(get_database_service)
    ):
        """Get application statistics"""
        try:
            stats = db_service.get_stats()
            user_sessions = len(db_service.get_user_sessions(current_user["user_id"]))
            
            return APIResponse(
                success=True,
                message="Application statistics retrieved",
                data={
                    "global_stats": stats,
                    "user_stats": {
                        "session_count": user_sessions,
                        "user_id": current_user["user_id"]
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve statistics"
            )
    
    # ================================
    # Custom OpenAPI
    # ================================
    
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        
        openapi_schema = get_openapi(
            title="MEFAPEX ChatBox API",
            version="2.0.0",
            description="Modern AI-powered chat application with enterprise features",
            routes=app.routes,
        )
        
        # Add security scheme
        openapi_schema["components"]["securitySchemes"] = {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT"
            }
        }
        
        # Add global security
        openapi_schema["security"] = [{"bearerAuth": []}]
        
        app.openapi_schema = openapi_schema
        return app.openapi_schema
    
    app.openapi = custom_openapi
    
    return app


# ================================
# Application Instance
# ================================

# Create the FastAPI application
app = create_fastapi_application()

if __name__ == "__main__":
    import uvicorn
    
    # Get configuration
    container = DependencyContainer.get_instance()
    config_service = container.resolve(IConfigurationService)
    app_config = config_service.get_application_config()
    
    # Run application
    uvicorn.run(
        "fastapi_app:app",
        host=app_config.get("host", "0.0.0.0"),
        port=app_config.get("port", 8000),
        reload=app_config.get("debug", False),
        log_level="info" if not app_config.get("debug") else "debug",
        access_log=True
    )
