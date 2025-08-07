"""
🚀 Async AI Model Manager with Thread Pool Execution
Prevents blocking of async event loop during AI inference
"""

import asyncio
import threading
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional, Callable
from functools import lru_cache
from cachetools import TTLCache
import time
import numpy as np
from dataclasses import dataclass
import psutil
import gc

logger = logging.getLogger(__name__)

@dataclass
class ModelStats:
    """AI Model performance statistics"""
    total_requests: int = 0
    total_inference_time: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    current_memory_mb: float = 0.0
    peak_memory_mb: float = 0.0

class AsyncModelManager:
    """
    🧠 High-performance async AI model manager
    - Non-blocking AI inference via thread pool
    - TTL-based caching to prevent memory leaks
    - Memory monitoring and cleanup
    - Concurrent request handling
    """
    
    def __init__(self, max_workers: int = 2):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="AIModel"
        )
        
        # TTL caches to prevent memory leaks
        self._embedding_cache = TTLCache(maxsize=500, ttl=1800)  # 30 min TTL
        self._response_cache = TTLCache(maxsize=200, ttl=900)    # 15 min TTL
        self._cache_lock = threading.RLock()
        
        # Model instances (loaded lazily)
        self._sentence_model = None
        self._text_generator = None
        self._model_loading_lock = threading.Lock()
        
        # Performance tracking
        self._stats = ModelStats()
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # 5 minutes
        
        # Memory monitoring
        self._memory_threshold_mb = 2000  # 2GB warning threshold
        
        logger.info(f"🧠 AsyncModelManager initialized with {max_workers} workers")
    
    def _get_sentence_model(self):
        """Lazy loading of sentence transformer model"""
        if self._sentence_model is None:
            with self._model_loading_lock:
                if self._sentence_model is None:  # Double-check locking
                    try:
                        from sentence_transformers import SentenceTransformer
                        logger.info("📥 Loading sentence transformer model...")
                        self._sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
                        logger.info("✅ Sentence transformer model loaded")
                    except Exception as e:
                        logger.error(f"❌ Failed to load sentence transformer: {e}")
                        raise
        return self._sentence_model
    
    def _get_text_generator(self):
        """Lazy loading of text generation model"""
        if self._text_generator is None:
            with self._model_loading_lock:
                if self._text_generator is None:  # Double-check locking
                    try:
                        from transformers import pipeline
                        import os
                        
                        model_name = os.getenv("HUGGINGFACE_MODEL", "microsoft/DialoGPT-small")
                        logger.info(f"📥 Loading text generation model: {model_name}")
                        
                        self._text_generator = pipeline(
                            "text-generation",
                            model=model_name,
                            tokenizer=model_name,
                            device=-1,  # Use CPU to avoid GPU memory issues
                            model_kwargs={
                                "torch_dtype": "auto",
                                "low_cpu_mem_usage": True
                            }
                        )
                        logger.info("✅ Text generation model loaded")
                    except Exception as e:
                        logger.error(f"❌ Failed to load text generator: {e}")
                        raise
        return self._text_generator
    
    def _generate_embedding_sync(self, text: str) -> List[float]:
        """Synchronous embedding generation (runs in thread pool)"""
        try:
            start_time = time.time()
            
            # Check cache first
            with self._cache_lock:
                if text in self._embedding_cache:
                    self._stats.cache_hits += 1
                    return self._embedding_cache[text]
                self._stats.cache_misses += 1
            
            # Generate embedding
            model = self._get_sentence_model()
            embedding = model.encode([text])[0].tolist()
            
            # Cache result
            with self._cache_lock:
                self._embedding_cache[text] = embedding
            
            # Update stats
            inference_time = time.time() - start_time
            self._stats.total_requests += 1
            self._stats.total_inference_time += inference_time
            
            return embedding
            
        except Exception as e:
            logger.error(f"❌ Embedding generation error: {e}")
            raise
    
    def _generate_text_sync(self, prompt: str, max_length: int = 100) -> str:
        """Synchronous text generation (runs in thread pool)"""
        try:
            start_time = time.time()
            
            # Check cache first
            cache_key = f"{prompt[:50]}_{max_length}"
            with self._cache_lock:
                if cache_key in self._response_cache:
                    self._stats.cache_hits += 1
                    return self._response_cache[cache_key]
                self._stats.cache_misses += 1
            
            # Generate text
            generator = self._get_text_generator()
            
            outputs = generator(
                prompt,
                max_length=max_length,
                num_return_sequences=1,
                temperature=0.7,
                do_sample=True,
                pad_token_id=generator.tokenizer.eos_token_id,
                return_full_text=False
            )
            
            generated_text = outputs[0]['generated_text'].strip()
            
            # Cache result
            with self._cache_lock:
                self._response_cache[cache_key] = generated_text
            
            # Update stats
            inference_time = time.time() - start_time
            self._stats.total_requests += 1
            self._stats.total_inference_time += inference_time
            
            return generated_text
            
        except Exception as e:
            logger.error(f"❌ Text generation error: {e}")
            raise
    
    async def generate_embedding_async(self, text: str) -> List[float]:
        """
        🔮 Generate text embedding asynchronously
        Runs in thread pool to avoid blocking event loop
        """
        try:
            # Check memory before heavy operation
            await self._check_memory_usage()
            
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                self.executor,
                self._generate_embedding_sync,
                text
            )
            
            # Periodic cleanup
            await self._periodic_cleanup()
            
            return embedding
            
        except Exception as e:
            logger.error(f"❌ Async embedding generation failed: {e}")
            raise
    
    async def generate_text_async(self, prompt: str, max_length: int = 100) -> str:
        """
        📝 Generate text response asynchronously
        Runs in thread pool to avoid blocking event loop
        """
        try:
            # Check memory before heavy operation
            await self._check_memory_usage()
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self.executor,
                self._generate_text_sync,
                prompt,
                max_length
            )
            
            # Periodic cleanup
            await self._periodic_cleanup()
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Async text generation failed: {e}")
            raise
    
    async def generate_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        📦 Generate multiple embeddings concurrently
        """
        try:
            await self._check_memory_usage()
            
            # Create tasks for concurrent execution
            tasks = [
                self.generate_embedding_async(text) 
                for text in texts
            ]
            
            # Execute with controlled concurrency
            semaphore = asyncio.Semaphore(self.max_workers)
            
            async def bounded_task(task):
                async with semaphore:
                    return await task
            
            bounded_tasks = [bounded_task(task) for task in tasks]
            results = await asyncio.gather(*bounded_tasks, return_exceptions=True)
            
            # Filter out exceptions
            embeddings = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"❌ Batch embedding failed for text {i}: {result}")
                    embeddings.append([])  # Empty embedding for failed cases
                else:
                    embeddings.append(result)
            
            return embeddings
            
        except Exception as e:
            logger.error(f"❌ Batch embedding generation failed: {e}")
            raise
    
    async def _check_memory_usage(self):
        """
        🧠 Monitor memory usage and trigger cleanup if needed
        """
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            current_memory_mb = memory_info.rss / 1024 / 1024
            
            self._stats.current_memory_mb = current_memory_mb
            if current_memory_mb > self._stats.peak_memory_mb:
                self._stats.peak_memory_mb = current_memory_mb
            
            # Trigger cleanup if memory usage is high
            if current_memory_mb > self._memory_threshold_mb:
                logger.warning(f"⚠️ High memory usage: {current_memory_mb:.1f}MB, triggering cleanup...")
                await self._force_cleanup()
                
        except Exception as e:
            logger.error(f"❌ Memory monitoring error: {e}")
    
    async def _periodic_cleanup(self):
        """
        🧹 Periodic cache and memory cleanup
        """
        current_time = time.time()
        if current_time - self._last_cleanup > self._cleanup_interval:
            await self._force_cleanup()
            self._last_cleanup = current_time
    
    async def _force_cleanup(self):
        """
        🧹 Force cache cleanup and garbage collection
        """
        try:
            with self._cache_lock:
                # Clear expired cache entries
                self._embedding_cache.expire()
                self._response_cache.expire()
                
                # If still too much memory, clear more aggressively
                if self._stats.current_memory_mb > self._memory_threshold_mb:
                    cache_size_before = len(self._embedding_cache) + len(self._response_cache)
                    
                    # Clear 25% of oldest entries
                    embedding_to_clear = max(1, len(self._embedding_cache) // 4)
                    response_to_clear = max(1, len(self._response_cache) // 4)
                    
                    # Clear oldest entries (TTLCache doesn't have direct access to timestamps,
                    # so we'll clear some random entries)
                    for _ in range(embedding_to_clear):
                        if self._embedding_cache:
                            self._embedding_cache.popitem()
                    
                    for _ in range(response_to_clear):
                        if self._response_cache:
                            self._response_cache.popitem()
                    
                    cache_size_after = len(self._embedding_cache) + len(self._response_cache)
                    logger.info(f"🧹 Aggressive cleanup: {cache_size_before} → {cache_size_after} cache entries")
            
            # Force garbage collection
            gc.collect()
            
            # Update memory stats after cleanup
            await self._check_memory_usage()
            
        except Exception as e:
            logger.error(f"❌ Cleanup error: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        📊 Get model performance statistics
        """
        with self._cache_lock:
            cache_hit_rate = (
                self._stats.cache_hits / max(self._stats.cache_hits + self._stats.cache_misses, 1) * 100
            )
            
            avg_inference_time = (
                self._stats.total_inference_time / max(self._stats.total_requests, 1)
            )
        
        return {
            "total_requests": self._stats.total_requests,
            "cache_hit_rate_percent": round(cache_hit_rate, 2),
            "average_inference_time_ms": round(avg_inference_time * 1000, 2),
            "current_memory_mb": round(self._stats.current_memory_mb, 2),
            "peak_memory_mb": round(self._stats.peak_memory_mb, 2),
            "cache_sizes": {
                "embeddings": len(self._embedding_cache),
                "responses": len(self._response_cache)
            },
            "models_loaded": {
                "sentence_transformer": self._sentence_model is not None,
                "text_generator": self._text_generator is not None
            },
            "thread_pool": {
                "max_workers": self.max_workers,
                "active_threads": self.executor._threads.__len__() if hasattr(self.executor, '_threads') else 0
            }
        }
    
    async def warmup_models(self):
        """
        🔥 Warm up models for better first-request performance
        """
        logger.info("🔥 Starting async model warmup...")
        
        try:
            # Warm up with simple requests
            warmup_tasks = [
                self.generate_embedding_async("Hello world"),
                self.generate_text_async("Hello", max_length=20)
            ]
            
            results = await asyncio.gather(*warmup_tasks, return_exceptions=True)
            
            success_count = sum(1 for r in results if not isinstance(r, Exception))
            logger.info(f"✅ Model warmup completed: {success_count}/{len(warmup_tasks)} models ready")
            
        except Exception as e:
            logger.warning(f"⚠️ Model warmup failed: {e}")
    
    async def clear_caches(self):
        """
        🗑️ Clear all caches
        """
        with self._cache_lock:
            self._embedding_cache.clear()
            self._response_cache.clear()
        
        # Reset stats
        self._stats.cache_hits = 0
        self._stats.cache_misses = 0
        
        logger.info("🗑️ All model caches cleared")
    
    async def shutdown(self):
        """
        🔐 Shutdown model manager and cleanup resources
        """
        logger.info("🔐 Shutting down AsyncModelManager...")
        
        # Clear caches
        await self.clear_caches()
        
        # Shutdown thread pool
        self.executor.shutdown(wait=True, cancel_futures=True)
        
        # Clear model references
        self._sentence_model = None
        self._text_generator = None
        
        # Force garbage collection
        gc.collect()
        
        logger.info("✅ AsyncModelManager shutdown complete")

# Global instance
async_model_manager = AsyncModelManager()

# Compatibility functions for existing code
async def generate_embedding(text: str) -> List[float]:
    """Generate embedding using async model manager"""
    return await async_model_manager.generate_embedding_async(text)

async def generate_text_response(prompt: str, max_length: int = 100) -> str:
    """Generate text response using async model manager"""
    return await async_model_manager.generate_text_async(prompt, max_length)
