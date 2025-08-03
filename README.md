# 🏭 MEFAPEX Turkish AI Chatbot

> Fabrika çalışanları için Türkçe AI destekli soru-cevap sistemi

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--3.5-orange.svg)](https://openai.com)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

MEFAPEX fabrikası için geliştirilmiş Türkçe AI chatbot prototipi. Çalışanların fabrika ile ilgili sorularına hızlı ve doğru yanıtlar vermek için tasarlanmıştır.

## 🚀 Özellikler

- **Türkçe Dil Desteği**: Tamamen Türkçe soru-cevap sistemi
- **Vector Search**: Qdrant ile benzerlik tabanlı arama
- **AI Destekli Yanıtlar**: OpenAI GPT-3.5 Turbo ile akıllı yanıt üretimi
- **Basit Kimlik Doğrulama**: Demo amaçlı sabit kullanıcı girişi
- **Modern Web Arayüzü**: HTML/CSS/JavaScript ile responsive tasarım
- **FastAPI Backend**: Yüksek performanslı REST API

## 🛠️ Teknolojiler

- **Backend**: Python + FastAPI
- **Frontend**: HTML + JavaScript
- **Veritabanı**: MySQL (kullanıcı verileri)
- **Vector Veritabanı**: Qdrant (döküman embeddings)
- **AI API**: OpenAI GPT-3.5 Turbo
- **Embedding**: OpenAI text-embedding-ada-002

## 📋 Gereksinimler

- Python 3.8+
- MySQL Server
- Qdrant Server
- OpenAI API Key

## 🔧 Kurulum

### 1. Bağımlılıkları Yükleyin

```bash
pip install -r requirements.txt
```

### 2. Çevre Değişkenlerini Ayarlayın

`.env` dosyasını düzenleyin:

```env
OPENAI_API_KEY=your_openai_api_key_here
QDRANT_HOST=localhost
QDRANT_PORT=6333
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=mefapex_chatbot
```

### 3. Qdrant Sunucusunu Başlatın

Docker ile:
```bash
docker run -p 6333:6333 qdrant/qdrant
```

### 4. MySQL Veritabanını Oluşturun

```bash
mysql -u root -p < database.sql
```

### 5. Vector Verilerini Yükleyin

```bash
python embedding_loader.py
```

### 6. Uygulamayı Başlatın

```bash
python main.py
```

Uygulama `http://localhost:8000` adresinde çalışacaktır.

## 💡 Kullanım

1. Tarayıcıda `http://localhost:8000` adresine gidin
2. Demo bilgileri ile giriş yapın:
   - **Kullanıcı Adı**: demo
   - **Şifre**: 1234
3. Chat arayüzünde Türkçe sorularınızı yazın
4. AI asistandan anında yanıt alın

## 📝 Örnek Sorular

- "Fabrika çalışma saatleri nelerdir?"
- "İzin başvurusu nasıl yapılır?"
- "Güvenlik kuralları nelerdir?"
- "Vardiya değişiklikleri nasıl yapılır?"
- "Güncel üretim çıktısı nedir?"

## 🏗️ Proje Yapısı

```
mefapex/
├── main.py                 # FastAPI backend
├── embedding_loader.py     # Vector veri yükleme scripti
├── requirements.txt        # Python bağımlılıkları
├── .env                   # Çevre değişkenleri
├── database.sql           # MySQL veritabanı şeması
├── static/
│   ├── index.html         # Ana web sayfası
│   └── script.js          # Frontend JavaScript
└── README.md              # Bu dosya
```

## 🔍 API Endpoints

- `GET /` - Ana sayfa
- `POST /login` - Kullanıcı girişi
- `POST /chat` - Chat mesajı gönderme
- `GET /health` - Sistem sağlık kontrolü

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

## 🚧 Geliştirme Notları

Bu bir prototiptir ve aşağıdaki özellikler henüz implementasyona dahil değildir:

- TESLA/LOGO ERP entegrasyonu
- Gerçek kullanıcı yönetimi
- Session yönetimi
- Chat geçmişi saklama
- Canlı veri sorguları (sadece simüle edilmiş)

## 🐛 Sorun Giderme

### Qdrant Bağlantı Hatası
```bash
# Qdrant'ın çalıştığını kontrol edin
curl http://localhost:6333/health
```

### OpenAI API Hatası
- `.env` dosyasında API anahtarınızı kontrol edin
- API kotanızı kontrol edin

### MySQL Bağlantı Hatası
- MySQL servisinin çalıştığını kontrol edin
- Veritabanı bilgilerini `.env` dosyasında kontrol edin

## 📞 Destek

Herhangi bir sorun için proje geliştiricisi ile iletişime geçin.

## 📄 Lisans

Bu proje MEFAPEX için geliştirilmiş bir prototiptir.
