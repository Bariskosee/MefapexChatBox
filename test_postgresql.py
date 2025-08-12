#!/usr/bin/env python3
"""
PostgreSQL Bağlantı Test Script
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Test environment variables
os.environ['POSTGRES_HOST'] = 'localhost'
os.environ['POSTGRES_PORT'] = '5432'
os.environ['POSTGRES_USER'] = 'bariskose'  # macOS default user
os.environ['POSTGRES_PASSWORD'] = ''  # macOS Homebrew default
os.environ['POSTGRES_DB'] = 'postgres'  # Default database

print("🔍 PostgreSQL Bağlantı Testi Başlıyor...")

try:
    import psycopg2
    print("✅ psycopg2 kütüphanesi yüklü")
    
    # Test basic connection
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        user='bariskose',
        password='',
        database='postgres'
    )
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    version = cursor.fetchone()
    print(f"✅ PostgreSQL bağlantısı başarılı: {version[0]}")
    
    # Test creating mefapex database and user
    cursor.execute("SELECT 1 FROM pg_database WHERE datname='mefapex_chatbot'")
    if not cursor.fetchone():
        cursor.execute("CREATE DATABASE mefapex_chatbot")
        print("✅ mefapex_chatbot veritabanı oluşturuldu")
    else:
        print("✅ mefapex_chatbot veritabanı zaten mevcut")
    
    # Check for mefapex user
    cursor.execute("SELECT 1 FROM pg_roles WHERE rolname='mefapex'")
    if not cursor.fetchone():
        cursor.execute("CREATE USER mefapex WITH PASSWORD 'mefapex_secure_password'")
        cursor.execute("GRANT ALL PRIVILEGES ON DATABASE mefapex_chatbot TO mefapex")
        print("✅ mefapex kullanıcısı oluşturuldu")
    else:
        print("✅ mefapex kullanıcısı zaten mevcut")
    
    conn.commit()
    conn.close()
    
    # Now test with mefapex credentials
    os.environ['POSTGRES_USER'] = 'mefapex'
    os.environ['POSTGRES_PASSWORD'] = 'mefapex_secure_password'
    os.environ['POSTGRES_DB'] = 'mefapex_chatbot'
    
    print("\n🧪 Database Manager Test Ediliyor...")
    
    # Test database manager
    from database_manager import DatabaseManager
    
    db = DatabaseManager()
    print("✅ Database Manager başlatıldı")
    
    # Test health check
    health = db.health_check()
    print(f"✅ Health check: {health}")
    
    # Test stats
    stats = db.get_stats()
    print(f"✅ Database stats: {stats}")
    
    db.close()
    print("✅ Database bağlantısı kapatıldı")
    
    print("\n🎉 PostgreSQL entegrasyonu başarıyla tamamlandı!")
    print("\n📝 Şimdi .env dosyasını şu şekilde güncelleyin:")
    print("POSTGRES_HOST=localhost")
    print("POSTGRES_PORT=5432")
    print("POSTGRES_USER=mefapex")
    print("POSTGRES_PASSWORD=mefapex_secure_password")
    print("POSTGRES_DB=mefapex_chatbot")
    
except ImportError as e:
    print(f"❌ Kütüphane hatası: {e}")
    print("pip install psycopg2-binary çalıştırın")
    
except Exception as e:
    print(f"❌ Bağlantı hatası: {e}")
    print("PostgreSQL'in çalıştığından emin olun: brew services start postgresql@15")
