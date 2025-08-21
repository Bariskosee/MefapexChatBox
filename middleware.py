"""
🛡️ Security and Rate Limiting Middleware
Centralized middleware for security headers and distributed rate limiting
"""
import time
import logging
import asyncio
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from fastapi import HTTPException, status

from core.rate_limiter import get_rate_limiter, DistributedRateLimiter

logger = logging.getLogger(__name__)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"  # Safari için daha esnek
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "no-referrer-when-downgrade"  # Safari uyumlu
        response.headers["Content-Security-Policy"] = (
            "default-src 'self' data: ws: wss: http: https:; "
            "script-src 'self'; "
            "style-src 'self'; "
            "img-src 'self' data: https: http:; "
            "font-src 'self' data:; "
            "connect-src 'self' ws: wss: http: https:; "
            "object-src 'none'; "
            "base-uri 'self';"
        )
        
        # HSTS for HTTPS
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Distributed rate limiting middleware using Redis backend"""
    
    def __init__(self, app, rate_limiter: DistributedRateLimiter = None):
        super().__init__(app)
        self.rate_limiter = rate_limiter
        self._stats = {
            "total_requests": 0,
            "blocked_requests": 0,
            "redis_errors": 0,
            "fallback_used": 0
        }
    
    async def _ensure_rate_limiter(self):
        """Ensure rate limiter is initialized"""
        if self.rate_limiter is None:
            try:
                self.rate_limiter = await get_rate_limiter()
            except Exception as e:
                logger.error(f"Failed to initialize rate limiter: {e}")
                # Create a disabled rate limiter as fallback
                from core.configuration import RateLimitConfig
                config = RateLimitConfig()
                config.enabled = False
                from core.rate_limiter import DistributedRateLimiter
                self.rate_limiter = DistributedRateLimiter(config)
    
    def _get_client_ip(self, request) -> str:
        """Get client IP safely with proper fallback"""
        try:
            if request.client and hasattr(request.client, 'host') and request.client.host:
                return request.client.host
            else:
                # Fallback to headers for proxy situations
                forwarded_for = request.headers.get("X-Forwarded-For")
                if forwarded_for:
                    return forwarded_for.split(",")[0].strip()
                else:
                    # Additional fallbacks
                    return (
                        request.headers.get("X-Real-IP") or
                        request.headers.get("X-Forwarded-Host") or
                        "127.0.0.1"
                    )
        except Exception as e:
            logger.warning(f"Failed to get client IP: {e}")
            return "127.0.0.1"
    
    async def dispatch(self, request, call_next):
        await self._ensure_rate_limiter()
        
        # If rate limiting is disabled, skip the check
        if not self.rate_limiter.config.enabled:
            return await call_next(request)
        
        self._stats["total_requests"] += 1
        
        client_ip = self._get_client_ip(request)
        path = request.url.path
        
        # Determine endpoint type
        endpoint_type = "general"
        if "/api/chat/" in path:
            endpoint_type = "chat"
        
        # Check rate limit
        try:
            is_allowed = await self.rate_limiter.is_allowed(client_ip, endpoint_type)
            
            if not is_allowed:
                self._stats["blocked_requests"] += 1
                logger.warning(f"Rate limit exceeded for {client_ip} on {path}")
                
                # Get current count for debugging
                current_count = await self.rate_limiter.get_current_count(client_ip, endpoint_type)
                
                return Response(
                    content=f'{{"detail":"Rate limit exceeded","current_requests":{current_count}}}',
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    headers={
                        "Content-Type": "application/json",
                        "X-RateLimit-Limit": str(
                            self.rate_limiter.config.chat_requests_per_minute 
                            if endpoint_type == "chat" 
                            else self.rate_limiter.config.requests_per_minute
                        ),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(time.time()) + self.rate_limiter.config.window_size_seconds),
                        "Retry-After": str(self.rate_limiter.config.window_size_seconds)
                    }
                )
            
            # Add rate limit headers to successful responses
            response = await call_next(request)
            
            # Get current count for headers
            current_count = await self.rate_limiter.get_current_count(client_ip, endpoint_type)
            limit = (
                self.rate_limiter.config.chat_requests_per_minute 
                if endpoint_type == "chat" 
                else self.rate_limiter.config.requests_per_minute
            )
            
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(max(0, limit - current_count))
            response.headers["X-RateLimit-Reset"] = str(int(time.time()) + self.rate_limiter.config.window_size_seconds)
            
            return response
            
        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            self._stats["redis_errors"] += 1
            
            # On error, allow request but log the issue
            # This prevents service disruption when Redis is down
            response = await call_next(request)
            response.headers["X-RateLimit-Error"] = "true"
            return response
    
    async def get_stats(self) -> dict:
        """Get middleware statistics"""
        rate_limiter_stats = await self.rate_limiter.get_stats() if self.rate_limiter else {}
        
        return {
            "middleware_stats": self._stats,
            "rate_limiter_stats": rate_limiter_stats
        }

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
