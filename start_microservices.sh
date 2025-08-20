#!/bin/bash

# 🏗️ MEFAPEX Mikroservis Mimarisi Başlatma Scripti
# ===============================================

echo "🏗️ MEFAPEX Mikroservis Mimarisi başlatılıyor..."

# Sanal ortamı etkinleştir
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    echo "✅ Sanal ortam etkinleştirildi"
else
    echo "⚠️ Sanal ortam bulunamadı, sistem Python kullanılıyor"
fi

# Ortam değişkenlerini ayarla
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
export AI_SERVICE_ENABLED=true
export AI_SERVICE_HOST=127.0.0.1
export AI_SERVICE_PORT=8001

# Log dizini oluştur
mkdir -p logs

echo ""
echo "🎯 Mikroservis Başlatma Sırası:"
echo "1. 🤖 AI Mikroservisi (Port: 8001)"
echo "2. 🚀 Ana Uygulama (Port: 8000)"
echo ""

# 1. AI Mikroservisi Başlat
echo "🤖 1/2: AI Mikroservisi başlatılıyor..."
./start_ai_service.sh

if [ $? -ne 0 ]; then
    echo "❌ AI Mikroservisi başlatılamadı!"
    echo "🔧 Manuel başlatma için: ./start_ai_service.sh"
    exit 1
fi

echo ""
echo "⏳ AI Mikroservisi hazır, ana uygulama başlatılıyor..."
sleep 3

# 2. Ana Uygulama Başlat (AI Service Mode ile)
echo "🚀 2/2: Ana Uygulama başlatılıyor (AI Service Mode)..."

# Mevcut ana uygulamayı durdur
pkill -f "python.*main.py" 2>/dev/null || true
sleep 2

# Ana uygulamayı başlat
LOG_FILE="logs/main_app_$(date +%Y%m%d_%H%M%S).log"

python main.py > "$LOG_FILE" 2>&1 &
MAIN_APP_PID=$!

echo "🔄 Ana uygulama başlatıldı (PID: $MAIN_APP_PID)"
echo "📄 Log dosyası: $LOG_FILE"

# Ana uygulamanın başlamasını bekle
echo "⏳ Ana uygulama hazır olması bekleniyor..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health >/dev/null 2>&1; then
        echo "✅ Ana uygulama hazır! (http://localhost:8000)"
        break
    fi
    echo "  Deneme $i/30..."
    sleep 2
done

# Servislerin durumunu kontrol et
echo ""
echo "🔍 Servis Durumu Kontrolü:"

# AI Servisi
if curl -s http://localhost:8001/health >/dev/null 2>&1; then
    echo "  ✅ AI Mikroservisi: ÇALIŞIYOR (http://localhost:8001)"
else
    echo "  ❌ AI Mikroservisi: ÇALIŞMIYOR"
fi

# Ana Uygulama
if curl -s http://localhost:8000/health >/dev/null 2>&1; then
    echo "  ✅ Ana Uygulama: ÇALIŞIYOR (http://localhost:8000)"
else
    echo "  ❌ Ana Uygulama: ÇALIŞMIYOR"
fi

echo ""
echo "🎉 MEFAPEX Mikroservis Mimarisi Başlatıldı!"
echo ""
echo "📋 Servis Endpoint'leri:"
echo "┌─────────────────────────────────────────────────────────────┐"
echo "│  🚀 Ana Uygulama (Port 8000)                               │"
echo "│    - Web UI: http://localhost:8000                         │"
echo "│    - API Docs: http://localhost:8000/docs                  │"
echo "│    - Sağlık: http://localhost:8000/health                  │"
echo "│                                                             │"
echo "│  🤖 AI Mikroservisi (Port 8001)                            │"
echo "│    - AI API Docs: http://localhost:8001/docs               │"
echo "│    - AI Sağlık: http://localhost:8001/health               │"
echo "│    - Embedding: POST /embedding                             │"
echo "│    - Metin Üretimi: POST /generate                         │"
echo "│    - Dil Tanıma: POST /language/detect                     │"
echo "└─────────────────────────────────────────────────────────────┘"
echo ""
echo "🔧 Yönetim Komutları:"
echo "  - Tüm servisleri durdur: pkill -f 'python.*main.py'"
echo "  - AI servisini durdur: pkill -f 'services/ai_service/main.py'"
echo "  - Logları izle: tail -f logs/*.log"
echo "  - AI servis durumu: curl http://localhost:8001/health"
echo "  - Ana uygulama durumu: curl http://localhost:8000/health"
echo ""
echo "🐳 Docker ile başlatma için:"
echo "  docker-compose up -d"
echo ""

# Background processes bilgisi
echo "📊 Çalışan Process'ler:"
echo "  - Ana Uygulama PID: $MAIN_APP_PID"
echo "  - AI Servisi PID: $(pgrep -f 'services/ai_service/main.py' | head -1)"
echo ""
echo "✅ Mikroservis mimarisi başarıyla başlatıldı!"
