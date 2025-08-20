"""
🇹🇷 Gelişmiş Türkçe Content Manager
==================================
Daha iyi Türkçe yanıtlar için optimize edilmiş content yöneticisi
"""
import json
import re
import logging
from typing import Dict, List, Tuple, Optional
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

class ImprovedTurkishContentManager:
    """
    Gelişmiş Türkçe content yöneticisi
    - Daha kapsamlı static responses
    - Gelişmiş fuzzy matching
    - Türkçe karakter desteği
    - Akıllı fallback responses
    """
    
    def __init__(self):
        self.responses = self._load_enhanced_responses()
        self.synonym_map = self._create_synonym_map()
        self.pattern_cache = {}
        
        logger.info("🇹🇷 Enhanced Turkish Content Manager initialized")
    
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
    
    def _create_synonym_map(self) -> Dict[str, List[str]]:
        """Türkçe eş anlamlı kelimeler"""
        return {
            'çalışma': ['iş', 'mesai', 'görev', 'vazife', 'work', 'job'],
            'saat': ['zaman', 'vakit', 'time', 'hours', 'hour'],
            'açık': ['open', 'başlama', 'start', 'begin'],
            'kapalı': ['closed', 'bitiş', 'end', 'finish', 'stop'],
            'destek': ['yardım', 'help', 'support', 'assistance', 'aid'],
            'problem': ['sorun', 'hata', 'error', 'issue', 'bug'],
            'mefapex': ['şirket', 'company', 'firma', 'organization', 'kurum'],
            'güvenlik': ['security', 'safety', 'emniyet', 'koruma'],
            'izin': ['leave', 'vacation', 'tatil', 'permit', 'permission'],
            'proje': ['project', 'görev', 'task', 'iş', 'work'],
            'eğitim': ['training', 'education', 'kurs', 'course', 'öğretim'],
            'sistem': ['system', 'software', 'yazılım', 'program'],
            'hata': ['error', 'bug', 'problem', 'sorun', 'issue'],
            'yardım': ['help', 'support', 'destek', 'assistance']
        }
    
    def _normalize_turkish(self, text: str) -> str:
        """Türkçe karakterleri normalize et"""
        # Türkçe karakter dönüşümleri
        turkish_map = {
            'ç': 'c', 'ğ': 'g', 'ı': 'i', 'ö': 'o', 'ş': 's', 'ü': 'u',
            'Ç': 'c', 'Ğ': 'g', 'I': 'i', 'İ': 'i', 'Ö': 'o', 'Ş': 's', 'Ü': 'u'
        }
        
        normalized = ""
        for char in text.lower():
            normalized += turkish_map.get(char, char)
        
        return normalized
    
    def _expand_with_synonyms(self, text: str) -> List[str]:
        """Metni eş anlamlı kelimelerle genişlet"""
        words = text.split()
        expanded_texts = [text]
        
        # Her kelime için eş anlamlıları kontrol et
        for word in words:
            normalized_word = self._normalize_turkish(word)
            if normalized_word in self.synonym_map:
                synonyms = self.synonym_map[normalized_word]
                for synonym in synonyms:
                    # Orijinal kelimeyi eş anlamlısıyla değiştir
                    new_text = text.replace(word, synonym)
                    if new_text not in expanded_texts:
                        expanded_texts.append(new_text)
        
        return expanded_texts
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """İki metin arasında benzerlik hesapla"""
        # Cache kontrolü
        cache_key = f"{text1}|{text2}"
        if cache_key in self.pattern_cache:
            return self.pattern_cache[cache_key]
        
        # Metinleri normalize et
        norm1 = self._normalize_turkish(text1)
        norm2 = self._normalize_turkish(text2)
        
        # Temel benzerlik
        basic_similarity = SequenceMatcher(None, norm1, norm2).ratio()
        
        # Kelime bazlı benzerlik
        words1 = set(norm1.split())
        words2 = set(norm2.split())
        
        if not words1 or not words2:
            similarity = basic_similarity
        else:
            word_similarity = len(words1 & words2) / len(words1 | words2)
            # Ağırlıklı ortalama
            similarity = (basic_similarity * 0.6) + (word_similarity * 0.4)
        
        # Cache'e kaydet
        self.pattern_cache[cache_key] = similarity
        return similarity
    
    def find_best_match(self, user_input: str, threshold: float = 0.3) -> Optional[Dict]:
        """Kullanıcı girdisi için en iyi eşleşmeyi bul"""
        user_input = user_input.strip().lower()
        if not user_input:
            return None
        
        best_match = None
        best_score = 0.0
        
        # Eş anlamlı kelimelerle genişletilmiş versiyonları da kontrol et
        expanded_inputs = self._expand_with_synonyms(user_input)
        
        for category, data in self.responses.items():
            patterns = data["patterns"]
            responses = data["responses"]
            
            for pattern in patterns:
                # Tüm genişletilmiş versiyonları kontrol et
                for expanded_input in expanded_inputs:
                    # Direkt içerme kontrolü (yüksek puan)
                    if pattern in expanded_input or expanded_input in pattern:
                        score = 0.9
                    else:
                        # Fuzzy matching
                        score = self._calculate_similarity(expanded_input, pattern)
                    
                    if score > best_score and score >= threshold:
                        best_score = score
                        best_match = {
                            "category": category,
                            "pattern": pattern,
                            "responses": responses,
                            "score": score
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
            logger.info(f"🎯 Static response matched: {match['category']} (score: {match['score']:.2f})")
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
        
        return {
            "total_categories": len(self.responses),
            "total_patterns": total_patterns,
            "total_responses": total_responses,
            "cache_size": len(self.pattern_cache),
            "synonym_words": len(self.synonym_map),
            "language": "Turkish (Enhanced)"
        }

# Global instance
improved_turkish_content = ImprovedTurkishContentManager()
