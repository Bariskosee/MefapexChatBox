# 🏗️ MEFAPEX Mikroservis Mimarisi

## Genel Bakış

MEFAPEX ChatBox artık mikroservis mimarisi kullanıyor. AI işlemleri ayrı bir servise çıkarıldı ve ana uygulama ile haberleşiyor.

### Mimari Bileşenler

```
┌─────────────────────────────────────────────────────────────────┐
│                    MEFAPEX Mikroservis Mimarisi                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  🌐 Client (Web Browser)                                        │
│         │                                                       │
│         ▼                                                       │
│  🚀 Ana Uygulama (Port 8000)                                   │
│     ├─ Web UI & API Gateway                                     │
│     ├─ Authentication & Session Management                      │
│     ├─ Database Operations                                      │
│     └─ Static Content Management                                │
│         │                                                       │
│         │ HTTP/REST API                                         │
│         ▼                                                       │
│  🤖 AI Mikroservisi (Port 8001)                                │
│     ├─ Embedding Generation                                     │
│     ├─ Text Generation                                          │
│     ├─ Language Detection                                       │
│     └─ Model Management                                         │
│                                                                 │
│  📊 Ortak Altyapı:                                              │
│     ├─ 🗄️ PostgreSQL Database                                   │
│     ├─ 🔍 Qdrant Vector Database                                │
│     └─ 🗂️ Redis Cache                                           │
└─────────────────────────────────────────────────────────────────┘
```

## Servis Detayları

### 🚀 Ana Uygulama (Port 8000)

**Görevler:**
- Web arayüzü sunma
- Kullanıcı kimlik doğrulama
- Session yönetimi
- Database operasyonları
- Static content yönetimi
- AI servisi ile iletişim

**API Endpoints:**
- `GET /` - Ana sayfa
- `POST /login` - Kullanıcı girişi
- `POST /chat` - Basit chat (kimlik doğrulama gerektirmez)
- `POST /chat/authenticated` - Kimlik doğrulamalı chat
- `GET /health` - Sağlık kontrolü
- `GET /docs` - API dokümantasyonu

### 🤖 AI Mikroservisi (Port 8001)

**Görevler:**
- AI model yönetimi
- Metin embedding üretimi
- Metin yanıt üretimi
- Dil tanıma
- Model performans optimizasyonu

**API Endpoints:**
- `POST /embedding` - Embedding üretimi
- `POST /generate` - Temel metin üretimi
- `POST /generate/huggingface` - Gelişmiş HuggingFace yanıt
- `POST /language/detect` - Dil tanıma
- `GET /models/info` - Model bilgileri
- `POST /models/warmup` - Model ısıtma
- `POST /models/cleanup` - Model temizliği
- `GET /health` - Sağlık kontrolü
- `GET /docs` - AI API dokümantasyonu

## Başlatma Seçenekleri

### 1. 🐳 Docker ile (Önerilen)

```bash
# Tüm servisleri Docker ile başlat
docker-compose up -d

# Sadece AI servisi
docker-compose up -d mefapex-ai

# Logları izle
docker-compose logs -f
```

### 2. 🔧 Manuel (Development)

```bash
# Tüm mikroservisleri başlat
./start_microservices.sh

# Sadece AI servisini başlat
./start_ai_service.sh

# Ana uygulamayı başlat (AI servisi çalışırken)
python main.py
```

### 3. 🛠️ Adım Adım

```bash
# 1. Gerekli bağımlılıkları yükle
pip install -r requirements.txt

# 2. AI mikroservisini başlat
python services/ai_service/main.py --host 0.0.0.0 --port 8001

# 3. Ana uygulamayı başlat (yeni terminal)
export AI_SERVICE_ENABLED=true
export AI_SERVICE_HOST=127.0.0.1
export AI_SERVICE_PORT=8001
python main.py
```

## Konfigürasyon

### Ortam Değişkenleri

```bash
# AI Mikroservis Ayarları
AI_SERVICE_ENABLED=true          # AI mikroservisi kullan/kullanma
AI_SERVICE_HOST=127.0.0.1        # AI servis host adresi
AI_SERVICE_PORT=8001             # AI servis portu

# Ana Uygulama Ayarları
DEBUG=true                       # Debug modu
ENVIRONMENT=development          # Ortam (development/production)
POSTGRES_HOST=localhost          # Database host
POSTGRES_PORT=5432              # Database port

# AI Modelleri
AI_MODELS_PATH=./models_cache    # Model cache dizini
TORCH_HOME=./models_cache/torch  # PyTorch model cache
HF_HOME=./models_cache/huggingface  # HuggingFace model cache
```

## Servis İletişimi

### Ana Uygulama → AI Servisi

Ana uygulama AI servisi ile HTTP REST API üzerinden iletişim kurar:

