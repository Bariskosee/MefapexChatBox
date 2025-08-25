"""
🇹🇷 Gelişmiş Türkçe Content Manager
==================================
Daha iyi Türkçe yanıtlar için optimize edilmiş content yöneticisi
Morfological analysis ve lemmatization ile desteklenmiş

🚀 ULTRA PERFORMANCE OPTIMIZATION:
- Morphological analyzer ARTIK TAMAMEN LAZY LOADING ile yüklenir
- Eş anlamlı kelimeler sadece kullanıcı soru sorduğunda genişletilir  
- Başlangıç zamanı maksimum seviyede azaltıldı
- Kaynak tüketimi minimize edildi
- Zeyrek analyzer tamamen devre dışı bırakıldı

🔧 STRICT LAZY LOADING FEATURES:
- TurkishMorphAnalyzer: Sadece gerçek ihtiyaç anında yüklenir
- Synonym expansion: İlk soru işlendiğinde aktif olur
- Morphological enhancement: Tamamen on-demand olarak çalışır
- Hiçbir NLP tool otomatik olarak başlatılmaz

🔇 SILENT MODE OPTIMIZATION:
- Varsayılan log seviyesi ERROR olarak ayarlandı
- Ayrıntılı loglar sadece enable_detailed_logging=True ile görünür
- Gereksiz çıktılar tamamen elimine edildi
- Sessiz çalışma modu aktif
"""
import json
import re
import logging
import os
from typing import Dict, List, Tuple, Optional, Set
from difflib import SequenceMatcher

# Turkish NLP dependencies
try:
    import spacy
    from spacy.cli import download
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    spacy = None

# Alternative Turkish NLP libraries
try:
    from TurkishStemmer import TurkishStemmer
    TURKISH_STEMMER_AVAILABLE = True
except ImportError:
    TURKISH_STEMMER_AVAILABLE = False
    TurkishStemmer = None

# Zeyrek library - DISABLED due to verbose output and slow initialization
# ZEYREK COMPLETELY DISABLED TO PREVENT VERBOSE OUTPUT
ZEYREK_AVAILABLE = False
zeyrek = None

logger = logging.getLogger(__name__)

