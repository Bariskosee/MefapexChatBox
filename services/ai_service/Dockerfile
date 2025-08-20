# MEFAPEX AI Mikroservisi Docker Image
FROM python:3.11-slim

# Çalışma dizini oluştur
WORKDIR /app

# Sistem bağımlılıklarını yükle
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python bağımlılıklarını kopyala ve yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama kodunu kopyala
COPY . .

# AI servis için ek bağımlılıklar
RUN pip install --no-cache-dir aiohttp

# Model cache dizini oluştur
RUN mkdir -p /app/models_cache

# Port ayarları
EXPOSE 8001

# Sağlık kontrolü
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# AI servisi başlat
CMD ["python", "services/ai_service/main.py", "--host", "0.0.0.0", "--port", "8001"]
