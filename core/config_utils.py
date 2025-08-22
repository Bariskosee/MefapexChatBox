"""
🔧 Configuration Utilities for MEFAPEX
=====================================
Shared helper functions to eliminate configuration import redundancy
and provide consistent fallback handling across all modules.
"""

import logging
from typing import Any, Optional, Union
from functools import lru_cache

logger = logging.getLogger(__name__)

# Cache for configuration objects to avoid repeated imports
_cached_config: Optional[Any] = None
_cached_legacy_config: Optional[Any] = None


@lru_cache(maxsize=1)
def load_config() -> Any:
    """
    Load configuration with fallback logic.
    
    This function encapsulates the try/except pattern used across multiple modules
    to import the new core.configuration.get_config() with fallback to legacy config.
    
    Returns:
        Configuration object (either UnifiedConfig or legacy Config)
    """
    global _cached_config, _cached_legacy_config
    
    if _cached_config is not None:
        return _cached_config
    
    try:
        from core.configuration import get_config
        _cached_config = get_config()
        logger.debug("Successfully loaded unified configuration")
        return _cached_config
    except ImportError as e:
        logger.warning(f"Failed to import unified configuration, falling back to legacy config: {e}")
        if _cached_legacy_config is not None:
            return _cached_legacy_config
        
        try:
            from config import config
            _cached_legacy_config = config
            logger.debug("Successfully loaded legacy configuration")
            return _cached_legacy_config
        except ImportError as fallback_error:
            logger.error(f"Failed to import legacy configuration: {fallback_error}")
            raise ImportError("Cannot import any configuration module") from fallback_error


@lru_cache(maxsize=1)
def load_cache_config() -> Any:
    """
    Load cache-specific configuration with fallback logic.
    
    Returns:
        Cache configuration object
    """
    try:
        from core.configuration import get_cache_config
        config = get_cache_config()
        logger.debug("Successfully loaded unified cache configuration")
        return config
    except ImportError as e:
        logger.warning(f"Failed to import unified cache configuration, falling back to legacy config: {e}")
        try:
            from config import config as app_config
            logger.debug("Successfully loaded legacy cache configuration")
            return app_config
        except ImportError as fallback_error:
            logger.error(f"Failed to import legacy cache configuration: {fallback_error}")
            raise ImportError("Cannot import any cache configuration module") from fallback_error


def get_config_value(key: str, default: Any = None, config_obj: Optional[Any] = None) -> Any:
    """
    Get a configuration value with intelligent fallback.
    
    Args:
        key: Configuration key (supports dot notation for nested access)
        default: Default value if key is not found
        config_obj: Optional config object to use (if None, loads automatically)
    
    Returns:
        Configuration value or default
    """
    if config_obj is None:
        config_obj = load_config()
    
    # Handle dot notation for nested access (e.g., 'qdrant.host')
    keys = key.split('.')
    value = config_obj
    
    try:
        for k in keys:
            if hasattr(value, k):
                value = getattr(value, k)
            elif hasattr(value, k.upper()):  # Try uppercase for legacy config
                value = getattr(value, k.upper())
            elif isinstance(value, dict) and k in value:
                value = value[k]
            elif isinstance(value, dict) and k.upper() in value:
                value = value[k.upper()]
            else:
                return default
        return value
    except (AttributeError, KeyError, TypeError):
        return default


def is_unified_config(config_obj: Optional[Any] = None) -> bool:
    """
    Check if the loaded configuration is the new unified configuration.
    
    Args:
        config_obj: Optional config object to check (if None, loads automatically)
    
    Returns:
        True if unified configuration, False if legacy
    """
    if config_obj is None:
        config_obj = load_config()
    
    # Check if it has the unified config methods/attributes
    return hasattr(config_obj, 'environment') and hasattr(config_obj, 'is_production')


def reset_config_cache():
    """
    Reset the cached configuration objects.
    Useful for testing or when configuration needs to be reloaded.
    """
    global _cached_config, _cached_legacy_config
    _cached_config = None
    _cached_legacy_config = None
    
    # Clear the lru_cache
    load_config.cache_clear()
    load_cache_config.cache_clear()
    
    logger.debug("Configuration cache reset")


# Convenience functions for common configuration patterns
def get_qdrant_config() -> dict:
    """Get Qdrant configuration with fallback."""
    config = load_config()
    
    if is_unified_config(config):
        return {
            'host': getattr(config.qdrant, 'host', 'localhost'),
            'port': getattr(config.qdrant, 'port', 6333)
        }
    else:
        return {
            'host': getattr(config, 'QDRANT_HOST', 'localhost'),
            'port': getattr(config, 'QDRANT_PORT', 6333)
        }


def get_ai_config() -> dict:
    """Get AI configuration with fallback."""
    config = load_config()
    
    if is_unified_config(config):
        return {
            'use_openai': getattr(config.ai, 'use_openai', False),
            'openai_api_key': getattr(config.ai, 'openai_api_key', None),
            'model': getattr(config.ai, 'model', 'gpt-3.5-turbo'),
            'use_huggingface': getattr(config.ai, 'use_huggingface', True)
        }
    else:
        return {
            'use_openai': getattr(config, 'USE_OPENAI', False),
            'openai_api_key': getattr(config, 'OPENAI_API_KEY', None),
            'model': getattr(config, 'OPENAI_MODEL', 'gpt-3.5-turbo'),
            'use_huggingface': getattr(config, 'USE_HUGGINGFACE', True)
        }


def get_redis_config() -> dict:
    """Get Redis configuration with fallback."""
    config = load_cache_config()
    
    if hasattr(config, 'redis_host'):  # Unified config
        return {
            'host': getattr(config, 'redis_host', None),
            'port': getattr(config, 'redis_port', 6379),
            'url': getattr(config, 'redis_url', None)
        }
    else:  # Legacy config
        return {
            'host': getattr(config, 'REDIS_HOST', None),
            'port': getattr(config, 'REDIS_PORT', 6379),
            'url': getattr(config, 'REDIS_URL', None)
        }


def get_cache_settings() -> dict:
    """Get cache settings with safe property access and fallback."""
    config = load_cache_config()
    
    if hasattr(config, 'response_cache_max_size'):  # Unified config
        return {
            'max_size': getattr(config, 'response_cache_max_size', 1000),
            'ttl': getattr(config, 'response_cache_ttl', 3600),
            'eviction_policy': getattr(config, 'response_cache_eviction_policy', 'lru'),
            'max_memory_mb': getattr(config, 'max_memory_usage_mb', 100),  # Default 100MB
            'auto_scale': getattr(config, 'auto_scale_enabled', True),
            'cleanup_interval': getattr(config, 'cleanup_interval', 300)  # 5 minutes
        }
    else:  # Legacy config
        return {
            'max_size': getattr(config, 'RESPONSE_CACHE_MAX_SIZE', getattr(config, 'CACHE_SIZE', 1000)),
            'ttl': getattr(config, 'RESPONSE_CACHE_TTL', getattr(config, 'CACHE_TTL', 3600)),
            'eviction_policy': getattr(config, 'RESPONSE_CACHE_EVICTION_POLICY', 'lru'),
            'max_memory_mb': getattr(config, 'MAX_MEMORY_USAGE_MB', 100),
            'auto_scale': getattr(config, 'AUTO_SCALE_ENABLED', True),
            'cleanup_interval': getattr(config, 'CLEANUP_INTERVAL', 300)
        }
