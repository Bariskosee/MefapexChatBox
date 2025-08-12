# 🗄️ PostgreSQL Kurulum ve Yapılandırma Rehberi

## 📋 Genel Bakış

MEFAPEX ChatBox artık **sadece PostgreSQL** desteği sunmaktadır. MySQL ve SQLite desteği kaldırılmıştır. Bu değişiklik daha güvenilir, ölçeklenebilir ve production-ready bir veritabanı deneyimi sağlar.

## 🚀 Hızlı Başlangıç

### 🐳 Docker ile (Önerilen)

En kolay yol Docker Compose kullanmaktır:

```bash
# Repository'yi klonlayın
git clone https://github.com/Bariskosee/MefapexChatBox.git
cd MefapexChatBox

# PostgreSQL ile birlikte tüm servisleri başlatın
docker-compose up -d

# Logları kontrol edin
docker-compose logs -f
```

Bu komut otomatik olarak:
- PostgreSQL 15 container'ı başlatır
- Veritabanını init.sql ile başlatır
- Gerekli tabloları ve indexleri oluşturur
- Uygulamayı PostgreSQL ile bağlar

## 🔧 Manuel PostgreSQL Kurulumu

### Windows

```bash
# 1. PostgreSQL indir ve yükle
# https://www.postgresql.org/download/windows/

# 2. pgAdmin ile bağlan
# localhost:5432

# 3. Veritabanı oluştur
CREATE DATABASE mefapex_chatbot;
CREATE USER mefapex WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE mefapex_chatbot TO mefapex;

# 4. Init script'i çalıştır
psql -U mefapex -d mefapex_chatbot -f database/init.sql
```

### macOS

```bash
# 1. Homebrew ile PostgreSQL yükle
brew install postgresql@15
brew services start postgresql@15

# 2. Veritabanı oluştur
createdb mefapex_chatbot
psql mefapex_chatbot

# PostgreSQL shell'de:
CREATE USER mefapex WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE mefapex_chatbot TO mefapex;

# 3. Init script'i çalıştır
psql -U mefapex -d mefapex_chatbot -f database/init.sql
```

### Linux (Ubuntu/Debian)

```bash
# 1. PostgreSQL yükle
sudo apt update
sudo apt install postgresql postgresql-contrib

# 2. PostgreSQL servisini başlat
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 3. Veritabanı ve kullanıcı oluştur
sudo -u postgres psql

# PostgreSQL shell'de:
CREATE DATABASE mefapex_chatbot;
CREATE USER mefapex WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE mefapex_chatbot TO mefapex;
\q

# 4. Init script'i çalıştır
psql -U mefapex -d mefapex_chatbot -h localhost -f database/init.sql
```

## ⚙️ Environment Yapılandırması

### .env Dosyası Oluşturma

```bash
# .env.postgresql dosyasını kopyalayın
cp .env.postgresql .env

# Gerekli değerleri düzenleyin
nano .env
```

### Gerekli Environment Variables

```env
# PostgreSQL Veritabanı Ayarları
DATABASE_TYPE=postgresql
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=mefapex
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_DB=mefapex_chatbot

# Alternatif: Tek URL ile
DATABASE_URL=postgresql://mefapex:your_password@localhost:5432/mefapex_chatbot

# Güvenlik
SECRET_KEY=your-super-secure-secret-key-change-this-immediately

# AI Yapılandırması
USE_OPENAI=false
USE_HUGGINGFACE=true
```

## 🗄️ Veritabanı Şeması

PostgreSQL veritabanında aşağıdaki tablolar oluşturulur:

### 👥 users
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    user_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    failed_login_attempts INTEGER DEFAULT 0
);
```

### 💬 chat_sessions
```sql
CREATE TABLE chat_sessions (
    id SERIAL PRIMARY KEY,
    session_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    message_count INTEGER DEFAULT 0
);
```

### 📝 chat_messages
```sql
CREATE TABLE chat_messages (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    user_message TEXT NOT NULL,
    bot_response TEXT NOT NULL,
    source VARCHAR(50) DEFAULT 'unknown',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);
