"""
Static-Only Content Manager for MEFAPEX Chatbot
Handles ONLY static responses from JSON files + AI-assisted understanding
AI is used ONLY to better understand user intent and match with static responses
"""

import json
import os
import logging
import asyncio
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class ContentManager:
    """
    Static-Only Content Management System:
    - Primary: Static responses from JSON files
    - AI Usage: ONLY for better understanding user intent to match static responses
    - No AI-generated responses - sistem tamamen static temelli
    - Default response when no static match found
    - Response caching for performance
    """
    
    def __init__(self, content_dir: str = "content"):
        self.content_dir = content_dir
        self.static_responses = {}
        self.categories = {}
        self.settings = {}
        self._cache = {}
        self._cache_enabled = True
        self._ai_enabled = True  # AI sadece anlama için kullanılır
        
        # Import model manager for AI-assisted understanding (not generation)
        try:
            from model_manager import model_manager
            self.model_manager = model_manager
            logger.info("✅ AI understanding assistance enabled (for static response matching)")
        except ImportError as e:
            self.model_manager = None
            self._ai_enabled = False
            logger.warning(f"⚠️ AI understanding assistance not available: {e}")
        
        # Load static content on initialization
        self.load_static_content()
        
        logger.info("🎯 ContentManager initialized in STATIC-ONLY mode")
        logger.info("📝 AI usage: Understanding assistance only, no response generation")
        
    def load_static_content(self) -> bool:
        """Load static responses from JSON file"""
        try:
            json_path = os.path.join(self.content_dir, "static_responses.json")
            
            if not os.path.exists(json_path):
                logger.warning(f"Static responses file not found: {json_path}")
                return False
                
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            self.static_responses = data.get("responses", {})
            self.categories = data.get("categories", {})
            self.settings = data.get("settings", {})
            
            logger.info(f"✅ Loaded {len(self.static_responses)} static responses")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load static content: {e}")
            return False

    def find_response(self, user_message: str) -> Tuple[str, str]:
        """
        Find appropriate response for user message - STATIC ONLY SYSTEM
        Flow: Static Response -> AI Enhanced Understanding -> Default Response
        Returns: (response_text, source)
        Source can be: static, cache_static, default
        
        Sistem tamamen static cevap temelli çalışır:
        - Static sorular arasında cevap varsa o döner
        - Static sorular arasında cevap yoksa varsayılan mesaj döner
        - Hugging Face sadece static soruları daha iyi anlamak ve yanıtlamak için kullanılır
        """
        if not user_message or not user_message.strip():
            return self._get_static_default_response(user_message), "default"
        
        user_message_lower = user_message.lower().strip()
        
        # Check cache first (for performance)
        if self._cache_enabled and user_message_lower in self._cache:
            cached_response, source = self._cache[user_message_lower]
            logger.debug(f"🎯 Cache hit for: {user_message[:30]}...")
            return cached_response, f"cache_{source}"
        
        # Try static responses first (primary system)
        response, source = self._find_static_response_enhanced(user_message_lower, user_message)
        
        if response:
            # Cache the response
            if self._cache_enabled:
                self._cache[user_message_lower] = (response, source)
            return response, source
        
        # No static response found - return default static message
        default_response = self._get_static_default_response(user_message)
        if self._cache_enabled:
            self._cache[user_message_lower] = (default_response, "default")
        
        logger.info(f"📝 No static response found for: {user_message[:50]}... - returning default")
        return default_response, "default"
    
    async def _check_relevance_async(self, user_message: str):
        """
        Async wrapper for relevance detection
        """
        if self.relevance_detector:
            return await self.relevance_detector.classify(user_message)
        return None
    
    def _run_relevance_check(self, user_message: str):
        """
        Synchronous wrapper to run relevance check in thread
        """
        return asyncio.run(self._check_relevance_async(user_message))

    def _find_static_response_enhanced(self, user_message_lower: str, original_message: str) -> Tuple[Optional[str], str]:
        """
        Enhanced static response finder with AI-assisted understanding
        AI is used ONLY to better understand and match static responses
        """
        # First try direct keyword matching
        direct_response, source = self._find_static_response(user_message_lower)
        if direct_response:
            logger.info(f"✅ Direct static match found for: {original_message[:30]}...")
            return direct_response, source
        
        # If no direct match, try AI-enhanced understanding (if available)
        if self._ai_enabled and self.model_manager:
            try:
                enhanced_response = self._ai_enhanced_static_matching(original_message, user_message_lower)
                if enhanced_response:
                    logger.info(f"🤖✅ AI-enhanced static match found for: {original_message[:30]}...")
                    return enhanced_response, "static"
            except Exception as e:
                logger.debug(f"AI-enhanced matching failed: {e}")
        
        return None, ""
    
    def _ai_enhanced_static_matching(self, original_message: str, user_message_lower: str) -> Optional[str]:
        """
        Use AI to better understand user intent and match with static responses
        AI DOES NOT generate responses, only helps understand which static response to use
        """
        try:
            # Create embeddings for the user message and all static response keywords
            if not hasattr(self.model_manager, 'get_sentence_embedding'):
                return None
            
            user_embedding = self.model_manager.get_sentence_embedding(original_message)
            if user_embedding is None:
                return None
            
            best_match = None
            best_similarity = 0.0
            similarity_threshold = 0.6  # Minimum similarity for match
            
            # Check similarity with each static response's keywords and content
            for category, response_data in self.static_responses.items():
                if not isinstance(response_data, dict):
                    continue
                
                keywords = response_data.get("keywords", [])
                message_text = response_data.get("message", "")
                
                # Create combined text for better matching
                combined_text = " ".join(keywords) + " " + message_text[:200]
                
                try:
                    static_embedding = self.model_manager.get_sentence_embedding(combined_text)
                    if static_embedding is None:
                        continue
                    
                    # Calculate cosine similarity
                    similarity = self._calculate_cosine_similarity(user_embedding, static_embedding)
                    
                    if similarity > best_similarity and similarity >= similarity_threshold:
                        best_similarity = similarity
                        best_match = message_text
                        
                        logger.debug(f"🎯 AI similarity match: {category} ({similarity:.3f})")
                
                except Exception as e:
                    logger.debug(f"Embedding comparison failed for {category}: {e}")
                    continue
            
            if best_match and best_similarity >= similarity_threshold:
                logger.info(f"🤖 AI-enhanced match found with similarity: {best_similarity:.3f}")
                return best_match
            
            return None
            
        except Exception as e:
            logger.debug(f"AI-enhanced static matching error: {e}")
            return None
    
    def _calculate_cosine_similarity(self, embedding1, embedding2):
        """Calculate cosine similarity between two embeddings"""
        try:
            import numpy as np
            
            # Normalize embeddings
            norm1 = np.linalg.norm(embedding1)
            norm2 = np.linalg.norm(embedding2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            # Calculate cosine similarity
            similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
            return float(similarity)
            
        except Exception as e:
            logger.debug(f"Cosine similarity calculation error: {e}")
            return 0.0

    def _find_static_response(self, user_message_lower: str) -> Tuple[Optional[str], str]:
        """Find matching static response with keyword matching"""
        best_match = None
        best_score = 0
        
        for category, response_data in self.static_responses.items():
            if isinstance(response_data, dict):
                keywords = response_data.get("keywords", [])
                response_text = response_data.get("message", "")
                
                # Calculate match score
                score = self._calculate_match_score(user_message_lower, keywords)
                
                if score > best_score:
                    best_match = response_text
                    best_score = score
                    
                # Also check for category name match
                if category.lower() in user_message_lower:
                    return response_text, "static"
            elif isinstance(response_data, str):
                # Simple string response
                if category.lower() in user_message_lower:
                    return response_data, "static"
        
        if best_match and best_score > 0.2:  # Minimum threshold
            return best_match, "static"
        
        return None, ""
    
    def _get_static_default_response(self, user_message: str = "") -> str:
        """
        Get static default response - sistem tamamen static temelli
        Static sorularda cevap yoksa bu mesaj döner
        """
        # Static responses'dan default_response'u kullan
        if "default_response" in self.static_responses:
            default_data = self.static_responses["default_response"]
            if isinstance(default_data, dict):
                default_message = default_data.get("message", "")
                if default_message and "{user_input}" in default_message:
                    # User input'u güvenli şekilde ekle
                    safe_input = user_message[:50] if user_message else "bilinmeyen soru"
                    return default_message.replace("{user_input}", safe_input)
                elif default_message:
                    return default_message
        
        # Fallback default response
        return ("🤔 **Üzgünüm, bu konuda hazır bir cevabım yok.**\n\n"
               "**Size yardımcı olabilmem için:**\n"
               "• Daha spesifik bir soru sorabilirsiniz\n"
               "• Aşağıdaki konulardan birini seçebilirsiniz:\n\n"
               "**Mevcut konularım:**\n"
               "• 👋 Selamlama ve karşılama\n"
               "• 🏭 MEFAPEX şirket bilgileri\n"
               "• ⏰ Çalışma saatleri\n"
               "• 🛠️ Teknik destek türleri\n"
               "• 💻 Teknoloji ve yazılım\n"
               "• 🙏 Teşekkür ve veda\n\n"
               "**Direkt iletişim:**\n"
               "• 📞 Telefon desteği\n"
               "• 📧 destek@mefapex.com\n\n"
               "Hangi konuda yardım almak istiyorsunuz? 💬")

    def _calculate_match_score(self, user_message: str, keywords: List[str]) -> float:
        """Calculate keyword match score"""
        if not keywords:
            return 0.0
        
        user_words = set(user_message.lower().split())
        keyword_words = set()
        
        for keyword in keywords:
            keyword_words.update(keyword.lower().split())
        
        if not keyword_words:
            return 0.0
        
        # Calculate intersection score
        intersection = user_words.intersection(keyword_words)
        score = len(intersection) / len(keyword_words)
        
        # Bonus for exact phrase matches
        for keyword in keywords:
            if keyword.lower() in user_message.lower():
                score += 0.3
        
        return min(score, 1.0)

    def get_categories(self) -> Dict:
        """Get all response categories"""
        return self.categories

    def get_stats(self) -> Dict:
        """Get content manager statistics"""
        stats = {
            "static_responses": len(self.static_responses),
            "categories": len(self.categories),
            "cache_entries": len(self._cache),
            "cache_enabled": self._cache_enabled,
            "ai_enabled": self._ai_enabled,
            "huggingface_available": self.model_manager is not None,
            "system_mode": "static_only",
            "ai_usage": "understanding_only"
        }
        
        # Add AI model stats if available (for understanding only)
        if self.model_manager:
            try:
                model_info = self.model_manager.get_model_info()
                stats["ai_model_info"] = {
                    "purpose": "static_response_understanding_only",
                    "turkish_model_loaded": model_info.get("turkish_sentence_model_loaded", False),
                    "device": model_info.get("device", "unknown"),
                    "cache_hits": model_info.get("cache_info", {}).get("embedding_cache_hits", 0),
                    "cache_size": model_info.get("cache_info", {}).get("embedding_cache_size", 0)
                }
            except Exception as e:
                logger.warning(f"Could not get AI model stats: {e}")
                stats["ai_model_info"] = {"error": str(e)}
        
        return stats

    def clear_cache(self):
        """Clear response cache"""
        self._cache.clear()
        logger.info("🗑️ Response cache cleared")

    def reload_content(self):
        """Reload static content and clear cache"""
        self.clear_cache()
        self.load_static_content()
        logger.info("🔄 Content reloaded")
    
    async def find_response_async(self, user_message: str) -> Tuple[str, str]:
        """
        Async version of find_response
        """
        return self.find_response(user_message)
    
    def warmup_ai_models(self):
        """
        Warm up AI models for better understanding performance
        """
        if self._ai_enabled and self.model_manager:
            try:
                logger.info("🔥 Warming up AI models for understanding assistance...")
                self.model_manager.warmup_models()
                logger.info("✅ AI understanding models warmed up successfully")
            except Exception as e:
                logger.error(f"❌ AI warmup failed: {e}")
        else:
            logger.info("ℹ️ AI understanding models not available for warmup")
    
    def enable_ai_understanding(self, enabled: bool = True):
        """
        Enable or disable AI understanding assistance (for static response matching)
        """
        if enabled and not self.model_manager:
            logger.warning("⚠️ Cannot enable AI understanding: model_manager not available")
            return False
        
        self._ai_enabled = enabled
        status = "enabled" if enabled else "disabled"
        logger.info(f"🤖 AI understanding assistance {status}")
        return True

# Global instance
content_manager = ContentManager()
