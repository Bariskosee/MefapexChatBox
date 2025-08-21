# 🏭 MEFAPEX AI Chatbot

<div align="center">

![MEFAPEX Logo](static/images/logo.png)

**Fabrika çalışanları için Türkçe AI destekli soru-cevap sistemi**

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.116+-green.svg)](https://fastapi.tiangolo.com)
[![Turkish AI](https://img.shields.io/badge/Turkish-AI%20Ready-red.svg)](https://github.com/Bariskosee/MefapexChatBox)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Quick Setup](https://img.shields.io/badge/Setup-30%20seconds-brightgreen.svg)](https://github.com/Bariskosee/MefapexChatBox#-hızlı-başlangıç)
[![One Command](https://img.shields.io/badge/Install-One%20Command-orange.svg)](https://github.com/Bariskosee/MefapexChatBox#-ultra-hızlı-kurulum-30-saniye)

</div>

## 🌟 Öne Çıkan Özellikler

### 🤖 **Gelişmiş Türkçe AI Desteği**
- **🇹🇷 Türkçe Optimize Modeller**: `emrecan/bert-base-turkish-cased-mean-nli-stsb-tr`
- **🔥 Lazy Loading**: AI modelleri sadece ihtiyaç duyulduğunda yüklenir (70% hızlı başlangıç)
- **💾 Bellek Optimizasyonu**: Otomatik temizlik ve memory management
- **🔄 Türkçe Metin Üretimi**: `ytu-ce-cosmos/turkish-gpt2-large`
- **🔍 Otomatik Dil Algılama**: Dinamik model seçimi
- **🌐 Çok Dilli Fallback**: İngilizce destek

### 🎨 **Modern Kullanıcı Deneyimi**
- **🌙 Dark Theme**: Göz dostu koyu tema tasarımı
- **📱 Responsive Design**: Mobil uyumlu arayüz
- **⚡ Gerçek Zamanlı Chat**: WebSocket desteği
- **🔄 Distributed WebSocket**: Yatay ölçekleme ve yük dağıtımı
- **🌐 Multi-Worker Support**: Redis pub/sub ile çoklu worker desteği
- **💾 Session Persistence**: WebSocket oturumları Redis'te saklanır
- **💬 Session Yönetimi**: Oturum bazlı chat geçmişi

### 🔐 **Güvenlik & Performans**
- **🔑 JWT Authentication**: Güvenli kullanıcı yönetimi
- **🚦 Rate Limiting**: API koruması
- **💾 Smart Caching**: Performans optimizasyonu
- **📊 Memory Monitoring**: Kaynak izleme

## 🚀 Hızlı Başlangıç

### ⚡ **Ultra Hızlı Kurulum (30 Saniye!)**

**Tek komut ile kurulum:**
```bash
# 1. Repository'yi klonlayın ve ultra hızlı kurulum
git clone https://github.com/Bariskosee/MefapexChatBox.git
cd MefapexChatBox

# 2. Tek komut kurulum
./quick-start.sh    # Linux/macOS
# VEYA
quick-start.bat     # Windows
```

**Makefile ile (Önerilen):**
```bash
git clone https://github.com/Bariskosee/MefapexChatBox.git
cd MefapexChatBox
make quick          # Ultra hızlı kurulum + başlatma
```

🎉 **30 saniyede hazır!** Sistem `http://localhost:8000` adresinde çalışıyor.

### 🔧 **Alternatif Kurulum Yöntemleri**

**Manuel Kurulum:**
```bash
git clone https://github.com/Bariskosee/MefapexChatBox.git
cd MefapexChatBox
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows
pip install -r requirements.txt
cp .env.example .env
python main.py
```

**Docker ile Hızlı Başlatma:**
```bash
git clone https://github.com/Bariskosee/MefapexChatBox.git
cd MefapexChatBox
docker-compose up -d
# VEYA
make docker
```

## 📋 Sistem Gereksinimleri

### ✅ Minimum Gereksinimler
- **Python**: 3.11+ (Önerilen: 3.13+)
- **RAM**: 4GB+ (AI modelleri için)
- **Disk**: 2GB+ boş alan
- **İşletim Sistemi**: Windows 10+, macOS 10.15+, Linux Ubuntu 20.04+

### � Desteklenen Python Sürümleri
- ✅ **Python 3.13**: Tam uyumlu (Test edildi)
- ✅ **Python 3.12**: Tam uyumlu 
- ✅ **Python 3.11**: Tam uyumlu

## 🏗️ Proje Mimarisi

```
MefapexChatBox/
├── 🌐 Frontend
│   ├── static/
│   │   ├── index.html          # Ana web arayüzü (Dark Theme)
│   │   ├── script.js           # Ana JavaScript
│   │   ├── websocket_client.js # WebSocket yönetimi
│   │   ├── session-manager.js  # Oturum yönetimi
│   │   └── images/            # Logo ve görseller
│
├── 🔧 Backend API
│   ├── main.py                # Ana uygulama giriş noktası
│   ├── api/
│   │   ├── auth.py            # Authentication endpoints
│   │   ├── chat.py            # Chat API endpoints
│   │   └── health.py          # Health check endpoints
│   ├── core/                  # Çekirdek konfigürasyon
│   │   ├── configuration.py   # Uygulama ayarları
│   │   └── app_factory.py     # FastAPI app factory
│   └── middleware.py          # Güvenlik middleware
│
├── 🤖 AI & ML
│   ├── model_manager.py       # AI model yönetimi
│   ├── content_manager.py     # İçerik yönetimi
│   └── models_cache/          # Önbelleğe alınan modeller
│
├── 🗄️ Database
│   ├── database/
│   │   ├── manager.py         # Database yöneticisi
│   │   ├── interface.py       # Database arayüzü
│   │   └── models/           # Database modelleri
│   └── simple_schema.sql      # Veritabanı şeması
│
├── 🔐 Security & Auth
│   ├── auth_service.py        # Kimlik doğrulama servisi
│   ├── security_config.py     # Güvenlik konfigürasyonu
│   └── websocket_manager.py   # WebSocket güvenliği
│
├── 🛠️ Configuration
│   ├── .env.example          # Environment değişkenleri
│   ├── config.py            # Basit konfigürasyon
│   ├── requirements.txt     # Python bağımlılıkları
│   └── docker-compose.yml   # Docker konfigürasyonu
│
└── 📊 Monitoring & Testing
    ├── memory_monitor.py     # Bellek izleme
    ├── tests/               # Test dosyaları
    └── logs/               # Log dosyaları
```

## 🛠️ Teknoloji Stack'i

### �️ **Backend Framework**
- **FastAPI**: Modern, hızlı web framework
- **Uvicorn**: ASGI server
- **WebSockets**: Gerçek zamanlı iletişim
- **Python 3.13**: En güncel Python desteği

### 🤖 **AI & Machine Learning**
- **Hugging Face Transformers**: AI model desteği
- **PyTorch**: Deep learning framework
- **Sentence Transformers**: Metin embedding'leri
- **Turkish Models**: Türkçe optimize edilmiş modeller
  - `emrecan/bert-base-turkish-cased-mean-nli-stsb-tr`
  - `ytu-ce-cosmos/turkish-gpt2-large`

### 🗄️ **Database & Storage**
- **SQLite**: Varsayılan veritabanı (development)
- **PostgreSQL**: Production veritabanı desteği
- **SQLAlchemy**: ORM
- **Qdrant**: Vector database (opsiyonel)

### 🔐 **Security & Authentication**
- **JWT**: JSON Web Tokens
- **Passlib + Bcrypt**: Şifre hashleme
- **CORS Middleware**: Cross-origin desteği
- **Rate Limiting**: API koruması

### 💾 **Caching & Performance**
- **Redis**: Distributed cache (opsiyonel)
- **Memory Monitor**: Kaynak izleme
- **Response Cache**: API yanıt önbelleği

## 🌐 Erişim Adresleri

| Servis | URL | Açıklama |
|--------|-----|----------|
| 🏠 **Ana Uygulama** | http://localhost:8000 | MEFAPEX AI Chatbot |
| 📚 **API Dokümantasyonu** | http://localhost:8000/docs | Swagger UI |
| 🏥 **Health Check** | http://localhost:8000/health | Sistem durumu |
| � **Admin Panel** | http://localhost:8000/admin | Yönetim paneli |

## � Kullanım Rehberi

### 🔑 **Giriş Bilgileri**
```
� Kullanıcı Adı: demo
🔒 Şifre: 1234
```

### � **Chat Kullanımı**
1. Tarayıcıda `http://localhost:8000` adresine gidin
2. Modern dark theme arayüzü ile karşılaşın
3. Demo bilgileri ile giriş yapın
4. Chat alanında Türkçe sorularınızı yazın
5. AI asistandan anında yanıt alın
6. Oturum geçmişiniz otomatik olarak kaydedilir

### 📝 **Örnek Sorular**

**👷 Fabrika İle İlgili:**
- "Fabrika çalışma saatleri nelerdir?"
- "İzin başvurusu nasıl yapılır?"
- "Güvenlik kuralları nelerdir?"
- "Vardiya değişiklikleri nasıl yapılır?"

**🤖 Genel AI Soruları:**
- "Python nedir?"
- "Yapay zeka hakkında bilgi ver"
- "15 + 27 kaç eder?"
- "Bugünün tarihi nedir?"

## 🔍 API Endpoints

### 🔐 **Authentication**
```http
POST /login                    # Kullanıcı girişi
POST /register                 # Yeni kullanıcı kaydı
GET  /me                      # Kullanıcı bilgileri
POST /logout                  # Çıkış
```

### 💬 **Chat System**
```http
POST /chat/public             # Anonim chat
POST /chat/authenticated      # Kimlik doğrulamalı chat
GET  /chat/sessions/{user_id} # Chat oturumları
POST /chat/sessions/save      # Oturum kaydet
```

### 🏥 **Health & Monitoring**
```http
GET  /health                  # Sistem durumu
GET  /health/comprehensive    # Detaylı sistem analizi
GET  /stats                   # Performance istatistikleri
```

### 🌐 **WebSocket**
```javascript
// WebSocket bağlantısı
ws://localhost:8000/ws/{user_id}
```

## ⚙️ Konfigürasyon

### � **Environment Değişkenleri (.env)**

```bash
# � Uygulama Ayarları
ENVIRONMENT=development
DEBUG=true
APP_PORT=8000

# 🔑 Güvenlik
SECRET_KEY=your-secret-key-here
DEMO_PASSWORD=1234

# 🤖 AI Modelleri
USE_OPENAI=false
USE_HUGGINGFACE=true
AI_PREFER_TURKISH_MODELS=true

# 🗄️ Veritabanı
DATABASE_TYPE=sqlite
POSTGRES_HOST=localhost
POSTGRES_USER=mefapex
POSTGRES_PASSWORD=secure_password

# 🔍 Vector Database (Opsiyonel)
QDRANT_HOST=localhost
QDRANT_PORT=6333

# 📊 Cache (Opsiyonel)
REDIS_HOST=localhost
REDIS_PORT=6379
```

### 🎛️ **Performans Ayarları**

```bash
# Bellek Yönetimi
MAX_MEMORY_MB=4096
CACHE_SIZE=1000

# Rate Limiting
RATE_LIMIT_REQUESTS=200
RATE_LIMIT_CHAT=100

# AI Model Ayarları
AI_MAX_TOKENS=150
AI_TEMPERATURE=0.7
```

## 🧪 Test & Doğrulama

### ✅ **Sistem Durumu Kontrolü**
```bash
# Hızlı sistem kontrolü
curl http://localhost:8000/health

# Detaylı sistem analizi
curl http://localhost:8000/health/comprehensive
```

### 🧪 **API Test**
```bash
# Chat API testi
curl -X POST "http://localhost:8000/chat/public" \
     -H "Content-Type: application/json" \
     -d '{"message": "Merhaba!"}'
```

### 🔍 **Log İzleme**
```bash
# Uygulama logları
tail -f logs/app.log

# Gerçek zamanlı log takibi
python -c "
import logging
logging.basicConfig(level=logging.INFO)
# Log takibi başlar
"
```

## � Sorun Giderme

### 🐍 **Python & Dependencies**

**Virtual Environment Problemleri:**
```bash
# Virtual environment'ı yeniden oluştur
rm -rf .venv
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# veya
.venv\Scripts\activate     # Windows

pip install --upgrade pip
pip install -r requirements.txt
```

**Python 3.13 Uyumluluk Sorunları:**
```bash
# Eğer paket kurulum hatası alırsanız
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt --no-cache-dir
```

### 🤖 **AI Model Problemleri**

**Model Yükleme Hatası:**
```bash
# Model cache'i temizle
rm -rf models_cache/
python -c "
from model_manager import model_manager
model_manager.warmup_models()
"
```

**Bellek Yetersizliği:**
```bash
# .env dosyasında AI model ayarlarını azalt
AI_MAX_TOKENS=50
USE_HUGGINGFACE=true
USE_OPENAI=false
```

### 🌐 **Network & Port Problemleri**

**Port 8000 Kullanımda:**
```bash
# Farklı port kullan
python main.py --port 8001

# Veya .env dosyasında
APP_PORT=8001
```

**CORS Hatası:**
```bash
# .env dosyasında CORS ayarlarını güncelle
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000,*
```

### �️ **Database Problemleri**

**SQLite Database Hatası:**
```bash
# Database dosyasını sil ve yeniden oluştur
rm -f mefapex_chatbot.db
python main.py  # Otomatik olarak yeniden oluşur
```

**PostgreSQL Bağlantı Hatası:**
```bash
# SQLite kullanmaya geç (development için)
# .env dosyasında:
DATABASE_TYPE=sqlite
```

### 📱 **Frontend Problemleri**

**Static Files Yüklenmiyor:**
```bash
# Static klasörünü kontrol et
ls -la static/
# Dosyalar mevcut değilse repository'yi yeniden klonla
```

**WebSocket Bağlantı Hatası:**
```bash
# Firewall/antivirus yazılımını kontrol et
# Tarayıcı console'unda hata mesajlarını kontrol et
```

### 🔧 **Genel Sorun Giderme**

**Uygulama Başlamıyor:**
```bash
# Detaylı log ile başlat
python main.py --log-level DEBUG

# Veya log dosyasını kontrol et
tail -f logs/app.log
```

**Memory Warning'leri:**
```bash
# Normal davranıştır, AI modelleri çok bellek kullanır
# Eğer sistem donuyorsa, modelleri devre dışı bırak:
USE_HUGGINGFACE=false
USE_OPENAI=true  # API key gerekli
```

### � **Yardım Alma**

**Log Dosyası Konumları:**
- `logs/app.log` - Ana uygulama logları
- `logs/error.log` - Hata logları
- Console output - Terminal çıktısı

**Sistem Bilgisi Toplama:**
```bash
# Sistem durumunu kontrol et
curl http://localhost:8000/health/comprehensive

# Python environment bilgisi
python --version
pip list | grep fastapi
```

## 🚀 Production Deployment

### 🐳 **Docker Production Setup**

```bash
# Production için Docker Compose
docker-compose -f docker-compose.prod.yml up -d

# SSL sertifikası ile
docker-compose -f docker-compose.ssl.yml up -d

# Distributed WebSocket ile horizontal scaling
docker-compose -f docker-compose.distributed.yml up -d
```

### 🌐 **Distributed WebSocket Deployment**

**Yatay ölçekleme ve çoklu worker desteği:**

```bash
# Redis ile distributed WebSocket başlatma
export REDIS_URL=redis://localhost:6379/0
export DISTRIBUTED_WEBSOCKET_ENABLED=true
export WORKERS=4

# Distributed modda başlat
./start_distributed.sh

# Veya Gunicorn ile
gunicorn main:app -c gunicorn.conf.py
```

**Özellikler:**
- ✅ **Multi-Worker Support**: 4+ worker ile yük dağıtımı
- ✅ **Session Persistence**: Redis'te WebSocket oturum saklama
- ✅ **Auto-Failover**: Worker çökmelerinde otomatik geçiş
- ✅ **Load Balancing**: Nginx ile otomatik yük dengeleme
- ✅ **Real-time Sync**: Workers arası gerçek zamanlı mesaj senkronizasyonu

**Monitoring:**
```bash
# WebSocket sistem durumu
curl http://localhost:8000/health

# Connection istatistikleri  
curl http://localhost:8000/api/websocket/stats

# Distributed test
python test_distributed_websocket.py
```

### 🔒 **Güvenlik Checklist**

- [ ] **Secret Key**: Güçlü secret key kullan
- [ ] **Environment**: `ENVIRONMENT=production` ayarla
- [ ] **Debug Mode**: `DEBUG=false` yap
- [ ] **CORS**: Sadece güvenli domain'lere izin ver
- [ ] **Rate Limiting**: Uygun limitler belirle
- [ ] **SSL/HTTPS**: SSL sertifikası konfigüre et
- [ ] **Firewall**: Gereksiz portları kapat
- [ ] **Database**: Production database kullan
- [ ] **Backup**: Otomatik yedekleme sistemi kur
- [ ] **Monitoring**: Log ve metrik takibi kur

### 📈 **Performance Optimization**

```bash
# Production ayarları
WORKERS=4
ENVIRONMENT=production
DEBUG=false

# Cache ayarları
REDIS_HOST=your-redis-server
CACHE_TTL=3600

# AI model optimizasyonu
AI_MAX_TOKENS=100
USE_MODEL_CACHE=true
```

## 🤝 Katkıda Bulunma

### 🎯 **Katkı Alanları**
- 🐛 **Bug Reports**: GitHub Issues
- 💡 **Feature Requests**: GitHub Discussions
- 🔧 **Code Contributions**: Pull Requests
- 📚 **Documentation**: README ve Wiki güncellemeleri
- 🧪 **Testing**: Unit ve integration testleri
- 🌐 **Localization**: Çok dilli destek

### 📝 **Development Setup**

```bash
# Development için ek paketler
pip install -r requirements.txt
pip install pytest black isort flake8

# Test çalıştır
python -m pytest tests/

# Code formatting
black . --line-length 88
isort . --profile black
```

### 🔄 **Pull Request Süreci**

1. **Fork** edin
2. **Feature branch** oluşturun: `git checkout -b feature/amazing-feature`
3. **Commit** edin: `git commit -m 'Add amazing feature'`
4. **Push** edin: `git push origin feature/amazing-feature`
5. **Pull Request** açın

## 📄 Lisans & Destek

### 📜 **Lisans**
Bu proje MIT lisansı altında yayınlanmıştır. Detaylar için `LICENSE` dosyasını inceleyebilirsiniz.

### � **İletişim & Destek**
- **Email**: info@mefapex.com
- **GitHub Issues**: [Bug Reports](https://github.com/Bariskosee/MefapexChatBox/issues)
- **GitHub Discussions**: [Feature Requests](https://github.com/Bariskosee/MefapexChatBox/discussions)
- **Wiki**: [Dokümantasyon](https://github.com/Bariskosee/MefapexChatBox/wiki)

### � **Credits**
- **Geliştirici**: [Bariskosee](https://github.com/Bariskosee)
- **AI Models**: Hugging Face Community
- **Turkish NLP**: Emrecan & YTU-CE-COSMOS teams
- **Framework**: FastAPI & Python Community

---

<div align="center">

### 🏭 **MEFAPEX AI Chatbot - Production Ready**

**Fabrika verimliliği ve çalışan desteği için tasarlandı**

![Built with Love](https://img.shields.io/badge/Built%20with-❤️-red.svg)
![Turkish AI](https://img.shields.io/badge/Turkish-AI%20Optimized-red.svg)
![Production Ready](https://img.shields.io/badge/Production-Ready-green.svg)

**🚀 Modern • 🇹🇷 Türkçe • 🤖 AI Powered • 🔒 Secure**

</div>
