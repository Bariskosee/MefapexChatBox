# 🚀 MEFAPEX ChatBox - Makefile
# Kolay kullanım için komutlar

.PHONY: help install start stop test clean docker-start docker-stop health

# Varsayılan komut
help:
	@echo "🚀 MEFAPEX ChatBox - Kullanılabilir Komutlar:"
	@echo ""
	@echo "📦 Kurulum:"
	@echo "  make install     - Tam kurulum (virtual env + dependencies)"
	@echo "  make quick       - Ultra hızlı kurulum"
	@echo ""
	@echo "🚀 Çalıştırma:"
	@echo "  make start       - Sunucuyu başlat"
	@echo "  make stop        - Sunucuyu durdur"
	@echo "  make restart     - Sunucuyu yeniden başlat"
	@echo ""
	@echo "🐳 Docker:"
	@echo "  make docker      - Docker ile başlat"
	@echo "  make docker-stop - Docker'ı durdur"
	@echo ""
	@echo "🧪 Test & Kontrol:"
	@echo "  make test        - Testleri çalıştır"
	@echo "  make health      - Sistem durumunu kontrol et"
	@echo "  make logs        - Logları göster"
	@echo ""
	@echo "🧹 Temizlik:"
	@echo "  make clean       - Cache ve temp dosyaları temizle"
	@echo "  make reset       - Tam sıfırlama"

# Ultra hızlı kurulum
quick:
	@echo "🚀 Ultra hızlı kurulum başlatılıyor..."
	@chmod +x quick-start.sh
	@./quick-start.sh

# Tam kurulum
install:
	@echo "📦 Tam kurulum başlatılıyor..."
	@python -m venv .venv
	@echo "Activating virtual environment..."
	@. .venv/bin/activate && pip install --upgrade pip
	@. .venv/bin/activate && pip install -r requirements.txt
	@if [ ! -f .env ]; then cp .env.example .env 2>/dev/null || echo "ENVIRONMENT=development" > .env; fi
	@echo "✅ Kurulum tamamlandı!"
	@echo "🚀 Başlatmak için: make start"

# Sunucuyu başlat
start:
	@echo "🚀 MEFAPEX Sunucusu başlatılıyor..."
	@. .venv/bin/activate && python main.py

# Docker ile başlat
docker:
	@echo "🐳 Docker ile başlatılıyor..."
	@docker-compose up -d
	@echo "✅ Docker servisleri başlatıldı"
	@echo "🌐 URL: http://localhost:8000"

# Docker'ı durdur
docker-stop:
	@echo "🐳 Docker servisleri durduruluyor..."
	@docker-compose down

# Sistem durumu kontrol
health:
	@echo "🏥 Sistem durumu kontrol ediliyor..."
	@curl -s http://localhost:8000/health | python -m json.tool || echo "❌ Sunucu çalışmıyor"

# Testleri çalıştır
test:
	@echo "🧪 Testler çalıştırılıyor..."
	@. .venv/bin/activate && python -m pytest tests/ -v

# Logları göster
logs:
	@echo "📋 Son loglar:"
	@tail -f logs/app.log 2>/dev/null || echo "❌ Log dosyası bulunamadı"

# Cache temizle
clean:
	@echo "🧹 Cache temizleniyor..."
	@rm -rf __pycache__
	@rm -rf .pytest_cache
	@rm -rf models_cache/*
	@find . -name "*.pyc" -delete
	@echo "✅ Temizlik tamamlandı"

# Tam sıfırlama
reset: clean
	@echo "🔄 Tam sıfırlama yapılıyor..."
	@rm -rf .venv
	@rm -f .env
	@rm -f *.db
	@echo "✅ Sıfırlama tamamlandı"
	@echo "📦 Yeniden kurmak için: make install"

# Sunucuyu yeniden başlat
restart:
	@echo "🔄 Sunucu yeniden başlatılıyor..."
	@pkill -f "python main.py" || true
	@sleep 2
	@make start

# Geliştirici modu
dev:
	@echo "👨‍💻 Geliştirici modu başlatılıyor..."
	@. .venv/bin/activate && python main.py --reload

# Production kurulum
production:
	@echo "🏭 Production kurulumu..."
	@cp .env.example .env.production
	@echo "⚠️  .env.production dosyasını düzenleyin!"
	@echo "🐳 Production için: docker-compose -f docker-compose.prod.yml up -d"