```python
# Örnek: Embedding üretimi
async def generate_embedding(text: str):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://ai-service:8001/embedding",
            json={"text": text}
        ) as response:
            data = await response.json()
            return data["embedding"]
```

### Fallback Mekanizması

AI servisi erişilemezse, ana uygulama otomatik olarak yerel model manager'a geçer:

```python
try:
    # AI servisi ile deneme
    result = await ai_client.generate_embedding(text)
except AIServiceUnavailableError:
    # Yerel model manager ile fallback
    result = local_model_manager.generate_embedding(text)
```

## Performans Avantajları

### 🚀 Ölçeklenebilirlik
- AI servisi bağımsız olarak ölçeklendirilebilir
- Ana uygulama AI yükünden kurtuldu
- Her servis kendi kaynaklarını yönetir

### 🧠 Hafıza Optimizasyonu
- AI modelleri sadece AI servisinde yüklenir
- Ana uygulama hafıza kullanımı %60-70 azaldı
- Model cache'i merkezi olarak yönetilir

### ⚡ Yanıt Süreleri
- AI işlemleri paralel olarak çalışabilir
- Ana uygulama blocking olmadan çalışır
- Lazy loading optimize edildi

### 🔒 Güvenlik
- AI servisi internal network'te çalışır
- API rate limiting bağımsız olarak uygulanır
- Servis izolasyonu sağlandı

## Monitoring ve Logging

### Sağlık Kontrolleri

```bash
# Ana uygulama sağlığı
curl http://localhost:8000/health

# AI servisi sağlığı
curl http://localhost:8001/health

# Detaylı AI model bilgileri
curl http://localhost:8001/models/info
```

### Log Dosyaları

```
logs/
├── main_app_YYYYMMDD_HHMMSS.log    # Ana uygulama
├── ai_service_YYYYMMDD_HHMMSS.log  # AI mikroservisi
└── docker_compose.log              # Docker logları
```

### Performans Metrikleri

```bash
# AI servis istatistikleri
curl http://localhost:8001/stats/lazy-loading

# Model bilgileri
curl http://localhost:8001/models/info

# Ana uygulama sağlık durumu
curl http://localhost:8000/api/health
```

## Troubleshooting

### 🔧 Yaygın Problemler

**AI Servisi Başlamıyor:**
```bash
# Bağımlılıkları kontrol et
pip install aiohttp

# Port çakışması kontrol et
lsof -i :8001

# Manuel başlatma
python services/ai_service/main.py --host 0.0.0.0 --port 8001
```

**Ana Uygulama AI Servisine Bağlanamıyor:**
```bash
# AI servis durumunu kontrol et
curl http://localhost:8001/health

# Network bağlantısını test et
telnet localhost 8001

# Fallback moda geç
export AI_SERVICE_ENABLED=false
```

**Model Yükleme Sorunları:**
```bash
# Model cache'i temizle
rm -rf models_cache/*

# Modelleri yeniden indir
curl -X POST http://localhost:8001/models/warmup

# Hafıza kullanımını kontrol et
curl http://localhost:8001/models/info
```

### 📊 Debug Komutları

```bash
# Tüm servislerin durumu
ps aux | grep python | grep -E "(main.py|ai_service)"

# Port kullanımı
netstat -tulpn | grep -E "(8000|8001)"

# Log takibi
tail -f logs/*.log

# Docker container durumu
docker-compose ps
docker-compose logs mefapex-ai
```

## Migration Rehberi

### Mevcut Kurulumdan Mikroservise Geçiş

1. **Backup Alın:**
```bash
cp -r . ../mefapex_backup_$(date +%Y%m%d)
```

2. **Yeni Kodu Güncelleyin:**
```bash
git pull origin main
```

3. **Bağımlılıkları Yükleyin:**
```bash
pip install -r requirements.txt
```

4. **Mikroservisleri Başlatın:**
```bash
./start_microservices.sh
```

5. **Test Edin:**
```bash
curl http://localhost:8000/health
curl http://localhost:8001/health
```

## İleri Düzey Konfigürasyon

### Load Balancing

Çoklu AI servisi çalıştırma:
```bash
# Port 8001, 8002, 8003'te AI servisleri başlat
python services/ai_service/main.py --port 8001 &
python services/ai_service/main.py --port 8002 &
python services/ai_service/main.py --port 8003 &
```

### Service Discovery

Docker Compose ile otomatik service discovery:
```yaml
environment:
  - AI_SERVICE_HOST=mefapex-ai
  - AI_SERVICE_PORT=8001
```

### Monitoring Stack

Production için Prometheus + Grafana:
```bash
docker-compose --profile production up -d
```

---

## 📞 Destek

Mikroservis mimarisi ile ilgili sorularınız için:
- 📖 Dokümantasyon: `/docs` endpoints
- 🐛 Issue tracking: GitHub Issues
- 📧 Teknik destek: Proje ekibi
