# 🏭 MEFAPEX Turkish AI Chatbot

> Fabrika çalışanları için Türkçe AI destekli soru-cevap sistemi - Modern Dark Theme ile

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com)
[![Hugging Face](https://img.shields.io/badge/HuggingFace-Transformers-yellow.svg)](https://huggingface.co)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

MEFAPEX fabrikası için geliştirilmiş Türkçe AI chatbot sistemi. Çalışanların fabrika ile ilgili sorularına hızlı ve doğru yanıtlar vermek için tasarlanmıştır.

## 🚀 Özellikler

- **🌙 Modern Dark Theme**: Göz dostu koyu tema tasarımı
- **🇹🇷 Türkçe Dil Desteği**: Tamamen Türkçe soru-cevap sistemi
- **🔍 Vector Search**: Qdrant ile benzerlik tabanlı arama
- **🤖 Hybrid AI**: OpenAI + Hugging Face ile çoklu AI desteği
- **👤 Kimlik Doğrulama**: JWT tabanlı güvenli giriş sistemi
- **📱 Responsive Tasarım**: Mobil uyumlu modern web arayüzü
- **📊 Chat Geçmişi**: Kullanıcı bazlı oturum yönetimi
- **🚀 FastAPI Backend**: Yüksek performanslı REST API
- **🔄 WebSocket Desteği**: Gerçek zamanlı mesajlaşma
- **🧠 Akıllı Önbellekleme**: Hızlı yanıt için gelişmiş caching

## 🛠️ Teknolojiler

- **Backend**: Python + FastAPI + WebSockets
- **Frontend**: HTML + JavaScript + Modern CSS (Dark Theme)
- **Veritabanı**: SQLite (chat geçmişi ve kullanıcı verileri)
- **Vector Veritabanı**: Qdrant (döküman embeddings)
- **AI Engines**: 
  - OpenAI GPT-3.5 Turbo (opsiyonel)
  - Hugging Face Transformers (varsayılan)
- **Embedding**: Sentence Transformers
- **Authentication**: JWT Token sistemi
- **Caching**: Memory-based response caching

## 📋 Gereksinimler

- Python 3.8+
- Qdrant Server (opsiyonel - vector search için)
- OpenAI API Key (opsiyonel - OpenAI kullanımı için)

## 🔧 Kurulum

### 1. Repository'yi Klonlayın

```bash
git clone https://github.com/Bariskosee/MefapexChatBox.git
cd MefapexChatBox
```

### 2. Bağımlılıkları Yükleyin

```bash
pip install -r requirements.txt
```

### 3. Çevre Değişkenlerini Ayarlayın (Opsiyonel)

`.env` dosyası oluşturun:

```env
# OpenAI (Opsiyonel - daha gelişmiş AI için)
OPENAI_API_KEY=your_openai_api_key_here
USE_OPENAI=false

# Hugging Face (Varsayılan)
USE_HUGGINGFACE=true

# Qdrant (Opsiyonel - vector search için)
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Güvenlik (Prodüksiyon için değiştirin)
SECRET_KEY=your-secret-key-change-this-in-production
ENVIRONMENT=development
DEBUG=true
```

### 4. Qdrant Sunucusunu Başlatın (Opsiyonel)

Vector search özelliği için:
```bash
docker run -p 6333:6333 qdrant/qdrant
```

### 5. Uygulamayı Başlatın

```bash
# Geliştirme modu
uvicorn main:app --reload --port 8000

# Veya basit başlatma
python main.py
```

Uygulama `http://localhost:8000` adresinde çalışacaktır.

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

## 🏗️ Proje Yapısı

```
MefapexChatBox/
├── main.py                     # FastAPI backend
├── database_manager.py         # Veritabanı yönetimi
├── model_manager.py           # AI model yönetimi
├── response_cache.py          # Yanıt önbellekleme
├── websocket_manager.py       # WebSocket yönetimi
├── embedding_loader.py        # Vector veri yükleme
├── requirements.txt           # Python bağımlılıkları
├── .env                      # Çevre değişkenleri (opsiyonel)
├── mefapex.db               # SQLite veritabanı
├── static/
│   ├── index.html           # Ana web sayfası (Dark Theme)
│   ├── script.js           # Frontend JavaScript
│   └── websocket_client.js # WebSocket istemcisi
└── README.md               # Bu dosya
```

## 🔍 API Endpoints

- `GET /` - Ana sayfa (Dark Theme)
- `POST /login` - JWT tabanlı kullanıcı girişi
- `POST /chat` - Chat mesajı gönderme (anonim)
- `POST /chat/authenticated` - Kimlik doğrulamalı chat
- `GET /chat/history/{user_id}` - Chat geçmişi
- `GET /chat/sessions/{user_id}` - Chat oturumları
- `POST /chat/sessions/{user_id}/new` - Yeni chat oturumu
- `GET /health` - Sistem sağlık kontrolü
- `GET /health/comprehensive` - Detaylı sistem durumu
- `GET /system/status` - Sistem konfigürasyonu
- `WebSocket /ws/{user_id}` - Gerçek zamanlı chat

## 🧪 Test

Sistem sağlığını kontrol etmek için:

```bash
curl http://localhost:8000/health
```

Chat API'sini test etmek için:

```bash
curl -X POST "http://localhost:8000/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "Çalışma saatleri nelerdir?"}'
```

Sistem durumunu görmek için:

```bash
curl http://localhost:8000/system/status
```

## ⚙️ Konfigürasyon

### AI Motor Seçimi
- `USE_OPENAI=true` - OpenAI GPT-3.5 kullan (API key gerekli)
- `USE_HUGGINGFACE=true` - Hugging Face modellerini kullan (varsayılan)

### Güvenlik Ayarları
- `SECRET_KEY` - JWT token için güvenlik anahtarı
- `ENVIRONMENT` - production/development modu
- `DEBUG` - Debug modunu aç/kapat

## 🚧 Özellikler

### ✅ Mevcut Özellikler
- ✅ Dark theme modern arayüz
- ✅ JWT tabanlı kimlik doğrulama
- ✅ Chat geçmişi ve oturum yönetimi
- ✅ Hybrid AI desteği (OpenAI + Hugging Face)
- ✅ WebSocket gerçek zamanlı mesajlaşma
- ✅ Akıllı önbellekleme sistemi
- ✅ Responsive mobile uyumlu tasarım
- ✅ Kapsamlı sistem monitoring

### 🔄 Geliştirilecek Özellikler
- 🔄 TESLA/LOGO ERP entegrasyonu
- 🔄 Çoklu kullanıcı yönetimi
- 🔄 Admin paneli
- 🔄 Dosya yükleme desteği
- 🔄 Çoklu dil desteği
- 🔄 Voice chat desteği

## 🐛 Sorun Giderme

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

## 🌟 Katkıda Bulunma

1. Repository'yi fork edin
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Değişikliklerinizi commit edin (`git commit -m 'Add amazing feature'`)
4. Branch'inizi push edin (`git push origin feature/amazing-feature`)
5. Pull Request açın

## 📞 Destek

Herhangi bir sorun için:
- Issue açın: [GitHub Issues](https://github.com/Bariskosee/MefapexChatBox/issues)
- Proje geliştiricisi ile iletişime geçin

## 📄 Lisans

Bu proje MEFAPEX için geliştirilmiş bir sistemdir.

---

**Made with ❤️ for MEFAPEX Factory Workers**
