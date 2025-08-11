#!/bin/bash
echo "🚀 MEFAPEX ChatBox başlatılıyor..."
echo

# Virtual environment'ı aktive et
source .venv/bin/activate

# Python versiyonunu kontrol et
python --version

# Serveri başlat
echo "✅ Server başlatılıyor: http://localhost:8000"
echo "🔑 Giriş: demo / 1234"
echo
python main.py
