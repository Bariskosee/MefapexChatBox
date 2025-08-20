"""
🔄 AI Mikroservis Entegrasyon Dosyası
====================================
Ana uygulamayı AI mikroservisi ile entegre eder
"""
import logging
import os
from typing import Optional
from core.configuration import get_config

logger = logging.getLogger(__name__)

# AI Service konfigürasyonu
AI_SERVICE_ENABLED = os.getenv("AI_SERVICE_ENABLED", "true").lower() == "true"
AI_SERVICE_HOST = os.getenv("AI_SERVICE_HOST", "127.0.0.1")
AI_SERVICE_PORT = int(os.getenv("AI_SERVICE_PORT", "8001"))

def setup_ai_service_integration():
    """AI servis entegrasyonunu ayarla"""
    global model_manager
    
    try:
        if AI_SERVICE_ENABLED:
            logger.info("🔄 AI Mikroservis entegrasyonu etkinleştiriliyor...")
            
            # Orijinal model manager'ı yedekle
            from model_manager import model_manager as original_model_manager
            
            # AI Service adapter'ı kur
            from services.ai_service.adapter import get_ai_adapter, set_original_model_manager
            
            # Adapter'ı yapılandır
            ai_adapter = get_ai_adapter(enable_ai_service=True)
            set_original_model_manager(original_model_manager)
            
            # Global model_manager'ı değiştir
            import sys
            import model_manager as mm_module
            
            # Module seviyesinde değiştir
            mm_module.model_manager = ai_adapter
            
            # Global namespace'de de değiştir
            if 'model_manager' in globals():
                globals()['model_manager'] = ai_adapter
            
            logger.info(f"✅ AI Mikroservis entegrasyonu başarılı ({AI_SERVICE_HOST}:{AI_SERVICE_PORT})")
            
        else:
            logger.info("ℹ️ AI Mikroservis devre dışı, orijinal model manager kullanılıyor")
            
    except Exception as e:
        logger.error(f"❌ AI Mikroservis entegrasyonu başarısız: {e}")
        logger.info("🔄 Orijinal model manager ile devam ediliyor")

def get_model_manager():
    """Aktif model manager'ı al"""
    if AI_SERVICE_ENABLED:
        try:
            from services.ai_service.adapter import get_ai_adapter
            return get_ai_adapter()
        except Exception as e:
            logger.warning(f"AI adapter hatası, orijinal kullanılıyor: {e}")
    
    # Fallback
    from model_manager import model_manager
    return model_manager

async def cleanup_ai_service():
    """AI servis kaynaklarını temizle"""
    try:
        if AI_SERVICE_ENABLED:
            from services.ai_service.adapter import get_ai_adapter
            adapter = get_ai_adapter()
            await adapter.cleanup_resources_async()
            logger.info("✅ AI servis kaynakları temizlendi")
    except Exception as e:
        logger.error(f"AI servis temizlik hatası: {e}")

# Startup'ta otomatik entegrasyon
if AI_SERVICE_ENABLED:
    try:
        setup_ai_service_integration()
    except Exception as e:
        logger.error(f"Otomatik AI servis entegrasyonu başarısız: {e}")
