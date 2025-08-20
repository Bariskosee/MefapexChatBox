"""
🏗️ MEFAPEX Mikroservis Mimarisi - Kapsamlı Düzeltme
==================================================
Karmaşık bağımlılıkları ve tutarsız fallback mekanizmalarını düzeltir

SORUNLAR:
1. AI mikroservisi ile ana uygulama arasında karmaşık bağımlılıklar
2. Fallback mekanizmaları tutarsız çalışıyor
3. Race condition'lar ve circular dependency'ler
4. Hata handling eksiklikleri

ÇÖZÜMLER:
1. Service Registry Pattern ile merkezi servis yönetimi
2. Circuit Breaker Pattern ile güvenilir fallback
3. Dependency Injection ile loose coupling
4. Graceful degradation ile robust error handling
"""

import logging
import asyncio
import threading
import time
import enum
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
import weakref

logger = logging.getLogger(__name__)

# =============================================================================
# 1. SERVICE REGISTRY PATTERN - Merkezi Servis Yönetimi
# =============================================================================

class ServiceState(enum.Enum):
    """Servis durumları"""
    UNKNOWN = "unknown"
    STARTING = "starting"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    STOPPED = "stopped"

@dataclass
class ServiceInfo:
    """Servis bilgileri"""
    name: str
    state: ServiceState = ServiceState.UNKNOWN
    endpoint: Optional[str] = None
    last_health_check: float = 0.0
    consecutive_failures: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_available(self) -> bool:
        """Servis kullanılabilir mi?"""
        return self.state in [ServiceState.HEALTHY, ServiceState.DEGRADED]

class ServiceRegistry:
    """
    Merkezi Servis Kayıt ve Yönetim Sistemi
    =======================================
    Tüm servislerin durumunu merkezi olarak yönetir
    """
    
    def __init__(self):
        self._services: Dict[str, ServiceInfo] = {}
        self._lock = threading.RLock()
        self._health_check_interval = 30  # 30 saniye
        self._health_check_task: Optional[asyncio.Task] = None
        self._observers: List[Callable[[str, ServiceState], None]] = []
        
    def register_service(self, name: str, endpoint: str = None, metadata: Dict[str, Any] = None) -> ServiceInfo:
        """Servis kaydet"""
        with self._lock:
            service_info = ServiceInfo(
                name=name,
                endpoint=endpoint,
                metadata=metadata or {}
            )
            self._services[name] = service_info
            logger.info(f"📝 Servis kayıtlı: {name}")
            return service_info
    
    def update_service_state(self, name: str, state: ServiceState, metadata: Dict[str, Any] = None):
        """Servis durumunu güncelle"""
        with self._lock:
            if name in self._services:
                old_state = self._services[name].state
                self._services[name].state = state
                self._services[name].last_health_check = time.time()
                
                if metadata:
                    self._services[name].metadata.update(metadata)
                
                # State değişikliğini bildir
                if old_state != state:
                    logger.info(f"🔄 Servis durumu değişti: {name} {old_state.value} → {state.value}")
                    self._notify_observers(name, state)
                    
                # Hata sayacını yönet
                if state == ServiceState.HEALTHY:
                    self._services[name].consecutive_failures = 0
                elif state == ServiceState.UNHEALTHY:
                    self._services[name].consecutive_failures += 1
    
    def get_service(self, name: str) -> Optional[ServiceInfo]:
        """Servis bilgilerini al"""
        with self._lock:
            return self._services.get(name)
    
    def is_service_available(self, name: str) -> bool:
        """Servis kullanılabilir mi?"""
        service = self.get_service(name)
        return service.is_available() if service else False
    
    def list_services(self) -> Dict[str, ServiceInfo]:
        """Tüm servisleri listele"""
        with self._lock:
            return self._services.copy()
    
    def add_observer(self, observer: Callable[[str, ServiceState], None]):
        """Durum değişiklik observer'ı ekle"""
        self._observers.append(observer)
    
    def _notify_observers(self, service_name: str, new_state: ServiceState):
        """Observer'ları bilgilendir"""
        for observer in self._observers:
            try:
                observer(service_name, new_state)
            except Exception as e:
                logger.error(f"Observer notification error: {e}")
    
    async def start_health_monitoring(self):
        """Sağlık kontrolü görevini başlat"""
        if self._health_check_task is None:
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            logger.info("🏥 Sağlık kontrolü görevı başlatıldı")
    
    async def stop_health_monitoring(self):
        """Sağlık kontrolü görevini durdur"""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None
            logger.info("🏥 Sağlık kontrolü görevı durduruldu")
    
    async def _health_check_loop(self):
        """Sürekli sağlık kontrolü döngüsü"""
        while True:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self._health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(5)  # Kısa bekleme sonra devam
    
    async def _perform_health_checks(self):
        """Tüm servislerin sağlık kontrolü"""
        with self._lock:
            services_to_check = list(self._services.items())
        
        for name, service_info in services_to_check:
            if service_info.endpoint:
                await self._check_service_health(name, service_info)
    
    async def _check_service_health(self, name: str, service_info: ServiceInfo):
        """Tek servis sağlık kontrolü"""
        try:
            # HTTP health check implementasyonu
            import aiohttp
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                health_url = f"{service_info.endpoint}/health"
                async with session.get(health_url) as response:
                    if response.status == 200:
                        health_data = await response.json()
                        if health_data.get("status") == "healthy":
                            self.update_service_state(name, ServiceState.HEALTHY)
                        else:
                            self.update_service_state(name, ServiceState.DEGRADED)
                    else:
                        self.update_service_state(name, ServiceState.UNHEALTHY)
                        
        except Exception as e:
            logger.warning(f"Health check failed for {name}: {e}")
            self.update_service_state(name, ServiceState.UNHEALTHY)

