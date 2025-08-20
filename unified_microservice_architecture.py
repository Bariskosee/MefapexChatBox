"""
🏗️ Birleşik Mikroservis Mimarisi
================================
Tüm mikroservis yaklaşımlarını tek bir tutarlı sistemde birleştirir

ÇÖZÜLEN SORUNLAR:
✅ Circular dependency elimination
✅ Race condition prevention  
✅ Consistent API interfaces
✅ Robust fallback mechanisms
✅ Thread-safe initialization
✅ Clear service boundaries

DESIGN PATTERNS:
- Service Registry Pattern
- Circuit Breaker Pattern
- Factory Pattern
- Singleton Pattern (thread-safe)
- Observer Pattern (for health monitoring)
"""

import logging
import asyncio
import threading
import time
import os
from typing import Dict, Any, List, Optional, Union, Protocol
from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass
from functools import wraps
import weakref

# Configure logging
logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION AND ENUMS
# =============================================================================

class ServiceMode(Enum):
    """Servis çalışma modları"""
    LOCAL_ONLY = "local_only"
    MICROSERVICE = "microservice"
    HYBRID = "hybrid"
    FALLBACK = "fallback"

class ServiceStatus(Enum):
    """Servis durumları"""
    UNKNOWN = "unknown"
    INITIALIZING = "initializing"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    OFFLINE = "offline"

@dataclass
class MicroserviceConfig:
    """Mikroservis yapılandırması"""
    ai_service_enabled: bool = True
    ai_service_host: str = "127.0.0.1"
    ai_service_port: int = 8001
    fallback_strategy: str = "progressive"  # progressive, immediate, disabled
    health_check_interval: int = 60
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 30
    max_retry_attempts: int = 3
    retry_delay: float = 1.0

    @classmethod
    def from_env(cls) -> 'MicroserviceConfig':
        """Environment'tan yapılandırma oluştur"""
        return cls(
            ai_service_enabled=os.getenv("AI_SERVICE_ENABLED", "true").lower() == "true",
            ai_service_host=os.getenv("AI_SERVICE_HOST", "127.0.0.1"),
            ai_service_port=int(os.getenv("AI_SERVICE_PORT", "8001")),
            fallback_strategy=os.getenv("FALLBACK_STRATEGY", "progressive"),
            health_check_interval=int(os.getenv("HEALTH_CHECK_INTERVAL", "60")),
            circuit_breaker_threshold=int(os.getenv("CIRCUIT_BREAKER_THRESHOLD", "5")),
            circuit_breaker_timeout=int(os.getenv("CIRCUIT_BREAKER_TIMEOUT", "30"))
        )

# =============================================================================
# INTERFACES AND PROTOCOLS
# =============================================================================

class IModelManager(Protocol):
    """Model manager interface"""
    
    def generate_embedding(self, text: str, force_turkish: bool = None) -> List[float]:
        """Embedding oluştur"""
        ...
    
    def generate_text_response(self, prompt: str, max_length: int = 80, turkish_context: bool = True) -> str:
        """Metin yanıtı oluştur"""
        ...
    
    async def generate_huggingface_response(self, message: str, user_id: str = None) -> str:
        """Hugging Face yanıt oluştur"""
        ...
    
    def detect_language(self, text: str) -> str:
        """Dil tanıma"""
        ...
    
    def get_model_info(self) -> Dict[str, Any]:
        """Model bilgilerini al"""
        ...
    
    def clear_caches(self) -> None:
        """Cache temizliği"""
        ...
    
    def cleanup_resources(self) -> None:
        """Kaynakları temizle"""
        ...

class IHealthMonitor(ABC):
    """Sağlık izleme interface"""
    
    @abstractmethod
    async def check_health(self) -> Dict[str, Any]:
        """Sağlık kontrolü"""
        pass
    
    @abstractmethod
    async def get_metrics(self) -> Dict[str, Any]:
        """Metrikleri al"""
        pass

