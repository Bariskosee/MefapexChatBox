"""
💬 Chat API Routes
Main chat functionality and session management
"""
from fastapi import APIRouter, HTTPException, Depends, status, Request
from pydantic import BaseModel
from typing import List, Dict, Optional
import logging
import asyncio
import time
from database.utils import get_database_helper

from auth_service import verify_token
# Use new database manager
from database.manager import DatabaseManager
from model_manager import model_manager
from security_config import input_validator
from content_manager import ContentManager
from qdrant_client import QdrantClient

logger = logging.getLogger(__name__)

# Import centralized cache manager
try:
    from cache_manager import get_response_cache, get_distributed_cache
    logger.info("✅ Cache manager available")
except ImportError:
    logger.warning("⚠️ Cache manager not available")
    get_response_cache = None
    get_distributed_cache = None

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Rate limiter placeholder (will be set by main.py)
rate_limiter = None

def set_rate_limiter(limiter):
    """Set rate limiter from main app"""
    global rate_limiter
    rate_limiter = limiter

# Initialize database manager
db_manager = DatabaseManager()

# Initialize Qdrant client
try:
    from core.config_utils import get_qdrant_config
    qdrant_config = get_qdrant_config()
    
    qdrant_client = QdrantClient(
        host=qdrant_config['host'],
        port=qdrant_config['port']
    )
except Exception as e:
    logger.warning(f"Failed to initialize Qdrant client: {e}")
    qdrant_client = None

# Initialize ContentManager
try:
    content_manager = ContentManager()
except Exception as e:
    logger.warning(f"Failed to initialize ContentManager: {e}")
    content_manager = None

# Pydantic models
class ChatMessage(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    source: str
    session_id: str
    response_time_ms: Optional[int] = None

@router.post("/message", response_model=ChatResponse)
async def chat_message(
    chat_msg: ChatMessage,
    request: Request,
    current_user: dict = Depends(verify_token)
):
    """Process chat message with AI response"""
    start_time = time.time()
    
    try:
        from core.utils import get_client_ip
        client_ip = get_client_ip(request)
        user_id = current_user["user_id"]
        
        # Rate limiting for chat
        if rate_limiter and not rate_limiter.is_allowed(client_ip, "chat"):
            logger.warning(f"Chat rate limit exceeded for user {user_id}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many chat requests. Please slow down."
            )
        
        # Input validation
        message = chat_msg.message.strip()
        if not message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message cannot be empty"
            )
        
        if len(message) > 1000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message too long (max 1000 characters)"
            )
        
        # Security validation
        is_xss, xss_pattern = input_validator.detect_xss_attempt(message)
        if is_xss:
            logger.warning(f"XSS attempt blocked: {xss_pattern}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid content detected"
            )
        
        is_sql_injection, sql_pattern = input_validator.detect_sql_injection(message)
        if is_sql_injection:
            logger.warning(f"SQL injection attempt blocked: {sql_pattern}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid content detected"
            )
        
        # Sanitize input
        sanitized_message = input_validator.sanitize_input(message)
        
        # Get or create session
        session_id = db_manager.get_or_create_session(user_id)
        
        # Get appropriate cache instance (distributed cache preferred, fallback to response cache)
        cache_instance = None
        if get_distributed_cache:
            cache_instance = get_distributed_cache()
        
        # Fallback to response cache if distributed cache not available
        if not cache_instance and get_response_cache:
            cache_instance = get_response_cache()
        
        # Try to get cached response
        cached = None
        if cache_instance:
            try:
                if hasattr(cache_instance, 'get') and asyncio.iscoroutinefunction(cache_instance.get):
                    # Async cache (distributed)
                    cached = await cache_instance.get(sanitized_message)
                else:
                    # Sync cache (local)
                    cached = cache_instance.get(sanitized_message)
            except Exception as e:
                logger.warning(f"Cache get error: {e}")
        
        if cached:
            ai_response, response_source = cached
            logger.info(f"Returning cached response from {response_source}")
            response_source = f"cache_{response_source}"
        else:
            # Generate AI response
            ai_response, response_source = await generate_ai_response(sanitized_message)
            
            # Cache the response
            if cache_instance:
                try:
                    if hasattr(cache_instance, 'set') and asyncio.iscoroutinefunction(cache_instance.set):
                        # Async cache (distributed)
                        await cache_instance.set(sanitized_message, ai_response, source=response_source)
                    else:
                        # Sync cache (local)
                        cache_instance.set(sanitized_message, ai_response, source=response_source)
                except Exception as e:
                    logger.warning(f"Cache set error: {e}")
        
        # Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Save to database with unified helper
        db_helper = get_database_helper(db_manager)
        save_result = db_helper.save_chat_interaction(
            user_id=user_id,
            message=sanitized_message,
            response=ai_response,
            source=response_source,
            session_id=session_id
        )
        
        if not save_result["success"]:
            logger.warning(f"Failed to save message: {save_result.get('error')}")
        
        logger.info(f"Chat response generated for user {user_id}: {response_time_ms}ms")
        
        return ChatResponse(
            response=ai_response,
            source=response_source,
            session_id=session_id,
            response_time_ms=response_time_ms
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process chat message"
        )

