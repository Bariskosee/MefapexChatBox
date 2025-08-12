"""
Enhanced Content Manager for MEFAPEX Chatbot
Handles static responses from JSON and dynamic content from PostgreSQL database
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
    - Dynamic content from PostgreSQL database
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
        
        # Ensure dynamic responses table exists
        self._ensure_dynamic_table_exists()
        
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
        Source can be: static, dynamic_database, cache_static, cache_dynamic, default
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
        
        # Try dynamic content from database
        dynamic_response = self._get_dynamic_response(user_message_lower)
        if dynamic_response:
            if self._cache_enabled:
                self._cache[user_message_lower] = (dynamic_response, "dynamic_database")
            return dynamic_response, "dynamic_database"
        
        # Return default response
        default_response = self._get_default_response(user_message)
        if self._cache_enabled:
            self._cache[user_message_lower] = (default_response, "default")
        
        return default_response, "default"

    def _get_dynamic_response(self, user_message: str) -> Optional[str]:
        """Get dynamic response from PostgreSQL database"""
        try:
            from database_manager import db_manager
            
            conn = db_manager._get_connection()
            cursor = conn.cursor()
            
            # Search for matching keywords in dynamic responses
            cursor.execute(
                """SELECT response_text, keywords, category FROM dynamic_responses 
                   WHERE is_active = TRUE 
                   ORDER BY created_at DESC""")
            
            results = cursor.fetchall()
            db_manager._put_connection(conn)
            
            # Check keyword matches
            for row in results:
                response_text = row["response_text"]
                keywords = row["keywords"] if isinstance(row["keywords"], list) else []
                category = row["category"]
                
                # Check if any keyword matches the user message
                for keyword in keywords:
                    if keyword.lower() in user_message.lower():
                        logger.info(f"✅ Dynamic response match: {keyword} -> {category}")
                        return response_text
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get dynamic response: {e}")
            return None

    def _ensure_dynamic_table_exists(self):
        """Ensure dynamic_responses table exists in PostgreSQL"""
        try:
            from database_manager import db_manager
            
            conn = db_manager._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS dynamic_responses (
                    id SERIAL PRIMARY KEY,
                    category VARCHAR(100) NOT NULL,
                    keywords JSONB NOT NULL,
                    response_text TEXT NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_by VARCHAR(100) DEFAULT 'system',
                    usage_count INTEGER DEFAULT 0,
                    last_used TIMESTAMP WITH TIME ZONE
                )
            ''')
            
            # Create indexes for faster searches
            cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_dynamic_responses_keywords ON dynamic_responses USING GIN (keywords)'
            )
            cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_dynamic_responses_category ON dynamic_responses(category)'
            )
            cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_dynamic_responses_active ON dynamic_responses(is_active)'
            )
            
            conn.commit()
            db_manager._put_connection(conn)
            logger.info("✅ Dynamic responses table ensured")
            
        except Exception as e:
            logger.error(f"❌ Failed to create dynamic responses table: {e}")

    def _find_static_response(self, user_message_lower: str) -> Tuple[Optional[str], str]:
        """Find matching static response"""
        best_match = None
        best_score = 0
        best_source = "static"
        
        for category, category_data in self.static_responses.items():
            responses = category_data.get("responses", [])
            
            for response_item in responses:
                keywords = response_item.get("keywords", [])
                score = self._calculate_match_score(user_message_lower, keywords)
                
                if score > best_score and score > 0.3:  # Minimum threshold
                    best_match = response_item.get("message", "")
                    best_score = score
                    best_source = f"static_{category}"
        
        if best_match:
            logger.debug(f"🎯 Static match: {best_source} (score: {best_score:.2f})")
        
        return best_match, best_source

    def _calculate_match_score(self, user_message: str, keywords: List[str]) -> float:
        """Calculate keyword match score"""
        if not keywords:
            return 0
        
        user_words = set(user_message.lower().split())
        keyword_words = set()
        
        for keyword in keywords:
            keyword_words.update(keyword.lower().split())
        
        if not keyword_words:
            return 0
        
        matches = len(user_words.intersection(keyword_words))
        return matches / len(keyword_words)

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
            from database_manager import db_manager
            
            conn = db_manager._get_connection()
            cursor = conn.cursor()
            
            # Insert dynamic response
            cursor.execute(
                """INSERT INTO dynamic_responses 
                   (category, keywords, response_text, created_at, is_active) 
                   VALUES (%s, %s, %s, CURRENT_TIMESTAMP, TRUE)""",
                (category, keywords, message)
            )
            conn.commit()
            db_manager._put_connection(conn)
            
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
            from database_manager import db_manager
            
            conn = db_manager._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                """UPDATE dynamic_responses 
                   SET usage_count = usage_count + 1, 
                       last_used = CURRENT_TIMESTAMP 
                   WHERE response_text = %s AND is_active = TRUE""",
                (response_text,)
            )
            conn.commit()
            db_manager._put_connection(conn)
            
        except Exception as e:
            logger.error(f"❌ Failed to update usage stats: {e}")

    def get_categories(self) -> Dict:
        """Get all response categories"""
        return self.categories

    def get_stats(self) -> Dict:
        """Get content manager statistics"""
        try:
            from database_manager import db_manager
            
            conn = db_manager._get_connection()
            cursor = conn.cursor()
            
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
            
            db_manager._put_connection(conn)
            
            return {
                "static_responses": len(self.static_responses),
                "dynamic_responses": dynamic_count,
                "categories": len(self.categories),
                "cache_entries": len(self._cache),
                "cache_enabled": self._cache_enabled,
                "top_dynamic_responses": [
                    {
                        "category": row["category"],
                        "response": row["response_text"][:50] + "...",
                        "usage_count": row["usage_count"]
                    }
                    for row in top_dynamic
                ]
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get stats: {e}")
            return {
                "static_responses": len(self.static_responses),
                "error": str(e)
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