class ICircuitBreaker(ABC):
    """Circuit breaker interface"""
    
    @abstractmethod
    def is_open(self) -> bool:
        """Circuit açık mı?"""
        pass
    
    @abstractmethod
    def record_success(self) -> None:
        """Başarılı çağrı kaydet"""
        pass
    
    @abstractmethod
    def record_failure(self) -> None:
        """Başarısız çağrı kaydet"""
        pass

# =============================================================================
# CIRCUIT BREAKER IMPLEMENTATION
# =============================================================================

class CircuitBreaker(ICircuitBreaker):
    """Thread-safe circuit breaker implementasyonu"""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 30):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "closed"  # closed, open, half-open
        self._lock = threading.Lock()
    
    def is_open(self) -> bool:
        with self._lock:
            if self.state == "open":
                if time.time() - self.last_failure_time > self.timeout:
                    self.state = "half-open"
                    return False
                return True
            return False
    
    def record_success(self) -> None:
        with self._lock:
            self.failure_count = 0
            self.state = "closed"
    
    def record_failure(self) -> None:
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                logger.warning(f"🔴 Circuit breaker AÇILDI - {self.failure_count} başarısızlık")

# =============================================================================
# SERVICE REGISTRY
# =============================================================================

class ServiceRegistry:
    """Merkezi servis kayıt sistemi"""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._health_monitors: Dict[str, IHealthMonitor] = {}
        self._circuit_breakers: Dict[str, ICircuitBreaker] = {}
        self._lock = threading.Lock()
        self._observers: List[weakref.ReferenceType] = []
    
    def register_service(self, name: str, service: Any, health_monitor: IHealthMonitor = None) -> None:
        """Servis kaydet"""
        with self._lock:
            self._services[name] = service
            if health_monitor:
                self._health_monitors[name] = health_monitor
            self._circuit_breakers[name] = CircuitBreaker()
            
        logger.info(f"📝 Servis kaydedildi: {name}")
        self._notify_observers(f"service_registered:{name}")
    
    def get_service(self, name: str) -> Optional[Any]:
        """Servis al"""
        with self._lock:
            return self._services.get(name)
    
    def get_circuit_breaker(self, name: str) -> Optional[ICircuitBreaker]:
        """Circuit breaker al"""
        with self._lock:
            return self._circuit_breakers.get(name)
    
    def list_services(self) -> List[str]:
        """Servisleri listele"""
        with self._lock:
            return list(self._services.keys())
    
    def add_observer(self, observer) -> None:
        """Observer ekle"""
        self._observers.append(weakref.ref(observer))
    
    def _notify_observers(self, event: str) -> None:
        """Observer'ları bilgilendir"""
        for observer_ref in self._observers[:]:
            observer = observer_ref()
            if observer is None:
                self._observers.remove(observer_ref)
            else:
                try:
                    observer.on_service_event(event)
                except Exception as e:
                    logger.error(f"Observer notification error: {e}")

# =============================================================================
# HEALTH MONITOR IMPLEMENTATIONS
# =============================================================================

class LocalModelHealthMonitor(IHealthMonitor):
    """Yerel model sağlık izleyici"""
    
    def __init__(self, model_manager):
        self.model_manager = model_manager
    
    async def check_health(self) -> Dict[str, Any]:
        try:
            # Model bilgilerini al
            model_info = self.model_manager.get_model_info()
            
            return {
                "status": ServiceStatus.HEALTHY.value,
                "service_type": "local_model",
                "models_loaded": model_info.get("models_loaded", {}),
                "memory_usage": model_info.get("memory_info", {}),
                "timestamp": time.time()
            }
        except Exception as e:
            return {
                "status": ServiceStatus.UNHEALTHY.value,
                "error": str(e),
                "timestamp": time.time()
            }
    
    async def get_metrics(self) -> Dict[str, Any]:
        try:
            model_info = self.model_manager.get_model_info()
            return {
                "memory_usage": model_info.get("memory_info", {}),
                "lazy_loading_stats": model_info.get("lazy_loading_stats", {}),
                "cache_info": model_info.get("cache_info", {})
            }
        except Exception as e:
            return {"error": str(e)}