# Global service registry
_service_registry = ServiceRegistry()

def get_service_registry() -> ServiceRegistry:
    """Global service registry'yi al"""
    return _service_registry

# =============================================================================
# 2. CIRCUIT BREAKER PATTERN - Güvenilir Fallback
# =============================================================================

class CircuitState(enum.Enum):
    """Circuit breaker durumları"""
    CLOSED = "closed"      # Normal çalışma
    OPEN = "open"          # Hata nedeniyle açık
    HALF_OPEN = "half_open"  # Test aşaması

@dataclass
class CircuitBreakerConfig:
    """Circuit breaker yapılandırması"""
    failure_threshold: int = 5          # Hata eşiği
    timeout_duration: float = 60.0      # Açık kalma süresi (saniye)
    success_threshold: int = 3          # Half-open'da başarı eşiği
    call_timeout: float = 10.0          # İşlem timeout'u

class CircuitBreakerError(Exception):
    """Circuit breaker hatası"""
    pass

class CircuitBreaker:
    """
    Circuit Breaker Pattern Implementasyonu
    =====================================
    Servisleri hata durumlarında korur ve fallback sağlar
    """
    
    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        
        # State management
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0.0
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Statistics
        self._total_calls = 0
        self._successful_calls = 0
        self._failed_calls = 0
        
        logger.info(f"🔌 Circuit breaker created: {name}")
    
    @property
    def state(self) -> CircuitState:
        """Mevcut durumu al"""
        with self._lock:
            return self._state
    
    @property
    def is_closed(self) -> bool:
        """Kapalı durumda mı?"""
        return self.state == CircuitState.CLOSED
    
    @property
    def is_open(self) -> bool:
        """Açık durumda mı?"""
        return self.state == CircuitState.OPEN
    
    @property
    def is_half_open(self) -> bool:
        """Yarı açık durumda mı?"""
        return self.state == CircuitState.HALF_OPEN
    
    def can_execute(self) -> bool:
        """İşlem yapılabilir mi?"""
        with self._lock:
            if self._state == CircuitState.CLOSED:
                return True
            
            elif self._state == CircuitState.OPEN:
                # Timeout süresini kontrol et
                if time.time() - self._last_failure_time >= self.config.timeout_duration:
                    self._state = CircuitState.HALF_OPEN
                    self._success_count = 0
                    logger.info(f"🔄 Circuit breaker {self.name} HALF_OPEN durumuna geçti")
                    return True
                return False
            
            elif self._state == CircuitState.HALF_OPEN:
                return True
            
            return False
    
    async def call(self, func: Callable, *args, **kwargs):
        """Circuit breaker ile korumalı işlem çağrısı"""
        if not self.can_execute():
            raise CircuitBreakerError(f"Circuit breaker {self.name} açık durumda")
        
        with self._lock:
            self._total_calls += 1
        
        try:
            # Timeout ile işlemi çalıştır
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.config.call_timeout
            )
            
            self._record_success()
            return result
            
        except Exception as e:
            self._record_failure()
            raise e
    
    def call_sync(self, func: Callable, *args, **kwargs):
        """Synchronous circuit breaker çağrısı"""
        if not self.can_execute():
            raise CircuitBreakerError(f"Circuit breaker {self.name} açık durumda")
        
        with self._lock:
            self._total_calls += 1
        
        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
            
        except Exception as e:
            self._record_failure()
            raise e
    
    def _record_success(self):
        """Başarılı işlemi kaydet"""
        with self._lock:
            self._successful_calls += 1
            
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.config.success_threshold:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    logger.info(f"✅ Circuit breaker {self.name} CLOSED durumuna geçti")
            
            elif self._state == CircuitState.CLOSED:
                self._failure_count = 0  # Reset failure count on success
    
    def _record_failure(self):
        """Başarısız işlemi kaydet"""
        with self._lock:
            self._failed_calls += 1
            self._failure_count += 1
            self._last_failure_time = time.time()
            
            if self._state in [CircuitState.CLOSED, CircuitState.HALF_OPEN]:
                if self._failure_count >= self.config.failure_threshold:
                    self._state = CircuitState.OPEN
                    logger.warning(f"⚠️ Circuit breaker {self.name} OPEN durumuna geçti")
    
    def get_stats(self) -> Dict[str, Any]:
        """İstatistikleri al"""
        with self._lock:
            return {
                "name": self.name,
                "state": self._state.value,
                "total_calls": self._total_calls,
                "successful_calls": self._successful_calls,
                "failed_calls": self._failed_calls,
                "failure_count": self._failure_count,
                "success_rate": self._successful_calls / max(self._total_calls, 1),
                "last_failure_time": self._last_failure_time
            }
    
    def reset(self):
        """Circuit breaker'ı sıfırla"""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._last_failure_time = 0.0
            logger.info(f"🔄 Circuit breaker {self.name} sıfırlandı")

