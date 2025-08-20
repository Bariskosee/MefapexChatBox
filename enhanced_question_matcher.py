"""
🧠 Gelişmiş Türkçe Soru Anlama ve Eşleştirme Sistemi
================================================================
Fuzzy matching, semantic similarity ve NLP teknikleri ile gelişmiş soru-cevap eşleştirmesi

Bu sistem, banka uygulamalarındaki chatbot asistanları gibi akıllı soru anlama özelliği sağlar.
"""

import re
import hashlib
import logging
import unicodedata
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
from functools import lru_cache
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

class TurkishTextNormalizer:
    """Türkçe metin normalizasyonu ve temizleme"""
    
    # Türkçe karakter dönüşümleri
    TURKISH_CHAR_MAP = {
        'ç': 'c', 'ğ': 'g', 'ı': 'i', 'ö': 'o', 'ş': 's', 'ü': 'u',
        'Ç': 'C', 'Ğ': 'G', 'I': 'I', 'İ': 'I', 'Ö': 'O', 'Ş': 'S', 'Ü': 'U'
    }
    
    # Eş anlamlı kelimeler (synonyms) - MEFAPEX için özelleştirilmiş
    SYNONYMS = {
        'çalışma': ['iş', 'mesai', 'görev', 'faaliyet', 'iş saatleri', 'working', 'work', 'job'],
        'saat': ['zaman', 'vakit', 'süre', 'time', 'hours', 'hour', 'saat kaç', 'ne zaman'],
        'saatleri': ['zamanları', 'vakitleri', 'hours', 'times'],
        'açık': ['open', 'açılış', 'başlama', 'start'],
        'kapalı': ['closed', 'kapanış', 'bitiş', 'end'],
        'nedir': ['ne', 'nelerdir', 'hangi', 'nasıl', 'what', 'which', 'kim'],
        'güvenlik': ['emniyet', 'koruma', 'security', 'safety'],
        'kural': ['yönetmelik', 'prosedür', 'talimat', 'rule', 'regulation'],
        'destek': ['yardım', 'assistance', 'help', 'support'],
        'sistem': ['platform', 'uygulama', 'yazılım', 'system', 'software'],
        'personel': ['çalışan', 'işçi', 'employee', 'staff', 'worker'],
        'fabrika': ['tesis', 'imalathane', 'üretim', 'factory', 'plant', 'manufacturing'],
        'mefapex': ['şirket', 'firma', 'company'],
        'teknoloji': ['technology', 'tech', 'bilişim', 'it'],
        'hizmet': ['service', 'servis'],
        'proje': ['project'],
        'yazılım': ['software', 'program'],
        'uygulama': ['application', 'app'],
        'geliştirme': ['development', 'dev'],
        'işlem': ['process', 'procedure', 'operation'],
        'başvuru': ['application', 'request', 'form'],
        'izin': ['permission', 'leave', 'vacation'],
        'talep': ['request', 'demand'],
        'randevu': ['appointment', 'meeting'],
        'toplantı': ['meeting', 'conference'],
        'iletişim': ['contact', 'communication', 'connection'],
        'ofis': ['office', 'büro', 'workplace'],
        'fabrika': ['factory', 'plant', 'tesis'],
        'kaçta': ['ne zaman', 'saat kaçta', 'when', 'what time'],
        'bilgi': ['information', 'info', 'detay', 'detail'],
        'hakkında': ['about', 'konusunda', 'ile ilgili', 'regarding']
    }
    
    # Soru kalıpları - Türkçe'ye özel
    QUESTION_PATTERNS = [
        r'(.*?)\s+(nedir|ne|nelerdir|nasıl|hangi|kim|nerede|ne zaman|kaç|kaçta)',
        r'(.*?)\s+(hakkında|ile ilgili|konusunda)\s+(bilgi|detay)',
        r'(.*?)\s+(yapılır|olur|edilir|alınır)',
        r'(.*?)\s+(var mı|mevcut mu|bulunuyor mu)',
        r'(.*?)\s+(gerekli|lazım|şart)',
        r'(kaç|kaçta|ne zaman)\s+(.*)',
        r'(nerede|hangi)\s+(.*)',
        r'(.*?)\s+(saatleri|zamanları|hours)'
    ]
    
    @classmethod
    def normalize_text(cls, text: str) -> str:
        """Metni normalize et (küçük harf, noktalama temizleme)"""
        if not text:
            return ""
        
        # Unicode normalize
        text = unicodedata.normalize('NFKD', text)
        
        # Küçük harfe çevir
        text = text.lower()
        
        # Ekstra boşlukları temizle
        text = ' '.join(text.split())
        
        # Noktalama işaretlerini temizle (bazıları hariç)
        text = re.sub(r'[^\w\sçğıöşüÇĞIİÖŞÜ]', ' ', text)
        
        return text.strip()
    
    @classmethod
    def remove_diacritics(cls, text: str) -> str:
        """Türkçe karakterleri ASCII karşılıklarına çevir"""
        for turkish, ascii_char in cls.TURKISH_CHAR_MAP.items():
            text = text.replace(turkish, ascii_char)
        return text
    
    @classmethod
    def extract_question_core(cls, text: str) -> str:
        """Sorunun asıl konusunu çıkar"""
        text = cls.normalize_text(text)
        
        # Soru kelimelerini kaldır
        question_words = ['ne', 'nedir', 'nelerdir', 'nasıl', 'hangi', 'kim', 
                         'nerede', 'ne zaman', 'kaç', 'kaçta', 'var mı', 'mevcut mu']
        
        words = text.split()
        core_words = [w for w in words if w not in question_words]
        
        return ' '.join(core_words)
    
    @classmethod
    def expand_with_synonyms(cls, text: str) -> List[str]:
        """Metni eş anlamlılarla genişlet"""
        words = cls.normalize_text(text).split()
        expanded_variations = [text]  # Orijinal metni de ekle
        
        for word in words:
            if word in cls.SYNONYMS:
                for synonym in cls.SYNONYMS[word]:
                    # Her eş anlamlı için yeni varyasyon oluştur
                    new_variation = text.replace(word, synonym)
                    expanded_variations.append(new_variation)
        
        return list(set(expanded_variations))  # Tekrarları kaldır

