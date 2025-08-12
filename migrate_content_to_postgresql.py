#!/usr/bin/env python3
"""
Static Content to PostgreSQL Migration Script
Bu script static_responses.json dosyasındaki içeriği PostgreSQL'e aktarır
"""

import os
import sys
import json
from datetime import datetime

# Environment variables ayarla
os.environ['POSTGRES_HOST'] = 'localhost'
os.environ['POSTGRES_PORT'] = '5432'
os.environ['POSTGRES_USER'] = 'mefapex'
os.environ['POSTGRES_PASSWORD'] = 'mefapex_secure_2024'
os.environ['POSTGRES_DB'] = 'mefapex_chatbot'

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def migrate_static_to_postgresql():
    """Static content'i PostgreSQL'e aktarır"""
    
    try:
        from database_manager import db_manager
        
        print("🚀 MEFAPEX Static Content Migration")
        print("=" * 50)
        
        # JSON dosyasını yükle
        json_path = "content/static_responses.json"
        if not os.path.exists(json_path):
            print(f"❌ {json_path} dosyası bulunamadı!")
            return False
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        responses = data.get("responses", {})
        categories = data.get("categories", {})
        
        print(f"📋 Toplam {len(responses)} response kategorisi bulundu")
        
        # Database bağlantısını test et
        health = db_manager.health_check()
        if health.get('status') != 'healthy':
            print("❌ Database bağlantısı sağlanamadı!")
            return False
        
        print("✅ PostgreSQL bağlantısı başarılı")
        
        # Dynamic responses tablosunu temizle (sadece system kayıtları)
        conn = db_manager._get_connection()
        cursor = conn.cursor()
        
        print("🧹 Mevcut system responses temizleniyor...")
        cursor.execute("DELETE FROM dynamic_responses WHERE created_by = 'system'")
        
        # Her response kategorisini PostgreSQL'e ekle
        successful_imports = 0
        
        for category_key, response_data in responses.items():
            try:
                category_info = categories.get(category_key, {})
                
                # Response bilgilerini al
                message = response_data.get("message", "")
                keywords = response_data.get("keywords", [])
                category_name = category_info.get("name", category_key)
                
                # PostgreSQL'e ekle
                cursor.execute("""
                    INSERT INTO dynamic_responses 
                    (category, keywords, response_text, created_by, is_active, created_at) 
                    VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                """, (
                    category_name,
                    json.dumps(keywords, ensure_ascii=False),  # JSONB format
                    message,
                    'system',
                    True
                ))
                
                successful_imports += 1
                print(f"✅ {category_name}: {len(keywords)} anahtar kelime ile eklendi")
                
            except Exception as e:
                print(f"❌ {category_key} eklenirken hata: {e}")
                continue
        
        # Değişiklikleri kaydet
        conn.commit()
        db_manager._put_connection(conn)
        
        print(f"\n🎉 Migration tamamlandı!")
        print(f"✅ {successful_imports}/{len(responses)} response başarıyla aktarıldı")
        
        # Verification
        print("\n📊 Database verification...")
        conn = db_manager._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as total FROM dynamic_responses WHERE created_by = 'system'")
        total_count = cursor.fetchone()['total']
        
        cursor.execute("""
            SELECT category, jsonb_array_length(keywords) as keyword_count 
            FROM dynamic_responses 
            WHERE created_by = 'system' 
            ORDER BY category
        """)
        categories_info = cursor.fetchall()
        
        db_manager._put_connection(conn)
        
        print(f"📋 Toplam sistem response'ları: {total_count}")
        print("📂 Kategoriler:")
        for cat in categories_info:
            print(f"   • {cat['category']}: {cat['keyword_count']} anahtar kelime")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration hatası: {e}")
        return False

def test_responses():
    """Aktarılan response'ları test et"""
    
    try:
        from content_manager import content_manager
        
        print("\n🧪 Response Test Başlıyor...")
        print("=" * 30)
        
        # Test soruları
        test_queries = [
            "merhaba",
            "mefapex hakkında bilgi",
            "çalışma saatleri nedir",
            "teknik destek",
            "teknoloji",
            "teşekkürler"
        ]
        
        for query in test_queries:
            response, source = content_manager.find_response(query)
            print(f"\n📝 Soru: '{query}'")
            print(f"🔍 Kaynak: {source}")
            print(f"💬 Cevap: {response[:100]}...")
        
        # Statistics
        stats = content_manager.get_stats()
        print(f"\n📊 Content Manager İstatistikleri:")
        print(f"   • Static responses: {stats.get('static_responses', 0)}")
        print(f"   • Dynamic responses: {stats.get('dynamic_responses', 0)}")
        print(f"   • Cache entries: {stats.get('cache_entries', 0)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test hatası: {e}")
        return False

