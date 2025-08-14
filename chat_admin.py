#!/usr/bin/env python3
"""
MEFAPEX Chat Admin Tool
PostgreSQL'e yeni soru-cevap çiftleri eklemek için kullanılır
"""

import os
import sys
import json

# Environment variables
os.environ['POSTGRES_HOST'] = 'localhost'
os.environ['POSTGRES_PORT'] = '5432'
os.environ['POSTGRES_USER'] = 'mefapex'
os.environ['POSTGRES_PASSWORD'] = 'mefapex_secure_2024'
os.environ['POSTGRES_DB'] = 'mefapex_chatbot'

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def add_new_question():
    """Yeni soru-cevap çifti ekle"""
    
    try:
        from content_manager import content_manager
        
        print("🤖 MEFAPEX Chat Admin Tool")
        print("=" * 40)
        print("Yeni soru-cevap çifti ekleme")
        print()
        
        # Kullanıcıdan bilgi al
        category = input("📂 Kategori adı: ").strip()
        if not category:
            print("❌ Kategori adı gerekli!")
            return False
        
        print("\n🔑 Anahtar kelimeler (virgülle ayırın):")
        keywords_input = input("   Örnek: soru,question,help,yardım\n   > ").strip()
        if not keywords_input:
            print("❌ En az bir anahtar kelime gerekli!")
            return False
        
        keywords = [k.strip() for k in keywords_input.split(',') if k.strip()]
        
        print(f"\n💬 Cevap metni (çok satırlı giriş için son satırda 'END' yazın):")
        print("   Markdown formatı desteklenir (**, *, •, etc.)")
        
        response_lines = []
        while True:
            line = input("   > ")
            if line.strip().upper() == 'END':
                break
            response_lines.append(line)
        
        response_text = '\n'.join(response_lines).strip()
        if not response_text:
            print("❌ Cevap metni gerekli!")
            return False
        
        # Önizleme göster
        print("\n" + "="*50)
        print("📋 ÖNİZLEME:")
        print(f"📂 Kategori: {category}")
        print(f"🔑 Anahtar kelimeler: {', '.join(keywords)}")
        print(f"💬 Cevap:")
        print(response_text)
        print("="*50)
        
        # Onay al
        confirm = input("\n✅ Bu bilgileri kaydetmek istediğinizden emin misiniz? (y/N): ").strip().lower()
        if confirm not in ['y', 'yes', 'evet', 'e']:
            print("❌ İşlem iptal edildi.")
            return False
        
        # Database'e ekle
        if content_manager.add_dynamic_response(category, keywords, response_text):
            print("✅ Yeni soru-cevap çifti başarıyla eklendi!")
            
            # Test et
            print(f"\n🧪 Test ediliyor: '{keywords[0]}'")
            test_response, source = content_manager.find_response(keywords[0])
            print(f"🔍 Kaynak: {source}")
            print(f"💬 Cevap: {test_response[:100]}...")
            
            return True
        else:
            print("❌ Ekleme işlemi başarısız!")
            return False
            
    except Exception as e:
        print(f"❌ Hata: {e}")
        return False

def list_responses():
    """Mevcut response'ları listele"""
    
    try:
        from database.manager import db_manager
        
        print("📋 Mevcut Response'lar")
        print("=" * 30)
        
        conn = db_manager._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, category, keywords, 
                   LEFT(response_text, 100) as preview,
                   created_by, usage_count,
                   created_at
            FROM dynamic_responses 
            WHERE is_active = TRUE 
            ORDER BY created_at DESC
        """)
        
        responses = cursor.fetchall()
        db_manager._put_connection(conn)
        
        for i, resp in enumerate(responses, 1):
            keywords_list = json.loads(resp['keywords']) if resp['keywords'] else []
            print(f"\n{i}. 📂 {resp['category']}")
            print(f"   🔑 Kelimeler: {', '.join(keywords_list[:3])}{'...' if len(keywords_list) > 3 else ''}")
            print(f"   💬 Önizleme: {resp['preview']}...")
            print(f"   📊 Kullanım: {resp['usage_count']} | 👤 {resp['created_by']}")
            print(f"   📅 {resp['created_at'].strftime('%Y-%m-%d %H:%M')}")
        
        print(f"\n📊 Toplam: {len(responses)} aktif response")
        return True
        
    except Exception as e:
        print(f"❌ Hata: {e}")
        return False

def test_question():
    """Soru test et"""
    
    try:
        from content_manager import content_manager
        
        print("🧪 Soru Testi")
        print("=" * 20)
        
        question = input("❓ Test etmek istediğiniz soruyu yazın: ").strip()
        if not question:
            print("❌ Soru gerekli!")
            return False
        
        print(f"\n🔍 '{question}' sorusu test ediliyor...")
        
        response, source = content_manager.find_response(question)
        
        print(f"\n📊 Sonuç:")
        print(f"🔍 Kaynak: {source}")
        print(f"💬 Cevap:")
        print("-" * 40)
        print(response)
        print("-" * 40)
        
        return True
        
    except Exception as e:
        print(f"❌ Hata: {e}")
        return False

def main_menu():
    """Ana menü"""
    
    while True:
        print("\n🤖 MEFAPEX Chat Admin Tool")
        print("=" * 40)
        print("1. ➕ Yeni soru-cevap ekle")
        print("2. 📋 Mevcut response'ları listele")
        print("3. 🧪 Soru test et")
        print("4. 📊 İstatistikleri göster")
        print("5. 🚪 Çıkış")
        print()
        
        choice = input("Seçiminiz (1-5): ").strip()
        
        if choice == '1':
            add_new_question()
        elif choice == '2':
            list_responses()
        elif choice == '3':
            test_question()
        elif choice == '4':
            try:
                from content_manager import content_manager
                stats = content_manager.get_stats()
                print("\n📊 Sistem İstatistikleri:")
                print(f"   • Static responses: {stats.get('static_responses', 0)}")
                print(f"   • Dynamic responses: {stats.get('dynamic_responses', 0)}")
                print(f"   • Cache entries: {stats.get('cache_entries', 0)}")
                print(f"   • Cache enabled: {stats.get('cache_enabled', False)}")
            except Exception as e:
                print(f"❌ İstatistik hatası: {e}")
        elif choice == '5':
            print("👋 Görüşürüz!")
            break
        else:
            print("❌ Geçersiz seçim!")

if __name__ == "__main__":
    main_menu()
