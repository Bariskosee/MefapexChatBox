#!/bin/bash

# 🚀 MEFAPEX ChatBox - Ultra Hızlı Kurulum
# Bu script ile 30 saniyede sistemi ayağa kaldırın!

set -e  # Hata durumunda dur

echo "🚀 MEFAPEX ChatBox - Ultra Hızlı Kurulum Başlatılıyor..."
echo "=========================================================="
echo ""

# Renk kodları
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Hata yakalama fonksiyonu
error_exit() {
    echo -e "${RED}❌ HATA: $1${NC}" >&2
    echo ""
    echo "🆘 Yardım için:"
    echo "   - README.md dosyasını okuyun"
    echo "   - GitHub Issues: https://github.com/Bariskosee/MefapexChatBox/issues"
    exit 1
}

# Başarı mesajı
success_msg() {
    echo -e "${GREEN}✅ $1${NC}"
}

# Bilgi mesajı
info_msg() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Uyarı mesajı
warn_msg() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# 1. Python kontrol
info_msg "Python kontrol ediliyor..."
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        error_exit "Python bulunamadı! Python 3.11+ yükleyin: https://python.org"
    fi
    PYTHON_CMD="python"
else
    PYTHON_CMD="python3"
fi

# Python sürüm kontrolü
PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2)
PYTHON_MAJOR=$($PYTHON_CMD -c "import sys; print(sys.version_info.major)")
PYTHON_MINOR=$($PYTHON_CMD -c "import sys; print(sys.version_info.minor)")

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]); then
    error_exit "Python 3.11+ gerekli! Mevcut sürüm: $PYTHON_VERSION"
fi

success_msg "Python $PYTHON_VERSION uygun"

# 2. Virtual Environment
info_msg "Virtual environment kontrol ediliyor..."
if [ ! -d ".venv" ]; then
    info_msg "Virtual environment oluşturuluyor..."
    $PYTHON_CMD -m venv .venv || error_exit "Virtual environment oluşturulamadı"
    success_msg "Virtual environment oluşturuldu"
else
    success_msg "Virtual environment mevcut"
fi

# 3. Virtual Environment Aktivasyonu
info_msg "Virtual environment aktive ediliyor..."
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    source .venv/Scripts/activate || error_exit "Virtual environment aktive edilemedi"
else
    source .venv/bin/activate || error_exit "Virtual environment aktive edilemedi"
fi
success_msg "Virtual environment aktive edildi"

# 4. Dependencies
info_msg "Gerekli paketler yükleniyor... (Bu birkaç dakika sürebilir)"
pip install --quiet --upgrade pip || error_exit "Pip güncellenemedi"
pip install --quiet -r requirements.txt || error_exit "Paketler yüklenemedi"
success_msg "Tüm paketler yüklendi"

# 5. Environment ayarları
info_msg "Environment ayarları yapılandırılıyor..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        success_msg "Environment dosyası oluşturuldu (.env.example'dan kopyalandı)"
    else
        # Minimal .env dosyası oluştur
        cat > .env << EOF
# MEFAPEX ChatBox Configuration
ENVIRONMENT=development
DEBUG=true
APP_PORT=8000
SECRET_KEY=mefapex-development-secret-$(date +%s)
DEMO_USER_ENABLED=true
DEMO_PASSWORD=1234
USE_OPENAI=false
USE_HUGGINGFACE=true
AI_PREFER_TURKISH_MODELS=true
DATABASE_TYPE=sqlite
ALLOWED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000,*
EOF
        success_msg "Minimal environment dosyası oluşturuldu"
    fi
else
    success_msg "Environment dosyası mevcut"
fi

# 6. Quick validation
info_msg "Sistem doğrulaması yapılıyor..."
$PYTHON_CMD -c "
import sys
import pkg_resources

# Temel paketleri kontrol et
required_packages = ['fastapi', 'uvicorn', 'sqlalchemy', 'transformers']
missing = []

for package in required_packages:
    try:
        pkg_resources.get_distribution(package)
    except pkg_resources.DistributionNotFound:
        missing.append(package)

if missing:
    print(f'❌ Eksik paketler: {missing}')
    sys.exit(1)
    
print('✅ Temel paketler mevcut')
" || error_exit "Sistem doğrulaması başarısız"

success_msg "Sistem doğrulaması başarılı"

# 7. Start info
echo ""
echo "🎉 KURULUM TAMAMLANDI!"
echo "======================"
echo ""
info_msg "Sistemi başlatmak için:"
echo "  $PYTHON_CMD main.py"
echo ""
info_msg "Erişim bilgileri:"
echo "  🌐 URL: http://localhost:8000"
echo "  👤 Kullanıcı: demo"
echo "  🔑 Şifre: 1234"
echo "  📚 API Docs: http://localhost:8000/docs"
echo ""

# Sunucuyu başlatmak isteyip istemediğini sor
read -p "🚀 Sunucuyu şimdi başlatmak ister misiniz? (y/N): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    info_msg "Sunucu başlatılıyor..."
    echo ""
    $PYTHON_CMD main.py
else
    info_msg "Sunucuyu daha sonra başlatabilirsiniz:"
    echo "  $PYTHON_CMD main.py"
fi