class AIServiceHealthMonitor(IHealthMonitor):
    """AI mikroservis sağlık izleyici"""
    
    def __init__(self, ai_client):
        self.ai_client = ai_client
    
    async def check_health(self) -> Dict[str, Any]:
        try:
            health_data = await self.ai_client.get_service_health()
            return {
                "status": ServiceStatus.HEALTHY.value if health_data.get("status") == "healthy" else ServiceStatus.UNHEALTHY.value,
                "service_type": "ai_microservice",
                "ai_service_data": health_data,
                "timestamp": time.time()
            }
        except Exception as e:
            return {
                "status": ServiceStatus.OFFLINE.value,
                "error": str(e),
                "timestamp": time.time()
            }
    
    async def get_metrics(self) -> Dict[str, Any]:
        try:
            model_info = await self.ai_client.get_model_info()
            return {
                "models_available": model_info.get("models_loaded", {}),
                "memory_usage": model_info.get("memory_usage", {}),
                "lazy_loading_stats": model_info.get("lazy_loading_stats", {})
            }
        except Exception as e:
            return {"error": str(e)}

# =============================================================================
# UNIFIED MODEL MANAGER
# =============================================================================

class UnifiedModelManager(IModelManager):
    """
    Birleşik Model Manager
    =====================
    Hem yerel hem mikroservis modellerini yöneten unified interface
    """
    
    def __init__(self, config: MicroserviceConfig, service_registry: ServiceRegistry):
        self.config = config
        self.registry = service_registry
        self.mode = ServiceMode.LOCAL_ONLY
        self.status = ServiceStatus.UNKNOWN
        
        # Service references
        self._local_model_manager = None
        self._ai_service_client = None
        
        # Thread safety
        self._lock = threading.Lock()
        self._initialized = False
        
        # Performance tracking
        self._metrics = {
            "request_count": 0,
            "error_count": 0,
            "fallback_count": 0,
            "mode_switches": 0
        }
    
    async def initialize(self) -> None:
        """Birleşik manager'ı başlat"""
        if self._initialized:
            return
        
        with self._lock:
            if self._initialized:
                return
                
            try:
                logger.info("🔄 Birleşik Model Manager başlatılıyor...")
                self.status = ServiceStatus.INITIALIZING
                
                # Yerel model manager'ı yükle
                await self._initialize_local_model_manager()
                
                # AI servis varsa başlat
                if self.config.ai_service_enabled:
                    await self._initialize_ai_service()
                
                # Mode belirle
                self._determine_mode()
                
                # Health monitoring kur
                await self._setup_health_monitoring()
                
                self.status = ServiceStatus.HEALTHY
                self._initialized = True
                
                logger.info(f"✅ Birleşik Model Manager başlatıldı - Mode: {self.mode.value}")
                
            except Exception as e:
                logger.error(f"❌ Birleşik manager başlatma hatası: {e}")
                self.status = ServiceStatus.UNHEALTHY
                await self._fallback_to_local()
    
    async def _initialize_local_model_manager(self) -> None:
        """Yerel model manager'ı başlat"""
        try:
            from model_manager import model_manager
            self._local_model_manager = model_manager
            
            # Lazy loading için hazırla
            if hasattr(model_manager, 'initialize') and not getattr(model_manager, '_initialized', False):
                await model_manager.initialize()
            
            # Service registry'ye kaydet
            health_monitor = LocalModelHealthMonitor(model_manager)
            self.registry.register_service("local_model", model_manager, health_monitor)
            
            logger.info("✅ Yerel model manager başlatıldı")
            
        except Exception as e:
            logger.error(f"❌ Yerel model manager hatası: {e}")
            raise
    
    async def _initialize_ai_service(self) -> None:
        """AI mikroservisini başlat"""
        try:
            from services.ai_service.client import get_ai_client
            self._ai_service_client = await get_ai_client()
            
            # Health check
            health_data = await self._ai_service_client.get_service_health()
            if health_data.get("status") != "healthy":
                raise Exception("AI servis sağlıksız durumda")
            
            # Service registry'ye kaydet
            health_monitor = AIServiceHealthMonitor(self._ai_service_client)
            self.registry.register_service("ai_service", self._ai_service_client, health_monitor)
            
            logger.info("✅ AI mikroservis bağlantısı kuruldu")
            
        except Exception as e:
            logger.warning(f"⚠️ AI mikroservis başlatılamadı: {e}")
            self._ai_service_client = None
    
    def _determine_mode(self) -> None:
        """Çalışma modunu belirle"""
        if self._ai_service_client and self._local_model_manager:
            self.mode = ServiceMode.HYBRID
        elif self._ai_service_client:
            self.mode = ServiceMode.MICROSERVICE
        else:
            self.mode = ServiceMode.LOCAL_ONLY
        
        logger.info(f"🎯 Çalışma modu belirlendi: {self.mode.value}")
    
    async def _setup_health_monitoring(self) -> None:
        """Sağlık izleme sistemini kur"""
        # Periyodik health check başlat
        asyncio.create_task(self._periodic_health_check())
    
    async def _periodic_health_check(self) -> None:
        """Periyodik sağlık kontrolü"""
        while True:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                
                # AI servis sağlık kontrolü
                if self._ai_service_client:
                    circuit_breaker = self.registry.get_circuit_breaker("ai_service")
                    if circuit_breaker and not circuit_breaker.is_open():
                        try:
                            health_data = await self._ai_service_client.get_service_health()
                            if health_data.get("status") == "healthy":
                                circuit_breaker.record_success()
                            else:
                                circuit_breaker.record_failure()
                        except Exception:
                            circuit_breaker.record_failure()
                
            except Exception as e:
                logger.error(f"Health check error: {e}")
    
    async def _fallback_to_local(self) -> None:
        """Yerel moda geri dön"""
        logger.warning("🔄 Yerel moda geçiş yapılıyor...")
        self.mode = ServiceMode.FALLBACK
        self._metrics["mode_switches"] += 1
    
    def _should_use_ai_service(self) -> bool:
        """AI servis kullanılmalı mı?"""
        if not self._ai_service_client:
            return False
        
        circuit_breaker = self.registry.get_circuit_breaker("ai_service")
        if circuit_breaker and circuit_breaker.is_open():
            return False
        
        return self.mode in [ServiceMode.MICROSERVICE, ServiceMode.HYBRID]
    
    async def _execute_with_fallback(self, operation_name: str, ai_func, local_func, *args, **kwargs):
        """Circuit breaker ve fallback ile işlem çalıştır"""
        self._metrics["request_count"] += 1
        
        # AI servis dene
        if self._should_use_ai_service():
            circuit_breaker = self.registry.get_circuit_breaker("ai_service")
            try:
                result = await ai_func(*args, **kwargs)
                if circuit_breaker:
                    circuit_breaker.record_success()
                return result
                
            except Exception as e:
                logger.warning(f"⚠️ AI servis hatası ({operation_name}): {e}")
                if circuit_breaker:
                    circuit_breaker.record_failure()
                
                self._metrics["error_count"] += 1
        
        # Fallback - yerel manager kullan
        self._metrics["fallback_count"] += 1
        
        if self._local_model_manager:
            try:
                return local_func(*args, **kwargs)
            except Exception as e:
                logger.error(f"❌ Yerel fallback hatası ({operation_name}): {e}")
                raise
        else:
            raise Exception(f"Hem AI servis hem yerel manager kullanılamıyor: {operation_name}")
    
    # IModelManager implementation
    
    def generate_embedding(self, text: str, force_turkish: bool = None) -> List[float]:
        """Embedding oluştur"""
        return asyncio.run(self.generate_embedding_async(text, force_turkish))
    
    async def generate_embedding_async(self, text: str, force_turkish: bool = None) -> List[float]:
        """Embedding oluştur - async"""
        async def ai_func(text, force_turkish):
            return await self._ai_service_client.generate_embedding(text, force_turkish)
        
        def local_func(text, force_turkish):
            return self._local_model_manager.generate_embedding(text, force_turkish)
        
        return await self._execute_with_fallback("generate_embedding", ai_func, local_func, text, force_turkish)
    
    def generate_text_response(self, prompt: str, max_length: int = 80, turkish_context: bool = True) -> str:
        """Metin yanıtı oluştur"""
        return asyncio.run(self.generate_text_response_async(prompt, max_length, turkish_context))
    
    async def generate_text_response_async(self, prompt: str, max_length: int = 80, turkish_context: bool = True) -> str:
        """Metin yanıtı oluştur - async"""
        async def ai_func(prompt, max_length, turkish_context):
            return await self._ai_service_client.generate_text(prompt, max_length, turkish_context)
        
        def local_func(prompt, max_length, turkish_context):
            return self._local_model_manager.generate_text_response(prompt, max_length, turkish_context)
        
        return await self._execute_with_fallback("generate_text", ai_func, local_func, prompt, max_length, turkish_context)
    
    async def generate_huggingface_response(self, message: str, user_id: str = None) -> str:
        """Hugging Face yanıt oluştur"""
        async def ai_func(message, user_id):
            return await self._ai_service_client.generate_huggingface_response(message, user_id)
        
        def local_func(message, user_id):
            return asyncio.run(self._local_model_manager.generate_huggingface_response(message, user_id))
        
        return await self._execute_with_fallback("generate_huggingface", ai_func, local_func, message, user_id)
    
    def detect_language(self, text: str) -> str:
        """Dil tanıma"""
        return asyncio.run(self.detect_language_async(text))
    
    async def detect_language_async(self, text: str) -> str:
        """Dil tanıma - async"""
        async def ai_func(text):
            return await self._ai_service_client.detect_language(text)
        
        def local_func(text):
            return self._local_model_manager.detect_language(text)
        
        return await self._execute_with_fallback("detect_language", ai_func, local_func, text)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Model bilgilerini al"""
        return asyncio.run(self.get_model_info_async())
    
    async def get_model_info_async(self) -> Dict[str, Any]:
        """Model bilgilerini al - async"""
        try:
            info = {
                "unified_manager": {
                    "mode": self.mode.value,
                    "status": self.status.value,
                    "metrics": self._metrics,
                    "config": {
                        "ai_service_enabled": self.config.ai_service_enabled,
                        "ai_service_endpoint": f"{self.config.ai_service_host}:{self.config.ai_service_port}",
                        "fallback_strategy": self.config.fallback_strategy
                    }
                }
            }
            
            # AI servis bilgileri
            if self._should_use_ai_service():
                try:
                    ai_info = await self._ai_service_client.get_model_info()
                    info["ai_service"] = ai_info
                except Exception as e:
                    info["ai_service_error"] = str(e)
            
            # Yerel model bilgileri
            if self._local_model_manager:
                try:
                    local_info = self._local_model_manager.get_model_info()
                    info["local_model"] = local_info
                except Exception as e:
                    info["local_model_error"] = str(e)
            
            return info
            
        except Exception as e:
            return {"error": str(e), "status": "unhealthy"}
    
    def clear_caches(self) -> None:
        """Cache temizliği"""
        asyncio.run(self.clear_caches_async())
    
    async def clear_caches_async(self) -> None:
        """Cache temizliği - async"""
        tasks = []
        
        # AI servis cache temizliği
        if self._ai_service_client:
            tasks.append(self._ai_service_client.cleanup_models())
        
        # Yerel cache temizliği
        if self._local_model_manager:
            try:
                self._local_model_manager.clear_caches()
            except Exception as e:
                logger.error(f"Local cache clear error: {e}")
        
        # Async görevleri bekle
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        logger.info("✅ Tüm cache'ler temizlendi")
    
    def cleanup_resources(self) -> None:
        """Kaynakları temizle"""
        asyncio.run(self.cleanup_resources_async())
    
    async def cleanup_resources_async(self) -> None:
        """Kaynakları temizle - async"""
        try:
            # AI client kapat
            if self._ai_service_client:
                from services.ai_service.client import close_ai_client
                await close_ai_client()
                self._ai_service_client = None
            
            # Yerel manager temizle
            if self._local_model_manager:
                self._local_model_manager.cleanup_resources()
                self._local_model_manager = None
            
            self._initialized = False
            self.status = ServiceStatus.OFFLINE
            
            logger.info("✅ Birleşik manager kaynakları temizlendi")
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
    
    # Ek özellikler
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Sistem durumunu al"""
        service_statuses = {}
        
        # Servislerin sağlık durumunu kontrol et
        for service_name in self.registry.list_services():
            circuit_breaker = self.registry.get_circuit_breaker(service_name)
            service_statuses[service_name] = {
                "available": circuit_breaker is not None and not circuit_breaker.is_open(),
                "circuit_state": getattr(circuit_breaker, 'state', 'unknown') if circuit_breaker else 'no_circuit'
            }
        
        return {
            "unified_manager": {
                "mode": self.mode.value,
                "status": self.status.value,
                "initialized": self._initialized,
                "metrics": self._metrics
            },
            "services": service_statuses,
            "config": {
                "ai_service_enabled": self.config.ai_service_enabled,
                "fallback_strategy": self.config.fallback_strategy
            }
        }
    
    def force_mode_switch(self, target_mode: ServiceMode, reason: str = "Manual") -> bool:
        """Mode değiştir"""
        try:
            logger.info(f"🔄 Mode değişikliği: {self.mode.value} → {target_mode.value} ({reason})")
            
            if target_mode == ServiceMode.LOCAL_ONLY:
                self.mode = ServiceMode.LOCAL_ONLY
            elif target_mode == ServiceMode.MICROSERVICE and self._ai_service_client:
                self.mode = ServiceMode.MICROSERVICE
            elif target_mode == ServiceMode.HYBRID and self._ai_service_client and self._local_model_manager:
                self.mode = ServiceMode.HYBRID
            else:
                logger.error(f"❌ Geçersiz mode geçişi: {target_mode.value}")
                return False
            
            self._metrics["mode_switches"] += 1
            logger.info(f"✅ Mode değiştirildi: {self.mode.value}")
            return True
            
        except Exception as e:
            logger.error(f"Mode switch error: {e}")
            return False

