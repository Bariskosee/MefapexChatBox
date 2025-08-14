"""
🔧 MEFAPEX Unified Configuration System
=====================================
Single source of truth for all application configuration
Solves the "Configuration Chaos" problem with 10+ env files
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import json

# Setup logger
logger = logging.getLogger(__name__)

class Environment(Enum):
    """Environment types"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"

@dataclass
class DatabaseConfig:
    """Database configuration"""
    type: str = "postgresql"
    host: str = "localhost"
    port: int = 5432
    user: str = "mefapex"
    password: Optional[str] = None
    database: str = "mefapex_chatbot"
    url: Optional[str] = None
    max_connections: int = 20
    timeout: int = 30
    
    def __post_init__(self):
        if not self.url and self.password:
            self.url = f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
        
        # Async URL for SQLAlchemy
        if self.url and self.url.startswith('postgresql://'):
            self.async_url = self.url.replace('postgresql://', 'postgresql+asyncpg://')
        else:
            self.async_url = self.url

@dataclass
class SecurityConfig:
    """Security configuration"""
    secret_key: Optional[str] = None
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    min_password_length: int = 8
    max_password_length: int = 128
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_numbers: bool = True
    require_special_chars: bool = True
    max_login_attempts: int = 5
    block_duration_minutes: int = 15
    
    # Demo user settings
    demo_user_enabled: bool = True
    demo_password: str = "demo123"
    force_demo_in_production: bool = False
    accept_weak_demo_password: bool = False

@dataclass
class AIConfig:
    """AI/ML configuration"""
    use_openai: bool = False
    use_huggingface: bool = True
    openai_api_key: Optional[str] = None
    sentence_model: str = "emrecan/bert-base-turkish-cased-mean-nli-stsb-tr"
    huggingface_model: str = "ytu-ce-cosmos/turkish-gpt2-large"
    turkish_sentence_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    english_fallback_model: str = "all-MiniLM-L6-v2"
    max_tokens: int = 150
    temperature: float = 0.7
    language_detection: bool = True
    prefer_turkish_models: bool = True

@dataclass
class QdrantConfig:
    """Qdrant vector database configuration"""
    host: str = "localhost"
    port: int = 6333
    collection_name: str = "mefapex_faq"
    vector_size: int = 384

@dataclass
class ServerConfig:
    """Server configuration"""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    reload: bool = False
    allowed_origins: List[str] = field(default_factory=lambda: [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ])
    allowed_hosts: List[str] = field(default_factory=lambda: [
        "localhost",
        "127.0.0.1"
    ])

@dataclass
class RateLimitConfig:
    """Rate limiting configuration"""
    requests_per_minute: int = 200
    chat_requests_per_minute: int = 100
    enabled: bool = True

@dataclass
class ValidationConfig:
    """Input validation configuration"""
    max_message_length: int = 1000
    min_message_length: int = 2
    max_username_length: int = 50
    min_username_length: int = 3

