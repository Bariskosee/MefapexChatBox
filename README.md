# 🏭 MEFAPEX Turkish AI Chatbot

> Fabrika çalışanları için Türkçe AI destekli soru-cevap sistemi - Modern Modüler Mimari & Docker Ready

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.116+-green.svg)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-blue.svg)](https://www.postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com)
[![Hugging Face](https://img.shields.io/badge/HuggingFace-Transformers-yellow.svg)](https://huggingface.co)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

MEFAPEX fabrikası için geliştirilmiş **production-ready** Türkçe AI chatbot sistemi. PostgreSQL database, modüler mimari ve Docker orchestration ile enterprise-level deployment.

## 🔄 Recent Updates (v2.2.0)
- ✅ **Unified Main File**: Eliminated duplicate main files (`main.py` & `main_postgresql.py`)
- 🗄️ **PostgreSQL Focus**: System now uses PostgreSQL exclusively
- 🛠️ **Better Maintainability**: Single main file reduces code duplication by 95%
- 📝 **Enhanced Logging**: Improved startup and error logging
- 🎯 **See [REFACTORING_LOG.md](REFACTORING_LOG.md) for details**

## 🚀 Hızlı Başlangıç

### 🔍 Uyumluluk Kontrolü (Önerilen)
```bash
# Repository'yi klonlayın
git clone https://github.com/Bariskosee/MefapexChatBox.git
cd MefapexChatBox

# Python sürümünüzü ve sistem uyumluluğunu kontrol edin
python check_compatibility.py
```

### ⚡ Otomatik Kurulum (Önerilen)
```bash
# Repository'yi klonlayın (eğer henüz yapmadıysanız)
git clone https://github.com/Bariskosee/MefapexChatBox.git
cd MefapexChatBox

# Otomatik kurulum scriptini çalıştırın
python setup.py

# Uygulamayı başlatın
python main.py
```

### 🐳 Docker ile Hızlı Başlatma
```bash
git clone https://github.com/Bariskosee/MefapexChatBox.git
cd MefapexChatBox
docker-compose up -d
```

🎉 **İşte bu kadar!** Sistem `http://localhost:8000` adresinde hazır.

## 📋 Gereksinimler

### ✅ Minimum Sistem Gereksinimleri
- **Python**: 3.11+ (Zorunlu)
- **RAM**: 4GB+ (AI modelleri için)
- **Disk**: 2GB+ boş alan
- **İşletim Sistemi**: Windows 10+, macOS 10.15+, Linux Ubuntu 20.04+

### 🐍 Python Kurulumu & Sürüm Uyumluluğu

**🎯 Önerilen Python Sürümleri:**
- ✅ **Python 3.11**: Tam uyumlu (Önerilen)
- ✅ **Python 3.12**: Tam uyumlu
- ⚠️ **Python 3.13**: Uyumlu (bazı paketler özel kurulum gerektirebilir)

**Windows:**
```bash
# Microsoft Store'dan Python 3.11+ indirin
# VEYA python.org'dan resmi installer

python --version  # 3.11+ olmalı
```

**macOS:**
```bash
# Homebrew ile
brew install python@3.11

# VEYA python.org'dan resmi installer
python3.11 --version
```

**Linux (Ubuntu/Debian):**
```bash
# APT ile
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-pip

# Versiyonu kontrol edin
python3.11 --version
```

### 🔧 Python 3.13 Özel Notları
Python 3.13 kullanıyorsanız:
1. `setup.py` otomatik olarak uyumluluğu sağlar
2. Alternatif olarak: `pip install -r requirements-python313.txt`
3. Bazı paketler daha yeni sürümlerde yüklenecektir

## 🚀 Özellikler

### 🏗️ **Mimari & Deployment**
- **🐳 Docker Orchestration**: Tek komutla complete deployment
- **🔧 Modüler Mimari**: Microservice-ready architecture  
- **⚡ Lazy Loading**: AI models ve performance optimization
- **📊 Advanced Monitoring**: Prometheus + health checks
- **🔄 Auto-scaling**: Production-ready container setup

### � **Chatbot Özellikleri**  
- **🌙 Modern Dark Theme**: Göz dostu koyu tema tasarımı
- **🇹🇷 Türkçe Dil Desteği**: Tamamen Türkçe soru-cevap sistemi
- **🔍 Vector Search**: Qdrant ile benzerlik tabanlı arama
- **🤖 Hybrid AI**: OpenAI + Hugging Face ile çoklu AI desteği
- **👤 JWT Authentication**: Güvenli kullanıcı yönetimi
- **📱 Responsive Design**: Mobil uyumlu modern web arayüzü
- **🔄 WebSocket**: Gerçek zamanlı mesajlaşma
- **🧠 Advanced Caching**: Multi-level caching system

## 🛠️ Teknolojiler

### 🏗️ **Backend Architecture**
- **API Framework**: FastAPI + WebSockets  
- **Modüler Yapı**: Router-based microservice architecture
- **Authentication**: JWT + middleware security
- **Caching**: Multi-level Redis + memory caching
- **Performance**: Lazy loading + connection pooling

### 🗄️ **Database & Storage**
- **Primary DB**: PostgreSQL (production-ready relational database)
- **Vector DB**: Qdrant (document embeddings)  
- **Cache Layer**: Redis (session & response caching)
- **File Storage**: Docker volumes for persistence

### 🤖 **AI & ML Stack**
- **AI Engines**: OpenAI GPT-3.5 + Hugging Face Transformers
- **Embeddings**: Sentence Transformers (multilingual)
- **Vector Search**: Qdrant similarity search
- **Optimization**: Model lazy loading + response caching

### � **DevOps & Deployment**
- **Containerization**: Docker + Docker Compose
- **Reverse Proxy**: Nginx (load balancing + SSL)
- **Monitoring**: Prometheus + health checks
- **Security**: Container isolation + non-root user

## 🐳 Deployment Seçenekleri

### 🚀 **1. Docker (Önerilen)**
```bash
# Tek komutla complete setup
./start-docker.sh

# Manuel Docker Compose  
docker-compose up -d

# Production deployment
docker-compose -f docker-compose.prod.yml up -d
```

### 🔧 **Manuel Kurulum**
```bash
# 1. Repository'yi klonlayın
git clone https://github.com/Bariskosee/MefapexChatBox.git
cd MefapexChatBox

# 2. Python 3.11+ kontrol edin
python --version  # 3.11+ olmalı

# 3. Virtual environment oluşturun
python -m venv .venv

# 4. Virtual environment'ı aktive edin
# Linux/macOS:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

# 5. Dependencies'leri yükleyin
pip install --upgrade pip
pip install -r requirements.txt

# 6. Environment dosyası oluşturun
cp .env.example .env  # Ayarları düzenleyin

# 7. Uygulamayı başlatın
python main.py
```

### 🔧 **İsteğe Bağlı Servisler**
```bash
# Vector search için Qdrant (isteğe bağlı)
docker run -p 6333:6333 qdrant/qdrant

# Caching için Redis (isteğe bağlı)
docker run -p 6379:6379 redis:alpine
```

## 🌐 **Erişim Adresleri**

| Servis | URL | Açıklama |
|--------|-----|----------|
| 🚀 Ana Uygulama | http://localhost:8000 | MefapexChatBox |
| 📚 API Docs | http://localhost:8000/docs | Swagger UI |
| 🏥 Health Check | http://localhost:8000/health | Sistem durumu |
| 🗄️ Qdrant | http://localhost:6333 | Vector Database |
| 🗂️ Redis | localhost:6379 | Cache Service |
| 🌍 Nginx | http://localhost:80 | Reverse Proxy |
| 📊 Monitoring | http://localhost:9090 | Prometheus |

## 💡 Kullanım

1. Tarayıcıda `http://localhost:8000` adresine gidin
2. Modern dark theme ile karşılaşacaksınız
3. Demo bilgileri ile giriş yapın:
   - **Kullanıcı Adı**: demo
   - **Şifre**: 1234
4. Chat arayüzünde Türkçe sorularınızı yazın
5. AI asistandan anında yanıt alın
6. Chat geçmişiniz otomatik olarak kaydedilir

## 📝 Örnek Sorular

- "Fabrika çalışma saatleri nelerdir?"
- "İzin başvurusu nasıl yapılır?"
- "Güvenlik kuralları nelerdir?"
- "Vardiya değişiklikleri nasıl yapılır?"
- "Python nedir?"
- "Yapay zeka hakkında bilgi ver"
- "15 + 27 kaç eder?"

## 🏗️ **Modüler Proje Yapısı**

```
MefapexChatBox/
├── 🐳 Docker Infrastructure
│   ├── docker-compose.yml      # Multi-container orchestration
│   ├── Dockerfile             # Production-optimized image
│   ├── nginx/nginx.conf      # Reverse proxy config
│   └── monitoring/           # Prometheus setup
│
├── 🏗️ Modular Architecture  
│   ├── main.py              # Modern unified entry point
│   ├── api/                 # API endpoint modules
│   │   ├── auth.py          # Authentication endpoints
│   │   ├── chat.py          # Chat functionality
│   │   └── health.py        # Health checks
│   └── services/            # Business logic layer
│       ├── auth_service.py    # Authentication service
│       ├── model_manager.py   # AI model management
│       ├── database_manager.py # Database operations
│       └── websocket_manager.py # WebSocket management
│
├── 🗄️ Database & Storage
│   ├── database/            # PostgreSQL init scripts
│   ├── models_cache/        # AI model cache
│   ├── content/            # Static responses
│   └── logs/               # Application logs
│
├── 🌐 Frontend
│   ├── static/index.html    # Main web interface
│   ├── static/script.js     # Frontend JavaScript
│   └── static/session-manager.js # Session management
│
└── 📋 Configuration
    ├── requirements.txt     # Python dependencies
    ├── .env.example        # Environment template
    ├── config.py           # Configuration management
    ├── middleware.py       # Security middleware
    └── security_config.py  # Security settings
```

## 📊 **Performance & Monitoring**

### 🚀 **Performans Optimizasyonları**
- ✅ **Lazy Loading**: AI models sadece gerektiğinde yüklenir
- ✅ **Multi-level Caching**: Redis + memory + response caching
- ✅ **Connection Pooling**: Database connection optimization  
- ✅ **Query Optimization**: LIMIT + indexed queries
- ✅ **Background Tasks**: Async processing + cleanup

### 📈 **Monitoring & Health Checks**
- ✅ **Real-time Metrics**: CPU, memory, disk, network
- ✅ **API Performance**: Request times + error rates
- ✅ **Health Endpoints**: `/health`, `/metrics`, `/stats`
- ✅ **Prometheus Integration**: Production monitoring ready
- ✅ **Auto-restart**: Container health checks

### 🔒 **Security & Production**
- ✅ **Container Isolation**: Non-root user + resource limits
- ✅ **Network Security**: Internal networks + rate limiting
- ✅ **JWT Authentication**: Secure session management
- ✅ **Input Validation**: SQL injection + XSS protection
- ✅ **CORS Protection**: Cross-origin security

## 🔍 **API Endpoints**

### 🔐 **Authentication**
- `POST /auth/login` - JWT token alımı
- `POST /auth/register` - Yeni kullanıcı kaydı  
- `GET /auth/verify` - Token doğrulama
- `POST /auth/refresh` - Token yenileme

### 💬 **Chat System**
- `POST /chat/public` - Anonim chat mesajı
- `POST /chat/authenticated` - Kimlik doğrulamalı chat
- `GET /chat/history/{user_id}` - Chat geçmişi
- `GET /chat/sessions/{user_id}` - Chat oturumları
- `POST /chat/sessions/{user_id}/new` - Yeni chat oturumu
- `WebSocket /ws/{user_id}` - Gerçek zamanlı chat

### 🏥 **Health & Monitoring**  
- `GET /health` - Temel sistem durumu
- `GET /health/comprehensive` - Detaylı sistem analizi
- `GET /metrics` - Prometheus metrics
- `GET /stats` - Performance statistics
- `GET /system/status` - Sistem konfigürasyonu

### 🚀 **Development & Testing**
- `GET /` - Ana sayfa (Dark Theme)
- `GET /docs` - Swagger API dokümantasyonu
- `GET /redoc` - ReDoc API dokümantasyonu

## 🧪 **Test & Validation**

### 🔍 **Quick Health Check**
```bash
# Sistem durumu
curl http://localhost:8000/health

# Comprehensive check
curl http://localhost:8000/health/comprehensive

# Performance stats
curl http://localhost:8000/stats
```

### 💬 **Chat API Test**
```bash
# Anonim chat
curl -X POST "http://localhost:8000/chat/public" \
     -H "Content-Type: application/json" \
     -d '{"message": "Merhaba, nasılsın?"}'

# Authenticated chat (JWT token gerekli)
curl -X POST "http://localhost:8000/chat/authenticated" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -d '{"message": "Fabrika kuralları nelerdir?"}'
```

### 🐳 **Docker Validation**
```bash
# Container durumu
docker-compose ps

# Service logs
docker-compose logs -f mefapex-app

# Resource monitoring  
docker stats
```

## ⚙️ **Konfigürasyon**

### 🐳 **Docker Environment (.env.docker)**
```env
# 🏗️ Application Settings
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=your-super-secret-key

# 🤖 AI Configuration  
USE_OPENAI=false
USE_HUGGINGFACE=true
OPENAI_API_KEY=your-openai-key

# 🗄️ Database URLs
POSTGRES_HOST=postgres
POSTGRES_USER=mefapex  
POSTGRES_PASSWORD=secure_password
POSTGRES_DB=mefapex_chatbot
QDRANT_HOST=qdrant
REDIS_HOST=redis

# 🌐 Network & Security
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
RATE_LIMIT_PER_MINUTE=60
```

### 🔧 **Manuel Setup (.env)**
```env
# Local development
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=dev-secret-key

# AI Services
USE_OPENAI=false  # Set true for OpenAI
USE_HUGGINGFACE=true
OPENAI_API_KEY=sk-your-api-key

# Local Services  
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=mefapex
POSTGRES_PASSWORD=secure_password
POSTGRES_DB=mefapex_chatbot
QDRANT_HOST=localhost
QDRANT_PORT=6333
REDIS_HOST=localhost
REDIS_PORT=6379
```

### 🚀 **Production Checklist**
- [ ] Change default `SECRET_KEY`
- [ ] Set proper `CORS_ORIGINS`  
- [ ] Configure SSL certificates
- [ ] Set up firewall rules
- [ ] Enable monitoring alerts
- [ ] Configure backup strategy
- [ ] Set resource limits
- [ ] Test disaster recovery

## 🚧 **Geliştirme Roadmap**

### ✅ **Tamamlanan (v2.0)**
- ✅ **Modüler Mimari**: Router-based microservice architecture
- ✅ **Docker Orchestration**: One-command deployment
- ✅ **Performance Optimization**: 95/100 score achieved
- ✅ **Advanced Caching**: Multi-level caching system
- ✅ **Production Monitoring**: Comprehensive health checks
- ✅ **Security Hardening**: Container isolation + JWT auth
- ✅ **Auto-scaling Ready**: Load balancer + health checks

### 🔄 **Geliştirme Aşamasında (v2.1)**
- 🔄 **Kubernetes Deployment**: K8s manifests + Helm charts
- 🔄 **CI/CD Pipeline**: GitHub Actions deployment
- 🔄 **Advanced Analytics**: User behavior tracking
- 🔄 **Multi-language Support**: English interface option
- 🔄 **Voice Chat**: Speech-to-text integration

### � **Gelecek Özellikler (v3.0)**
- � **ERP Integration**: TESLA/LOGO/SAP connectivity
- � **Multi-tenant Support**: Organization-level isolation
- � **Admin Dashboard**: User management + analytics
- � **File Upload**: Document processing + RAG
- � **Mobile App**: React Native mobile client
- � **Workflow Automation**: Process automation integration

## 🐛 Sorun Giderme

### 🐍 Python Sürüm Sorunları

**Virtual Environment Python Sürüm Uyumsuzluğu:**
```bash
# Problemi kontrol edin
python --version
source .venv/bin/activate
python --version

# Farklı sürümler gösteriyorsa:
rm -rf .venv
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Python 3.13 Kurulum Sorunları:**
```bash
# Özel Python 3.13 requirements kullanın
pip install -r requirements-python313.txt

# Manuel greenlet kurulumu
pip install greenlet>=3.2.0

# Scikit-learn için
pip install scikit-learn>=1.3.0
```

### Qdrant Bağlantı Hatası
```bash
# Qdrant'ın çalıştığını kontrol edin
curl http://localhost:6333/health
```

### OpenAI API Hatası
- `.env` dosyasında API anahtarınızı kontrol edin
- API kotanızı kontrol edin
- `USE_OPENAI=false` yaparak Hugging Face kullanın

### Model Yükleme Hatası
```bash
# Hugging Face modellerini manuel yükleyin
python -c "from model_manager import model_manager; model_manager.warmup_models()"
```

### Port Çakışması
```bash
# Farklı port kullanın
uvicorn main:app --port 8001
```

## 🌟 **Katkıda Bulunma**

### 🤝 **Katkı Süreci**
1. **Repository'yi fork edin**
2. **Feature branch oluşturun** (`git checkout -b feature/amazing-feature`)
3. **Değişikliklerinizi commit edin** (`git commit -m 'Add amazing feature'`)
4. **Branch'inizi push edin** (`git push origin feature/amazing-feature`)
5. **Pull Request açın**

### 🎯 **Katkı Alanları**
- � **Backend Development**: FastAPI optimization, AI integration
- 🎨 **Frontend Development**: Modern UI/UX improvements
- 🧪 **Testing**: Unit tests, integration tests, E2E tests
- 📚 **Documentation**: README updates, API documentation
- 🐳 **DevOps**: Docker optimization, Kubernetes deployment
- 🤖 **AI/ML**: Model optimization, new AI provider integration

## 📞 **Destek & İletişim**

### 🆘 **Destek Kanalları**
- 📧 **Email**: info@mefapex.com
- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/Bariskosee/MefapexChatBox/issues)
- 💬 **Feature Requests**: GitHub Discussions
- 📊 **Monitoring**: Prometheus metrics at `/metrics`

### 🏥 **Health Check Endpoints**
```bash
# System health
curl http://localhost:8000/health

# Detailed metrics  
curl http://localhost:8000/metrics

# Performance stats
curl http://localhost:8000/stats
```

## 📄 **Lisans**

Bu proje MIT lisansı altında yayınlanmıştır. Detaylar için `LICENSE` dosyasını inceleyebilirsiniz.

**© 2024 MEFAPEX - Enterprise AI Chatbot Solution**

---

<div align="center">

### 🚀 **Production Ready - Docker Optimized** 

**Built with ❤️ for scalable enterprise AI solutions**

![Docker Ready](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Production-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![AI Powered](https://img.shields.io/badge/AI-Powered-FF6B35?style=for-the-badge&logo=openai&logoColor=white)
![Kubernetes Ready](https://img.shields.io/badge/K8s-Ready-326CE5?style=for-the-badge&logo=kubernetes&logoColor=white)

**🏭 Designed for MEFAPEX Factory Efficiency & Worker Support**

</div>
