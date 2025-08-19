"""
🎯 Hybrid Relevance Detection System for MEFAPEX AI
====================================================
Advanced system combining multiple techniques to detect irrelevant questions
and provide intelligent, contextual responses.
"""

import asyncio
import re
import logging
from typing import Dict, Optional, List, Tuple, Set
from dataclasses import dataclass
from enum import Enum
import numpy as np
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

class ClassificationMethod(Enum):
    """Classification methods used"""
    KEYWORD_FILTER = "keyword_filter"
    SEMANTIC_SIMILARITY = "semantic_similarity"  
    AI_CLASSIFICATION = "ai_classification"
    HYBRID_VOTE = "hybrid_vote"
    PATTERN_MATCHING = "pattern_matching"

class RelevanceLevel(Enum):
    """Question relevance levels"""
    HIGHLY_RELEVANT = "highly_relevant"      # 0.8+
    RELEVANT = "relevant"                    # 0.6-0.8
    PARTIALLY_RELEVANT = "partially_relevant" # 0.4-0.6
    LOW_RELEVANCE = "low_relevance"          # 0.2-0.4
    IRRELEVANT = "irrelevant"                # 0.0-0.2

@dataclass
class ClassificationResult:
    """Result of relevance classification"""
    is_relevant: bool
    confidence: float
    relevance_level: RelevanceLevel
    method: ClassificationMethod
    details: Dict
    matched_categories: List[str]
    reasoning: str
    response_suggestion: Optional[str] = None
    processing_time_ms: float = 0.0

