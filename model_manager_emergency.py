"""
🧠 MEFAPEX Emergency Memory-Optimized Model Manager
===================================================
Critical memory leak fixes applied - optimized for 5.35MB/min leak issue

CRITICAL FIXES:
✅ Aggressive lazy loading (models load only when needed)
✅ Automatic model unloading after idle time
✅ Reduced cache sizes by 80%
✅ Memory-safe embedding generation
✅ Emergency mode support
✅ Enhanced garbage collection
"""

import threading
import logging
import gc
import torch
import time
import weakref
import os
from functools import wraps
from typing import Optional, Dict, Any, Union, Callable
from sentence_transformers import SentenceTransformer
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
import atexit
from enum import Enum

logger = logging.getLogger(__name__)

# Emergency mode check
EMERGENCY_MODE = os.getenv('EMERGENCY_MODE', 'false').lower() == 'true'
DISABLE_AI_MODELS = os.getenv('DISABLE_AI_MODELS', 'false').lower() == 'true'

class ModelType(Enum):
    """Model types for lazy loading management"""
    TURKISH_SENTENCE = "turkish_sentence"
    ENGLISH_SENTENCE = "english_sentence"
    TEXT_GENERATOR = "text_generator"

class MemoryTracker:
    """Simplified memory tracking for emergency mode"""
    
    def __init__(self):
        self.load_times = {}
        self.memory_usage = {}
        self.last_access = {}
        
    def record_load(self, model_type: str, load_time: float, memory_mb: float):
        self.load_times[model_type] = load_time
        self.last_access[model_type] = time.time()
        self.memory_usage[model_type] = memory_mb
        
    def record_access(self, model_type: str):
        self.last_access[model_type] = time.time()
        
    def get_idle_models(self, max_idle_seconds: int = 300) -> list:
        """Get models that have been idle for too long"""
        current_time = time.time()
        idle_models = []
        
        for model_type, last_time in self.last_access.items():
            if current_time - last_time > max_idle_seconds:
                idle_models.append(model_type)
        
        return idle_models

