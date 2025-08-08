# 🐳 Docker ile Tek Komutla Başlatma Rehberi

## 🚀 Hızlı Başlangıç

### Tek komutla tüm sistemi başlat:
```bash
./start-docker.sh
```

### Alternatif yöntemler:
```bash
# Docker Compose ile direkt
docker-compose up -d

# Rebuild ile başlat
docker-compose up --build -d
```

## 📋 Servis Komutları

### Servisleri Yönet:
```bash
./start-docker.sh start    # Başlat
./start-docker.sh stop     # Durdur
./start-docker.sh restart  # Yeniden başlat
./start-docker.sh status   # Durum göster
./start-docker.sh logs     # Log göster
./start-docker.sh clean    # Temizle ve başlat
```

### Manuel Docker Compose:
```bash
docker-compose ps              # Durum
docker-compose logs -f         # Log takibi
docker-compose down            # Durdur
docker-compose restart         # Yeniden başlat
docker-compose pull            # Güncellemeleri çek
```

## 🌐 Erişim Adresleri

| Servis | URL | Açıklama |
|--------|-----|----------|
| 🚀 Ana Uygulama | http://localhost:8000 | MefapexChatBox |
| 📚 API Dokümantasyonu | http://localhost:8000/docs | Swagger UI |
| 🏥 Health Check | http://localhost:8000/health | Sistem durumu |
| 🗄️ Qdrant | http://localhost:6333 | Vektör veritabanı |
| 🗂️ Redis | localhost:6379 | Cache servisi |
| 🌍 Nginx | http://localhost:80 | Reverse proxy |
| 📊 Monitoring | http://localhost:9090 | Prometheus |

## 🔧 Konfigürasyon

### Environment Variables (.env):
```bash
# Temel ayarlar
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=your-secret-key

# AI Ayarları
USE_OPENAI=false
USE_HUGGINGFACE=true
OPENAI_API_KEY=your-key

# Veritabanı
DATABASE_URL=sqlite:///./data/mefapex.db
QDRANT_HOST=qdrant
REDIS_HOST=redis
```

### Volumes (Veri Depolama):
- `./data/` - SQLite veritabanı
- `./models_cache/` - AI model önbelleği
- `./logs/` - Uygulama logları

## 🚀 Production Optimizations

### Container Özellikleri:
- ✅ Multi-stage build (optimize boyut)
- ✅ Non-root user (güvenlik)
- ✅ Health checks (otomatik yeniden başlatma)
- ✅ Resource limits (bellek yönetimi)
- ✅ Restart policies (otomatik kurtarma)

### Network Güvenlik:
- ✅ Internal network (container iletişimi)
- ✅ Rate limiting (Nginx)
- ✅ CORS protection
- ✅ Security headers

### Performance:
- ✅ Nginx reverse proxy
- ✅ Gzip compression
- ✅ Static file caching
- ✅ Connection pooling
- ✅ Redis caching

## 🛠️ Geliştirme

### Debug Mode:
```bash
# Development environment
cp .env.docker .env
# Edit .env: DEBUG=true
docker-compose up --build
```

### Hot Reload:
```bash
# Volume mount kaynak kodu
docker-compose -f docker-compose.dev.yml up
```

### Database Reset:
```bash
docker-compose down -v  # Volumes ile birlikte sil
docker-compose up -d    # Yeniden başlat
```

## 🔍 Troubleshooting

### Container Logs:
```bash
docker-compose logs mefapex-app
docker-compose logs qdrant
docker-compose logs redis
```

### Container İçine Gir:
```bash
docker exec -it mefapex-chatbox bash
```

### Resource Monitoring:
```bash
docker stats
docker system df
```

### Clean Up:
```bash
# Tüm container ve volume'ları sil
docker-compose down -v
docker system prune -a -f
```

## 📊 Monitoring

### Health Endpoints:
- `/health` - Uygulama sağlığı
- `/metrics` - Prometheus metrics
- `/stats` - Performance statistics

### Log Monitoring:
```bash
# Real-time logs
docker-compose logs -f

# Specific service
docker-compose logs -f mefapex-app

# Last 100 lines
docker-compose logs --tail=100 mefapex-app
```

## 🚀 Production Deployment

### Requirements:
- Docker 20.10+
- Docker Compose 2.0+
- 4GB RAM minimum
- 2 CPU cores recommended

### Security Checklist:
- [ ] Change default SECRET_KEY
- [ ] Set proper CORS_ORIGINS
- [ ] Enable HTTPS (SSL certificates)
- [ ] Set up firewall rules
- [ ] Monitor resource usage
- [ ] Regular backups

## 🎉 Sonuç

Bu Docker setup ile:
- ✅ **Tek komutla** tüm sistem ayağa kalkıyor
- ✅ **Production-ready** optimizasyonlar
- ✅ **Auto-scaling** ve **health checks**
- ✅ **Monitoring** ve **logging**
- ✅ **Security** best practices
- ✅ **Easy maintenance** ve **updates**

**Artık sadece `./start-docker.sh` komutu ile tüm MefapexChatBox sistemi ayağa kalkıyor! 🚀**
