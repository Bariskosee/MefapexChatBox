"""
🔗 MEFAPEX Middleware Integration System
=======================================
Centralized middleware registration and configuration
"""

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import logging
from typing import Dict, Any, List

from core.request_tracking import RequestTrackingMiddleware
from core.error_handlers import (
    GlobalExceptionHandler,
    register_exception_handlers
)
from core.monitoring import get_metrics_collector
from core.logging_config import get_structured_logger
from core.configuration import get_config

logger = get_structured_logger(__name__)

class MiddlewareManager:
    """Manages all middleware registration and configuration"""
    
    def __init__(self, app: FastAPI):
        self.app = app
        self.config = get_config()
        self.metrics_collector = get_metrics_collector()
        
    def register_all_middleware(self):
        """Register all middleware in the correct order"""
        logger.info("Registering middleware stack")
        
        # 1. Security middleware (outermost layer)
        self._register_security_middleware()
        
        # 2. Request tracking (for correlation IDs)
        self._register_request_tracking()
        
        # 3. Error handling (catch all errors)
        self._register_error_handling()
        
        # 4. Performance middleware
        self._register_performance_middleware()
        
        # 5. Compression (innermost layer before app)
        self._register_compression_middleware()
        
        logger.info("Middleware stack registration completed")
    
    def _register_security_middleware(self):
        """Register security-related middleware"""
        # CORS configuration - check if CORS is available in config
        cors_enabled = getattr(self.config.server, 'cors_enabled', True)
        cors_origins = getattr(self.config.server, 'cors_origins', ["*"])
        
        if cors_enabled:
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=cors_origins,
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
            logger.info("CORS middleware registered", origins=cors_origins)
        
        # Trusted hosts - check if available
        trusted_hosts = getattr(self.config.server, 'trusted_hosts', None)
        if trusted_hosts:
            self.app.add_middleware(
                TrustedHostMiddleware,
                allowed_hosts=trusted_hosts
            )
            logger.info("TrustedHost middleware registered", hosts=trusted_hosts)
    
    def _register_request_tracking(self):
        """Register request tracking middleware"""
        self.app.add_middleware(RequestTrackingMiddleware)
        logger.info("Request tracking middleware registered")
    
    def _register_error_handling(self):
        """Register error handling middleware"""
        # Global exception middleware
        self.app.add_middleware(GlobalExceptionHandler)
        
        # Register exception handlers
        register_exception_handlers(self.app)
        
        logger.info("Error handling middleware registered")
    
    def _register_performance_middleware(self):
        """Register performance monitoring middleware"""
        @self.app.middleware("http")
        async def performance_monitoring(request: Request, call_next):
            """Monitor request performance and collect metrics"""
            import time
            from core.request_tracking import get_correlation_id
            
            start_time = time.time()
            correlation_id = get_correlation_id()
            
            # Log request start
            logger.info(
                "Request started",
                method=request.method,
                url=str(request.url),
                user_agent=request.headers.get("user-agent"),
                correlation_id=correlation_id
            )
            
            try:
                response = await call_next(request)
                
                # Calculate metrics
                duration = time.time() - start_time
                
                # Collect metrics
                self.metrics_collector.track_request(
                    method=request.method,
                    endpoint=str(request.url.path),
                    status_code=response.status_code,
                    duration_ms=duration * 1000
                )
                
                # Log successful response
                logger.info(
                    "Request completed",
                    method=request.method,
                    url=str(request.url),
                    status_code=response.status_code,
                    duration_ms=round(duration * 1000, 2),
                    correlation_id=correlation_id
                )
                
                # Add performance headers
                response.headers["X-Response-Time"] = f"{duration:.3f}s"
                response.headers["X-Correlation-ID"] = correlation_id
                
                return response
                
            except Exception as e:
                duration = time.time() - start_time
                
                # Log error
                logger.error(
                    "Request failed",
                    method=request.method,
                    url=str(request.url),
                    duration_ms=round(duration * 1000, 2),
                    error=str(e),
                    correlation_id=correlation_id
                )
                
                # Still collect metrics for failed requests
                self.metrics_collector.track_request(
                    method=request.method,
                    endpoint=str(request.url.path),
                    status_code=500,
                    duration_ms=duration * 1000
                )
                
                raise
        
        logger.info("Performance monitoring middleware registered")
    
    def _register_compression_middleware(self):
        """Register compression middleware"""
        enable_gzip = getattr(self.config.server, 'enable_gzip', True)
        if enable_gzip:
            self.app.add_middleware(GZipMiddleware, minimum_size=1000)
            logger.info("GZip compression middleware registered")

class RateLimitingMiddleware:
    """Rate limiting middleware (optional enhancement)"""
    
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.request_counts: Dict[str, List[float]] = {}
    
    async def __call__(self, request: Request, call_next):
        import time
        
        # Get client IP
        from core.utils import get_client_ip
        client_ip = get_client_ip(request)
        current_time = time.time()
        
        # Clean old requests
        if client_ip in self.request_counts:
            self.request_counts[client_ip] = [
                req_time for req_time in self.request_counts[client_ip]
                if current_time - req_time < 60  # Last minute
            ]
        else:
            self.request_counts[client_ip] = []
        
        # Check rate limit
        if len(self.request_counts[client_ip]) >= self.requests_per_minute:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded"
            )
        
        # Record this request
        self.request_counts[client_ip].append(current_time)
        
        return await call_next(request)

def setup_middleware(app: FastAPI) -> None:
    """Setup all middleware for the FastAPI application"""
    manager = MiddlewareManager(app)
    manager.register_all_middleware()
    
    # Optional: Add rate limiting
    config = get_config()
    enable_rate_limiting = getattr(config.server, 'enable_rate_limiting', False)
    if enable_rate_limiting:
        rate_limit = getattr(config.server, 'rate_limit_per_minute', 60)
        app.add_middleware(
            RateLimitingMiddleware,
            requests_per_minute=rate_limit
        )
        logger.info("Rate limiting middleware registered", limit=rate_limit)

# Middleware order (from outermost to innermost):
# 1. TrustedHostMiddleware (Security)
# 2. CORSMiddleware (Security)
# 3. RateLimitingMiddleware (Optional)
# 4. RequestTrackingMiddleware (Correlation)
# 5. GlobalExceptionHandler (Error handling)
# 6. Performance monitoring (Metrics)
# 7. GZipMiddleware (Compression)
# 8. Application routes
