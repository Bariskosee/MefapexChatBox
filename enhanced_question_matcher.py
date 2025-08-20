"""
🧠 Memory-Optimized Türkçe Soru Anlama ve Eşleştirme Sistemi
================================================================
Fixed memory leak issues with optimized caching and resource management

⚠️ CRITICAL MEMORY LEAK FIXES:
- Reduced LRU cache size from 1000 to 50 (96% reduction)
- Added automatic cache cleanup
- Implemented memory-safe similarity calculations
- Added garbage collection triggers
- Optimized text processing algorithms
"""

import re
import hashlib
import logging
import unicodedata
import gc
import weakref
import time
import json
import os
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
from functools import lru_cache, wraps
from difflib import SequenceMatcher
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class QuestionMatch:
    """Soru eşleştirme sonucu"""
    original_question: str
    matched_content: str
    similarity_score: float
    matching_keywords: List[str]
    match_type: str  # fuzzy, semantic, keyword, exact
    confidence: float
    response: str
    category: str

class MemorySafeCache:
    """Memory-safe caching with automatic cleanup"""
    
    def __init__(self, maxsize: int = 50, cleanup_interval: int = 100):
        self.maxsize = maxsize
        self.cleanup_interval = cleanup_interval
        self.cache = {}
        self.access_times = {}
        self.access_count = 0
        
    def get(self, key: str):
        """Get item from cache"""
        if key in self.cache:
            self.access_times[key] = time.time()
            return self.cache[key]
        return None
    
    def set(self, key: str, value):
        """Set item in cache with automatic cleanup"""
        # Trigger cleanup if needed
        self.access_count += 1
        if self.access_count % self.cleanup_interval == 0:
            self._cleanup()
        
        # Add to cache
        self.cache[key] = value
        self.access_times[key] = time.time()
        
        # Limit cache size
        if len(self.cache) > self.maxsize:
            self._evict_oldest()
    
    def _cleanup(self):
        """Cleanup old cache entries"""
        try:
            current_time = time.time()
            old_keys = [
                key for key, access_time in self.access_times.items()
                if current_time - access_time > 300  # 5 minutes
            ]
            
            for key in old_keys:
                self.cache.pop(key, None)
                self.access_times.pop(key, None)
            
            if old_keys:
                logger.debug(f"🧹 Cleaned {len(old_keys)} old cache entries")
                gc.collect()  # Force garbage collection
                
        except Exception as e:
            logger.warning(f"Cache cleanup failed: {e}")
    
    def _evict_oldest(self):
        """Evict oldest cache entry"""
        if not self.access_times:
            return
            
        oldest_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
        self.cache.pop(oldest_key, None)
        self.access_times.pop(oldest_key, None)
    
    def clear(self):
        """Clear all cache"""
        self.cache.clear()
        self.access_times.clear()
        gc.collect()
    
    def info(self):
        """Get cache info"""
        return {
            'size': len(self.cache),
            'maxsize': self.maxsize,
            'hits': 0,  # Would need to track hits/misses
            'misses': 0
        }

def memory_optimized_cache(maxsize: int = 50):
    """Memory-optimized cache decorator with automatic cleanup"""
    def decorator(func):
        cache = MemorySafeCache(maxsize=maxsize)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key
            key = str(hash((args, frozenset(kwargs.items()) if kwargs else frozenset())))
            
            # Try cache first
            result = cache.get(key)
            if result is not None:
                return result
            
            # Compute and cache
            result = func(*args, **kwargs)
            cache.set(key, result)
            
            return result
        
        wrapper.cache_info = cache.info
        wrapper.cache_clear = cache.clear
        return wrapper
    return decorator