# Set default logging level to ERROR to minimize verbose output
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setLevel(logging.ERROR)
    formatter = logging.Formatter('%(levelname)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.ERROR)
    logger.propagate = False

class TurkishMorphAnalyzer:
    """
    Türkçe morfological analysis ve lemmatization sınıfı
    spaCy Turkish model kullanır
    """
    
    def __init__(self, enable_detailed_logging=False):
        self.nlp = None
        self.turkish_stemmer = None
        self.zeyrek_analyzer = None
        self.fallback_lemmas = self._load_fallback_lemmas()
        self.enable_detailed_logging = enable_detailed_logging
        self._lazy_init = False  # Lazy initialization için
        
        # Asla otomatik olarak initialize etme - sadece gerçekten gerektiğinde
        # Eski kod: if enable_detailed_logging: self._initialize_nlp_tools()
        # Bu satır kaldırıldı - artık hiçbir durumda otomatik init yok
    
    def _ensure_initialized(self):
        """Lazy initialization - sadece gerektiğinde NLP tools'ları yükle"""
        if not self._lazy_init:
            self._initialize_nlp_tools()
            self._lazy_init = True
    
    def _initialize_nlp_tools(self):
        """Initialize Turkish NLP tools with fallback options - ONLY when really needed"""
        # Sadece detailed logging etkinse debug mesajları göster
        if self.enable_detailed_logging:
            print("🔧 Initializing Turkish NLP tools...")
        
        # Try to initialize TurkishStemmer
        if TURKISH_STEMMER_AVAILABLE:
            try:
                self.turkish_stemmer = TurkishStemmer()
                if self.enable_detailed_logging:
                    print("✅ TurkishStemmer initialized successfully")
            except Exception as e:
                if self.enable_detailed_logging:
                    print(f"⚠️ Failed to initialize TurkishStemmer: {e}")
                
        # Try to initialize Zeyrek morphological analyzer - DISABLED to prevent verbose output
        # if ZEYREK_AVAILABLE:
        #     try:
        #         self.zeyrek_analyzer = zeyrek.MorphAnalyzer()
        #         if self.enable_detailed_logging:
        #             print("✅ Zeyrek morphological analyzer initialized successfully")
        #     except Exception as e:
        #         if self.enable_detailed_logging:
        #             print(f"⚠️ Failed to initialize Zeyrek: {e}")
        
        # Try to initialize spaCy as backup
        if SPACY_AVAILABLE:
            try:
                # Try to load Turkish model
                try:
                    self.nlp = spacy.load("tr_core_news_sm")
                    if self.enable_detailed_logging:
                        print("✅ Turkish spaCy model loaded successfully")
                except OSError:
                    # Model not found, try basic Turkish language support
                    if self.enable_detailed_logging:
                        print("⚠️ Turkish spaCy model (tr_core_news_sm) not found.")
                        print("🔄 Using basic Turkish language support")
                    try:
                        from spacy.lang.tr import Turkish
                        self.nlp = Turkish()
                        if self.enable_detailed_logging:
                            print("✅ Basic Turkish language support loaded")
                    except Exception as fallback_error:
                        if self.enable_detailed_logging:
                            print(f"⚠️ Could not load basic Turkish support: {fallback_error}")
                        self.nlp = None
            except Exception as e:
                if self.enable_detailed_logging:
                    print(f"❌ Error initializing spaCy: {e}")
                self.nlp = None
        
        # Report available tools - only if detailed logging enabled
        if self.enable_detailed_logging:
            available_tools = []
            if self.turkish_stemmer:
                available_tools.append("TurkishStemmer")
            if self.zeyrek_analyzer:
                available_tools.append("Zeyrek")
            if self.nlp:
                available_tools.append("spaCy")
            if available_tools:
                print(f"✅ Available Turkish NLP tools: {', '.join(available_tools)}")
            else:
                print("🔄 Using fallback morphological analysis with manual lemma dictionary")
                print("💡 To enhance Turkish analysis, install: pip install TurkishStemmer zeyrek")
    
    def _load_fallback_lemmas(self) -> Dict[str, str]:
        """Fallback lemma sözlüğü yükle"""
        return {
            # Fiiller (Verbs)
            'çalışıyor': 'çalış', 'çalışıyorum': 'çalış', 'çalışıyorsun': 'çalış',
            'çalışan': 'çalış', 'çalışmak': 'çalış', 'çalıştı': 'çalış',
            'gidiyor': 'git', 'gidiyorum': 'git', 'gitti': 'git', 'gitmek': 'git',
            'geliyor': 'gel', 'geliyorum': 'gel', 'geldi': 'gel', 'gelmek': 'gel',
            'yapıyor': 'yap', 'yapıyorum': 'yap', 'yaptı': 'yap', 'yapmak': 'yap',
            'oluyor': 'ol', 'oluyorum': 'ol', 'oldu': 'ol', 'olmak': 'ol',
            'istiyor': 'iste', 'istiyorum': 'iste', 'istedi': 'iste', 'istemek': 'iste',
            'başlıyor': 'başla', 'başlıyorum': 'başla', 'başladı': 'başla', 'başlamak': 'başla',
            'bitiyor': 'bit', 'bitiyorum': 'bit', 'bitti': 'bit', 'bitmek': 'bit',
            'açıyor': 'aç', 'açıyorum': 'aç', 'açtı': 'aç', 'açmak': 'aç',
            'kapıyor': 'kapa', 'kapıyorum': 'kapa', 'kapattı': 'kapa', 'kapamak': 'kapa',
            'alıyor': 'al', 'alıyorum': 'al', 'aldı': 'al', 'almak': 'al',
            'veriyor': 'ver', 'veriyorum': 'ver', 'verdi': 'ver', 'vermek': 'ver',
            'buluyor': 'bul', 'buluyorum': 'bul', 'buldu': 'bul', 'bulmak': 'bul',
            'düşünüyor': 'düşün', 'düşünüyorum': 'düşün', 'düşündü': 'düşün',
            'konuşuyor': 'konuş', 'konuşuyorum': 'konuş', 'konuştu': 'konuş',
            'çalışması': 'çalış', 'çalışmasını': 'çalış', 'çalışmasına': 'çalış',
            
            # İsimler (Nouns) - Çoğul ve hal ekleri
            'saatleri': 'saat', 'saatler': 'saat', 'saatin': 'saat', 'saate': 'saat',
            'günleri': 'gün', 'günler': 'gün', 'günün': 'gün', 'güne': 'gün',
            'işleri': 'iş', 'işler': 'iş', 'işin': 'iş', 'işe': 'iş',
            'sorunları': 'sorun', 'sorunlar': 'sorun', 'sorunun': 'sorun', 'soruna': 'sorun',
            'hataları': 'hata', 'hatalar': 'hata', 'hatanın': 'hata', 'hataya': 'hata',
            'sistemleri': 'sistem', 'sistemler': 'sistem', 'sistemin': 'sistem', 'sisteme': 'sistem',
            'bilgileri': 'bilgi', 'bilgiler': 'bilgi', 'bilginin': 'bilgi', 'bilgiye': 'bilgi',
            'desteği': 'destek', 'destekler': 'destek', 'desteğin': 'destek', 'desteğe': 'destek',
            'güvenliği': 'güvenlik', 'güvenlikler': 'güvenlik', 'güvenliğin': 'güvenlik',
            'personeli': 'personel', 'personeller': 'personel', 'personelin': 'personel',
            'projesi': 'proje', 'projeler': 'proje', 'projenin': 'proje', 'projeye': 'proje',
            'eğitimi': 'eğitim', 'eğitimler': 'eğitim', 'eğitimin': 'eğitim', 'eğitime': 'eğitim',
            'kullanıcısı': 'kullanıcı', 'kullanıcılar': 'kullanıcı', 'kullanıcının': 'kullanıcı',
            
            # Sıfatlar (Adjectives)
            'iyi': 'iyi', 'iyiler': 'iyi', 'iyidir': 'iyi', 'iyiyi': 'iyi',
            'kötü': 'kötü', 'kötüler': 'kötü', 'kötüdür': 'kötü', 'kötüyü': 'kötü',
            'hızlı': 'hızlı', 'hızlılar': 'hızlı', 'hızlıdır': 'hızlı',
            'yavaş': 'yavaş', 'yavaşlar': 'yavaş', 'yavaştır': 'yavaş',
            'kolay': 'kolay', 'kolaylar': 'kolay', 'kolaydır': 'kolay',
            'zor': 'zor', 'zorlar': 'zor', 'zordur': 'zor',
            'yeni': 'yeni', 'yeniler': 'yeni', 'yenidir': 'yeni',
            'eski': 'eski', 'eskiler': 'eski', 'eskidir': 'eski',
            'büyük': 'büyük', 'büyükler': 'büyük', 'büyüktür': 'büyük',
            'küçük': 'küçük', 'küçükler': 'küçük', 'küçüktür': 'küçük',
            
            # Zamanlar (Time expressions)
            'bugün': 'bugün', 'bugünü': 'bugün', 'bugüne': 'bugün',
            'yarın': 'yarın', 'yarını': 'yarın', 'yarına': 'yarın',
            'dün': 'dün', 'dünü': 'dün', 'düne': 'dün',
            'şimdi': 'şimdi', 'şimdiyi': 'şimdi', 'şimdiye': 'şimdi',
            'sonra': 'sonra', 'sonrası': 'sonra', 'sonrasına': 'sonra',
            'önce': 'önce', 'öncesi': 'önce', 'öncesine': 'önce',
        }
    
    def lemmatize_word(self, word: str) -> str:
        """Tek kelimeyi lemmatize et using multiple Turkish NLP tools"""
        if not word:
            return word
        
        # Sadece gerektiğinde initialize et
        self._ensure_initialized()
        
        word_lower = word.lower()
        
        # ZEYREK DISABLED to prevent verbose output
        # Try Zeyrek morphological analyzer first (most accurate) - DISABLED
        # if self.zeyrek_analyzer:
        #     try:
        #         analysis = self.zeyrek_analyzer.analyze(word_lower)
        #         if analysis and len(analysis) > 0:
        #             lemma = analysis[0][1].lemma
        #             if lemma and lemma != word_lower:
        #                 if self.enable_detailed_logging:
        #                     print(f"Zeyrek lemmatization: '{word}' → '{lemma}'")
        #                 return lemma
        #     except Exception as e:
        #         if self.enable_detailed_logging:
        #             print(f"Zeyrek lemmatization error for '{word}': {e}")
        
        # Try TurkishStemmer (good for stemming)
        if self.turkish_stemmer:
            try:
                stem = self.turkish_stemmer.stem(word_lower)
                if stem and stem != word_lower and len(stem) >= 2:
                    if self.enable_detailed_logging:
                        print(f"TurkishStemmer: '{word}' → '{stem}'")
                    return stem
            except Exception as e:
                if self.enable_detailed_logging:
                    print(f"TurkishStemmer error for '{word}': {e}")
        
        # Try spaCy (if available) - with minimal logging
        if self.nlp:
            try:
                doc = self.nlp(word_lower)
                if doc and len(doc) > 0:
                    lemma = doc[0].lemma_
                    if lemma and lemma != word_lower:
                        if self.enable_detailed_logging:
                            print(f"spaCy lemmatization: '{word}' → '{lemma}'")
                        return lemma
            except Exception as e:
                if self.enable_detailed_logging:
                    print(f"spaCy lemmatization error for '{word}': {e}")
        
        # Fallback lemma sözlüğünü kullan
        if word_lower in self.fallback_lemmas:
            if self.enable_detailed_logging:
                print(f"Fallback lemma: '{word}' → '{self.fallback_lemmas[word_lower]}'")
            return self.fallback_lemmas[word_lower]
        
        # Temel morfological rules
        basic_result = self._apply_basic_rules(word_lower)
        if basic_result != word_lower and self.enable_detailed_logging:
            print(f"Basic rules: '{word}' → '{basic_result}'")
        return basic_result
    
    def _apply_basic_rules(self, word: str) -> str:
        """Temel morfological kuralları uygula"""
        if len(word) < 3:
            return word
        
        # Çoğul ekleri (-ler, -lar)
        if word.endswith(('ler', 'lar')):
            base = word[:-3]
            if len(base) >= 2:
                return base
        
        # İyelik ekleri (-i, -ı, -u, -ü)
        if word.endswith(('ları', 'leri', 'ları', 'leri')):
            base = word[:-4]
            if len(base) >= 2:
                return base
        
        # Hal ekleri
        if word.endswith(('nın', 'nin', 'nun', 'nün')):
            base = word[:-3]
            if len(base) >= 2:
                return base
        
        if word.endswith(('na', 'ne', 'ya', 'ye')):
            base = word[:-2]
            if len(base) >= 2:
                return base
        
        # Fiil ekleri
        if word.endswith(('ıyor', 'iyor', 'uyor', 'üyor')):
            base = word[:-4]
            if len(base) >= 2:
                return base
        
        if word.endswith(('mak', 'mek')):
            base = word[:-3]
            if len(base) >= 2:
                return base
        
        return word
    
    def lemmatize_text(self, text: str) -> str:
        """Metindeki tüm kelimeleri lemmatize et"""
        if not text:
            return text
        
        words = text.split()
        lemmatized_words = []
        
        for word in words:
            # Noktalama işaretlerini ayır
            clean_word = re.sub(r'[^\w\s]', '', word)
            if clean_word:
                lemma = self.lemmatize_word(clean_word)
                lemmatized_words.append(lemma)
        
        return ' '.join(lemmatized_words)
    
    def get_word_variants(self, word: str) -> Set[str]:
        """Bir kelimenin farklı varyantlarını üret"""
        variants = {word.lower()}
        lemma = self.lemmatize_word(word)
        variants.add(lemma)
        
        # Temel varyantlar ekle
        if lemma in self.fallback_lemmas.values():
            # Bu lemma için bilinen tüm formları bul
            for inflected, base in self.fallback_lemmas.items():
                if base == lemma:
                    variants.add(inflected)
        
        return variants

logger = logging.getLogger(__name__)

class ImprovedTurkishContentManager:
    """
    Gelişmiş Türkçe content yöneticisi
    - Daha kapsamlı static responses
    - On-demand morfological analysis ile gelişmiş matching
    - Türkçe karakter desteği
    - Lemmatization ile akıllı eşleştirme
    - Akıllı fallback responses
    """
    
    def __init__(self, enable_detailed_logging=False):
        # İlk önce tüm özellikleri ata
        self.enable_detailed_logging = enable_detailed_logging
        self.pattern_cache = {}
        
        # Lazy loading için morphological analyzer'ı None olarak başlat
        self.morph_analyzer = None
        self.responses = self._load_enhanced_responses()
        
        # Eş anlamlı kelimeleri de lazy loading ile yükle
        self._synonym_map = None
        self._synonyms_loaded = False
        self._synonyms_enhanced = False  # Morfological genişletme yapıldı mı?
        
        # Sadece detailed logging aktifse bu mesajı göster
        if enable_detailed_logging:
            print("🇹🇷 Enhanced Turkish Content Manager with lazy morphological analysis initialized")
        # Sessiz mod - hiç log gösterme
    
    @property
    def synonym_map(self):
        """Lazy loading property for synonym map"""
        if not self._synonyms_loaded:
            # Sadece detailed logging etkinse mesaj göster
            if self.enable_detailed_logging:
                print("🔧 Loading synonyms on-demand...")
            self._synonym_map = self._load_synonyms_from_file()
            self._synonyms_loaded = True
        return self._synonym_map
    
    def _get_morph_analyzer(self):
        """Lazy loading: Sadece gerektiğinde morphological analyzer'ı oluştur"""
        if self.morph_analyzer is None:
            # Sadece detailed logging etkinse mesaj göster
            if self.enable_detailed_logging:
                print("🔧 Creating morphological analyzer on-demand...")
            self.morph_analyzer = TurkishMorphAnalyzer(enable_detailed_logging=self.enable_detailed_logging)
        return self.morph_analyzer
    
    def _load_synonyms_from_file(self) -> Dict[str, List[str]]:
        """synonyms.json dosyasından eş anlamlı kelimeleri yükle"""
        try:
            # Önce mevcut dizinde ara
            synonyms_path = "content/synonyms.json"
            if not os.path.exists(synonyms_path):
                # Alternatif yolları dene
                possible_paths = [
                    "./content/synonyms.json",
                    "../content/synonyms.json",
                    "/Users/bariskose/Downloads/MefapexChatBox-main/content/synonyms.json"
                ]
                for path in possible_paths:
                    if os.path.exists(path):
                        synonyms_path = path
                        break
            
            with open(synonyms_path, 'r', encoding='utf-8') as f:
                loaded_synonyms = json.load(f)
            
            # İlk yüklemede sadece basit synonyms'ları kullan
            # Morfological genişletme ilk kullanımda yapılacak
            simple_synonyms = {}
            for base_word, synonyms in loaded_synonyms.items():
                # Sadece temel kelimeleri ekle, morfological analiz yapmadan
                all_variants = set()
                all_variants.add(base_word.lower())
                
                for synonym in synonyms:
                    all_variants.add(synonym.lower())
                
                # Boş stringleri filtrele
                all_variants = [v for v in all_variants if v and len(v) > 1]
                simple_synonyms[base_word.lower()] = list(all_variants)
            
            # Sadece detailed logging etkinse bu mesajı göster
            if self.enable_detailed_logging:
                print(f"📚 Loaded {len(simple_synonyms)} synonym groups from file (basic mode)")
            return simple_synonyms
            
        except Exception as e:
            # Sadece detailed logging etkinse warning göster
            if self.enable_detailed_logging:
                print(f"⚠️ Could not load synonyms from file: {e}")
            return self._create_basic_synonym_map()  # Fallback to hardcoded synonyms
    
    def _create_basic_synonym_map(self) -> Dict[str, List[str]]:
        """Fallback: Türkçe eş anlamlı kelimeler (hard-coded, basic mode)"""
        return {
            'çalış': ['iş', 'mesai', 'görev', 'vazife', 'work', 'job', 'çalışma'],
            'saat': ['zaman', 'vakit', 'time', 'hours', 'hour'],
            'aç': ['open', 'başla', 'start', 'begin', 'açık'],
            'kapa': ['closed', 'bit', 'end', 'finish', 'stop', 'kapalı'],
            'destek': ['yardım', 'help', 'support', 'assistance', 'aid'],
            'sorun': ['problem', 'hata', 'error', 'issue', 'bug'],
            'mefapex': ['şirket', 'company', 'firma', 'organization', 'kurum'],
            'güvenlik': ['security', 'safety', 'emniyet', 'koruma'],
            'izin': ['leave', 'vacation', 'tatil', 'permit', 'permission'],
            'proje': ['project', 'görev', 'task', 'iş', 'work'],
            'eğitim': ['training', 'education', 'kurs', 'course', 'öğretim'],
            'sistem': ['system', 'software', 'yazılım', 'program'],
            'hata': ['error', 'bug', 'problem', 'sorun', 'issue'],
            'yardım': ['help', 'support', 'destek', 'assistance']
        }
    
    def _load_enhanced_responses(self) -> Dict:
        """Gelişmiş Türkçe yanıtlar yükle"""
        return {
            "greeting": {
                "patterns": [
                    "merhaba", "selam", "selamlar", "selamun aleyküm", "günaydın", 
                    "iyi günler", "iyi akşamlar", "iyi geceler", "nasılsın", 
                    "nasıl gidiyor", "naber", "hello", "hi", "hey"
                ],
                "responses": [
                    "🙋‍♂️ **Merhaba! Hoş geldiniz MEFAPEX'e!**\n\nBen sizin AI asistanınızım. Size şu konularda yardımcı olabilirim:\n\n• 🏭 **Fabrika Operasyonları**: Çalışma saatleri, vardiya bilgileri\n• 💻 **Teknik Destek**: Yazılım, sistem ve IT sorunları\n• 👥 **İnsan Kaynakları**: İzin başvuruları, personel işlemleri\n• 🛡️ **Güvenlik**: İş güvenliği kuralları ve prosedürler\n• 🏢 **Şirket Bilgileri**: MEFAPEX hizmetleri ve politikaları\n\nSorularınızı bekliyorum! 😊",
                    
                    "👋 **Hoş geldiniz!**\n\nMEFAPEX Bilişim Teknolojileri'nin AI asistanıyım. Size nasıl yardımcı olabilirim?\n\n**Popüler Sorular:**\n• \"Çalışma saatleri nelerdir?\"\n• \"Teknik destek nasıl alabilirim?\"\n• \"İzin başvurusu nasıl yapılır?\"\n• \"Güvenlik kuralları nelerdir?\"\n\nDetaylı bilgi için sorunuzu yazabilirsiniz! 🚀"
                ]
            },
            
            "working_hours": {
                "patterns": [
                    "çalışma saat", "iş saat", "mesai", "vardiya", "kaçta açık", 
                    "kaçta kapalı", "ne zaman açık", "working hours", "office hours",
                    "çalışma zamanı", "iş zamanı", "açılış", "kapanış", "ofis saat"
                ],
                "responses": [
                    "⏰ **MEFAPEX Çalışma Saatleri**\n\n**📅 Hafta İçi Çalışma:**\n• Pazartesi - Cuma: 09:00 - 18:00\n• Öğle molası: 12:00 - 13:00\n\n**📅 Hafta Sonu:**\n• Cumartesi: 09:00 - 13:00 (Yarım gün)\n• Pazar: Kapalı\n\n**🚨 Acil Durumlar:**\n• 7/24 teknik destek hattı\n• Kritik sistem arızaları için anında müdahale\n\n**📞 İletişim:**\n• Ana hat: [Telefon numarası]\n• Acil: [Acil telefon]\n• Email: info@mefapex.com",
                    
                    "🕘 **İş Saatleri ve Vardiya Bilgileri**\n\n**Standart Mesai:**\n• Başlangıç: 09:00\n• Bitiş: 18:00\n• Toplam: 8 saat + 1 saat mola\n\n**Mola Saatleri:**\n• Öğle arası: 12:00-13:00\n• Çay molası: 10:00 ve 15:30\n\n**Esnek Çalışma:**\n• Uzaktan çalışma imkanı\n• Esnek başlangıç saatleri (08:00-10:00)\n\nDetaylı bilgi için İK departmanıyla iletişime geçin."
                ]
            },
            
            "technical_support": {
                "patterns": [
                    "teknik destek", "technical support", "yardım", "help", "problem", 
                    "sorun", "hata", "error", "arıza", "breakdown", "sistem", "yazılım",
                    "bilgisayar", "network", "ağ", "server", "sunucu"
                ],
                "responses": [
                    "🛠️ **MEFAPEX Teknik Destek**\n\n**📞 Anında Destek:**\n• Teknik Destek Hattı: [Telefon]\n• Email: destek@mefapex.com\n• Canlı Chat: Bu platform üzerinden\n\n**🔧 Destek Türleri:**\n• **Yazılım Desteği**: Uygulama hataları, güncelleme\n• **Sistem Desteği**: Sunucu, ağ altyapısı\n• **Acil Müdahale**: Kritik sistem çökmeleri\n• **Kullanıcı Eğitimi**: Sistem kullanım rehberi\n\n**⏱️ Yanıt Süreleri:**\n• Acil: 15 dakika\n• Normal: 2 saat\n• Planlı: 24 saat\n\nProbleminizi detaylandırın, hemen yardımcı olalım! 🚀",
                    
                    "💻 **IT Destek ve Çözümler**\n\n**Hızlı Çözümler:**\n• Şifre sıfırlama: [Link]\n• VPN kurulumu: [Rehber]\n• Email ayarları: [Kılavuz]\n\n**Acil Durumlar:**\n• Sistem çökmesi ➜ Hemen arayın\n• Güvenlik ihlali ➜ Acil bildirim\n• Veri kaybı ➜ Backup kurtarma\n\n**📱 Uzaktan Destek:**\n• TeamViewer bağlantısı\n• Ekran paylaşımı\n• Canlı rehberlik\n\nSorununuzu açıklayın, çözüm bulalım!"
                ]
            },
            
            "company_info": {
                "patterns": [
                    "mefapex", "şirket", "company", "firma", "hakkında", "about", 
                    "bilişim teknolojileri", "nedir", "ne yapıyor", "hizmet",
                    "teknoloji", "yazılım geliştirme"
                ],
                "responses": [
                    "🏢 **MEFAPEX Bilişim Teknolojileri**\n\n**🎯 Misyonumuz:**\nModern teknoloji çözümleri ile işletmelerin dijital dönüşümünde öncü olmak\n\n**💼 Hizmet Alanlarımız:**\n• **🖥️ Yazılım Geliştirme**: Web, mobil, masaüstü uygulamalar\n• **☁️ Bulut Çözümleri**: AWS, Azure, Google Cloud\n• **🔒 Siber Güvenlik**: Penetrasyon testleri, güvenlik danışmanlığı\n• **📊 Veri Analizi**: Big Data, Business Intelligence\n• **🤖 Yapay Zeka**: Machine Learning, chatbot geliştirme\n• **🌐 Sistem Entegrasyonu**: ERP, CRM sistemleri\n\n**🌟 Neden MEFAPEX?**\n• 10+ yıl tecrübe\n• ISO 27001 sertifikalı\n• 7/24 destek\n• Yenilikçi çözümler",
                    
                    "🚀 **MEFAPEX: Teknolojide Güvenilir Çözüm Ortağınız**\n\n**📈 Başarı Hikayeleri:**\n• 500+ tamamlanan proje\n• %98 müşteri memnuniyeti\n• 50+ teknoloji uzmanı\n\n**🏆 Sertifikalar:**\n• ISO 9001 Kalite Yönetimi\n• ISO 27001 Bilgi Güvenliği\n• Microsoft Partner\n• AWS Partner Network\n\n**📍 İletişim:**\n• Merkez: İstanbul\n• Şubeler: Ankara, İzmir\n• Web: www.mefapex.com\n• Email: info@mefapex.com\n\nDaha detaylı bilgi için bizimle iletişime geçin!"
                ]
            },
            
            "hr_processes": {
                "patterns": [
                    "izin", "leave", "tatil", "vacation", "başvuru", "application",
                    "personel", "ik", "human resources", "özlük", "bordro", "maaş"
                ],
                "responses": [
                    "👥 **İnsan Kaynakları Süreçleri**\n\n**📝 İzin Başvuruları:**\n• Yıllık izin: Online sistem üzerinden\n• Mazeret izni: Üst amir onayı ile\n• Hastalık izni: Rapor ibrazı\n\n**📋 Gerekli Belgeler:**\n• İzin formu (doldurulmuş)\n• Varsa tıbbi rapor\n• Üst amir onayı\n\n**⏱️ Başvuru Süreleri:**\n• Yıllık izin: 15 gün önceden\n• Acil izin: Amir onayı ile\n\n**📞 İK İletişim:**\n• İK Departmanı: [Telefon]\n• Email: ik@mefapex.com\n• Ofis: Ana bina 2. kat\n\nDetaylı bilgi için İK departmanımızla iletişime geçin.",
                    
                    "📊 **Personel İşlemleri ve Haklar**\n\n**💰 Maaş ve Ödemeler:**\n• Bordro: Her ayın 30'u\n• Prim ödemeleri: Performansa göre\n• Yan haklar: Yemek, ulaşım, sağlık\n\n**🎓 Eğitim ve Gelişim:**\n• Teknik kurslar\n• Sertifikasyon programları\n• Konferans katılımları\n\n**🏥 Sosyal Haklar:**\n• Özel sağlık sigortası\n• Yemek kartı\n• Ulaşım desteği\n• Spor üyeliği\n\nKişisel dosyanız için İK'ya başvurun."
                ]
            },
            
            "security_safety": {
                "patterns": [
                    "güvenlik", "security", "safety", "kural", "rule", "kaza", "accident",
                    "acil", "emergency", "koruyucu", "protective", "kask", "helmet"
                ],
                "responses": [
                    "🛡️ **İş Güvenliği Kuralları**\n\n**⚠️ Zorunlu Koruyucu Ekipmanlar:**\n• 🦺 Reflektif yelek\n• 👷 Güvenlik kaskı\n• 👟 Güvenlik ayakkabısı\n• 🧤 İş eldivenleri\n• 🥽 Koruyucu gözlük\n\n**🚨 Acil Durum Prosedürleri:**\n• Yangın: Alarm çal, binayı boşalt\n• Kaza: İlk yardım, 112'yi ara\n• Güvenlik ihlali: Güvenliği bilgilendir\n\n**📞 Acil Numaralar:**\n• İtfaiye: 110\n• Ambulans: 112\n• Polis: 155\n• İç hat güvenlik: [Dahili]\n\n**📋 Güvenlik Eğitimleri:**\n• Aylık güvenlik toplantıları\n• İlk yardım sertifikası\n• Yangın tatbikatları",
                    
                    "🔒 **Güvenlik Protokolleri ve Önlemler**\n\n**🏭 Fabrika Güvenliği:**\n• Makine çalışırken yaklaşma\n• Güvenlik bariyerlerine uy\n• Uyarı levhalarını oku\n• Temizlik maddelerini dikkatli kullan\n\n**💻 Bilgi Güvenliği:**\n• Güçlü şifreler kullan\n• 2FA (iki faktörlü doğrulama) aktif et\n• Şüpheli emailleri açma\n• USB cihazları kontrol et\n\n**🆔 Erişim Güvenliği:**\n• Kartını başkasına verme\n• Kapıları arkandan kitle\n• Ziyaretçileri kaydet\n\nGüvenlik sizin sorumluluğunuz!"
                ]
            },
            
            "thanks_goodbye": {
                "patterns": [
                    "teşekkür", "thanks", "sağol", "thank you", "bye", "görüşürüz",
                    "hoşça kal", "goodbye", "elveda", "iyi günler"
                ],
                "responses": [
                    "🙏 **Rica ederim!**\n\nSize yardımcı olabildiysem ne mutlu bana! \n\n**📞 İhtiyaç halinde:**\n• Teknik destek: destek@mefapex.com\n• Genel bilgi: info@mefapex.com\n• Acil durumlar: [Acil telefon]\n\nBaşka sorularınız olduğunda her zaman buradayım.\n\n✨ **MEFAPEX ailesinin bir parçası olduğunuz için teşekkürler!**\n\nİyi çalışmalar dilerim! 🌟",
                    
                    "😊 **Her zaman yardımcı olmaktan mutluluk duyarım!**\n\nUmarım sorularınıza faydalı yanıtlar verebildim.\n\n**🔗 Bağlantıda Kalın:**\n• Web: www.mefapex.com\n• LinkedIn: MEFAPEX Bilişim\n• Email: info@mefapex.com\n\n**💡 İpucu:** Favorilerinize ekleyerek bana daha kolay ulaşabilirsiniz!\n\nGörüşürüz! 👋"
                ]
            },
            
            # Yeni kategoriler
            "project_management": {
                "patterns": [
                    "proje", "project", "görev", "task", "deadline", "son tarih",
                    "teslim", "delivery", "milestone", "plan", "planlama"
                ],
                "responses": [
                    "📋 **Proje Yönetimi ve Süreçler**\n\n**🎯 Proje Aşamaları:**\n• **Analiz**: İhtiyaç belirleme ve dokümantasyon\n• **Tasarım**: Sistem mimarisi ve UI/UX\n• **Geliştirme**: Kodlama ve test süreçleri\n• **Test**: QA ve kullanıcı testleri\n• **Teslim**: Canlıya alma ve eğitim\n\n**📊 Proje Takibi:**\n• Haftalık durum raporları\n• Sprint toplantıları\n• Milestone değerlendirmeleri\n\n**🔧 Kullanılan Araçlar:**\n• Jira - Görev yönetimi\n• Confluence - Dokümantasyon\n• Git - Versiyon kontrolü\n• Slack - İletişim\n\nProje durumunuz için proje yöneticisiyle iletişime geçin."
                ]
            },
            
            "training_education": {
                "patterns": [
                    "eğitim", "training", "kurs", "course", "öğren", "learn",
                    "sertifika", "certificate", "rehber", "guide", "nasıl"
                ],
                "responses": [
                    "🎓 **Eğitim ve Gelişim Programları**\n\n**💻 Teknik Eğitimler:**\n• **Programlama**: Python, JavaScript, C#\n• **Veritabanı**: SQL, MongoDB, PostgreSQL\n• **Bulut**: AWS, Azure, Google Cloud\n• **DevOps**: Docker, Kubernetes, CI/CD\n\n**📚 Kişisel Gelişim:**\n• Proje yönetimi\n• İletişim becerileri\n• Liderlik eğitimleri\n• Agile metodolojiler\n\n**🏆 Sertifikasyon Desteği:**\n• Sınav ücretleri karşılanır\n• Hazırlık kursları\n• Mentorluk programı\n\n**📞 Eğitim Koordinatörü:**\n• Email: egitim@mefapex.com\n• Dahili: [Telefon]\n\nKariyerinizi geliştirmek için bizimle iletişime geçin!"
                ]
            }
        }
    
    def _enhance_synonyms_with_morphology(self):
        """İlk soru işlendiğinde eş anlamlıları morfological analiz ile genişlet - ONLY when user asks a question"""
        if not hasattr(self, '_synonyms_enhanced') or not self._synonyms_enhanced:
            # Sadece detailed logging etkinse mesaj göster
            if self.enable_detailed_logging:
                print("🔧 Enhancing synonyms with morphological analysis...")
            
            # Önce synonyms'ları yükle (eğer yüklenmemişse)
            if not self._synonyms_loaded:
                # synonym_map property'sini çağırarak lazy loading'i tetikle
                _ = self.synonym_map
            
            # Mevcut synonym map'i al
            current_synonyms = dict(self._synonym_map)  # Copy to avoid modification during iteration
            enhanced_synonyms = {}
            
            # Morfological analyzer'ı al - bu da lazy loading ile çalışır
            morph_analyzer = self._get_morph_analyzer()
            
            for base_word, synonyms in current_synonyms.items():
                # Base word'ü lemmatize et
                base_lemma = morph_analyzer.lemmatize_word(base_word)
                
                # Tüm eş anlamlıları lemmatize et ve varyantlarını ekle
                all_variants = set()
                all_variants.add(base_word)
                all_variants.add(base_lemma)
                
                for synonym in synonyms:
                    all_variants.add(synonym)
                    synonym_lemma = morph_analyzer.lemmatize_word(synonym)
                    all_variants.add(synonym_lemma)
                    
                    # Kelime varyantlarını da ekle - sadece gerekirse
                    try:
                        variants = morph_analyzer.get_word_variants(synonym)
                        all_variants.update(variants)
                    except Exception as e:
                        # Hataları sessizce geç - verbose logging yok
                        pass
                
                # Boş stringleri filtrele
                all_variants = [v for v in all_variants if v and len(v) > 1]
                
                enhanced_synonyms[base_lemma] = list(all_variants)
                
                # Orijinal kelimenin kendisi için de entry ekle
                if base_word != base_lemma:
                    enhanced_synonyms[base_word] = list(all_variants)
            
            # Enhanced synonyms'ı güncelle
            self._synonym_map = enhanced_synonyms
            self._synonyms_enhanced = True
            
            # Sadece detailed logging etkinse sonuç mesajı göster
            if self.enable_detailed_logging:
                print(f"✅ Enhanced {len(enhanced_synonyms)} synonym groups with morphological analysis")
    
    def _normalize_turkish(self, text: str) -> str:
        """Türkçe karakterleri normalize et ve morfological analysis uygula"""
        if not text:
            return text
        
        # Önce türkçe karakter dönüşümleri
        turkish_map = {
            'ç': 'c', 'ğ': 'g', 'ı': 'i', 'ö': 'o', 'ş': 's', 'ü': 'u',
            'Ç': 'c', 'Ğ': 'g', 'I': 'i', 'İ': 'i', 'Ö': 'o', 'Ş': 's', 'Ü': 'u'
        }
        
        normalized = ""
        for char in text.lower():
            normalized += turkish_map.get(char, char)
        
        return normalized
    
    def _preprocess_text(self, text: str) -> str:
        """Metni önişleme: temizleme + normalizasyon + lemmatization"""
        if not text:
            return text
        
        # Temizleme
        text = text.strip().lower()
        text = re.sub(r'[^\w\s]', ' ', text)  # Noktalama işaretlerini kaldır
        text = re.sub(r'\s+', ' ', text)  # Çoklu boşlukları tek boşluğa çevir
        
        # Lemmatization (lazy loading ile)
        morph_analyzer = self._get_morph_analyzer()
        lemmatized_text = morph_analyzer.lemmatize_text(text)
        
        # Türkçe karakter normalizasyonu (son adım olarak)
        normalized_text = self._normalize_turkish(lemmatized_text)
        
        return normalized_text
    
    def _expand_with_synonyms(self, text: str) -> List[str]:
        """Metni eş anlamlı kelimelerle ve morfological varyantlarla genişlet"""
        # İlk kullanımda morfological genişletmeyi yap
        self._enhance_synonyms_with_morphology()
        
        words = text.split()
        expanded_texts = {text}  # Set kullanarak dublicate'leri önle
        
        # Lazy loading ile morphological analyzer'ı al
        morph_analyzer = self._get_morph_analyzer()
        
        # Her kelime için eş anlamlıları ve varyantlarını kontrol et
        for word in words:
            # Kelimeyi lemmatize et
            lemma = morph_analyzer.lemmatize_word(word)
            
            # Normalized versiyonları da kontrol et
            normalized_word = self._normalize_turkish(word)
            normalized_lemma = self._normalize_turkish(lemma)
            
            # Eş anlamlıları bul
            synonyms_found = set()
            
            # Orijinal kelime için eş anlamlıları
            for key in [word, lemma, normalized_word, normalized_lemma]:
                if key in self.synonym_map:
                    synonyms_found.update(self.synonym_map[key])
            
            # Morfological varyantları da ekle
            variants = morph_analyzer.get_word_variants(word)
            for variant in variants:
                normalized_variant = self._normalize_turkish(variant)
                for key in [variant, normalized_variant]:
                    if key in self.synonym_map:
                        synonyms_found.update(self.synonym_map[key])
            
            # Bulunan eş anlamlıları ile yeni metinler oluştur
            for synonym in synonyms_found:
                if synonym and synonym != word:
                    # Orijinal kelimeyi eş anlamlısıyla değiştir
                    new_text = text.replace(word, synonym)
                    expanded_texts.add(new_text)
                    
                    # Lemmatized versiyonlarını da dene
                    lemma_text = text.replace(word, morph_analyzer.lemmatize_word(synonym))
                    expanded_texts.add(lemma_text)
        
        return list(expanded_texts)
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """İki metin arasında morfological analysis destekli benzerlik hesapla"""
        # Cache kontrolü
        cache_key = f"{text1}|{text2}"
        if cache_key in self.pattern_cache:
            return self.pattern_cache[cache_key]
        
        # Metinleri önişle
        processed1 = self._preprocess_text(text1)
        processed2 = self._preprocess_text(text2)
        
        # Temel benzerlik
        basic_similarity = SequenceMatcher(None, processed1, processed2).ratio()
        
        # Kelime bazlı benzerlik (lemmatized)
        words1 = set(processed1.split())
        words2 = set(processed2.split())
        
        if not words1 or not words2:
            similarity = basic_similarity
        else:
            # Exact match
            word_similarity = len(words1 & words2) / len(words1 | words2)
            
            # Semantic similarity (synonym-based)
            semantic_matches = 0
            total_comparisons = 0
            
            for w1 in words1:
                for w2 in words2:
                    total_comparisons += 1
                    if w1 == w2:
                        semantic_matches += 1
                    else:
                        # Check if words are synonyms
                        w1_synonyms = set()
                        w2_synonyms = set()
                        
                        # Collect synonyms for w1
                        for key, synonyms in self.synonym_map.items():
                            if w1 in synonyms or w1 == key:
                                w1_synonyms.update(synonyms)
                                w1_synonyms.add(key)
                        
                        # Collect synonyms for w2
                        for key, synonyms in self.synonym_map.items():
                            if w2 in synonyms or w2 == key:
                                w2_synonyms.update(synonyms)
                                w2_synonyms.add(key)
                        
                        # Check if there's overlap
                        if w1_synonyms & w2_synonyms:
                            semantic_matches += 0.8  # Synonym match weight
            
            if total_comparisons > 0:
                semantic_similarity = semantic_matches / total_comparisons
            else:
                semantic_similarity = 0
            
            # Ağırlıklı ortalama
            similarity = (basic_similarity * 0.4) + (word_similarity * 0.4) + (semantic_similarity * 0.2)
        
        # Cache'e kaydet
        self.pattern_cache[cache_key] = similarity
        return similarity
    
    def find_best_match(self, user_input: str, threshold: float = 0.3) -> Optional[Dict]:
        """Kullanıcı girdisi için en iyi eşleşmeyi bul (morfological analysis ile)"""
        if not user_input or not user_input.strip():
            return None
        
        # Kullanıcı girdisini önişle
        processed_input = self._preprocess_text(user_input)
        
        best_match = None
        best_score = 0.0
        
        # Eş anlamlı kelimelerle ve morfological varyantlarla genişletilmiş versiyonları da kontrol et
        expanded_inputs = self._expand_with_synonyms(processed_input)
        
        # Orijinal girdiyi de ekle
        all_inputs = [user_input.strip().lower(), processed_input] + expanded_inputs
        all_inputs = list(set(all_inputs))  # Duplicate'leri kaldır
        
        for category, data in self.responses.items():
            patterns = data["patterns"]
            responses = data["responses"]
            
            for pattern in patterns:
                # Pattern'i de önişle
                processed_pattern = self._preprocess_text(pattern)
                
                # Tüm girdi versiyonlarını kontrol et
                for input_variant in all_inputs:
                    # Direkt içerme kontrolü (yüksek puan)
                    if processed_pattern in input_variant or input_variant in processed_pattern:
                        score = 0.95
                    elif pattern.lower() in user_input.lower() or user_input.lower() in pattern.lower():
                        score = 0.9  # Orijinal metin eşleşmesi
                    else:
                        # Morfological similarity
                        score = self._calculate_similarity(input_variant, processed_pattern)
                    
                    if score > best_score and score >= threshold:
                        best_score = score
                        best_match = {
                            "category": category,
                            "pattern": pattern,
                            "responses": responses,
                            "score": score,
                            "matched_input": input_variant,
                            "processed_pattern": processed_pattern
                        }
        
        # Eğer hala eşleşme yoksa, daha esnek arama yap
        if not best_match or best_score < 0.5:
            # Lemmatized kelime bazlı arama
            input_lemmas = set(self._preprocess_text(user_input).split())
            
            for category, data in self.responses.items():
                patterns = data["patterns"]
                responses = data["responses"]
                
                for pattern in patterns:
                    pattern_lemmas = set(self._preprocess_text(pattern).split())
                    
                    if input_lemmas and pattern_lemmas:
                        # Lemma intersection score
                        intersection = len(input_lemmas & pattern_lemmas)
                        union = len(input_lemmas | pattern_lemmas)
                        
                        if union > 0:
                            lemma_score = intersection / union
                            
                            # Bonus for multiple word matches
                            if intersection > 1:
                                lemma_score *= 1.2
                            
                            if lemma_score > best_score and lemma_score >= (threshold * 0.8):
                                best_score = lemma_score
                                best_match = {
                                    "category": category,
                                    "pattern": pattern,
                                    "responses": responses,
                                    "score": lemma_score,
                                    "matched_input": user_input,
                                    "processed_pattern": pattern,
                                    "match_type": "lemma_based"
                                }
        
        return best_match
    
    def get_response(self, user_input: str) -> str:
        """Kullanıcı girdisi için yanıt üret"""
        # Önce static responses'dan ara
        match = self.find_best_match(user_input)
        
        if match:
            responses = match["responses"]
            import random
            response = random.choice(responses)
            # Sadece detailed logging etkinse debug mesajı göster
            if self.enable_detailed_logging:
                print(f"🎯 Static response matched: {match['category']} (score: {match['score']:.2f})")
            return response
        
        # Fallback yanıtları
        return self._get_fallback_response(user_input)
    
    def _get_fallback_response(self, user_input: str) -> str:
        """Eşleşme bulunamadığında fallback yanıtları"""
        fallback_responses = [
            f"🤔 **\"{user_input}\" konusunda size yardımcı olmaya çalışıyorum...**\n\n"
            "Bu konuda elimde yeterli bilgi bulunmuyor, ancak size şu şekillerde yardımcı olabilirim:\n\n"
            "• 📞 **Teknik Destek**: destek@mefapex.com\n"
            "• 💬 **Genel Sorular**: info@mefapex.com\n"
            "• 🆘 **Acil Durumlar**: [Acil telefon]\n\n"
            "Lütfen sorunuzu daha detaylandırır mısınız? Böylece size daha iyi yardımcı olabilirim.",
            
            f"💡 **\"{user_input}\" hakkında bilgi arıyorsunuz...**\n\n"
            "Bu konu için size en doğru bilgiyi şu kanallardan alabilirsiniz:\n\n"
            "• 🏢 **İlgili Departman**: Konuyla ilgili uzman ekibimiz\n"
            "• 📋 **Dokümantasyon**: Şirket içi rehberler\n"
            "• 👥 **Meslektaşlarınız**: Deneyimli ekip üyeleri\n\n"
            "Ben de öğrenmeye devam ediyorum. Sorunuzu biraz daha açabilir misiniz?",
            
            f"🔍 **\"{user_input}\" konusunu araştırıyorum...**\n\n"
            "Şu anda bu konuda size kapsamlı bir yanıt veremiyorum, ama:\n\n"
            "• 📞 **Hızlı Çözüm**: İlgili departmanı arayın\n"
            "• 💻 **Online Kaynaklar**: Şirket portalını kontrol edin\n"
            "• 📝 **Ticket Açın**: Sistemden destek talebi oluşturun\n\n"
            "Bu arada bana daha spesifik sorular sorabilirsiniz. Örneğin teknik, İK, güvenlik konularında size yardımcı olabilirim!"
        ]
        
        import random
        return random.choice(fallback_responses)
    
    def get_category_suggestions(self, user_input: str) -> List[str]:
        """Kullanıcı girdisine göre kategori önerileri"""
        suggestions = []
        user_input_lower = user_input.lower()
        
        # Anahtar kelimeler bazında öneriler
        if any(word in user_input_lower for word in ['saat', 'çalışma', 'mesai', 'açık', 'kapalı']):
            suggestions.append("Çalışma saatleri hakkında bilgi almak için: 'çalışma saatleri' yazın")
        
        if any(word in user_input_lower for word in ['destek', 'help', 'problem', 'hata']):
            suggestions.append("Teknik destek için: 'teknik destek' yazın")
        
        if any(word in user_input_lower for word in ['izin', 'tatil', 'ik', 'personel']):
            suggestions.append("İnsan kaynakları için: 'izin başvurusu' yazın")
        
        if any(word in user_input_lower for word in ['güvenlik', 'kural', 'kaza']):
            suggestions.append("Güvenlik bilgileri için: 'güvenlik kuralları' yazın")
        
        if any(word in user_input_lower for word in ['şirket', 'mefapex', 'hakkında']):
            suggestions.append("Şirket bilgileri için: 'MEFAPEX hakkında' yazın")
        
        return suggestions[:3]  # En fazla 3 öneri
    
    def get_stats(self) -> Dict:
        """Content manager istatistikleri"""
        total_patterns = sum(len(data["patterns"]) for data in self.responses.values())
        total_responses = sum(len(data["responses"]) for data in self.responses.values())
        
        # Morfological analyzer stats (lazy loading aware)
        if self.morph_analyzer is None:
            morph_stats = {
                "morphological_analyzer": "Not loaded (lazy loading - will initialize on first use)",
                "fallback_lemmas": "Available",
                "morphological_analysis": "On-demand"
            }
        else:
            morph_stats = {
                "spacy_available": self.morph_analyzer.nlp is not None,
                "fallback_lemmas": len(self.morph_analyzer.fallback_lemmas),
                "morphological_analysis": "Loaded and active"
            }
        
        # Synonym stats (lazy loading aware)
        if not self._synonyms_loaded:
            synonym_stats = {
                "synonyms": "Not loaded (lazy loading - will load on first use)",
                "enhanced_with_morphology": "Pending"
            }
        else:
            synonym_stats = {
                "synonym_words": len(self.synonym_map),
                "enhanced_with_morphology": self._synonyms_enhanced
            }
        
        return {
            "total_categories": len(self.responses),
            "total_patterns": total_patterns,
            "total_responses": total_responses,
            "cache_size": len(self.pattern_cache),
            "language": "Turkish (Enhanced with On-Demand Morphological Analysis)",
            "morphological_analysis": morph_stats,
            "synonym_analysis": synonym_stats
        }

# Global instance - ultra efficient mode (no detailed logging, ERROR level only, completely silent)
# Morfological analysis sadece kullanıcı soru sorduğunda çalışır
improved_turkish_content = ImprovedTurkishContentManager(enable_detailed_logging=False)
