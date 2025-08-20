"""
🔄 AI Mikroservis Adaptörü
=========================
Mevcut model_manager arayüzünü koruyarak AI mikroservisine proxy görevi görür
"""
import logging
import asyncio
from typing import List, Dict, Any, Optional
import threading
import time

logger = logging.getLogger(__name__)

class AIServiceAdapter:
    """
    AI Mikroservis Adaptörü
    ========================
    Mevcut model_manager API'sini koruyarak AI servisine yönlendirir
    Fallback olarak mevcut model_manager'ı kullanır
    """
    
    def __init__(self, enable_ai_service: bool = True):
        self.enable_ai_service = enable_ai_service
        self._original_model_manager = None
        self._ai_client = None
        self._fallback_mode = False
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Performance tracking
        self._request_count = 0
        self._error_count = 0
        self._fallback_count = 0
        
        logger.info(f"🔄 AI Service Adapter initialized (AI Service: {'enabled' if enable_ai_service else 'disabled'})")
    
    def set_original_model_manager(self, model_manager):
        """Orijinal model manager'ı ayarla (fallback için)"""
        self._original_model_manager = model_manager
        logger.info("✅ Original model manager set for fallback")
    
    async def _get_ai_client(self):
        """AI istemcisini al"""
        if not self.enable_ai_service:
            return None
        
        if self._ai_client is None:
            try:
                from services.ai_service.client import get_ai_client
                self._ai_client = await get_ai_client()
                logger.info("✅ AI client connected")
            except Exception as e:
                logger.error(f"❌ AI client connection failed: {e}")
                self._fallback_mode = True
                return None
        
        return self._ai_client
    
    async def _execute_with_fallback(self, ai_func, fallback_func, *args, **kwargs):
        """AI servis ile çalıştır, başarısızsa fallback kullan"""
        with self._lock:
            self._request_count += 1
        
        if not self.enable_ai_service or self._fallback_mode:
            # Direkt fallback kullan
            with self._lock:
                self._fallback_count += 1
            return fallback_func(*args, **kwargs)
        
        try:
            # AI servis dene
            result = await ai_func(*args, **kwargs)
            return result
            
        except Exception as e:
            logger.warning(f"⚠️ AI service call failed, using fallback: {e}")
            
            with self._lock:
                self._error_count += 1
                self._fallback_count += 1
            
            # Fallback kullan
            if self._original_model_manager and hasattr(self._original_model_manager, fallback_func.__name__):
                return fallback_func(*args, **kwargs)
            else:
                return fallback_func(*args, **kwargs)
    
    # Model Manager API Uyumluluğu
    
    def generate_embedding(self, text: str, force_turkish: bool = None) -> List[float]:
        """Embedding oluştur - sync wrapper"""
        return asyncio.run(self.generate_embedding_async(text, force_turkish))
    
    async def generate_embedding_async(self, text: str, force_turkish: bool = None) -> List[float]:
        """Embedding oluştur - async"""
        async def ai_func(text, force_turkish):
            client = await self._get_ai_client()
            if client:
                return await client.generate_embedding(text, force_turkish)
            raise Exception("AI client not available")
        
        def fallback_func(text, force_turkish):
            if self._original_model_manager:
                return self._original_model_manager.generate_embedding(text, force_turkish)
            else:
                # Basit fallback
                from services.ai_service.client import FallbackAIManager
                return FallbackAIManager.generate_embedding_fallback(text)
        
        return await self._execute_with_fallback(ai_func, fallback_func, text, force_turkish)
    
    def generate_text_response(self, prompt: str, max_length: int = 80, turkish_context: bool = True) -> str:
        """Metin yanıtı oluştur - sync wrapper"""
        return asyncio.run(self.generate_text_response_async(prompt, max_length, turkish_context))
    
    async def generate_text_response_async(self, prompt: str, max_length: int = 80, turkish_context: bool = True) -> str:
        """Metin yanıtı oluştur - async"""
        async def ai_func(prompt, max_length, turkish_context):
            client = await self._get_ai_client()
            if client:
                return await client.generate_text(prompt, max_length, turkish_context)
            raise Exception("AI client not available")
        
        def fallback_func(prompt, max_length, turkish_context):
            if self._original_model_manager:
                return self._original_model_manager.generate_text_response(prompt, max_length, turkish_context)
            else:
                from services.ai_service.client import FallbackAIManager
                return FallbackAIManager.generate_text_fallback(prompt)
        
        return await self._execute_with_fallback(ai_func, fallback_func, prompt, max_length, turkish_context)
    
    async def generate_huggingface_response(self, message: str, user_id: str = None) -> str:
        """Hugging Face yanıt oluştur"""
        async def ai_func(message, user_id):
            client = await self._get_ai_client()
            if client:
                return await client.generate_huggingface_response(message, user_id)
            raise Exception("AI client not available")
        
        def fallback_func(message, user_id):
            if self._original_model_manager:
                return asyncio.run(self._original_model_manager.generate_huggingface_response(message, user_id))
            else:
                from services.ai_service.client import FallbackAIManager
                return FallbackAIManager.generate_text_fallback(message)
        
        return await self._execute_with_fallback(ai_func, fallback_func, message, user_id)
    
    def detect_language(self, text: str) -> str:
        """Dil tanıma - sync wrapper"""
        return asyncio.run(self.detect_language_async(text))
    
    async def detect_language_async(self, text: str) -> str:
        """Dil tanıma - async"""
        async def ai_func(text):
            client = await self._get_ai_client()
            if client:
                return await client.detect_language(text)
            raise Exception("AI client not available")
        
        def fallback_func(text):
            if self._original_model_manager:
                return self._original_model_manager.detect_language(text)
            else:
                from services.ai_service.client import FallbackAIManager
                return FallbackAIManager.detect_language_fallback(text)
        
        return await self._execute_with_fallback(ai_func, fallback_func, text)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Model bilgilerini al"""
        return asyncio.run(self.get_model_info_async())
    
    async def get_model_info_async(self) -> Dict[str, Any]:
        """Model bilgilerini al - async"""
        try:
            if self.enable_ai_service and not self._fallback_mode:
                client = await self._get_ai_client()
                if client:
                    ai_info = await client.get_model_info()
                    
                    # Adapter istatistiklerini ekle
                    ai_info["adapter_stats"] = {
                        "ai_service_enabled": self.enable_ai_service,
                        "fallback_mode": self._fallback_mode,
                        "request_count": self._request_count,
                        "error_count": self._error_count,
                        "fallback_count": self._fallback_count,
                        "success_rate": ((self._request_count - self._error_count) / max(self._request_count, 1)) * 100
                    }
                    
                    return ai_info
            
            # Fallback
            if self._original_model_manager:
                fallback_info = self._original_model_manager.get_model_info()
                fallback_info["adapter_stats"] = {
                    "ai_service_enabled": False,
                    "fallback_mode": True,
                    "note": "Using original model manager"
                }
                return fallback_info
            else:
                return {
                    "adapter_stats": {
                        "ai_service_enabled": False,
                        "fallback_mode": True,
                        "error": "No model manager available"
                    }
                }
                
        except Exception as e:
            logger.error(f"Model info error: {e}")
            return {
                "adapter_stats": {
                    "error": str(e),
                    "fallback_mode": True
                }
            }
    
    def clear_caches(self):
        """Cache temizliği"""
        return asyncio.run(self.clear_caches_async())
    
    async def clear_caches_async(self):
        """Cache temizliği - async"""
        try:
            if self.enable_ai_service and not self._fallback_mode:
                client = await self._get_ai_client()
                if client:
                    await client.cleanup_models()
                    logger.info("✅ AI service caches cleared")
                    return
            
            # Fallback
            if self._original_model_manager:
                self._original_model_manager.clear_caches()
                logger.info("✅ Original model manager caches cleared")
                
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
    
    def unload_all_models(self):
        """Tüm modelleri kaldır"""
        return asyncio.run(self.unload_all_models_async())
    
    async def unload_all_models_async(self):
        """Tüm modelleri kaldır - async"""
        try:
            if self.enable_ai_service and not self._fallback_mode:
                client = await self._get_ai_client()
                if client:
                    # AI servis model'larını kaldıramayız, sadece cache temizleriz
                    await client.cleanup_models()
                    logger.info("✅ AI service models cleaned")
                    return
            
            # Fallback
            if self._original_model_manager:
                self._original_model_manager.unload_all_models()
                logger.info("✅ Original models unloaded")
                
        except Exception as e:
            logger.error(f"Model unload error: {e}")
    
    def cleanup_resources(self):
        """Kaynakları temizle"""
        return asyncio.run(self.cleanup_resources_async())
    
    async def cleanup_resources_async(self):
        """Kaynakları temizle - async"""
        try:
            # AI client'ı kapat
            if self._ai_client:
                from services.ai_service.client import close_ai_client
                await close_ai_client()
                self._ai_client = None
            
            # Original model manager'ı temizle
            if self._original_model_manager:
                self._original_model_manager.cleanup_resources()
            
            logger.info("✅ AI Service Adapter cleaned up")
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
    
    # Ek AI servis metodları
    
    async def warmup_models(self):
        """Modelleri ısıt"""
        try:
            if self.enable_ai_service and not self._fallback_mode:
                client = await self._get_ai_client()
                if client:
                    return await client.warmup_models()
            
            # Fallback
            if self._original_model_manager and hasattr(self._original_model_manager, 'warmup_models'):
                self._original_model_manager.warmup_models()
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Model warmup error: {e}")
            return False
    
    async def get_service_health(self) -> Dict[str, Any]:
        """Servis sağlığını kontrol et"""
        try:
            if self.enable_ai_service:
                client = await self._get_ai_client()
                if client:
                    return await client.get_service_health()
            
            return {
                "status": "healthy",
                "service": "fallback",
                "adapter_mode": "original_model_manager"
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "adapter_mode": "fallback"
            }
    
    def set_auto_cleanup(self, enabled: bool, cleanup_interval: int = 300, max_idle_time: int = 600):
        """Auto cleanup ayarları (uyumluluk için)"""
        if self._original_model_manager and hasattr(self._original_model_manager, 'set_auto_cleanup'):
            self._original_model_manager.set_auto_cleanup(enabled, cleanup_interval, max_idle_time)
        
        logger.info(f"🔧 Auto cleanup configured: {enabled}")
    
    def get_lazy_loading_statistics(self) -> Dict[str, Any]:
        """Lazy loading istatistikleri"""
        return asyncio.run(self.get_lazy_loading_statistics_async())
    
    async def get_lazy_loading_statistics_async(self) -> Dict[str, Any]:
        """Lazy loading istatistikleri - async"""
        try:
            if self.enable_ai_service and not self._fallback_mode:
                client = await self._get_ai_client()
                if client:
                    return await client.get_lazy_loading_stats()
            
            # Fallback
            if self._original_model_manager and hasattr(self._original_model_manager, 'get_lazy_loading_statistics'):
                return self._original_model_manager.get_lazy_loading_statistics()
            
            return {"adapter_mode": "fallback", "stats": "not_available"}
            
        except Exception as e:
            logger.error(f"Lazy loading stats error: {e}")
            return {"error": str(e)}
    
    # Property uyumluluğu için
    
    @property
    def device(self) -> str:
        """Cihaz bilgisi"""
        if self._original_model_manager:
            return self._original_model_manager.device
        return "ai_service"
    
    @property
    def sentence_model(self):
        """Sentence model (uyumluluk için)"""
        logger.warning("⚠️ Direct sentence_model access not supported in AI service mode")
        return None
    
    @property
    def turkish_sentence_model(self):
        """Turkish sentence model (uyumluluk için)"""
        logger.warning("⚠️ Direct turkish_sentence_model access not supported in AI service mode")
        return None
    
    @property
    def english_sentence_model(self):
        """English sentence model (uyumluluk için)"""
        logger.warning("⚠️ Direct english_sentence_model access not supported in AI service mode")
        return None
    
    @property
    def text_generator(self):
        """Text generator (uyumluluk için)"""
        logger.warning("⚠️ Direct text_generator access not supported in AI service mode")
        return None
    
    # Alias metodlar (uyumluluk için)
    
    def get_sentence_embedding(self, text: str) -> Optional[List[float]]:
        """Sentence embedding al (alias)"""
        try:
            return self.generate_embedding(text)
        except Exception as e:
            logger.error(f"Sentence embedding error: {e}")
            return None
    
    def get_embedding_model_for_text(self, text: str):
        """Metin için embedding modeli al (uyumluluk için)"""
        logger.warning("⚠️ Direct model access not supported in AI service mode")
        return None

# Global adapter instance
_ai_adapter = None

def get_ai_adapter(enable_ai_service: bool = True) -> AIServiceAdapter:
    """Global AI adapter'ı al"""
    global _ai_adapter
    
    if _ai_adapter is None:
        _ai_adapter = AIServiceAdapter(enable_ai_service)
    
    return _ai_adapter

def set_original_model_manager(model_manager):
    """Orijinal model manager'ı ayarla"""
    adapter = get_ai_adapter()
    adapter.set_original_model_manager(model_manager)