class TurkishTextNormalizer:
    """Türkçe metin normalizasyonu ve temizleme - Memory Optimized"""
    
    # Türkçe karakter dönüşümleri
    TURKISH_CHAR_MAP = {
        'ç': 'c', 'ğ': 'g', 'ı': 'i', 'ö': 'o', 'ş': 's', 'ü': 'u',
        'Ç': 'C', 'Ğ': 'G', 'I': 'I', 'İ': 'I', 'Ö': 'O', 'Ş': 'S', 'Ü': 'U'
    }
    
    # Fallback eş anlamlı kelimeler (JSON yüklenemezse kullanılır)
    FALLBACK_SYNONYMS = {
        'çalışma': ['iş', 'mesai', 'görev'],
        'saat': ['zaman', 'vakit', 'time'],
        'açık': ['open', 'başlama'],
        'kapalı': ['closed', 'bitiş'],
        'nedir': ['ne', 'what'],
        'güvenlik': ['emniyet', 'security'],
        'destek': ['yardım', 'help'],
        'mefapex': ['şirket', 'company'],
        'bilgi': ['information', 'detay'],
        'kaçta': ['ne zaman', 'when']
    }
    
    # Class-level cache for loaded synonyms
    _synonyms = None
    _synonyms_file_path = None
    
    @classmethod
    def load_synonyms(cls) -> Dict[str, List[str]]:
        """JSON dosyasından eş anlamlıları yükle"""
        if cls._synonyms is not None:
            return cls._synonyms
        
        try:
            # Synonyms dosyasının yolunu belirle
            current_dir = os.path.dirname(os.path.abspath(__file__))
            synonyms_path = os.path.join(current_dir, 'content', 'synonyms.json')
            
            # Alternative path if not found
            if not os.path.exists(synonyms_path):
                synonyms_path = os.path.join(current_dir, '..', 'content', 'synonyms.json')
            
            # Alternative path for direct access
            if not os.path.exists(synonyms_path):
                synonyms_path = os.path.join('content', 'synonyms.json')
            
            cls._synonyms_file_path = synonyms_path
            
            if os.path.exists(synonyms_path):
                with open(synonyms_path, 'r', encoding='utf-8') as f:
                    cls._synonyms = json.load(f)
                    logger.info(f"✅ Eş anlamlılar başarıyla yüklendi: {len(cls._synonyms)} kelime")
            else:
                logger.warning(f"⚠️ Synonyms dosyası bulunamadı: {synonyms_path}")
                cls._synonyms = cls.FALLBACK_SYNONYMS.copy()
                
        except Exception as e:
            logger.error(f"❌ Synonyms yükleme hatası: {e}")
            cls._synonyms = cls.FALLBACK_SYNONYMS.copy()
        
        return cls._synonyms
    
    @classmethod
    def reload_synonyms(cls):
        """Eş anlamlıları yeniden yükle"""
        cls._synonyms = None
        return cls.load_synonyms()
    
    @classmethod
    def get_synonyms_info(cls) -> Dict[str, any]:
        """Eş anlamlılar hakkında bilgi döndür"""
        synonyms = cls.load_synonyms()
        return {
            'total_words': len(synonyms),
            'total_synonyms': sum(len(syns) for syns in synonyms.values()),
            'file_path': cls._synonyms_file_path,
            'using_fallback': synonyms == cls.FALLBACK_SYNONYMS
        }
    
    # Legacy property for backward compatibility
    @property
    def SYNONYMS(self):
        return self.load_synonyms()
    
    @classmethod
    @memory_optimized_cache(maxsize=100)  # Reduced from unlimited
    def normalize_text(cls, text: str) -> str:
        """Memory-optimized text normalization"""
        if not text:
            return ""
        
        # Limit text length to prevent memory bloat
        text = text[:500]  # Max 500 characters
        
        # Unicode normalize
        text = unicodedata.normalize('NFKD', text)
        
        # Küçük harfe çevir
        text = text.lower()
        
        # Ekstra boşlukları temizle
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Noktalama işaretlerini temizle (sadece gerekli olanları)
        text = re.sub(r'[^\w\sğüşıöçĞÜŞIİÖÇ]', '', text)
        
        return text
    
    @classmethod
    @memory_optimized_cache(maxsize=50)  # Reduced cache
    def remove_diacritics(cls, text: str) -> str:
        """Türkçe karakterleri ASCII'ye çevir - Memory optimized"""
        if not text:
            return ""
        
        result = ""
        for char in text[:500]:  # Limit length
            result += cls.TURKISH_CHAR_MAP.get(char, char)
        
        return result
    
    @classmethod
    def expand_synonyms(cls, text: str) -> Set[str]:
        """Eş anlamlı kelimeleri genişlet - Memory optimized"""
        synonyms = cls.load_synonyms()
        
        # Hem orijinal hem de normalleştirilmiş kelimeleri kullan
        original_words = text.split()[:20]  # Limit to 20 words max
        normalized_text = cls.normalize_text(text)
        normalized_words = normalized_text.split()[:20]
        
        # Her iki forma da dahil et
        expanded = set(original_words + normalized_words)
        
        # Orijinal kelimeler için eş anlamlı ara
        for word in original_words:
            word_lower = word.lower()
            if word_lower in synonyms:
                expanded.update(synonyms[word_lower][:5])
        
        # Normalleştirilmiş kelimeler için eş anlamlı ara
        for word in normalized_words:
            if word in synonyms:
                expanded.update(synonyms[word][:5])
        
        return expanded

