#!/usr/bin/env python3
"""
MEFAPEX ChatBox Otomatik Kurulum Script'i
Python 3.11+ ile uyumlu setup ve dependency management
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def print_header():
    """Kurulum başlığını göster"""
    print("🚀 MEFAPEX ChatBox Otomatik Kurulum")
    print("=" * 50)
    print("✅ Python 3.11+ uyumlu kurulum")
    print("✅ Dependency management")
    print("✅ Virtual environment setup")
    print("=" * 50)

def check_python_version():
    """Python versiyonunu kontrol et"""
    print("\n🐍 Python versiyonu kontrol ediliyor...")
    
    version = sys.version_info
    print(f"   Mevcut Python: {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 11):
        print("❌ HATA: Python 3.11+ gerekli!")
        print("   Python 3.11+ indirin: https://www.python.org/downloads/")
        sys.exit(1)
    
    print("✅ Python versiyonu uygun!")
    return f"{version.major}.{version.minor}"

def check_system():
    """Sistem gereksinimlerini kontrol et"""
    print("\n🖥️ Sistem bilgileri:")
    print(f"   İşletim Sistemi: {platform.system()} {platform.release()}")
    print(f"   Mimari: {platform.machine()}")
    print(f"   Python Path: {sys.executable}")

def create_virtual_env():
    """Virtual environment oluştur"""
    print("\n📦 Virtual environment kontrol ediliyor...")
    
    venv_path = Path(".venv")
    
    if venv_path.exists():
        print("✅ Virtual environment mevcut")
        return str(venv_path)
    
    print("🔧 Virtual environment oluşturuluyor...")
    try:
        subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True)
        print("✅ Virtual environment oluşturuldu")
        return str(venv_path)
    except subprocess.CalledProcessError as e:
        print(f"❌ Virtual environment oluşturulamadı: {e}")
        sys.exit(1)

def get_pip_executable():
    """Doğru pip executable'ını bul"""
    system = platform.system()
    
    if system == "Windows":
        return str(Path(".venv/Scripts/pip"))
    else:
        return str(Path(".venv/bin/pip"))

def get_python_executable():
    """Doğru python executable'ını bul"""
    system = platform.system()
    
    if system == "Windows":
        return str(Path(".venv/Scripts/python"))
    else:
        return str(Path(".venv/bin/python"))

def install_dependencies():
    """Dependencies'leri yükle"""
    print("\n📚 Dependencies yükleniyor...")
    
    pip_path = get_pip_executable()
    
    try:
        # Pip'i güncelle
        print("🔄 pip güncelleniyor...")
        subprocess.run([pip_path, "install", "--upgrade", "pip"], check=True)
        
        # Requirements'ları yükle
        print("📦 Requirements yükleniyor...")
        subprocess.run([pip_path, "install", "-r", "requirements.txt"], check=True)
        
        print("✅ Tüm dependencies başarıyla yüklendi!")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Dependencies yüklenemedi: {e}")
        print("\n🔧 Manuel kurulum deneyin:")
        print(f"   {pip_path} install -r requirements.txt")
        sys.exit(1)

def test_installation():
    """Kurulumu test et"""
    print("\n🧪 Kurulum test ediliyor...")
    
    python_path = get_python_executable()
    
    # Critical imports'u test et
    test_imports = [
        "fastapi",
        "uvicorn", 
        "qdrant_client",
        "transformers",
        "sentence_transformers"
    ]
    
    for module in test_imports:
        try:
            result = subprocess.run([
                python_path, "-c", f"import {module}; print('✅ {module}')"
            ], capture_output=True, text=True, check=True)
            print(f"   {result.stdout.strip()}")
        except subprocess.CalledProcessError:
            print(f"❌ {module} import hatası!")
            return False
    
    print("✅ Tüm testler başarılı!")
    return True