# =============================================================================
# UNIFIED FACTORY
# =============================================================================

class UnifiedMicroserviceFactory:
    """Birleşik mikroservis factory"""
    
    @staticmethod
    def create_unified_architecture(config: MicroserviceConfig = None) -> UnifiedModelManager:
        """Birleşik mikroservis mimarisi oluştur"""
        if config is None:
            config = MicroserviceConfig.from_env()
        
        # Service registry oluştur
        service_registry = ServiceRegistry()
        
        # Unified manager oluştur
        unified_manager = UnifiedModelManager(config, service_registry)
        
        return unified_manager

# =============================================================================
# GLOBAL INSTANCE MANAGEMENT
# =============================================================================

# Thread-safe singleton pattern
_unified_manager: Optional[UnifiedModelManager] = None
_manager_lock = threading.Lock()

def get_unified_manager() -> UnifiedModelManager:
    """Global unified manager'ı al"""
    global _unified_manager
    
    if _unified_manager is None:
        with _manager_lock:
            if _unified_manager is None:
                config = MicroserviceConfig.from_env()
                _unified_manager = UnifiedMicroserviceFactory.create_unified_architecture(config)
    
    return _unified_manager

async def initialize_unified_architecture() -> UnifiedModelManager:
    """Birleşik mimarisiyi başlat"""
    manager = get_unified_manager()
    await manager.initialize()
    return manager