class FuzzyMatcher:
    """Gelişmiş fuzzy matching algoritmaları"""
    
    @staticmethod
    def levenshtein_distance(s1: str, s2: str) -> int:
        """Levenshtein distance hesapla"""
        if len(s1) < len(s2):
            return FuzzyMatcher.levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    @staticmethod
    def similarity_ratio(s1: str, s2: str) -> float:
        """İki string arasındaki benzerlik oranı (0-1)"""
        if not s1 or not s2:
            return 0.0
        
        # SequenceMatcher kullan (Python built-in)
        matcher = SequenceMatcher(None, s1, s2)
        return matcher.ratio()
    
    @staticmethod
    def partial_ratio(s1: str, s2: str) -> float:
        """Kısmi eşleşme oranı"""
        if not s1 or not s2:
            return 0.0
        
        shorter, longer = (s1, s2) if len(s1) <= len(s2) else (s2, s1)
        
        best_ratio = 0.0
        for i in range(len(longer) - len(shorter) + 1):
            substring = longer[i:i + len(shorter)]
            ratio = FuzzyMatcher.similarity_ratio(shorter, substring)
            best_ratio = max(best_ratio, ratio)
        
        return best_ratio
    
    @staticmethod
    def token_set_ratio(s1: str, s2: str) -> float:
        """Token set oranı (kelime bazlı karşılaştırma)"""
        if not s1 or not s2:
            return 0.0
        
        tokens1 = set(s1.lower().split())
        tokens2 = set(s2.lower().split())
        
        intersection = tokens1.intersection(tokens2)
        union = tokens1.union(tokens2)
        
        if not union:
            return 0.0
        
        return len(intersection) / len(union)

