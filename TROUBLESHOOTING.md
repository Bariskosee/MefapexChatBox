# 🔧 MEFAPEX Sorun Giderme Rehberi

## 🚨 En Yaygın Sorunlar ve Çözümleri

### 1. Sunucu Başlamıyor
```bash
# Problem: Import hataları
# Çözüm: Virtual environment'ı yeniden oluştur
rm -rf .venv
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# veya
.venv\Scripts\activate     # Windows

pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Configuration Hataları
```bash
# Problem: Environment dosyası bulunamıyor
# Çözüm: Environment değişkenlerini manuel ayarla

export ENVIRONMENT=development
export DEBUG=true
export SECRET_KEY=dev-secret-key
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_USER=mefapex
export POSTGRES_PASSWORD=mefapex
export POSTGRES_DB=mefapex_chatbot
export USE_OPENAI=false
export USE_HUGGINGFACE=true
```

### 3. Database Bağlantı Sorunu
```python
# Problem: PostgreSQL bağlantısı yok
# Çözüm: PostgreSQL servisini başlat

# macOS (Homebrew):
brew services start postgresql@15

# Ubuntu/Debian:
sudo systemctl start postgresql

# Manuel bağlantı testi:
PGPASSWORD=mefapex psql -h localhost -U mefapex -d mefapex_chatbot -c "SELECT 1;"
```

### 4. AI Model Yükleme Hataları
```bash
# Problem: Hugging Face modelleri yüklenmiyor
# Çözüm: Internet bağlantısını kontrol et ve cache temizle

# Cache temizle
rm -rf ~/.cache/huggingface/
rm -rf models_cache/

# Offline çalışma için AI'yi devre dışı bırak
export USE_HUGGINGFACE=false
export USE_OPENAI=false
```

### 5. Port Çakışması
```bash
# Problem: Port 8000 kullanımda
# Çözüm: Farklı port kullan

export APP_PORT=8001
python main.py

# Veya kullanımdaki portu bul ve öldür
lsof -ti:8000 | xargs kill -9  # macOS/Linux
netstat -ano | findstr :8000   # Windows
```

## 🛠️ Hızlı Düzeltme Komutları

### Basit Başlatma (Minimum Ayarlar)
```bash
# 1. Sadece gerekli paketleri yükle
pip install fastapi uvicorn psycopg2-binary python-jose passlib

# 2. Minimum environment ayarla
export ENVIRONMENT=development
export DEBUG=true
export POSTGRES_HOST=localhost
export POSTGRES_USER=mefapex
export POSTGRES_PASSWORD=mefapex
export POSTGRES_DB=mefapex_chatbot
export USE_OPENAI=false
export USE_HUGGINGFACE=false

# 3. Basit modda başlat
python main.py
```

### Database Reset
```bash
# PostgreSQL database'i sıfırla
PGPASSWORD=mefapex psql -h localhost -U mefapex -c "DROP DATABASE IF EXISTS mefapex_chatbot;"
PGPASSWORD=mefapex psql -h localhost -U mefapex -c "CREATE DATABASE mefapex_chatbot;"

# Yeniden oluşturulacak
python main.py
```

### Dependency Kontrolü
```python
# Eksik paketleri kontrol et
python -c "
required = ['fastapi', 'uvicorn', 'pydantic', 'python-jose', 'passlib', 'psycopg2']
missing = []
for pkg in required:
    try:
        __import__(pkg)
        print(f'✅ {pkg}')
    except ImportError:
        print(f'❌ {pkg} - EKSIK')
        missing.append(pkg)

if missing:
    print(f'Eksik paketler: {missing}')
    print(f'Yüklemek için: pip install {\" \".join(missing)}')
"
```

## 🎯 Debug Modunda Başlatma
```bash
# Maksimum debug bilgisi ile
export DEBUG=true
export LOG_LEVEL=DEBUG
python -u main.py 2>&1 | tee debug.log
```

## 🔍 Sistem Durumu Kontrolü
```bash
# Servisleri kontrol et (manuel test)
# Server çalışıyorsa browser'da şu adresleri ziyaret edin:
# http://localhost:8000/
# http://localhost:8000/docs
# http://localhost:8000/health
```

## 🚑 Acil Durum Basit Server

Eğer hiçbir şey çalışmıyorsa, bu minimal server'ı kullan:

```python
# emergency_server.py
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI(title="MEFAPEX Emergency Server")

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html>
        <head><title>MEFAPEX Test</title></head>
        <body>
            <h1>🚀 MEFAPEX Emergency Server</h1>
            <p>Server çalışıyor!</p>
            <p><a href="/docs">API Docs</a></p>
        </body>
    </html>
    """

@app.get("/health")
def health():
    return {"status": "healthy", "message": "Emergency server running"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, debug=True)
```

## 📞 Son Çare Adımları

1. **Tüm cache'leri temizle:**
```bash
rm -rf __pycache__ .pytest_cache models_cache logs
find . -name "*.pyc" -delete
```

2. **Virtual environment'ı yeniden oluştur:**
```bash
rm -rf .venv
python -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn psycopg2-binary
```

3. **Minimal requirements.txt kullan:**
```txt
fastapi>=0.100.0
uvicorn[standard]>=0.20.0
pydantic>=2.0.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
psycopg2-binary>=2.9.0
```

4. **Adım adım test et:**
```bash
python -c "import fastapi; print('✅ FastAPI')"
python -c "import uvicorn; print('✅ Uvicorn')"
python -c "from main import app; print('✅ Main app')"
```

## 🔍 Ana Sorunlar ve Çözümler:

- **Karmaşık Dependency Graph**: requirements.txt'de sadece gerekli paketler kullan
- **PostgreSQL Dependency**: PostgreSQL servisinin çalıştığından emin ol
- **Heavy AI Models**: Development için AI modellerini devre dışı bırak
- **Configuration Complexity**: Environment değişkenlerini manuel ayarla

## 🚀 Hızlı Başlatma Özet:

1. `chmod +x setup_and_start.sh && ./setup_and_start.sh`
2. PostgreSQL çalışıyorsa direkt: `python main.py`
3. Sorun varsa: Emergency server kullan
4. Debug için: `export DEBUG=true && python main.py`

**Not**: Curl testleri zaman aldığı için browser'da manuel test yapın.
