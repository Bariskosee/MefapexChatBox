# Qdrant Geçiş Rehberi

## ✅ Başarıyla Tamamlanan Adımlar

1. **Docker ile Qdrant Kurulumu**
   ```bash
   docker run -d -p 6333:6333 -p 6334:6334 --name qdrant-server qdrant/qdrant
   ```
   
2. **Qdrant Sunucusu Çalışıyor**
   - Container ID: d086916dc489
   - Port: 6333 (API), 6334 (gRPC)
   - Status: Running ✅

3. **Proje Yapılandırması**
   - main.py: Qdrant entegrasyonu mevcut ✅
   - .env: Qdrant ayarları yapılandırılmış ✅
   - embedding_loader.py: FAQ yükleme scripti hazır ✅

## ⚠️ Mevcut Sorun

OpenAI API quota sorunu nedeniyle embeddings oluşturulamıyor:
```
Error code: 429 - You exceeded your current quota
```

## 🚀 Çözüm Seçenekleri

### Seçenek 1: OpenAI API Kredisi Ekle
- OpenAI hesabınıza kredi ekleyin
- embedding_loader.py'yi çalıştırın
- FAQ verileri otomatik yüklenecek

### Seçenek 2: Alternatif Embedding Modeli
- Hugging Face sentence-transformers kullanın
- Ücretsiz local embedding

### Seçenek 3: Mock Data ile Test
- Önceden hazırlanmış embeddings kullanın
- Test amaçlı çalıştırın

## 📋 Sonraki Adımlar

1. OpenAI API kredisi ekleyin VEYA
2. Alternatif embedding yöntemi seçin
3. `python embedding_loader.py` çalıştırın
4. `python main.py` ile gerçek Qdrant serverını başlatın

## 🔧 Qdrant Yönetim Komutları

```bash
# Qdrant durumunu kontrol et
docker ps

# Qdrant loglarını görüntüle
docker logs qdrant-server

# Qdrant'ı durdur
docker stop qdrant-server

# Qdrant'ı başlat
docker start qdrant-server

# Qdrant'ı kaldır
docker rm qdrant-server
```

## 🌐 API Test

Qdrant API'sini test etmek için:
```bash
curl http://localhost:6333/
```

Bu size Qdrant'ın çalıştığını doğrulayacak.
