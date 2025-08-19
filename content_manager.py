"""
Enhanced Content Manager for MEFAPEX Chatbot
Handles static responses from JSON files + Hugging Face AI integration + Hybrid Relevance Detection
"""

import json
import os
import logging
import asyncio
from typing import Dict, List, Optional, Tuple

# Import hybrid relevance detector
try:
    from hybrid_relevance_detector import HybridRelevanceDetector, RelevanceLevel
    RELEVANCE_DETECTOR_AVAILABLE = True
except ImportError as e:
    RELEVANCE_DETECTOR_AVAILABLE = False
    HybridRelevanceDetector = None
    RelevanceLevel = None

logger = logging.getLogger(__name__)

class ContentManager:
    """
    Enhanced content management system:
    - Static responses from JSON files (primary)
    - Hugging Face AI integration (secondary)
    - Hybrid relevance detection for off-topic questions
    - Intelligent keyword matching
    - Response caching for performance
    """
    
    def __init__(self, content_dir: str = "content"):
        self.content_dir = content_dir
        self.static_responses = {}
        self.categories = {}
        self.settings = {}
        self._cache = {}
        self._cache_enabled = True
        self._ai_enabled = True
        self._relevance_detection_enabled = True
        
        # Initialize hybrid relevance detector
        if RELEVANCE_DETECTOR_AVAILABLE:
            try:
                self.relevance_detector = HybridRelevanceDetector("MEFAPEX Bilişim Teknolojileri")
                logger.info("✅ Hybrid relevance detection enabled")
            except Exception as e:
                self.relevance_detector = None
                self._relevance_detection_enabled = False
                logger.warning(f"⚠️ Relevance detector initialization failed: {e}")
        else:
            self.relevance_detector = None
            self._relevance_detection_enabled = False
            logger.warning("⚠️ Hybrid relevance detector not available")
        
        # Import model manager for AI responses
        try:
            from model_manager import model_manager
            self.model_manager = model_manager
            logger.info("✅ Hugging Face AI integration enabled")
        except ImportError as e:
            self.model_manager = None
            self._ai_enabled = False
            logger.warning(f"⚠️ Hugging Face AI not available: {e}")
        
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
        Find appropriate response for user message with relevance detection
        Flow: Relevance Check -> Static -> Hugging Face AI -> Default
        Returns: (response_text, source)
        Source can be: irrelevant, static, cache_static, huggingface, cache_huggingface, default
        """
        if not user_message or not user_message.strip():
            return self._get_default_response(user_message), "default"
        
        user_message_lower = user_message.lower().strip()
        
        # Check cache first (for performance)
        if self._cache_enabled and user_message_lower in self._cache:
            cached_response, source = self._cache[user_message_lower]
            logger.debug(f"🎯 Cache hit for: {user_message[:30]}...")
            return cached_response, f"cache_{source}"
        
        # Check relevance using hybrid detector (if enabled)
        if self._relevance_detection_enabled and self.relevance_detector:
            try:
                # Check if we're already in an event loop
                try:
                    loop = asyncio.get_running_loop()
                    # We're in an event loop, create a task
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(self._run_relevance_check, user_message)
                        relevance_result = future.result(timeout=2.0)  # 2 second timeout
                except RuntimeError:
                    # No event loop running, we can use asyncio.run
                    relevance_result = asyncio.run(self._check_relevance_async(user_message))
                
                # If question is clearly irrelevant, return smart response immediately
                if (relevance_result and not relevance_result.is_relevant and 
                    relevance_result.confidence > 0.7 and
                    relevance_result.response_suggestion):
                    
                    logger.info(f"🚫 Irrelevant question detected ({relevance_result.confidence:.3f}): {user_message[:50]}...")
                    logger.info(f"📊 Method: {relevance_result.method.value}, Level: {relevance_result.relevance_level.value}")
                    
                    # Cache the irrelevant response
                    if self._cache_enabled:
                        self._cache[user_message_lower] = (relevance_result.response_suggestion, "irrelevant")
                    
                    return relevance_result.response_suggestion, "irrelevant"
                
                # Log relevance analysis for debugging
                if relevance_result:
                    logger.debug(f"🎯 Relevance: {relevance_result.is_relevant} "
                               f"({relevance_result.confidence:.3f}) - {relevance_result.method.value}")
                
            except Exception as e:
                logger.error(f"❌ Relevance detection failed: {e}")
                # Continue with normal processing
        
        # Try static responses first (highest priority)
        response, source = self._find_static_response(user_message_lower)
        
        if response:
            # Cache the response
            if self._cache_enabled:
                self._cache[user_message_lower] = (response, source)
            return response, source
        
        # Try Hugging Face AI if static response not found
        # AI with strict quality control enabled
        ai_enabled_for_testing = True  # Set to False to disable AI
        
        if self._ai_enabled and self.model_manager and ai_enabled_for_testing:
            try:
                ai_response = self._generate_ai_response(user_message)
                if ai_response and ai_response.strip() and len(ai_response.strip()) > 15:
                    logger.info(f"🤖 AI response generated for: {user_message[:30]}...")
                    # Cache the AI response
                    if self._cache_enabled:
                        self._cache[user_message_lower] = (ai_response, "huggingface")
                    return ai_response, "huggingface"
                else:
                    logger.debug(f"🤖 AI response quality insufficient, using fallback for: {user_message[:30]}...")
            except Exception as e:
                logger.error(f"❌ AI response generation failed: {e}")
        
        # Return intelligent default response as fallback
        intelligent_response = self._get_intelligent_default_response(user_message)
        if self._cache_enabled:
            self._cache[user_message_lower] = (intelligent_response, "intelligent_default")
        
        return intelligent_response, "intelligent_default"
    
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

    def _find_static_response(self, user_message_lower: str) -> Tuple[Optional[str], str]:
        """Find matching static response"""
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

    def _generate_ai_response(self, user_message: str) -> Optional[str]:
        """
        Generate AI response using Hugging Face models with improved quality control
        """
        try:
            if not self.model_manager:
                return None
            
            # Limit message length for processing
            message = user_message.strip()[:200]
            
            # Create a better prompt for Turkish context
            enhanced_prompt = self._create_enhanced_prompt(message)
            
            # Generate response using Turkish-optimized models
            ai_response = self.model_manager.generate_text_response(
                prompt=enhanced_prompt,
                max_length=120,  # Slightly longer for better context
                turkish_context=True
            )
            
            if ai_response and len(ai_response.strip()) > 10:
                # Clean and validate the response
                cleaned_response = self._clean_and_validate_ai_response(ai_response, user_message)
                if cleaned_response:
                    return cleaned_response
            
            # If AI response is poor quality, return None to trigger fallback
            return None
            
        except Exception as e:
            logger.error(f"AI response generation error: {e}")
            return None
    
    def _create_enhanced_prompt(self, user_message: str) -> str:
        """
        Create an enhanced prompt for better AI responses
        """
        # Detect question type and create appropriate context
        if any(word in user_message.lower() for word in ['hava', 'weather', 'meteoroloji']):
            return f"MEFAPEX müşteri destek asistanı olarak hava durumu sorusuna kısa ve profesyonel yanıt ver: {user_message}"
        
        elif any(word in user_message.lower() for word in ['nasıl', 'nedir', 'ne', 'kim', 'nerede', 'ne zaman']):
            return f"MEFAPEX teknoloji firması destek uzmanı olarak bu soruya yardımcı ve bilgilendirici yanıt ver: {user_message}"
        
        elif any(word in user_message.lower() for word in ['öğren', 'program', 'kod', 'yazılım', 'teknoloji']):
            return f"MEFAPEX teknoloji uzmanı olarak yazılım/teknoloji konusundaki bu soruya rehberlik et: {user_message}"
        
        else:
            return f"MEFAPEX müşteri hizmetleri asistanı olarak bu konuda yardımcı ol: {user_message}"
    
    def _clean_and_validate_ai_response(self, ai_response: str, original_message: str) -> Optional[str]:
        """
        Clean, validate and improve AI response quality
        """
        try:
            # Remove the original prompt if it appears in response
            response = ai_response.strip()
            
            # Remove common prompt artifacts
            prompt_artifacts = [
                "MEFAPEX müşteri destek asistanı olarak",
                "MEFAPEX teknoloji firması destek uzmanı olarak", 
                "MEFAPEX teknoloji uzmanı olarak",
                "MEFAPEX müşteri hizmetleri asistanı olarak",
                "olarak bu soruya", "olarak hava durumu", "olarak yazılım",
                "yanıt ver:", "yardımcı ol:", "rehberlik et:"
            ]
            
            for artifact in prompt_artifacts:
                if artifact in response:
                    response = response.replace(artifact, "").strip()
            
            # Remove the original message if it appears at the start
            if original_message.lower() in response.lower()[:50]:
                idx = response.lower().find(original_message.lower())
                if idx >= 0:
                    response = response[idx + len(original_message):].strip()
            
            # Clean up common prefixes
            prefixes_to_remove = [
                "türkçe:", "turkish:", "cevap:", "response:", "yanıt:", "answer:",
                "soru:", "question:", "merhaba", "selam", ":"
            ]
            
            for prefix in prefixes_to_remove:
                if response.lower().startswith(prefix):
                    response = response[len(prefix):].strip()
            
            # Quality checks
            if len(response) < 15:
                logger.debug("AI response too short, rejecting")
                return None
            
            # Check for repetitive patterns (sign of poor generation)
            words = response.split()
            if len(words) > 3:
                if len(set(words[:5])) <= 2:  # Too repetitive
                    logger.debug("AI response too repetitive, rejecting")
                    return None
            
            # Check for training data artifacts more strictly
            if any(artifact in response.lower() for artifact in [
                'fiyat', 'güncellendi', 'web site', 'aracılığıyla', 'sunulmaktadır',
                'cumhuriyet gazetesi', 'yazarı', 'köşe yazısı', 'hutbe',
                'domuz eti', 'imam', 'vaaz', 'cuma namazı', 'anasayfa',
                'müşteri temsilcisi', '0850', 'numaralı', 'şikayetiniz',
                'en çok sorulan', 'sıcaklığı kaç', 'derece', 'telefon',
                'ulaşabilirsiniz', 'aklınıza takılan'
            ]):
                logger.debug("AI response contains training artifacts, rejecting")
                return None
            
            # Check for nonsensical patterns
            nonsense_patterns = [
                "###", "***", "===", "---", "///",
                "çok çok çok", "ve ve ve", "bir bir bir",
                "gibi gibi", "için için", "ile ile ile"
            ]
            
            if any(pattern in response.lower() for pattern in nonsense_patterns):
                logger.debug("AI response contains nonsense patterns, rejecting")
                return None
            
            # Check if response seems relevant to the question
            if not self._is_response_relevant(original_message, response):
                logger.debug("AI response not relevant to question, rejecting")
                return None
            
            # Additional quality checks for Turkish responses
            if not self._passes_quality_checks(response):
                logger.debug("AI response failed quality checks, rejecting")
                return None
            
            # Format the response with MEFAPEX branding if appropriate
            if len(response) > 20 and not any(brand in response.lower() for brand in ['mefapex', 'destek', 'yardım']):
                formatted_response = f"🤖 **MEFAPEX AI Asistanı:**\n\n{response}\n\n💡 Daha detaylı bilgi için destek ekibimizle iletişime geçebilirsiniz."
                return formatted_response
            
            return response
            
        except Exception as e:
            logger.error(f"Response cleaning error: {e}")
            return None
    
    def _passes_quality_checks(self, response: str) -> bool:
        """
        Additional quality checks for AI responses
        """
        try:
            # Check for common signs of poor quality
            lower_response = response.lower()
            
            # Check for incomplete sentences (no proper ending)
            if not response.strip().endswith(('.', '!', '?', ':', '🚀', '💡', '🌟', '✨')):
                return False
            
            # Check for training artifacts more thoroughly
            training_artifacts = [
                'mefapex müşteri destek asistanı',
                'mefapex müşteri hizmet',
                'fiyatlar güncellendi',
                'müşteri hizmetlerine bağlan',
                'mefepro',
                'sana yardım etmek için',
                'bir sonraki',
                'şimdi bu',
                'diyebilirsin',
                'gerekli malzeme',
                'tamam, şimdi',
                'hazır olduğunu bilmen',
                'yemek tarifi ver',
                'bahsettiklerinde',
                'aradığında',
                'pişirmek için',
                'alacağım'
            ]
            
            for artifact in training_artifacts:
                if artifact in lower_response:
                    return False
            
            # Check for broken sentences that start oddly
            bad_starts = [
                'yemek tarifi ver',
                'müşteri hizmet',
                'fiyatlar güncellendi',
                'tamam, şimdi',
                'sana yardım',
                'bir sonraki',
                'gerekli malzeme',
                'pişirmek için'
            ]
            
            for bad_start in bad_starts:
                if lower_response.strip().startswith(bad_start):
                    return False
            
            # Check for repetitive company name mentions (sign of confusion)
            mefapex_count = lower_response.count('mefapex') + lower_response.count('mefopex') + lower_response.count('mefpex')
            if mefapex_count > 2:
                return False
            
            # Check for incomplete or fragmented sentences
            if response.count('...') > 2:
                return False
            
            # Check for HTML/URL fragments (sign of training data leakage)
            if any(fragment in lower_response for fragment in ['http', 'www', 'href', 'html', '.com']):
                return False
            
            # Check for excessive punctuation (sign of poor generation)
            punctuation_ratio = sum(1 for c in response if c in '.,!?;:') / max(len(response), 1)
            if punctuation_ratio > 0.15:
                return False
            
            # Check for date/time stamps (sign of training data)
            if any(fragment in response for fragment in ['2021', '2022', '2023', '2024', '2020', '2019']):
                return False
            
            # Check for meta-language about AI/chatbots
            if any(word in lower_response for word in ['ai', 'bot', 'asistan olarak', 'model olarak']):
                return False
            
            # Check for repeated words in sequence
            words = response.split()
            if len(words) >= 3:
                for i in range(len(words) - 2):
                    if words[i] == words[i+1] == words[i+2]:  # 3 consecutive identical words
                        return False
                        
            return True
            
        except Exception:
            return False
    
    def _is_response_relevant(self, question: str, response: str) -> bool:
        """
        Check if AI response is relevant to the original question
        """
        try:
            question_words = set(question.lower().split())
            response_words = set(response.lower().split())
            
            # Remove common stop words
            stop_words = {
                'bir', 'bu', 'şu', 've', 'ile', 'için', 'den', 'dan', 'dır', 'dir',
                'mı', 'mi', 'mu', 'mü', 'da', 'de', 'ta', 'te', 'ya', 'ye',
                'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with'
            }
            
            question_words -= stop_words
            response_words -= stop_words
            
            if not question_words:
                return True  # Can't determine, allow it
            
            # Check for word overlap
            overlap = len(question_words.intersection(response_words))
            overlap_ratio = overlap / len(question_words)
            
            # Require at least 10% word overlap for relevance
            return overlap_ratio >= 0.1
            
        except Exception:
            return True  # If can't determine, allow it

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

    def _get_intelligent_default_response(self, user_message: str = "") -> str:
        """
        Get contextual default response based on message content
        """
        if not user_message:
            return "Merhaba! Size nasıl yardımcı olabilirim?"
        
        message_lower = user_message.lower()
        
        # Context-aware responses based on message content
        if any(word in message_lower for word in ['hava', 'weather', 'sıcaklık', 'yağmur', 'kar', 'güneş']):
            return "🌤️ **Hava Durumu Sorgusu**\n\nÜzgünüm, gerçek zamanlı hava durumu bilgisine erişimim yok. En güncel hava durumu için:\n\n• Meteoroloji Genel Müdürlüğü (mgm.gov.tr)\n• Hava durumu uygulamaları\n• Yerel haber kanalları\n\nkaynaklarını kullanabilirsiniz."
        
        elif any(word in message_lower for word in ['nasıl', 'öğren', 'öğret', 'anlat', 'bilgi', 'nedir']):
            return "🤔 **Bilgi Talebi**\n\nSorduğunuz konu hakkında detaylı bilgi verebilmem için sorunuzu biraz daha spesifik hale getirebilir misiniz?\n\n**Yardımcı olabileceğim konular:**\n• MEFAPEX hizmetleri\n• Teknik destek\n• Yazılım geliştirme\n• Sistem entegrasyonu\n\n💬 Hangi konuda yardıma ihtiyacınız var?"
        
        elif any(word in message_lower for word in ['program', 'kod', 'yazılım', 'teknoloji', 'development']):
            return "💻 **Yazılım & Teknoloji**\n\nMEFAPEX olarak yazılım geliştirme ve teknoloji konularında size yardımcı olabilirim.\n\n**Hizmetlerimiz:**\n• Özel yazılım geliştirme\n• Web uygulamaları\n• Mobil uygulamalar\n• Sistem entegrasyonu\n• Teknoloji danışmanlığı\n\n🔧 Hangi teknoloji konusunda destek almak istiyorsunuz?"
        
        elif any(word in message_lower for word in ['problem', 'sorun', 'hata', 'çalışmıyor', 'bozuk']):
            return "🛠️ **Teknik Destek**\n\nTeknik bir sorunla karşılaştığınızı anlıyorum. Size en iyi şekilde yardımcı olabilmem için:\n\n**Lütfen belirtin:**\n• Hangi sistem/uygulama ile ilgili\n• Sorunun detayları\n• Ne zaman başladı\n• Hata mesajları (varsa)\n\n📞 Acil durumlar için: **destek@mefapex.com**"
        
        elif any(word in message_lower for word in ['teşekkür', 'sağol', 'thanks']):
            return "😊 **Rica Ederim!**\n\nSize yardımcı olabildiysem çok mutluyum. Başka sorularınız olduğunda her zaman buradayım.\n\n🌟 İyi çalışmalar dilerim!"
        
        else:
            # Generic but helpful response
            responses = [
                "🤝 **MEFAPEX Destek**\n\nSorduğunuz konu hakkında size daha iyi yardımcı olabilmem için biraz daha detay verebilir misiniz?\n\n**Popüler konular:**\n• Teknik destek\n• Yazılım geliştirme\n• Sistem entegrasyonu\n• Proje danışmanlığı",
                
                "💬 **Size Nasıl Yardımcı Olabilirim?**\n\nMEFAPEX ekibi olarak size destek olmaktan mutluluk duyarız.\n\n**Hizmet alanlarımız:**\n• Bilişim teknolojileri\n• Yazılım çözümleri\n• Teknik danışmanlık\n\n📝 Sorunuzu daha spesifik olarak sorabilir misiniz?",
                
                "🔍 **Daha Fazla Bilgi**\n\nBu konuda size yardımcı olmak istiyorum ancak sorunuzu tam olarak anlayamadım.\n\n**Deneyebilirsiniz:**\n• Sorunuzu farklı kelimelerle ifade edin\n• Daha spesifik bilgi verin\n• Hangi alanda yardım istediğinizi belirtin\n\n💡 Ben buradayım!"
            ]
            
            # Select response based on message hash for consistency
            import hashlib
            hash_value = int(hashlib.md5(user_message.encode()).hexdigest()[:8], 16)
            return responses[hash_value % len(responses)]

    def _get_default_response(self, user_message: str = "") -> str:
        """Get simple default response (legacy method)"""
        return self._get_intelligent_default_response(user_message)

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
            "relevance_detection_enabled": self._relevance_detection_enabled,
            "relevance_detector_available": RELEVANCE_DETECTOR_AVAILABLE
        }
        
        # Add relevance detection stats
        if self._relevance_detection_enabled and self.relevance_detector:
            stats["relevance_detection"] = {
                "enabled": True,
                "company_name": self.relevance_detector.company_name,
                "domain_categories": len(self.relevance_detector.domain_categories),
                "quick_filter_keywords": {
                    "relevant": len(self.relevance_detector.quick_filters["definitely_relevant"]),
                    "irrelevant": len(self.relevance_detector.quick_filters["definitely_irrelevant"])
                }
            }
        else:
            stats["relevance_detection"] = {"enabled": False}
        
        # Add AI model stats if available
        if self.model_manager:
            try:
                model_info = self.model_manager.get_model_info()
                stats["ai_model_info"] = {
                    "turkish_model_loaded": model_info.get("turkish_sentence_model_loaded", False),
                    "text_generator_loaded": model_info.get("text_generator_loaded", False),
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
        Async version of find_response for better performance with AI models
        """
        return self.find_response(user_message)
    
    def warmup_ai_models(self):
        """
        Warm up AI models for better response times
        """
        if self._ai_enabled and self.model_manager:
            try:
                logger.info("🔥 Warming up AI models...")
                self.model_manager.warmup_models()
                logger.info("✅ AI models warmed up successfully")
            except Exception as e:
                logger.error(f"❌ AI warmup failed: {e}")
        else:
            logger.info("ℹ️ AI models not available for warmup")
    
    def enable_ai(self, enabled: bool = True):
        """
        Enable or disable AI responses
        """
        if enabled and not self.model_manager:
            logger.warning("⚠️ Cannot enable AI: model_manager not available")
            return False
        
        self._ai_enabled = enabled
        status = "enabled" if enabled else "disabled"
        logger.info(f"🤖 AI responses {status}")
        return True
    
    def enable_relevance_detection(self, enabled: bool = True):
        """
        Enable or disable relevance detection
        """
        if enabled and not self.relevance_detector:
            logger.warning("⚠️ Cannot enable relevance detection: detector not available")
            return False
        
        self._relevance_detection_enabled = enabled
        status = "enabled" if enabled else "disabled"
        logger.info(f"🎯 Relevance detection {status}")
        return True
    
    async def test_relevance_detection(self, test_messages: List[str] = None):
        """
        Test relevance detection with sample messages
        """
        if not self._relevance_detection_enabled or not self.relevance_detector:
            logger.warning("⚠️ Relevance detection not available for testing")
            return {}
        
        if test_messages is None:
            test_messages = [
                "MEFAPEX fabrikasında çalışma saatleri nedir?",  # Relevant
                "En iyi pizza tarifi nedir?",                    # Irrelevant
                "Yazılım geliştirme hizmetleri",                 # Relevant
                "Hangi film izlemeliyim?",                       # Irrelevant
                "Teknik destek nasıl alabilirim?",               # Relevant
                "Bugün hava nasıl?",                             # Irrelevant
            ]
        
        results = {}
        total_time = 0
        
        logger.info("🧪 Testing relevance detection...")
        
        for message in test_messages:
            try:
                result = await self.relevance_detector.classify(message)
                
                results[message] = {
                    "is_relevant": result.is_relevant,
                    "confidence": result.confidence,
                    "level": result.relevance_level.value,
                    "method": result.method.value,
                    "processing_time_ms": result.processing_time_ms,
                    "reasoning": result.reasoning,
                    "has_suggestion": result.response_suggestion is not None
                }
                
                total_time += result.processing_time_ms
                
                # Log result
                relevance_emoji = "✅" if result.is_relevant else "❌"
                logger.info(f"{relevance_emoji} {message[:40]}... -> "
                          f"{result.confidence:.3f} ({result.processing_time_ms:.1f}ms)")
                
            except Exception as e:
                logger.error(f"❌ Test failed for '{message}': {e}")
                results[message] = {"error": str(e)}
        
        # Summary
        avg_time = total_time / len(test_messages) if test_messages else 0
        relevant_count = sum(1 for r in results.values() 
                           if isinstance(r, dict) and r.get("is_relevant", False))
        
        summary = {
            "total_tests": len(test_messages),
            "relevant_detected": relevant_count,
            "irrelevant_detected": len(test_messages) - relevant_count,
            "average_processing_time_ms": avg_time,
            "total_processing_time_ms": total_time
        }
        
        logger.info(f"📊 Test Summary: {relevant_count}/{len(test_messages)} relevant, "
                   f"avg time: {avg_time:.1f}ms")
        
        return {
            "results": results,
            "summary": summary
        }

# Global instance
content_manager = ContentManager()