def create_env_file():
    """Environment dosyası oluştur"""
    print("\n⚙️ Environment dosyası kontrol ediliyor...")
    
    env_file = Path(".env")
    
    if env_file.exists():
        print("✅ .env dosyası mevcut")
        return
    
    print("🔧 .env dosyası oluşturuluyor...")
    
    env_content = """# MEFAPEX ChatBox Environment Configuration
# Production için değerleri güncelleyin

# Application Settings
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=dev-secret-key-change-in-production

# AI Configuration  
USE_OPENAI=false
USE_HUGGINGFACE=true
OPENAI_API_KEY=your-openai-api-key-here

# Database Configuration
DATABASE_URL=sqlite:///./data/mefapex.db

# Vector Database (Qdrant)
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Cache (Redis)
REDIS_HOST=localhost
REDIS_PORT=6379

# Security & CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8000,http://127.0.0.1:8000
JWT_SECRET_KEY=your-jwt-secret-key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60

# Monitoring
ENABLE_MONITORING=true
LOG_LEVEL=INFO
"""
    
    with open(env_file, "w", encoding="utf-8") as f:
        f.write(env_content)
    
    print("✅ .env dosyası oluşturuldu")

def create_run_script():
    """Çalıştırma scripti oluştur"""
    print("\n🚀 Çalıştırma scripti oluşturuluyor...")
    
    system = platform.system()
    
    if system == "Windows":
        script_name = "run.bat"
        script_content = """@echo off
echo 🚀 MEFAPEX ChatBox başlatılıyor...
echo.

REM Virtual environment'ı aktive et
call .venv\\Scripts\\activate

REM Python versiyonunu kontrol et
python --version

REM Serveri başlat
echo ✅ Server başlatılıyor: http://localhost:8000
echo 🔑 Giriş: demo / 1234
echo.
python main.py

pause
"""
    else:
        script_name = "run.sh"
        script_content = """#!/bin/bash
echo "🚀 MEFAPEX ChatBox başlatılıyor..."
echo

# Virtual environment'ı aktive et
source .venv/bin/activate

# Python versiyonunu kontrol et
python --version

# Serveri başlat
echo "✅ Server başlatılıyor: http://localhost:8000"
echo "🔑 Giriş: demo / 1234"
echo
python main.py
"""
    
    script_path = Path(script_name)
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script_content)
    
    # Unix sistemlerde executable yap
    if system != "Windows":
        os.chmod(script_path, 0o755)
    
    print(f"✅ {script_name} oluşturuldu")

def show_completion_message():
    """Kurulum tamamlama mesajı"""
    print("\n" + "="*60)
    print("🎉 MEFAPEX ChatBox kurulumu tamamlandı!")
    print("="*60)
    print()
    print("🚀 Sistemi başlatmak için:")
    
    system = platform.system()
    if system == "Windows":
        print("   ./run.bat")
        print("   VEYA: .venv\\Scripts\\activate && python main.py")
    else:
        print("   ./run.sh")
        print("   VEYA: source .venv/bin/activate && python main.py")
    
    print()
    print("🌐 Erişim adresleri:")
    print("   Ana uygulama: http://localhost:8000")
    print("   API docs:     http://localhost:8000/docs")
    print("   Health check: http://localhost:8000/health")
    print()
    print("🔑 Demo giriş bilgileri:")
    print("   Kullanıcı: demo")
    print("   Şifre:     1234")
    print()
    print("📚 Daha fazla bilgi için README.md dosyasını okuyun")
    print("🆘 Sorun yaşarsanız: https://github.com/Bariskosee/MefapexChatBox/issues")
    print("="*60)

def main():
    """Ana kurulum fonksiyonu"""
    try:
        print_header()
        
        # Python versiyonunu kontrol et
        python_version = check_python_version()
        
        # Sistem bilgilerini göster
        check_system()
        
        # Virtual environment oluştur
        create_virtual_env()
        
        # Dependencies'leri yükle
        install_dependencies()
        
        # Kurulumu test et
        if not test_installation():
            print("❌ Kurulum testi başarısız!")
            sys.exit(1)
        
        # Environment dosyası oluştur
        create_env_file()
        
        # Çalıştırma scripti oluştur
        create_run_script()
        
        # Tamamlama mesajı
        show_completion_message()
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Kurulum iptal edildi!")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Beklenmeyen hata: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
