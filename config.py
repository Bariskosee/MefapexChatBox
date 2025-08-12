"""
🔧 MEFAPEX Configuration Manager - LEGACY COMPATIBILITY LAYER
===========================================================
*** DEPRECATED: Use core.configuration.UnifiedConfig instead ***

This file provides backward compatibility for existing code.
New code should use the unified configuration system.
"""

import warnings
import logging
from core.configuration import get_config as get_unified_config

# Setup logger
logger = logging.getLogger(__name__)

# Issue deprecation warning
warnings.warn(
    "config.py is deprecated. Use 'from core.configuration import get_config' instead.",
    DeprecationWarning,
    stacklevel=2
)

class Config:
    """
    LEGACY: Backward compatibility wrapper for unified configuration
    *** DEPRECATED: Use core.configuration.UnifiedConfig instead ***
    """
    
    def __init__(self):
        self._unified_config = get_unified_config()
        logger.warning("⚠️ Using legacy Config class. Migrate to core.configuration.UnifiedConfig")
    
    @property
    def ENVIRONMENT(self):
        return self._unified_config.environment.value
    
    @property
    def DEBUG_MODE(self):
        return self._unified_config.server.debug
    
    @property
    def SECRET_KEY(self):
        return self._unified_config.security.secret_key
    
    @property
    def USE_OPENAI(self):
        return self._unified_config.ai.use_openai
    
    @property
    def USE_HUGGINGFACE(self):
        return self._unified_config.ai.use_huggingface
    
    @property
    def OPENAI_API_KEY(self):
        return self._unified_config.ai.openai_api_key
    
    @property
    def DATABASE_TYPE(self):
        return self._unified_config.database.type
    
    @property
    def DATABASE_URL(self):
        return self._unified_config.database.url
    
    @property
    def POSTGRES_HOST(self):
        return self._unified_config.database.host
    
    @property
    def POSTGRES_PORT(self):
        return self._unified_config.database.port
    
    @property
    def POSTGRES_USER(self):
        return self._unified_config.database.user
    
    @property
    def POSTGRES_PASSWORD(self):
        return self._unified_config.database.password
    
    @property
    def POSTGRES_DB(self):
        return self._unified_config.database.database
    
    @property
    def QDRANT_HOST(self):
        return self._unified_config.qdrant.host
    
    @property
    def QDRANT_PORT(self):
        return self._unified_config.qdrant.port
    
    @property
    def RATE_LIMIT_REQUESTS(self):
        return self._unified_config.rate_limit.requests_per_minute
    
    @property
    def RATE_LIMIT_CHAT(self):
        return self._unified_config.rate_limit.chat_requests_per_minute
    
    @property
    def ALLOWED_ORIGINS(self):
        return self._unified_config.server.allowed_origins
    
    def validate_production_config(self):
        """LEGACY: Validate configuration for production environment"""
        logger.warning("⚠️ Using legacy validate_production_config. The unified config auto-validates.")
        # The unified config already validates on initialization
        pass

class DevelopmentConfig(Config):
    """LEGACY: Development configuration wrapper"""
    pass

class ProductionConfig(Config):
    """LEGACY: Production configuration wrapper"""
    pass

def get_config() -> Config:
    """
    LEGACY: Get configuration based on environment
    *** DEPRECATED: Use core.configuration.get_config() instead ***
    """
    logger.warning("⚠️ Using legacy get_config(). Use 'from core.configuration import get_config' instead.")
    return Config()

# Global config instance for backward compatibility
config = get_config()

# Export unified config for easy migration
from core.configuration import get_config as get_unified_config
unified_config = get_unified_config()
