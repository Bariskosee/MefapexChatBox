# 🏭 MEFAPEX Hybrid AI Chatbot

> Akıllı hibrit sistem: OpenAI + Hugging Face destekli Türkçe fabrika asistanı

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.116+-green.svg)](https://fastapi.tiangolo.com)
[![Hybrid](https://img.shields.io/badge/System-Hybrid-orange.svg)]()
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## 🌟 Hibrit Sistem Özellikleri

- **🔄 Çifte Motor**: OpenAI GPT + Hugging Face modelleri
- **🆓 Ücretsiz Mod**: Sadece Hugging Face ile çalışabilir
- **💰 Premium Mod**: OpenAI + Hugging Face kombinasyonu
- **🛡️ Yedekleme**: Bir sistem çökerse diğeri devreye girer
- **⚙️ Yapılandırılabilir**: .env dosyası ile kolay ayar

## 🚀 Hızlı Başlangıç

### 1. Projeyi İndirin
```bash
git clone <repo-url>
cd MefapexChatBox-main
```

### 2. Bağımlılıkları Yükleyin
```bash
pip install -r requirements.txt
```

### 3. Çevre Değişkenlerini Ayarlayın
```bash
cp .env.example .env
nano .env
```

**Ücretsiz kullanım için:**
```env
USE_OPENAI=false
USE_HUGGINGFACE=true
```

**Premium kullanım için:**
```env
USE_OPENAI=true
USE_HUGGINGFACE=true
OPENAI_API_KEY=your_api_key_here
```

### 4. Qdrant'ı Başlatın
```bash
docker run -d -p 6333:6333 --name qdrant qdrant/qdrant
```

### 5. Verileri Yükleyin
```bash
python embedding_loader.py
```

### 6. Uygulamayı Çalıştırın
```bash
python main.py
```

## 🎯 Kullanım Modları

### 🆓 Ücretsiz Mod (Sadece Hugging Face)
- API key gerekmez
- Tamamen offline çalışır
- Hızlı ve güvenilir
- Sınırsız kullanım

### 💎 Premium Mod (OpenAI + Hugging Face)
- Daha akıllı yanıtlar
- Gelişmiş doğal dil anlama
- Yaratıcı cevaplar
- OpenAI API key gerekli

### 🔄 Hibrit Mod (Önerilen)
- İki sistemin en iyisi
- Otomatik yedekleme
- Yüksek güvenilirlik
- Esnek yapılandırma

## 📁 Yeni Proje Yapısı

```
mefapex/
├── main.py                    # Ana hibrit uygulama ⭐
├── embedding_loader.py        # Veri yükleme scripti ⭐
├── requirements.txt           # Güncel bağımlılıklar ⭐
├── .env                      # Yapılandırma dosyası ⭐
├── backup/                   # Eski dosyalar
│   ├── main_original.py      # Orijinal main
│   ├── main_free.py          # Ücretsiz versiyon
│   ├── main_hybrid.py        # Hibrit orijinal
│   └── ...                   # Diğer yedekler
├── static/
│   ├── index.html            # Web arayüzü
│   └── script.js             # Frontend kodu
└── test_*.py                 # Test dosyaları
```

## 🔧 API Endpoints

| Endpoint | Method | Açıklama |
|----------|--------|----------|
| `/` | GET | Ana web sayfası |
| `/health` | GET | Sistem sağlığı |
| `/system/status` | GET | Konfigürasyon durumu |
| `/login` | POST | Kullanıcı girişi |
| `/chat` | POST | Chat mesajı |

## 🎮 Demo Bilgileri

- **URL**: http://localhost:8000
- **Kullanıcı**: demo
- **Şifre**: 1234

## 📊 Sistem Durumu Kontrolü

```bash
# Sağlık kontrolü
curl http://localhost:8000/health

# Sistem konfigürasyonu
curl http://localhost:8000/system/status

# Chat testi
curl -X POST "http://localhost:8000/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "Çalışma saatleri nedir?"}'
```

## 🔄 Mod Değiştirme

Sistemi yeniden başlatmadan mod değiştirmek için `.env` dosyasını düzenleyin:

```env
# Sadece Hugging Face
USE_OPENAI=false
USE_HUGGINGFACE=true

# Sadece OpenAI  
USE_OPENAI=true
USE_HUGGINGFACE=false

# Her ikisi (Hibrit)
USE_OPENAI=true
USE_HUGGINGFACE=true
```

## 🚨 Sorun Giderme

### OpenAI Hatası
```bash
# API key kontrolü
grep OPENAI_API_KEY .env

# OpenAI'yi devre dışı bırak
sed -i 's/USE_OPENAI=true/USE_OPENAI=false/' .env
```

### Hugging Face Hatası
```bash
# Model indirme
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

### Qdrant Hatası
```bash
# Container yeniden başlat
docker restart qdrant
```

## 🎉 Avantajlar

- **✅ Hibrit Güvenilirlik**: Çifte güvence
- **✅ Maliyet Kontrolü**: İsteğe bağlı OpenAI
- **✅ Hızlı Geliştirme**: Hazır yapılandırma
- **✅ Production Ready**: Test edilmiş sistem
- **✅ Kolay Kurulum**: Adım adım kılavuz

## 📞 Destek

Herhangi bir sorun için proje dokümantasyonunu kontrol edin veya issue açın.

---

**🔥 Bu hibrit sistem sayesinde hem ücretsiz hem de premium özelliklerin keyfini çıkarabilirsiniz!**
