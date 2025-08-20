"""
🚀 Enhanced Lazy-Loading Model Manager for MEFAPEX AI Assistant
==============================================================
Optimized for Turkish Language Support with Advanced Lazy Loading
- True lazy loading: Models only loaded when actually needed
- Memory-efficient: Automatic cleanup and garbage collection
- Smart caching: LRU cache with configurable size limits
- Turkish language optimization: Auto-detection and model selection
- Thread-safe: Concurrent access protection
Fixed memory leak issues and improved resource management
"""
import threading
import logging
import gc
import torch
import time
import weakref
from sentence_transformers import SentenceTransformer
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
from typing import Optional, Dict, Any, Union, Callable
import os
from functools import lru_cache, wraps
import atexit
from core.configuration import get_config
import re
from enum import Enum

logger = logging.getLogger(__name__)

class ModelType(Enum):
    """Model types for lazy loading management"""
    TURKISH_SENTENCE = "turkish_sentence"
    ENGLISH_SENTENCE = "english_sentence"
    TEXT_GENERATOR = "text_generator"

class LazyLoadTracker:
    """Track lazy loading statistics and performance"""
    
    def __init__(self):
        self.load_times = {}
        self.load_counts = {}
        self.last_access = {}
        self.memory_usage = {}
        
    def record_load(self, model_type: str, load_time: float, memory_mb: float):
        """Record model loading metrics"""
        self.load_times[model_type] = load_time
        self.load_counts[model_type] = self.load_counts.get(model_type, 0) + 1
        self.last_access[model_type] = time.time()
        self.memory_usage[model_type] = memory_mb
        
    def record_access(self, model_type: str):
        """Record model access"""
        self.last_access[model_type] = time.time()
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get loading statistics"""
        now = time.time()
        return {
            "load_times": self.load_times,
            "load_counts": self.load_counts,
            "last_access": {k: now - v for k, v in self.last_access.items()},
            "memory_usage": self.memory_usage
        }

def lazy_load_model(model_type: ModelType):
    """
    Decorator for lazy loading AI models with performance tracking
    Models are only loaded when first accessed, not during initialization
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Track access
            if hasattr(self, '_lazy_tracker'):
                self._lazy_tracker.record_access(model_type.value)
            
            # Check if model is already loaded
            attr_name = f"_{model_type.value.replace('_', '_')}_model"
            if getattr(self, attr_name, None) is not None:
                return getattr(self, attr_name)
            
            # Load model with timing and memory tracking
            start_time = time.time()
            start_memory = self._get_memory_usage()
            
            logger.info(f"🔄 Lazy loading {model_type.value} model...")
            
            # Call the original loading function
            model = func(self, *args, **kwargs)
            
            # Record performance metrics
            load_time = time.time() - start_time
            memory_used = self._get_memory_usage() - start_memory
            
            if hasattr(self, '_lazy_tracker'):
                self._lazy_tracker.record_load(model_type.value, load_time, memory_used)
            
            logger.info(f"✅ {model_type.value} model loaded in {load_time:.2f}s, memory: {memory_used:.1f}MB")
            
            # Store the loaded model
            setattr(self, attr_name, model)
            
            # Schedule periodic cleanup
            self._schedule_cleanup()
            
            return model
        return wrapper
    return decorator

def memory_efficient_cache(maxsize: int = 50):
    """
    Memory-efficient LRU cache with automatic cleanup
    Smaller cache size to prevent memory bloat
    """
    def decorator(func):
        cached_func = lru_cache(maxsize=maxsize)(func)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = cached_func(*args, **kwargs)
            
            # Periodic cache cleanup
            cache_info = cached_func.cache_info()
            if cache_info.currsize > maxsize * 0.8:  # 80% full
                logger.debug(f"Cache {func.__name__} approaching limit, considering cleanup")
                
            return result
        
        wrapper.cache_info = cached_func.cache_info
        wrapper.cache_clear = cached_func.cache_clear
        return wrapper
    return decorator

