"""
⚙️ Configuration Interface
===========================
Abstract base class for configuration management following Single Responsibility Principle.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union


class IConfigurationService(ABC):
    """
    Interface for configuration management.
    Single Responsibility: Application configuration access and validation.
    """
    
    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        pass
    
    @abstractmethod
    def get_string(self, key: str, default: str = "") -> str:
        """Get string configuration value"""
        pass
    
    @abstractmethod
    def get_int(self, key: str, default: int = 0) -> int:
        """Get integer configuration value"""
        pass
    
    @abstractmethod
    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get boolean configuration value"""
        pass
    
    @abstractmethod
    def get_list(self, key: str, default: List[Any] = None) -> List[Any]:
        """Get list configuration value"""
        pass
    
    @abstractmethod
    def validate_required_configs(self, required_keys: List[str]) -> Dict[str, bool]:
        """Validate that required configuration keys are present"""
        pass
    
    @abstractmethod
    def is_production(self) -> bool:
        """Check if running in production environment"""
        pass
    
    @abstractmethod
    def is_development(self) -> bool:
        """Check if running in development environment"""
        pass


class IDatabaseConfigurationService(ABC):
    """
    Database-specific configuration service.
    Single Responsibility: Database configuration management.
    """
    
    @abstractmethod
    def get_database_url(self) -> str:
        """Get database connection URL"""
        pass
    
    @abstractmethod
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration dictionary"""
        pass
    
    @abstractmethod
    def validate_database_config(self) -> bool:
        """Validate database configuration"""
        pass


class ISecurityConfigurationService(ABC):
    """
    Security-specific configuration service.
    Single Responsibility: Security configuration management.
    """
    
    @abstractmethod
    def get_secret_key(self) -> str:
        """Get application secret key"""
        pass
    
    @abstractmethod
    def get_jwt_config(self) -> Dict[str, Any]:
        """Get JWT configuration"""
        pass
    
    @abstractmethod
    def get_cors_config(self) -> Dict[str, Any]:
        """Get CORS configuration"""
        pass
    
    @abstractmethod
    def validate_production_security(self) -> Dict[str, bool]:
        """Validate production security settings"""
        pass


class IAIConfigurationService(ABC):
    """
    AI-specific configuration service.
    Single Responsibility: AI/ML configuration management.
    """
    
    @abstractmethod
    def get_model_config(self) -> Dict[str, Any]:
        """Get AI model configuration"""
        pass
    
    @abstractmethod
    def get_openai_config(self) -> Dict[str, Any]:
        """Get OpenAI configuration"""
        pass
    
    @abstractmethod
    def get_huggingface_config(self) -> Dict[str, Any]:
        """Get HuggingFace configuration"""
        pass
    
    @abstractmethod
    def is_openai_enabled(self) -> bool:
        """Check if OpenAI is enabled"""
        pass
    
    @abstractmethod
    def is_huggingface_enabled(self) -> bool:
        """Check if HuggingFace is enabled"""
        pass
