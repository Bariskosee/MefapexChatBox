"""
Simplified Content Manager for MEFAPEX Chatbot
Handles static responses from JSON files
"""

import json
import os
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

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
            self._cache_enabled = self.settings.get("cache_enabled", True)
            
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
        best_source = "static"
        
        # Updated to match the actual JSON structure
        for category, response_data in self.static_responses.items():
            # Each category directly contains message and keywords
            keywords = response_data.get("keywords", [])
            score = self._calculate_match_score(user_message_lower, keywords)
            
            if score > best_score and score > 0.1:  # Lower threshold for better matching
                best_match = response_data.get("message", "")
                best_score = score
                best_source = f"static_{category}"
        
        if best_match:
            logger.info(f"🎯 Static match: {best_source} (score: {best_score:.2f})")
        
        return best_match, best_source

    def _calculate_match_score(self, user_message: str, keywords: List[str]) -> float:
        """Calculate keyword match score with improved algorithm"""
        if not keywords:
            return 0
        
        user_message_clean = user_message.lower().strip()
        
        # Direct keyword match (highest priority)
        for keyword in keywords:
            keyword_clean = keyword.lower().strip()
            if keyword_clean == user_message_clean:
                return 1.0  # Perfect match
            if keyword_clean in user_message_clean:
                return 0.8  # Substring match
        
        # Reverse check - user message contains keyword
        for keyword in keywords:
            keyword_clean = keyword.lower().strip()
            if user_message_clean in keyword_clean:
                return 0.7  # User message is substring of keyword
        
        # Word-based matching
        user_words = set(user_message_clean.split())
        total_score = 0
        
        for keyword in keywords:
            keyword_words = set(keyword.lower().split())
            if keyword_words:
                matches = len(user_words.intersection(keyword_words))
                if matches > 0:
                    word_score = matches / len(keyword_words)
                    total_score = max(total_score, word_score)
        
        return total_score

    def _get_default_response(self, user_message: str) -> str:
        """Get default response when no match found"""
        default_responses = [
            "Üzgünüm, bu konuda size nasıl yardımcı olabileceğimi anlayamadım. Daha spesifik bir soru sorabilir misiniz?",
            "Bu konuda elimde bilgi bulunmuyor. Başka bir şekilde yardımcı olabilir miyim?",
            "Sorunuzu anlayamadım. Lütfen farklı kelimelerle tekrar söyleyebilir misiniz?",
            "Bu konu hakkında size bilgi veremiyorum. Başka bir konuda yardım edebilirim.",
        ]
        
        # Simple hash-based selection for consistency
        hash_val = hash(user_message) % len(default_responses)
        return default_responses[hash_val]

    def add_dynamic_response(self, category: str, keywords: List[str], message: str) -> bool:
        """Add a dynamic response to PostgreSQL database"""
        try:
            import json
            from database.manager import db_manager
            
            db = db_manager
            
            # Check if sync connection is available and working
            if not hasattr(db, 'sync_connection') or db.sync_connection is None:
                logger.warning("PostgreSQL not available for adding dynamic response")
                return False
                
            try:
                cursor = db.sync_connection.cursor()
                cursor.execute("SELECT 1")  # Test connection
            except Exception:
                logger.warning("PostgreSQL connection not working for adding dynamic response")
                return False
            
            # Insert dynamic response with JSON serialized keywords
            cursor.execute(
                """INSERT INTO dynamic_responses 
                   (category, keywords, response_text, created_at, is_active) 
                   VALUES (%s, %s, %s, CURRENT_TIMESTAMP, TRUE)""",
                (category, json.dumps(keywords, ensure_ascii=False), message)
            )
            db.sync_connection.commit()
            
            # Clear cache to ensure new response is used
            self._cache.clear()
            
            logger.info(f"✅ Dynamic response added: {category}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to add dynamic response: {e}")
            return False

    def update_response_usage(self, response_text: str):
        """Update usage statistics for dynamic responses"""
        try:
            from database.manager import db_manager
            
            db = db_manager
            
            # Check if sync connection is available and working
            if not hasattr(db, 'sync_connection') or db.sync_connection is None:
                return
                
            try:
                cursor = db.sync_connection.cursor()
                cursor.execute("SELECT 1")  # Test connection
            except Exception:
                logger.debug("PostgreSQL connection not available for updating usage stats")
                return
            
            cursor.execute(
                """UPDATE dynamic_responses 
                   SET usage_count = usage_count + 1, 
                       last_used = CURRENT_TIMESTAMP 
                   WHERE response_text = %s AND is_active = TRUE""",
                (response_text,)
            )
            db.sync_connection.commit()
            
        except Exception as e:
            logger.error(f"❌ Failed to update usage stats: {e}")

    def get_categories(self) -> Dict:
        """Get all response categories"""
        return self.categories

    def get_stats(self) -> Dict:
        """Get content manager statistics"""
        try:
            from database.manager import db_manager
            
            db = db_manager
            
            # Check if sync connection is available and working
            if not hasattr(db, 'sync_connection') or db.sync_connection is None:
                return {
                    "static_responses": len(self.static_responses),
                    "dynamic_responses": 0,
                    "categories": len(self.categories),
                    "cache_entries": len(self._cache),
                    "cache_enabled": self._cache_enabled,
                    "database_status": "unavailable"
                }
                
            try:
                cursor = db.sync_connection.cursor()
                cursor.execute("SELECT 1")  # Test connection
            except Exception:
                return {
                    "static_responses": len(self.static_responses),
                    "dynamic_responses": 0,
                    "categories": len(self.categories),
                    "cache_entries": len(self._cache),
                    "cache_enabled": self._cache_enabled,
                    "database_status": "connection_error"
                }
            
            # Get dynamic responses count
            cursor.execute("SELECT COUNT(*) as count FROM dynamic_responses WHERE is_active = TRUE")
            dynamic_count = cursor.fetchone()["count"]
            
            # Get most used dynamic responses
            cursor.execute(
                """SELECT category, response_text, usage_count 
                   FROM dynamic_responses 
                   WHERE is_active = TRUE 
                   ORDER BY usage_count DESC 
                   LIMIT 5"""
            )
            top_dynamic = cursor.fetchall()
            
            return {
                "static_responses": len(self.static_responses),
                "dynamic_responses": dynamic_count,
                "categories": len(self.categories),
                "cache_entries": len(self._cache),
                "cache_enabled": self._cache_enabled,
                "database_status": "connected",
                "top_dynamic_responses": [
                    {
                        "category": row["category"],
                        "response": row["response_text"][:50] + "...",
                        "usage_count": row["usage_count"]
                    } for row in top_dynamic
                ]
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get stats: {e}")
            return {
                "static_responses": len(self.static_responses),
                "dynamic_responses": 0,
                "categories": len(self.categories),
                "cache_entries": len(self._cache),
                "cache_enabled": self._cache_enabled,
                "database_status": f"error: {str(e)}"
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
