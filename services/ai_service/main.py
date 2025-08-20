"""
🤖 MEFAPEX AI Mikroservisi
=======================
AI işlemlerini yöneten ayrı mikroservis
- Metin üretimi
- Embedding oluşturma
- Dil tanıma
- Model yönetimi
"""
import logging
import asyncio
import os
import sys
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Proje root'unu path'e ekle
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# AI model manager'ı import et
from model_manager import model_manager
from core.configuration import get_config

# Logging ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Pydantic Models
class EmbeddingRequest(BaseModel):
    text: str
    force_turkish: Optional[bool] = None

class EmbeddingResponse(BaseModel):
    embedding: List[float]
    model_used: str
    language_detected: str

class TextGenerationRequest(BaseModel):
    prompt: str
    max_length: Optional[int] = 80
    turkish_context: Optional[bool] = True

class TextGenerationResponse(BaseModel):
    generated_text: str
    model_used: str
    quality_score: float

class LanguageDetectionRequest(BaseModel):
    text: str

class LanguageDetectionResponse(BaseModel):
    language: str
    confidence: float

class ModelInfoResponse(BaseModel):
    models_loaded: Dict[str, bool]
    device: str
    memory_usage: Dict[str, Any]
    cache_info: Dict[str, Any]
    lazy_loading_stats: Dict[str, Any]

class HealthResponse(BaseModel):
    status: str
    ai_service_version: str
    models_available: Dict[str, bool]
    memory_usage_mb: float
    uptime_seconds: float

# Global değişkenler
startup_time = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """AI Mikroservis yaşam döngüsü yönetimi"""
    global startup_time
    startup_time = asyncio.get_event_loop().time()
    
    # Startup
    logger.info("🤖 MEFAPEX AI Mikroservisi başlatılıyor...")
    
    try:
        # Model manager'ı yapılandır
        model_manager.set_auto_cleanup(
            enabled=True,
            cleanup_interval=300,  # 5 dakika
            max_idle_time=600      # 10 dakika
        )
        
        logger.info("✅ AI Mikroservisi başarıyla başlatıldı")
        
    except Exception as e:
        logger.error(f"❌ AI Mikroservisi başlatılamadı: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🔄 AI Mikroservisi kapatılıyor...")
    
    try:
        # Model kaynaklarını temizle
        model_manager.cleanup_resources()
        logger.info("✅ AI Mikroservisi temizlendi")
    except Exception as e:
        logger.error(f"❌ Kapatma hatası: {e}")

