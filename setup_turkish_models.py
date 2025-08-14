#!/usr/bin/env python3
"""
🇹🇷 MEFAPEX Turkish AI Model Setup Script
=========================================
Bu script Türkçe dil desteği için gerekli AI modellerini kurar ve test eder.
"""

import os
import sys
import logging
import time
from pathlib import Path

# Add current directory to path to import modules
sys.path.append(str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('turkish_model_setup.log')
    ]
)
logger = logging.getLogger(__name__)

def check_requirements():
    """Check if required packages are installed"""
    logger.info("🔍 Python paket gereksinimlerini kontrol ediliyor...")
    
    required_packages = [
        'torch',
        'transformers',
        'sentence_transformers',
        'qdrant_client'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            logger.info(f"✅ {package} yüklü")
        except ImportError:
            logger.error(f"❌ {package} eksik")
            missing_packages.append(package)
    
    if missing_packages:
        logger.error(f"❌ Eksik paketler: {', '.join(missing_packages)}")
        logger.info("💡 Çözüm: pip install -r requirements.txt")
        return False
    
    logger.info("✅ Tüm gerekli paketler yüklü")
    return True

def setup_environment():
    """Setup Turkish environment configuration"""
    logger.info("🔧 Türkçe model konfigürasyonu ayarlanıyor...")
    
    env_file = Path('.env')
    env_turkish = Path('.env.turkish')
    
    if not env_file.exists():
        if env_turkish.exists():
            logger.info("📁 .env.turkish dosyası .env olarak kopyalanıyor...")
            import shutil
            shutil.copy2(env_turkish, env_file)
        else:
            logger.info("📁 .env.example dosyası .env olarak kopyalanıyor...")
            env_example = Path('.env.example')
            if env_example.exists():
                import shutil
                shutil.copy2(env_example, env_file)
            else:
                logger.error("❌ .env.example dosyası bulunamadı!")
                return False
    
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
        logger.info("✅ Environment değişkenleri yüklendi")
    except ImportError:
        logger.warning("⚠️ python-dotenv yüklü değil, environment değişkenleri manual olarak ayarlanmalı")
    
    return True

def download_and_test_models():
    """Download and test Turkish AI models"""
    logger.info("🤖 Türkçe AI modelleri indiriliyor ve test ediliyor...")
    
    try:
        from sentence_transformers import SentenceTransformer
        import torch
        
        # Test Turkish sentence model
        logger.info("📚 Türkçe cümle modeli test ediliyor...")
        try:
            turkish_model = SentenceTransformer('emrecan/bert-base-turkish-cased-mean-nli-stsb-tr')
            test_text = "Merhaba, ben MEFAPEX AI asistanıyım."
            embedding = turkish_model.encode([test_text])
            logger.info(f"✅ Türkçe model başarılı - Boyut: {embedding.shape}")
            del turkish_model  # Free memory
        except Exception as e:
            logger.warning(f"⚠️ Ana Türkçe model başarısız: {e}")
            logger.info("🔄 Çok dilli modele geçiliyor...")
            
            # Fallback to multilingual
            multilingual_model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
            test_text = "Merhaba, ben MEFAPEX AI asistanıyım."
            embedding = multilingual_model.encode([test_text])
            logger.info(f"✅ Çok dilli model başarılı - Boyut: {embedding.shape}")
            del multilingual_model
        
        # Test text generation model
        logger.info("💬 Türkçe metin üretim modeli test ediliyor...")
        try:
            from transformers import pipeline
            generator = pipeline('text-generation', 
                               model='ytu-ce-cosmos/turkish-gpt2-large',
                               max_length=50,
                               do_sample=True,
                               temperature=0.7)
            test_prompt = "Merhaba"
            result = generator(test_prompt, max_length=30, num_return_sequences=1)
            logger.info(f"✅ Türkçe metin üretimi başarılı: {result[0]['generated_text'][:50]}...")
            del generator
        except Exception as e:
            logger.warning(f"⚠️ Türkçe metin üretim modeli başarısız: {e}")
            logger.info("🔄 İngilizce fallback kullanılacak...")
        
        # Force cleanup
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        logger.info("✅ Model testleri tamamlandı")
        return True
        
    except Exception as e:
        logger.error(f"❌ Model indirme/test başarısız: {e}")
        return False

def test_model_manager():
    """Test the enhanced model manager"""
    logger.info("🧠 Gelişmiş model manager test ediliyor...")
    
    try:
        from model_manager import model_manager
        
        # Test Turkish language detection
        turkish_text = "Fabrika çalışma saatleri nelerdir?"
        english_text = "What are the factory working hours?"
        
        logger.info("🇹🇷 Türkçe dil algılama test ediliyor...")
        turkish_detected = model_manager.detect_language(turkish_text)
        english_detected = model_manager.detect_language(english_text)
        
        logger.info(f"Türkçe metin algılama: {turkish_detected}")
        logger.info(f"İngilizce metin algılama: {english_detected}")
        
        # Test embeddings
        logger.info("🎯 Embedding üretimi test ediliyor...")
        turkish_embedding = model_manager.generate_embedding(turkish_text, force_turkish=True)
        english_embedding = model_manager.generate_embedding(english_text, force_turkish=False)
        
        logger.info(f"Türkçe embedding boyutu: {len(turkish_embedding)}")
        logger.info(f"İngilizce embedding boyutu: {len(english_embedding)}")
        
        # Test model info
        model_info = model_manager.get_model_info()
        logger.info("📊 Model bilgileri:")
        for key, value in model_info.items():
            if key != 'cache_info':  # Skip detailed cache info
                logger.info(f"  {key}: {value}")
        
        logger.info("✅ Model manager testleri başarılı")
        return True
        
    except Exception as e:
        logger.error(f"❌ Model manager test başarısız: {e}")
        return False

def create_startup_script():
    """Create a startup script for easy launching"""
    logger.info("🚀 Başlatma scripti oluşturuluyor...")
    
    startup_script = """#!/bin/bash
# 🇹🇷 MEFAPEX Turkish Chatbot Startup Script
echo "🇹🇷 MEFAPEX Türkçe Chatbot Başlatılıyor..."

# Virtual environment kontrolü
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment bulunamadı!"
    echo "💡 python -m venv .venv komutu ile oluşturun"
    exit 1
fi

# Virtual environment aktivasyonu
echo "🔧 Virtual environment aktive ediliyor..."
source .venv/bin/activate

# Python versiyonu kontrolü
python_version=$(python --version 2>&1)
echo "🐍 Python versiyonu: $python_version"

# Gerekli paketlerin kontrolü
echo "📦 Paket gereksinimlerini kontrol ediliyor..."
pip check

# Türkçe modellerin varlığını kontrol
echo "🤖 Türkçe AI modelleri kontrol ediliyor..."
python -c "from model_manager import model_manager; print('✅ Model Manager hazır')"

# Ana uygulamayı başlat
echo "🚀 MEFAPEX Chatbot başlatılıyor..."
echo "🌐 Tarayıcınızda http://localhost:8000 adresini açın"
python main.py
"""

    script_path = Path('start_turkish.sh')
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(startup_script)
    
    # Make executable on Unix systems
    if sys.platform != 'win32':
        os.chmod(script_path, 0o755)
    
    logger.info(f"✅ Başlatma scripti oluşturuldu: {script_path}")
    
    # Create Windows batch file too
    windows_script = """@echo off
REM 🇹🇷 MEFAPEX Turkish Chatbot Startup Script (Windows)
echo 🇹🇷 MEFAPEX Türkçe Chatbot Başlatılıyor...

REM Virtual environment kontrolü
if not exist ".venv" (
    echo ❌ Virtual environment bulunamadı!
    echo 💡 python -m venv .venv komutu ile oluşturun
    pause
    exit /b 1
)

REM Virtual environment aktivasyonu
echo 🔧 Virtual environment aktive ediliyor...
call .venv\\Scripts\\activate.bat

REM Python versiyonu kontrolü
python --version

REM Gerekli paketlerin kontrolü
echo 📦 Paket gereksinimlerini kontrol ediliyor...
pip check

REM Türkçe modellerin varlığını kontrol
echo 🤖 Türkçe AI modelleri kontrol ediliyor...
python -c "from model_manager import model_manager; print('✅ Model Manager hazır')"

REM Ana uygulamayı başlat
echo 🚀 MEFAPEX Chatbot başlatılıyor...
echo 🌐 Tarayıcınızda http://localhost:8000 adresini açın
python main.py
pause
"""
    
    windows_script_path = Path('start_turkish.bat')
    with open(windows_script_path, 'w', encoding='utf-8') as f:
        f.write(windows_script)
    
    logger.info(f"✅ Windows başlatma scripti oluşturuldu: {windows_script_path}")

def main():
    """Main setup function"""
    logger.info("🇹🇷 MEFAPEX Türkçe AI Model Kurulum Başlatılıyor...")
    logger.info("=" * 60)
    
    start_time = time.time()
    
    # Check requirements
    if not check_requirements():
        logger.error("❌ Gereksinimler karşılanmadı!")
        return False
    
    # Setup environment
    if not setup_environment():
        logger.error("❌ Environment kurulumu başarısız!")
        return False
    
    # Download and test models
    if not download_and_test_models():
        logger.error("❌ Model kurulumu başarısız!")
        return False
    
    # Test model manager
    if not test_model_manager():
        logger.error("❌ Model manager testi başarısız!")
        return False
    
    # Create startup scripts
    create_startup_script()
    
    end_time = time.time()
    duration = end_time - start_time
    
    logger.info("=" * 60)
    logger.info("🎉 TÜRKÇE MODEL KURULUMU TAMAMLANDI!")
    logger.info(f"⏱️ Toplam süre: {duration:.2f} saniye")
    logger.info("")
    logger.info("📋 SONRAKI ADIMLAR:")
    logger.info("1. 🚀 Chatbot'u başlatmak için: python main.py")
    logger.info("2. 🌐 Tarayıcıda açın: http://localhost:8000")
    logger.info("3. 🔑 Giriş bilgileri: demo / 1234")
    logger.info("4. 🇹🇷 Türkçe sorular sorun!")
    logger.info("")
    logger.info("💡 ÖRNEK TÜRKÇE SORULAR:")
    logger.info("   • Fabrika çalışma saatleri nelerdir?")
    logger.info("   • İzin başvurusu nasıl yapılır?")
    logger.info("   • Güvenlik kuralları nelerdir?")
    logger.info("   • Yapay zeka hakkında bilgi ver")
    logger.info("")
    logger.info("🔧 Kolay başlatma için:")
    logger.info("   Linux/Mac: ./start_turkish.sh")
    logger.info("   Windows: start_turkish.bat")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n⏹️ Kurulum kullanıcı tarafından iptal edildi")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Beklenmeyen hata: {e}")
        sys.exit(1)
