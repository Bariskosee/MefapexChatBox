"""
🤖 Model Management Interface
============================
Abstract base class for AI model operations following Single Responsibility Principle.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import torch


class IModelManager(ABC):
    """
    Interface for AI model management.
    Single Responsibility: AI model loading, management and inference.
    """
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize model manager"""
        pass
    
    @abstractmethod
    def warmup_models(self) -> None:
        """Warm up models for faster inference"""
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about loaded models"""
        pass
    
    @abstractmethod
    def cleanup_resources(self) -> None:
        """Clean up model resources"""
        pass
    
    @property
    @abstractmethod
    def device(self) -> str:
        """Get optimal device for model inference"""
        pass


class ITextGenerationService(ABC):
    """
    Text generation service.
    Single Responsibility: Text generation operations.
    """
    
    @abstractmethod
    def generate_response(self, prompt: str, max_length: int = 80, **kwargs) -> str:
        """Generate text response"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if text generation is available"""
        pass


class IEmbeddingService(ABC):
    """
    Text embedding service.
    Single Responsibility: Text embedding operations.
    """
    
    @abstractmethod
    def generate_embedding(self, text: str) -> List[float]:
        """Generate text embedding"""
        pass
    
    @abstractmethod
    def compute_similarity(self, text1: str, text2: str) -> float:
        """Compute similarity between two texts"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if embedding service is available"""
        pass


class IModelLoader(ABC):
    """
    Model loading service.
    Single Responsibility: Model loading and initialization.
    """
    
    @abstractmethod
    def load_sentence_transformer(self, model_name: str) -> Any:
        """Load sentence transformer model"""
        pass
    
    @abstractmethod
    def load_text_generator(self, model_name: str) -> Any:
        """Load text generation model"""
        pass
    
    @abstractmethod
    def unload_model(self, model_name: str) -> bool:
        """Unload a specific model"""
        pass


class IModelCache(ABC):
    """
    Model caching service.
    Single Responsibility: Model result caching.
    """
    
    @abstractmethod
    def get_cached_embedding(self, text: str) -> Optional[List[float]]:
        """Get cached embedding"""
        pass
    
    @abstractmethod
    def cache_embedding(self, text: str, embedding: List[float]) -> None:
        """Cache embedding result"""
        pass
    
    @abstractmethod
    def clear_cache(self) -> None:
        """Clear all cached results"""
        pass
    
    @abstractmethod
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        pass