# =============================================================================
# 3. IMPROVED AI SERVICE ADAPTER - Loose Coupling
# =============================================================================

class IServiceProvider(ABC):
    """Servis sağlayıcı arayüzü"""
    
    @abstractmethod
    async def generate_embedding(self, text: str, **kwargs) -> List[float]:
        pass
    
    @abstractmethod
    async def generate_text(self, prompt: str, **kwargs) -> str:
        pass
    
    @abstractmethod
    async def detect_language(self, text: str) -> str:
        pass
    
    @abstractmethod
    async def get_model_info(self) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    async def cleanup(self):
        pass

class AIServiceProvider(IServiceProvider):
    """AI mikroservis sağlayıcısı"""
    
    def __init__(self, service_name: str = "ai_service"):
        self.service_name = service_name
        self._client = None
        
    async def _get_client(self):
        """AI istemcisini al"""
        if self._client is None:
            from services.ai_service.client import get_ai_client
            self._client = await get_ai_client()
        return self._client
    
    async def generate_embedding(self, text: str, **kwargs) -> List[float]:
        client = await self._get_client()
        return await client.generate_embedding(text, **kwargs)
    
    async def generate_text(self, prompt: str, **kwargs) -> str:
        client = await self._get_client()
        return await client.generate_text(prompt, **kwargs)
    
    async def detect_language(self, text: str) -> str:
        client = await self._get_client()
        return await client.detect_language(text)
    
    async def get_model_info(self) -> Dict[str, Any]:
        client = await self._get_client()
        return await client.get_model_info()
    
    async def cleanup(self):
        if self._client:
            await self._client.close()

class LocalModelProvider(IServiceProvider):
    """Yerel model sağlayıcısı (fallback)"""
    
    def __init__(self):
        self._model_manager = None
    
    def _get_model_manager(self):
        """Orijinal model manager'ı al"""
        if self._model_manager is None:
            from model_manager import ModelManager
            self._model_manager = ModelManager()
        return self._model_manager
    
    async def generate_embedding(self, text: str, **kwargs) -> List[float]:
        manager = self._get_model_manager()
        return await manager.generate_embedding_async(text, **kwargs)
    
    async def generate_text(self, prompt: str, **kwargs) -> str:
        manager = self._get_model_manager()
        return await manager.generate_text_async(prompt, **kwargs)
    
    async def detect_language(self, text: str) -> str:
        manager = self._get_model_manager()
        return manager.detect_language(text)
    
    async def get_model_info(self) -> Dict[str, Any]:
        manager = self._get_model_manager()
        return manager.get_model_info()
    
    async def cleanup(self):
        manager = self._get_model_manager()
        if hasattr(manager, 'cleanup'):
            await manager.cleanup()

