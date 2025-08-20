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

def memory_efficient_cache(maxsize: int = 20):  # CRITICAL FIX: Reduced default from 50 to 20
    """
    CRITICAL MEMORY LEAK FIX: Enhanced memory-efficient LRU cache with aggressive cleanup
    Much smaller cache size and more frequent cleanup to prevent memory bloat
    """
    def decorator(func):
        cached_func = lru_cache(maxsize=maxsize)(func)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = cached_func(*args, **kwargs)
            
            # CRITICAL FIX: More aggressive cache cleanup
            cache_info = cached_func.cache_info()
            if cache_info.currsize > maxsize * 0.6:  # CRITICAL FIX: Reduced from 80% to 60%
                logger.debug(f"Cache {func.__name__} at {cache_info.currsize}/{maxsize}, triggering cleanup")
                # CRITICAL FIX: Clear cache when it gets moderately full
                if cache_info.currsize >= maxsize * 0.8:  # 80% full
                    cached_func.cache_clear()
                    logger.debug(f"🧹 Cache {func.__name__} cleared due to memory pressure")
                    
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
                    
                    # CRITICAL FIX: Enhanced lazy loading and performance tracking
                    self._lazy_tracker = LazyLoadTracker()
                    self._last_cleanup = time.time()
                    self._cleanup_interval = 150  # CRITICAL FIX: More frequent cleanup
                    self._max_idle_time = 300  # CRITICAL FIX: Shorter idle time
                    
                    # Memory management
                    self._memory_monitor = True
                    self._max_cache_size = 20  # CRITICAL FIX: Reduced from 50 to 20
                    self._auto_cleanup = True
                    self._cleanup_interval = 150  # CRITICAL FIX: Reduced from 300 to 150 seconds
                    self._max_idle_time = 300  # CRITICAL FIX: Reduced from 600 to 300 seconds
                    
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

    @memory_efficient_cache(maxsize=20)  # CRITICAL FIX: Reduced from 50 to 20 to prevent memory bloat
    def generate_embedding(self, text: str, force_turkish: bool = None) -> list:
        """
        🧠 Generate embedding with CRITICAL memory leak fixes and optimization
        Uses lazy loading - models only load when first needed
        """
        try:
            # CRITICAL FIX: More aggressive text length limiting
            normalized_text = text.strip().lower()[:200]  # Reduced from 500 to 200 chars
            
            # CRITICAL FIX: Skip empty or very short texts immediately
            if len(normalized_text.strip()) < 3:
                return []
            
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
            
            # CRITICAL FIX: Generate embedding with aggressive memory optimization
            with torch.no_grad():  # Prevent gradient accumulation
                # CRITICAL FIX: Use torch.inference_mode for better memory efficiency
                with torch.inference_mode():
                    embedding = model.encode(
                        [normalized_text], 
                        convert_to_tensor=False,  # Return numpy array, not tensor
                        show_progress_bar=False,
                        batch_size=1,  # Process one at a time
                        normalize_embeddings=True,  # Normalize for better similarity calculations
                        device=self.device if self.device != "mps" else "cpu"  # Ensure correct device
                    )[0]
                    
                    # CRITICAL FIX: Convert to list immediately and del numpy array
                    result = embedding.tolist()
                    del embedding  # Explicit cleanup
                    
            # CRITICAL FIX: More aggressive periodic memory cleanup
            if hasattr(self, '_embedding_counter'):
                self._embedding_counter += 1
            else:
                self._embedding_counter = 1
                
            # CRITICAL FIX: Much more frequent cleanup - every 15 embeddings instead of 25
            if self._embedding_counter % 15 == 0:
                self._force_gc()
                logger.debug(f"🧹 Memory cleanup after {self._embedding_counter} embeddings")
            
            return result
            
        except Exception as e:
            logger.error(f"Embedding generation failed for text: {text[:50]}... Error: {e}")
            # Fallback to English model if Turkish model fails
            if use_turkish_model:
                logger.warning("🔄 Falling back to English model...")
                try:
                    return self.generate_embedding(text, force_turkish=False)
                except Exception as fallback_e:
                    logger.error(f"Fallback also failed: {fallback_e}")
                    return []
            return []
        finally:
            # CRITICAL FIX: Aggressive cache cleanup for memory efficiency
            try:
                cache_info = self.generate_embedding.cache_info()
                if cache_info.currsize > 15:  # CRITICAL FIX: Reduced from 40 to 15
                    if cache_info.currsize >= 18:  # CRITICAL FIX: Clear cache when near full
                        self.generate_embedding.cache_clear()
                        self._force_gc()
                        logger.debug("🧹 Cache cleared due to memory pressure")
            except Exception as cleanup_e:
                logger.debug(f"Cache cleanup warning: {cleanup_e}")
    
    def generate_text_response(self, prompt: str, max_length: int = 60, turkish_context: bool = True) -> str:
        """
        CRITICAL FIX: Generate text response with aggressive memory optimization and leak prevention
        """
        try:
            if self.text_generator is None:
                raise RuntimeError("Text generator not available")
            
            # CRITICAL FIX: More aggressive prompt length limiting
            prompt = prompt[:100]  # Reduced from 150
            
            # Enhanced Turkish context for better responses
            if turkish_context and self._language_detector.is_turkish(prompt):
                # Create a more structured prompt for better quality
                enhanced_prompt = f"Soru: {prompt}\nYanıt:"
            else:
                enhanced_prompt = prompt
            
            # CRITICAL FIX: Enhanced memory management for text generation
            with torch.no_grad():  # Prevent gradient accumulation
                with torch.inference_mode():  # CRITICAL FIX: Better memory efficiency
                    outputs = self.text_generator(
                        enhanced_prompt,
                        max_length=min(max_length, 60),  # CRITICAL FIX: Reduced max length
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
            
            # CRITICAL FIX: Force cleanup after text generation
            del outputs  # Explicit cleanup
            self._force_gc()
            
            return generated_text
            
        except Exception as e:
            logger.error(f"Text generation failed: {e}")
            # CRITICAL FIX: Ensure cleanup even on error
            self._force_gc()
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
        ENHANCED: Generate improved Hugging Face response with Turkish quality optimization
        """
        try:
            # First try improved Turkish content manager
            try:
                from improved_turkish_content_manager import improved_turkish_content
                static_response = improved_turkish_content.get_response(message)
                
                # Check if we got a meaningful static response (not fallback)
                if static_response and not any(phrase in static_response.lower() for phrase in [
                    'elimde yeterli bilgi', 'bu konuda size', 'daha detaylandırır'
                ]):
                    logger.info("🎯 Using improved Turkish static response")
                    return static_response
                    
            except ImportError:
                logger.debug("Improved Turkish content manager not available")
            
            # Generate AI response with quality control
            response = self.generate_text_response(
                prompt=message,
                max_length=80,  # Increased for better responses
                turkish_context=True
            )
            
            # ENHANCED: Quality check and improvement
            if response and len(response.strip()) > 8:
                cleaned_response = self._enhance_turkish_response(response, message)
                
                # Quality threshold check
                quality_score = self._assess_response_quality(cleaned_response, message)
                
                if quality_score < get_config().ai.turkish_quality_threshold:
                    logger.warning(f"Response quality too low ({quality_score:.2f}), using fallback")
                    return self._get_quality_fallback_response(message)
                
                return cleaned_response
            
            # Fallback for poor quality responses
            return self._get_quality_fallback_response(message)
            
        except Exception as e:
            logger.error(f"Hugging Face response generation failed: {e}")
            return self._get_quality_fallback_response(message)
    
    def _enhance_turkish_response(self, response: str, original_message: str) -> str:
        """ENHANCED: Improve Turkish response quality"""
        try:
            # Clean the response
            cleaned = response.strip()
            
            # Remove artifacts and repetitions
            import re
            
            # Remove common artifacts
            cleaned = re.sub(r'</s>|<s>|<pad>|<unk>', '', cleaned)
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()
            
            # Remove original message repetition
            if original_message.lower() in cleaned.lower():
                idx = cleaned.lower().find(original_message.lower())
                if idx >= 0:
                    before = cleaned[:idx].strip()
                    after = cleaned[idx + len(original_message):].strip()
                    
                    # Choose the better part
                    if len(after) > len(before) and len(after) > 10:
                        cleaned = after
                    elif len(before) > 10:
                        cleaned = before
            
            # Fix Turkish-specific issues
            cleaned = self._fix_turkish_grammar(cleaned)
            
            # Ensure proper ending
            if cleaned and not cleaned.endswith(('.', '!', '?')):
                cleaned += '.'
            
            # Add MEFAPEX context if appropriate
            if len(cleaned) > 20 and self._should_add_mefapex_context(cleaned):
                cleaned = f"🤖 **MEFAPEX AI Asistanı:** {cleaned}\n\n💡 Daha detaylı bilgi için ilgili departmanla iletişime geçebilirsiniz."
            
            return cleaned
            
        except Exception as e:
            logger.warning(f"Response enhancement failed: {e}")
            return response
    
    def _fix_turkish_grammar(self, text: str) -> str:
        """Fix common Turkish grammar issues in AI responses"""
        try:
            # Turkish-specific fixes
            fixes = {
                # Common grammar fixes
                ' de ': ' da ',  # Turkish "de/da" conjunction
                ' ve ': ' ve ',  # Ensure proper spacing
                'mefapex': 'MEFAPEX',  # Proper company name
                'Mefapex': 'MEFAPEX',
                
                # Remove repetitive patterns
                r'(\w+)\s+\1': r'\1',  # Remove word repetitions
                r'\.\.+': '.',  # Multiple dots to single
                r'\s+': ' '  # Multiple spaces to single
            }
            
            import re
            for pattern, replacement in fixes.items():
                if pattern.startswith('r\''):
                    # Regex pattern
                    pattern = pattern[2:-1]  # Remove r' and '
                    text = re.sub(pattern, replacement, text)
                else:
                    # Simple replacement
                    text = text.replace(pattern, replacement)
            
            return text.strip()
            
        except Exception as e:
            logger.warning(f"Grammar fix failed: {e}")
            return text
    
    def _assess_response_quality(self, response: str, original_message: str) -> float:
        """Assess the quality of a Turkish response"""
        try:
            if not response or len(response.strip()) < 5:
                return 0.0
            
            quality_score = 1.0
            words = response.split()
            
            # Length penalties/bonuses
            if len(words) < 3:
                quality_score *= 0.3  # Too short
            elif len(words) > 100:
                quality_score *= 0.7  # Too long
            elif 10 <= len(words) <= 50:
                quality_score *= 1.2  # Good length
            
            # Repetition check
            unique_words = set(words)
            if len(unique_words) < len(words) * 0.6:  # Too many repetitions
                quality_score *= 0.5
            
            # Turkish quality indicators
            turkish_indicators = ['için', 'ile', 'bir', 'bu', 'şu', 've', 'da', 'de']
            has_turkish = any(word in response.lower() for word in turkish_indicators)
            if has_turkish:
                quality_score *= 1.3
            
            # MEFAPEX context bonus
            if 'mefapex' in response.lower() or 'destek' in response.lower():
                quality_score *= 1.2
            
            # Coherence check (simple)
            if response.endswith(('.', '!', '?')):
                quality_score *= 1.1
            
            return min(quality_score, 1.0)
            
        except Exception as e:
            logger.warning(f"Quality assessment failed: {e}")
            return 0.5
    
    def _should_add_mefapex_context(self, response: str) -> bool:
        """Check if response should have MEFAPEX context added"""
        response_lower = response.lower()
        
        # Don't add if already has company context
        if any(word in response_lower for word in ['mefapex', 'şirket', 'company', 'destek']):
            return False
        
        # Add context for technical/business responses
        if any(word in response_lower for word in [
            'sistem', 'yazılım', 'teknik', 'proje', 'bilgi', 'hizmet', 'çözüm'
        ]):
            return True
        
        return False
    
    def _get_quality_fallback_response(self, message: str) -> str:
        """Get high-quality fallback response for poor AI responses"""
        # Try improved Turkish content manager first
        try:
            from improved_turkish_content_manager import improved_turkish_content
            fallback = improved_turkish_content._get_fallback_response(message)
            if fallback:
                return fallback
        except ImportError:
            pass
        
        # Default high-quality fallback
        return (
            f"🤖 **MEFAPEX AI Asistanı**\n\n"
            f"Sorduğunuz konuda size daha iyi yardımcı olabilmek için, "
            f"lütfen sorunuzu biraz daha detaylandırır mısınız?\n\n"
            f"**Size yardımcı olabileceğim konular:**\n"
            f"• 🏭 Çalışma saatleri ve operasyonlar\n"
            f"• 💻 Teknik destek ve IT sorunları\n"
            f"• 👥 İnsan kaynakları ve izin işlemleri\n"
            f"• 🛡️ Güvenlik kuralları ve prosedürler\n"
            f"• 🏢 Şirket bilgileri ve hizmetler\n\n"
            f"**Acil durumlar için:**\n"
            f"📞 Teknik Destek: destek@mefapex.com\n"
            f"📧 Genel Bilgi: info@mefapex.com"
        )
    
    def _force_gc(self):
        """CRITICAL FIX: Enhanced garbage collection and memory cleanup"""
        try:
            # CRITICAL FIX: Multiple GC passes for better cleanup
            import gc
            for i in range(3):  # Multiple passes
                gc.collect()
            
            # CRITICAL FIX: Clear PyTorch cache more aggressively
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()  # Wait for operations to complete
            
            # CRITICAL FIX: Clear MPS cache if available
            if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                try:
                    torch.mps.empty_cache()
                except AttributeError:
                    pass  # Older PyTorch versions
            
            # CRITICAL FIX: Force Python garbage collection with all generations
            if hasattr(gc, 'collect'):
                collected = gc.collect()
                if collected > 0:
                    logger.debug(f"🧹 Collected {collected} objects during cleanup")
                    
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
