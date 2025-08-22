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
        
        # NEW: Inverted index for optimized keyword lookup
        self._keyword_index = {}  # keyword -> set of categories
        self._phrase_index = {}   # phrase -> set of categories
        self._index_built = False
        
        # Import model manager for AI-assisted understanding (not generation)
        try:
            from model_manager import model_manager
            self.model_manager = model_manager
            logger.info("✅ AI understanding assistance enabled (for static response matching)")
        except ImportError as e:
            self.model_manager = None
            self._ai_enabled = False
            logger.warning(f"⚠️ AI understanding assistance not available: {e}")
        
        # ENHANCED: Import improved Turkish content manager
        try:
            from improved_turkish_content_manager import improved_turkish_content
            self.improved_turkish = improved_turkish_content
            logger.info("🇹🇷 Enhanced Turkish content manager integrated")
        except ImportError as e:
            self.improved_turkish = None
            logger.warning(f"⚠️ Enhanced Turkish content manager not available: {e}")
        
        # Enhanced Question Matcher'ı initialize et
        try:
            from enhanced_question_matcher import EnhancedQuestionMatcher
            self.enhanced_matcher = EnhancedQuestionMatcher(self.model_manager)
            logger.info("🧠 Enhanced Question Matcher initialized with semantic search")
        except ImportError as e:
            self.enhanced_matcher = None
            logger.warning(f"⚠️ Enhanced Question Matcher not available: {e}")
        
        # NEW: Intent Classifier'ı initialize et
        try:
            from intent_classifier import intent_classifier
            self.intent_classifier = intent_classifier
            if intent_classifier.is_trained:
                logger.info("🎯 Intent Classifier initialized and ready")
            else:
                logger.info("🎯 Intent Classifier available but not trained")
        except ImportError as e:
            self.intent_classifier = None
            logger.warning(f"⚠️ Intent Classifier not available: {e}")
        
        # İstatistikler - enhanced tracking
        self.stats = {
            'total_queries': 0,
            'exact_matches': 0,
            'fuzzy_matches': 0,
            'semantic_matches': 0,
            'enhanced_matches': 0,
            'intent_matches': 0,  # NEW: Intent classifier matches
            'no_matches': 0,
            'cache_hits': 0
        }
        
        # Load static content on initialization
        self.load_static_content()
        
        logger.info("🎯 ContentManager initialized in ENHANCED STATIC-ONLY mode")
        logger.info("📝 AI usage: Multi-level understanding assistance (semantic + intent)")
        logger.info("🧠 Enhanced fuzzy matching and semantic search enabled")
        if self.intent_classifier and self.intent_classifier.is_trained:
            logger.info("🤖 Machine Learning Intent Classification enabled")
        elif self.intent_classifier:
            logger.info("🤖 Intent Classification available but not trained")
        else:
            logger.info("⚠️ Intent Classification not available")
        
    def load_static_content(self) -> bool:
        """Load static responses from JSON file and build inverted index"""
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
            
            # Build inverted index for optimized lookup
            self._build_inverted_index()
            
            logger.info(f"✅ Loaded {len(self.static_responses)} static responses")
            logger.info(f"🔍 Built inverted index: {len(self._keyword_index)} keywords, {len(self._phrase_index)} phrases")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load static content: {e}")
            return False

    def _build_inverted_index(self):
        """Build inverted index structure for fast keyword lookup"""
        self._keyword_index.clear()
        self._phrase_index.clear()
        
        for category, response_data in self.static_responses.items():
            if not isinstance(response_data, dict):
                continue
                
            keywords = response_data.get("keywords", [])
            
            for keyword in keywords:
                keyword_lower = keyword.lower().strip()
                
                # Index individual words
                words = keyword_lower.split()
                for word in words:
                    if word:  # Skip empty words
                        if word not in self._keyword_index:
                            self._keyword_index[word] = set()
                        self._keyword_index[word].add(category)
                
                # Index full phrases (for exact phrase matching)
                if keyword_lower:
                    if keyword_lower not in self._phrase_index:
                        self._phrase_index[keyword_lower] = set()
                    self._phrase_index[keyword_lower].add(category)
            
            # Also index category name for direct category matching
            category_lower = category.lower()
            if category_lower not in self._keyword_index:
                self._keyword_index[category_lower] = set()
            self._keyword_index[category_lower].add(category)
        
        self._index_built = True
        logger.debug(f"🔍 Inverted index built: {len(self._keyword_index)} keywords, {len(self._phrase_index)} phrases")

    def find_response(self, user_message: str) -> Tuple[str, str]:
        """
        Find appropriate response for user message - ENHANCED with Intent Classification
        Flow: Cache -> Intent Classifier -> Enhanced Turkish -> Enhanced Matching -> Direct Match -> AI Semantic -> Default
        Returns: (response_text, source)
        """
        if not user_message or not user_message.strip():
            return self._get_static_default_response(user_message), "default"
        
        self.stats['total_queries'] += 1
        user_message_lower = user_message.lower().strip()
        
        # Check cache first (for performance)
        if self._cache_enabled and user_message_lower in self._cache:
            cached_response, source = self._cache[user_message_lower]
            self.stats['cache_hits'] += 1
            logger.debug(f"🎯 Cache hit for: {user_message[:30]}...")
            return cached_response, f"cache_{source}"
        
        # ======= NEW: Intent Classification (PRIORITY) =======
        if self.intent_classifier and self.intent_classifier.is_trained:
            try:
                intent_prediction = self.intent_classifier.predict_intent(user_message)
                if intent_prediction:
                    # Intent classifier found a confident prediction
                    intent_category = intent_prediction.category
                    confidence = intent_prediction.confidence
                    
                    # Map intent to static response
                    static_response = self._get_response_by_category(intent_category)
                    if static_response:
                        self.stats['intent_matches'] += 1
                        logger.info(f"🎯 Intent match: '{user_message[:30]}...' -> {intent_category} "
                                   f"(confidence: {confidence:.3f})")
                        
                        # Cache the response
                        if self._cache_enabled:
                            self._cache[user_message_lower] = (static_response, f"intent_{intent_category}")
                        
                        return static_response, f"intent_{intent_category}"
                    else:
                        logger.debug(f"Intent {intent_category} matched but no static response found")
                        
            except Exception as e:
                logger.warning(f"Intent classification failed: {e}")
        
        # ======= Enhanced Turkish Content Manager (Fallback Level 1) =======
        if self.improved_turkish:
            try:
                turkish_match = self.improved_turkish.find_best_match(user_message)
                if turkish_match and turkish_match["score"] > 0.4:  # Higher threshold for quality
                    turkish_response = self.improved_turkish.get_response(user_message)
                    
                    # Check if it's a meaningful response (not fallback)
                    if turkish_response and not any(phrase in turkish_response.lower() for phrase in [
                        'elimde yeterli bilgi', 'bu konuda size', 'daha detaylandırır'
                    ]):
                        self.stats['turkish_enhanced_matches'] = self.stats.get('turkish_enhanced_matches', 0) + 1
                        logger.info(f"🇹🇷 Enhanced Turkish match: '{user_message[:30]}...' -> {turkish_match['category']} "
                                   f"(score: {turkish_match['score']:.3f})")
                        
                        # Cache the response
                        if self._cache_enabled:
                            self._cache[user_message_lower] = (turkish_response, "turkish_enhanced")
                        
                        return turkish_response, "turkish_enhanced"
                        
            except Exception as e:
                logger.warning(f"Enhanced Turkish matching failed: {e}")
        
        # ======= Enhanced Question Matching (Fallback Level 2) =======
        if self.enhanced_matcher:
            try:
                enhanced_match = self.enhanced_matcher.find_best_match(user_message)
                if enhanced_match:
                    # Enhanced match bulundu - static response'u al
                    static_response = self._get_response_by_category(enhanced_match.category)
                    if static_response:
                        self.stats['enhanced_matches'] += 1
                        logger.info(f"🧠 Enhanced match: '{user_message[:30]}...' -> {enhanced_match.category} "
                                   f"(confidence: {enhanced_match.confidence:.3f})")
                        
                        # Cache'e kaydet
                        if self._cache_enabled:
                            self._cache[user_message_lower] = (static_response, f"enhanced_{enhanced_match.match_type}")
                        
                        return static_response, f"enhanced_{enhanced_match.match_type}"
            except Exception as e:
                logger.warning(f"Enhanced matching failed: {e}")
        
        # Level 3: Direct keyword matching (fallback)
        response, source = self._find_static_response_direct(user_message_lower)
        if response:
            self.stats['exact_matches'] += 1
            logger.info(f"✅ Direct keyword match found for: {user_message[:30]}...")
            if self._cache_enabled:
                self._cache[user_message_lower] = (response, source)
            return response, source
        
        # Level 4: AI semantic similarity matching (fallback)
        if self._ai_enabled and self.model_manager:
            response, source = self._find_static_response_semantic(user_message, user_message_lower)
            if response:
                self.stats['semantic_matches'] += 1
                logger.info(f"🤖✅ AI semantic match found for: {user_message[:30]}...")
                if self._cache_enabled:
                    self._cache[user_message_lower] = (response, source)
                return response, source
        
        # Level 5: Intent-based matching (fallback)
        response, source = self._find_static_response_intent(user_message, user_message_lower)
        if response:
            self.stats['fuzzy_matches'] += 1
            logger.info(f"🎯 Intent-based match found for: {user_message[:30]}...")
            if self._cache_enabled:
                self._cache[user_message_lower] = (response, source)
            return response, source
        
        # No static response found - try Turkish fallback first
        if self.improved_turkish:
            try:
                turkish_fallback = self.improved_turkish.get_response(user_message)
                if turkish_fallback:
                    self.stats['turkish_fallback'] = self.stats.get('turkish_fallback', 0) + 1
                    logger.info(f"🇹🇷 Using Turkish fallback response")
                    if self._cache_enabled:
                        self._cache[user_message_lower] = (turkish_fallback, "turkish_fallback")
                    return turkish_fallback, "turkish_fallback"
            except Exception as e:
                logger.warning(f"Turkish fallback failed: {e}")
        
        # Final fallback - enhanced default
        self.stats['no_matches'] += 1
        default_response = self._get_enhanced_default_response(user_message)
        if self._cache_enabled:
            self._cache[user_message_lower] = (default_response, "default")
        
        logger.info(f"📝 No match found for: {user_message[:50]}... - returning enhanced default")
        return default_response, "default"
    
    def _get_response_by_category(self, category: str) -> Optional[str]:
        """Kategori adına göre static response'u al"""
        if category in self.static_responses:
            response_data = self.static_responses[category]
            if isinstance(response_data, dict):
                return response_data.get("message", "")
            elif isinstance(response_data, str):
                return response_data
        
        # Kategori bulunamadı
        logger.debug(f"Category not found in static responses: {category}")
        return None

    def _find_static_response_direct(self, user_message_lower: str) -> Tuple[Optional[str], str]:
        """
        Level 1: Direct keyword and phrase matching using inverted index
        Fast, exact matching for common queries with O(k) complexity instead of O(n*k)
        """
        if not self._index_built:
            logger.warning("Inverted index not built, falling back to linear search")
            return self._find_static_response_direct_fallback(user_message_lower)
        
        # Quick phrase matching first (exact matches)
        for phrase in self._phrase_index:
            if phrase in user_message_lower:
                categories = self._phrase_index[phrase]
                for category in categories:
                    response_data = self.static_responses.get(category)
                    if isinstance(response_data, dict):
                        response_text = response_data.get("message", "")
                        if response_text:
                            logger.debug(f"🎯 Direct phrase match: '{phrase}' -> {category}")
                            return response_text, "static_phrase"
        
        # Word-based matching with scoring
        user_words = set(user_message_lower.split())
        category_scores = {}
        
        for word in user_words:
            if word in self._keyword_index:
                categories = self._keyword_index[word]
                for category in categories:
                    if category not in category_scores:
                        category_scores[category] = 0
                    category_scores[category] += 1
        
        # Find best matching category
        if category_scores:
            # Sort by score, then by category priority
            best_category = max(category_scores.keys(), 
                              key=lambda cat: (category_scores[cat], 
                                             -self.categories.get(cat, {}).get("priority", 999)))
            
            # Calculate normalized score
            response_data = self.static_responses.get(best_category)
            if isinstance(response_data, dict):
                keywords = response_data.get("keywords", [])
                total_keyword_words = sum(len(kw.split()) for kw in keywords)
                
                if total_keyword_words > 0:
                    normalized_score = category_scores[best_category] / max(total_keyword_words, len(user_words))
                    
                    # Require minimum confidence for direct matches
                    if normalized_score > 0.3:  # Tuned threshold
                        response_text = response_data.get("message", "")
                        if response_text:
                            logger.debug(f"🎯 Direct keyword match: {best_category} "
                                       f"(score: {normalized_score:.3f}, words: {category_scores[best_category]})")
                            return response_text, "static_keyword"
        
        return None, ""
    
    def _find_static_response_direct_fallback(self, user_message_lower: str) -> Tuple[Optional[str], str]:
        """
        Fallback method for direct matching when inverted index is not available
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
            "enhanced_matcher_enabled": self.enhanced_matcher is not None,
            "intent_classifier_enabled": self.intent_classifier is not None,
            "intent_classifier_trained": self.intent_classifier.is_trained if self.intent_classifier else False,
            "huggingface_available": self.model_manager is not None,
            "system_mode": "enhanced_static_with_smart_matching_and_intent_classification",
            "ai_usage": "multi_level_understanding_plus_semantic_plus_intent",
            "inverted_index": {
                "enabled": self._index_built,
                "keywords": len(self._keyword_index),
                "phrases": len(self._phrase_index),
                "avg_categories_per_keyword": (sum(len(cats) for cats in self._keyword_index.values()) / len(self._keyword_index)) if self._keyword_index else 0
            },
            "matching_levels": {
                "level_0": "intent_classification_ml_model",  # NEW
                "level_1": "enhanced_turkish_content_matching",
                "level_2": "enhanced_question_matching_with_fuzzy_and_semantic",
                "level_3": "direct_keyword_matching_with_inverted_index",  # UPDATED
                "level_4": "ai_semantic_similarity", 
                "level_5": "intent_based_matching"
            },
            "query_stats": self.stats
        }
        
        # Success rate hesapla
        total_queries = self.stats['total_queries']
        if total_queries > 0:
            successful_matches = (
                self.stats['exact_matches'] + 
                self.stats['fuzzy_matches'] + 
                self.stats['semantic_matches'] + 
                self.stats['enhanced_matches'] +
                self.stats['intent_matches']  # NEW
            )
            
            stats["performance"] = {
                "total_queries": total_queries,
                "successful_matches": successful_matches,
                "success_rate": f"{(successful_matches / total_queries) * 100:.1f}%",
                "intent_match_rate": f"{(self.stats['intent_matches'] / total_queries) * 100:.1f}%",  # NEW
                "enhanced_match_rate": f"{(self.stats['enhanced_matches'] / total_queries) * 100:.1f}%",
                "cache_hit_rate": f"{(self.stats['cache_hits'] / total_queries) * 100:.1f}%"
            }
        
        # Add AI model stats if available (for understanding only)
        if self.model_manager:
            try:
                model_info = self.model_manager.get_model_info()
                stats["ai_model_info"] = {
                    "purpose": "enhanced_static_response_understanding_and_semantic_search",
                    "capabilities": ["semantic_similarity", "intent_detection", "context_analysis", "fuzzy_matching", "turkish_support"],
                    "turkish_model_loaded": model_info.get("turkish_sentence_model_loaded", False),
                    "device": model_info.get("device", "unknown"),
                    "cache_hits": model_info.get("cache_info", {}).get("embedding_cache_hits", 0),
                    "cache_size": model_info.get("cache_info", {}).get("embedding_cache_size", 0)
                }
            except Exception as e:
                logger.warning(f"Could not get AI model stats: {e}")
                stats["ai_model_info"] = {"error": str(e)}
        
        # Add Intent Classifier stats if available
        if self.intent_classifier:
            try:
                intent_info = self.intent_classifier.get_model_info()
                stats["intent_classifier_info"] = {
                    "purpose": "machine_learning_based_intent_classification",
                    "model_type": "tfidf_logistic_regression",
                    "is_trained": intent_info.get("is_trained", False),
                    "categories": intent_info.get("categories", []),
                    "num_categories": intent_info.get("num_categories", 0),
                    "confidence_threshold": intent_info.get("confidence_threshold", 0.3),
                    "vocabulary_size": intent_info.get("vocabulary_size", 0),
                    "sklearn_available": intent_info.get("sklearn_available", False)
                }
            except Exception as e:
                logger.warning(f"Could not get Intent Classifier stats: {e}")
                stats["intent_classifier_info"] = {"error": str(e)}
        
        return stats

    def clear_cache(self):
        """Clear response cache"""
        self._cache.clear()
        logger.info("🗑️ Response cache cleared")

    def reload_content(self):
        """Reload static content, rebuild inverted index and clear cache"""
        self.clear_cache()
        self.load_static_content()  # This will also rebuild the inverted index
        logger.info("🔄 Content reloaded and inverted index rebuilt")
    
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
        Test the enhanced multi-level matching system with intent classification
        """
        if test_queries is None:
            test_queries = [
                # Intent classification testleri
                "merhaba nasılsınız",               # Should match greetings via intent
                "selam arkadaş",                   # Should match greetings via intent
                "MEFAPEX ne yapıyor",              # Should match company_info via intent
                "şirketiniz hakkında bilgi",       # Should match company_info via intent
                "çalışma saatleri nelerdir",       # Should match working_hours via intent
                "kaçta açıyorsunuz",               # Should match working_hours via intent
                "yardıma ihtiyacım var",           # Should match support_types via intent
                "teknik destek nasıl alabilirim",  # Should match support_types via intent
                "hangi programlama dilleri",       # Should match technology_info via intent
                "yazılım geliştirme yapıyor musunuz", # Should match technology_info via intent
                "teşekkürler görüşürüz",           # Should match thanks_goodbye via intent
                "sağolun yardımınız için",         # Should match thanks_goodbye via intent
                
                # Fuzzy matching testleri (eğer intent başarısız olursa)
                "calisma saatleri nedir",          # Türkçe char yok
                "calışma saatleri",               # Karışık yazım
                "iş saatleri kaç",                # Eş anlamlı
                "saat kaçta açıksınız",           # Farklı kalıp
                "ne zaman açık",                  # Kısa soru
                "working hours",                  # İngilizce
                "mesai saatleri",                 # Eş anlamlı
                "ofis saatleri nedir",            # Workplace synonym
                
                # Edge cases
                "bugün hava nasıl",               # Should match default (low intent confidence)
                "futbol maçı ne zaman",           # Should match default (low intent confidence)
                "rastgele metin buraya",          # Should match default (low intent confidence)
            ]
        
        results = {}
        logger.info("🧪 Testing enhanced matching system with intent classification...")
        
        for query in test_queries:
            try:
                response, source = self.find_response(query)
                results[query] = {
                    "source": source,
                    "response_length": len(response),
                    "found_static": source != "default",
                    "intent_match": "intent_" in source,
                    "enhanced_match": "enhanced" in source,
                    "turkish_match": "turkish" in source
                }
                
                # Log results with detailed info
                if "intent_" in source:
                    logger.info(f"🎯✅ \"{query}\" -> {source} (Intent Classification)")
                elif "enhanced" in source:
                    logger.info(f"🧠✅ \"{query}\" -> {source} (Enhanced Match)")
                elif "turkish" in source:
                    logger.info(f"🇹🇷✅ \"{query}\" -> {source} (Turkish Enhanced)")
                elif source != "default":
                    logger.info(f"✅ \"{query}\" -> {source}")
                else:
                    logger.info(f"❌ \"{query}\" -> {source}")
                    
            except Exception as e:
                results[query] = {"error": str(e)}
                logger.error(f"❌ Test failed for '{query}': {e}")
        
        # Summary with detailed stats
        successful_matches = sum(1 for r in results.values() 
                               if isinstance(r, dict) and r.get("found_static", False))
        intent_matches = sum(1 for r in results.values() 
                           if isinstance(r, dict) and r.get("intent_match", False))
        enhanced_matches = sum(1 for r in results.values() 
                             if isinstance(r, dict) and r.get("enhanced_match", False))
        turkish_matches = sum(1 for r in results.values() 
                            if isinstance(r, dict) and r.get("turkish_match", False))
        
        summary = {
            "total_tests": len(test_queries),
            "successful_static_matches": successful_matches,
            "intent_matches": intent_matches,
            "enhanced_matches": enhanced_matches,
            "turkish_matches": turkish_matches,
            "default_responses": len(test_queries) - successful_matches,
            "success_rate": f"{(successful_matches/len(test_queries)*100):.1f}%",
            "intent_match_rate": f"{(intent_matches/len(test_queries)*100):.1f}%",
            "enhanced_match_rate": f"{(enhanced_matches/len(test_queries)*100):.1f}%",
            "turkish_match_rate": f"{(turkish_matches/len(test_queries)*100):.1f}%"
        }
        
        logger.info(f"📊 Test Summary: {successful_matches}/{len(test_queries)} static matches "
                   f"({summary['success_rate']} success rate)")
        logger.info(f"🎯 Intent matches: {intent_matches}/{len(test_queries)} "
                   f"({summary['intent_match_rate']} intent rate)")
        logger.info(f"🧠 Enhanced matches: {enhanced_matches}/{len(test_queries)} "
                   f"({summary['enhanced_match_rate']} enhanced rate)")
        logger.info(f"🇹🇷 Turkish matches: {turkish_matches}/{len(test_queries)} "
                   f"({summary['turkish_match_rate']} turkish rate)")
        
        return {
            "results": results,
            "summary": summary,
            "system_stats": self.get_stats()
        }

# Global instance
content_manager = ContentManager()