class EnhancedQuestionMatcher:
    """Gelişmiş soru eşleştirme sistemi"""
    
    def __init__(self, model_manager=None):
        self.normalizer = TurkishTextNormalizer()
        self.fuzzy_matcher = FuzzyMatcher()
        self.model_manager = model_manager
        
        # Gelişmiş bilgi bankası - MEFAPEX için özelleştirilmiş
        self.knowledge_base = {
            "working_hours": {
                "keywords": [
                    "çalışma saatleri", "calisma saatleri", "calışma saatleri", "iş saatleri", 
                    "mesai saatleri", "working hours", "work hours",
                    "çalışma zamanı", "iş zamanı", "ofis saatleri", "fabrika saatleri",
                    "kaçta açık", "kaçta kapalı", "ne zaman açık", "ne zaman kapalı",
                    "saat kaç", "çalışma", "mesai", "working", "hours", "time",
                    "açılış", "kapanış", "opening", "closing", "saat", "zaman",
                    "çalışma saati", "iş saati", "mesai saati"
                ],
                "patterns": [
                    r"çalış.*saat",
                    r"calis.*saat", 
                    r"calış.*saat",
                    r"iş.*saat",
                    r"mesai.*saat",
                    r"saat.*ne.*zaman",
                    r"kaç.*saat.*çalış",
                    r"ne.*zaman.*açık",
                    r"ne.*zaman.*kapalı",
                    r"working.*hour",
                    r"work.*hour",
                    r"office.*hour"
                ],
                "title": "Çalışma Saatleri ve İletişim",
                "category": "working_hours"
            },
            "company_info": {
                "keywords": [
                    "mefapex", "şirket", "firma", "company", "hakkında", "about",
                    "nedir", "bilgi", "information", "kim", "ne yapıyor", "what",
                    "hizmetler", "services", "teknoloji", "bilişim", "kimsiniz"
                ],
                "patterns": [
                    r"mefapex.*nedir",
                    r"mefapex.*hakkında",
                    r"şirket.*bilgi",
                    r"firma.*nedir",
                    r"company.*info"
                ],
                "title": "MEFAPEX Bilişim Teknolojileri Hakkında",
                "category": "company_info"
            },
            "technical_support": {
                "keywords": [
                    "teknik destek", "technical support", "destek", "support", "yardım", "help",
                    "problem", "sorun", "hata", "error", "arıza", "bug",
                    "nasıl alabilirim", "nasıl ulaşırım", "kim ile konuşurum",
                    "yardıma ihtiyacım var", "destek lazım"
                ],
                "patterns": [
                    r"teknik.*destek",
                    r"destek.*nasıl",
                    r"yardım.*alabilirim",
                    r"problem.*çözüm",
                    r"technical.*support"
                ],
                "title": "Teknik Destek",
                "category": "support_types"
            },
            "greetings": {
                "keywords": [
                    "merhaba", "merhabalar", "selam", "selamlar", "selamun aleyküm", "selamünaleyküm", 
                    "günaydın", "iyi günler", "iyi akşamlar", "iyi geceler", 
                    "nasılsın", "nasilsin", "nasıl gidiyor", "naber", "nabersin", "naberin", "ne haber", 
                    "hoş geldin", "hoşgeldin", "hello", "hi", "hey",
                    "good morning", "good afternoon", "good evening",
                    # Informal variations
                    "selammm", "selammmm", "merhabaaaa", "heyyyy", "hiii", "hiiii",
                    "slm", "mrb", "nbr", "nasılsınız", "nasilsiniz",
                    "nasıl gidiyorsun", "nasıl gidiyorsunuz", "ne yapıyorsun", "ne yapıyorsunuz",
                    "ne yapiyorsun", "ne yapiyorsunuz", "işler nasıl", "isler nasil",
                    "keyifler nasıl", "keyifler nasil", "everything ok", "whats up", "what's up", "wassup", "sup"
                ],
                "patterns": [
                    r"mer+haba+", r"selam+", r"günaydın", r"hel+o+", r"hi+",
                    r"naber+\w*", r"nasıl.*gid", r"ne.*yapıyor", r"işler.*nasıl",
                    r"whats+.*up", r"what.*up", r"was+up", r"sup+"
                ],
                "title": "Selamlama",
                "category": "greetings"
            },
            "thanks_goodbye": {
                "keywords": [
                    "teşekkür", "thanks", "sağol", "görüşürüz", "bye", "hoşça kal",
                    "teşekkürler", "thank you", "sağolun"
                ],
                "patterns": [
                    r"teşekkür",
                    r"thanks",
                    r"sağol",
                    r"bye"
                ],
                "title": "Teşekkür ve Veda",
                "category": "thanks_goodbye"
            }
        }
        
        # Cache için
        self._similarity_cache = {}
    
    @lru_cache(maxsize=1000)
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Cache'li benzerlik hesaplama"""
        # Normalleştir
        norm1 = self.normalizer.normalize_text(text1)
        norm2 = self.normalizer.normalize_text(text2)
        
        # Farklı similarity metrikleri
        basic_ratio = self.fuzzy_matcher.similarity_ratio(norm1, norm2)
        partial_ratio = self.fuzzy_matcher.partial_ratio(norm1, norm2)
        token_ratio = self.fuzzy_matcher.token_set_ratio(norm1, norm2)
        
        # Türkçe karaktersiz versiyon da test et
        ascii1 = self.normalizer.remove_diacritics(norm1)
        ascii2 = self.normalizer.remove_diacritics(norm2)
        ascii_ratio = self.fuzzy_matcher.similarity_ratio(ascii1, ascii2)
        
        # En yüksek skoru al
        max_score = max(basic_ratio, partial_ratio, token_ratio, ascii_ratio)
        
        return max_score
    
    def find_keyword_matches(self, question: str, category_data: Dict) -> Tuple[float, List[str]]:
        """Anahtar kelime eşleştirmesi"""
        question_normalized = self.normalizer.normalize_text(question)
        question_words = set(question_normalized.split())
        
        matched_keywords = []
        total_score = 0.0
        
        # Direct keyword matching
        for keyword in category_data["keywords"]:
            keyword_normalized = self.normalizer.normalize_text(keyword)
            
            # Tam eşleşme
            if keyword_normalized in question_normalized:
                matched_keywords.append(keyword)
                total_score += 1.0
                continue
            
            # Fuzzy eşleşme
            similarity = self._calculate_similarity(question_normalized, keyword_normalized)
            if similarity > 0.65:  # %65 benzerlik eşiği
                matched_keywords.append(keyword)
                total_score += similarity
                continue
            
            # Token-based eşleşme
            keyword_words = set(keyword_normalized.split())
            overlap = question_words.intersection(keyword_words)
            if overlap and len(overlap) >= len(keyword_words) * 0.5:  # %50 kelime örtüşmesi
                matched_keywords.append(keyword)
                total_score += len(overlap) / len(keyword_words)
        
        # Pattern matching
        for pattern in category_data.get("patterns", []):
            if re.search(pattern, question_normalized):
                matched_keywords.append(f"pattern: {pattern}")
                total_score += 0.8
        
        # Normalize score
        final_score = min(total_score / len(category_data["keywords"]), 1.0) if category_data["keywords"] else 0.0
        
        return final_score, matched_keywords
    
    def semantic_similarity_search(self, question: str) -> List[QuestionMatch]:
        """Semantic similarity ile arama"""
        results = []
        
        # Model manager yoksa fuzzy matching'e geri dön
        if not self.model_manager:
            return self._fallback_fuzzy_search(question)
        
        try:
            # Soru embedding'ini al
            question_embedding = self.model_manager.generate_embedding(question)
            if not question_embedding:
                return self._fallback_fuzzy_search(question)
            
            # Soruyu normalize et ve genişlet
            question_variations = self.normalizer.expand_with_synonyms(question)
            question_core = self.normalizer.extract_question_core(question)
            
            for category_key, category_data in self.knowledge_base.items():
                best_score = 0.0
                best_keywords = []
                best_semantic_score = 0.0
                
                # Keyword matching skoru
                keyword_score, keywords = self.find_keyword_matches(question, category_data)
                
                # Semantic similarity skoru
                try:
                    # Kategori için enhanced text oluştur
                    category_text = f"{category_data['title']} {' '.join(category_data['keywords'][:10])}"
                    category_embedding = self.model_manager.generate_embedding(category_text)
                    
                    if category_embedding:
                        semantic_score = self._calculate_cosine_similarity(
                            question_embedding, category_embedding
                        )
                        best_semantic_score = semantic_score
                    
                except Exception as e:
                    logger.debug(f"Semantic similarity failed for {category_key}: {e}")
                    semantic_score = 0.0
                
                # Combined score (keyword + semantic)
                combined_score = (keyword_score * 0.6) + (best_semantic_score * 0.4)
                
                # Her soru varyasyonu için de test et
                for variation in question_variations + [question_core]:
                    var_score, var_keywords = self.find_keyword_matches(variation, category_data)
                    if var_score > keyword_score:
                        keyword_score = var_score
                        keywords = var_keywords
                
                # Final score hesapla
                final_score = max(combined_score, keyword_score)
                
                # Eşik kontrolü
                if final_score > 0.25:  # Minimum %25 benzerlik
                    confidence = min(final_score * 1.3, 1.0)  # Boost confidence
                    
                    match = QuestionMatch(
                        original_question=question,
                        matched_content=category_data["title"],
                        similarity_score=final_score,
                        matching_keywords=keywords[:5],  # İlk 5 anahtar kelime
                        match_type="semantic_enhanced",
                        confidence=confidence,
                        response="",  # Response content_manager'dan gelecek
                        category=category_data["category"]
                    )
                    results.append(match)
            
            # Skora göre sırala
            results.sort(key=lambda x: x.confidence, reverse=True)
            return results
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return self._fallback_fuzzy_search(question)
    
    def _fallback_fuzzy_search(self, question: str) -> List[QuestionMatch]:
        """Fallback fuzzy search when semantic search fails"""
        results = []
        
        question_variations = self.normalizer.expand_with_synonyms(question)
        question_core = self.normalizer.extract_question_core(question)
        
        for category_key, category_data in self.knowledge_base.items():
            best_score = 0.0
            best_keywords = []
            
            # Her soru varyasyonu için test et
            for variation in question_variations + [question_core]:
                score, keywords = self.find_keyword_matches(variation, category_data)
                if score > best_score:
                    best_score = score
                    best_keywords = keywords
            
            # Eşik kontrolü
            if best_score > 0.3:  # Minimum %30 benzerlik
                confidence = min(best_score * 1.1, 1.0)
                
                match = QuestionMatch(
                    original_question=question,
                    matched_content=category_data["title"],
                    similarity_score=best_score,
                    matching_keywords=best_keywords,
                    match_type="fuzzy_fallback",
                    confidence=confidence,
                    response="",
                    category=category_data["category"]
                )
                results.append(match)
        
        results.sort(key=lambda x: x.confidence, reverse=True)
        return results
    
    def _calculate_cosine_similarity(self, embedding1, embedding2) -> float:
        """Cosine similarity hesapla"""
        try:
            # NumPy array'e çevir
            if isinstance(embedding1, list):
                embedding1 = np.array(embedding1)
            if isinstance(embedding2, list):
                embedding2 = np.array(embedding2)
            
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
    
    def _detect_intelligent_greeting(self, question: str) -> Optional[QuestionMatch]:
        """Akıllı selamlama tespiti - pattern matching ve repeated character detection"""
        
        normalized_text = self.normalizer.normalize_text(question.lower().strip())
        original_text = question.lower().strip()
        
        # Pattern-based greeting detection
        greeting_patterns = [
            # Temel selamlamalar ve varyasyonları
            r"^(merhaba+|selam+|hi+|hey+|hello+)$",
            r"^(mrb|slm|nbr)$",  # Kısaltmalar
            
            # Nasılsın variations
            r"^(naber|nabersin|naberin|ne haber)[\s\w]*$",
            r"^nasıl[\s\w]*$",
            r"^ne[\s]+(yapıyor|yapıyorsun|yapıyorsunuz)[\s\w]*$",
            r"^(işler|keyifler)[\s]+nasıl[\s\w]*$",
            
            # English greetings
            r"^(whats+[\s]*up|what[\s]*up|sup+|wassup)[\s\w]*$",
            r"^(good[\s]+(morning|afternoon|evening|night))[\s\w]*$",
            
            # Repeated characters (selammm, heyyyy, etc)
            r"^(selam{2,}|merhaba{2,}|hi{2,}|hey{2,})[\s\w]*$",
            
            # Günün zamanı selamlamaları
            r"^(günaydın|iyi[\s]+(günler|akşamlar|geceler))[\s\w]*$",
            
            # Mixed language patterns
            r"^(everything[\s]+ok|everything[\s]+fine)[\s\w]*$"
        ]
        
        # Pattern kontrolü
        for pattern in greeting_patterns:
            if re.match(pattern, normalized_text, re.IGNORECASE):
                logger.info(f"🎯 Intelligent greeting detected: '{question}' matched pattern: {pattern}")
                
                return QuestionMatch(
                    original_question=question,
                    category="greetings",
                    matched_content="Selamlama",
                    similarity_score=0.95,
                    matching_keywords=[pattern],
                    match_type="intelligent_greeting_pattern",
                    confidence=0.95,  # Yüksek confidence - pattern match
                    response="Greeting detected via pattern matching"
                )
        
        # Keyword-based greeting detection with repeated characters
        greeting_keywords = [
            "merhaba", "selam", "selamlar", "merhabalar", "günaydın", "naber", "nabersin",
            "nasılsın", "nasilsin", "hi", "hello", "hey", "slm", "mrb", "nbr",
            "whats up", "what's up", "wassup", "sup", "ne yapıyorsun", "işler nasıl"
        ]
        
        # Repeated character detection (selammm -> selam)
        def clean_repeated_chars(text):
            """Tekrarlanan karakterleri temizle"""
            return re.sub(r'(.)\1{2,}', r'\1', text)
        
        cleaned_text = clean_repeated_chars(normalized_text)
        
        # Keyword match check
        for keyword in greeting_keywords:
            normalized_keyword = self.normalizer.normalize_text(keyword.lower())
            
            # Direct match
            if normalized_keyword in normalized_text or normalized_keyword in cleaned_text:
                logger.info(f"🎯 Intelligent greeting detected: '{question}' contains keyword: '{keyword}'")
                
                return QuestionMatch(
                    original_question=question,
                    category="greetings",
                    matched_content="Selamlama",
                    similarity_score=0.90,
                    matching_keywords=[keyword],
                    match_type="intelligent_greeting_keyword",
                    confidence=0.90,
                    response="Greeting detected via keyword matching"
                )
        
        # Short message heuristic - kısa mesajlar genelde greeting'dir
        words = normalized_text.split()
        if len(words) <= 3 and len(normalized_text) <= 15:
            # Greeting-like short messages
            short_greeting_patterns = [
                r"^[a-zçğıöşü]{2,8}$",  # Tek kelime, makul uzunluk
                r"^[a-zçğıöşü]{2,5}[\s]+[a-zçğıöşü]{2,8}$",  # İki kelime
            ]
            
            for pattern in short_greeting_patterns:
                if re.match(pattern, normalized_text):
                    # Additional check - contains greeting-like characters
                    if any(char in normalized_text for char in ['selam', 'merh', 'naber', 'nasıl', 'hey', 'hello']):
                        logger.info(f"🎯 Intelligent greeting detected: '{question}' short greeting heuristic")
                        
                        return QuestionMatch(
                            original_question=question,
                            category="greetings",
                            matched_content="Selamlama",
                            similarity_score=0.75,
                            matching_keywords=["short_heuristic"],
                            match_type="intelligent_greeting_heuristic",
                            confidence=0.75,
                            response="Greeting detected via heuristic analysis"
                        )
        
        return None
    
    def find_best_match(self, question: str, threshold: float = 0.35) -> Optional[QuestionMatch]:
        """En iyi eşleşmeyi bul"""
        
        # Boş soru kontrolü
        if not question or len(question.strip()) < 2:
            return None
        
        # Önce intelligent greeting detection yap
        greeting_match = self._detect_intelligent_greeting(question)
        if greeting_match:
            return greeting_match
        
        # Semantic search
        matches = self.semantic_similarity_search(question)
        
        # En iyi eşleşmeyi seç
        if matches and matches[0].confidence >= threshold:
            best_match = matches[0]
            
            logger.info(f"✅ Enhanced Question matched: '{question}' -> '{best_match.matched_content}' "
                       f"(confidence: {best_match.confidence:.3f}, type: {best_match.match_type})")
            
            return best_match
        
        # Eşleşme bulunamadı
        if matches:
            logger.info(f"❌ No strong match found for: '{question}' (best score: {matches[0].confidence:.3f})")
        else:
            logger.info(f"❌ No match found for: '{question}'")
        
        return None

