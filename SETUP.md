# MEFAPEX Chatbot - Hızlı Başlangıç Kılavuzu

## 🚀 Hızlı Kurulum (5 dakika)

### 1. OpenAI API Anahtarı Alın
1. https://platform.openai.com adresine gidin
2. Hesap oluşturun veya giriş yapın
3. API Keys bölümünden yeni bir anahtar oluşturun
4. Anahtarı kopyalayın (sk-... ile başlar)

### 2. .env Dosyasını Düzenleyin
```bash
# .env dosyasını açın
nano .env

# OPENAI_API_KEY satırını bulun ve gerçek anahtarınızla değiştirin
OPENAI_API_KEY=sk-your-actual-api-key-here
```

### 3. Qdrant Kurulumu (Docker ile)
```bash
# Docker kurulu değilse:
# macOS: brew install docker
# Ubuntu: sudo apt install docker.io

# Qdrant'ı başlatın
docker run -d -p 6333:6333 --name qdrant qdrant/qdrant
```

### 4. Uygulamayı Başlatın
```bash
# Tüm bağımlılıkları yükle ve başlat
./start.sh

# VEYA manuel olarak:
pip install -r requirements.txt
python embedding_loader.py
python main.py
```

### 5. Test Edin
1. Tarayıcıda http://localhost:8000 açın
2. demo / 1234 ile giriş yapın
3. "Çalışma saatleri nelerdir?" sorusunu sorun

## 🔧 Sorun Giderme

### OpenAI API Hatası
```bash
# .env dosyasını kontrol edin
cat .env | grep OPENAI

# API anahtarı geçerli mi test edin
curl -H "Authorization: Bearer YOUR_API_KEY" https://api.openai.com/v1/models
```

### Qdrant Bağlantı Hatası
```bash
# Qdrant çalışıyor mu?
curl http://localhost:6333/health

# Eğer çalışmıyorsa:
docker start qdrant
# veya
docker run -d -p 6333:6333 --name qdrant qdrant/qdrant
```

### Port Kullanımda Hatası
```bash
# 8000 portunu kullanan processleri bul
lsof -i :8000

# Processleri sonlandır
kill -9 PID_NUMBER
```

## 📝 Sistem Gereksinimleri

- **Python**: 3.8 veya üzeri
- **RAM**: En az 2GB
- **Disk**: En az 1GB boş alan
- **İnternet**: OpenAI API için gerekli

## 🧪 Test Komutları

```bash
# Sistem sağlığını test et
curl http://localhost:8000/health

# Chat API'sini test et
curl -X POST "http://localhost:8000/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "Merhaba"}'

# Otomatik test suite çalıştır
python test_chatbot.py
```

## 📞 Destek

Sorun yaşarsanız:
1. README.md dosyasını okuyun
2. Terminal çıktılarını kontrol edin
3. .env dosyasının doğru yapılandırıldığından emin olun

## 🎯 Demo Bilgileri

- **URL**: http://localhost:8000
- **Kullanıcı**: demo
- **Şifre**: 1234
- **Örnek Soru**: "Fabrika çalışma saatleri nelerdir?"
