#!/bin/bash

# MEFAPEX Chatbot Startup Script
# Bu script tüm servisleri başlatır

echo "🚀 MEFAPEX AI Chatbot başlatılıyor..."

# Renk kodları
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonksiyonlar
print_step() {
    echo -e "${BLUE}📋 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 1. Çevre değişkenlerini kontrol et
print_step "Çevre değişkenleri kontrol ediliyor..."
if [ ! -f ".env" ]; then
    print_error ".env dosyası bulunamadı!"
    print_warning "Lütfen .env.example dosyasını .env olarak kopyalayın ve düzenleyin."
    exit 1
fi
print_success "✓ .env dosyası bulundu"

# 2. Python bağımlılıklarını kontrol et
print_step "Python bağımlılıkları kontrol ediliyor..."
if ! pip list | grep -q fastapi; then
    print_warning "Bağımlılıklar yükleniyor..."
    pip install -r requirements.txt
fi
print_success "✓ Python bağımlılıkları hazır"

# 3. Qdrant servisini kontrol et
print_step "Qdrant servisi kontrol ediliyor..."
if ! curl -s http://localhost:6333/health > /dev/null; then
    print_warning "Qdrant servisi çalışmıyor. Docker ile başlatılıyor..."
    if command -v docker &> /dev/null; then
        docker run -d -p 6333:6333 --name qdrant qdrant/qdrant
        sleep 5
        print_success "✓ Qdrant servisi başlatıldı"
    else
        print_error "Docker bulunamadı. Lütfen Qdrant'ı manuel olarak başlatın."
        exit 1
    fi
else
    print_success "✓ Qdrant servisi çalışıyor"
fi

# 4. Vector verilerini yükle
print_step "Vector verileri kontrol ediliyor..."
if ! python -c "from qdrant_client import QdrantClient; client = QdrantClient('localhost', 6333); client.get_collection('mefapex_faq')" 2>/dev/null; then
    print_warning "Vector verileri yükleniyor..."
    python embedding_loader.py
    print_success "✓ Vector verileri yüklendi"
else
    print_success "✓ Vector verileri mevcut"
fi

# 5. FastAPI uygulamasını başlat
print_step "FastAPI uygulaması başlatılıyor..."
print_success "🌐 Uygulama http://localhost:8000 adresinde çalışacak"
print_success "🔑 Demo giriş: kullanıcı='demo', şifre='1234'"

echo ""
echo -e "${GREEN}🎉 MEFAPEX AI Chatbot hazır!${NC}"
echo ""

# Uygulamayı başlat
python main.py
