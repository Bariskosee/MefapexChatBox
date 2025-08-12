"""
🛡️ Security and Rate Limiting Middleware
Centralized middleware for security headers and rate limiting
"""
import time
import logging
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

class RateLimiter:
    """Rate limiting with IP-based tracking"""
    
    def __init__(self, max_requests_per_minute: int = 200, max_chat_requests_per_minute: int = 100):
        self.requests = defaultdict(list)
        self.chat_requests = defaultdict(list)
        self.max_requests_per_minute = max_requests_per_minute
        self.max_chat_requests_per_minute = max_chat_requests_per_minute
        
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

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    async def dispatch(self, request, call_next):
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
        
        # HSTS for HTTPS
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware"""
    
    def __init__(self, app, rate_limiter: RateLimiter):
        super().__init__(app)
        self.rate_limiter = rate_limiter
    
    async def dispatch(self, request, call_next):
        # Get client IP safely with proper fallback
        client_ip = "unknown"
        
        try:
            if request.client and hasattr(request.client, 'host') and request.client.host:
                client_ip = request.client.host
            else:
                # Fallback to headers for proxy situations
                forwarded_for = request.headers.get("X-Forwarded-For")
                if forwarded_for:
                    client_ip = forwarded_for.split(",")[0].strip()
                else:
                    # Additional fallbacks
                    client_ip = (
                        request.headers.get("X-Real-IP") or
                        request.headers.get("X-Forwarded-Host") or
                        "127.0.0.1"
                    )
        except Exception as e:
            logger.warning(f"Failed to get client IP: {e}")
            client_ip = "127.0.0.1"
        
        path = request.url.path
        
        # Determine endpoint type
        endpoint_type = "general"
        if "/api/chat/" in path:
            endpoint_type = "chat"
        
        # Check rate limit
        if not self.rate_limiter.is_allowed(client_ip, endpoint_type):
            logger.warning(f"Rate limit exceeded for {client_ip} on {path}")
            return Response(
                content='{"detail":"Rate limit exceeded"}',
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={"Content-Type": "application/json"}
            )
        
        return await call_next(request)

class LoggingMiddleware(BaseHTTPMiddleware):
    """Request/Response logging middleware"""
    
    async def dispatch(self, request, call_next):
        start_time = time.time()
        
        # Get client IP safely with proper fallback
        client_ip = "unknown"
        
        try:
            if request.client and hasattr(request.client, 'host') and request.client.host:
                client_ip = request.client.host
            else:
                # Fallback to headers for proxy situations
                forwarded_for = request.headers.get("X-Forwarded-For")
                if forwarded_for:
                    client_ip = forwarded_for.split(",")[0].strip()
                else:
                    # Additional fallbacks
                    client_ip = (
                        request.headers.get("X-Real-IP") or
                        request.headers.get("X-Forwarded-Host") or
                        "127.0.0.1"
                    )
        except Exception as e:
            logger.warning(f"Failed to get client IP: {e}")
            client_ip = "127.0.0.1"
        
        # Log request
        logger.info(f"🌐 {request.method} {request.url.path} - Client: {client_ip}")
        
        # Process request
        response = await call_next(request)
        
        # Calculate response time
        process_time = time.time() - start_time
        
        # Log response
        logger.info(
            f"📤 {request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Time: {process_time:.3f}s"
        )
        
        # Add response time header
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