class UnifiedConfig:
    """
    🎯 Unified Configuration Manager
    Single source of truth for all application settings
    """
    
    def __init__(self, env_file: Optional[str] = None):
        self.env_file = env_file or self._find_env_file()
        self.environment = self._get_environment()
        
        # Load environment variables
        self._load_env_file()
        
        # Initialize configuration sections
        self.database = self._init_database_config()
        self.security = self._init_security_config()
        self.ai = self._init_ai_config()
        self.qdrant = self._init_qdrant_config()
        self.server = self._init_server_config()
        self.rate_limit = self._init_rate_limit_config()
        self.validation = self._init_validation_config()
        
        # Validate configuration
        self._validate_config()
        
        logger.info(f"✅ Unified configuration loaded for {self.environment.value} environment")
    
    def _find_env_file(self) -> Optional[str]:
        """Find the .env file in the project"""
        possible_locations = [
            ".env",
            os.path.join(os.getcwd(), ".env"),
            os.path.join(Path(__file__).parent.parent, ".env")
        ]
        
        for location in possible_locations:
            if os.path.exists(location):
                return location
        
        return None
    
    def _load_env_file(self):
        """Load environment variables from .env file"""
        if self.env_file and os.path.exists(self.env_file):
            try:
                from dotenv import load_dotenv
                load_dotenv(self.env_file)
                logger.info(f"📁 Loaded environment variables from {self.env_file}")
            except ImportError:
                logger.warning("⚠️ python-dotenv not installed, skipping .env file loading")
            except Exception as e:
                logger.warning(f"⚠️ Error loading .env file: {e}")
    
    def _get_environment(self) -> Environment:
        """Get current environment"""
        env_str = os.getenv("ENVIRONMENT", "development").lower()
        try:
            return Environment(env_str)
        except ValueError:
            logger.warning(f"⚠️ Unknown environment '{env_str}', defaulting to development")
            return Environment.DEVELOPMENT
    
    def _init_database_config(self) -> DatabaseConfig:
        """Initialize database configuration"""
        return DatabaseConfig(
            type=os.getenv("DATABASE_TYPE", "postgresql"),
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            user=os.getenv("POSTGRES_USER", "mefapex"),
            password=os.getenv("POSTGRES_PASSWORD"),
            database=os.getenv("POSTGRES_DB", "mefapex_chatbot"),
            url=os.getenv("DATABASE_URL"),
            max_connections=int(os.getenv("DB_MAX_CONNECTIONS", "20")),
            timeout=int(os.getenv("DB_TIMEOUT", "30"))
        )
    
    def _init_security_config(self) -> SecurityConfig:
        """Initialize security configuration"""
        return SecurityConfig(
            secret_key=os.getenv("SECRET_KEY"),
            jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
            access_token_expire_minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")),
            min_password_length=int(os.getenv("MIN_PASSWORD_LENGTH", "8")),
            max_password_length=int(os.getenv("MAX_PASSWORD_LENGTH", "128")),
            require_uppercase=os.getenv("REQUIRE_UPPERCASE", "true").lower() == "true",
            require_lowercase=os.getenv("REQUIRE_LOWERCASE", "true").lower() == "true",
            require_numbers=os.getenv("REQUIRE_NUMBERS", "true").lower() == "true",
            require_special_chars=os.getenv("REQUIRE_SPECIAL_CHARS", "true").lower() == "true",
            max_login_attempts=int(os.getenv("MAX_LOGIN_ATTEMPTS", "5")),
            block_duration_minutes=int(os.getenv("BLOCK_DURATION_MINUTES", "15")),
            demo_user_enabled=os.getenv("DEMO_USER_ENABLED", "true").lower() == "true",
            demo_password=os.getenv("DEMO_PASSWORD", "demo123"),
            force_demo_in_production=os.getenv("FORCE_DEMO_IN_PRODUCTION", "false").lower() == "true",
            accept_weak_demo_password=os.getenv("ACCEPT_WEAK_DEMO_PASSWORD", "false").lower() == "true"
        )
    
    def _init_ai_config(self) -> AIConfig:
        """Initialize AI configuration"""
        return AIConfig(
            use_openai=os.getenv("USE_OPENAI", "false").lower() == "true",
            use_huggingface=os.getenv("USE_HUGGINGFACE", "true").lower() == "true",
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            sentence_model=os.getenv("SENTENCE_MODEL", "emrecan/bert-base-turkish-cased-mean-nli-stsb-tr"),
            huggingface_model=os.getenv("HUGGINGFACE_MODEL", "ytu-ce-cosmos/turkish-gpt2-large"),
            turkish_sentence_model=os.getenv("TURKISH_SENTENCE_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"),
            english_fallback_model=os.getenv("ENGLISH_FALLBACK_MODEL", "all-MiniLM-L6-v2"),
            max_tokens=int(os.getenv("AI_MAX_TOKENS", "150")),
            temperature=float(os.getenv("AI_TEMPERATURE", "0.7")),
            language_detection=os.getenv("AI_LANGUAGE_DETECTION", "true").lower() == "true",
            prefer_turkish_models=os.getenv("AI_PREFER_TURKISH_MODELS", "true").lower() == "true"
        )
    
    def _init_qdrant_config(self) -> QdrantConfig:
        """Initialize Qdrant configuration"""
        return QdrantConfig(
            host=os.getenv("QDRANT_HOST", "localhost"),
            port=int(os.getenv("QDRANT_PORT", "6333")),
            collection_name=os.getenv("QDRANT_COLLECTION", "mefapex_faq"),
            vector_size=int(os.getenv("QDRANT_VECTOR_SIZE", "384"))
        )
    
    def _init_server_config(self) -> ServerConfig:
        """Initialize server configuration"""
        # Parse allowed origins
        origins_str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000,http://127.0.0.1:8000")
        allowed_origins = [origin.strip() for origin in origins_str.split(",") if origin.strip()]
        
        # Parse allowed hosts
        hosts_str = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1")
        allowed_hosts = [host.strip() for host in hosts_str.split(",") if host.strip()]
        
        return ServerConfig(
            host=os.getenv("SERVER_HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "8000")),
            debug=os.getenv("DEBUG", "false").lower() == "true",
            reload=os.getenv("RELOAD", "false").lower() == "true",
            allowed_origins=allowed_origins,
            allowed_hosts=allowed_hosts
        )
    
    def _init_rate_limit_config(self) -> RateLimitConfig:
        """Initialize rate limiting configuration"""
        return RateLimitConfig(
            requests_per_minute=int(os.getenv("RATE_LIMIT_REQUESTS", "200")),
            chat_requests_per_minute=int(os.getenv("RATE_LIMIT_CHAT", "100")),
            enabled=os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
        )
    
    def _init_validation_config(self) -> ValidationConfig:
        """Initialize validation configuration"""
        return ValidationConfig(
            max_message_length=int(os.getenv("MAX_MESSAGE_LENGTH", "1000")),
            min_message_length=int(os.getenv("MIN_MESSAGE_LENGTH", "2")),
            max_username_length=int(os.getenv("MAX_USERNAME_LENGTH", "50")),
            min_username_length=int(os.getenv("MIN_USERNAME_LENGTH", "3"))
        )
    
    def _validate_config(self):
        """Validate configuration for current environment"""
        errors = []
        warnings = []
        
        # Production-specific validations
        if self.environment == Environment.PRODUCTION:
            if self.server.debug:
                errors.append("DEBUG mode must be disabled in production")
            
            if not self.security.secret_key:
                errors.append("SECRET_KEY is required in production")
            
            if not self.database.password:
                errors.append("POSTGRES_PASSWORD is required in production")
            
            if self.ai.use_openai and not self.ai.openai_api_key:
                errors.append("OPENAI_API_KEY is required when USE_OPENAI is enabled")
            
            if self.security.demo_user_enabled and not self.security.force_demo_in_production:
                warnings.append("Demo user is enabled in production (use FORCE_DEMO_IN_PRODUCTION=true to confirm)")
            
            if "*" in self.server.allowed_origins:
                errors.append("Wildcard CORS origins not allowed in production")
        
        # General validations
        if self.security.min_password_length < 4:
            warnings.append(f"Minimum password length is very low: {self.security.min_password_length}")
        
        if self.database.port < 1 or self.database.port > 65535:
            errors.append(f"Invalid database port: {self.database.port}")
        
        if self.server.port < 1 or self.server.port > 65535:
            errors.append(f"Invalid server port: {self.server.port}")
        
        # Log results
        if errors:
            error_msg = "❌ Configuration validation failed:\n" + "\n".join(f"  - {err}" for err in errors)
            logger.error(error_msg)
            if self.environment == Environment.PRODUCTION:
                raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")
        
        if warnings:
            warning_msg = "⚠️ Configuration warnings:\n" + "\n".join(f"  - {warn}" for warn in warnings)
            logger.warning(warning_msg)
        
        if not errors and not warnings:
            logger.info("✅ Configuration validation passed")
    
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment == Environment.PRODUCTION
    
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.environment == Environment.DEVELOPMENT
    
    def is_testing(self) -> bool:
        """Check if running in testing"""
        return self.environment == Environment.TESTING
    
    def get_database_url(self, async_mode: bool = False) -> str:
        """Get database connection URL"""
        if async_mode:
            return self.database.async_url or self.database.url
        return self.database.url
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get configuration summary for debugging"""
        return {
            "environment": self.environment.value,
            "database": {
                "type": self.database.type,
                "host": self.database.host,
                "port": self.database.port,
                "database": self.database.database,
                "has_password": bool(self.database.password)
            },
            "security": {
                "has_secret_key": bool(self.security.secret_key),
                "demo_user_enabled": self.security.demo_user_enabled,
                "min_password_length": self.security.min_password_length
            },
            "ai": {
                "use_openai": self.ai.use_openai,
                "use_huggingface": self.ai.use_huggingface,
                "has_openai_key": bool(self.ai.openai_api_key)
            },
            "server": {
                "host": self.server.host,
                "port": self.server.port,
                "debug": self.server.debug,
                "allowed_origins_count": len(self.server.allowed_origins)
            }
        }
    
    def export_config(self, file_path: str):
        """Export current configuration to file (for debugging)"""
        config_data = self.get_config_summary()
        with open(file_path, 'w') as f:
            json.dump(config_data, f, indent=2)
        logger.info(f"📝 Configuration exported to {file_path}")

# Global configuration instance
_global_config: Optional[UnifiedConfig] = None

def get_config() -> UnifiedConfig:
    """
    Get the global configuration instance
    Implements singleton pattern to ensure single source of truth
    """
    global _global_config
    if _global_config is None:
        _global_config = UnifiedConfig()
    return _global_config

def reset_config():
    """Reset global configuration (useful for testing)"""
    global _global_config
    _global_config = None

# Convenience functions for backward compatibility
def get_database_config() -> DatabaseConfig:
    """Get database configuration"""
    return get_config().database

def get_security_config() -> SecurityConfig:
    """Get security configuration"""
    return get_config().security

def get_ai_config() -> AIConfig:
    """Get AI configuration"""
    return get_config().ai

def get_server_config() -> ServerConfig:
    """Get server configuration"""
    return get_config().server

def is_production() -> bool:
    """Check if running in production"""
    return get_config().is_production()

def is_development() -> bool:
    """Check if running in development"""
    return get_config().is_development()

if __name__ == "__main__":
    # Test the configuration system
    config = get_config()
    print("🔧 MEFAPEX Unified Configuration Test")
    print("=" * 50)
    print(json.dumps(config.get_config_summary(), indent=2))
