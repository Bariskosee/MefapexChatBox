#!/bin/bash
# 🇹🇷 MEFAPEX Turkish Chatbot Startup Script
echo "🇹🇷 MEFAPEX Türkçe Chatbot Başlatılıyor..."

# Virtual environment kontrolü
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment bulunamadı!"
    echo "💡 python -m venv .venv komutu ile oluşturun"
    exit 1
fi

# Virtual environment aktivasyonu
echo "🔧 Virtual environment aktive ediliyor..."
source .venv/bin/activate

# Python versiyonu kontrolü
python_version=$(python --version 2>&1)
echo "🐍 Python versiyonu: $python_version"

# Gerekli paketlerin kontrolü
echo "📦 Paket gereksinimlerini kontrol ediliyor..."
pip check

# Türkçe modellerin varlığını kontrol
echo "🤖 Türkçe AI modelleri kontrol ediliyor..."
python -c "from model_manager import model_manager; print('✅ Model Manager hazır')"

# Ana uygulamayı başlat
echo "🚀 MEFAPEX Chatbot başlatılıyor..."
echo "🌐 Tarayıcınızda http://localhost:8000 adresini açın"
python main.py