class TurkishLanguageDetector:
    """Simple Turkish language detection utility"""
    
    TURKISH_CHARS = set('çğıöşüÇĞIİÖŞÜ')
    TURKISH_WORDS = {
        've', 'ile', 'bir', 'bu', 'şu', 'ne', 'nasıl', 'nedir', 'niye', 'niçin',
        'için', 'den', 'dan', 'dır', 'dir', 'dur', 'dür', 'mı', 'mi', 'mu', 'mü',
        'da', 'de', 'ta', 'te', 'la', 'le', 'ya', 'ye', 'sa', 'se', 'ka', 'ke',
        'ben', 'sen', 'o', 'biz', 'siz', 'onlar', 'benim', 'senin', 'bizim',
        'sizin', 'onların', 'var', 'yok', 'varsa', 'yoksa', 'gibi', 'kadar',
        'çok', 'az', 'büyük', 'küçük', 'iyi', 'kötü', 'güzel', 'çirkin'
    }
    
    @classmethod
    def is_turkish(cls, text: str) -> bool:
        """Detect if text is primarily Turkish"""
        if not text:
            return False
            
        text_lower = text.lower().strip()
        words = re.findall(r'\b\w+\b', text_lower)
        
        if not words:
            return False
        
        # Check for Turkish-specific characters
        turkish_char_score = sum(1 for char in text if char in cls.TURKISH_CHARS) / len(text)
        
        # Check for Turkish words
        turkish_word_score = sum(1 for word in words if word in cls.TURKISH_WORDS) / len(words)
        
        # Combined score with character patterns having higher weight
        combined_score = (turkish_char_score * 0.7) + (turkish_word_score * 0.3)
        
        return combined_score > 0.1  # Threshold for Turkish detection

