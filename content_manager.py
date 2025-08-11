"""
Content Manager for MEFAPEX Chatbot
Handles static responses from JSON and dynamic content from database
"""

import json
import os
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class ContentManager:
    """
    Hybrid content management system:
    - Static responses from JSON files
    - Dynamic content from database
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
            self._cache_enabled = self.settings.get("cache_enabled", True)
            
            logger.info(f"✅ Loaded {len(self.static_responses)} static responses")
            logger.info(f"📁 Categories: {list(self.categories.keys())}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load static content: {e}")
            return False
    
    def find_response(self, user_message: str) -> Tuple[str, str]:
        """
        Find the best response for user message
        Returns: (response_text, source)
        """
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
        
        # If no static response found, try database (future implementation)
        # TODO: Add database lookup here
        
        # Return default response
        default_response = self._get_default_response(user_message)
        if self._cache_enabled:
            self._cache[user_message_lower] = (default_response, "default")
        
        return default_response, "default"
    
    def _find_static_response(self, user_message_lower: str) -> Tuple[Optional[str], str]:
        """Find response in static JSON data"""
        best_match = None
        best_score = 0
        best_category = ""
        
        # Check each response category
        for response_key, response_data in self.static_responses.items():
            if response_key == "default_response":
                continue
                
            keywords = response_data.get("keywords", [])
            category = response_data.get("category", "")
            
            # Skip disabled categories
            if not self.categories.get(category, {}).get("enabled", True):
                continue
            
            # Calculate match score
            score = self._calculate_match_score(user_message_lower, keywords)
            
            if score > best_score:
                best_score = score
                best_match = response_data.get("message", "")
                best_category = category
        
        # Return best match if score is high enough
        if best_score > 0.3:  # Threshold for accepting a match
            logger.debug(f"📍 Static match found: {best_category} (score: {best_score:.2f})")
            return best_match, f"static_{best_category}"
        
        return None, ""
    
    def _calculate_match_score(self, user_message: str, keywords: List[str]) -> float:
        """Calculate how well user message matches keywords"""
        if not keywords:
            return 0.0
        
        words_in_message = user_message.split()
        matched_keywords = 0
        
        for keyword in keywords:
            if keyword.lower() in user_message:
                matched_keywords += 1
        
        # Score based on percentage of matched keywords
        score = matched_keywords / len(keywords)
        
        # Bonus for exact word matches
        for keyword in keywords:
            if keyword.lower() in words_in_message:
                score += 0.1
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _get_default_response(self, user_message: str) -> str:
        """Get default response when no match found"""
        default_data = self.static_responses.get("default_response", {})
        default_message = default_data.get("message", "")
        
        # Replace placeholder with user input
        return default_message.replace("{user_input}", user_message)
    
    def add_dynamic_response(self, category: str, keywords: List[str], message: str) -> bool:
        """Add a dynamic response (future database implementation)"""
        # TODO: Implement database storage
        logger.info(f"📝 Dynamic response request: {category}")
        return True
    
    def get_categories(self) -> Dict:
        """Get all available categories"""
        return self.categories
    
    def get_stats(self) -> Dict:
        """Get content manager statistics"""
        return {
            "static_responses": len(self.static_responses),
            "categories": len(self.categories),
            "cache_size": len(self._cache),
            "cache_enabled": self._cache_enabled,
            "last_loaded": datetime.now().isoformat()
        }
    
    def clear_cache(self) -> None:
        """Clear response cache"""
        self._cache.clear()
        logger.info("🗑️ Response cache cleared")
    
    def reload_content(self) -> bool:
        """Reload static content from files"""
        self.clear_cache()
        return self.load_static_content()

# Global content manager instance
content_manager = ContentManager()
