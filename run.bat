@echo off
REM MEFAPEX ChatBox Çalıştırma Scripti - Windows

echo 🚀 MEFAPEX ChatBox başlatılıyor...
echo ==================================

REM Python versiyonunu kontrol et
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python bulunamadı!
    echo    Python 3.11+ indirin: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Virtual environment kontrol et
if not exist ".venv" (
    echo ❌ Virtual environment bulunamadı!
    echo    Önce setup.py scriptini çalıştırın: python setup.py
    pause
    exit /b 1
)

REM Virtual environment'ı aktive et
echo 📦 Virtual environment aktive ediliyor...
call .venv\Scripts\activate

REM Python versiyonunu göster
echo 🐍 Python versiyonu:
python --version

REM .env dosyasını kontrol et
if not exist ".env" (
    echo ⚠️  .env dosyası bulunamadı!
    echo    .env.example dosyasından kopyalayın:
    echo    copy .env.example .env
    echo.
    echo 🔧 Varsayılan ayarlarla devam ediliyor...
)

REM Serveri başlat
echo.
echo ✅ Server başlatılıyor...
echo 🌐 Erişim adresi: http://localhost:8000
echo 🔑 Demo giriş: demo / 1234
echo 📊 API docs: http://localhost:8000/docs
echo 🏥 Health check: http://localhost:8000/health
echo.
echo 🛑 Durdurmak için: Ctrl+C
echo ==================================
echo.

REM Ana uygulamayı başlat
python main.py

pause
