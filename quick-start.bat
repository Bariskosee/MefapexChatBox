@echo off
:: 🚀 MEFAPEX ChatBox - Windows Ultra Hızlı Kurulum
:: Bu script ile 30 saniyede sistemi ayağa kaldırın!

setlocal enabledelayedexpansion
title MEFAPEX ChatBox - Ultra Hızlı Kurulum

echo.
echo 🚀 MEFAPEX ChatBox - Windows Ultra Hızlı Kurulum
echo =================================================
echo.

:: Renk ayarları için
set "RED=[91m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "NC=[0m"

:: Python kontrol
echo %BLUE%ℹ️  Python kontrol ediliyor...%NC%
python --version >nul 2>&1
if errorlevel 1 (
    echo %RED%❌ HATA: Python bulunamadı!%NC%
    echo.
    echo Python 3.11+ yüklemek için:
    echo 1. https://python.org adresine gidin
    echo 2. Latest Python'u indirin
    echo 3. Kurulumda "Add to PATH" seçeneğini işaretleyin
    echo.
    pause
    exit /b 1
)

:: Python sürüm kontrolü
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo %GREEN%✅ Python %PYTHON_VERSION% uygun%NC%

:: Virtual Environment kontrol
echo %BLUE%ℹ️  Virtual environment kontrol ediliyor...%NC%
if not exist ".venv" (
    echo %BLUE%ℹ️  Virtual environment oluşturuluyor...%NC%
    python -m venv .venv
    if errorlevel 1 (
        echo %RED%❌ Virtual environment oluşturulamadı%NC%
        pause
        exit /b 1
    )
    echo %GREEN%✅ Virtual environment oluşturuldu%NC%
) else (
    echo %GREEN%✅ Virtual environment mevcut%NC%
)

:: Virtual Environment aktive et
echo %BLUE%ℹ️  Virtual environment aktive ediliyor...%NC%
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo %RED%❌ Virtual environment aktive edilemedi%NC%
    pause
    exit /b 1
)
echo %GREEN%✅ Virtual environment aktive edildi%NC%

:: Dependencies yükle
echo %BLUE%ℹ️  Gerekli paketler yükleniyor... (Bu birkaç dakika sürebilir)%NC%
python -m pip install --quiet --upgrade pip
if errorlevel 1 (
    echo %RED%❌ Pip güncellenemedi%NC%
    pause
    exit /b 1
)

pip install --quiet -r requirements.txt
if errorlevel 1 (
    echo %RED%❌ Paketler yüklenemedi%NC%
    echo.
    echo Lütfen internet bağlantınızı kontrol edin ve tekrar deneyin.
    pause
    exit /b 1
)
echo %GREEN%✅ Tüm paketler yüklendi%NC%

:: Environment ayarları
echo %BLUE%ℹ️  Environment ayarları yapılandırılıyor...%NC%
if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env >nul
        echo %GREEN%✅ Environment dosyası oluşturuldu (.env.example'dan kopyalandı)%NC%
    ) else (
        :: Minimal .env dosyası oluştur
        (
            echo # MEFAPEX ChatBox Configuration
            echo ENVIRONMENT=development
            echo DEBUG=true
            echo APP_PORT=8000
            echo SECRET_KEY=mefapex-development-secret-%RANDOM%
            echo DEMO_USER_ENABLED=true
            echo DEMO_PASSWORD=1234
            echo USE_OPENAI=false
            echo USE_HUGGINGFACE=true
            echo AI_PREFER_TURKISH_MODELS=true
            echo DATABASE_TYPE=sqlite
            echo ALLOWED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000,*
        ) > .env
        echo %GREEN%✅ Minimal environment dosyası oluşturuldu%NC%
    )
) else (
    echo %GREEN%✅ Environment dosyası mevcut%NC%
)

:: Sistem doğrulaması
echo %BLUE%ℹ️  Sistem doğrulaması yapılıyor...%NC%
python -c "import fastapi, uvicorn, sqlalchemy; print('✅ Temel paketler mevcut')" 2>nul
if errorlevel 1 (
    echo %RED%❌ Sistem doğrulaması başarısız%NC%
    echo Bazı paketler eksik olabilir. requirements.txt'i kontrol edin.
    pause
    exit /b 1
)
echo %GREEN%✅ Sistem doğrulaması başarılı%NC%

:: Kurulum tamamlandı
echo.
echo %GREEN%🎉 KURULUM TAMAMLANDI!%NC%
echo ======================
echo.
echo %BLUE%ℹ️  Sistemi başlatmak için:%NC%
echo   python main.py
echo.
echo %BLUE%ℹ️  Erişim bilgileri:%NC%
echo   🌐 URL: http://localhost:8000
echo   👤 Kullanıcı: demo
echo   🔑 Şifre: 1234
echo   📚 API Docs: http://localhost:8000/docs
echo.

:: Sunucuyu başlatmak isteyip istemediğini sor
set /p "choice=🚀 Sunucuyu şimdi başlatmak ister misiniz? (y/N): "
if /i "%choice%"=="y" (
    echo.
    echo %BLUE%ℹ️  Sunucu başlatılıyor...%NC%
    echo.
    python main.py
) else (
    echo.
    echo %BLUE%ℹ️  Sunucuyu daha sonra başlatabilirsiniz:%NC%
    echo   python main.py
    echo.
    echo Script'i kapatmak için herhangi bir tuşa basın...
    pause >nul
)

endlocal
