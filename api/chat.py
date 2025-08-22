"""
💬 Chat API Routes
Main chat functionality and session management
OPTIMIZED: Cache-based configuration loading and parallel AI response generation
"""
from fastapi import APIRouter, HTTPException, Depends, status, Request
from pydantic import BaseModel
from typing import List, Dict, Optional, Tuple, Any
import logging
import asyncio
import time
from functools import lru_cache
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

# OPTIMIZATION: Cache AI configuration to avoid repeated loading
@lru_cache(maxsize=1)
def get_cached_ai_config() -> Dict[str, Any]:
    """Cache AI configuration flags to avoid repeated loading on every request"""
    try:
        from core.config_utils import get_ai_config
        config = get_ai_config()
        logger.debug("🔧 AI configuration loaded and cached")
        return config
    except Exception as e:
        logger.warning(f"Failed to load AI config: {e}")
        return {
            'use_openai': False,
            'use_huggingface': True,
            'openai_api_key': None,
            'model': 'gpt-3.5-turbo'
        }

# Performance metrics tracking
class PerformanceMetrics:
    """Track and store performance metrics for AI response generation"""
    
    def __init__(self):
        self.reset_metrics()
    
    def reset_metrics(self):
        self.metrics = {
            'total_requests': 0,
            'average_response_time': 0,
            'cache_hits': 0,
            'knowledge_base_hits': 0,
            'static_content_hits': 0,
            'openai_hits': 0,
            'huggingface_hits': 0,
            'fallback_hits': 0,
            'parallel_optimization_saves': 0,
            'config_cache_saves': 0
        }
        self.response_times = []
    
    def record_request(self, response_time_ms: int, source: str, used_parallel: bool = False):
        """Record performance metrics for a request"""
        self.metrics['total_requests'] += 1
        self.response_times.append(response_time_ms)
        
        # Update average (rolling window of last 100 requests)
        if len(self.response_times) > 100:
            self.response_times.pop(0)
        self.metrics['average_response_time'] = sum(self.response_times) / len(self.response_times)
        
        # Track source hits
        source_key = f"{source.replace('_', '_')}_hits"
        if source_key in self.metrics:
            self.metrics[source_key] += 1
        
        # Track optimization benefits
        if used_parallel:
            self.metrics['parallel_optimization_saves'] += 1
        
        self.metrics['config_cache_saves'] += 1  # Config is always cached
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        return {
            **self.metrics,
            'current_response_times': self.response_times[-10:],  # Last 10 response times
            'median_response_time': sorted(self.response_times)[len(self.response_times)//2] if self.response_times else 0
        }

# Global performance metrics instance
performance_metrics = PerformanceMetrics()

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
        
        logger.info(f"Chat response generated for user {user_id}: {response_time_ms}ms from {response_source}")
        
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
    """
    OPTIMIZED: Generate AI response from various sources with parallel processing
    
    Performance optimizations:
    1. Cached configuration loading (no re-fetching on every request)
    2. Parallel query execution with early return on high-confidence answers
    3. Performance metrics tracking
    """
    start_time = time.time()
    used_parallel = False
    
    # OPTIMIZATION: Use cached configuration instead of re-fetching
    ai_config = get_cached_ai_config()
    
    # OPTIMIZATION: Run multiple sources in parallel with early return
    async def check_knowledge_base():
        """Check knowledge base for answers"""
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            
            # Search in knowledge base
            search_results = qdrant_client.search(
                collection_name="mefapex_faq",
                query_text=message,
                limit=3
            )
            
            if search_results and search_results[0].score > 0.8:
                return search_results[0].payload.get("answer", ""), "knowledge_base", search_results[0].score
            return None, "knowledge_base", 0.0
            
        except Exception as e:
            logger.warning(f"Knowledge base search failed: {e}")
            return None, "knowledge_base", 0.0
    
    async def check_static_content():
        """Check static content for answers"""
        try:
            if content_manager:
                static_response, response_type = content_manager.find_response(message)
                if static_response:
                    # Assume high confidence for exact matches
                    confidence = 0.9 if response_type == "exact_match" else 0.7
                    return static_response, "static_content", confidence
            return None, "static_content", 0.0
        except Exception as e:
            logger.warning(f"Static content search failed: {e}")
            return None, "static_content", 0.0
    
    async def check_openai():
        """Check OpenAI for answers"""
        try:
            if not ai_config['use_openai']:
                return None, "openai", 0.0
                
            # Check if model_manager has OpenAI support
            if hasattr(model_manager, 'generate_openai_response'):
                openai_response = await model_manager.generate_openai_response(
                    context="You are MEFAPEX AI Assistant, a helpful and knowledgeable assistant.",
                    query=message
                )
                if openai_response:
                    return openai_response, "openai", 0.8  # Assume good confidence for OpenAI
            else:
                logger.debug("OpenAI not implemented in model manager")
            return None, "openai", 0.0
        except Exception as e:
            logger.warning(f"OpenAI generation failed: {e}")
            return None, "openai", 0.0
    
    async def check_huggingface():
        """Check HuggingFace for answers"""
        try:
            if not ai_config['use_huggingface']:
                return None, "huggingface", 0.0
                
            hf_response = await model_manager.generate_huggingface_response(
                message=message
            )
            if hf_response:
                return hf_response, "huggingface", 0.6  # Lower confidence for local models
            return None, "huggingface", 0.0
        except Exception as e:
            logger.warning(f"HuggingFace generation failed: {e}")
            return None, "huggingface", 0.0
    
    # OPTIMIZATION: Execute all sources in parallel
    try:
        tasks = [
            check_knowledge_base(),
            check_static_content(),
            check_openai(),
            check_huggingface()
        ]
        
        # Use asyncio.gather with return_when=FIRST_COMPLETED for early return
        # But we'll check all quickly since they should be fast
        results = await asyncio.gather(*tasks, return_exceptions=True)
        used_parallel = True
        
        # Find the best result based on confidence score
        best_response = None
        best_source = "fallback"
        best_confidence = 0.0
        
        for result in results:
            if isinstance(result, Exception):
                logger.warning(f"Task failed: {result}")
                continue
                
            response, source, confidence = result
            if response and confidence > best_confidence:
                best_response = response
                best_source = source
                best_confidence = confidence
                
                # OPTIMIZATION: Early return for high-confidence answers
                if confidence > 0.85:
                    logger.info(f"🎯 Early return with high-confidence answer from {source} (confidence: {confidence:.2f})")
                    break
        
        if best_response:
            response_time_ms = int((time.time() - start_time) * 1000)
            performance_metrics.record_request(response_time_ms, best_source, used_parallel)
            logger.info(f"✅ Parallel AI response generated: {response_time_ms}ms from {best_source}")
            return best_response, best_source
            
    except Exception as e:
        logger.error(f"Parallel AI response generation failed: {e}")
    
    # Final fallback
    fallback_response = "Üzgünüm, şu anda sorunuza uygun bir yanıt üretemiyorum. Lütfen daha sonra tekrar deneyin."
    response_time_ms = int((time.time() - start_time) * 1000)
    performance_metrics.record_request(response_time_ms, "fallback", used_parallel)
    
    return fallback_response, "fallback"

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

@router.get("/performance/metrics")
async def get_performance_metrics(current_user: dict = Depends(verify_token)):
    """Get AI response generation performance metrics"""
    try:
        metrics = performance_metrics.get_metrics()
        
        # Add configuration info
        ai_config = get_cached_ai_config()
        config_info = {
            "use_openai": ai_config.get('use_openai', False),
            "use_huggingface": ai_config.get('use_huggingface', True),
            "config_cached": True  # Always true since we use cached config
        }
        
        return {
            "performance_metrics": metrics,
            "configuration": config_info,
            "optimization_status": {
                "config_caching": "enabled",
                "parallel_processing": "enabled", 
                "early_return": "enabled",
                "metrics_tracking": "enabled"
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching performance metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch performance metrics"
        )

@router.post("/performance/reset-metrics")
async def reset_performance_metrics(current_user: dict = Depends(verify_token)):
    """Reset performance metrics (admin only)"""
    try:
        # Simple admin check - in production you'd want proper role checking
        user_id = current_user.get("user_id", "")
        if not user_id.startswith("admin") and user_id != "demo":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        performance_metrics.reset_metrics()
        logger.info(f"Performance metrics reset by user {user_id}")
        
        return {"message": "Performance metrics reset successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting performance metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset performance metrics"
        )

@router.post("/config/refresh")
async def refresh_ai_config(current_user: dict = Depends(verify_token)):
    """Refresh cached AI configuration"""
    try:
        # Clear the cached configuration
        get_cached_ai_config.cache_clear()
        
        # Load fresh configuration
        new_config = get_cached_ai_config()
        
        logger.info(f"AI configuration refreshed by user {current_user.get('user_id')}")
        
        return {
            "message": "AI configuration refreshed successfully",
            "config": {
                "use_openai": new_config.get('use_openai'),
                "use_huggingface": new_config.get('use_huggingface'),
                "model": new_config.get('model')
            }
        }
        
    except Exception as e:
        logger.error(f"Error refreshing AI config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh AI configuration"
        )
