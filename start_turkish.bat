@echo off
REM 🇹🇷 MEFAPEX Turkish Chatbot Startup Script (Windows)
echo 🇹🇷 MEFAPEX Türkçe Chatbot Başlatılıyor...

REM Virtual environment kontrolü
if not exist ".venv" (
    echo ❌ Virtual environment bulunamadı!
    echo 💡 python -m venv .venv komutu ile oluşturun
    pause
    exit /b 1
)

REM Virtual environment aktivasyonu
echo 🔧 Virtual environment aktive ediliyor...
call .venv\Scripts\activate.bat

REM Python versiyonu kontrolü
python --version

REM Gerekli paketlerin kontrolü
echo 📦 Paket gereksinimlerini kontrol ediliyor...
pip check

REM Türkçe modellerin varlığını kontrol
echo 🤖 Türkçe AI modelleri kontrol ediliyor...
python -c "from model_manager import model_manager; print('✅ Model Manager hazır')"

REM Ana uygulamayı başlat
echo 🚀 MEFAPEX Chatbot başlatılıyor...
echo 🌐 Tarayıcınızda http://localhost:8000 adresini açın
python main.py
pause