class FuzzyMatcher:
    """Optimized fuzzy string matching"""
    
    @staticmethod
    @memory_optimized_cache(maxsize=200)  # Reduced cache
    def similarity_ratio(s1: str, s2: str) -> float:
        """Basic similarity ratio - Memory optimized"""
        if not s1 or not s2:
            return 0.0
        
        # Limit string length
        s1, s2 = s1[:200], s2[:200]
        
        return SequenceMatcher(None, s1, s2).ratio()
    
    @staticmethod
    @memory_optimized_cache(maxsize=100)  # Reduced cache
    def partial_ratio(s1: str, s2: str) -> float:
        """Partial string matching - Memory optimized"""
        if not s1 or not s2:
            return 0.0
        
        # Limit string length
        s1, s2 = s1[:200], s2[:200]
        
        # Find best partial match
        shorter, longer = (s1, s2) if len(s1) <= len(s2) else (s2, s1)
        
        best_ratio = 0.0
        for i in range(len(longer) - len(shorter) + 1):
            ratio = SequenceMatcher(None, shorter, longer[i:i+len(shorter)]).ratio()
            best_ratio = max(best_ratio, ratio)
        
        return best_ratio
    
    @staticmethod
    @memory_optimized_cache(maxsize=100)  # Reduced cache
    def token_set_ratio(s1: str, s2: str) -> float:
        """Token set matching - Memory optimized"""
        if not s1 or not s2:
            return 0.0
        
        # Limit and tokenize
        tokens1 = set(s1[:200].split()[:10])  # Max 10 tokens
        tokens2 = set(s2[:200].split()[:10])  # Max 10 tokens
        
        if not tokens1 or not tokens2:
            return 0.0
        
        intersection = tokens1 & tokens2
        union = tokens1 | tokens2
        
        return len(intersection) / len(union) if union else 0.0

