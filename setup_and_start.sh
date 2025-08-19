#!/bin/bash

# 🚀 MEFAPEX ChatBox Kurulum ve Çalıştırma Rehberi
# Bu script, projenizi adım adım başlatmanıza yardımcı olacak

echo "🚀 MEFAPEX ChatBox Kurulum Başlatılıyor..."
echo "================================================"

# 1. Python sürümünü kontrol et
echo "1️⃣ Python sürümü kontrol ediliyor..."
python_version=$(python --version 2>&1)
echo "Python sürümü: $python_version"

if ! python -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null; then
    echo "❌ HATA: Python 3.11+ gerekli!"
    echo "Lütfen Python 3.11 veya üstünü yükleyin."
    exit 1
fi
echo "✅ Python sürümü uygun"

# 2. Virtual Environment Kontrolü
echo ""
echo "2️⃣ Virtual Environment kontrol ediliyor..."
if [ ! -d ".venv" ]; then
    echo "🔧 Virtual environment oluşturuluyor..."
    python -m venv .venv
    echo "✅ Virtual environment oluşturuldu"
else
    echo "✅ Virtual environment mevcut"
fi

# 3. Virtual Environment Aktivasyonu
echo ""
echo "3️⃣ Virtual environment aktive ediliyor..."
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    # Windows
    source .venv/Scripts/activate
else
    # Linux/macOS
    source .venv/bin/activate
fi
echo "✅ Virtual environment aktive edildi"

# 4. Gerekli paketleri yükle
echo ""
echo "4️⃣ Gerekli paketler yükleniyor..."
pip install --upgrade pip
pip install -r requirements.txt
echo "✅ Paketler yüklendi"

# 5. Environment değişkenlerini ayarla
echo ""
echo "5️⃣ Environment değişkenleri ayarlanıyor..."

export ENVIRONMENT=development
export DEBUG=true
export APP_PORT=8000
export SECRET_KEY=mefapex-development-secret-key
export DEMO_USER_ENABLED=true
export DEMO_PASSWORD=1234

# Database ayarları (PostgreSQL kullanılıyor)
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_USER=mefapex
export POSTGRES_PASSWORD=mefapex
export POSTGRES_DB=mefapex_chatbot

# AI ayarları
export USE_OPENAI=false
export USE_HUGGINGFACE=true
export AI_PREFER_TURKISH_MODELS=true

# CORS ayarları
export ALLOWED_ORIGINS="http://localhost:8000,http://127.0.0.1:8000,*"

echo "✅ Environment değişkenleri ayarlandı"

# 6. Basit test
echo ""
echo "6️⃣ Sistem testi yapılıyor..."
python -c "
try:
    from core.configuration import get_config
    config = get_config()
    print('✅ Konfigürasyon yüklendi')
    
    from database.manager import db_manager
    print('✅ Database manager yüklendi')
    
    from model_manager import model_manager
    print('✅ Model manager yüklendi (AI modelleri lazy loading)')
    
    print('✅ Temel sistem kontrolü başarılı')
except Exception as e:
    print(f'❌ Sistem hatası: {e}')
    exit(1)
"

if [ $? -ne 0 ]; then
    echo "❌ Sistem testi başarısız!"
    exit 1
fi

# 7. Sunucuyu başlat
echo ""
echo "7️⃣ Sunucu başlatılıyor..."
echo "🌐 URL: http://localhost:8000"
echo "👤 Demo Kullanıcı: demo / 1234"
echo "📚 API Docs: http://localhost:8000/docs"
echo ""
echo "Sunucuyu durdurmak için Ctrl+C kullanın"
echo ""

# Sunucuyu başlat
python main.py