class FallbackProvider(IServiceProvider):
    """Acil durum fallback sağlayıcısı"""
    
    async def generate_embedding(self, text: str, **kwargs) -> List[float]:
        from services.ai_service.client import FallbackAIManager
        return FallbackAIManager.generate_embedding_fallback(text)
    
    async def generate_text(self, prompt: str, **kwargs) -> str:
        from services.ai_service.client import FallbackAIManager
        return FallbackAIManager.generate_text_fallback(prompt)
    
    async def detect_language(self, text: str) -> str:
        from services.ai_service.client import FallbackAIManager
        return FallbackAIManager.detect_language_fallback(text)
    
    async def get_model_info(self) -> Dict[str, Any]:
        return {
            "provider": "fallback",
            "status": "basic_responses_only",
            "message": "AI servisleri kullanılamıyor, temel yanıtlar veriliyor"
        }
    
    async def cleanup(self):
        pass

# =============================================================================
# 4. RESILIENT SERVICE MANAGER - Ana Koordinatör
# =============================================================================

class ResilientServiceManager:
    """
    Dayanıklı Servis Yöneticisi
    ==========================
    Tüm servisleri koordine eder ve graceful degradation sağlar
    """
    
    def __init__(self):
        self.service_registry = get_service_registry()
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.service_providers: Dict[str, IServiceProvider] = {}
        
        # Provider hierarchy (fallback chain)
        self.provider_chain = [
            "ai_service",      # Primary: AI mikroservisi
            "local_model",     # Secondary: Yerel model
            "fallback"         # Emergency: Basit yanıtlar
        ]
        
        # Initialize providers
        self._init_providers()
        
        # Setup service monitoring
        self.service_registry.add_observer(self._on_service_state_change)
        
        logger.info("🏗️ ResilientServiceManager initialized")
    
    def _init_providers(self):
        """Servis sağlayıcılarını başlat"""
        # AI Service Provider
        self.service_providers["ai_service"] = AIServiceProvider()
        self.circuit_breakers["ai_service"] = CircuitBreaker(
            "ai_service",
            CircuitBreakerConfig(failure_threshold=3, timeout_duration=30.0)
        )
        
        # Local Model Provider
        self.service_providers["local_model"] = LocalModelProvider()
        self.circuit_breakers["local_model"] = CircuitBreaker(
            "local_model",
            CircuitBreakerConfig(failure_threshold=5, timeout_duration=60.0)
        )
        
        # Fallback Provider
        self.service_providers["fallback"] = FallbackProvider()
        # No circuit breaker for fallback - always available
        
        # Register services
        self.service_registry.register_service("ai_service", "http://127.0.0.1:8001")
        self.service_registry.register_service("local_model")
        self.service_registry.register_service("fallback")
    
    def _on_service_state_change(self, service_name: str, new_state: ServiceState):
        """Servis durumu değişikliğini işle"""
        logger.info(f"📊 Service state change: {service_name} → {new_state.value}")
        
        # Circuit breaker durumunu güncelle
        if service_name in self.circuit_breakers:
            if new_state == ServiceState.HEALTHY:
                self.circuit_breakers[service_name].reset()
            elif new_state == ServiceState.UNHEALTHY:
                # Circuit breaker already handles failures
                pass
    
    async def _try_provider(self, provider_name: str, method_name: str, *args, **kwargs):
        """Belirli bir provider ile işlem dene"""
        if provider_name not in self.service_providers:
            raise ValueError(f"Unknown provider: {provider_name}")
        
        provider = self.service_providers[provider_name]
        method = getattr(provider, method_name)
        
        # Circuit breaker kontrolü (fallback hariç)
        if provider_name in self.circuit_breakers:
            circuit_breaker = self.circuit_breakers[provider_name]
            return await circuit_breaker.call(method, *args, **kwargs)
        else:
            # Fallback provider - always try
            return await method(*args, **kwargs)
    
    async def _execute_with_fallback_chain(self, method_name: str, *args, **kwargs):
        """Fallback chain ile işlem çalıştır"""
        last_error = None
        
        for provider_name in self.provider_chain:
            try:
                logger.debug(f"🔄 Trying {provider_name} for {method_name}")
                result = await self._try_provider(provider_name, method_name, *args, **kwargs)
                
                if provider_name != "ai_service":
                    logger.warning(f"⚠️ Using fallback provider: {provider_name}")
                
                return result
                
            except Exception as e:
                last_error = e
                logger.warning(f"❌ Provider {provider_name} failed for {method_name}: {e}")
                continue
        
        # Tüm provider'lar başarısız
        raise RuntimeError(f"All providers failed for {method_name}. Last error: {last_error}")
    
    # Public API Methods
    
    async def generate_embedding(self, text: str, **kwargs) -> List[float]:
        """Embedding üret (fallback destekli)"""
        return await self._execute_with_fallback_chain("generate_embedding", text, **kwargs)
    
    async def generate_text(self, prompt: str, **kwargs) -> str:
        """Metin üret (fallback destekli)"""
        return await self._execute_with_fallback_chain("generate_text", prompt, **kwargs)
    
    async def detect_language(self, text: str) -> str:
        """Dil tanı (fallback destekli)"""
        return await self._execute_with_fallback_chain("detect_language", text)
    
    async def get_model_info(self) -> Dict[str, Any]:
        """Model bilgilerini al (fallback destekli)"""
        return await self._execute_with_fallback_chain("get_model_info")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Sistem durumu raporu"""
        status = {
            "timestamp": time.time(),
            "services": {},
            "circuit_breakers": {},
            "primary_provider": None,
            "degradation_level": 0
        }
        
        # Service states
        for name, service_info in self.service_registry.list_services().items():
            status["services"][name] = {
                "state": service_info.state.value,
                "available": service_info.is_available(),
                "last_check": service_info.last_health_check,
                "failures": service_info.consecutive_failures
            }
        
        # Circuit breaker states
        for name, cb in self.circuit_breakers.items():
            status["circuit_breakers"][name] = cb.get_stats()
        
        # Determine primary provider
        for provider_name in self.provider_chain:
            if provider_name in self.circuit_breakers:
                if self.circuit_breakers[provider_name].is_closed:
                    status["primary_provider"] = provider_name
                    break
            else:
                # Fallback is always available
                if status["primary_provider"] is None:
                    status["primary_provider"] = provider_name
        
        # Calculate degradation level
        if status["primary_provider"] == "ai_service":
            status["degradation_level"] = 0  # Full functionality
        elif status["primary_provider"] == "local_model":
            status["degradation_level"] = 1  # Moderate degradation
        else:
            status["degradation_level"] = 2  # High degradation
        
        return status
    
    async def start(self):
        """Servis manager'ı başlat"""
        await self.service_registry.start_health_monitoring()
        logger.info("🚀 ResilientServiceManager started")
    
    async def stop(self):
        """Servis manager'ı durdur"""
        await self.service_registry.stop_health_monitoring()
        
        # Cleanup all providers
        for provider in self.service_providers.values():
            try:
                await provider.cleanup()
            except Exception as e:
                logger.error(f"Provider cleanup error: {e}")
        
        logger.info("🛑 ResilientServiceManager stopped")

