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
    Enhanced Static-Only Content Management System:
    - Primary: Static responses from JSON files
    - AI Usage: Multi-level understanding and matching assistance
    - NO AI-generated responses - sistem tamamen static temelli
    - Enhanced default responses with context awareness
    - Advanced caching and performance optimization
    
    Matching Levels:
    1. Direct keyword matching (fast, exact)
    2. AI semantic similarity (intelligent, context-aware) 
    3. Intent-based matching (pattern recognition)
    4. Enhanced default response (contextual fallback)
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
        
        logger.info("🎯 ContentManager initialized in ENHANCED STATIC-ONLY mode")
        logger.info("📝 AI usage: Multi-level understanding assistance (semantic + intent)")
        
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
        Find appropriate response for user message - ENHANCED STATIC SYSTEM
        Flow: Cache -> Direct Match -> AI Semantic Match -> Intent Detection -> Default
        Returns: (response_text, source)
        Source can be: static, ai_enhanced_static, semantic_match, cache_static, default
        
        AI sistem static cevapları daha iyi eşleştirmek için kullanılır:
        - Önce direkt anahtar kelime eşleştirme
        - Sonra AI semantic benzerlik analizi  
        - Intent detection ile kullanıcının ne istediğini anlama
        - En uygun static cevabı bulma ve döndürme
        """
        if not user_message or not user_message.strip():
            return self._get_static_default_response(user_message), "default"
        
        user_message_lower = user_message.lower().strip()
        
        # Check cache first (for performance)
        if self._cache_enabled and user_message_lower in self._cache:
            cached_response, source = self._cache[user_message_lower]
            logger.debug(f"🎯 Cache hit for: {user_message[:30]}...")
            return cached_response, f"cache_{source}"
        
        # Level 1: Direct keyword matching
        response, source = self._find_static_response_direct(user_message_lower)
        if response:
            logger.info(f"✅ Direct keyword match found for: {user_message[:30]}...")
            if self._cache_enabled:
                self._cache[user_message_lower] = (response, source)
            return response, source
        
        # Level 2: AI semantic similarity matching
        if self._ai_enabled and self.model_manager:
            response, source = self._find_static_response_semantic(user_message, user_message_lower)
            if response:
                logger.info(f"🤖✅ AI semantic match found for: {user_message[:30]}...")
                if self._cache_enabled:
                    self._cache[user_message_lower] = (response, source)
                return response, source
        
        # Level 3: Intent-based matching
        response, source = self._find_static_response_intent(user_message, user_message_lower)
        if response:
            logger.info(f"🎯 Intent-based match found for: {user_message[:30]}...")
            if self._cache_enabled:
                self._cache[user_message_lower] = (response, source)
            return response, source
        
        # No static response found - return enhanced default
        default_response = self._get_enhanced_default_response(user_message)
        if self._cache_enabled:
            self._cache[user_message_lower] = (default_response, "default")
        
        logger.info(f"📝 No static match found for: {user_message[:50]}... - returning enhanced default")
        return default_response, "default"
    
    def _find_static_response_direct(self, user_message_lower: str) -> Tuple[Optional[str], str]:
        """
        Level 1: Direct keyword and phrase matching
        Fast, exact matching for common queries
        """
        best_match = None
        best_score = 0
        best_category = ""
        
        for category, response_data in self.static_responses.items():
            if isinstance(response_data, dict):
                keywords = response_data.get("keywords", [])
                response_text = response_data.get("message", "")
                
                # Calculate match score
                score = self._calculate_match_score(user_message_lower, keywords)
                
                if score > best_score:
                    best_match = response_text
                    best_score = score
                    best_category = category
                    
                # Also check for category name match
                if category.lower() in user_message_lower:
                    logger.debug(f"🎯 Direct category match: {category}")
                    return response_text, "static"
            elif isinstance(response_data, str):
                # Simple string response
                if category.lower() in user_message_lower:
                    logger.debug(f"🎯 Direct simple match: {category}")
                    return response_data, "static"
        
        # Require minimum confidence for direct matches
        if best_match and best_score > 0.3:  # Increased threshold for better accuracy
            logger.debug(f"🎯 Direct keyword match: {best_category} (score: {best_score:.3f})")
            return best_match, "static"
        
        return None, ""
    
    def _find_static_response_semantic(self, original_message: str, user_message_lower: str) -> Tuple[Optional[str], str]:
        """
        Level 2: AI-powered semantic similarity matching
        Uses embeddings to find semantically similar static responses
        """
        try:
            if not hasattr(self.model_manager, 'get_sentence_embedding'):
                return None, ""
            
            user_embedding = self.model_manager.get_sentence_embedding(original_message)
            if user_embedding is None:
                return None, ""
            
            best_match = None
            best_similarity = 0.0
            best_category = ""
            similarity_threshold = 0.55  # Lowered for better coverage
            
            # Check similarity with each static response
            for category, response_data in self.static_responses.items():
                if not isinstance(response_data, dict):
                    continue
                
                keywords = response_data.get("keywords", [])
                message_text = response_data.get("message", "")
                
                # Create enhanced text for semantic matching
                # Include keywords, category name, and sample content
                enhanced_text = f"{category} {' '.join(keywords)} {message_text[:150]}"
                
                try:
                    static_embedding = self.model_manager.get_sentence_embedding(enhanced_text)
                    if static_embedding is None:
                        continue
                    
                    # Calculate cosine similarity
                    similarity = self._calculate_cosine_similarity(user_embedding, static_embedding)
                    
                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_match = message_text
                        best_category = category
                        
                        logger.debug(f"🤖 Semantic similarity: {category} ({similarity:.3f})")
                
                except Exception as e:
                    logger.debug(f"Embedding comparison failed for {category}: {e}")
                    continue
            
            # Return match if above threshold
            if best_match and best_similarity >= similarity_threshold:
                logger.info(f"🤖 Semantic match: {best_category} (similarity: {best_similarity:.3f})")
                return best_match, "ai_enhanced_static"
            
            return None, ""
            
        except Exception as e:
            logger.debug(f"Semantic matching error: {e}")
            return None, ""
    
    def _find_static_response_intent(self, original_message: str, user_message_lower: str) -> Tuple[Optional[str], str]:
        """
        Level 3: Intent-based matching
        Analyzes user intent and maps to appropriate static responses
        """
        # Define intent patterns
        intent_patterns = {
            "greeting": {
                "patterns": ["merhaba", "selam", "iyi", "günaydın", "akşam", "nasıl", "hello", "hi"],
                "category": "greetings"
            },
            "company_info": {
                "patterns": ["mefapex", "şirket", "firma", "hakkında", "kimsiniz", "nedir", "company"],
                "category": "company_info"
            },
            "working_hours": {
                "patterns": ["saat", "zaman", "çalışma", "mesai", "açık", "kapalı", "hours"],
                "category": "working_hours"
            },
            "support": {
                "patterns": ["destek", "yardım", "problem", "sorun", "hata", "support", "help"],
                "category": "support_types"
            },
            "technology": {
                "patterns": ["teknoloji", "yazılım", "program", "kod", "development", "tech"],
                "category": "technology_info"
            },
            "thanks": {
                "patterns": ["teşekkür", "sağol", "thanks", "thank you", "bye", "görüşürüz"],
                "category": "thanks_goodbye"
            }
        }
        
        # Calculate intent scores
        best_intent = None
        best_score = 0
        
        for intent_name, intent_data in intent_patterns.items():
            patterns = intent_data["patterns"]
            score = 0
            
            # Count pattern matches
            for pattern in patterns:
                if pattern in user_message_lower:
                    score += 1
            
            # Calculate relative score
            if patterns:
                relative_score = score / len(patterns)
                if relative_score > best_score:
                    best_score = relative_score
                    best_intent = intent_data["category"]
        
        # Return matched static response if intent is confident enough
        if best_intent and best_score > 0.15:  # Minimum intent confidence
            if best_intent in self.static_responses:
                response_data = self.static_responses[best_intent]
                if isinstance(response_data, dict):
                    message = response_data.get("message", "")
                    if message:
                        logger.debug(f"🎯 Intent match: {best_intent} (score: {best_score:.3f})")
                        return message, "intent_based_static"
                elif isinstance(response_data, str):
                    logger.debug(f"🎯 Intent match: {best_intent} (score: {best_score:.3f})")
                    return response_data, "intent_based_static"
        
        return None, ""
    
    def _get_enhanced_default_response(self, user_message: str = "") -> str:
        """
        Enhanced default response with AI-assisted context analysis
        """
        # Use existing static default if available
        if "default_response" in self.static_responses:
            default_data = self.static_responses["default_response"]
            if isinstance(default_data, dict):
                default_message = default_data.get("message", "")
                if default_message and "{user_input}" in default_message:
                    safe_input = user_message[:50] if user_message else "bilinmeyen soru"
                    return default_message.replace("{user_input}", safe_input)
                elif default_message:
                    return default_message
        
        # AI-enhanced contextual default responses
        if user_message:
            message_lower = user_message.lower()
            
            # Context-aware defaults based on question type
            if any(word in message_lower for word in ['ne', 'nedir', 'nasıl', 'kim', 'nerede', 'neden']):
                return ("🤔 **Sorduğunuz konu hakkında hazır bir cevabım yok.**\n\n"
                       "**MEFAPEX olarak size yardımcı olabileceğim konular:**\n"
                       "• 🏭 Şirket bilgileri ve hizmetlerimiz\n"
                       "• ⏰ Çalışma saatleri ve iletişim\n"
                       "• 🛠️ Teknik destek türleri\n"
                       "• 💻 Teknoloji ve yazılım hizmetleri\n\n"
                       "**Daha spesifik sorularınız için:**\n"
                       "• 📞 Direkt destek hattımız\n"
                       "• 📧 destek@mefapex.com\n\n"
                       "Hangi konuda bilgi almak istiyorsunuz? 💬")
            
            elif any(word in message_lower for word in ['help', 'yardım', 'destek']):
                return ("🛠️ **Yardım ve Destek**\n\n"
                       "Size yardımcı olmak için buradayım! \n\n"
                       "**Hızlı erişim için şunları sorabilirsiniz:**\n"
                       "• \"MEFAPEX hakkında bilgi\"\n"
                       "• \"Çalışma saatleriniz nedir?\"\n"
                       "• \"Teknik destek nasıl alabilirim?\"\n"
                       "• \"Hangi teknolojileri kullanıyorsunuz?\"\n\n"
                       "**Acil durumlar için:**\n"
                       "• 📞 Telefon desteği\n"
                       "• 📧 destek@mefapex.com\n\n"
                       "Nasıl yardımcı olabilirim? 🤝")
            
            else:
                return ("💬 **MEFAPEX Chatbot**\n\n"
                       "Sorduğunuz konuda spesifik bir cevabım bulunmuyor. \n\n"
                       "**Size yardımcı olabileceğim ana konular:**\n"
                       "• 👋 Genel karşılama ve bilgilendirme\n"
                       "• 🏭 MEFAPEX şirket bilgileri\n"
                       "• ⏰ Çalışma saatleri ve iletişim\n"
                       "• 🛠️ Teknik destek seçenekleri\n"
                       "• 💻 Teknoloji ve yazılım hizmetleri\n"
                       "• 🙏 Genel yardım ve yönlendirme\n\n"
                       "**Bu konulardan biri ile ilgili soru sormayı deneyin!**\n\n"
                       "🔗 **Direkt iletişim:** destek@mefapex.com")
        
        # Fallback
        return self._get_static_default_response(user_message)
    
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
        """Get enhanced content manager statistics"""
        stats = {
            "static_responses": len(self.static_responses),
            "categories": len(self.categories),
            "cache_entries": len(self._cache),
            "cache_enabled": self._cache_enabled,
            "ai_enabled": self._ai_enabled,
            "huggingface_available": self.model_manager is not None,
            "system_mode": "enhanced_static_only",
            "ai_usage": "multi_level_understanding",
            "matching_levels": {
                "level_1": "direct_keyword_matching",
                "level_2": "ai_semantic_similarity", 
                "level_3": "intent_based_matching"
            }
        }
        
        # Add AI model stats if available (for understanding only)
        if self.model_manager:
            try:
                model_info = self.model_manager.get_model_info()
                stats["ai_model_info"] = {
                    "purpose": "enhanced_static_response_understanding",
                    "capabilities": ["semantic_similarity", "intent_detection", "context_analysis"],
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
    
    def warmup_ai_models(self):
        """
        Warm up AI models for enhanced understanding performance
        """
        if self._ai_enabled and self.model_manager:
            try:
                logger.info("🔥 Warming up AI models for enhanced static response matching...")
                self.model_manager.warmup_models()
                logger.info("✅ Enhanced AI understanding models warmed up successfully")
            except Exception as e:
                logger.error(f"❌ AI warmup failed: {e}")
        else:
            logger.info("ℹ️ AI understanding models not available for warmup")
    
    def enable_ai_understanding(self, enabled: bool = True):
        """
        Enable or disable enhanced AI understanding assistance
        """
        if enabled and not self.model_manager:
            logger.warning("⚠️ Cannot enable AI understanding: model_manager not available")
            return False
        
        self._ai_enabled = enabled
        status = "enabled" if enabled else "disabled"
        logger.info(f"🤖 Enhanced AI understanding assistance {status}")
        return True
    
    def test_enhanced_matching(self, test_queries: List[str] = None) -> Dict:
        """
        Test the enhanced multi-level matching system
        """
        if test_queries is None:
            test_queries = [
                "merhaba nasılsın",           # Should match greetings
                "MEFAPEX ne yapıyor",         # Should match company_info  
                "saat kaçta açıksınız",       # Should match working_hours
                "yardıma ihtiyacım var",      # Should match support_types
                "hangi programlama dilleri", # Should match technology_info
                "teşekkürler görüşürüz",     # Should match thanks_goodbye
                "bugün hava nasıl"           # Should match default
            ]
        
        results = {}
        logger.info("🧪 Testing enhanced matching system...")
        
        for query in test_queries:
            try:
                response, source = self.find_response(query)
                results[query] = {
                    "source": source,
                    "response_length": len(response),
                    "found_static": source != "default"
                }
                logger.info(f"{'✅' if source != 'default' else '❌'} \"{query}\" -> {source}")
            except Exception as e:
                results[query] = {"error": str(e)}
                logger.error(f"❌ Test failed for '{query}': {e}")
        
        # Summary
        successful_matches = sum(1 for r in results.values() 
                               if isinstance(r, dict) and r.get("found_static", False))
        
        summary = {
            "total_tests": len(test_queries),
            "successful_static_matches": successful_matches,
            "default_responses": len(test_queries) - successful_matches,
            "success_rate": f"{(successful_matches/len(test_queries)*100):.1f}%"
        }
        
        logger.info(f"📊 Test Summary: {successful_matches}/{len(test_queries)} static matches "
                   f"({summary['success_rate']} success rate)")
        
        return {
            "results": results,
            "summary": summary
        }

# Global instance
content_manager = ContentManager()
