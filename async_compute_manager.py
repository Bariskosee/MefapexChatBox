"""
⚡ Async CPU-Bound Operations Manager
Handles heavy computational tasks without blocking the event loop
"""

import asyncio
import numpy as np
import threading
import time
import logging
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from typing import List, Dict, Any, Tuple, Optional
from functools import lru_cache
import multiprocessing as mp
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ComputeStats:
    """CPU computation statistics"""
    total_operations: int = 0
    total_compute_time: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0

class AsyncComputeManager:
    """
    🖥️ High-performance async compute manager for CPU-bound operations
    - Process pool for CPU-intensive tasks
    - Thread pool for I/O-bound tasks
    - Efficient vector operations
    - Result caching
    """
    
    def __init__(self, max_processes: int = None, max_threads: int = 4):
        # Use optimal number of processes (CPU cores)
        self.max_processes = max_processes or max(1, mp.cpu_count() - 1)
        self.max_threads = max_threads
        
        # Executors for different types of operations
        self.process_executor = ProcessPoolExecutor(max_workers=self.max_processes)
        self.thread_executor = ThreadPoolExecutor(
            max_workers=max_threads,
            thread_name_prefix="AsyncCompute"
        )
        
        # Cache for computed results
        self._result_cache = {}
        self._cache_lock = threading.RLock()
        self._stats = ComputeStats()
        
        logger.info(f"⚡ AsyncComputeManager initialized: {self.max_processes} processes, {max_threads} threads")
    
    async def cosine_similarity_async(
        self, 
        vector_a: List[float], 
        vector_b: List[float]
    ) -> float:
        """
        📐 Compute cosine similarity asynchronously
        Uses optimized numpy operations in process pool
        """
        try:
            # Create cache key
            cache_key = f"cosine_{hash(tuple(vector_a))}_{hash(tuple(vector_b))}"
            
            # Check cache first
            with self._cache_lock:
                if cache_key in self._result_cache:
                    self._stats.cache_hits += 1
                    return self._result_cache[cache_key]
                self._stats.cache_misses += 1
            
            start_time = time.time()
            
            # Run in process pool for CPU-bound numpy operations
            loop = asyncio.get_event_loop()
            similarity = await loop.run_in_executor(
                self.process_executor,
                _compute_cosine_similarity,
                vector_a,
                vector_b
            )
            
            # Cache result
            with self._cache_lock:
                self._result_cache[cache_key] = similarity
                
                # Limit cache size
                if len(self._result_cache) > 1000:
                    # Remove oldest 20% of entries
                    keys_to_remove = list(self._result_cache.keys())[:200]
                    for key in keys_to_remove:
                        del self._result_cache[key]
            
            # Update stats
            compute_time = time.time() - start_time
            self._stats.total_operations += 1
            self._stats.total_compute_time += compute_time
            
            return similarity
            
        except Exception as e:
            logger.error(f"❌ Cosine similarity computation failed: {e}")
            raise
    
    async def batch_cosine_similarity_async(
        self, 
        query_vector: List[float], 
        vectors: List[List[float]]
    ) -> List[float]:
        """
        📦 Compute cosine similarities for multiple vectors in parallel
        """
        try:
            start_time = time.time()
            
            # Create tasks for parallel execution
            similarity_tasks = [
                self.cosine_similarity_async(query_vector, vector)
                for vector in vectors
            ]
            
            # Execute with controlled concurrency
            semaphore = asyncio.Semaphore(self.max_processes)
            
            async def bounded_task(task):
                async with semaphore:
                    return await task
            
            bounded_tasks = [bounded_task(task) for task in similarity_tasks]
            similarities = await asyncio.gather(*bounded_tasks, return_exceptions=True)
            
            # Handle exceptions
            results = []
            for i, similarity in enumerate(similarities):
                if isinstance(similarity, Exception):
                    logger.error(f"❌ Similarity computation failed for vector {i}: {similarity}")
                    results.append(0.0)  # Default similarity
                else:
                    results.append(similarity)
            
            compute_time = time.time() - start_time
            logger.info(f"⚡ Batch similarity computed: {len(vectors)} vectors in {compute_time:.3f}s")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Batch cosine similarity failed: {e}")
            raise
    
    async def text_processing_async(
        self, 
        text: str, 
        operations: List[str] = None
    ) -> Dict[str, Any]:
        """
        📝 Process text with heavy operations asynchronously
        Operations: 'lowercase', 'normalize', 'tokenize', 'clean'
        """
        try:
            if operations is None:
                operations = ['lowercase', 'normalize', 'clean']
            
            start_time = time.time()
            
            # Run in thread pool (text processing is more I/O bound)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.thread_executor,
                _process_text_heavy,
                text,
                operations
            )
            
            compute_time = time.time() - start_time
            self._stats.total_operations += 1
            self._stats.total_compute_time += compute_time
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Text processing failed: {e}")
            raise
    
    async def vector_operations_async(
        self, 
        vectors: List[List[float]], 
        operation: str = "normalize"
    ) -> List[List[float]]:
        """
        🔢 Perform vector operations asynchronously
        Operations: 'normalize', 'standardize', 'pca_reduce'
        """
        try:
            start_time = time.time()
            
            # Run in process pool for CPU-intensive numpy operations
            loop = asyncio.get_event_loop()
            processed_vectors = await loop.run_in_executor(
                self.process_executor,
                _process_vectors,
                vectors,
                operation
            )
            
            compute_time = time.time() - start_time
            self._stats.total_operations += 1
            self._stats.total_compute_time += compute_time
            
            logger.info(f"🔢 Vector operation '{operation}' completed: {len(vectors)} vectors in {compute_time:.3f}s")
            
            return processed_vectors
            
        except Exception as e:
            logger.error(f"❌ Vector operations failed: {e}")
            raise
    
    async def similarity_search_async(
        self, 
        query_vector: List[float], 
        database_vectors: List[List[float]], 
        top_k: int = 5
    ) -> List[Tuple[int, float]]:
        """
        🔍 Perform similarity search asynchronously
        Returns list of (index, similarity_score) tuples
        """
        try:
            start_time = time.time()
            
            # Compute similarities in parallel
            similarities = await self.batch_cosine_similarity_async(query_vector, database_vectors)
            
            # Sort and get top-k in thread pool
            loop = asyncio.get_event_loop()
            top_results = await loop.run_in_executor(
                self.thread_executor,
                _get_top_k_results,
                similarities,
                top_k
            )
            
            compute_time = time.time() - start_time
            logger.info(f"🔍 Similarity search completed: top-{top_k} from {len(database_vectors)} vectors in {compute_time:.3f}s")
            
            return top_results
            
        except Exception as e:
            logger.error(f"❌ Similarity search failed: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """
        📊 Get compute performance statistics
        """
        with self._cache_lock:
            cache_hit_rate = (
                self._stats.cache_hits / max(self._stats.cache_hits + self._stats.cache_misses, 1) * 100
            )
            
            avg_compute_time = (
                self._stats.total_compute_time / max(self._stats.total_operations, 1)
            )
        
        return {
            "total_operations": self._stats.total_operations,
            "cache_hit_rate_percent": round(cache_hit_rate, 2),
            "average_compute_time_ms": round(avg_compute_time * 1000, 2),
            "cache_size": len(self._result_cache),
            "executors": {
                "process_pool_workers": self.max_processes,
                "thread_pool_workers": self.max_threads
            }
        }
    
    async def clear_cache(self):
        """
        🗑️ Clear computation cache
        """
        with self._cache_lock:
            self._result_cache.clear()
        
        self._stats.cache_hits = 0
        self._stats.cache_misses = 0
        
        logger.info("🗑️ Compute cache cleared")
    
    async def shutdown(self):
        """
        🔐 Shutdown compute manager
        """
        logger.info("🔐 Shutting down AsyncComputeManager...")
        
        # Clear cache
        await self.clear_cache()
        
        # Shutdown executors
        self.process_executor.shutdown(wait=True, cancel_futures=True)
        self.thread_executor.shutdown(wait=True, cancel_futures=True)
        
        logger.info("✅ AsyncComputeManager shutdown complete")

# === Standalone functions for process pool execution ===

def _compute_cosine_similarity(vector_a: List[float], vector_b: List[float]) -> float:
    """
    Compute cosine similarity using optimized numpy operations
    This function runs in a separate process
    """
    try:
        a = np.array(vector_a, dtype=np.float32)
        b = np.array(vector_b, dtype=np.float32)
        
        # Optimized computation
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        similarity = dot_product / (norm_a * norm_b)
        return float(similarity)
        
    except Exception as e:
        logger.error(f"❌ Cosine similarity computation error: {e}")
        return 0.0

def _process_text_heavy(text: str, operations: List[str]) -> Dict[str, Any]:
    """
    Heavy text processing operations
    This function runs in a thread pool
    """
    try:
        import re
        import unicodedata
        
        result = {
            "original_length": len(text),
            "processed_text": text
        }
        
        processed = text
        
        if 'lowercase' in operations:
            processed = processed.lower()
        
        if 'normalize' in operations:
            # Unicode normalization
            processed = unicodedata.normalize('NFKD', processed)
        
        if 'clean' in operations:
            # Remove extra whitespace and special characters
            processed = re.sub(r'\s+', ' ', processed)
            processed = re.sub(r'[^\w\s\-.,!?]', '', processed)
            processed = processed.strip()
        
        if 'tokenize' in operations:
            # Simple tokenization
            tokens = processed.split()
            result["tokens"] = tokens
            result["token_count"] = len(tokens)
        
        result["processed_text"] = processed
        result["processed_length"] = len(processed)
        result["operations_applied"] = operations
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Text processing error: {e}")
        return {"error": str(e), "processed_text": text}

def _process_vectors(vectors: List[List[float]], operation: str) -> List[List[float]]:
    """
    Process vectors with CPU-intensive operations
    This function runs in a separate process
    """
    try:
        vectors_array = np.array(vectors, dtype=np.float32)
        
        if operation == 'normalize':
            # L2 normalization
            norms = np.linalg.norm(vectors_array, axis=1, keepdims=True)
            norms[norms == 0] = 1  # Avoid division by zero
            processed = vectors_array / norms
            
        elif operation == 'standardize':
            # Z-score standardization
            mean = np.mean(vectors_array, axis=0)
            std = np.std(vectors_array, axis=0)
            std[std == 0] = 1  # Avoid division by zero
            processed = (vectors_array - mean) / std
            
        elif operation == 'pca_reduce':
            # Simple PCA dimension reduction (to 80% of original)
            from sklearn.decomposition import PCA
            target_dim = max(1, int(vectors_array.shape[1] * 0.8))
            pca = PCA(n_components=target_dim)
            processed = pca.fit_transform(vectors_array)
            
        else:
            processed = vectors_array
        
        return processed.tolist()
        
    except Exception as e:
        logger.error(f"❌ Vector processing error: {e}")
        return vectors  # Return original on error

def _get_top_k_results(similarities: List[float], top_k: int) -> List[Tuple[int, float]]:
    """
    Get top-k similarity results efficiently
    This function runs in a thread pool
    """
    try:
        # Create index-similarity pairs
        indexed_similarities = [(i, sim) for i, sim in enumerate(similarities)]
        
        # Sort by similarity (descending)
        sorted_results = sorted(indexed_similarities, key=lambda x: x[1], reverse=True)
        
        # Return top-k
        return sorted_results[:top_k]
        
    except Exception as e:
        logger.error(f"❌ Top-k results error: {e}")
        return []

# Global instance
async_compute_manager = AsyncComputeManager()

# Compatibility functions for existing code
async def cosine_similarity(vector_a: List[float], vector_b: List[float]) -> float:
    """Compute cosine similarity asynchronously"""
    return await async_compute_manager.cosine_similarity_async(vector_a, vector_b)

async def process_text_heavy(text: str, operations: List[str] = None) -> Dict[str, Any]:
    """Process text with heavy operations asynchronously"""
    return await async_compute_manager.text_processing_async(text, operations)
