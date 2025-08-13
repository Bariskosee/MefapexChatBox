#!/usr/bin/env python3
"""
Setup script to add initial dynamic responses to the database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from content_manager import ContentManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_initial_responses():
    """Add initial dynamic responses to the database"""
    
    content_manager = ContentManager()
    
    # Sample dynamic responses
    dynamic_responses = [
        {
            "category": "technical_support",
            "keywords": ["sunucu", "server", "down", "çalışmıyor", "erişim", "bağlanamıyorum", "slow", "yavaş"],
            "message": "🔧 **Teknik Destek - Sunucu Problemleri**\n\nSunucu ile ilgili yaşadığınız problem için hemen yardım edeyim:\n\n**Hızlı Kontroller:**\n• İnternet bağlantınızı kontrol edin\n• Tarayıcınızı yenileyin (Ctrl+F5)\n• VPN bağlantınızı kontrol edin\n\n**Acil Destek:**\n📞 7/24 Teknik Destek: [Telefon]\n📧 Acil: teknik@mefapex.com\n\n**Problem Detayları:**\nLütfen şu bilgileri paylaşın:\n• Hangi sisteme erişmeye çalışıyorsunuz?\n• Ne zaman başladı?\n• Hata mesajı var mı?\n\nHemen çözüm bulalım! 🚀"
        },
        {
            "category": "database_support",
            "keywords": ["veritabanı", "database", "sql", "veri", "kayıt", "backup", "yedek"],
            "message": "💾 **Veritabanı Desteği**\n\nVeritabanı konusunda size yardımcı olayım:\n\n**Yaygın Çözümler:**\n• Bağlantı sorunları için port kontrolü\n• Yetki problemleri için user hakları\n• Performance için query optimizasyonu\n• Backup/restore işlemleri\n\n**Acil Durum:**\n• Veri kaybı durumunda hemen iletişime geçin\n• Backup'larımız 24 saat öncesine kadar mevcut\n• Otomatik recovery sistemimiz aktif\n\n**İletişim:**\n📞 DB Uzmanı: [Telefon]\n💬 Bu sistem üzerinden detay verebilirsiniz\n\nSorununuzu daha detaylandırır mısınız?"
        },
        {
            "category": "software_bugs",
            "keywords": ["hata", "bug", "error", "çalışmıyor", "donuyor", "crash", "sorun"],
            "message": "🐛 **Yazılım Hatası Bildirimi**\n\nYazılım hatası için teşekkürler! Hemen inceleyelim:\n\n**Lütfen Şu Bilgileri Verin:**\n• Hangi sayfa/özellikte hata oluştu?\n• Hata mesajının ekran görüntüsü\n• Hangi adımları izlediniz?\n• Tarayıcı/cihaz bilgileri\n\n**Hızlı Çözümler:**\n• Sayfayı yenileyin (F5)\n• Cache'i temizleyin (Ctrl+Shift+Del)\n• Farklı tarayıcı deneyin\n• Gizli sekme modunu deneyin\n\n**Bug Tracking:**\n• Raporunuz hemen development ekibine iletilir\n• 24 saat içinde geri dönüş garantisi\n• Kritik hatalar 2 saat içinde çözülür\n\n🔧 Detayları bu sistemden paylaşabilirsiniz."
        },
        {
            "category": "user_training",
            "keywords": ["nasıl", "how", "kullanım", "öğrenmek", "eğitim", "training", "tutorial"],
            "message": "📚 **Kullanıcı Eğitimi ve Rehberlik**\n\nSistemi öğrenmenize yardımcı olalım:\n\n**Eğitim Kaynakları:**\n• 📖 Online kullanım kılavuzu\n• 🎥 Video tutorial'lar\n• 📋 Adım adım rehberler\n• 💡 Tips & tricks dokümanları\n\n**Canlı Eğitim:**\n• Haftalık grup eğitimleri\n• Birebir özel eğitim\n• Uzaktan ekran paylaşımı ile destek\n• Q&A oturumları\n\n**Hızlı Başlangıç:**\n• Temel özellikler 15 dakikada\n• İleri özellikler için özel program\n• İş süreçlerinize özel eğitim\n\n**Eğitim Rezervasyonu:**\n📞 Eğitim koordinatörü: [Telefon]\n📧 egitim@mefapex.com\n\nHangi konuda eğitime ihtiyacınız var? 🎯"
        },
        {
            "category": "integration_support",
            "keywords": ["entegrasyon", "integration", "api", "bağlantı", "sync", "senkron"],
            "message": "🔗 **Sistem Entegrasyonu Desteği**\n\nEntegrasyon konusunda size yardımcı olayım:\n\n**API Desteği:**\n• REST API dokümantasyonu\n• WebHook konfigürasyonu\n• OAuth 2.0 authentication\n• Rate limiting bilgileri\n\n**Yaygın Entegrasyonlar:**\n• CRM sistemleri (Salesforce, HubSpot)\n• ERP çözümleri (SAP, Oracle)\n• E-ticaret platformları\n• Muhasebe yazılımları\n\n**Teknik Destek:**\n• API test ortamı\n• Sandbox environment\n• Postman collection'ları\n• SDK'lar (Python, .NET, Java)\n\n**Entegrasyon Süreci:**\n• İhtiyaç analizi\n• Teknik tasarım\n• Development & testing\n• Go-live desteği\n\n👨‍💻 Entegrasyon uzmanımızla konuşmak ister misiniz?"
        }
    ]
    
    # Add each response to the database
    success_count = 0
    for response in dynamic_responses:
        if content_manager.add_dynamic_response(
            response["category"],
            response["keywords"], 
            response["message"]
        ):
            success_count += 1
            logger.info(f"✅ Added: {response['category']}")
        else:
            logger.error(f"❌ Failed to add: {response['category']}")
    
    logger.info(f"🎉 Setup complete! Added {success_count}/{len(dynamic_responses)} dynamic responses")
    
    # Display stats
    stats = content_manager.get_stats()
    logger.info(f"📊 Stats: {stats}")

if __name__ == "__main__":
    setup_initial_responses()