# FastAPI uygulaması oluştur
app = FastAPI(
    title="MEFAPEX AI Mikroservisi",
    description="AI işlemlerini yöneten mikroservis",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS ayarları
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Prod'da spesifik originler kullan
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """AI servis sağlık kontrolü"""
    try:
        global startup_time
        uptime = asyncio.get_event_loop().time() - startup_time if startup_time else 0
        
        # Model bilgilerini al
        model_info = model_manager.get_model_info()
        
        return HealthResponse(
            status="healthy",
            ai_service_version="1.0.0",
            models_available={
                "turkish_sentence": model_info["turkish_sentence_model_loaded"],
                "english_sentence": model_info["english_sentence_model_loaded"],
                "text_generator": model_info["text_generator_loaded"]
            },
            memory_usage_mb=model_info["memory_info"].get("memory_mb", 0),
            uptime_seconds=uptime
        )
    except Exception as e:
        logger.error(f"Sağlık kontrolü hatası: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")

@app.post("/embedding", response_model=EmbeddingResponse)
async def generate_embedding(request: EmbeddingRequest):
    """Metin için embedding oluştur"""
    try:
        if not request.text.strip():
            raise HTTPException(status_code=400, detail="Text cannot be empty")
        
        # Dil tanıma
        language = model_manager.detect_language(request.text)
        
        # Embedding oluştur
        embedding = model_manager.generate_embedding(
            request.text, 
            force_turkish=request.force_turkish
        )
        
        if not embedding:
            raise HTTPException(status_code=500, detail="Failed to generate embedding")
        
        # Kullanılan modeli belirle
        config = get_config().ai
        if request.force_turkish or (config.language_detection and language == 'turkish'):
            model_used = "turkish_sentence_transformer"
        else:
            model_used = "english_sentence_transformer"
        
        return EmbeddingResponse(
            embedding=embedding,
            model_used=model_used,
            language_detected=language
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Embedding oluşturma hatası: {e}")
        raise HTTPException(status_code=500, detail=f"Embedding generation failed: {str(e)}")

@app.post("/generate", response_model=TextGenerationResponse)
async def generate_text(request: TextGenerationRequest):
    """Metin üretimi"""
    try:
        if not request.prompt.strip():
            raise HTTPException(status_code=400, detail="Prompt cannot be empty")
        
        # Metin üret
        generated_text = model_manager.generate_text_response(
            prompt=request.prompt,
            max_length=request.max_length,
            turkish_context=request.turkish_context
        )
        
        if not generated_text:
            raise HTTPException(status_code=500, detail="Failed to generate text")
        
        # Kalite skoru hesapla (basit metrik)
        quality_score = min(1.0, len(generated_text.split()) / 10.0)
        
        return TextGenerationResponse(
            generated_text=generated_text,
            model_used="huggingface_text_generator", 
            quality_score=quality_score
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Metin üretme hatası: {e}")
        raise HTTPException(status_code=500, detail=f"Text generation failed: {str(e)}")

@app.post("/generate/huggingface")
async def generate_huggingface_response(request: TextGenerationRequest):
    """Gelişmiş Hugging Face yanıt üretimi"""
    try:
        if not request.prompt.strip():
            raise HTTPException(status_code=400, detail="Prompt cannot be empty")
        
        # Hugging Face modeli ile yanıt üret
        response = await model_manager.generate_huggingface_response(
            message=request.prompt,
            user_id="ai_service"
        )
        
        if not response:
            raise HTTPException(status_code=500, detail="Failed to generate response")
        
        return {"response": response}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Hugging Face yanıt hatası: {e}")
        raise HTTPException(status_code=500, detail=f"Hugging Face response failed: {str(e)}")

@app.post("/language/detect", response_model=LanguageDetectionResponse)
async def detect_language(request: LanguageDetectionRequest):
    """Dil tanıma"""
    try:
        if not request.text.strip():
            raise HTTPException(status_code=400, detail="Text cannot be empty")
        
        language = model_manager.detect_language(request.text)
        
        # Güven skoru hesapla (basit implementasyon)
        confidence = 0.9 if language == 'turkish' else 0.7
        
        return LanguageDetectionResponse(
            language=language,
            confidence=confidence
        )
        
    except Exception as e:
        logger.error(f"Dil tanıma hatası: {e}")
        raise HTTPException(status_code=500, detail=f"Language detection failed: {str(e)}")

@app.get("/models/info", response_model=ModelInfoResponse)
async def get_model_info():
    """Model bilgilerini al"""
    try:
        model_info = model_manager.get_model_info()
        
        return ModelInfoResponse(
            models_loaded={
                "turkish_sentence": model_info["turkish_sentence_model_loaded"],
                "english_sentence": model_info["english_sentence_model_loaded"],
                "text_generator": model_info["text_generator_loaded"]
            },
            device=model_info["device"],
            memory_usage=model_info["memory_info"],
            cache_info=model_info["cache_info"],
            lazy_loading_stats=model_info["lazy_loading_stats"]
        )
        
    except Exception as e:
        logger.error(f"Model bilgisi hatası: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get model info: {str(e)}")

@app.post("/models/warmup")
async def warmup_models():
    """Modelleri ısıt"""
    try:
        model_manager.warmup_models()
        return {"message": "Models warmed up successfully"}
        
    except Exception as e:
        logger.error(f"Model ısıtma hatası: {e}")
        raise HTTPException(status_code=500, detail=f"Model warmup failed: {str(e)}")

@app.post("/models/cleanup")
async def cleanup_models():
    """Model temizliği"""
    try:
        model_manager.clear_caches()
        return {"message": "Model caches cleared successfully"}
        
    except Exception as e:
        logger.error(f"Model temizlik hatası: {e}")
        raise HTTPException(status_code=500, detail=f"Model cleanup failed: {str(e)}")

@app.post("/models/unload")
async def unload_models():
    """Tüm modelleri kaldır"""
    try:
        model_manager.unload_all_models()
        return {"message": "All models unloaded successfully"}
        
    except Exception as e:
        logger.error(f"Model kaldırma hatası: {e}")
        raise HTTPException(status_code=500, detail=f"Model unload failed: {str(e)}")

@app.get("/stats/lazy-loading")
async def get_lazy_loading_stats():
    """Lazy loading istatistikleri"""
    try:
        stats = model_manager.get_lazy_loading_statistics()
        return {"lazy_loading_stats": stats}
        
    except Exception as e:
        logger.error(f"Lazy loading istatistik hatası: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get lazy loading stats: {str(e)}")

# Hata yöneticileri
@app.exception_handler(404)
async def not_found_handler(request, exc):
    """404 hata yöneticisi"""
    return {"error": "Endpoint not found", "detail": "The requested AI service endpoint does not exist"}

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """500 hata yöneticisi"""
    logger.error(f"Internal server error: {exc}")
    return {"error": "Internal server error", "detail": "AI service encountered an error"}

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="MEFAPEX AI Mikroservisi")
    parser.add_argument("--host", default="127.0.0.1", help="Host address")
    parser.add_argument("--port", type=int, default=8001, help="Port number")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    
    args = parser.parse_args()
    
    logger.info(f"🤖 MEFAPEX AI Mikroservisi başlatılıyor: {args.host}:{args.port}")
    
    uvicorn.run(
        "main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info"
    )