async def cleanup_unified_architecture() -> None:
    """Birleşik mimarisiyi temizle"""
    global _unified_manager
    
    if _unified_manager:
        await _unified_manager.cleanup_resources_async()
        _unified_manager = None

# =============================================================================
# DIAGNOSTICS AND UTILITIES
# =============================================================================

async def diagnose_microservice_architecture() -> Dict[str, Any]:
    """Mikroservis mimarisini teşhis et"""
    try:
        manager = get_unified_manager()
        
        if not manager._initialized:
            await manager.initialize()
        
        diagnosis = {
            "timestamp": time.time(),
            "architecture_type": "unified_microservice",
            "system_status": await manager.get_system_status(),
            "health_details": {},
            "recommendations": []
        }
        
        # Service health details
        for service_name in manager.registry.list_services():
            service = manager.registry.get_service(service_name)
            if hasattr(service, 'get_service_health'):
                try:
                    health = await service.get_service_health()
                    diagnosis["health_details"][service_name] = health
                except Exception as e:
                    diagnosis["health_details"][service_name] = {"error": str(e)}
        
        # Generate recommendations
        if manager.mode == ServiceMode.FALLBACK:
            diagnosis["recommendations"].extend([
                "Sistem fallback modunda çalışıyor",
                "AI servis bağlantısını kontrol edin",
                f"curl http://{manager.config.ai_service_host}:{manager.config.ai_service_port}/health",
                "python services/ai_service/main.py ile AI servisini başlatın"
            ])
        
        if manager._metrics["error_count"] > manager._metrics["request_count"] * 0.1:
            diagnosis["recommendations"].append("Yüksek hata oranı tespit edildi - logları inceleyin")
        
        return diagnosis
        
    except Exception as e:
        return {
            "error": str(e),
            "status": "diagnosis_failed",
            "timestamp": time.time()
        }

