"""
Simplified Content Manager for MEFAPEX Chatbot
Handles static responses from JSON files only
"""

import json
import os
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class ContentManager:
    """
    Static content management system:
    - Static responses from JSON files
    - Intelligent keyword matching
    - Caching for performance
    """
    
    def __init__(self, content_dir: str = "content"):
        self.content_dir = content_dir
        self.static_responses = {}
        self.categories = {}
        self.settings = {}
        self._cache = {}
        self._cache_enabled = True
        
        # Load static content on initialization
        self.load_static_content()
        
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
        Find appropriate response for user message
        Returns: (response_text, source)
        Source can be: static, cache_static, default
        """
        if not user_message or not user_message.strip():
            return self._get_default_response(user_message), "default"
        
        user_message_lower = user_message.lower().strip()
        
        # Check cache first
        if self._cache_enabled and user_message_lower in self._cache:
            cached_response, source = self._cache[user_message_lower]
            logger.debug(f"🎯 Cache hit for: {user_message[:30]}...")
            return cached_response, f"cache_{source}"
        
        # Try static responses first
        response, source = self._find_static_response(user_message_lower)
        
        if response:
            # Cache the response
            if self._cache_enabled:
                self._cache[user_message_lower] = (response, source)
            return response, source
        
        # Return default response
        default_response = self._get_default_response(user_message)
        if self._cache_enabled:
            self._cache[user_message_lower] = (default_response, "default")
        
        return default_response, "default"

    def _find_static_response(self, user_message_lower: str) -> Tuple[Optional[str], str]:
        """Find matching static response"""
        best_match = None
        best_score = 0
        
        for category, responses in self.static_responses.items():
            for response_data in responses:
                if isinstance(response_data, dict):
                    keywords = response_data.get("keywords", [])
                    response_text = response_data.get("response", "")
                    
                    # Calculate match score
                    score = self._calculate_match_score(user_message_lower, keywords)
                    
                    if score > best_score:
                        best_match = response_text
                        best_score = score
                elif isinstance(response_data, str):
                    # Simple string response
                    if category.lower() in user_message_lower:
                        return response_data, "static"
        
        if best_match and best_score > 0.2:  # Minimum threshold
            return best_match, "static"
        
        return None, ""

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

    def _get_default_response(self, user_message: str = "") -> str:
        """Get default response when no match is found"""
        default_responses = [
            "Üzgünüm, bu konuda size yardımcı olamıyorum. Başka bir şey sorabilirsiniz.",
            "Bu konu hakkında bilgim yok. Farklı bir soru sorabilir misiniz?",
            "Size bu konuda yardım edemiyorum. Başka nasıl yardımcı olabilirim?",
            "Bu sorunuzla ilgili bilgim bulunmuyor. Başka sorularınız var mı?"
        ]
        
        # Simple hash-based selection for consistency
        import hashlib
        hash_value = int(hashlib.md5(user_message.encode()).hexdigest()[:8], 16)
        selected_response = default_responses[hash_value % len(default_responses)]
        
        return selected_response

    def get_categories(self) -> Dict:
        """Get all response categories"""
        return self.categories

    def get_stats(self) -> Dict:
        """Get content manager statistics"""
        return {
            "static_responses": len(self.static_responses),
            "categories": len(self.categories),
            "cache_entries": len(self._cache),
            "cache_enabled": self._cache_enabled,
            "database_status": "disabled"
        }

    def clear_cache(self):
        """Clear response cache"""
        self._cache.clear()
        logger.info("🗑️ Response cache cleared")

    def reload_content(self):
        """Reload static content and clear cache"""
        self.clear_cache()
        self.load_static_content()
        logger.info("🔄 Content reloaded")

# Global instance
content_manager = ContentManager()
