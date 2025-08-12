"""
🔧 Configuration Service Implementation
====================================
Implements the configuration interfaces using the unified configuration system
"""

from typing import Any, Dict, List
from core.interfaces.config_interface import (
    IConfigurationService,
    IDatabaseConfigurationService,
    ISecurityConfigurationService,
    IAIConfigurationService
)
from core.configuration import get_config, UnifiedConfig


class UnifiedConfigurationService(
    IConfigurationService,
    IDatabaseConfigurationService,
    ISecurityConfigurationService,
    IAIConfigurationService
):
    """
    Unified configuration service that implements all configuration interfaces
    Single Responsibility: Provide configuration access through clean interfaces
    """
    
    def __init__(self):
        self._config = get_config()
    
    # IConfigurationService implementation
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key with dot notation support"""
        try:
            # Support dot notation like 'database.host'
            keys = key.split('.')
            value = self._config
            
            for k in keys:
                if hasattr(value, k):
                    value = getattr(value, k)
                else:
                    return default
            
            return value
        except (AttributeError, KeyError):
            return default
    
    def get_string(self, key: str, default: str = "") -> str:
        """Get string configuration value"""
        value = self.get(key, default)
        return str(value) if value is not None else default
    
    def get_int(self, key: str, default: int = 0) -> int:
        """Get integer configuration value"""
        value = self.get(key, default)
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get boolean configuration value"""
        value = self.get(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        return bool(value) if value is not None else default
    
    def get_list(self, key: str, default: List[Any] = None) -> List[Any]:
        """Get list configuration value"""
        value = self.get(key, default or [])
        if isinstance(value, list):
            return value
        return default or []
    
    def validate_required_configs(self, required_keys: List[str]) -> Dict[str, bool]:
        """Validate that required configuration keys are present"""
        results = {}
        for key in required_keys:
            value = self.get(key)
            results[key] = value is not None and value != ""
        return results
    
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self._config.is_production()
    
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self._config.is_development()
    
    # IDatabaseConfigurationService implementation
    def get_database_url(self) -> str:
        """Get database connection URL"""
        return self._config.get_database_url()
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration dictionary"""
        db_config = self._config.database
        return {
            "type": db_config.type,
            "host": db_config.host,
            "port": db_config.port,
            "user": db_config.user,
            "password": db_config.password,
            "database": db_config.database,
            "url": db_config.url,
            "async_url": db_config.async_url,
            "max_connections": db_config.max_connections,
            "timeout": db_config.timeout
        }
    
    def validate_database_config(self) -> bool:
        """Validate database configuration"""
        db_config = self._config.database
        
        # Basic validation
        if not db_config.host or not db_config.database:
            return False
        
        if not db_config.password and self._config.is_production():
            return False
        
        if db_config.port < 1 or db_config.port > 65535:
            return False
        
        return True
    
    # ISecurityConfigurationService implementation
    def get_secret_key(self) -> str:
        """Get application secret key"""
        return self._config.security.secret_key or ""
    
    def get_jwt_config(self) -> Dict[str, Any]:
        """Get JWT configuration"""
        sec_config = self._config.security
        return {
            "secret_key": sec_config.secret_key,
            "algorithm": sec_config.jwt_algorithm,
            "access_token_expire_minutes": sec_config.access_token_expire_minutes
        }
    
    def get_cors_config(self) -> Dict[str, Any]:
        """Get CORS configuration"""
        server_config = self._config.server
        return {
            "allowed_origins": server_config.allowed_origins,
            "allowed_hosts": server_config.allowed_hosts,
            "allow_credentials": True,
            "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["*"]
        }
    
    def validate_production_security(self) -> Dict[str, bool]:
        """Validate production security settings"""
        sec_config = self._config.security
        server_config = self._config.server
        
        validations = {
            "has_secret_key": bool(sec_config.secret_key),
            "debug_disabled": not server_config.debug,
            "strong_password_policy": sec_config.min_password_length >= 8,
            "no_wildcard_cors": "*" not in server_config.allowed_origins,
            "demo_user_properly_configured": (
                not sec_config.demo_user_enabled or 
                sec_config.force_demo_in_production
            )
        }
        
        return validations
    
    # IAIConfigurationService implementation
    def get_model_config(self) -> Dict[str, Any]:
        """Get AI model configuration"""
        ai_config = self._config.ai
        return {
            "use_openai": ai_config.use_openai,
            "use_huggingface": ai_config.use_huggingface,
            "sentence_model": ai_config.sentence_model,
            "huggingface_model": ai_config.huggingface_model,
            "max_tokens": ai_config.max_tokens,
            "temperature": ai_config.temperature
        }
    
    def get_openai_config(self) -> Dict[str, Any]:
        """Get OpenAI configuration"""
        ai_config = self._config.ai
        return {
            "api_key": ai_config.openai_api_key,
            "enabled": ai_config.use_openai,
            "max_tokens": ai_config.max_tokens,
            "temperature": ai_config.temperature
        }
    
    def get_huggingface_config(self) -> Dict[str, Any]:
        """Get HuggingFace configuration"""
        ai_config = self._config.ai
        return {
            "enabled": ai_config.use_huggingface,
            "model": ai_config.huggingface_model,
            "sentence_model": ai_config.sentence_model
        }
    
    def is_openai_enabled(self) -> bool:
        """Check if OpenAI is enabled"""
        return self._config.ai.use_openai
    
    def is_huggingface_enabled(self) -> bool:
        """Check if HuggingFace is enabled"""
        return self._config.ai.use_huggingface
    
    # Additional utility methods
    def get_qdrant_config(self) -> Dict[str, Any]:
        """Get Qdrant configuration"""
        qdrant_config = self._config.qdrant
        return {
            "host": qdrant_config.host,
            "port": qdrant_config.port,
            "collection_name": qdrant_config.collection_name,
            "vector_size": qdrant_config.vector_size
        }
    
    def get_rate_limit_config(self) -> Dict[str, Any]:
        """Get rate limiting configuration"""
        rate_config = self._config.rate_limit
        return {
            "requests_per_minute": rate_config.requests_per_minute,
            "chat_requests_per_minute": rate_config.chat_requests_per_minute,
            "enabled": rate_config.enabled
        }
    
    def get_validation_config(self) -> Dict[str, Any]:
        """Get validation configuration"""
        val_config = self._config.validation
        return {
            "max_message_length": val_config.max_message_length,
            "min_message_length": val_config.min_message_length,
            "max_username_length": val_config.max_username_length,
            "min_username_length": val_config.min_username_length
        }
    
    def reload_config(self):
        """Reload configuration from environment"""
        from core.configuration import reset_config
        reset_config()
        self._config = get_config()


# Global service instance
_config_service: UnifiedConfigurationService = None

def get_config_service() -> UnifiedConfigurationService:
    """Get the global configuration service instance"""
    global _config_service
    if _config_service is None:
        _config_service = UnifiedConfigurationService()
    return _config_service
