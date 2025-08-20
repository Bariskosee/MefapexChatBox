"""
🔄 Geliştirilmiş AI Mikroservis Entegrasyonu
===========================================
Resilient microservice architecture ile güvenilir entegrasyon

IYILEŞTIRMELER:
- Service Registry Pattern ile merkezi yönetim
- Circuit Breaker Pattern ile güvenilir fallback
- Graceful degradation ile robust error handling
- Race condition prevention
- Circular dependency elimination
"""

import logging
import os
import asyncio
from typing import Optional
from core.configuration import get_config

logger = logging.getLogger(__name__)

# Microservice configuration
AI_SERVICE_ENABLED = os.getenv("AI_SERVICE_ENABLED", "true").lower() == "true"
AI_SERVICE_HOST = os.getenv("AI_SERVICE_HOST", "127.0.0.1")
AI_SERVICE_PORT = int(os.getenv("AI_SERVICE_PORT", "8001"))
FALLBACK_STRATEGY = os.getenv("FALLBACK_STRATEGY", "progressive")  # progressive, immediate, disabled

class MicroserviceIntegrationManager:
    """
    Mikroservis Entegrasyon Yöneticisi
    =================================
    Tüm entegrasyon işlemlerini merkezi olarak yönetir
    """
    
    def __init__(self):
        self._initialized = False
        self._resilient_manager = None
        self._original_model_manager = None
        self._integration_mode = "none"
        
    async def initialize(self):
        """Entegrasyonu başlat"""
        if self._initialized:
            return
        
        try:
            logger.info("🔄 Mikroservis entegrasyonu başlatılıyor...")
            
            # Import resilient architecture
            from microservice_architecture_fix import (
                setup_resilient_microservice_architecture,
                create_resilient_model_manager
            )
            
            if AI_SERVICE_ENABLED:
                logger.info("🤖 AI Mikroservis modu etkinleştiriliyor...")
                
                # Backup original model manager
                await self._backup_original_model_manager()
                
                # Setup resilient architecture
                self._resilient_manager = await setup_resilient_microservice_architecture()
                self._integration_mode = "resilient_microservice"
                
                logger.info(f"✅ Resilient mikroservis entegrasyonu başarılı ({AI_SERVICE_HOST}:{AI_SERVICE_PORT})")
                
            else:
                logger.info("💻 Yerel model modu - mikroservis devre dışı")
                self._integration_mode = "local_only"
                await self._setup_local_only_mode()
            
            self._initialized = True
            
        except Exception as e:
            logger.error(f"❌ Mikroservis entegrasyonu başarısız: {e}")
            await self._setup_fallback_mode()
    
    async def _backup_original_model_manager(self):
        """Orijinal model manager'ı yedekle"""
        try:
            from model_manager import model_manager
            self._original_model_manager = model_manager
            logger.info("💾 Orijinal model manager yedeklendi")
        except Exception as e:
            logger.warning(f"Model manager backup failed: {e}")
    
    async def _setup_local_only_mode(self):
        """Sadece yerel model modunu kur"""
        try:
            from model_manager import model_manager
            # Ensure model manager is properly initialized
            if hasattr(model_manager, 'initialize') and not getattr(model_manager, '_initialized', False):
                await model_manager.initialize()
            
            self._resilient_manager = model_manager
            logger.info("✅ Yerel model modu kuruldu")
            
        except Exception as e:
            logger.error(f"Local model setup failed: {e}")
            raise
    
    async def _setup_fallback_mode(self):
        """Acil durum fallback modunu kur"""
        try:
            logger.warning("⚠️ Acil durum fallback modu etkinleştiriliyor...")
            
            from microservice_architecture_fix import FallbackProvider
            self._resilient_manager = FallbackProvider()
            self._integration_mode = "emergency_fallback"
            
            logger.info("🆘 Acil durum modu kuruldu")
            
        except Exception as e:
            logger.error(f"Fallback mode setup failed: {e}")
            # Son çare - en basit fallback
            self._resilient_manager = None
            self._integration_mode = "minimal_fallback"
    
    def get_model_manager(self):
        """Aktif model manager'ı al"""
        if not self._initialized:
            # Synchronous initialization for backward compatibility
            asyncio.create_task(self.initialize())
            
        return self._resilient_manager or self._get_minimal_fallback()
    
    def _get_minimal_fallback(self):
        """En basit fallback manager"""
        class MinimalFallback:
            def generate_embedding(self, text: str, **kwargs):
                return [0.0] * 384  # Empty embedding
            
            def generate_text(self, prompt: str, **kwargs):
                return "Servis geçici olarak kullanılamıyor. Lütfen daha sonra tekrar deneyin."
            
            def detect_language(self, text: str):
                return 'turkish' if any(c in 'çğıöşüÇĞIİÖŞÜ' for c in text) else 'other'
            
            def get_model_info(self):
                return {"status": "minimal_fallback", "message": "Temel servis modu"}
        
        return MinimalFallback()
    
    async def get_system_status(self):
        """Sistem durumunu al"""
        if not self._initialized:
            await self.initialize()
        
        status = {
            "integration_mode": self._integration_mode,
            "ai_service_enabled": AI_SERVICE_ENABLED,
            "ai_service_endpoint": f"{AI_SERVICE_HOST}:{AI_SERVICE_PORT}",
            "fallback_strategy": FALLBACK_STRATEGY,
            "initialized": self._initialized
        }
        
        # Get detailed status from resilient manager
        if self._resilient_manager and hasattr(self._resilient_manager, 'get_system_status'):
            try:
                detailed_status = self._resilient_manager.get_system_status()
                status["detailed_status"] = detailed_status
            except Exception as e:
                status["status_error"] = str(e)
        
        return status
    
    async def cleanup(self):
        """Temizlik işlemleri"""
        if self._resilient_manager and hasattr(self._resilient_manager, 'cleanup'):
            try:
                await self._resilient_manager.cleanup()
                logger.info("🧹 Mikroservis entegrasyonu temizlendi")
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
        
        self._initialized = False
    
    def force_fallback(self, reason: str = "Manual trigger"):
        """Fallback moduna zorla geç"""
        logger.warning(f"🔄 Fallback moduna zorla geçiliyor: {reason}")
        
        if self._original_model_manager:
            self._resilient_manager = self._original_model_manager
            self._integration_mode = "forced_fallback"
            logger.info("✅ Orijinal model manager'a geri dönüldü")
        else:
            asyncio.create_task(self._setup_fallback_mode())