class MemoryOptimizedEnhancedQuestionMatcher:
    """
    🚀 Memory-Optimized Enhanced Question Matcher
    =============================================
    
    CRITICAL MEMORY LEAK FIXES:
    - Reduced all cache sizes by 95%
    - Added automatic cache cleanup
    - Limited text processing lengths
    - Added garbage collection triggers
    - Optimized similarity calculations
    """
    
    def __init__(self, content_data: Dict = None):
        self.content_data = content_data or {}
        self.normalizer = TurkishTextNormalizer()
        self.fuzzy_matcher = FuzzyMatcher()
        
        # Memory-optimized settings
        self._processing_count = 0
        self._cleanup_interval = 50  # Cleanup every 50 operations
        self._max_text_length = 500  # Limit input text length
        
        # Statistics
        self._total_matches = 0
        self._cache_hits = 0
        self._memory_cleanups = 0
        
        logger.info("🧠 Memory-Optimized Question Matcher initialized")
    
    @memory_optimized_cache(maxsize=50)  # CRITICAL FIX: Reduced from 1000 to 50
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Memory-optimized similarity calculation"""
        # Limit text length to prevent memory bloat
        text1 = text1[:self._max_text_length]
        text2 = text2[:self._max_text_length]
        
        # Normalleştir
        norm1 = self.normalizer.normalize_text(text1)
        norm2 = self.normalizer.normalize_text(text2)
        
        # Skip if too short
        if len(norm1) < 2 or len(norm2) < 2:
            return 0.0
        
        # Farklı similarity metrikleri (simplified)
        basic_ratio = self.fuzzy_matcher.similarity_ratio(norm1, norm2)
        
        # Only calculate other ratios if basic ratio is promising
        if basic_ratio > 0.3:
            partial_ratio = self.fuzzy_matcher.partial_ratio(norm1, norm2)
            token_ratio = self.fuzzy_matcher.token_set_ratio(norm1, norm2)
            max_score = max(basic_ratio, partial_ratio, token_ratio)
        else:
            max_score = basic_ratio
        
        return max_score
    
    def _periodic_cleanup(self):
        """Periodic memory cleanup"""
        self._processing_count += 1
        
        if self._processing_count % self._cleanup_interval == 0:
            try:
                # Clear caches
                self._calculate_similarity.cache_clear()
                self.normalizer.normalize_text.cache_clear()
                self.normalizer.remove_diacritics.cache_clear()
                
                # Force garbage collection
                gc.collect()
                
                self._memory_cleanups += 1
                logger.debug(f"🧹 Memory cleanup #{self._memory_cleanups} completed")
                
            except Exception as e:
                logger.warning(f"Memory cleanup failed: {e}")
    
    def find_keyword_matches(self, question: str, category_data: Dict) -> Tuple[float, List[str]]:
        """Memory-optimized keyword matching"""
        # Trigger periodic cleanup
        self._periodic_cleanup()
        
        # Limit question length
        question = question[:self._max_text_length]
        question_normalized = self.normalizer.normalize_text(question)
        question_words = set(question_normalized.split()[:20])  # Limit words
        
        matched_keywords = []
        total_score = 0.0
        
        # Limit keywords to process
        keywords = category_data.get("keywords", [])[:50]  # Max 50 keywords
        
        for keyword in keywords:
            keyword_normalized = self.normalizer.normalize_text(keyword)
            
            # Tam eşleşme
            if keyword_normalized in question_normalized:
                matched_keywords.append(keyword)
                total_score += 1.0
                continue
            
            # Fuzzy eşleşme (only if keyword is reasonably long)
            if len(keyword_normalized) > 3:
                similarity = self._calculate_similarity(question_normalized, keyword_normalized)
                if similarity > 0.65:  # %65 benzerlik eşiği
                    matched_keywords.append(keyword)
                    total_score += similarity
                    continue
        
        # Limit matched keywords
        matched_keywords = matched_keywords[:10]  # Max 10 matches
        
        return total_score, matched_keywords
    
    def find_semantic_matches(self, question: str, category_data: Dict, model_manager=None) -> Tuple[float, str]:
        """Memory-optimized semantic matching"""
        try:
            if not model_manager or not hasattr(model_manager, 'generate_embedding'):
                return 0.0, ""
            
            # Trigger periodic cleanup
            self._periodic_cleanup()
            
            # Limit question length
            question = question[:self._max_text_length]
            
            # Get question embedding with memory optimization
            try:
                question_embedding = model_manager.generate_embedding(question)
                if not question_embedding:
                    return 0.0, ""
            except Exception as e:
                logger.warning(f"Embedding generation failed: {e}")
                return 0.0, ""
            
            best_score = 0.0
            best_match = ""
            
            # Limit content items to process
            content_items = category_data.get("content", [])[:20]  # Max 20 items
            
            for item in content_items:
                try:
                    content_text = item.get("keywords", "")[:self._max_text_length]
                    if not content_text:
                        continue
                    
                    # Get content embedding
                    content_embedding = model_manager.generate_embedding(content_text)
                    if not content_embedding:
                        continue
                    
                    # Calculate cosine similarity (memory efficient)
                    similarity = self._calculate_cosine_similarity(question_embedding, content_embedding)
                    
                    if similarity > best_score:
                        best_score = similarity
                        best_match = item.get("response", "")
                
                except Exception as e:
                    logger.debug(f"Semantic matching error for item: {e}")
                    continue
            
            return best_score, best_match
            
        except Exception as e:
            logger.warning(f"Semantic matching failed: {e}")
            return 0.0, ""
    
    @staticmethod
    def _calculate_cosine_similarity(embedding1: List[float], embedding2: List[float]) -> float:
        """Memory-efficient cosine similarity calculation"""
        try:
            # Convert to numpy arrays (more memory efficient than manual calculation)
            arr1 = np.array(embedding1, dtype=np.float32)  # Use float32 for memory efficiency
            arr2 = np.array(embedding2, dtype=np.float32)
            
            # Calculate cosine similarity
            dot_product = np.dot(arr1, arr2)
            norm1 = np.linalg.norm(arr1)
            norm2 = np.linalg.norm(arr2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            
            # Clean up arrays immediately
            del arr1, arr2
            
            return float(similarity)
            
        except Exception as e:
            logger.debug(f"Cosine similarity calculation failed: {e}")
            return 0.0
    
    def find_best_match(self, question: str, model_manager=None) -> Optional[QuestionMatch]:
        """Memory-optimized best match finding"""
        try:
            # Trigger periodic cleanup
            self._periodic_cleanup()
            
            # Limit question length
            question = question[:self._max_text_length]
            
            if not question.strip():
                return None
            
            best_match = None
            best_score = 0.0
            
            # Limit categories to process
            categories = list(self.content_data.keys())[:10]  # Max 10 categories
            
            for category in categories:
                category_data = self.content_data[category]
                
                # Find keyword matches
                keyword_score, matched_keywords = self.find_keyword_matches(question, category_data)
                
                # Find semantic matches (if model available)
                semantic_score, semantic_response = 0.0, ""
                if model_manager:
                    semantic_score, semantic_response = self.find_semantic_matches(
                        question, category_data, model_manager
                    )
                
                # Calculate combined score (weighted)
                combined_score = (keyword_score * 0.6) + (semantic_score * 0.4)
                
                # Check if this is the best match
                if combined_score > best_score and combined_score > 0.3:  # Minimum threshold
                    # Determine match type and response
                    if keyword_score > semantic_score:
                        match_type = "keyword"
                        response = category_data.get("default_response", "")
                    else:
                        match_type = "semantic"
                        response = semantic_response or category_data.get("default_response", "")
                    
                    best_match = QuestionMatch(
                        original_question=question,
                        matched_content=category,
                        similarity_score=combined_score,
                        matching_keywords=matched_keywords[:5],  # Limit keywords
                        match_type=match_type,
                        confidence=min(combined_score, 1.0),
                        response=response[:1000],  # Limit response length
                        category=category
                    )
                    best_score = combined_score
            
            self._total_matches += 1
            return best_match
            
        except Exception as e:
            logger.error(f"Best match finding failed: {e}")
            return None
    
    def get_statistics(self) -> Dict:
        """Get matching statistics"""
        return {
            "total_matches": self._total_matches,
            "memory_cleanups": self._memory_cleanups,
            "processing_count": self._processing_count,
            "cache_info": {
                "similarity_cache": self._calculate_similarity.cache_info(),
                "normalize_cache": self.normalizer.normalize_text.cache_info(),
                "diacritics_cache": self.normalizer.remove_diacritics.cache_info()
            }
        }
    
    def clear_all_caches(self):
        """Clear all caches and force cleanup"""
        try:
            self._calculate_similarity.cache_clear()
            self.normalizer.normalize_text.cache_clear()
            self.normalizer.remove_diacritics.cache_clear()
            self.fuzzy_matcher.similarity_ratio.cache_clear()
            self.fuzzy_matcher.partial_ratio.cache_clear()
            self.fuzzy_matcher.token_set_ratio.cache_clear()
            
            # Force garbage collection
            gc.collect()
            
            logger.info("🧹 All caches cleared and memory cleaned")
            
        except Exception as e:
            logger.warning(f"Cache clearing failed: {e}")

# For backward compatibility
EnhancedQuestionMatcher = MemoryOptimizedEnhancedQuestionMatcher

logger.info("🚀 Memory-Optimized Enhanced Question Matcher loaded with leak fixes")