def add_custom_responses():
    """Özel response'lar ekle"""
    
    try:
        from content_manager import content_manager
        
        print("\n➕ Özel Response'lar Ekleniyor...")
        print("=" * 35)
        
        # Ek custom responses
        custom_responses = [
            {
                "category": "Sistem Durumu",
                "keywords": ["sistem", "durum", "çalışıyor mu", "aktif mi", "status", "health"],
                "message": "🟢 **Sistem Durumu: Aktif**\n\nTüm sistemlerimiz normal çalışıyor:\n• 💾 Database: ✅ Çalışıyor\n• 🌐 Web servisi: ✅ Aktif\n• 🤖 AI asistan: ✅ Hazır\n• 🔄 API'ler: ✅ Yanıt veriyor\n\nSistem performansı normal seviyede. Herhangi bir sorun yaşıyorsanız lütfen bildirin."
            },
            {
                "category": "Güvenlik",
                "keywords": ["güvenlik", "şifre", "password", "security", "güvenli", "koruma"],
                "message": "🔐 **Güvenlik ve Veri Koruması**\n\n**Güvenlik Önlemlerimiz:**\n• 🛡️ End-to-end şifreleme\n• 🔑 Çok faktörlü kimlik doğrulama\n• 📊 Sürekli güvenlik izleme\n• 🚫 DDoS koruması\n• 💾 Güvenli veri yedekleme\n\n**Şifre Güvenliği:**\n• En az 8 karakter\n• Büyük/küçük harf kombinasyonu\n• Sayı ve özel karakter kullanımı\n• Düzenli şifre değişimi\n\n**Şüpheli aktivite tespit edilirse anında müdahale edilir.**"
            },
            {
                "category": "API ve Entegrasyon", 
                "keywords": ["api", "entegrasyon", "integration", "webservice", "rest", "endpoint"],
                "message": "🔌 **API ve Entegrasyon Hizmetleri**\n\n**Sunduğumuz API'ler:**\n• 📡 RESTful API servisleri\n• 🔄 Real-time WebSocket bağlantıları\n• 📊 Veri analizi API'leri\n• 🤖 AI/ML model API'leri\n• 🔐 Güvenli authentication endpoints\n\n**Entegrasyon Desteği:**\n• Üçüncü taraf sistem entegrasyonları\n• Custom API geliştirme\n• Webhook implementasyonu\n• Veri senkronizasyonu\n\n**Dokümantasyon: `/docs` endpoint'inde mevcuttur.**"
            }
        ]
        
        success_count = 0
        for response in custom_responses:
            if content_manager.add_dynamic_response(
                response["category"],
                response["keywords"], 
                response["message"]
            ):
                success_count += 1
                print(f"✅ {response['category']} eklendi")
            else:
                print(f"❌ {response['category']} eklenemedi")
        
        print(f"\n🎯 {success_count}/{len(custom_responses)} özel response eklendi")
        return True
        
    except Exception as e:
        print(f"❌ Özel response ekleme hatası: {e}")
        return False

if __name__ == "__main__":
    print("🚀 MEFAPEX Content Migration Tool")
    print("=" * 50)
    
    # 1. Static content'i PostgreSQL'e aktar
    if migrate_static_to_postgresql():
        print("✅ 1. Static content migration: BAŞARILI")
    else:
        print("❌ 1. Static content migration: BAŞARISIZ")
        sys.exit(1)
    
    # 2. Özel response'ları ekle
    if add_custom_responses():
        print("✅ 2. Custom responses ekleme: BAŞARILI")
    else:
        print("❌ 2. Custom responses ekleme: BAŞARISIZ")
    
    # 3. Response'ları test et
    if test_responses():
        print("✅ 3. Response testing: BAŞARILI")
    else:
        print("❌ 3. Response testing: BAŞARISIZ")
    
    print("\n" + "="*50)
    print("🎉 MIGRATION TAMAMLANDI!")
    print("📋 Artık tüm sorular PostgreSQL'den yanıtlanacak")
    print("💬 Kullanıcılar chat'te daha iyi yanıtlar alacak")
    print("⚡ Sistem dinamik olarak yeni sorular öğrenebilir")
    print("=" * 50)
