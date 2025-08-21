"""
Middleware for distributed WebSocket session management
Handles session validation, cleanup, and health monitoring
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

class DistributedWebSocketMiddleware(BaseHTTPMiddleware):
    """Middleware for distributed WebSocket session management"""
    
    def __init__(self, app: FastAPI, websocket_manager, cleanup_interval: int = 300):
        super().__init__(app)
        self.websocket_manager = websocket_manager
        self.cleanup_interval = cleanup_interval  # 5 minutes default
        self.cleanup_task: Optional[asyncio.Task] = None
        self.health_check_task: Optional[asyncio.Task] = None
        
        # Start background tasks
        self._start_background_tasks()
    
    def _start_background_tasks(self):
        """Start background tasks for cleanup and health monitoring"""
        try:
            # Session cleanup task
            self.cleanup_task = asyncio.create_task(self._periodic_cleanup())
            
            # Health check task (if distributed manager supports it)
            if hasattr(self.websocket_manager, 'health_check'):
                self.health_check_task = asyncio.create_task(self._periodic_health_check())
                
            logger.info("🔧 Distributed WebSocket middleware background tasks started")
            
        except Exception as e:
            logger.error(f"Error starting background tasks: {e}")
    
    async def dispatch(self, request: Request, call_next):
        """Middleware dispatch method"""
        # Add WebSocket manager to request state for easy access
        request.state.websocket_manager = self.websocket_manager
        
        # Add session statistics to response headers for monitoring
        response = await call_next(request)
        
        # Add WebSocket stats headers for monitoring
        if hasattr(self.websocket_manager, 'get_connection_stats'):
            try:
                stats = await self.websocket_manager.get_connection_stats()
                if 'local_stats' in stats:
                    response.headers["X-WebSocket-Local-Connections"] = str(stats['local_stats'].get('local_connections', 0))
                    response.headers["X-WebSocket-Worker-ID"] = str(stats['local_stats'].get('worker_id', 'unknown'))
                
                if 'distributed_stats' in stats:
                    response.headers["X-WebSocket-Total-Sessions"] = str(stats['distributed_stats'].get('total_sessions', 0))
                    response.headers["X-WebSocket-Total-Workers"] = str(stats['distributed_stats'].get('total_workers', 0))
                    
            except Exception as e:
                logger.debug(f"Error adding WebSocket stats headers: {e}")
        
        return response
    
    async def _periodic_cleanup(self):
        """Periodic cleanup of expired sessions"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                
                if hasattr(self.websocket_manager, 'cleanup_expired_sessions'):
                    expired_count = await self.websocket_manager.cleanup_expired_sessions()
                    if expired_count > 0:
                        logger.info(f"🧹 Cleaned up {expired_count} expired WebSocket sessions")
                
            except asyncio.CancelledError:
                logger.info("WebSocket cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in WebSocket cleanup task: {e}")
                # Continue running even if cleanup fails
    
    async def _periodic_health_check(self):
        """Periodic health check of distributed WebSocket system"""
        health_check_interval = 60  # 1 minute
        
        while True:
            try:
                await asyncio.sleep(health_check_interval)
                
                health_status = await self.websocket_manager.health_check()
                
                # Log health status
                if health_status.get('session_store_healthy') and health_status.get('message_broker_healthy'):
                    logger.debug(f"💚 WebSocket system healthy - Worker: {health_status.get('worker_id')}")
                else:
                    logger.warning(f"⚠️ WebSocket system health issues: {health_status}")
                
            except asyncio.CancelledError:
                logger.info("WebSocket health check task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in WebSocket health check: {e}")
    
    async def shutdown(self):
        """Clean shutdown of middleware tasks"""
        logger.info("🔌 Shutting down WebSocket middleware")
        
        # Cancel background tasks
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass
        
        # Shutdown WebSocket manager
        if hasattr(self.websocket_manager, 'close'):
            await self.websocket_manager.close()

class WebSocketSessionValidator:
    """Validator for WebSocket session data"""
    
    @staticmethod
    def validate_connection_params(user_id: str, username: str, metadata: Optional[dict] = None) -> tuple[bool, str]:
        """Validate WebSocket connection parameters"""
        if not user_id or not isinstance(user_id, str):
            return False, "Invalid user_id"
        
        if not username or not isinstance(username, str):
            return False, "Invalid username"
        
        if len(user_id) > 255:
            return False, "user_id too long"
        
        if len(username) > 255:
            return False, "username too long"
        
        if metadata and not isinstance(metadata, dict):
            return False, "Invalid metadata format"
        
        return True, "Valid"
    
    @staticmethod
    def sanitize_message(message: dict) -> dict:
        """Sanitize message data for broadcasting"""
        # Remove sensitive fields
        sensitive_fields = ['password', 'token', 'secret', 'key', 'auth']
        
        def clean_dict(d):
            if isinstance(d, dict):
                return {k: clean_dict(v) for k, v in d.items() 
                       if not any(field in k.lower() for field in sensitive_fields)}
            elif isinstance(d, list):
                return [clean_dict(item) for item in d]
            else:
                return d
        
        return clean_dict(message)

def setup_websocket_middleware(app: FastAPI, websocket_manager, cleanup_interval: int = 300):
    """Setup distributed WebSocket middleware for FastAPI app"""
    middleware = DistributedWebSocketMiddleware(app, websocket_manager, cleanup_interval)
    app.add_middleware(DistributedWebSocketMiddleware, websocket_manager=websocket_manager, cleanup_interval=cleanup_interval)
    
    # Add shutdown handler
    @app.on_event("shutdown")
    async def shutdown_websocket_middleware():
        await middleware.shutdown()
    
    return middleware
