"""
Thread-safe Model Manager for MEFAPEX AI Assistant
Implements singleton pattern with lazy loading and caching
"""
import threading
import logging
import torch
from sentence_transformers import SentenceTransformer
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
from typing import Optional, Dict, Any
import os
from functools import lru_cache

logger = logging.getLogger(__name__)

class ModelManager:
    """
    Thread-safe singleton model manager that ensures AI models are loaded only once
    and cached across all requests for optimal performance.
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
                    self._initialized = True
                    logger.info("🤖 ModelManager initialized")
    
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
                        model_name = os.getenv("SENTENCE_MODEL", "all-MiniLM-L6-v2")
                        self._sentence_model = SentenceTransformer(model_name)
                        
                        # Move to optimal device
                        if self.device != "cpu":
                            self._sentence_model = self._sentence_model.to(self.device)
                        
                        self._model_config['sentence_model'] = model_name
                        logger.info(f"✅ Sentence transformer loaded: {model_name}")
                        
                    except Exception as e:
                        logger.error(f"❌ Failed to load sentence transformer: {e}")
                        raise RuntimeError(f"Could not load sentence model: {e}")
        
        return self._sentence_model
    
    @property
    def text_generator(self) -> Optional[Any]:
        """
        Get text generation model with thread-safe lazy loading
        """
        if self._text_generator is None:
            with self._model_locks['text_generator']:
                if self._text_generator is None:
                    try:
                        model_name = os.getenv("HUGGINGFACE_MODEL", "microsoft/DialoGPT-small")
                        logger.info(f"🤖 Loading text generation model: {model_name}")
                        
                        # Configure device mapping
                        device_map = 0 if self.device == "cuda" else -1
                        
                        self._text_generator = pipeline(
                            "text-generation",
                            model=model_name,
                            tokenizer=model_name,
                            device=device_map,
                            max_length=150,
                            do_sample=True,
                            temperature=0.7,
                            pad_token_id=50256,
                            return_full_text=False,  # Only return generated part
                            clean_up_tokenization_spaces=True
                        )
                        
                        self._model_config['text_generator'] = model_name
                        logger.info(f"✅ Text generation model loaded: {model_name}")
                        
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to load text generation model: {e}")
                        self._text_generator = None
        
        return self._text_generator
    
    @lru_cache(maxsize=1000)
    def generate_embedding(self, text: str) -> list:
        """
        Generate embedding with caching for frequently used texts
        """
        try:
            # Normalize text for better cache hits
            normalized_text = text.strip().lower()
            embedding = self.sentence_model.encode([normalized_text])[0].tolist()
            return embedding
        except Exception as e:
            logger.error(f"Embedding generation failed for text: {text[:50]}... Error: {e}")
            raise
    
    def generate_text_response(self, prompt: str, max_length: int = 100) -> str:
        """
        Generate text response using cached model
        """
        try:
            if self.text_generator is None:
                raise RuntimeError("Text generator not available")
            
            # Generate response
            outputs = self.text_generator(
                prompt,
                max_length=max_length,
                num_return_sequences=1,
                temperature=0.8,
                do_sample=True,
                top_p=0.9,
                top_k=50,
                pad_token_id=self.text_generator.tokenizer.eos_token_id,
                eos_token_id=self.text_generator.tokenizer.eos_token_id,
                no_repeat_ngram_size=2,
                repetition_penalty=1.2
            )
            
            generated_text = outputs[0]['generated_text'].strip()
            return generated_text
            
        except Exception as e:
            logger.error(f"Text generation failed: {e}")
            raise
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about loaded models
        """
        return {
            "sentence_model_loaded": self._sentence_model is not None,
            "text_generator_loaded": self._text_generator is not None,
            "device": self.device,
            "model_config": self._model_config,
            "cache_info": {
                "embedding_cache_size": self.generate_embedding.cache_info().currsize,
                "embedding_cache_hits": self.generate_embedding.cache_info().hits,
                "embedding_cache_misses": self.generate_embedding.cache_info().misses
            }
        }
    
    def clear_caches(self):
        """
        Clear all model caches
        """
        self.generate_embedding.cache_clear()
        logger.info("🧹 Model caches cleared")
    
    def warmup_models(self):
        """
        Warm up models with sample data for faster first requests
        """
        try:
            logger.info("🔥 Warming up models...")
            
            # Warm up sentence model
            sample_text = "Hello, this is a test message"
            _ = self.generate_embedding(sample_text)
            
            # Warm up text generator
            if self.text_generator is not None:
                sample_prompt = "Hello"
                _ = self.generate_text_response(sample_prompt, max_length=20)
            
            logger.info("✅ Model warmup completed")
            
        except Exception as e:
            logger.warning(f"⚠️ Model warmup failed: {e}")

# Global instance
model_manager = ModelManager()