class HybridRelevanceDetector:
    """
    Advanced hybrid relevance detection system for MEFAPEX AI
    
    Combines multiple approaches:
    1. Fast keyword filtering (1-5ms)
    2. Pattern matching (5-10ms) 
    3. Semantic similarity (50-100ms)
    4. AI classification (200-500ms)
    5. Hybrid voting system
    """
    
    def __init__(self, company_name: str = "MEFAPEX Bilişim Teknolojileri"):
        self.company_name = company_name
        
        # Domain categories for MEFAPEX
        self.domain_categories = {
            "factory_operations": {
                "keywords": [
                    "fabrika", "üretim", "production", "manufacturing", "çalışma saati", 
                    "vardiya", "shift", "mesai", "iş", "work", "factory", "plant",
                    "operasyon", "operation", "makine", "machine", "equipment", "ekipman",
                    "hat", "line", "üretim hattı", "production line", "kalite", "quality"
                ],
                "weight": 1.2  # Higher importance for core business
            },
            "hr_processes": {
                "keywords": [
                    "izin", "leave", "vacation", "tatil", "başvuru", "application",
                    "personel", "staff", "employee", "çalışan", "ik", "hr", "human resources",
                    "maaş", "salary", "özlük", "sicil", "kayıt", "bordro", "payroll",
                    "terfi", "promotion", "eğitim", "training"
                ],
                "weight": 1.0
            },
            "safety_security": {
                "keywords": [
                    "güvenlik", "safety", "security", "kural", "rule", "regulation",
                    "kaza", "accident", "acil", "emergency", "first aid", "ilk yardım",
                    "helmet", "kask", "protective", "koruyucu", "ppe", "kişisel koruyucu",
                    "risk", "tehlike", "danger", "önlem", "precaution"
                ],
                "weight": 1.3  # Safety is critical
            },
            "technical_support": {
                "keywords": [
                    "teknik", "technical", "destek", "support", "bilgisayar", "computer",
                    "yazılım", "software", "sistem", "system", "problem", "hata", "error",
                    "arıza", "breakdown", "bug", "it", "network", "ağ", "server",
                    "database", "veritabanı", "backup", "yedek"
                ],
                "weight": 1.1
            },
            "company_info": {
                "keywords": [
                    "mefapex", "şirket", "company", "firma", "hakkında", "about",
                    "bilgi", "information", "iletişim", "contact", "adres", "address",
                    "telefon", "phone", "email", "website", "misyon", "mission",
                    "vizyon", "vision", "değer", "values", "tarihçe", "history"
                ],
                "weight": 0.9
            },
            "quality_compliance": {
                "keywords": [
                    "kalite", "quality", "iso", "standart", "standard", "belge", "certificate",
                    "denetim", "audit", "uygunluk", "compliance", "süreç", "process",
                    "prosedür", "procedure", "dokümantasyon", "documentation"
                ],
                "weight": 1.1
            }
        }
        
        # Quick filters for immediate classification
        self.quick_filters = {
            'definitely_relevant': [
                # Core business terms
                'mefapex', 'fabrika', 'üretim', 'production', 'manufacturing',
                'yazılım', 'software', 'sistem', 'system', 'teknik', 'technical',
                'destek', 'support', 'proje', 'project', 'geliştirme', 'development',
                
                # Work-related terms
                'çalışma', 'work', 'mesai', 'shift', 'vardiya', 'personel', 'staff',
                'izin', 'leave', 'başvuru', 'application', 'süreç', 'process',
                
                # Technical terms
                'web', 'mobile', 'mobil', 'api', 'database', 'veritabanı',
                'server', 'hosting', 'domain', 'ağ', 'network',
                
                # Business terms
                'fiyat', 'price', 'teklif', 'offer', 'hizmet', 'service',
                'müşteri', 'customer', 'client', 'firma', 'company'
            ],
            'definitely_irrelevant': [
                # Personal/lifestyle
                'tarif', 'recipe', 'yemek', 'food', 'cooking', 'pişir',
                'müzik', 'music', 'şarkı', 'song', 'film', 'movie', 'dizi', 'series',
                'oyun', 'game', 'eğlence', 'entertainment',
                
                # Personal relationships
                'aşk', 'love', 'sevgili', 'girlfriend', 'boyfriend', 'evlilik', 'marriage',
                'ilişki', 'relationship', 'flört', 'dating',
                
                # Health/medical (unless work-related)
                'doktor', 'doctor', 'hastane', 'hospital', 'ilaç', 'medicine',
                'hastalık', 'disease', 'ağrı', 'pain', 'tedavi', 'treatment',
                
                # Sports (unless company team)
                'spor', 'sport', 'futbol', 'football', 'basketbol', 'basketball',
                'voleybol', 'volleyball', 'maç', 'match', 'takım', 'team',
                
                # Weather/personal
                'hava', 'weather', 'yağmur', 'rain', 'kar', 'snow',
                'horoskop', 'horoscope', 'astroloji', 'astrology',
                'kilo', 'weight', 'diyet', 'diet', 'egzersiz', 'exercise'
            ]
        }
        
        # Irrelevant patterns with regex
        self.irrelevant_patterns = {
            "personal_life": [
                r"sevgili.*bul", r"sevgili.*barış", r"aşk.*hayat", r"kişisel.*problem",
                r"how.*marry", r"find.*girlfriend", r"love.*life", r"personal.*issue",
                r"ilişki.*tavsiye", r"relationship.*advice", r"evlen.*nasıl", r"nasıl.*evlen",
                r"barış.*sevgili", r"sevgili.*terk", r"ayrıl.*sevgili"
            ],
            "entertainment": [
                r"film.*öner", r"müzik.*dinle", r"oyun.*oyna", r"eğlence.*yer",
                r"movie.*recommend", r"music.*listen", r"game.*play", r"entertainment.*place",
                r"hangi.*film", r"which.*movie", r"what.*song", r"film.*izle", r"müzik.*öner",
                r"hangi.*müzik", r"oyun.*öner", r"eğlen.*ne"
            ],
            "cooking_food": [
                r"yemek.*tarif", r"nasıl.*piş", r"recipe.*cook", r"cooking.*method",
                r"malzeme.*liste", r"ingredient.*list", r"tarif.*ver", r"give.*recipe",
                r"ne.*pişir", r"what.*cook", r"pizza.*tarif", r"makarna.*nasıl",
                r"çorba.*tarif", r"et.*nasıl", r"tavuk.*piş", r"yemek.*yap"
            ],
            "travel": [
                r"seyahat.*plan", r"tatil.*yer", r"travel.*plan", r"vacation.*place",
                r"otel.*rezerv", r"hotel.*book", r"uçak.*bilet", r"flight.*ticket",
                r"nereye.*gid", r"where.*go", r"tatil.*öner", r"gezil.*yer"
            ],
            "health_medical": [
                r"hastalık.*tedavi", r"doktor.*öner", r"ilaç.*kullan", r"sağlık.*problem",
                r"disease.*treatment", r"doctor.*recommend", r"medicine.*use", r"health.*issue",
                r"ağrı.*var", r"pain.*have", r"hasta.*oldu", r"doktor.*git"
            ],
            "weather_personal": [
                r"hava.*durum", r"weather.*forecast", r"yağmur.*yağ", r"kar.*yağ",
                r"sıcaklık.*kaç", r"temperature.*what", r"bugün.*hava", r"today.*weather",
                r"hava.*nasıl", r"weather.*like"
            ],
            "general_personal": [
                r"bugün.*ne.*yap", r"what.*do.*today", r"boş.*zamanımda", r"free.*time",
                r"sıkıl.*ne.*yap", r"bored.*what.*do", r"eğlen.*ne.*yap", r"fun.*what.*do",
                r"ne.*yapsam", r"what.*should.*do"
            ]
        }
        
        # Smart responses for different categories
        self.smart_responses = {
            "personal_life": {
                "tr": """🤖 **MEFAPEX AI Asistanı**

Kişisel yaşam konularında size yardımcı olamam. Ben MEFAPEX çalışanları için tasarlanmış bir iş asistanıyım.

**Size yardımcı olabileceğim konular:**
• 🏭 Fabrika operasyonları ve çalışma saatleri
• 👥 İnsan kaynakları süreçleri  
• 🔧 Teknik destek ve IT sorunları
• 🛡️ Güvenlik kuralları ve prosedürleri
• 📊 Şirket bilgileri ve politikaları

💼 İş ile ilgili hangi konuda yardıma ihtiyacınız var?""",
                "en": """🤖 **MEFAPEX AI Assistant**

I can't help with personal life matters. I'm a work assistant designed for MEFAPEX employees.

**I can help you with:**
• 🏭 Factory operations and work schedules
• 👥 HR processes and procedures
• 🔧 Technical support and IT issues  
• 🛡️ Safety rules and procedures
• 📊 Company information and policies

💼 What work-related topic can I help you with?"""
            },
            "entertainment": {
                "tr": """🎬 **Eğlence konularında yardım edemem**

Ben MEFAPEX'te çalışanlar için iş odaklı bir asistanım. Film, müzik veya oyun önerilerinde bulunamam.

**Bunun yerine size yardımcı olabilirim:**
• 📅 Çalışma programları ve vardiya bilgileri
• 🎉 Şirket etkinlikleri ve sosyal aktiviteler
• ☕ Dinlenme alanları ve tesisler hakkında bilgi  
• ⚖️ İş-yaşam dengesi politikaları

🏭 Fabrika ile ilgili başka sorularınız var mı?""",
                "en": """🎬 **Can't help with entertainment topics**

I'm a work-focused assistant for MEFAPEX employees. I can't provide movie, music, or game recommendations.

**Instead, I can help with:**
• 📅 Work schedules and shift information
• 🎉 Company events and social activities
• ☕ Break room facilities and amenities
• ⚖️ Work-life balance policies

🏭 Any other factory-related questions?"""
            },
            "cooking_food": {
                "tr": """👨‍🍳 **Yemek tarifleri konusunda uzman değilim**

Ben MEFAPEX'in iş asistanıyım, aşçı değilim! 😊

**Size şunlarda yardımcı olabilirim:**
• 🍽️ Fabrika kantini menüleri ve saatleri
• ⏰ Yemek molası düzenlemeleri ve kuralları
• 🥪 Catering hizmetleri (varsa)
• 🍴 Personel mutfağı kullanım kuralları

🍽️ Fabrikadaki yemek imkanları hakkında bilgi ister misiniz?""",
                "en": """👨‍🍳 **I'm not an expert on cooking recipes**

I'm MEFAPEX's work assistant, not a chef! 😊

**I can help you with:**
• 🍽️ Factory cafeteria menus and hours
• ⏰ Meal break arrangements and rules
• 🥪 Catering services (if available)
• 🍴 Staff kitchen usage guidelines

🍽️ Would you like information about factory dining facilities?"""
            },
            "travel": {
                "tr": """✈️ **Seyahat konularında yardım edemem**

Ben MEFAPEX'in iş asistanıyım, seyahat acentesi değilim! 😊

**Bunun yerine size yardımcı olabilirim:**
• 🚗 Şirket araçları ve ulaşım politikaları
• 🏢 İş seyahatleri ve prosedürleri
• 📋 Seyahat masrafları ve gider raporları
• 🗓️ İş seyahati için izin başvuruları

✈️ İş ile ilgili seyahat konularında yardımcı olabilir miyim?""",
                "en": """✈️ **Can't help with travel planning**

I'm MEFAPEX's work assistant, not a travel agency! 😊

**Instead, I can help with:**
• 🚗 Company vehicles and transportation policies
• 🏢 Business travel procedures
• 📋 Travel expenses and reporting
• 🗓️ Leave applications for business trips

✈️ Can I help with work-related travel matters?"""
            },
            "health_medical": {
                "tr": """🏥 **Sağlık konularında yardım edemem**

Sağlık sorunları için mutlaka sağlık profesyonellerine danışın!

**MEFAPEX olarak size şunlarda yardımcı olabilirim:**
• 🏥 Şirket sağlık sigortası bilgileri
• 🚑 İş yerinde acil durum prosedürleri
• 🩺 Periyodik sağlık kontrolleri
• 💊 İş güvenliği ve sağlık kuralları

⚠️ Acil durumlar için: 112 | İş kazaları için: İSG birimi""",
                "en": """🏥 **Can't provide medical advice**

For health issues, please consult healthcare professionals!

**As MEFAPEX, I can help with:**
• 🏥 Company health insurance information
• 🚑 Workplace emergency procedures
• 🩺 Periodic health checkups
• 💊 Occupational health and safety rules

⚠️ Emergencies: 112 | Work accidents: OHS department"""
            },
            "general_irrelevant": {
                "tr": """❓ **Bu konu MEFAPEX kapsamında değil**

Sorduğunuz konu işyerimizle doğrudan ilgili görünmüyor. Ben MEFAPEX çalışanları için özel olarak tasarlanmış bir asistanım.

**Odak alanlarım:**
• 🏭 Fabrika operasyonları ve üretim süreçleri
• 👥 İnsan kaynakları ve personel işlemleri
• 🔧 Teknik destek ve IT çözümleri
• 🛡️ Güvenlik ve uyumluluk konuları
• 📊 Şirket politikaları ve prosedürleri
• 💼 İş süreçleri ve verimliliği

💡 İş ile ilgili hangi konuda yardıma ihtiyacınız var?""",
                "en": """❓ **This topic is outside MEFAPEX scope**

Your question doesn't seem directly related to our workplace. I'm an assistant specifically designed for MEFAPEX employees.

**My focus areas:**
• 🏭 Factory operations and production processes
• 👥 HR processes and personnel matters
• 🔧 Technical support and IT solutions
• 🛡️ Safety and compliance topics
• 📊 Company policies and procedures
• 💼 Work processes and efficiency

💡 What work-related topic can I help you with?"""
            }
        }
        
        logger.info("🎯 Hybrid Relevance Detector initialized for MEFAPEX")
    
    def _detect_language(self, text: str) -> str:
        """Detect if text is Turkish or English"""
        turkish_chars = set('çğıöşüÇĞIİÖŞÜ')
        has_turkish_chars = any(char in turkish_chars for char in text)
        
        turkish_words = [
            'ne', 'nasıl', 'nedir', 'niye', 'için', 'ben', 'sen', 'bu', 'şu',
            'var', 'yok', 'ile', 'bir', 'ki', 'da', 'de', 'mi', 'mı'
        ]
        turkish_word_count = sum(1 for word in turkish_words if word in text.lower().split())
        
        return "tr" if has_turkish_chars or turkish_word_count >= 2 else "en"
    
    def _quick_keyword_filter(self, message: str) -> Dict:
        """Fast keyword-based filtering (1-5ms)"""
        message_lower = message.lower().strip()
        
        # Count matches for relevant keywords
        relevant_matches = []
        for keyword in self.quick_filters['definitely_relevant']:
            if keyword in message_lower:
                relevant_matches.append(keyword)
        
        # Count matches for irrelevant keywords  
        irrelevant_matches = []
        for keyword in self.quick_filters['definitely_irrelevant']:
            if keyword in message_lower:
                irrelevant_matches.append(keyword)
        
        relevant_score = len(relevant_matches)
        irrelevant_score = len(irrelevant_matches)
        
        # Strong positive signals
        if relevant_score >= 2 and irrelevant_score == 0:
            return {
                'is_relevant': True,
                'confidence': min(0.95, 0.7 + (relevant_score * 0.1)),
                'matched_keywords': relevant_matches,
                'reason': f'strong_relevant_keywords ({relevant_score} matches)',
                'category': 'definitely_relevant'
            }
        
        # Strong negative signals
        elif irrelevant_score >= 1 and relevant_score == 0:
            return {
                'is_relevant': False,
                'confidence': min(0.9, 0.6 + (irrelevant_score * 0.15)),
                'matched_keywords': irrelevant_matches,
                'reason': f'clear_irrelevant_keywords ({irrelevant_score} matches)',
                'category': 'definitely_irrelevant'
            }
        
        # Mixed or unclear signals
        else:
            return {
                'is_relevant': relevant_score > irrelevant_score,
                'confidence': 0.3,  # Low confidence, need other methods
                'matched_keywords': {
                    'relevant': relevant_matches[:3],  # Limit for readability
                    'irrelevant': irrelevant_matches[:3]
                },
                'reason': f'ambiguous_keywords (rel:{relevant_score}, irr:{irrelevant_score})',
                'category': 'mixed_signals'
            }
    
    def _pattern_matching(self, message: str) -> Dict:
        """Pattern-based classification (5-10ms)"""
        message_lower = message.lower().strip()
        
        for category, patterns in self.irrelevant_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    return {
                        'is_relevant': False,
                        'confidence': 0.85,
                        'matched_pattern': pattern,
                        'pattern_category': category,
                        'reason': f'matched_irrelevant_pattern: {category}',
                        'category': 'pattern_match'
                    }
        
        # Check for work-related patterns
        work_patterns = [
            r"(mefapex|fabrika|üretim).*nasıl",
            r"(çalışma|work).*saat",
            r"(teknik|technical).*destek",
            r"(güvenlik|safety).*kural",
            r"(personel|hr).*işlem"
        ]
        
        for pattern in work_patterns:
            if re.search(pattern, message_lower):
                return {
                    'is_relevant': True,
                    'confidence': 0.8,
                    'matched_pattern': pattern,
                    'pattern_category': 'work_related',
                    'reason': 'matched_work_pattern',
                    'category': 'work_pattern'
                }
        
        return {
            'is_relevant': None,  # Uncertain
            'confidence': 0.5,
            'matched_pattern': None,
            'reason': 'no_pattern_match',
            'category': 'no_pattern'
        }
    
    def _domain_analysis(self, message: str) -> Dict:
        """Analyze message against domain categories"""
        message_lower = message.lower().strip()
        domain_scores = {}
        
        for domain, config in self.domain_categories.items():
            matches = 0
            matched_keywords = []
            
            for keyword in config["keywords"]:
                if keyword.lower() in message_lower:
                    matches += 1
                    matched_keywords.append(keyword)
            
            # Apply domain weight
            weighted_score = (matches / len(config["keywords"])) * config["weight"]
            domain_scores[domain] = {
                'score': weighted_score,
                'matches': matches,
                'matched_keywords': matched_keywords[:5]  # Limit for readability
            }
        
        # Find best matching domain
        best_domain = max(domain_scores.keys(), key=lambda x: domain_scores[x]['score'])
        best_score = domain_scores[best_domain]['score']
        
        return {
            'best_domain': best_domain,
            'best_score': best_score,
            'all_scores': domain_scores,
            'is_relevant': best_score > 0.1,  # Threshold for relevance
            'confidence': min(0.8, best_score * 2),  # Scale to confidence
            'reason': f'domain_analysis: best_match={best_domain}',
            'category': 'domain_analysis'
        }
    
    async def _semantic_classification(self, message: str) -> Dict:
        """Semantic similarity classification (simulated - 50-100ms)"""
        await asyncio.sleep(0.07)  # Simulate processing time
        
        # In real implementation, this would use sentence transformers
        # For now, we'll use a sophisticated keyword-based approximation
        
        message_lower = message.lower()
        
        # Business/technical context indicators
        business_indicators = [
            'yazılım', 'software', 'sistem', 'system', 'teknik', 'technical',
            'proje', 'project', 'geliştirme', 'development', 'üretim', 'production',
            'fabrika', 'factory', 'çalışma', 'work', 'iş', 'business'
        ]
        
        # Personal/lifestyle context indicators
        personal_indicators = [
            'kişisel', 'personal', 'özel', 'private', 'kendim', 'myself',
            'evim', 'home', 'ailem', 'family', 'arkadaş', 'friend'
        ]
        
        business_score = sum(1 for indicator in business_indicators if indicator in message_lower)
        personal_score = sum(1 for indicator in personal_indicators if indicator in message_lower)
        
        # Semantic context analysis
        if business_score > personal_score and business_score > 0:
            semantic_score = min(0.8, 0.4 + (business_score * 0.15))
            return {
                'is_relevant': True,
                'confidence': semantic_score,
                'business_score': business_score,
                'personal_score': personal_score,
                'reason': f'semantic_business_context (score: {business_score})',
                'category': 'semantic_business'
            }
        elif personal_score > 0:
            return {
                'is_relevant': False,
                'confidence': min(0.75, 0.5 + (personal_score * 0.1)),
                'business_score': business_score,
                'personal_score': personal_score,
                'reason': f'semantic_personal_context (score: {personal_score})',
                'category': 'semantic_personal'
            }
        else:
            return {
                'is_relevant': True,  # Default to relevant when uncertain
                'confidence': 0.4,
                'business_score': business_score,
                'personal_score': personal_score,
                'reason': 'semantic_uncertain_context',
                'category': 'semantic_uncertain'
            }
    
    async def _ai_classification(self, message: str) -> Dict:
        """AI-powered classification (simulated - 200-500ms)"""
        await asyncio.sleep(0.3)  # Simulate AI processing time
        
        # In real implementation, this would call OpenAI/Claude API
        # For now, we'll use advanced heuristics
        
        message_lower = message.lower().strip()
        
        # Advanced heuristic classification
        question_words = ['ne', 'nasıl', 'nedir', 'niye', 'what', 'how', 'why', 'when', 'where']
        has_question = any(word in message_lower for word in question_words)
        
        # Context clues
        work_context_clues = [
            'işte', 'at work', 'fabrikada', 'in factory', 'şirkette', 'at company',
            'mefapex', 'çalışırken', 'while working', 'iş yerinde', 'at workplace'
        ]
        
        personal_context_clues = [
            'evde', 'at home', 'kişisel', 'personal', 'özel', 'private',
            'kendim için', 'for myself', 'boş zamanımda', 'in free time'
        ]
        
        work_context = any(clue in message_lower for clue in work_context_clues)
        personal_context = any(clue in message_lower for clue in personal_context_clues)
        
        # AI-style reasoning simulation
        if work_context and not personal_context:
            confidence = 0.85
            is_relevant = True
            reasoning = "clear_work_context_detected"
        elif personal_context and not work_context:
            confidence = 0.8
            is_relevant = False
            reasoning = "clear_personal_context_detected"
        elif has_question and len(message_lower.split()) < 10:
            # Short questions are often more direct
            confidence = 0.6
            is_relevant = True
            reasoning = "short_direct_question"
        else:
            # Default heuristic based on message characteristics
            confidence = 0.65
            is_relevant = True
            reasoning = "ai_heuristic_classification"
        
        return {
            'is_relevant': is_relevant,
            'confidence': confidence,
            'has_question': has_question,
            'work_context': work_context,
            'personal_context': personal_context,
            'reasoning': reasoning,
            'reason': f'ai_classification: {reasoning}',
            'category': 'ai_classification'
        }
    
    def _generate_response_suggestion(self, classification_results: List[Dict], 
                                    original_message: str, language: str) -> Optional[str]:
        """Generate intelligent response suggestion based on classification"""
        
        # Find the most confident irrelevant classification
        irrelevant_results = [r for r in classification_results if not r.get('is_relevant', True)]
        
        if not irrelevant_results:
            return None  # Let main AI handle relevant questions
        
        # Get the most confident irrelevant classification
        best_irrelevant = max(irrelevant_results, key=lambda x: x.get('confidence', 0))
        
        message_lower = original_message.lower()
        
        # Determine response category based on content and pattern matches
        if 'pattern_category' in best_irrelevant:
            # Use the detected pattern category
            pattern_category = best_irrelevant['pattern_category']
            if pattern_category in ['personal_life', 'entertainment', 'cooking_food', 'travel', 'health_medical']:
                category = pattern_category
            else:
                category = "general_irrelevant"
        elif any(word in message_lower for word in ['yemek', 'tarif', 'recipe', 'cook', 'pişir', 'pizza', 'makarna']):
            category = "cooking_food"
        elif any(word in message_lower for word in ['film', 'müzik', 'oyun', 'movie', 'music', 'game', 'eğlence']):
            category = "entertainment"
        elif any(word in message_lower for word in ['aşk', 'sevgili', 'ilişki', 'love', 'relationship', 'evlen', 'barış']):
            category = "personal_life"
        elif any(word in message_lower for word in ['seyahat', 'tatil', 'travel', 'vacation', 'otel', 'hotel']):
            category = "travel"
        elif any(word in message_lower for word in ['doktor', 'hasta', 'ilaç', 'doctor', 'medicine', 'health']):
            category = "health_medical"
        else:
            category = "general_irrelevant"
        
        return self.smart_responses.get(category, {}).get(language, 
               self.smart_responses["general_irrelevant"][language])
    
    def _determine_relevance_level(self, confidence: float) -> RelevanceLevel:
        """Convert confidence score to relevance level"""
        if confidence >= 0.8:
            return RelevanceLevel.HIGHLY_RELEVANT
        elif confidence >= 0.6:
            return RelevanceLevel.RELEVANT
        elif confidence >= 0.4:
            return RelevanceLevel.PARTIALLY_RELEVANT
        elif confidence >= 0.2:
            return RelevanceLevel.LOW_RELEVANCE
        else:
            return RelevanceLevel.IRRELEVANT
    
    async def classify(self, user_message: str) -> ClassificationResult:
        """
        Main classification method using hybrid approach
        Optimized for speed while maintaining accuracy
        """
        start_time = asyncio.get_event_loop().time()
        
        message = user_message.strip()
        language = self._detect_language(message)
        
        classification_results = []
        
        try:
            # 1. QUICK KEYWORD FILTER (1-5ms) - First line of defense
            keyword_result = self._quick_keyword_filter(message)
            classification_results.append(keyword_result)
            
            # If high confidence, return immediately
            if keyword_result['confidence'] > 0.85:
                end_time = asyncio.get_event_loop().time()
                
                return ClassificationResult(
                    is_relevant=keyword_result['is_relevant'],
                    confidence=keyword_result['confidence'],
                    relevance_level=self._determine_relevance_level(keyword_result['confidence']),
                    method=ClassificationMethod.KEYWORD_FILTER,
                    details=keyword_result,
                    matched_categories=[keyword_result.get('category', 'keyword_filter')],
                    reasoning=keyword_result['reason'],
                    response_suggestion=self._generate_response_suggestion(
                        [keyword_result], message, language
                    ) if not keyword_result['is_relevant'] else None,
                    processing_time_ms=(end_time - start_time) * 1000
                )
            
            # 2. PATTERN MATCHING (5-10ms) - Quick pattern detection
            pattern_result = self._pattern_matching(message)
            classification_results.append(pattern_result)
            
            # If clear pattern match, return immediately
            if pattern_result['confidence'] > 0.8:
                end_time = asyncio.get_event_loop().time()
                
                return ClassificationResult(
                    is_relevant=pattern_result['is_relevant'],
                    confidence=pattern_result['confidence'],
                    relevance_level=self._determine_relevance_level(pattern_result['confidence']),
                    method=ClassificationMethod.PATTERN_MATCHING,
                    details=pattern_result,
                    matched_categories=[pattern_result.get('pattern_category', 'pattern_match')],
                    reasoning=pattern_result['reason'],
                    response_suggestion=self._generate_response_suggestion(
                        [pattern_result], message, language
                    ) if not pattern_result['is_relevant'] else None,
                    processing_time_ms=(end_time - start_time) * 1000
                )
            
            # 3. DOMAIN ANALYSIS (10-20ms) - Company-specific analysis
            domain_result = self._domain_analysis(message)
            classification_results.append(domain_result)
            
            # If strong domain match, consider returning
            if domain_result['confidence'] > 0.7:
                end_time = asyncio.get_event_loop().time()
                
                return ClassificationResult(
                    is_relevant=domain_result['is_relevant'],
                    confidence=domain_result['confidence'],
                    relevance_level=self._determine_relevance_level(domain_result['confidence']),
                    method=ClassificationMethod.SEMANTIC_SIMILARITY,
                    details=domain_result,
                    matched_categories=[domain_result['best_domain']],
                    reasoning=domain_result['reason'],
                    response_suggestion=None,  # Domain matches are relevant
                    processing_time_ms=(end_time - start_time) * 1000
                )
            
            # 4. SEMANTIC CLASSIFICATION (50-100ms) - For unclear cases
            semantic_result = await self._semantic_classification(message)
            classification_results.append(semantic_result)
            
            if semantic_result['confidence'] > 0.7:
                end_time = asyncio.get_event_loop().time()
                
                return ClassificationResult(
                    is_relevant=semantic_result['is_relevant'],
                    confidence=semantic_result['confidence'],
                    relevance_level=self._determine_relevance_level(semantic_result['confidence']),
                    method=ClassificationMethod.SEMANTIC_SIMILARITY,
                    details=semantic_result,
                    matched_categories=[semantic_result.get('category', 'semantic')],
                    reasoning=semantic_result['reason'],
                    response_suggestion=self._generate_response_suggestion(
                        [semantic_result], message, language
                    ) if not semantic_result['is_relevant'] else None,
                    processing_time_ms=(end_time - start_time) * 1000
                )
            
            # 5. AI CLASSIFICATION (200-500ms) - Final deep analysis
            ai_result = await self._ai_classification(message)
            classification_results.append(ai_result)
            
            end_time = asyncio.get_event_loop().time()
            
            return ClassificationResult(
                is_relevant=ai_result['is_relevant'],
                confidence=ai_result['confidence'],
                relevance_level=self._determine_relevance_level(ai_result['confidence']),
                method=ClassificationMethod.AI_CLASSIFICATION,
                details=ai_result,
                matched_categories=[ai_result.get('category', 'ai_classification')],
                reasoning=ai_result['reason'],
                response_suggestion=self._generate_response_suggestion(
                    classification_results, message, language
                ) if not ai_result['is_relevant'] else None,
                processing_time_ms=(end_time - start_time) * 1000
            )
            
        except Exception as e:
            logger.error(f"Classification error: {e}")
            end_time = asyncio.get_event_loop().time()
            
            # Fallback - default to relevant with low confidence
            return ClassificationResult(
                is_relevant=True,
                confidence=0.5,
                relevance_level=RelevanceLevel.PARTIALLY_RELEVANT,
                method=ClassificationMethod.HYBRID_VOTE,
                details={'error': str(e), 'fallback': True},
                matched_categories=['fallback'],
                reasoning='error_fallback_to_relevant',
                response_suggestion=None,
                processing_time_ms=(end_time - start_time) * 1000
            )

