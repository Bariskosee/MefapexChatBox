"""
🤖 AI Service
Optimized AI response generation with lazy loading and caching
"""

import logging
import asyncio
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class LazyAIService:
    """AI Service with lazy loading and intelligent caching"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Lazy loaded components
        self._openai_client = None
        self._huggingface_model = None
        self._embedding_model = None
        
        # Advanced caching
        self._response_cache = {}
        self._embedding_cache = {}
        self.cache_max_size = 200
        self.cache_ttl_hours = 24
        
        # Performance metrics
        self.metrics = {
            "cache_hits": 0,
            "cache_misses": 0,
            "model_loads": 0,
            "response_times": []
        }
        
        logger.info("🤖 LazyAIService initialized")
    
    @property
    def openai_client(self):
        """Lazy load OpenAI client only when needed"""
        if self._openai_client is None and self.config.get('USE_OPENAI'):
            try:
                import openai
                self._openai_client = openai.OpenAI(
                    api_key=self.config.get('OPENAI_API_KEY'),
                    timeout=30.0  # Add timeout
                )
                self.metrics["model_loads"] += 1
                logger.info("✅ OpenAI client loaded lazily")
            except Exception as e:
                logger.error(f"Failed to load OpenAI client: {e}")
                self._openai_client = False  # Mark as failed
        return self._openai_client if self._openai_client is not False else None
    
    @property
    def huggingface_model(self):
        """Lazy load HuggingFace model only when needed"""
        if self._huggingface_model is None and self.config.get('USE_HUGGINGFACE'):
            try:
                from transformers import pipeline
                self._huggingface_model = pipeline(
                    "text-generation",
                    model="microsoft/DialoGPT-small",
                    device=-1,  # CPU
                    model_kwargs={"cache_dir": "./models_cache"}
                )
                self.metrics["model_loads"] += 1
                logger.info("✅ HuggingFace model loaded lazily")
            except Exception as e:
                logger.error(f"Failed to load HuggingFace model: {e}")
                self._huggingface_model = False  # Mark as failed
        return self._huggingface_model if self._huggingface_model is not False else None
    
    @property
    def embedding_model(self):
        """Lazy load embedding model only when needed"""
        if self._embedding_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._embedding_model = SentenceTransformer(
                    'all-MiniLM-L6-v2',
                    cache_folder='./models_cache'
                )
                self.metrics["model_loads"] += 1
                logger.info("✅ Embedding model loaded lazily")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")
                self._embedding_model = False
        return self._embedding_model if self._embedding_model is not False else None
    
    def _generate_cache_key(self, text: str, model_type: str) -> str:
        """Generate cache key with model type"""
        return f"{model_type}:{hashlib.md5(text.lower().encode()).hexdigest()}"
    
    def _is_cache_valid(self, cache_entry: Dict) -> bool:
        """Check if cache entry is still valid"""
        if 'timestamp' not in cache_entry:
            return False
        
        cache_time = datetime.fromisoformat(cache_entry['timestamp'])
        expiry_time = cache_time + timedelta(hours=self.cache_ttl_hours)
        return datetime.now() < expiry_time
    
    def _get_cached_response(self, cache_key: str) -> Optional[str]:
        """Get cached response if valid"""
        if cache_key in self._response_cache:
            entry = self._response_cache[cache_key]
            if self._is_cache_valid(entry):
                self.metrics["cache_hits"] += 1
                logger.debug(f"Cache hit for key: {cache_key[:20]}...")
                return entry['response']
            else:
                # Remove expired entry
                del self._response_cache[cache_key]
        
        self.metrics["cache_misses"] += 1
        return None
    
    def _cache_response(self, cache_key: str, response: str):
        """Cache response with timestamp"""
        # Implement LRU eviction
        if len(self._response_cache) >= self.cache_max_size:
            # Remove oldest entries
            sorted_entries = sorted(
                self._response_cache.items(),
                key=lambda x: x[1].get('timestamp', '1970-01-01')
            )
            # Remove oldest 20% of entries
            remove_count = max(1, self.cache_max_size // 5)
            for i in range(remove_count):
                if i < len(sorted_entries):
                    del self._response_cache[sorted_entries[i][0]]
        
        self._response_cache[cache_key] = {
            'response': response,
            'timestamp': datetime.now().isoformat()
        }
    
    async def generate_embedding(self, text: str) -> Optional[list]:
        """Generate text embedding with caching"""
        try:
            start_time = datetime.now()
            
            # Check cache first
            cache_key = self._generate_cache_key(text, "embedding")
            if cache_key in self._embedding_cache:
                entry = self._embedding_cache[cache_key]
                if self._is_cache_valid(entry):
                    return entry['embedding']
            
            # Generate embedding
            if not self.embedding_model:
                logger.warning("Embedding model not available")
                return None
            
            embedding = await asyncio.to_thread(
                self.embedding_model.encode, [text]
            )
            
            result = embedding[0].tolist()
            
            # Cache result
            self._embedding_cache[cache_key] = {
                'embedding': result,
                'timestamp': datetime.now().isoformat()
            }
            
            # Track performance
            response_time = (datetime.now() - start_time).total_seconds()
            self.metrics["response_times"].append(response_time)
            
            return result
            
        except Exception as e:
            logger.error(f"Embedding generation error: {e}")
            return None
    
    async def generate_openai_response(self, context: str, query: str) -> str:
        """Generate OpenAI response with caching"""
        start_time = datetime.now()
        
        try:
            # Check cache
            cache_key = self._generate_cache_key(f"{context[:100]}|{query}", "openai")
            cached_response = self._get_cached_response(cache_key)
            if cached_response:
                return cached_response
            
            if not self.openai_client:
                raise Exception("OpenAI client not available")
            
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": context},
                    {"role": "user", "content": query}
                ],
                max_tokens=300,
                temperature=0.7,
                timeout=30
            )
            
            result = response.choices[0].message.content.strip()
            
            # Cache response
            self._cache_response(cache_key, result)
            
            # Track performance
            response_time = (datetime.now() - start_time).total_seconds()
            self.metrics["response_times"].append(response_time)
            
            return result
            
        except Exception as e:
            logger.error(f"OpenAI generation error: {e}")
            raise
    
    async def generate_huggingface_response(self, context: str, query: str) -> str:
        """Generate HuggingFace response with caching"""
        start_time = datetime.now()
        
        try:
            # Check cache
            cache_key = self._generate_cache_key(f"{context[:100]}|{query}", "huggingface")
            cached_response = self._get_cached_response(cache_key)
            if cached_response:
                return cached_response
            
            if not self.huggingface_model:
                raise Exception("HuggingFace model not available")
            
            prompt = f"{context[:200]}\nKullanıcı: {query}\nAsistan:"
            
            result = await asyncio.to_thread(
                self.huggingface_model,
                prompt,
                max_length=min(len(prompt) + 150, 512),  # Dynamic length
                num_return_sequences=1,
                temperature=0.7,
                do_sample=True,
                pad_token_id=50256  # Add padding token
            )
            
            response = result[0]['generated_text']
            
            # Extract assistant response
            if "Asistan:" in response:
                response = response.split("Asistan:")[-1].strip()
            
            # Clean up response
            response = response.replace(prompt, "").strip()
            if not response or len(response) < 10:
                response = "🤖 Anlayamadım. Lütfen sorunuzu daha açık bir şekilde sorar mısınız?"
            
            # Cache response
            self._cache_response(cache_key, response)
            
            # Track performance
            response_time = (datetime.now() - start_time).total_seconds()
            self.metrics["response_times"].append(response_time)
            
            return response
            
        except Exception as e:
            logger.error(f"HuggingFace generation error: {e}")
            raise
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        total_requests = self.metrics["cache_hits"] + self.metrics["cache_misses"]
        cache_hit_rate = (self.metrics["cache_hits"] / total_requests * 100) if total_requests > 0 else 0
        
        avg_response_time = 0
        if self.metrics["response_times"]:
            avg_response_time = sum(self.metrics["response_times"]) / len(self.metrics["response_times"])
        
        return {
            "cache_hit_rate": round(cache_hit_rate, 2),
            "total_requests": total_requests,
            "cache_size": len(self._response_cache),
            "embedding_cache_size": len(self._embedding_cache),
            "models_loaded": self.metrics["model_loads"],
            "avg_response_time": round(avg_response_time, 3),
            "active_models": {
                "openai": self._openai_client is not None and self._openai_client is not False,
                "huggingface": self._huggingface_model is not None and self._huggingface_model is not False,
                "embedding": self._embedding_model is not None and self._embedding_model is not False
            }
        }
    
    def clear_cache(self):
        """Clear all caches"""
        self._response_cache.clear()
        self._embedding_cache.clear()
        logger.info("🧹 AI service caches cleared")
    
    def warmup_models(self):
        """Warmup models by loading them"""
        logger.info("🔥 Warming up AI models...")
        
        # Load models in background
        if self.config.get('USE_OPENAI'):
            _ = self.openai_client
        
        if self.config.get('USE_HUGGINGFACE'):
            _ = self.huggingface_model
        
        _ = self.embedding_model
        
        logger.info(f"🔥 Model warmup completed. Loaded {self.metrics['model_loads']} models.")

# Global AI service instance
ai_service = None

def init_ai_service(config: Dict[str, Any] = None):
    """Initialize global AI service"""
    global ai_service
    ai_service = LazyAIService(config or {})
    return ai_service

def get_ai_service() -> LazyAIService:
    """Get global AI service instance"""
    global ai_service
    if ai_service is None:
        # Default configuration
        config = {
            'USE_OPENAI': False,
            'USE_HUGGINGFACE': True,
            'OPENAI_API_KEY': None
        }
        ai_service = LazyAIService(config)
    return ai_service
