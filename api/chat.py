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

from auth_service import verify_token
from database_manager import db_manager
from model_manager import model_manager
from response_cache import response_cache
from security_config import input_validator
from content_manager import ContentManager
from qdrant_client import QdrantClient
from config import config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])

# Initialize Qdrant client
qdrant_client = QdrantClient(
    host=config.QDRANT_HOST,
    port=config.QDRANT_PORT
)

# Initialize ContentManager
content_manager = ContentManager()

# Rate limiter will be imported from main
rate_limiter = None

# Pydantic models
class ChatMessage(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    source: str
    session_id: str
    response_time_ms: Optional[int] = None

def set_rate_limiter(limiter):
    """Set rate limiter from main app"""
    global rate_limiter
    rate_limiter = limiter

@router.post("/message", response_model=ChatResponse)
async def chat_message(
    chat_msg: ChatMessage,
    request: Request,
    current_user: dict = Depends(verify_token)
):
    """Process chat message with AI response"""
    start_time = time.time()
    
    try:
        client_ip = request.client.host
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
        
        # Try to get cached response
        cache_key = f"chat_{hash(sanitized_message)}"
        cached_response = response_cache.get(cache_key)
        
        if cached_response:
            logger.info("Returning cached response")
            response_source = "cache"
            ai_response = cached_response
        else:
            # Generate AI response
            ai_response, response_source = await generate_ai_response(sanitized_message)
            
            # Cache the response
            response_cache.set(cache_key, ai_response, ttl=3600)  # 1 hour
        
        # Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Save to database
        db_manager.add_message(
            session_id=session_id,
            user_id=user_id,
            user_message=sanitized_message,
            bot_response=ai_response,
            source=response_source
        )
        
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
    static_response = content_manager.get_response(message)
    if static_response:
        return static_response, "static_content"
    
    # Try OpenAI if available
    if config.USE_OPENAI:
        try:
            openai_response = await model_manager.generate_openai_response(
                context="You are MEFAPEX AI Assistant, a helpful and knowledgeable assistant.",
                query=message
            )
            if openai_response:
                return openai_response, "openai"
        except Exception as e:
            logger.warning(f"OpenAI generation failed: {e}")
    
    # Try HuggingFace as fallback
    if config.USE_HUGGINGFACE:
        try:
            hf_response = await model_manager.generate_huggingface_response(
                context="You are MEFAPEX AI Assistant.",
                query=message
            )
            if hf_response:
                return hf_response, "huggingface"
        except Exception as e:
            logger.warning(f"HuggingFace generation failed: {e}")
    
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