```

## 🔄 SQLite'dan PostgreSQL'e Geçiş

### Otomatik Migrasyon

Mevcut SQLite verilerinizi PostgreSQL'e aktarmak için:

```bash
# Migration script'i çalıştırın
python migrate_database.py --from sqlite --to postgresql

# Verileri doğrulayın
python migrate_database.py --validate-only
```

### Manuel Veri Aktarımı

```bash
# 1. SQLite'dan veri export et
sqlite3 mefapex.db ".dump" > sqlite_backup.sql

# 2. PostgreSQL'e uygun formata çevir
# (Bu adım karmaşık olabilir, otomatik migration önerilir)

# 3. PostgreSQL'e import et
psql -U mefapex -d mefapex_chatbot -f converted_data.sql
```

## 🔍 Sorun Giderme

### Bağlantı Sorunları

```bash
# PostgreSQL'in çalıştığını kontrol edin
sudo systemctl status postgresql

# Port kontrolü
netstat -an | grep 5432

# Bağlantı testi
psql -U mefapex -d mefapex_chatbot -h localhost -c "SELECT 1;"
```

### Yetki Sorunları

```sql
-- PostgreSQL shell'de yetkileri kontrol edin
\dp

-- Eksik yetkileri verin
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO mefapex;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO mefapex;
```

### Performance Ayarları

PostgreSQL performansını artırmak için `postgresql.conf` dosyasında:

```conf
# Memory ayarları
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB

# Checkpoint ayarları
checkpoint_completion_target = 0.9
wal_buffers = 16MB

# Connection ayarları
max_connections = 200
```

## 📊 Monitoring ve Bakım

### Veritabanı Durumu

```sql
-- Bağlantı sayısı
SELECT count(*) FROM pg_stat_activity;

-- Tablo boyutları
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public';

-- Index kullanımı
SELECT * FROM pg_stat_user_indexes;
```

### Yedekleme

```bash
# Veritabanı yedekleme
pg_dump -U mefapex -d mefapex_chatbot > backup_$(date +%Y%m%d).sql

# Otomatik yedekleme cron job'ı
0 2 * * * pg_dump -U mefapex -d mefapex_chatbot > /backups/mefapex_$(date +\%Y\%m\%d).sql
```

### Geri Yükleme

```bash
# Yedekten geri yükleme
psql -U mefapex -d mefapex_chatbot < backup_20241212.sql
```

## 🚀 Production Deployment

### Docker Production

```yaml
# docker-compose.prod.yml örneği
version: '3.8'
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: mefapex_chatbot
      POSTGRES_USER: mefapex
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    restart: always
    
volumes:
  postgres_data:
```

### Kubernetes Deployment

```yaml
# postgres-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
spec:
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15-alpine
        env:
        - name: POSTGRES_DB
          value: mefapex_chatbot
        - name: POSTGRES_USER
          value: mefapex
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: password
        ports:
        - containerPort: 5432
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
      volumes:
      - name: postgres-storage
        persistentVolumeClaim:
          claimName: postgres-pvc
```

## 🔒 Güvenlik

### Güvenlik Best Practices

```sql
-- Güçlü şifre politikası
ALTER SYSTEM SET password_encryption = 'scram-sha-256';

-- Bağlantı güvenliği
ALTER SYSTEM SET ssl = on;

-- Log ayarları
ALTER SYSTEM SET log_connections = on;
ALTER SYSTEM SET log_disconnections = on;
```

### Firewall Ayarları

```bash
# Sadece gerekli portları açın
sudo ufw allow from 10.0.0.0/8 to any port 5432
sudo ufw deny 5432
```

## 📞 Destek

Bu rehberle ilgili sorularınız için:

- 📧 Email: info@mefapex.com
- 🐛 GitHub Issues: https://github.com/Bariskosee/MefapexChatBox/issues
- 📚 Dokümantasyon: README.md

---

**© 2024 MEFAPEX - PostgreSQL Production-Ready Solution**
