# 🚀 MEFAPEX ChatBox Kurulum Rehberi

## ⚡ Hızlı Kurulum (3 Dakika)

### 1️⃣ Repository'yi İndirin
```bash
git clone https://github.com/Bariskosee/MefapexChatBox.git
cd MefapexChatBox
```

### 2️⃣ Otomatik Kurulum
```bash
python setup.py
```

### 3️⃣ Sistemi Başlatın
```bash
# Linux/macOS
./run.sh

# Windows
./run.bat
```

🎉 **Tamamlandı!** → http://localhost:8000

---

## 📋 Detaylı Kurulum Rehberi

### 🔍 Sistem Gereksinimleri

| Gereksinim | Minimum | Önerilen |
|------------|---------|----------|
| **Python** | 3.11+ | 3.11+ |
| **RAM** | 4GB | 8GB+ |
| **Disk** | 2GB | 4GB+ |
| **OS** | Windows 10+, macOS 10.15+, Ubuntu 20.04+ | - |

### 🐍 Python 3.11+ Kurulumu

**Windows:**
```bash
# Microsoft Store'dan Python 3.11+ indirin
# VEYA https://python.org'dan resmi installer

python --version  # 3.11+ kontrolü
```

**macOS:**
```bash
# Homebrew ile (önerilen)
brew install python@3.11

# Versiyonu kontrol edin
python3.11 --version
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-pip

# Versiyonu kontrol edin
python3.11 --version
```

### 🔧 Manuel Kurulum Adımları

```bash
# 1. Repository klonlayın
git clone https://github.com/Bariskosee/MefapexChatBox.git
cd MefapexChatBox

# 2. Python versiyonunu kontrol edin
python --version  # 3.11+ olmalı

# 3. Virtual environment oluşturun
python -m venv .venv

# 4. Virtual environment'ı aktive edin
# Linux/macOS:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

# 5. Pip'i güncelleyin
pip install --upgrade pip

# 6. Dependencies'leri yükleyin
pip install -r requirements.txt

# 7. Environment dosyası oluşturun
cp .env.example .env

# 8. Uygulamayı başlatın
python main.py
```

---

## 🔧 Konfigürasyon

### ⚙️ Environment Dosyası (.env)

```bash
# .env.example dosyasını kopyalayın
cp .env.example .env

# Gerekirse ayarları düzenleyin
nano .env  # Linux/macOS
notepad .env  # Windows
```

### 🔑 Varsayılan Ayarlar
- **URL**: http://localhost:8000
- **Kullanıcı**: demo
- **Şifre**: 1234
- **AI Engine**: Hugging Face (OpenAI devre dışı)

---

## 🚀 Çalıştırma Seçenekleri

### 🎯 Basit Çalıştırma
```bash
./run.sh        # Linux/macOS
./run.bat       # Windows
```

### 🐍 Manuel Çalıştırma
```bash
source .venv/bin/activate  # Virtual env aktive et
python main.py             # Uygulamayı başlat
```

### 🐳 Docker ile Çalıştırma
```bash
# Tek komutla başlatma
./start-docker.sh

# Manuel Docker
docker-compose up -d
```

---

## 🧪 Kurulum Testi

### ✅ Health Check
```bash
# Server çalışıyor mu?
curl http://localhost:8000/health

# Detaylı sistem durumu
curl http://localhost:8000/health/comprehensive
```

### ✅ API Testi
```bash
# Basit chat testi
curl -X POST "http://localhost:8000/chat/public" \
     -H "Content-Type: application/json" \
     -d '{"message": "Merhaba"}'
```

### ✅ Web Interface
- Tarayıcıda: http://localhost:8000
- Giriş: demo / 1234

---

## 🐛 Sorun Giderme

### ❌ Python Versiyonu Hatası
```bash
# Python 3.11+ kontrol edin
python --version

# Farklı Python versiyonu deneyin
python3.11 -m venv .venv
```

### ❌ Dependency Hatası
```bash
# Pip'i güncelleyin
pip install --upgrade pip

# Requirements'ı tekrar yükleyin
pip install -r requirements.txt --force-reinstall
```

### ❌ Port Çakışması
```bash
# Farklı port kullanın
uvicorn main:app --port 8001
```

### ❌ Permission Hatası (Linux/macOS)
```bash
# Script izinlerini düzeltin
chmod +x run.sh setup.py
```

### ❌ Virtual Environment Hatası
```bash
# Virtual environment'ı silin ve tekrar oluşturun
rm -rf .venv
python -m venv .venv
```

---

## 📊 Performans Optimizasyonu

### 🚀 Hızlı Başlatma İçin
```bash
# AI modellerini önceden indirin
python -c "from model_manager import model_manager; model_manager.warmup_models()"
```

### 💾 Disk Alanı Tasarrufu
```bash
# Cache'i temizleyin
rm -rf models_cache/*
rm -rf __pycache__
```

---

## 🆘 Destek

### 🔗 Yararlı Linkler
- **Ana Sayfa**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **GitHub Issues**: https://github.com/Bariskosee/MefapexChatBox/issues

### 📞 İletişim
- **Bug Reports**: GitHub Issues
- **Feature Requests**: GitHub Discussions
- **Email**: info@mefapex.com

---

## ✅ Kurulum Checklist

- [ ] Python 3.11+ yüklü
- [ ] Repository klonlandı
- [ ] Virtual environment oluşturuldu
- [ ] Dependencies yüklendi
- [ ] .env dosyası yapılandırıldı
- [ ] Uygulama başlatıldı
- [ ] Health check başarılı
- [ ] Web interface erişilebilir
- [ ] Chat fonksiyonu çalışıyor

🎉 **Kurulum tamamlandı! MEFAPEX ChatBox kullanıma hazır!**