class ModelManager:
    """
    🚀 Advanced Lazy-Loading Model Manager with Memory Optimization
    ============================================================
    - True lazy loading: Models loaded only when actually needed
    - Memory-efficient: Smart cleanup and garbage collection  
    - Thread-safe: Concurrent access protection
    - Turkish optimization: Auto-detection and model selection
    - Performance tracking: Load times and memory usage metrics
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
                    # ⚠️ MODELS ARE NOT LOADED HERE - LAZY LOADING ONLY! ⚠️
                    self._english_sentence_model = None
                    self._turkish_sentence_model = None
                    self._text_generator_model = None
                    self._device = None
                    self._model_config = {}
                    
                    # Thread locks for each model type
                    self._model_locks = {
                        'english_sentence': threading.Lock(),
                        'turkish_sentence': threading.Lock(), 
                        'text_generator': threading.Lock()
                    }
                    
                    # Lazy loading and performance tracking
                    self._lazy_tracker = LazyLoadTracker()
                    self._last_cleanup = time.time()
                    self._cleanup_interval = 300  # 5 minutes
                    self._max_idle_time = 600  # 10 minutes before unloading
                    
                    # Memory management
                    self._memory_monitor = True
                    self._max_cache_size = 50  # Reduced for memory efficiency
                    self._auto_cleanup = True
                    
                    # Language detection
                    self._language_detector = TurkishLanguageDetector()
                    
                    # Model cache directory
                    self._cache_dir = os.path.join(os.getcwd(), "models_cache")
                    os.makedirs(self._cache_dir, exist_ok=True)
                    
                    # Register cleanup on exit
                    atexit.register(self.cleanup_resources)
                    
                    self._initialized = True
                    logger.info("🚀 Lazy-Loading ModelManager initialized - models will load on first use")
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return 0.0
    
    def _schedule_cleanup(self):
        """Schedule periodic cleanup of unused models"""
        if not self._auto_cleanup:
            return
            
        current_time = time.time()
        if current_time - self._last_cleanup > self._cleanup_interval:
            threading.Thread(target=self._cleanup_idle_models, daemon=True).start()
            self._last_cleanup = current_time
    
    def _cleanup_idle_models(self):
        """Clean up models that haven't been used recently"""
        try:
            current_time = time.time()
            models_to_cleanup = []
            
            for model_type, last_access in self._lazy_tracker.last_access.items():
                if current_time - last_access > self._max_idle_time:
                    models_to_cleanup.append(model_type)
            
            for model_type in models_to_cleanup:
                self._unload_model(model_type)
                logger.info(f"🧹 Unloaded idle model: {model_type}")
            
            if models_to_cleanup:
                self._force_gc()
                
        except Exception as e:
            logger.warning(f"Model cleanup failed: {e}")
    
    def _unload_model(self, model_type: str):
        """Unload a specific model to free memory"""
        attr_name = f"_{model_type.replace('_', '_')}_model"
        if hasattr(self, attr_name):
            model = getattr(self, attr_name)
            if model is not None:
                del model
                setattr(self, attr_name, None)
                # Remove from config
                self._model_config.pop(model_type, None)
    
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
        Get sentence transformer model with intelligent model selection
        Automatically chooses Turkish or English model based on configuration
        """
        config = get_config().ai
        
        # Determine which model to use based on configuration
        if config.prefer_turkish_models:
            return self.turkish_sentence_model
        else:
            return self.english_sentence_model
    
    @property
    @lazy_load_model(ModelType.TURKISH_SENTENCE)
    def turkish_sentence_model(self) -> SentenceTransformer:
        """
        🇹🇷 Lazy-loaded Turkish-optimized sentence transformer
        Only loads when first accessed, not during initialization
        """
        with self._model_locks['turkish_sentence']:
            try:
                logger.info("📚 Loading Turkish sentence transformer model...")
                config = get_config().ai
                model_name = config.turkish_sentence_model
                
                # Force garbage collection before loading
                self._force_gc()
                
                # Load Turkish-optimized model with memory-efficient settings
                model = SentenceTransformer(
                    model_name,
                    device=self.device if self.device != "mps" else "cpu",  # MPS compatibility
                    cache_folder=self._cache_dir
                )
                
                # Optimize for inference
                model.eval()
                if hasattr(model, 'half') and self.device == "cuda":
                    model.half()  # Use FP16 for memory efficiency on CUDA
                
                self._model_config['turkish_sentence_model'] = model_name
                logger.info(f"✅ Turkish sentence transformer loaded: {model_name}")
                
                return model
                
            except Exception as e:
                logger.error(f"❌ Failed to load Turkish sentence transformer: {e}")
                logger.warning("🔄 Falling back to multilingual model...")
                
                # Fallback to multilingual model
                try:
                    fallback_model = SentenceTransformer(
                        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                        device=self.device if self.device != "mps" else "cpu",
                        cache_folder=self._cache_dir
                    )
                    fallback_model.eval()
                    self._model_config['turkish_sentence_model'] = "multilingual-fallback"
                    logger.info("✅ Multilingual fallback model loaded")
                    return fallback_model
                    
                except Exception as fallback_e:
                    logger.error(f"❌ Fallback model also failed: {fallback_e}")
                    raise RuntimeError(f"Could not load any Turkish sentence model: {e}")
    
    @property  
    @lazy_load_model(ModelType.ENGLISH_SENTENCE)
    def english_sentence_model(self) -> SentenceTransformer:
        """
        🇺🇸 Lazy-loaded English sentence transformer (fallback)
        Only loads when first accessed, not during initialization
        """
        with self._model_locks['english_sentence']:
            try:
                logger.info("📚 Loading English sentence transformer model...")
                config = get_config().ai
                model_name = config.english_fallback_model
                
                # Force garbage collection before loading
                self._force_gc()
                
                # Load with memory-efficient settings
                model = SentenceTransformer(
                    model_name,
                    device=self.device if self.device != "mps" else "cpu",
                    cache_folder=self._cache_dir
                )
                
                # Optimize for inference
                model.eval()
                if hasattr(model, 'half') and self.device == "cuda":
                    model.half()  # Use FP16 for memory efficiency on CUDA
                
                self._model_config['english_sentence_model'] = model_name
                logger.info(f"✅ English sentence transformer loaded: {model_name}")
                
                return model
                
            except Exception as e:
                logger.error(f"❌ Failed to load English sentence transformer: {e}")
                raise RuntimeError(f"Could not load English sentence model: {e}")
    
    @property
    @lazy_load_model(ModelType.TEXT_GENERATOR)  
    def text_generator(self) -> Optional[Any]:
        """
        🤖 Lazy-loaded text generation model with memory optimization
        Only loads when first accessed, not during initialization
        """
        with self._model_locks['text_generator']:
            try:
                model_name = get_config().ai.huggingface_model
                logger.info(f"🤖 Loading text generation model: {model_name}")
                
                # Force garbage collection before loading
                self._force_gc()
                
                # Load tokenizer with caching
                tokenizer = AutoTokenizer.from_pretrained(
                    model_name,
                    cache_dir=self._cache_dir
                )
                if tokenizer.pad_token is None:
                    tokenizer.pad_token = tokenizer.eos_token
                
                # Memory-efficient model loading
                model_kwargs = {
                    "cache_dir": self._cache_dir,
                    "low_cpu_mem_usage": True,
                }
                
                # Configure for different devices
                if self.device == "cuda":
                    model_kwargs.update({
                        "torch_dtype": torch.float16,
                        "device_map": "auto"
                    })
                elif self.device == "cpu":
                    model_kwargs.update({
                        "torch_dtype": torch.float32
                    })
                
                model = AutoModelForCausalLM.from_pretrained(model_name, **model_kwargs)
                
                # Move to device if not using device_map
                if self.device != "cuda":
                    model = model.to(self.device if self.device != "mps" else "cpu")
                
                # Create optimized pipeline
                text_generator = pipeline(
                    "text-generation",
                    model=model,
                    tokenizer=tokenizer,
                    device=0 if self.device == "cuda" else -1,
                    max_length=100,
                    do_sample=True,
                    temperature=0.7,
                    return_full_text=False,
                    clean_up_tokenization_spaces=True,
                    batch_size=1,
                    torch_dtype=torch.float16 if self.device == "cuda" else torch.float32
                )
                
                self._model_config['text_generator'] = model_name
                logger.info(f"✅ Text generation model loaded: {model_name}")
                
                return text_generator
                
            except Exception as e:
                logger.warning(f"⚠️ Failed to load text generation model: {e}")
                return None
    
    def get_sentence_embedding(self, text: str) -> Optional[list]:
        """
        Get sentence embedding for the given text (alias for generate_embedding)
        Returns embedding as list for compatibility with enhanced question matcher
        """
        try:
            return self.generate_embedding(text)
        except Exception as e:
            logger.error(f"Failed to get sentence embedding: {e}")
            return None

    @memory_efficient_cache(maxsize=50)  # Reduced cache size for better memory management
    def generate_embedding(self, text: str, force_turkish: bool = None) -> list:
        """
        🧠 Generate embedding with smart language detection and memory optimization
        Uses lazy loading - models only load when first needed
        """
        try:
            # Limit text length to prevent memory issues
            normalized_text = text.strip().lower()[:500]  # Max 500 chars
            
            # Detect language or use forced setting
            config = get_config().ai
            use_turkish_model = force_turkish
            
            if use_turkish_model is None and config.language_detection:
                use_turkish_model = self._language_detector.is_turkish(normalized_text)
            elif use_turkish_model is None:
                use_turkish_model = config.prefer_turkish_models
            
            # Choose appropriate model (triggers lazy loading if needed)
            if use_turkish_model:
                logger.debug(f"🇹🇷 Using Turkish model for: {normalized_text[:30]}...")
                model = self.turkish_sentence_model  # Lazy loaded
            else:
                logger.debug(f"🇺🇸 Using English model for: {normalized_text[:30]}...")
                model = self.english_sentence_model  # Lazy loaded
            
            # Generate embedding with memory optimization
            with torch.no_grad():  # Prevent gradient accumulation
                embedding = model.encode(
                    [normalized_text], 
                    convert_to_tensor=False,  # Return numpy array
                    show_progress_bar=False,
                    batch_size=1  # Process one at a time
                )[0].tolist()
            
            # Periodic memory cleanup
            if hasattr(self, '_embedding_counter'):
                self._embedding_counter += 1
            else:
                self._embedding_counter = 1
                
            # More frequent cleanup for better memory management
            if self._embedding_counter % 25 == 0:  # Every 25 embeddings
                self._force_gc()
            
            return embedding
            
        except Exception as e:
            logger.error(f"Embedding generation failed for text: {text[:50]}... Error: {e}")
            # Fallback to English model if Turkish model fails
            if use_turkish_model:
                logger.warning("🔄 Falling back to English model...")
                return self.generate_embedding(text, force_turkish=False)
            raise
        finally:
            # Periodic cache cleanup for memory efficiency
            cache_info = self.generate_embedding.cache_info()
            if cache_info.currsize > 40:  # Near cache limit
                if cache_info.currsize % 10 == 0:  # Every 10th near-full cache
                    self._force_gc()
    
    def generate_text_response(self, prompt: str, max_length: int = 80, turkish_context: bool = True) -> str:
        """
        Generate text response with improved quality settings and Turkish support
        """
        try:
            if self.text_generator is None:
                raise RuntimeError("Text generator not available")
            
            # Limit prompt length and clean it
            prompt = prompt[:150]  # Reduced prompt length
            
            # Enhanced Turkish context for better responses
            if turkish_context and self._language_detector.is_turkish(prompt):
                # Create a more structured prompt for better quality
                enhanced_prompt = f"Soru: {prompt}\nYanıt:"
            else:
                enhanced_prompt = prompt
            
            with torch.no_grad():  # Prevent gradient accumulation
                outputs = self.text_generator(
                    enhanced_prompt,
                    max_length=min(max_length, 80),  # Reduced max length for focus
                    num_return_sequences=1,
                    temperature=0.6,  # Reduced for more coherent responses
                    do_sample=True,
                    top_p=0.85,  # Reduced for better quality
                    top_k=40,  # Reduced for more focused responses
                    pad_token_id=self.text_generator.tokenizer.eos_token_id,
                    eos_token_id=self.text_generator.tokenizer.eos_token_id,
                    no_repeat_ngram_size=3,  # Increased to prevent repetition
                    repetition_penalty=1.3,  # Increased to discourage repetition
                    length_penalty=0.8,  # Encourage shorter, more focused responses
                    early_stopping=True,  # Stop when EOS token is reached
                    clean_up_tokenization_spaces=True
                )
            
            generated_text = outputs[0]['generated_text'].strip()
            
            # Clean up the enhanced prompt prefix if it was added
            if turkish_context and generated_text.startswith("Soru:"):
                # Remove the "Soru: ... Yanıt:" part
                yanit_index = generated_text.find("Yanıt:")
                if yanit_index != -1:
                    generated_text = generated_text[yanit_index + 6:].strip()
            
            # Additional cleaning for better quality
            generated_text = self._post_process_generated_text(generated_text, prompt)
            
            # Force cleanup after text generation
            self._force_gc()
            
            return generated_text
            
        except Exception as e:
            logger.error(f"Text generation failed: {e}")
            raise
    
    def _post_process_generated_text(self, text: str, original_prompt: str) -> str:
        """
        Post-process generated text for better quality
        """
        try:
            # Remove original prompt if it appears at the beginning
            if original_prompt and original_prompt.lower() in text.lower()[:100]:
                idx = text.lower().find(original_prompt.lower())
                if idx == 0:  # Only if it's at the very beginning
                    text = text[len(original_prompt):].strip()
            
            # Remove common artifacts
            text = text.replace("</s>", "").replace("<s>", "").strip()
            
            # Remove excessive whitespace
            import re
            text = re.sub(r'\s+', ' ', text).strip()
            
            # If text is too short or seems incomplete, return empty
            if len(text) < 8:
                return ""
            
            # Remove incomplete sentences at the end
            sentences = text.split('.')
            if len(sentences) > 1 and len(sentences[-1].strip()) < 5:
                # Last sentence seems incomplete, remove it
                text = '.'.join(sentences[:-1]) + '.'
            
            return text.strip()
            
        except Exception as e:
            logger.warning(f"Post-processing failed: {e}")
            return text
    
    async def generate_huggingface_response(self, message: str, user_id: str = None) -> str:
        """
        Generate improved Hugging Face response with quality control
        """
        try:
            # Use the improved text generation method
            response = self.generate_text_response(
                prompt=message,
                max_length=100,
                turkish_context=True
            )
            
            # Quality check and enhancement
            if response and len(response.strip()) > 8:
                cleaned_response = response.strip()
                
                # Advanced cleaning: remove user message repetition
                if message.lower() in cleaned_response.lower():
                    # Find and remove the original message
                    idx = cleaned_response.lower().find(message.lower())
                    if idx >= 0:
                        before = cleaned_response[:idx].strip()
                        after = cleaned_response[idx + len(message):].strip()
                        # Keep the part that seems like a response
                        if len(after) > len(before) and len(after) > 10:
                            cleaned_response = after
                        elif len(before) > 10:
                            cleaned_response = before
                
                # Check for minimum quality standards
                if len(cleaned_response.split()) < 3:
                    return "Üzgünüm, şu anda bu konuda size net bir yanıt veremiyorum. Lütfen sorunuzu daha detaylandırabilir misiniz?"
                
                # Check for repetitive or nonsensical content
                words = cleaned_response.split()
                if len(set(words)) < len(words) * 0.7:  # Too many repeated words
                    return "Bu konu hakkında size daha iyi yardımcı olabilmem için sorunuzu biraz daha açabilir misiniz?"
                
                # Add appropriate MEFAPEX context for good responses
                if len(cleaned_response) > 15 and not any(word in cleaned_response.lower() for word in ['mefapex', 'destek', 'yardım', 'asistan']):
                    formatted_response = f"🤖 **MEFAPEX AI Asistanı:**\n\n{cleaned_response}\n\n💡 Daha detaylı bilgi için destek ekibimizle iletişime geçebilirsiniz."
                    return formatted_response
                
                return cleaned_response
            
            # Fallback for poor quality responses
            return "Üzgünüm, şu anda bu konuda size yardımcı olamıyorum. Farklı bir soru sormayı deneyebilir veya destek ekibimizle iletişime geçebilirsiniz."
            
        except Exception as e:
            logger.error(f"Hugging Face response generation failed: {e}")
            # Return a helpful fallback instead of raising
            return "Teknik bir sorun yaşıyorum. Lütfen sorunuzu tekrar sormayı deneyin veya destek ekibimizle iletişime geçin."
    
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
        📊 Get comprehensive model information and performance metrics
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
        lazy_stats = self._lazy_tracker.get_statistics()
        
        return {
            # Model loading status (lazy loaded)
            "english_sentence_model_loaded": self._english_sentence_model is not None,
            "turkish_sentence_model_loaded": self._turkish_sentence_model is not None,
            "text_generator_loaded": self._text_generator_model is not None,
            
            # System info
            "device": self.device,
            "model_config": self._model_config,
            "memory_info": memory_info,
            
            # Configuration
            "language_detection_enabled": get_config().ai.language_detection,
            "prefer_turkish_models": get_config().ai.prefer_turkish_models,
            
            # Cache performance
            "cache_info": {
                "embedding_cache_size": cache_info.currsize,
                "embedding_cache_hits": cache_info.hits,
                "embedding_cache_misses": cache_info.misses,
                "embedding_cache_maxsize": cache_info.maxsize,
                "cache_hit_ratio": cache_info.hits / (cache_info.hits + cache_info.misses) if (cache_info.hits + cache_info.misses) > 0 else 0
            },
            
            # Lazy loading statistics
            "lazy_loading_stats": lazy_stats,
            
            # Memory management
            "auto_cleanup_enabled": self._auto_cleanup,
            "cleanup_interval_seconds": self._cleanup_interval,
            "max_idle_time_seconds": self._max_idle_time,
            "last_cleanup": time.time() - self._last_cleanup
        }
    
    def clear_caches(self):
        """
        🧹 Clear all model caches and force garbage collection
        """
        try:
            self.generate_embedding.cache_clear()
            self._force_gc()
            logger.info("🧹 Model caches cleared and memory cleaned")
        except Exception as e:
            logger.error(f"Cache clearing failed: {e}")
    
    def unload_all_models(self):
        """
        🗑️ Unload all models to free maximum memory
        """
        try:
            logger.info("🗑️ Unloading all models...")
            
            # Clear caches first
            self.clear_caches()
            
            # Unload all models
            models_unloaded = []
            
            if self._turkish_sentence_model is not None:
                del self._turkish_sentence_model
                self._turkish_sentence_model = None
                models_unloaded.append("Turkish sentence model")
                
            if self._english_sentence_model is not None:
                del self._english_sentence_model
                self._english_sentence_model = None
                models_unloaded.append("English sentence model")
                
            if self._text_generator_model is not None:
                del self._text_generator_model
                self._text_generator_model = None
                models_unloaded.append("Text generator model")
            
            # Clear model config
            self._model_config.clear()
            
            # Reset lazy loading tracker
            self._lazy_tracker = LazyLoadTracker()
            
            # Force cleanup
            self._force_gc()
            
            logger.info(f"✅ Models unloaded: {', '.join(models_unloaded) if models_unloaded else 'None were loaded'}")
            
        except Exception as e:
            logger.error(f"Model unloading failed: {e}")
    
    def cleanup_resources(self):
        """
        🧹 Cleanup all resources and free memory
        """
        try:
            logger.info("🧹 Starting resource cleanup...")
            
            # Unload all models
            self.unload_all_models()
            
            logger.info("✅ Resource cleanup completed")
            
        except Exception as e:
            logger.error(f"Resource cleanup failed: {e}")
    
    def set_auto_cleanup(self, enabled: bool, cleanup_interval: int = 300, max_idle_time: int = 600):
        """
        ⚙️ Configure automatic model cleanup
        
        Args:
            enabled: Enable/disable automatic cleanup
            cleanup_interval: How often to check for idle models (seconds)
            max_idle_time: How long before unloading idle models (seconds)
        """
        self._auto_cleanup = enabled
        self._cleanup_interval = cleanup_interval
        self._max_idle_time = max_idle_time
        
        logger.info(f"🔧 Auto cleanup: {'enabled' if enabled else 'disabled'}, "
                   f"interval: {cleanup_interval}s, max idle: {max_idle_time}s")
    
    def warmup_models(self, models: list = None):
        """
        🔥 Warm up specific models with minimal sample data
        
        Args:
            models: List of model types to warm up. If None, warms up configured models.
        """
        try:
            logger.info("🔥 Warming up models...")
            
            config = get_config().ai
            models_to_warmup = models or []
            
            # Determine which models to warm up based on configuration
            if not models_to_warmup:
                if config.prefer_turkish_models:
                    models_to_warmup.append("turkish_sentence")
                else:
                    models_to_warmup.append("english_sentence")
                
                if config.use_huggingface:
                    models_to_warmup.append("text_generator")
            
            warmed_models = []
            
            # Warm up sentence models
            if "turkish_sentence" in models_to_warmup:
                try:
                    turkish_sample = "Merhaba test"
                    _ = self.generate_embedding(turkish_sample, force_turkish=True)
                    warmed_models.append("Turkish sentence model")
                except Exception as e:
                    logger.warning(f"Failed to warm up Turkish model: {e}")
            
            if "english_sentence" in models_to_warmup:
                try:
                    english_sample = "Hello test"
                    _ = self.generate_embedding(english_sample, force_turkish=False)
                    warmed_models.append("English sentence model")
                except Exception as e:
                    logger.warning(f"Failed to warm up English model: {e}")
            
            # Warm up text generator
            if "text_generator" in models_to_warmup:
                try:
                    if self.text_generator is not None:
                        turkish_prompt = "Merhaba"
                        _ = self.generate_text_response(turkish_prompt, max_length=20, turkish_context=True)
                        warmed_models.append("Text generator model")
                except Exception as e:
                    logger.warning(f"Failed to warm up text generator: {e}")
            
            logger.info(f"✅ Model warmup completed: {', '.join(warmed_models) if warmed_models else 'No models warmed'}")
            
        except Exception as e:
            logger.warning(f"⚠️ Model warmup failed: {e}")
    
    def detect_language(self, text: str) -> str:
        """
        🔍 Detect language of given text
        Returns: 'turkish' or 'other'
        """
        if self._language_detector.is_turkish(text):
            return 'turkish'
        return 'other'
    
    def get_embedding_model_for_text(self, text: str) -> SentenceTransformer:
        """
        🎯 Get the most appropriate embedding model for the given text
        Uses lazy loading - model loads only when accessed
        """
        config = get_config().ai
        
        if config.language_detection and self._language_detector.is_turkish(text):
            return self.turkish_sentence_model  # Lazy loaded
        elif config.prefer_turkish_models:
            return self.turkish_sentence_model  # Lazy loaded
        else:
            return self.english_sentence_model  # Lazy loaded
    
    def get_lazy_loading_statistics(self) -> Dict[str, Any]:
        """
        📈 Get detailed lazy loading performance statistics
        """
        return {
            "tracker": self._lazy_tracker.get_statistics(),
            "config": {
                "auto_cleanup": self._auto_cleanup,
                "cleanup_interval": self._cleanup_interval,
                "max_idle_time": self._max_idle_time,
                "max_cache_size": self._max_cache_size
            },
            "current_state": {
                "models_loaded": {
                    "turkish_sentence": self._turkish_sentence_model is not None,
                    "english_sentence": self._english_sentence_model is not None,
                    "text_generator": self._text_generator_model is not None
                },
                "memory_usage_mb": self._get_memory_usage(),
                "cache_usage": self.generate_embedding.cache_info()._asdict()
            }
        }

# Global instance with lazy loading optimization
model_manager = ModelManager()