def memory_safe_lazy_load(model_type: ModelType):
    """Memory-safe lazy loading decorator with emergency mode support"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Emergency mode - return None for all models
            if EMERGENCY_MODE or DISABLE_AI_MODELS:
                logger.warning(f"🚨 Emergency mode active - {model_type.value} model disabled")
                return None
            
            # Track access
            if hasattr(self, '_memory_tracker'):
                self._memory_tracker.record_access(model_type.value)
            
            # Check if model is already loaded
            attr_name = f"_{model_type.value.replace('_', '_')}_model"
            model = getattr(self, attr_name, None)
            
            if model is not None:
                return model
            
            # Memory check before loading
            if hasattr(self, '_check_memory_before_load'):
                if not self._check_memory_before_load():
                    logger.warning(f"🚨 Memory threshold exceeded - cannot load {model_type.value}")
                    return None
            
            # Load model with memory tracking
            start_time = time.time()
            start_memory = self._get_memory_usage()
            
            logger.info(f"🔄 Emergency lazy loading {model_type.value} model...")
            
            try:
                # Force cleanup before loading
                self._aggressive_cleanup()
                
                # Call the original loading function
                model = func(self, *args, **kwargs)
                
                if model is None:
                    return None
                
                # Record performance metrics
                load_time = time.time() - start_time
                memory_used = self._get_memory_usage() - start_memory
                
                if hasattr(self, '_memory_tracker'):
                    self._memory_tracker.record_load(model_type.value, load_time, memory_used)
                
                logger.info(f"✅ {model_type.value} loaded: {load_time:.2f}s, {memory_used:.1f}MB")
                
                # Store the loaded model
                setattr(self, attr_name, model)
                
                # Schedule auto-unload
                self._schedule_auto_unload(model_type.value)
                
                return model
                
            except Exception as e:
                logger.error(f"❌ Failed to load {model_type.value}: {e}")
                # Force cleanup on error
                self._aggressive_cleanup()
                return None
        
        return wrapper
    return decorator

def memory_safe_cache(maxsize: int = 25):
    """Memory-safe cache with aggressive cleanup"""
    def decorator(func):
        cache = {}
        access_times = {}
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Emergency mode - no caching
            if EMERGENCY_MODE:
                return func(*args, **kwargs)
            
            # Create cache key (simplified)
            key = str(hash((str(args), str(kwargs))))[:32]  # Limit key length
            
            # Check cache
            if key in cache:
                access_times[key] = time.time()
                return cache[key]
            
            # Compute result
            result = func(*args, **kwargs)
            
            # Store in cache if space available
            if len(cache) < maxsize:
                cache[key] = result
                access_times[key] = time.time()
            elif len(cache) >= maxsize:
                # Evict oldest entry
                if access_times:
                    oldest_key = min(access_times.keys(), key=lambda k: access_times[k])
                    cache.pop(oldest_key, None)
                    access_times.pop(oldest_key, None)
                    cache[key] = result
                    access_times[key] = time.time()
            
            # Periodic cleanup
            if len(cache) % 10 == 0:
                wrapper.cache_clear()
            
            return result
        
        def cache_clear():
            cache.clear()
            access_times.clear()
            gc.collect()
        
        wrapper.cache_clear = cache_clear
        wrapper.cache_info = lambda: {'size': len(cache), 'maxsize': maxsize}
        
        return wrapper
    return decorator

class EmergencyModelManager:
    """
    🚨 Emergency Memory-Optimized Model Manager
    ==========================================
    
    CRITICAL MEMORY LEAK FIXES:
    - Aggressive lazy loading
    - Auto-unload idle models
    - Reduced cache sizes (80% reduction)
    - Emergency mode support
    - Memory threshold monitoring
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(EmergencyModelManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    # NO MODEL LOADING - PURE LAZY LOADING
                    self._english_sentence_model = None
                    self._turkish_sentence_model = None
                    self._text_generator_model = None
                    self._device = None
                    
                    # Memory management
                    self._memory_tracker = MemoryTracker()
                    self._memory_threshold_mb = float(os.getenv('MEMORY_THRESHOLD_MB', '2048'))
                    self._auto_unload_enabled = True
                    self._auto_unload_timeout = 120  # 5 minutes
                    
                    # Cache settings
                    self._cache_size = int(os.getenv('MODEL_CACHE_SIZE', '5'))
                    self._embedding_cache_size = int(os.getenv('LRU_CACHE_SIZE', '5'))
                    
                    # Emergency settings
                    self._emergency_mode = EMERGENCY_MODE
                    self._models_disabled = DISABLE_AI_MODELS
                    
                    # Model paths
                    self._cache_dir = os.path.join(os.getcwd(), "models_cache")
                    os.makedirs(self._cache_dir, exist_ok=True)
                    
                    # Register cleanup
                    atexit.register(self.emergency_cleanup)
                    
                    self._initialized = True
                    
                    if self._emergency_mode:
                        logger.warning("🚨 EMERGENCY MODE: Model Manager started in safe mode")
                    else:
                        logger.info("🧠 Emergency Model Manager initialized - aggressive memory optimization")
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return 0.0
    
    def _check_memory_before_load(self) -> bool:
        """Check if we can safely load a model"""
        current_memory = self._get_memory_usage()
        
        if current_memory > self._memory_threshold_mb:
            logger.warning(f"🚨 Memory threshold exceeded: {current_memory:.1f}MB > {self._memory_threshold_mb}MB")
            # Try emergency cleanup first
            self._aggressive_cleanup()
            
            # Check again
            current_memory = self._get_memory_usage()
            if current_memory > self._memory_threshold_mb:
                return False
        
        return True
    
    def _aggressive_cleanup(self):
        """Aggressive memory cleanup"""
        try:
            # Unload idle models
            idle_models = self._memory_tracker.get_idle_models(180)  # 3 minutes
            for model_type in idle_models:
                self._unload_model(model_type)
            
            # Force garbage collection
            for _ in range(3):
                gc.collect()
            
            # Clear torch cache if available
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            logger.debug("🧹 Aggressive cleanup completed")
            
        except Exception as e:
            logger.warning(f"Aggressive cleanup failed: {e}")
    
    def _unload_model(self, model_type: str):
        """Unload a specific model"""
        attr_name = f"_{model_type.replace('_', '_')}_model"
        if hasattr(self, attr_name):
            model = getattr(self, attr_name)
            if model is not None:
                del model
                setattr(self, attr_name, None)
                logger.info(f"🗑️ Unloaded model: {model_type}")
    
    def _schedule_auto_unload(self, model_type: str):
        """Schedule automatic model unloading"""
        if not self._auto_unload_enabled:
            return
        
        def unload_after_timeout():
            time.sleep(self._auto_unload_timeout)
            # Check if model is still idle
            idle_models = self._memory_tracker.get_idle_models(self._auto_unload_timeout - 10)
            if model_type in idle_models:
                self._unload_model(model_type)
        
        threading.Thread(target=unload_after_timeout, daemon=True).start()
    
    @property
    def device(self) -> str:
        """Get optimal device for model inference"""
        if self._device is None:
            if EMERGENCY_MODE:
                self._device = "cpu"  # Force CPU in emergency mode
            elif torch.backends.mps.is_available():
                self._device = "mps"
            elif torch.cuda.is_available():
                self._device = "cuda"
            else:
                self._device = "cpu"
            logger.info(f"🖥️ Device: {self._device}")
        return self._device
    
    @property
    @memory_safe_lazy_load(ModelType.TURKISH_SENTENCE)
    def turkish_sentence_model(self) -> Optional[SentenceTransformer]:
        """Emergency lazy-loaded Turkish sentence transformer"""
        try:
            logger.info("📚 Emergency loading Turkish sentence model...")
            
            # Use lightweight model in emergency mode
            model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
            
            model = SentenceTransformer(
                model_name,
                device=self.device if self.device != "mps" else "cpu",
                cache_folder=self._cache_dir
            )
            
            model.eval()
            return model
            
        except Exception as e:
            logger.error(f"❌ Turkish model loading failed: {e}")
            return None
    
    @property
    @memory_safe_lazy_load(ModelType.ENGLISH_SENTENCE)
    def english_sentence_model(self) -> Optional[SentenceTransformer]:
        """Emergency lazy-loaded English sentence transformer"""
        try:
            logger.info("📚 Emergency loading English sentence model...")
            
            model_name = "sentence-transformers/all-MiniLM-L6-v2"
            
            model = SentenceTransformer(
                model_name,
                device=self.device if self.device != "mps" else "cpu",
                cache_folder=self._cache_dir
            )
            
            model.eval()
            return model
            
        except Exception as e:
            logger.error(f"❌ English model loading failed: {e}")
            return None
    
    @property
    @memory_safe_lazy_load(ModelType.TEXT_GENERATOR)
    def text_generator(self) -> Optional[Any]:
        """Emergency lazy-loaded text generator (disabled in emergency mode)"""
        if EMERGENCY_MODE:
            logger.warning("🚨 Text generator disabled in emergency mode")
            return None
        
        try:
            logger.info("🤖 Emergency loading text generator...")
            
            # Use smaller model for memory efficiency
            model_name = "microsoft/DialoGPT-small"  # Smaller version
            
            tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=self._cache_dir)
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token
            
            model = AutoModelForCausalLM.from_pretrained(
                model_name,
                cache_dir=self._cache_dir,
                torch_dtype=torch.float32,  # Use float32 for stability
                low_cpu_mem_usage=True
            )
            
            model = model.to(self.device if self.device != "mps" else "cpu")
            
            text_generator = pipeline(
                "text-generation",
                model=model,
                tokenizer=tokenizer,
                device=0 if self.device == "cuda" else -1,
                max_length=50,  # Reduced for memory
                do_sample=True,
                temperature=0.7,
                return_full_text=False
            )
            
            return text_generator
            
        except Exception as e:
            logger.warning(f"⚠️ Text generator loading failed: {e}")
            return None
    
    @memory_safe_cache(maxsize=5)  # Reduced from 50
    def generate_embedding(self, text: str, force_turkish: bool = None) -> Optional[list]:
        """Memory-optimized embedding generation"""
        try:
            if EMERGENCY_MODE:
                logger.warning("🚨 Embedding generation disabled in emergency mode")
                return None
            
            # Limit text length aggressively
            text = text.strip()[:200]  # Max 200 chars in emergency mode
            
            if not text:
                return None
            
            # Choose model (prefer lightweight)
            if force_turkish or (force_turkish is None and self._detect_turkish(text)):
                model = self.turkish_sentence_model
                if model is None:
                    model = self.english_sentence_model  # Fallback
            else:
                model = self.english_sentence_model
            
            if model is None:
                logger.warning("🚨 No embedding model available")
                return None
            
            # Generate embedding with memory optimization
            with torch.no_grad():
                embedding = model.encode(
                    [text], 
                    convert_to_tensor=False,
                    show_progress_bar=False,
                    batch_size=1
                )[0]
            
            # Convert to list and limit precision
            if hasattr(embedding, 'tolist'):
                result = [round(float(x), 6) for x in embedding.tolist()]
            else:
                result = [round(float(x), 6) for x in embedding]
            
            # Periodic cleanup
            if hasattr(self, '_embedding_count'):
                self._embedding_count += 1
            else:
                self._embedding_count = 1
            
            if self._embedding_count % 5 == 0:  # More frequent cleanup
                self._aggressive_cleanup()
            
            return result
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return None
    
    def _detect_turkish(self, text: str) -> bool:
        """Simple Turkish detection"""
        turkish_chars = set('çğıöşüÇĞIİÖŞÜ')
        return any(char in turkish_chars for char in text)
    
    def generate_text_response(self, prompt: str, max_length: int = 50) -> str:
        """Emergency text generation"""
        if EMERGENCY_MODE or self.text_generator is None:
            return "Sistem bakımda, lütfen daha sonra tekrar deneyin."
        
        try:
            prompt = prompt[:100]  # Limit prompt length
            
            with torch.no_grad():
                outputs = self.text_generator(
                    prompt,
                    max_length=max_length,
                    num_return_sequences=1,
                    temperature=0.7,
                    do_sample=True,
                    pad_token_id=self.text_generator.tokenizer.eos_token_id
                )
            
            return outputs[0]['generated_text'].strip()
            
        except Exception as e:
            logger.error(f"Text generation failed: {e}")
            return "Üzgünüm, şu anda size yardımcı olamıyorum."
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get emergency model information"""
        memory_info = {"memory_mb": self._get_memory_usage()}
        
        return {
            "emergency_mode": self._emergency_mode,
            "models_disabled": self._models_disabled,
            "memory_threshold_mb": self._memory_threshold_mb,
            "current_memory_mb": memory_info["memory_mb"],
            "turkish_model_loaded": self._turkish_sentence_model is not None,
            "english_model_loaded": self._english_sentence_model is not None,
            "text_generator_loaded": self._text_generator_model is not None,
            "auto_unload_enabled": self._auto_unload_enabled,
            "cache_size": self._cache_size
        }
    
    def emergency_cleanup(self):
        """Emergency cleanup of all resources"""
        try:
            logger.warning("🚨 EMERGENCY CLEANUP INITIATED")
            
            # Unload all models
            self._unload_model("turkish_sentence")
            self._unload_model("english_sentence") 
            self._unload_model("text_generator")
            
            # Clear caches
            if hasattr(self.generate_embedding, 'cache_clear'):
                self.generate_embedding.cache_clear()
            
            # Aggressive garbage collection
            for _ in range(5):
                gc.collect()
            
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            logger.warning("🚨 Emergency cleanup completed")
            
        except Exception as e:
            logger.error(f"Emergency cleanup failed: {e}")
    
    def enable_emergency_mode(self):
        """Enable emergency mode"""
        self._emergency_mode = True
        self._models_disabled = True
        os.environ['EMERGENCY_MODE'] = 'true'
        os.environ['DISABLE_AI_MODELS'] = 'true'
        
        logger.warning("🚨 EMERGENCY MODE ENABLED")
        self.emergency_cleanup()
    
    def disable_emergency_mode(self):
        """Disable emergency mode"""
        self._emergency_mode = False
        self._models_disabled = False
        os.environ['EMERGENCY_MODE'] = 'false'
        os.environ['DISABLE_AI_MODELS'] = 'false'
        
        logger.info("✅ Emergency mode disabled")

# Global instance
model_manager = EmergencyModelManager()

# For backward compatibility
ModelManager = EmergencyModelManager

logger.info("🚨 Emergency Model Manager loaded with critical memory leak fixes")