# Performance testing and usage example
async def test_hybrid_system():
    """Test the hybrid relevance detection system"""
    detector = HybridRelevanceDetector("MEFAPEX Bilişim Teknolojileri")
    
    test_cases = [
        # Definitely relevant (should be caught by keyword filter)
        "MEFAPEX fabrikasında çalışma saatleri nedir?",
        "Yazılım geliştirme projeleri hakkında bilgi alabilir miyim?",
        "Teknik destek nasıl alabilirim?",
        
        # Definitely irrelevant (should be caught by keyword/pattern filter)
        "En iyi pizza tarifi nedir?",
        "Hangi film izlemeliyim bugün?",
        "Sevgilimle nasıl barışabilirim?",
        
        # Domain-specific relevant
        "Üretim hattında kalite kontrol nasıl yapılıyor?",
        "Güvenlik kuralları nelerdir?",
        "Personel izin başvurusu nasıl yapılır?",
        
        # Moderately unclear (will go through multiple stages)
        "İş yerinde verimlilik nasıl artırılır?",
        "Proje yönetimi konusunda bilgi",
        "Sistem entegrasyonu hakkında detay",
        
        # Edge cases
        "Bugün ne yapsam?",
        "Yardım eder misin?",
        "Nasılsın?"
    ]
    
    print("🧪 MEFAPEX Hybrid Relevance Detection Test")
    print("=" * 80)
    
    total_time = 0
    relevant_count = 0
    
    for i, message in enumerate(test_cases, 1):
        print(f"\n📝 Test {i}: {message}")
        print("-" * 60)
        
        result = await detector.classify(message)
        
        total_time += result.processing_time_ms
        if result.is_relevant:
            relevant_count += 1
        
        # Display results
        relevance_emoji = "✅" if result.is_relevant else "❌"
        print(f"🎯 Result: {relevance_emoji} {result.relevance_level.value.upper()}")
        print(f"📊 Confidence: {result.confidence:.3f}")
        print(f"⚡ Method: {result.method.value}")
        print(f"⏱️  Processing: {result.processing_time_ms:.1f}ms")
        print(f"🏷️  Categories: {', '.join(result.matched_categories)}")
        print(f"🔍 Reasoning: {result.reasoning}")
        
        if result.response_suggestion:
            print(f"\n💬 Suggested Response:")
            print(result.response_suggestion)
    
    # Summary statistics
    print("\n" + "=" * 80)
    print("📊 PERFORMANCE SUMMARY")
    print("=" * 80)
    print(f"Total tests: {len(test_cases)}")
    print(f"Relevant questions: {relevant_count}/{len(test_cases)} ({relevant_count/len(test_cases)*100:.1f}%)")
    print(f"Average processing time: {total_time/len(test_cases):.1f}ms")
    print(f"Total processing time: {total_time:.1f}ms")
    
    # Performance breakdown
    fast_results = sum(1 for result in [await detector.classify(msg) for msg in test_cases[:3]] 
                      if result.processing_time_ms < 50)
    print(f"Fast classifications (< 50ms): {fast_results}")

if __name__ == "__main__":
    asyncio.run(test_hybrid_system())
