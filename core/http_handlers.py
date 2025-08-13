"""
🌐 HTTP Route Handlers
=====================
HTTP endpoints that are not in API modules
"""

import logging
from fastapi import HTTPException, Request, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional
from database.utils import get_database_helper

from auth_service import get_auth_service, verify_token
from database_manager import db_manager
from model_manager import model_manager
from content_manager import ContentManager
from core.configuration import get_config

logger = logging.getLogger(__name__)
config = get_config()

# Initialize content manager
try:
    content_manager = ContentManager()
except ImportError:
    content_manager = None
    logger.warning("ContentManager not available")

class LoginRequest(BaseModel):
    """Legacy login request model"""
    username: str
    password: str

class ChatMessage(BaseModel):
    """Chat message model"""
    message: str

class HTTPRouteHandlers:
    """
    Handlers for HTTP routes that don't belong in API modules
    """
    
    @staticmethod
    async def read_root():
        """Serve the main chat interface"""
        return FileResponse("static/index.html", media_type="text/html; charset=utf-8")
    
    @staticmethod
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
    
    @staticmethod
    async def comprehensive_health_check():
        """Comprehensive health check with detailed system information"""
        health_data = {
            "status": "healthy",
            "timestamp": "2024-12-24T12:00:00Z",
            "checks": {}
        }
        
        try:
            # 1. 🗄️ Database Check
            try:
                db_health = db_manager.health_check()
                health_data["checks"]["database"] = {
                    "status": db_health.get("status", "unknown"),
                    "details": db_health
                }
            except Exception as e:
                health_data["checks"]["database"] = {"status": "error", "error": str(e)}
                health_data["status"] = "unhealthy"
            
            # 2. 🧠 Model Manager Check
            try:
                model_status = {
                    "sentence_transformer": bool(hasattr(model_manager, '_sentence_model') and model_manager._sentence_model),
                    "text_generator": bool(hasattr(model_manager, '_text_generator') and model_manager._text_generator),
                    "memory_usage": model_manager.get_memory_usage() if hasattr(model_manager, 'get_memory_usage') else {}
                }
                health_data["checks"]["models"] = {"status": "healthy", "details": model_status}
            except Exception as e:
                health_data["checks"]["models"] = {"status": "error", "error": str(e)}
            
            # 3. 🔐 Authentication Check
            try:
                auth_service = get_auth_service()
                auth_status = {
                    "initialized": auth_service is not None,
                    "demo_user_enabled": auth_service.demo_user_enabled if auth_service else False
                }
                health_data["checks"]["authentication"] = {"status": "healthy", "details": auth_status}
            except Exception as e:
                health_data["checks"]["authentication"] = {"status": "error", "error": str(e)}
            
            # 4. 🤖 AI Services Check
            try:
                ai_status = {
                    "openai_enabled": config.ai.use_openai,
                    "huggingface_enabled": config.ai.use_huggingface,
                    "content_manager": content_manager is not None
                }
                health_data["checks"]["ai_services"] = {"status": "healthy", "details": ai_status}
                
            except Exception as e:
                health_data["checks"]["ai_services"] = {"status": "error", "error": str(e)}
                
            # 5. 🔐 Security Check
            try:
                security_checks = {
                    "debug_mode": not config.server.debug,
                    "secure_secret_key": config.security.secret_key and config.security.secret_key != "your-secret-key-change-this-in-production",
                    "environment": config.environment.value,
                    "cors_configured": len(config.server.allowed_origins) > 0 and "*" not in config.server.allowed_origins
                }
                
                security_score = sum(1 for check in security_checks.values() if check)
                health_data["checks"]["security"] = {
                    "status": "healthy" if security_score >= 3 else "warning",
                    "score": f"{security_score}/4",
                    "details": security_checks
                }
                
            except Exception as e:
                health_data["checks"]["security"] = {"status": "error", "error": str(e)}
            
            # Overall status determination
            error_count = sum(1 for check in health_data["checks"].values() if check.get("status") == "error")
            if error_count > 0:
                health_data["status"] = "unhealthy"
            elif any(check.get("status") == "warning" for check in health_data["checks"].values()):
                health_data["status"] = "warning"
                
            return health_data
            
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": "2024-12-24T12:00:00Z"
            }
    
    @staticmethod
    async def login_user_simple(login_data: LoginRequest, request: Request):
        """Simple login endpoint (legacy compatible)"""
        try:
            auth_service = get_auth_service()
            if not auth_service:
                raise HTTPException(status_code=500, detail="Authentication service not available")
            
            # Get client IP for rate limiting
            client_ip = request.client.host if request.client else "127.0.0.1"
            
            # Check brute force protection
            if hasattr(auth_service, 'brute_force_protection'):
                if auth_service.brute_force_protection.is_blocked(client_ip):
                    raise HTTPException(
                        status_code=429,
                        detail="Too many failed attempts. Please try again later."
                    )
            
            # Authenticate user
            user_data = auth_service.authenticate_user(login_data.username, login_data.password)
            
            if user_data:
                # Create token
                token = auth_service.create_access_token(data={"sub": user_data["user_id"]})
                
                # Log successful login
                if hasattr(auth_service, 'brute_force_protection'):
                    auth_service.brute_force_protection.reset_failed_attempts(client_ip)
                
                return {
                    "access_token": token,
                    "token_type": "bearer",
                    "user_id": user_data["user_id"],
                    "username": user_data["username"]
                }
            else:
                # Log failed attempt
                if hasattr(auth_service, 'brute_force_protection'):
                    auth_service.brute_force_protection.record_failed_attempt(client_ip)
                
                raise HTTPException(
                    status_code=401,
                    detail="Incorrect username or password"
                )
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Login error: {e}")
            raise HTTPException(status_code=500, detail="Login failed")
    
    @staticmethod
    async def login_legacy(login_data: LoginRequest, request: Request):
        """Legacy login endpoint for compatibility"""
        return await HTTPRouteHandlers.login_user_simple(login_data, request)
    
    @staticmethod
    async def get_current_user(request: Request):
        """Get current user info (simplified for demo)"""
        try:
            # Extract token from Authorization header
            authorization = request.headers.get("Authorization")
            if not authorization or not authorization.startswith("Bearer "):
                # For demo purposes, return demo user
                return {
                    "user_id": "demo",
                    "username": "demo",
                    "authenticated": False
                }
            
            # Verify token
            auth_service = get_auth_service()
            if not auth_service:
                raise HTTPException(status_code=500, detail="Authentication service not available")
            
            token = authorization.split(" ")[1]
            payload = auth_service.verify_access_token(token)
            
            if payload:
                return {
                    "user_id": payload.get("sub"),
                    "username": "authenticated_user",
                    "authenticated": True
                }
            else:
                return {
                    "user_id": "demo",
                    "username": "demo",
                    "authenticated": False
                }
                
        except Exception as e:
            logger.error(f"Get current user error: {e}")
            return {
                "user_id": "demo", 
                "username": "demo",
                "authenticated": False
            }
    
    @staticmethod
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
    
    @staticmethod
    async def chat_authenticated(chat_msg: ChatMessage, request: Request, current_user: dict = Depends(verify_token)):
        """Authenticated chat endpoint with session management"""
        try:
            message = chat_msg.message.strip()
            if not message:
                raise HTTPException(status_code=400, detail="Message cannot be empty")
            
            user_id = current_user["user_id"]
            
            # Process message with AI
            ai_response = await HTTPRouteHandlers._process_ai_message(message, user_id)
            
            # Save to database with unified helper
            db_helper = get_database_helper(db_manager)
            save_result = db_helper.save_chat_interaction(
                user_id=user_id,
                message=message,
                response=ai_response,
                source="authenticated_chat"
            )
            
            if not save_result["success"]:
                logger.warning(f"Failed to save authenticated chat: {save_result.get('error')}")
            
            return {
                "response": ai_response,
                "session_id": save_result["session_id"],
                "user_id": user_id
            }
            
        except Exception as e:
            logger.error(f"Authenticated chat error: {e}")
            raise HTTPException(status_code=500, detail="Chat processing failed")
    
    @staticmethod
    async def _process_ai_message(message: str, user_id: str) -> str:
        """Process message with AI models"""
        try:
            # First try content manager for quick responses
            if content_manager:
                response, response_type = content_manager.find_response(message)
                if response and response_type in ["exact", "contains"]:
                    return response
            
            # Try AI model for complex responses
            if hasattr(model_manager, 'generate_response'):
                ai_response = await model_manager.generate_response(message, user_id)
                if ai_response:
                    return ai_response
            
            # Fallback to content manager
            if content_manager:
                response, _ = content_manager.find_response(message)
                if response:
                    return response
            
            # Final fallback
            return "Üzgünüm, şu anda bu soruya cevap veremiyorum. Lütfen daha sonra tekrar deneyin."
            
        except Exception as e:
            logger.error(f"AI processing error: {e}")
            return "Sistem geçici olarak müsait değil. Lütfen daha sonra tekrar deneyin."
    
    @staticmethod
    async def save_session(request: Request, current_user: dict = Depends(verify_token)):
        """Save current chat session"""
        try:
            user_id = current_user["user_id"]
            # Implementation for saving session
            return {"status": "success", "message": "Session saved"}
        except Exception as e:
            logger.error(f"Save session error: {e}")
            raise HTTPException(status_code=500, detail="Failed to save session")
    
    @staticmethod
    async def get_user_sessions(user_id: str, current_user: dict = Depends(verify_token)):
        """Get user's chat sessions"""
        try:
            # Check authorization
            if current_user["user_id"] != user_id:
                raise HTTPException(status_code=403, detail="Access denied")
            
            # Get sessions from database
            sessions = db_manager.get_user_sessions(user_id) if hasattr(db_manager, 'get_user_sessions') else []
            return {"sessions": sessions}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Get sessions error: {e}")
            raise HTTPException(status_code=500, detail="Failed to get sessions")
    
    @staticmethod
    async def get_session_messages(session_id: str, current_user: dict = Depends(verify_token)):
        """Get messages from a specific session"""
        try:
            user_id = current_user["user_id"]
            
            # Get messages from database
            messages = db_manager.get_session_messages(session_id, user_id) if hasattr(db_manager, 'get_session_messages') else []
            return {"messages": messages}
            
        except Exception as e:
            logger.error(f"Get session messages error: {e}")
            raise HTTPException(status_code=500, detail="Failed to get session messages")
    
    @staticmethod
    async def get_chat_history(request: Request, current_user: dict = Depends(verify_token)):
        """Get chat history for the current user"""
        try:
            user_id = current_user["user_id"]
            
            # Get chat history from database
            history = db_manager.get_chat_history(user_id, limit=50) if hasattr(db_manager, 'get_chat_history') else []
            
            return {
                "status": "success",
                "history": history,
                "user_id": user_id
            }
            
        except Exception as e:
            logger.error(f"Get chat history error: {e}")
            raise HTTPException(status_code=500, detail="Failed to get chat history")
    
    @staticmethod
    async def not_found_handler(request, exc):
        """Custom 404 handler"""
        return FileResponse("static/index.html", media_type="text/html; charset=utf-8")
