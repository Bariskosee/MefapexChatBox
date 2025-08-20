#!/bin/bash

# 🤖 MEFAPEX AI Mikroservisi Başlatma Scripti
# ==========================================

echo "🤖 MEFAPEX AI Mikroservisi başlatılıyor..."

# Sanal ortamı etkinleştir
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    echo "✅ Sanal ortam etkinleştirildi"
else
    echo "⚠️ Sanal ortam bulunamadı, sistem Python kullanılıyor"
fi

# Ortam değişkenlerini ayarla
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
export AI_MODELS_PATH="$(pwd)/models_cache"
export TORCH_HOME="$(pwd)/models_cache/torch"
export HF_HOME="$(pwd)/models_cache/huggingface"

# Model cache dizinlerini oluştur
mkdir -p models_cache/torch
mkdir -p models_cache/huggingface

# Gerekli bağımlılıkları kontrol et
echo "📦 Bağımlılıklar kontrol ediliyor..."

# aiohttp'yi kontrol et ve gerekirse yükle
python -c "import aiohttp" 2>/dev/null || {
    echo "📦 aiohttp yükleniyor..."
    pip install aiohttp
}

# Diğer kritik bağımlılıkları kontrol et
python -c "import torch, transformers, sentence_transformers" 2>/dev/null || {
    echo "❌ Kritik AI bağımlılıkları eksik!"
    echo "🔧 Lütfen requirements.txt dosyasını kullanarak bağımlılıkları yükleyin:"
    echo "    pip install -r requirements.txt"
    exit 1
}

echo "✅ Bağımlılık kontrolü başarılı"

# AI servisini başlat
echo "🚀 AI Mikroservisi başlatılıyor (Port: 8001)..."

# Log dosyası oluştur
mkdir -p logs
LOG_FILE="logs/ai_service_$(date +%Y%m%d_%H%M%S).log"

# Servis durumunu kontrol et
check_service() {
    curl -s http://localhost:8001/health >/dev/null 2>&1
    return $?
}

# Eğer servis zaten çalışıyorsa durdur
if check_service; then
    echo "⚠️ AI Mikroservisi zaten çalışıyor, yeniden başlatılıyor..."
    pkill -f "python.*services/ai_service/main.py" 2>/dev/null || true
    sleep 2
fi

# Background'da başlat
python services/ai_service/main.py \
    --host 0.0.0.0 \
    --port 8001 \
    > "$LOG_FILE" 2>&1 &

AI_SERVICE_PID=$!
echo "🔄 AI Mikroservisi başlatıldı (PID: $AI_SERVICE_PID)"
echo "📄 Log dosyası: $LOG_FILE"

# Servisin başlamasını bekle
echo "⏳ AI Mikroservisi hazır olması bekleniyor..."
for i in {1..30}; do
    if check_service; then
        echo "✅ AI Mikroservisi hazır! (http://localhost:8001)"
        echo "📚 API Dokümantasyonu: http://localhost:8001/docs"
        
        # Sağlık kontrolü yap
        echo "🔍 Sağlık kontrolü yapılıyor..."
        curl -s http://localhost:8001/health | python -m json.tool 2>/dev/null || echo "Sağlık kontrolü yanıtı alındı"
        
        echo ""
        echo "🎉 AI Mikroservisi başarıyla başlatıldı!"
        echo ""
        echo "📋 Kullanılabilir Endpoints:"
        echo "  - Sağlık: GET  http://localhost:8001/health"
        echo "  - Embedding: POST http://localhost:8001/embedding"
        echo "  - Metin Üretimi: POST http://localhost:8001/generate"
        echo "  - Dil Tanıma: POST http://localhost:8001/language/detect"
        echo "  - Model Bilgisi: GET http://localhost:8001/models/info"
        echo ""
        echo "🔧 Kontrol Komutları:"
        echo "  - Durumu görüntüle: curl http://localhost:8001/health"
        echo "  - Modelleri ısıt: curl -X POST http://localhost:8001/models/warmup"
        echo "  - Servisi durdur: pkill -f 'services/ai_service/main.py'"
        echo ""
        
        exit 0
    fi
    echo "  Deneme $i/30..."
    sleep 2
done

echo "❌ AI Mikroservisi başlatılamadı!"
echo "📄 Log dosyasını kontrol edin: $LOG_FILE"
echo "🔧 Manuel başlatma için:"
echo "    python services/ai_service/main.py --host 0.0.0.0 --port 8001"

# Process'i temizle
kill $AI_SERVICE_PID 2>/dev/null || true

exit 1