# =============================================================================
# 5. IMPROVED MODEL MANAGER ADAPTER
# =============================================================================

class ImprovedModelManagerAdapter:
    """
    Geliştirilmiş Model Manager Adaptörü
    ===================================
    Mevcut API'yi koruyarak yeni resilient architecture kullanır
    """
    
    def __init__(self):
        self._service_manager = ResilientServiceManager()
        self._initialized = False
        
        logger.info("🔄 ImprovedModelManagerAdapter created")
    
    async def _ensure_initialized(self):
        """Adapter'ın başlatıldığından emin ol"""
        if not self._initialized:
            await self._service_manager.start()
            self._initialized = True
    
    # Sync wrappers for backward compatibility
    
    def generate_embedding(self, text: str, force_turkish: bool = None) -> List[float]:
        """Embedding üret - sync wrapper"""
        try:
            # Try to get current running loop
            loop = asyncio.get_running_loop()
            # If we're already in an async context, can't use asyncio.run
            # Return a simple fallback or defer to fallback provider
            from services.ai_service.client import FallbackAIManager
            return FallbackAIManager.generate_embedding_fallback(text)
        except RuntimeError:
            # No running loop, safe to use asyncio.run
            return asyncio.run(self.generate_embedding_async(text, force_turkish=force_turkish))
    
    async def generate_embedding_async(self, text: str, force_turkish: bool = None) -> List[float]:
        """Embedding üret - async"""
        await self._ensure_initialized()
        return await self._service_manager.generate_embedding(text, force_turkish=force_turkish)
    
    def generate_text(self, prompt: str, max_length: int = 80, turkish_context: bool = True) -> str:
        """Metin üret - sync wrapper"""
        try:
            loop = asyncio.get_running_loop()
            from services.ai_service.client import FallbackAIManager
            return FallbackAIManager.generate_text_fallback(prompt)
        except RuntimeError:
            return asyncio.run(self.generate_text_async(prompt, max_length, turkish_context))
    
    async def generate_text_async(self, prompt: str, max_length: int = 80, turkish_context: bool = True) -> str:
        """Metin üret - async"""
        await self._ensure_initialized()
        return await self._service_manager.generate_text(prompt, max_length=max_length, turkish_context=turkish_context)
    
    async def generate_huggingface_response(self, message: str, user_id: str = None) -> str:
        """HuggingFace yanıt üret"""
        await self._ensure_initialized()
        return await self._service_manager.generate_text(message, user_id=user_id)
    
    def detect_language(self, text: str) -> str:
        """Dil tanı - sync wrapper"""
        try:
            loop = asyncio.get_running_loop()
            from services.ai_service.client import FallbackAIManager
            return FallbackAIManager.detect_language_fallback(text)
        except RuntimeError:
            return asyncio.run(self.detect_language_async(text))
    
    async def detect_language_async(self, text: str) -> str:
        """Dil tanı - async"""
        await self._ensure_initialized()
        return await self._service_manager.detect_language(text)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Model bilgilerini al - sync wrapper"""
        try:
            loop = asyncio.get_running_loop()
            return {
                "provider": "sync_fallback",
                "status": "running_in_async_context",
                "message": "Sync call in async context - using fallback info"
            }
        except RuntimeError:
            return asyncio.run(self.get_model_info_async())
    
    async def get_model_info_async(self) -> Dict[str, Any]:
        """Model bilgilerini al - async"""
        await self._ensure_initialized()
        
        # Combine model info with system status
        model_info = await self._service_manager.get_model_info()
        system_status = self._service_manager.get_system_status()
        
        return {
            **model_info,
            "system_status": system_status,
            "architecture": "resilient_microservice",
            "fallback_enabled": True
        }
    
    def get_system_status(self) -> Dict[str, Any]:
        """Sistem durumu al"""
        if not self._initialized:
            return {"status": "not_initialized"}
        return self._service_manager.get_system_status()
    
    async def cleanup(self):
        """Temizlik"""
        if self._initialized:
            await self._service_manager.stop()
            self._initialized = False

# =============================================================================
# 6. INTEGRATION FUNCTIONS
# =============================================================================

def create_resilient_model_manager() -> ImprovedModelManagerAdapter:
    """Dayanıklı model manager oluştur"""
    return ImprovedModelManagerAdapter()

async def setup_resilient_microservice_architecture():
    """Dayanıklı mikroservis mimarisini kur"""
    try:
        logger.info("🏗️ Setting up resilient microservice architecture...")
        
        # Create improved adapter
        adapter = create_resilient_model_manager()
        
        # Replace global model manager
        import model_manager as mm_module
        mm_module.model_manager = adapter
        
        # Start the system
        await adapter._ensure_initialized()
        
        logger.info("✅ Resilient microservice architecture setup complete")
        return adapter
        
    except Exception as e:
        logger.error(f"❌ Resilient architecture setup failed: {e}")
        raise

async def test_resilient_architecture():
    """Dayanıklı mimariyi test et"""
    logger.info("🧪 Testing resilient architecture...")
    
    adapter = create_resilient_model_manager()
    
    try:
        # Test different operations
        test_cases = [
            ("generate_embedding", ["test text"]),
            ("generate_text", ["test prompt"]),
            ("detect_language", ["test language detection"]),
            ("get_model_info", [])
        ]
        
        for method_name, args in test_cases:
            try:
                method = getattr(adapter, method_name)
                result = await method(*args) if asyncio.iscoroutinefunction(method) else method(*args)
                logger.info(f"✅ {method_name}: Success")
            except Exception as e:
                logger.warning(f"⚠️ {method_name}: {e}")
        
        # System status
        status = adapter.get_system_status()
        logger.info(f"📊 System Status: Primary provider: {status.get('primary_provider')}, Degradation: {status.get('degradation_level')}")
        
    finally:
        await adapter.cleanup()
    
    logger.info("🧪 Resilient architecture test complete")

if __name__ == "__main__":
    # Test the resilient architecture
    asyncio.run(test_resilient_architecture())
