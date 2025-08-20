"""
🤖 AI Mikroservisi İstemcisi
==========================
Ana uygulama ile AI mikroservisi arasındaki iletişimi sağlar
"""
import logging
import asyncio
import aiohttp
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import time

logger = logging.getLogger(__name__)

@dataclass
class AIServiceConfig:
    """AI servis yapılandırması"""
    host: str = "127.0.0.1"
    port: int = 8001
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: float = 1.0

class AIServiceError(Exception):
    """AI servis hatası"""
    pass

class AIServiceUnavailableError(AIServiceError):
    """AI servis erişilemez"""
    pass

class AIServiceClient:
    """
    AI Mikroservisi İstemcisi
    =========================
    Ana uygulama ile AI mikroservisi arasındaki tüm iletişimi yönetir
    """
    
    def __init__(self, config: AIServiceConfig = None):
        self.config = config or AIServiceConfig()
        self.base_url = f"http://{self.config.host}:{self.config.port}"
        self.session: Optional[aiohttp.ClientSession] = None
        self._service_available = False
        self._last_health_check = 0
        self._health_check_interval = 60  # 1 dakika
        
    async def __aenter__(self):
        """Async context manager giriş"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager çıkış"""
        await self.close()
    
    async def start(self):
        """İstemciyi başlat"""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)
        
        # Servis sağlık kontrolü
        await self._check_service_health()
    
    async def close(self):
        """İstemciyi kapat"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def _check_service_health(self) -> bool:
        """AI servis sağlık kontrolü"""
        try:
            current_time = time.time()
            
            # Cache'li sağlık kontrolü
            if (current_time - self._last_health_check) < self._health_check_interval:
                return self._service_available
            
            if not self.session:
                await self.start()
            
            async with self.session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    health_data = await response.json()
                    self._service_available = health_data.get("status") == "healthy"
                    self._last_health_check = current_time
                    
                    if self._service_available:
                        logger.debug("✅ AI servis sağlıklı")
                    else:
                        logger.warning("⚠️ AI servis sağlıksız durumda")
                    
                    return self._service_available
                else:
                    self._service_available = False
                    logger.warning(f"⚠️ AI servis sağlık kontrolü başarısız: {response.status}")
                    return False
                    
        except Exception as e:
            self._service_available = False
            logger.error(f"❌ AI servis sağlık kontrolü hatası: {e}")
            return False
    
    async def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """HTTP isteği yap"""
        if not await self._check_service_health():
            raise AIServiceUnavailableError("AI servis erişilemez durumda")
        
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(self.config.retry_attempts):
            try:
                if not self.session:
                    await self.start()
                
                if method.upper() == "GET":
                    async with self.session.get(url) as response:
                        return await self._handle_response(response)
                
                elif method.upper() == "POST":
                    headers = {"Content-Type": "application/json"}
                    json_data = json.dumps(data) if data else None
                    
                    async with self.session.post(url, data=json_data, headers=headers) as response:
                        return await self._handle_response(response)
                
                else:
                    raise AIServiceError(f"Desteklenmeyen HTTP metod: {method}")
                    
            except aiohttp.ClientError as e:
                logger.warning(f"⚠️ AI servis istek hatası (deneme {attempt + 1}): {e}")
                
                if attempt == self.config.retry_attempts - 1:
                    raise AIServiceUnavailableError(f"AI servis {self.config.retry_attempts} denemeden sonra erişilemez")
                
                await asyncio.sleep(self.config.retry_delay * (attempt + 1))
        
        raise AIServiceError("Beklenmeyen hata")
    
    async def _handle_response(self, response: aiohttp.ClientResponse) -> Dict:
        """HTTP yanıtını işle"""
        try:
            response_data = await response.json()
            
            if response.status == 200:
                return response_data
            
            elif response.status == 400:
                error_detail = response_data.get("detail", "Geçersiz istek")
                raise AIServiceError(f"Geçersiz istek: {error_detail}")
            
            elif response.status == 500:
                error_detail = response_data.get("detail", "Sunucu hatası")
                raise AIServiceError(f"AI servis hatası: {error_detail}")
            
            else:
                raise AIServiceError(f"Beklenmeyen yanıt kodu: {response.status}")
                
        except json.JSONDecodeError:
            raise AIServiceError("Geçersiz JSON yanıtı")
    
    # AI İşlemleri
    
    async def generate_embedding(self, text: str, force_turkish: bool = None) -> List[float]:
        """Metin için embedding oluştur"""
        try:
            data = {
                "text": text,
                "force_turkish": force_turkish
            }
            
            response = await self._make_request("POST", "/embedding", data)
            return response["embedding"]
            
        except Exception as e:
            logger.error(f"Embedding oluşturma hatası: {e}")
            raise AIServiceError(f"Embedding generation failed: {e}")
    
    async def generate_text(self, prompt: str, max_length: int = 80, turkish_context: bool = True) -> str:
        """Metin üret"""
        try:
            data = {
                "prompt": prompt,
                "max_length": max_length,
                "turkish_context": turkish_context
            }
            
            response = await self._make_request("POST", "/generate", data)
            return response["generated_text"]
            
        except Exception as e:
            logger.error(f"Metin üretme hatası: {e}")
            raise AIServiceError(f"Text generation failed: {e}")
    
    async def generate_huggingface_response(self, message: str, user_id: str = None) -> str:
        """Gelişmiş Hugging Face yanıt üret"""
        try:
            data = {
                "prompt": message,
                "max_length": 100,
                "turkish_context": True
            }
            
            response = await self._make_request("POST", "/generate/huggingface", data)
            return response["response"]
            
        except Exception as e:
            logger.error(f"Hugging Face yanıt hatası: {e}")
            raise AIServiceError(f"Hugging Face response failed: {e}")
    
    async def detect_language(self, text: str) -> str:
        """Dil tanıma"""
        try:
            data = {"text": text}
            response = await self._make_request("POST", "/language/detect", data)
            return response["language"]
            
        except Exception as e:
            logger.error(f"Dil tanıma hatası: {e}")
            raise AIServiceError(f"Language detection failed: {e}")
    
    async def get_model_info(self) -> Dict[str, Any]:
        """Model bilgilerini al"""
        try:
            return await self._make_request("GET", "/models/info")
            
        except Exception as e:
            logger.error(f"Model bilgisi alma hatası: {e}")
            raise AIServiceError(f"Failed to get model info: {e}")
    
    async def warmup_models(self) -> bool:
        """Modelleri ısıt"""
        try:
            response = await self._make_request("POST", "/models/warmup")
            return "success" in response.get("message", "").lower()
            
        except Exception as e:
            logger.error(f"Model ısıtma hatası: {e}")
            return False
    
    async def cleanup_models(self) -> bool:
        """Model temizliği"""
        try:
            response = await self._make_request("POST", "/models/cleanup")
            return "success" in response.get("message", "").lower()
            
        except Exception as e:
            logger.error(f"Model temizlik hatası: {e}")
            return False
    
    async def get_service_health(self) -> Dict[str, Any]:
        """Servis sağlık bilgilerini al"""
        try:
            return await self._make_request("GET", "/health")
            
        except Exception as e:
            logger.error(f"Sağlık kontrolü hatası: {e}")
            return {"status": "unhealthy", "error": str(e)}
    
    async def get_lazy_loading_stats(self) -> Dict[str, Any]:
        """Lazy loading istatistiklerini al"""
        try:
            response = await self._make_request("GET", "/stats/lazy-loading")
            return response["lazy_loading_stats"]
            
        except Exception as e:
            logger.error(f"Lazy loading istatistik hatası: {e}")
            return {}

# Global AI istemci instance
_ai_client = None

async def get_ai_client() -> AIServiceClient:
    """Global AI istemcisini al"""
    global _ai_client
    
    if _ai_client is None:
        _ai_client = AIServiceClient()
        await _ai_client.start()
    
    return _ai_client

async def close_ai_client():
    """Global AI istemcisini kapat"""
    global _ai_client
    
    if _ai_client:
        await _ai_client.close()
        _ai_client = None

# Fallback fonksiyonları (AI servis erişilemezse)

class FallbackAIManager:
    """
    AI servis erişilemezse kullanılacak fallback manager
    """
    
    @staticmethod
    def generate_embedding_fallback(text: str) -> List[float]:
        """Basit embedding fallback"""
        # Basit hash-based embedding (gerçek projede sentence transformers kullan)
        import hashlib
        hash_obj = hashlib.md5(text.encode())
        hash_hex = hash_obj.hexdigest()
        
        # 384 boyutlu basit vektör oluştur
        embedding = []
        for i in range(0, min(len(hash_hex), 96), 2):
            val = int(hash_hex[i:i+2], 16) / 255.0
            embedding.extend([val] * 4)  # Her hash byte'ı için 4 float değer
        
        # 384'e tamamla
        while len(embedding) < 384:
            embedding.append(0.0)
        
        return embedding[:384]
    
    @staticmethod
    def generate_text_fallback(prompt: str) -> str:
        """Basit metin üretme fallback"""
        # Basit şablon yanıtlar
        turkish_responses = [
            f"'{prompt}' konusunda size yardımcı olmaya çalışıyorum. AI servisimiz şu anda bakımda.",
            f"Sorunuz '{prompt}' ile ilgili olarak, lütfen biraz sonra tekrar deneyin.",
            f"'{prompt}' hakkında detaylı bilgi için teknik ekibimizle iletişime geçin.",
            "Üzgünüm, şu anda AI servislerimiz geçici olarak kullanılamıyor."
        ]
        
        import random
        return random.choice(turkish_responses)
    
    @staticmethod
    def detect_language_fallback(text: str) -> str:
        """Basit dil tanıma fallback"""
        turkish_chars = set('çğıöşüÇĞIİÖŞÜ')
        has_turkish = any(char in turkish_chars for char in text)
        return 'turkish' if has_turkish else 'other'

# Wrapper fonksiyonları - hem AI servis hem fallback desteği
async def safe_generate_embedding(text: str, force_turkish: bool = None) -> List[float]:
    """Güvenli embedding üretimi (fallback destekli)"""
    try:
        client = await get_ai_client()
        return await client.generate_embedding(text, force_turkish)
    except (AIServiceUnavailableError, AIServiceError) as e:
        logger.warning(f"AI servis kullanılamıyor, fallback kullanılıyor: {e}")
        return FallbackAIManager.generate_embedding_fallback(text)

async def safe_generate_text(prompt: str, max_length: int = 80, turkish_context: bool = True) -> str:
    """Güvenli metin üretimi (fallback destekli)"""
    try:
        client = await get_ai_client()
        return await client.generate_text(prompt, max_length, turkish_context)
    except (AIServiceUnavailableError, AIServiceError) as e:
        logger.warning(f"AI servis kullanılamıyor, fallback kullanılıyor: {e}")
        return FallbackAIManager.generate_text_fallback(prompt)

async def safe_generate_huggingface_response(message: str, user_id: str = None) -> str:
    """Güvenli Hugging Face yanıt üretimi (fallback destekli)"""
    try:
        client = await get_ai_client()
        return await client.generate_huggingface_response(message, user_id)
    except (AIServiceUnavailableError, AIServiceError) as e:
        logger.warning(f"AI servis kullanılamıyor, fallback kullanılıyor: {e}")
        return FallbackAIManager.generate_text_fallback(message)

async def safe_detect_language(text: str) -> str:
    """Güvenli dil tanıma (fallback destekli)"""
    try:
        client = await get_ai_client()
        return await client.detect_language(text)
    except (AIServiceUnavailableError, AIServiceError) as e:
        logger.warning(f"AI servis kullanılamıyor, fallback kullanılıyor: {e}")
        return FallbackAIManager.detect_language_fallback(text)
