"""
Enhanced Thread-safe Model Manager for MEFAPEX AI Assistant
Optimized for Turkish Language Support
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
import re

logger = logging.getLogger(__name__)

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
    Thread-safe singleton model manager with proper memory management,
    cleanup to prevent memory leaks, and Turkish language support.
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
                    self._turkish_sentence_model = None
                    self._text_generator = None
                    self._device = None
                    self._model_config = {}
                    self._model_locks = {
                        'sentence': threading.Lock(),
                        'turkish_sentence': threading.Lock(),
                        'text_generator': threading.Lock()
                    }
                    self._memory_monitor = True
                    self._max_cache_size = 100  # Reduced cache size from 500 to 100
                    self._initialized = True
                    self._language_detector = TurkishLanguageDetector()
                    
                    # Model cache directory for persistence
                    self._cache_dir = os.path.join(os.getcwd(), "models_cache")
                    os.makedirs(self._cache_dir, exist_ok=True)
                    
                    # Register cleanup on exit
                    atexit.register(self.cleanup_resources)
                    
                    logger.info("🤖 Enhanced ModelManager initialized with Turkish language support")
    
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
        Automatically chooses Turkish or multilingual model based on configuration
        """
        config = get_config().ai
        
        # Determine which model to use
        if config.prefer_turkish_models:
            return self.turkish_sentence_model
        else:
            return self.english_sentence_model
    
    @property
    def turkish_sentence_model(self) -> SentenceTransformer:
        """
        Get Turkish-optimized sentence transformer model with thread-safe lazy loading
        """
        if self._turkish_sentence_model is None:
            with self._model_locks['turkish_sentence']:
                if self._turkish_sentence_model is None:
                    try:
                        logger.info("📚 Loading Turkish sentence transformer model...")
                        config = get_config().ai
                        model_name = config.turkish_sentence_model
                        
                        # Force garbage collection before loading
                        self._force_gc()
                        
                        # Load Turkish-optimized model with reduced memory footprint
                        self._turkish_sentence_model = SentenceTransformer(
                            model_name,
                            device=self.device if self.device != "mps" else "cpu"  # MPS fix
                        )
                        
                        # Optimize model for inference
                        self._turkish_sentence_model.eval()  # Set to evaluation mode
                        
                        self._model_config['turkish_sentence_model'] = model_name
                        logger.info(f"✅ Turkish sentence transformer loaded: {model_name}")
                        
                        # Force garbage collection after model loading
                        self._force_gc()
                        
                    except Exception as e:
                        logger.error(f"❌ Failed to load Turkish sentence transformer: {e}")
                        logger.warning("🔄 Falling back to multilingual model...")
                        # Fallback to multilingual model
                        try:
                            self._turkish_sentence_model = SentenceTransformer(
                                "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                                device=self.device if self.device != "mps" else "cpu"
                            )
                            self._turkish_sentence_model.eval()
                            logger.info("✅ Multilingual fallback model loaded")
                        except Exception as fallback_e:
                            logger.error(f"❌ Fallback model also failed: {fallback_e}")
                            raise RuntimeError(f"Could not load any sentence model: {e}")
        
        return self._turkish_sentence_model
    
    @property
    def english_sentence_model(self) -> SentenceTransformer:
        """
        Get English sentence transformer model (fallback) with thread-safe lazy loading
        """
        if self._sentence_model is None:
            with self._model_locks['sentence']:
                if self._sentence_model is None:
                    try:
                        logger.info("📚 Loading English sentence transformer model...")
                        config = get_config().ai
                        model_name = config.english_fallback_model
                        
                        # Force garbage collection before loading
                        self._force_gc()
                        
                        # Load with reduced memory footprint
                        self._sentence_model = SentenceTransformer(
                            model_name,
                            device=self.device if self.device != "mps" else "cpu"  # MPS fix
                        )
                        
                        # Optimize model for inference
                        self._sentence_model.eval()  # Set to evaluation mode
                        
                        self._model_config['sentence_model'] = model_name
                        logger.info(f"✅ English sentence transformer loaded: {model_name}")
                        
                        # Force garbage collection after model loading
                        self._force_gc()
                        
                    except Exception as e:
                        logger.error(f"❌ Failed to load English sentence transformer: {e}")
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

    @lru_cache(maxsize=100)  # Further reduced cache size for memory efficiency
    def generate_embedding(self, text: str, force_turkish: bool = None) -> list:
        """
        Generate embedding with Turkish language support and reduced caching for memory efficiency
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
            
            # Choose appropriate model
            if use_turkish_model:
                logger.debug(f"🇹🇷 Using Turkish model for: {normalized_text[:30]}...")
                model = self.turkish_sentence_model
            else:
                logger.debug(f"🇺🇸 Using English model for: {normalized_text[:30]}...")
                model = self.english_sentence_model
            
            with torch.no_grad():  # Prevent gradient accumulation
                embedding = model.encode(
                    [normalized_text], 
                    convert_to_tensor=False,  # Return numpy array
                    show_progress_bar=False
                )[0].tolist()
            
            # Force garbage collection periodically
            if hasattr(self, '_embedding_counter'):
                self._embedding_counter += 1
            else:
                self._embedding_counter = 1
                
            if self._embedding_counter % 50 == 0:  # Every 50 embeddings
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
            # Periodic garbage collection
            if self.generate_embedding.cache_info().currsize % 50 == 0:
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
            "turkish_sentence_model_loaded": self._turkish_sentence_model is not None,
            "text_generator_loaded": self._text_generator is not None,
            "device": self.device,
            "model_config": self._model_config,
            "memory_info": memory_info,
            "language_detection_enabled": get_config().ai.language_detection,
            "prefer_turkish_models": get_config().ai.prefer_turkish_models,
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
                
            if self._turkish_sentence_model is not None:
                del self._turkish_sentence_model
                self._turkish_sentence_model = None
                
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
            
            # Warm up Turkish sentence model with Turkish text
            turkish_sample = "Merhaba test"
            _ = self.generate_embedding(turkish_sample, force_turkish=True)
            
            # Warm up English sentence model with English text
            english_sample = "Hello test"
            _ = self.generate_embedding(english_sample, force_turkish=False)
            
            # Warm up text generator with Turkish prompt
            if self.text_generator is not None:
                turkish_prompt = "Merhaba"
                _ = self.generate_text_response(turkish_prompt, max_length=20, turkish_context=True)
            
            logger.info("✅ Model warmup completed")
            
        except Exception as e:
            logger.warning(f"⚠️ Model warmup failed: {e}")
    
    def detect_language(self, text: str) -> str:
        """
        Detect language of given text
        Returns: 'turkish' or 'other'
        """
        if self._language_detector.is_turkish(text):
            return 'turkish'
        return 'other'
    
    def get_embedding_model_for_text(self, text: str) -> SentenceTransformer:
        """
        Get the most appropriate embedding model for the given text
        """
        config = get_config().ai
        
        if config.language_detection and self._language_detector.is_turkish(text):
            return self.turkish_sentence_model
        elif config.prefer_turkish_models:
            return self.turkish_sentence_model
        else:
            return self.english_sentence_model

# Global instance
model_manager = ModelManager()