# Test fonksiyonu
def test_enhanced_question_matching():
    """Gelişmiş soru eşleştirmesini test et"""
    
    # Model manager'ı import et
    try:
        from model_manager import model_manager
        enhanced_matcher = EnhancedQuestionMatcher(model_manager)
    except ImportError:
        logger.warning("Model manager not available, using fallback")
        enhanced_matcher = EnhancedQuestionMatcher(None)
    
    test_questions = [
        # Çalışma saatleri testleri
        ("çalışma saatleri nelerdir?", "working_hours"),
        ("calisma saatleri nedir?", "working_hours"),  # Türkçe karakter olmadan
        ("calışma saatleri", "working_hours"),  # Farklı yazım
        ("iş saatleri kaç?", "working_hours"),
        ("ne zaman açık?", "working_hours"),
        ("mesai saatleri nedir?", "working_hours"),
        ("working hours nedir?", "working_hours"),  # İngilizce karışık
        ("fabrika kaçta açılıyor?", "working_hours"),
        ("ofis saatleri", "working_hours"),
        ("saat kaçta açıksınız?", "working_hours"),
        
        # Şirket bilgileri testleri
        ("mefapex nedir?", "company_info"),
        ("şirket hakkında bilgi", "company_info"),
        ("firma ne yapıyor?", "company_info"),
        ("mefapex kimdir?", "company_info"),
        
        # Teknik destek testleri
        ("teknik destek nasıl alabilirim?", "technical_support"),
        ("yardıma ihtiyacım var", "technical_support"),
        ("problem çözümü", "technical_support"),
        ("destek lazım", "technical_support"),
        
        # Selamlama testleri
        ("merhaba", "greetings"),
        ("selam nasılsın?", "greetings"),
        ("günaydın", "greetings"),
        
        # Teşekkür testleri
        ("teşekkürler", "thanks_goodbye"),
        ("sağol", "thanks_goodbye"),
        ("thanks", "thanks_goodbye"),
        
        # İlgisiz sorular
        ("bugün hava nasıl?", None),  # Eşleşmemeli
        ("futbol maçı", None)  # Eşleşmemeli
    ]
    
    print("🧪 GELİŞMİŞ SORU EŞLEŞTİRME TESTİ")
    print("=" * 80)
    
    correct_matches = 0
    total_tests = len(test_questions)
    
    for i, (question, expected_category) in enumerate(test_questions, 1):
        match = enhanced_matcher.find_best_match(question)
        
        # Kategorinin doğru eşleşip eşleşmediğini kontrol et
        if expected_category is None:
            # Eşleşmemesi gereken sorular
            is_correct = match is None
            status = "✅ PASS (No Match)" if is_correct else "❌ FAIL (Unexpected Match)"
        else:
            # Eşleşmesi gereken sorular
            is_correct = match is not None and match.category == expected_category
            status = "✅ PASS" if is_correct else "❌ FAIL"
        
        if is_correct:
            correct_matches += 1
        
        print(f"{i:2d}. {status} | {question}")
        print(f"    Expected: {expected_category}")
        if match:
            print(f"    Got: {match.category} (confidence: {match.confidence:.3f}, type: {match.match_type})")
            print(f"    Keywords: {match.matching_keywords[:3]}")
        else:
            print(f"    Got: No match")
        print()
    
    # Sonuçları göster
    accuracy = (correct_matches / total_tests) * 100
    print(f"📊 TEST RESULTS:")
    print(f"    Correct: {correct_matches}/{total_tests}")
    print(f"    Accuracy: {accuracy:.1f}%")
    
    return accuracy > 85  # %85 üzeri başarı bekliyoruz

if __name__ == "__main__":
    test_enhanced_question_matching()
