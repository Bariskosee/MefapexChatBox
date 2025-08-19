#!/bin/bash
"""
🧹 MEFAPEX Project Cleanup Script
=================================
Bu script projedeki gereksiz dosyaları ve kod tekrarlarını temizler
"""

echo "🧹 MEFAPEX Proje Temizlik Scripti"
echo "================================="

# Temizlik öncesi durum
echo "📊 Temizlik öncesi durum:"
echo "Python dosyaları: $(find . -name "*.py" | wc -l)"
echo "Toplam dosya boyutu: $(du -sh . | cut -f1)"

# Cache ve log dosyalarını temizle
echo "🗑️ Cache ve log dosyaları temizleniyor..."
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "*.pyo" -delete 2>/dev/null || true
find . -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true
rm -rf logs/ 2>/dev/null || true
rm -f *.log 2>/dev/null || true

# Geçici dosyaları temizle
echo "🗑️ Geçici dosyalar temizleniyor..."
find . -name "*~" -delete 2>/dev/null || true
find . -name "*.tmp" -delete 2>/dev/null || true
find . -name "*.bak" -delete 2>/dev/null || true
find . -name ".DS_Store" -delete 2>/dev/null || true

# VS Code workspace dosyalarını koru ama gereksiz VS Code ayarlarını temizle
echo "🗑️ Editor geçici dosyaları temizleniyor..."
find .vscode -name "*.tmp" -delete 2>/dev/null || true

# Test coverage dosyalarını temizle
echo "🗑️ Test coverage dosyaları temizleniyor..."
rm -rf .coverage 2>/dev/null || true
rm -rf htmlcov/ 2>/dev/null || true
rm -rf .tox/ 2>/dev/null || true

# Virtual environment'i temizle (ama silme)
echo "🗑️ Virtual environment cache temizleniyor..."
find .venv -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find .venv -name "*.pyc" -delete 2>/dev/null || true

# Model cache'leri optimizasyonu (sadece boş klasörleri temizle)
echo "🗑️ Boş model klasörleri temizleniyor..."
find models_cache -type d -empty -delete 2>/dev/null || true

# Git geçici dosyalarını temizle
echo "🗑️ Git geçici dosyaları temizleniyor..."
git gc --prune=now 2>/dev/null || true

# Temizlik sonrası durum
echo ""
echo "✅ Temizlik tamamlandı!"
echo "📊 Temizlik sonrası durum:"
echo "Python dosyaları: $(find . -name "*.py" | wc -l)"
echo "Toplam dosya boyutu: $(du -sh . | cut -f1)"

echo ""
echo "🎯 Temizlenen öğeler:"
echo "  • Python cache dosyaları (__pycache__, *.pyc)"
echo "  • Test cache dosyaları (.pytest_cache)"
echo "  • Log dosyaları (*.log, logs/)"
echo "  • Geçici dosyalar (*~, *.tmp, *.bak)"
echo "  • Editor geçici dosyaları (.DS_Store)"
echo "  • Test coverage dosyaları"
echo "  • Git geçici dosyaları"
echo "  • Boş model klasörleri"

echo ""
echo "💡 Öneriler:"
echo "  • Bu scripti düzenli olarak çalıştırın"
echo "  • Büyük model dosyalarını .gitignore'a ekleyin"
echo "  • Test dosyalarını tests/ klasöründe organize edin"
echo "  • CI/CD pipeline'da otomatik temizlik kullanın"
