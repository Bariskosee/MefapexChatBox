"""
Enhanced Thread-safe Model Manager for MEFAPEX AI Assistant
Fixed memory leak issues and improved resource management
"""
import threading
import logging
import gc
import torch
from sentence_transformers import SentenceTransformer
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
from typing import Optional, Dict, Any
import os
from functools import lru_cache
import atexit
from core.configuration import get_config

logger = logging.getLogger(__name__)

class ModelManager:
    """
    Thread-safe singleton model manager with proper memory management
    and cleanup to prevent memory leaks.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ModelManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    self._sentence_model = None
                    self._text_generator = None
                    self._device = None
                    self._model_config = {}
                    self._model_locks = {
                        'sentence': threading.Lock(),
                        'text_generator': threading.Lock()
                    }
                    self._memory_monitor = True
                    self._max_cache_size = 500  # Reduced cache size
                    self._initialized = True
                    
                    # Register cleanup on exit
                    atexit.register(self.cleanup_resources)
                    
                    logger.info("🤖 Enhanced ModelManager initialized with memory management")
    
    @property
    def device(self) -> str:
        """Get optimal device for model inference"""
        if self._device is None:
            if torch.backends.mps.is_available():
                self._device = "mps"
            elif torch.cuda.is_available():
                self._device = "cuda"
            else:
                self._device = "cpu"
            logger.info(f"🖥️ Using device: {self._device}")
        return self._device
    
    @property
    def sentence_model(self) -> SentenceTransformer:
        """
        Get sentence transformer model with thread-safe lazy loading
        """
        if self._sentence_model is None:
            with self._model_locks['sentence']:
                if self._sentence_model is None:
                    try:
                        logger.info("📚 Loading sentence transformer model...")
                        model_name = get_config().ai.sentence_model
                        
                        # Load with reduced memory footprint
                        self._sentence_model = SentenceTransformer(
                            model_name,
                            device=self.device if self.device != "mps" else "cpu"  # MPS fix
                        )
                        
                        self._model_config['sentence_model'] = model_name
                        logger.info(f"✅ Sentence transformer loaded: {model_name}")
                        
                        # Force garbage collection after model loading
                        self._force_gc()
                        
                    except Exception as e:
                        logger.error(f"❌ Failed to load sentence transformer: {e}")
                        raise RuntimeError(f"Could not load sentence model: {e}")
        
        return self._sentence_model
    
    @property
    def text_generator(self) -> Optional[Any]:
        """
        Get text generation model with thread-safe lazy loading and memory optimization
        """
        if self._text_generator is None:
            with self._model_locks['text_generator']:
                if self._text_generator is None:
                    try:
                        model_name = get_config().ai.huggingface_model
                        logger.info(f"🤖 Loading text generation model: {model_name}")
                        
                        # Load tokenizer separately for better memory control
                        tokenizer = AutoTokenizer.from_pretrained(model_name)
                        if tokenizer.pad_token is None:
                            tokenizer.pad_token = tokenizer.eos_token
                        
                        # Load model with memory-efficient settings
                        model = AutoModelForCausalLM.from_pretrained(
                            model_name,
                            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                            low_cpu_mem_usage=True,
                            device_map="auto" if self.device == "cuda" else None
                        )
                        
                        # Move to device if not CUDA (device_map handles CUDA)
                        if self.device != "cuda":
                            model = model.to(self.device if self.device != "mps" else "cpu")
                        
                        # Create pipeline with memory-efficient settings
                        self._text_generator = pipeline(
                            "text-generation",
                            model=model,
                            tokenizer=tokenizer,
                            device=0 if self.device == "cuda" else -1,
                            max_length=100,  # Reduced from 150
                            do_sample=True,
                            temperature=0.7,
                            return_full_text=False,
                            clean_up_tokenization_spaces=True,
                            batch_size=1  # Process one at a time
                        )
                        
                        self._model_config['text_generator'] = model_name
                        logger.info(f"✅ Text generation model loaded: {model_name}")
                        
                        # Force garbage collection after model loading
                        self._force_gc()
                        
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to load text generation model: {e}")
                        self._text_generator = None
        
        return self._text_generator
    
    @lru_cache(maxsize=500)  # Reduced cache size
    def generate_embedding(self, text: str) -> list:
        """
        Generate embedding with reduced caching for memory efficiency
        """
        try:
            # Limit text length to prevent memory issues
            normalized_text = text.strip().lower()[:500]  # Max 500 chars
            
            with torch.no_grad():  # Prevent gradient accumulation
                embedding = self.sentence_model.encode(
                    [normalized_text], 
                    convert_to_tensor=False,  # Return numpy array
                    show_progress_bar=False
                )[0].tolist()
            
            return embedding
            
        except Exception as e:
            logger.error(f"Embedding generation failed for text: {text[:50]}... Error: {e}")
            raise
        finally:
            # Periodic garbage collection
            if self.generate_embedding.cache_info().currsize % 50 == 0:
                self._force_gc()
    
    def generate_text_response(self, prompt: str, max_length: int = 80) -> str:
        """
        Generate text response with memory-efficient settings
        """
        try:
            if self.text_generator is None:
                raise RuntimeError("Text generator not available")
            
            # Limit prompt length
            prompt = prompt[:200]  # Max 200 chars
            
            with torch.no_grad():  # Prevent gradient accumulation
                outputs = self.text_generator(
                    prompt,
                    max_length=min(max_length, 80),  # Reduced max length
                    num_return_sequences=1,
                    temperature=0.8,
                    do_sample=True,
                    top_p=0.9,
                    top_k=50,
                    pad_token_id=self.text_generator.tokenizer.eos_token_id,
                    eos_token_id=self.text_generator.tokenizer.eos_token_id,
                    no_repeat_ngram_size=2,
                    repetition_penalty=1.2,
                    clean_up_tokenization_spaces=True
                )
            
            generated_text = outputs[0]['generated_text'].strip()
            
            # Force cleanup after text generation
            self._force_gc()
            
            return generated_text
            
        except Exception as e:
            logger.error(f"Text generation failed: {e}")
            raise
    
    def _force_gc(self):
        """Force garbage collection and CUDA cache cleanup"""
        try:
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception as e:
            logger.debug(f"GC cleanup warning: {e}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about loaded models and memory usage
        """
        memory_info = {}
        
        try:
            import psutil
            process = psutil.Process()
            memory_info = {
                "memory_mb": round(process.memory_info().rss / 1024 / 1024, 2),
                "memory_percent": round(process.memory_percent(), 2)
            }
        except ImportError:
            memory_info = {"memory_mb": "psutil not available"}
        
        cache_info = self.generate_embedding.cache_info()
        
        return {
            "sentence_model_loaded": self._sentence_model is not None,
            "text_generator_loaded": self._text_generator is not None,
            "device": self.device,
            "model_config": self._model_config,
            "memory_info": memory_info,
            "cache_info": {
                "embedding_cache_size": cache_info.currsize,
                "embedding_cache_hits": cache_info.hits,
                "embedding_cache_misses": cache_info.misses,
                "embedding_cache_maxsize": cache_info.maxsize
            }
        }
    
    def clear_caches(self):
        """
        Clear all model caches and force garbage collection
        """
        try:
            self.generate_embedding.cache_clear()
            self._force_gc()
            logger.info("🧹 Model caches cleared and memory cleaned")
        except Exception as e:
            logger.error(f"Cache clearing failed: {e}")
    
    def cleanup_resources(self):
        """
        Cleanup all resources and free memory
        """
        try:
            logger.info("🧹 Starting resource cleanup...")
            
            # Clear caches
            self.clear_caches()
            
            # Delete models
            if self._sentence_model is not None:
                del self._sentence_model
                self._sentence_model = None
                
            if self._text_generator is not None:
                del self._text_generator
                self._text_generator = None
            
            # Force cleanup
            self._force_gc()
            
            logger.info("✅ Resource cleanup completed")
            
        except Exception as e:
            logger.error(f"Resource cleanup failed: {e}")
    
    def warmup_models(self):
        """
        Warm up models with minimal sample data
        """
        try:
            logger.info("🔥 Warming up models...")
            
            # Warm up sentence model with minimal text
            sample_text = "Hello test"
            _ = self.generate_embedding(sample_text)
            
            # Warm up text generator with minimal prompt
            if self.text_generator is not None:
                sample_prompt = "Hello"
                _ = self.generate_text_response(sample_prompt, max_length=20)
            
            logger.info("✅ Model warmup completed")
            
        except Exception as e:
            logger.warning(f"⚠️ Model warmup failed: {e}")

# Global instance
model_manager = ModelManager()
