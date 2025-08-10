"""
💬 Chat Router
Chat endpoints with optimized AI response generation
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import logging
import asyncio
from datetime import datetime

from routers.auth import verify_token

logger = logging.getLogger(__name__)

# Models
class ChatMessage(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    source: str

class SessionData(BaseModel):
    session_id: str
    started_at: str
    message_count: int

# Router
router = APIRouter(prefix="/chat", tags=["chat"])

# Dependencies (will be injected from main)
db_manager = None
qdrant_client = None
embedding_model = None
ai_config = {}

def init_chat_router(database_manager, qdrant, embedding, config):
    """Initialize router with dependencies from main app"""
    global db_manager, qdrant_client, embedding_model, ai_config
    db_manager = database_manager
    qdrant_client = qdrant
    embedding_model = embedding
    ai_config = config

class AIResponseGenerator:
    """Optimized AI response generator with caching and lazy loading"""
    
    def __init__(self):
        self._openai_client = None
        self._huggingface_model = None
        self._response_cache = {}
        self.cache_max_size = 100
    
    @property
    def openai_client(self):
        """Lazy load OpenAI client"""
        if self._openai_client is None and ai_config.get('USE_OPENAI'):
            try:
                import openai
                self._openai_client = openai.OpenAI(api_key=ai_config.get('OPENAI_API_KEY'))
                logger.info("✅ OpenAI client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI: {e}")
        return self._openai_client
    
    @property
    def huggingface_model(self):
        """Lazy load HuggingFace model"""
        if self._huggingface_model is None and ai_config.get('USE_HUGGINGFACE'):
            try:
                from transformers import pipeline
                self._huggingface_model = pipeline(
                    "text-generation",
                    model="microsoft/DialoGPT-small",
                    device=-1  # CPU
                )
                logger.info("✅ HuggingFace model initialized")
            except Exception as e:
                logger.error(f"Failed to initialize HuggingFace: {e}")
        return self._huggingface_model
    
    def get_cached_response(self, query_hash: str) -> Optional[str]:
        """Get cached response if available"""
        return self._response_cache.get(query_hash)
    
    def cache_response(self, query_hash: str, response: str):
        """Cache response with size limit"""
        if len(self._response_cache) >= self.cache_max_size:
            # Remove oldest entry
            oldest_key = next(iter(self._response_cache))
            del self._response_cache[oldest_key]
        
        self._response_cache[query_hash] = response
    
    async def search_knowledge_base(self, query: str) -> Optional[str]:
        """Search in Qdrant knowledge base with optimization"""
        try:
            # Generate query hash for caching
            import hashlib
            query_hash = hashlib.md5(query.lower().encode()).hexdigest()
            
            # Check cache first
            cached_response = self.get_cached_response(query_hash)
            if cached_response:
                logger.debug(f"Cache hit for query: {query[:50]}...")
                return cached_response
            
            # Generate embedding
            if embedding_model is None:
                logger.warning("Embedding model not available")
                return None
            
            query_embedding = embedding_model.encode([query])[0].tolist()
            
            # Search in Qdrant
            search_results = qdrant_client.search(
                collection_name="mefapex_faq",
                query_vector=query_embedding,
                limit=3,
                score_threshold=0.7
            )
            
            if search_results:
                best_match = search_results[0]
                response = best_match.payload.get("answer", "")
                
                # Cache the response
                self.cache_response(query_hash, response)
                
                logger.info(f"✅ Knowledge base match found (score: {best_match.score:.3f})")
                return response
            
            return None
            
        except Exception as e:
            logger.error(f"Knowledge base search error: {e}")
            return None
    
    async def generate_openai_response(self, context: str, query: str) -> str:
        """Generate response using OpenAI with optimization"""
        try:
            if not self.openai_client:
                raise Exception("OpenAI client not available")
            
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": context},
                    {"role": "user", "content": query}
                ],
                max_tokens=300,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"OpenAI generation error: {e}")
            raise
    
    async def generate_huggingface_response(self, context: str, query: str) -> str:
        """Generate response using HuggingFace with optimization"""
        try:
            if not self.huggingface_model:
                raise Exception("HuggingFace model not available")
            
            prompt = f"{context}\nKullanıcı: {query}\nAsistan:"
            
            result = await asyncio.to_thread(
                self.huggingface_model,
                prompt,
                max_length=200,
                num_return_sequences=1,
                temperature=0.7,
                do_sample=True
            )
            
            response = result[0]['generated_text']
            # Extract only the assistant's response
            if "Asistan:" in response:
                response = response.split("Asistan:")[-1].strip()
            
            return response
            
        except Exception as e:
            logger.error(f"HuggingFace generation error: {e}")
            raise

# Global AI generator instance
ai_generator = AIResponseGenerator()

def get_user_session(user_id: str, force_new: bool = False, auto_create: bool = True) -> str:
    """Get or create user session with optimization"""
    try:
        if auto_create:
            return db_manager.get_or_create_session(user_id, force_new=force_new)
        else:
            session = db_manager.get_current_session(user_id)
            if session:
                return session
            elif force_new:
                return db_manager.get_or_create_session(user_id, force_new=True)
            else:
                raise HTTPException(status_code=404, detail="No active session found")
    except Exception as e:
        logger.error(f"Session management error for user {user_id}: {e}")
        # Fallback: try to create a new session
        try:
            return db_manager.get_or_create_session(user_id, force_new=True)
        except Exception as fallback_error:
            logger.error(f"Fallback session creation failed for user {user_id}: {fallback_error}")
            raise

def add_message_to_session(session_id: str, user_message: str, bot_response: str, source: str, user_id: str = None):
    """Add message to session with optimization"""
    try:
        db_manager.add_message(session_id, user_id, user_message, bot_response, source)
    except Exception as e:
        logger.error(f"Failed to add message to session {session_id}: {e}")
        raise

@router.post("/", response_model=ChatResponse)
async def chat_public(message: ChatMessage):
    """Public chat endpoint without authentication"""
    try:
        user_message = message.message.strip()
        
        if not user_message:
            raise HTTPException(status_code=400, detail="Mesaj boş olamaz")
        
        logger.info(f"Public chat message: {user_message}")
        
        # Search knowledge base
        knowledge_response = await ai_generator.search_knowledge_base(user_message)
        
        if knowledge_response:
            return ChatResponse(response=knowledge_response, source="knowledge_base")
        
        # Fallback to AI generation
        context = "Sen MEFAPEX fabrikasının AI asistanısın. Türkçe cevap ver ve yardımcı ol."
        
        try:
            if ai_config.get('USE_OPENAI') and ai_generator.openai_client:
                response_text = await ai_generator.generate_openai_response(context, user_message)
                source = "openai"
            elif ai_config.get('USE_HUGGINGFACE') and ai_generator.huggingface_model:
                response_text = await ai_generator.generate_huggingface_response(context, user_message)
                source = "huggingface"
            else:
                response_text = "🤖 Üzgünüm, şu anda AI servislerim kullanılamıyor. Lütfen daha sonra tekrar deneyin."
                source = "fallback"
        
        except Exception as e:
            logger.error(f"AI response generation failed: {e}")
            response_text = "🤖 Bir hata oluştu. Lütfen tekrar deneyin."
            source = "error"
        
        return ChatResponse(response=response_text, source=source)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Public chat error: {e}")
        return ChatResponse(
            response="🤖 Bir hata oluştu. Lütfen tekrar deneyin.",
            source="error"
        )

@router.post("/authenticated", response_model=ChatResponse)
async def chat_authenticated(message: ChatMessage, current_user: dict = Depends(verify_token)):
    """Authenticated chat endpoint with session management"""
    try:
        user_message = message.message.strip()
        
        if not user_message:
            raise HTTPException(status_code=400, detail="Mesaj boş olamaz")
        
        logger.info(f"User {current_user['username']} message: {user_message}")
        
        # Get or create session
        try:
            session_id = get_user_session(current_user["user_id"], force_new=False, auto_create=True)
            logger.debug(f"Using session {session_id} for user {current_user['username']}")
        except Exception as session_error:
            logger.error(f"Session error for user {current_user['username']}: {session_error}")
            session_id = get_user_session(current_user["user_id"], force_new=True, auto_create=True)
        
        # Search knowledge base first
        knowledge_response = await ai_generator.search_knowledge_base(user_message)
        
        if knowledge_response:
            response_text = knowledge_response
            source = "knowledge_base"
        else:
            # Generate AI response
            context = f"""Sen MEFAPEX fabrikasının AI asistanısın. 
            Kullanıcı: {current_user['username']}
            Türkçe cevap ver ve yardımcı ol."""
            
            try:
                if ai_config.get('USE_OPENAI') and ai_generator.openai_client:
                    response_text = await ai_generator.generate_openai_response(context, user_message)
                    source = "openai"
                elif ai_config.get('USE_HUGGINGFACE') and ai_generator.huggingface_model:
                    response_text = await ai_generator.generate_huggingface_response(context, user_message)
                    source = "huggingface"
                else:
                    response_text = "🤖 Sistem geçici olarak kullanılamıyor. Lütfen daha sonra tekrar deneyin."
                    source = "error"
                    
            except Exception as e:
                logger.error(f"Response generation failed: {e}")
                # Fallback to alternative method
                try:
                    if ai_config.get('USE_HUGGINGFACE') and source != "huggingface":
                        response_text = await ai_generator.generate_huggingface_response(context, user_message)
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
        try:
            add_message_to_session(session_id, user_message, response_text, source, user_id=current_user["user_id"])
            logger.debug(f"Message saved to session {session_id} for user {current_user['username']}")
        except Exception as save_error:
            logger.error(f"Failed to save message to session for user {current_user['username']}: {save_error}")
            # Don't fail the request, just log the error
        
        return ChatResponse(response=response_text, source=source)
        
    except Exception as e:
        logger.error(f"Authenticated chat endpoint error: {e}")
        response_text = "🤖 Bir hata oluştu. Lütfen tekrar deneyin."
        source = "error"
        
        # Try to save to session even on error
        try:
            if 'session_id' not in locals():
                session_id = get_user_session(current_user["user_id"], force_new=False, auto_create=True)
            add_message_to_session(session_id, user_message if 'user_message' in locals() else "Hata", response_text, source, user_id=current_user["user_id"])
            logger.debug(f"Error message saved to session for user {current_user['username']}")
        except Exception as save_error:
            logger.error(f"Critical: Failed to save error message to session for user {current_user['username']}: {save_error}")
            
        return ChatResponse(response=response_text, source=source)

@router.post("/sessions/save", response_model=dict)
async def save_chat_session(session_data: SessionData, current_user: dict = Depends(verify_token)):
    """Save chat session"""
    try:
        db_manager.save_chat_session(
            current_user["user_id"],
            session_data.session_id,
            session_data.started_at,
            session_data.message_count
        )
        return {"success": True, "message": "Session saved successfully"}
    except Exception as e:
        logger.error(f"Failed to save session: {e}")
        raise HTTPException(status_code=500, detail="Failed to save session")

@router.post("/sessions/save-beacon")
async def save_session_beacon(request_data: dict):
    """Save session via beacon (for page unload)"""
    try:
        session_id = request_data.get("session_id")
        # Simple beacon save - no authentication required for page unload
        if session_id:
            logger.info(f"📡 Beacon save for session {session_id[:8]}...")
            return {"success": True}
        return {"success": False, "error": "No session ID"}
    except Exception as e:
        logger.error(f"Beacon save error: {e}")
        return {"success": False, "error": str(e)}

@router.get("/history", response_model=List[Dict])
async def get_chat_history(current_user: dict = Depends(verify_token)):
    """Get user's chat history"""
    try:
        history = db_manager.get_chat_sessions_with_history(current_user["user_id"], limit=15)
        return history
    except Exception as e:
        logger.error(f"Failed to get chat history for user {current_user['username']}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get chat history")

@router.delete("/history", response_model=dict)
async def clear_chat_history(current_user: dict = Depends(verify_token)):
    """Clear user's chat history"""
    try:
        db_manager.clear_chat_history(current_user["user_id"])
        logger.info(f"✅ Chat history cleared for user {current_user['username']}")
        return {"success": True, "message": "Chat history cleared successfully"}
    except Exception as e:
        logger.error(f"Failed to clear chat history for user {current_user['username']}: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear chat history")