async def generate_ai_response(message: str) -> tuple[str, str]:
    """Generate AI response from various sources"""
    
    # Try knowledge base first
    try:
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        
        # Search in knowledge base
        search_results = qdrant_client.search(
            collection_name="mefapex_faq",
            query_text=message,
            limit=3
        )
        
        if search_results and search_results[0].score > 0.8:
            return search_results[0].payload.get("answer", ""), "knowledge_base"
            
    except Exception as e:
        logger.warning(f"Knowledge base search failed: {e}")
    
    # Try static content
    static_response, response_type = content_manager.find_response(message)
    if static_response:
        return static_response, "static_content"
    
    # Try OpenAI if available
    try:
        from core.config_utils import get_ai_config
        ai_config = get_ai_config()
        use_openai = ai_config['use_openai']
            
        if use_openai:
            try:
                openai_response = await model_manager.generate_openai_response(
                    context="You are MEFAPEX AI Assistant, a helpful and knowledgeable assistant.",
                    query=message
                )
                if openai_response:
                    return openai_response, "openai"
            except Exception as e:
                logger.warning(f"OpenAI generation failed: {e}")
    except Exception as e:
        logger.warning(f"OpenAI config check failed: {e}")
    
    # Try HuggingFace as fallback
    try:
        from core.config_utils import get_ai_config
        ai_config = get_ai_config()
        use_huggingface = ai_config['use_huggingface']
            
        if use_huggingface:
            try:
                hf_response = await model_manager.generate_huggingface_response(
                    context="You are MEFAPEX AI Assistant.",
                    query=message
                )
                if hf_response:
                    return hf_response, "huggingface"
            except Exception as e:
                logger.warning(f"HuggingFace generation failed: {e}")
    except Exception as e:
        logger.warning(f"HuggingFace config check failed: {e}")
    
    # Final fallback
    return "Üzgünüm, şu anda sorunuza uygun bir yanıt üretemiyorum. Lütfen daha sonra tekrar deneyin.", "fallback"

@router.get("/history")
async def get_chat_history(current_user: dict = Depends(verify_token)):
    """Get user's chat history"""
    try:
        user_id = current_user["user_id"]
        messages = db_manager.get_chat_history(user_id, limit=20)
        
        return {
            "session_id": db_manager.get_or_create_session(user_id),
            "messages": messages,
            "total_count": len(messages)
        }
        
    except Exception as e:
        logger.error(f"Error fetching chat history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch chat history"
        )

@router.delete("/history")
async def clear_chat_history(current_user: dict = Depends(verify_token)):
    """Clear user's chat history"""
    try:
        user_id = current_user["user_id"]
        db_manager.clear_chat_history(user_id)
        
        logger.info(f"Chat history cleared for user {user_id}")
        return {"message": "Chat history cleared successfully"}
        
    except Exception as e:
        logger.error(f"Error clearing chat history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear chat history"
        )
