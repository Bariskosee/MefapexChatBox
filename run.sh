#!/bin/bash
# MEFAPEX ChatBox Çalıştırma Scripti
# Linux/macOS için

echo "🚀 MEFAPEX ChatBox başlatılıyor..."
echo "=================================="

# Python versiyonunu kontrol et
if ! command -v python3.11 &> /dev/null; then
    echo "❌ Python 3.11 bulunamadı!"
    echo "   Python 3.11+ yükleyin: https://www.python.org/downloads/"
    exit 1
fi

# Virtual environment kontrol et
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment bulunamadı!"
    echo "   Önce setup.py scriptini çalıştırın: python setup.py"
    exit 1
fi

# Virtual environment'ı aktive et
echo "📦 Virtual environment aktive ediliyor..."
source .venv/bin/activate

# Python versiyonunu göster
echo "🐍 Python versiyonu: $(python --version)"

# .env dosyasını kontrol et
if [ ! -f ".env" ]; then
    echo "⚠️  .env dosyası bulunamadı!"
    echo "   .env.example dosyasından kopyalayın:"
    echo "   cp .env.example .env"
    echo ""
    echo "🔧 Varsayılan ayarlarla devam ediliyor..."
fi

# Serveri başlat
echo ""
echo "✅ Server başlatılıyor..."
echo "🌐 Erişim adresi: http://localhost:8000"
echo "🔑 Demo giriş: demo / 1234"
echo "📊 API docs: http://localhost:8000/docs"
echo "🏥 Health check: http://localhost:8000/health"
echo ""
echo "🛑 Durdurmak için: Ctrl+C"
echo "=================================="
echo ""

# Ana uygulamayı başlat
python main.py
