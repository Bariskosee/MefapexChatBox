#!/bin/bash

# Log Rotation Script for MEFAPEX
# Bu script büyük log dosyalarını otomatik olarak yönetir

LOG_DIR="/Users/bariskose/Downloads/MefapexChatBox-main/logs"
BACKUP_DIR="$LOG_DIR/backup"
MAX_SIZE="1M"  # 1MB üzerindeki dosyalar işleme alınır
KEEP_LINES=100 # Dosyada kaç satır kalacak

echo "🧹 MEFAPEX Log Rotation Started - $(date)"

# Backup dizinini oluştur
mkdir -p "$BACKUP_DIR"

# Büyük log dosyalarını kontrol et
for logfile in "$LOG_DIR"/*.log; do
    if [ -f "$logfile" ]; then
        # Dosya boyutunu kontrol et
        size=$(stat -f%z "$logfile" 2>/dev/null || echo 0)
        
        if [ "$size" -gt 1048576 ]; then  # 1MB = 1048576 bytes
            filename=$(basename "$logfile")
            echo "📁 Processing large file: $filename (${size} bytes)"
            
            # Backup oluştur
            backup_name="${filename%.*}_$(date +%Y%m%d_%H%M%S).log"
            cp "$logfile" "$BACKUP_DIR/$backup_name"
            echo "✅ Backup created: $backup_name"
            
            # Dosyayı kısalt (son 100 satırı koru)
            tail -$KEEP_LINES "$logfile" > "${logfile}.tmp"
            mv "${logfile}.tmp" "$logfile"
            echo "✂️  File truncated, kept last $KEEP_LINES lines"
            
            # Log rotation bilgisini dosyaya ekle
            echo "# Log rotated on $(date) - Previous content backed up as $backup_name" >> "$logfile"
        fi
    fi
done

# Eski backup dosyalarını temizle (30 günden eski)
find "$BACKUP_DIR" -name "*.log" -mtime +30 -delete 2>/dev/null
echo "🗑️  Old backups (30+ days) cleaned"

echo "✅ Log rotation completed - $(date)"
echo ""

# Sonuçları göster
echo "📊 Current log sizes:"
du -h "$LOG_DIR"/*.log 2>/dev/null | sort -hr

echo ""
echo "📦 Available backups:"
ls -la "$BACKUP_DIR"/ | tail -5