# Global integration manager
_integration_manager = MicroserviceIntegrationManager()

def get_integration_manager() -> MicroserviceIntegrationManager:
    """Global entegrasyon manager'ı al"""
    return _integration_manager

async def setup_microservice_integration():
    """Mikroservis entegrasyonunu kur"""
    manager = get_integration_manager()
    await manager.initialize()
    return manager

def get_model_manager():
    """Model manager'ı al (backward compatibility)"""
    return _integration_manager.get_model_manager()

async def cleanup_microservice_integration():
    """Mikroservis entegrasyonunu temizle"""
    await _integration_manager.cleanup()

# Health check functions
async def check_ai_service_health():
    """AI servisi sağlık kontrolü"""
    try:
        import aiohttp
        
        health_url = f"http://{AI_SERVICE_HOST}:{AI_SERVICE_PORT}/health"
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
            async with session.get(health_url) as response:
                if response.status == 200:
                    health_data = await response.json()
                    return health_data.get("status") == "healthy"
                return False
                
    except Exception as e:
        logger.debug(f"AI service health check failed: {e}")
        return False

async def diagnose_microservice_issues():
    """Mikroservis sorunlarını teşhis et"""
    diagnosis = {
        "timestamp": asyncio.get_event_loop().time(),
        "ai_service_reachable": await check_ai_service_health(),
        "integration_status": await _integration_manager.get_system_status(),
        "recommendations": []
    }
    
    # Add recommendations based on diagnosis
    if not diagnosis["ai_service_reachable"]:
        diagnosis["recommendations"].extend([
            "AI servisi başlatılmamış olabilir",
            f"curl http://{AI_SERVICE_HOST}:{AI_SERVICE_PORT}/health ile kontrol edin",
            "python services/ai_service/main.py ile AI servisini başlatın"
        ])
    
    if diagnosis["integration_status"]["integration_mode"] == "emergency_fallback":
        diagnosis["recommendations"].extend([
            "Sistem acil durum modunda çalışıyor",
            "AI servis bağlantısını kontrol edin",
            "Logları inceleyin: tail -f logs/*.log"
        ])
    
    return diagnosis

# Startup integration
async def initialize_on_startup():
    """Uygulama başlangıcında entegrasyonu kur"""
    try:
        logger.info("🚀 Mikroservis entegrasyonu başlatılıyor...")
        
        # Initialize integration
        await setup_microservice_integration()
        
        # Replace global model manager
        import model_manager as mm_module
        mm_module.model_manager = get_model_manager()
        
        # Log status
        status = await _integration_manager.get_system_status()
        logger.info(f"📊 Entegrasyon durumu: {status['integration_mode']}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Startup integration failed: {e}")
        return False

# Automatic initialization (import-time)
if AI_SERVICE_ENABLED:
    logger.info("🔄 AI Mikroservis entegrasyonu import sırasında etkinleştiriliyor...")
    
    # Schedule initialization for next event loop
    def schedule_init():
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(initialize_on_startup())
            else:
                loop.run_until_complete(initialize_on_startup())
        except RuntimeError:
            # No event loop, will be initialized later
            logger.info("Event loop not ready, entegrasyon daha sonra yapılacak")
    
    try:
        schedule_init()
    except Exception as e:
        logger.warning(f"Import-time initialization failed: {e}")

else:
    logger.info("ℹ️ AI Mikroservis devre dışı - yerel model kullanılacak")