def circuit_breaker(threshold: int = 5, timeout: int = 30):
    """Circuit breaker decorator"""
    def decorator(func):
        breaker = CircuitBreaker(threshold, timeout)
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if breaker.is_open():
                raise Exception("Circuit breaker is open")
            
            try:
                result = await func(*args, **kwargs)
                breaker.record_success()
                return result
            except Exception as e:
                breaker.record_failure()
                raise
        
        return wrapper
    return decorator

# =============================================================================
# BACKWARD COMPATIBILITY
# =============================================================================

def get_model_manager() -> IModelManager:
    """Backward compatibility için model manager al"""
    return get_unified_manager()

async def setup_microservice_integration():
    """Backward compatibility için entegrasyon kur"""
    return await initialize_unified_architecture()

async def cleanup_microservice_integration():
    """Backward compatibility için temizlik"""
    await cleanup_unified_architecture()

# =============================================================================
# AUTO INITIALIZATION
# =============================================================================

def auto_initialize():
    """Otomatik başlatma (import zamanında)"""
    try:
        config = MicroserviceConfig.from_env()
        
        if config.ai_service_enabled:
            logger.info("🔄 Birleşik mikroservis mimarisi otomatik başlatılıyor...")
            
            # Schedule async initialization
            def schedule_init():
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(initialize_unified_architecture())
                    else:
                        asyncio.run(initialize_unified_architecture())
                except RuntimeError:
                    logger.info("Event loop hazır değil, başlatma daha sonra yapılacak")
            
            try:
                schedule_init()
            except Exception as e:
                logger.warning(f"Auto initialization failed: {e}")
        else:
            logger.info("ℹ️ AI Mikroservis devre dışı - birleşik mimari yerel modda")
            
    except Exception as e:
        logger.error(f"Auto initialization error: {e}")

# Initialize on import
auto_initialize()

logger.info("🏗️ Birleşik Mikroservis Mimarisi yüklendi")
