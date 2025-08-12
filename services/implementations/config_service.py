"""
⚙️ Pydantic Configuration Management
===================================
Modern Pydantic-based configuration with validation, environment management,
and type safety following FastAPI best practices.
"""

from typing import List, Optional, Union, Dict, Any
from pathlib import Path
from functools import lru_cache

from pydantic import BaseSettings, Field, validator, root_validator
from pydantic import PostgresDsn, RedisDsn, HttpUrl, EmailStr
from pydantic.env_settings import SettingsSourceCallable


class DatabaseSettings(BaseSettings):
    """Database configuration with Pydantic validation"""
    
    # PostgreSQL Configuration
    postgres_host: str = Field(default="localhost", env="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, env="POSTGRES_PORT", ge=1, le=65535)
    postgres_user: str = Field(env="POSTGRES_USER")
    postgres_password: str = Field(env="POSTGRES_PASSWORD")
    postgres_db: str = Field(env="POSTGRES_DB")
    
    # Connection Pool Settings
    min_connections: int = Field(default=1, ge=1, le=10)
    max_connections: int = Field(default=20, ge=1, le=100)
    pool_timeout: int = Field(default=30, ge=1, le=300)
    
    @validator('postgres_password')
    def validate_password(cls, v):
        if not v or len(v) < 8:
            raise ValueError('Database password must be at least 8 characters')
        return v
    
    @property
    def database_url(self) -> str:
        """Generate PostgreSQL connection URL"""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    @property
    def async_database_url(self) -> str:
        """Generate async PostgreSQL connection URL"""
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    class Config:
        env_prefix = "DB_"
        case_sensitive = False


class SecuritySettings(BaseSettings):
    """Security configuration with Pydantic validation"""
    
    # JWT Configuration
    secret_key: str = Field(env="SECRET_KEY", min_length=32)
    algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, ge=1, le=10080)  # Max 1 week
    refresh_token_expire_days: int = Field(default=7, ge=1, le=30)
    
    # Password Security
    min_password_length: int = Field(default=8, ge=4, le=128)
    max_password_length: int = Field(default=128, ge=8, le=256)
    require_special_chars: bool = Field(default=True)
    require_numbers: bool = Field(default=True)
    require_uppercase: bool = Field(default=True)
    
    # Rate Limiting
    rate_limit_requests: int = Field(default=100, ge=1, le=10000)
    rate_limit_chat: int = Field(default=50, ge=1, le=1000)
    rate_limit_window_minutes: int = Field(default=1, ge=1, le=60)
    
    # CORS Settings
    allowed_origins: List[str] = Field(default=["http://localhost:3000", "http://localhost:8000"])
    allowed_methods: List[str] = Field(default=["GET", "POST", "PUT", "DELETE"])
    allowed_headers: List[str] = Field(default=["*"])
    allow_credentials: bool = Field(default=True)
    
    # Production Security
    allowed_hosts: List[str] = Field(default=["localhost", "127.0.0.1"])
    enable_https_redirect: bool = Field(default=False)
    secure_cookies: bool = Field(default=False)
    
    @validator('secret_key')
    def validate_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError('Secret key must be at least 32 characters')
        return v
    
    @validator('allowed_origins')
    def validate_origins(cls, v):
        if "*" in v and len(v) > 1:
            raise ValueError('Cannot use "*" with other specific origins')
        return v
    
    class Config:
        env_prefix = "SECURITY_"
        case_sensitive = False


class AIModelSettings(BaseSettings):
    """AI Model configuration with Pydantic validation"""
    
    # Model Providers
    use_openai: bool = Field(default=False, env="USE_OPENAI")
    use_huggingface: bool = Field(default=True, env="USE_HUGGINGFACE")
    use_local_models: bool = Field(default=True, env="USE_LOCAL_MODELS")
    
    # OpenAI Configuration
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-3.5-turbo", env="OPENAI_MODEL")
    openai_max_tokens: int = Field(default=150, ge=1, le=4000)
    openai_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    
    # HuggingFace Configuration
    hf_model_name: str = Field(default="microsoft/DialoGPT-small", env="HF_MODEL_NAME")
    hf_cache_dir: str = Field(default="./models_cache", env="HF_CACHE_DIR")
    hf_device: str = Field(default="auto", env="HF_DEVICE")
    
    # Local Model Configuration
    sentence_model: str = Field(default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    embedding_dimension: int = Field(default=384, ge=128, le=1536)
    max_sequence_length: int = Field(default=512, ge=128, le=2048)
    
    # Performance Settings
    model_cache_size: int = Field(default=100, ge=10, le=1000)
    batch_size: int = Field(default=8, ge=1, le=64)
    max_workers: int = Field(default=4, ge=1, le=16)
    
    @validator('openai_api_key')
    def validate_openai_key(cls, v, values):
        if values.get('use_openai') and not v:
            raise ValueError('OpenAI API key is required when use_openai is True')
        return v
    
    @root_validator
    def validate_model_providers(cls, values):
        providers = [values.get('use_openai'), values.get('use_huggingface'), values.get('use_local_models')]
        if not any(providers):
            raise ValueError('At least one AI model provider must be enabled')
        return values
    
    class Config:
        env_prefix = "AI_"
        case_sensitive = False


class CacheSettings(BaseSettings):
    """Cache configuration with Pydantic validation"""
    
    # Redis Configuration
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT", ge=1, le=65535)
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    redis_db: int = Field(default=0, env="REDIS_DB", ge=0, le=15)
    redis_ssl: bool = Field(default=False, env="REDIS_SSL")
    
    # Connection Pool
    redis_max_connections: int = Field(default=10, ge=1, le=100)
    redis_timeout: int = Field(default=5, ge=1, le=60)
    
    # Cache TTL Settings (in seconds)
    default_ttl: int = Field(default=3600, ge=60, le=86400)  # 1 hour default
    session_ttl: int = Field(default=7200, ge=300, le=86400)  # 2 hours
    response_ttl: int = Field(default=1800, ge=60, le=3600)  # 30 minutes
    user_ttl: int = Field(default=3600, ge=300, le=14400)  # 1 hour
    
    @property
    def redis_url(self) -> str:
        """Generate Redis connection URL"""
        auth = f":{self.redis_password}@" if self.redis_password else ""
        protocol = "rediss" if self.redis_ssl else "redis"
        return f"{protocol}://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    class Config:
        env_prefix = "CACHE_"
        case_sensitive = False


class LoggingSettings(BaseSettings):
    """Logging configuration with Pydantic validation"""
    
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    log_file: Optional[str] = Field(default=None, env="LOG_FILE")
    log_rotation: str = Field(default="1 day", env="LOG_ROTATION")
    log_retention: str = Field(default="30 days", env="LOG_RETENTION")
    
    # Structured logging
    enable_json_logging: bool = Field(default=False, env="ENABLE_JSON_LOGGING")
    enable_request_logging: bool = Field(default=True, env="ENABLE_REQUEST_LOGGING")
    enable_error_tracking: bool = Field(default=True, env="ENABLE_ERROR_TRACKING")
    
    @validator('log_level')
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level must be one of: {valid_levels}')
        return v.upper()
    
    class Config:
        env_prefix = "LOG_"
        case_sensitive = False


class MonitoringSettings(BaseSettings):
    """Monitoring and observability configuration"""
    
    # Health Check Configuration
    enable_health_checks: bool = Field(default=True)
    health_check_interval: int = Field(default=30, ge=5, le=300)
    
    # Metrics Configuration
    enable_metrics: bool = Field(default=True)
    metrics_endpoint: str = Field(default="/metrics")
    
    # Prometheus Settings
    prometheus_host: str = Field(default="localhost")
    prometheus_port: int = Field(default=9090, ge=1, le=65535)
    
    # Performance Monitoring
    enable_performance_monitoring: bool = Field(default=True)
    slow_query_threshold: float = Field(default=1.0, ge=0.1, le=10.0)
    
    class Config:
        env_prefix = "MONITORING_"
        case_sensitive = False


class ApplicationSettings(BaseSettings):
    """Main application configuration combining all settings"""
    
    # Application Info
    app_name: str = Field(default="MEFAPEX AI Chatbot")
    app_version: str = Field(default="3.0.0")
    app_description: str = Field(default="Advanced AI-powered chatbot with modular architecture")
    
    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    testing: bool = Field(default=False, env="TESTING")
    
    # Server Configuration
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT", ge=1, le=65535)
    workers: int = Field(default=1, env="WORKERS", ge=1, le=16)
    
    # API Configuration
    api_prefix: str = Field(default="/api", env="API_PREFIX")
    docs_url: Optional[str] = Field(default="/docs")
    redoc_url: Optional[str] = Field(default="/redoc")
    openapi_url: Optional[str] = Field(default="/openapi.json")
    
    # Component Settings
    database: DatabaseSettings = DatabaseSettings()
    security: SecuritySettings = SecuritySettings()
    ai: AIModelSettings = AIModelSettings()
    cache: CacheSettings = CacheSettings()
    logging: LoggingSettings = LoggingSettings()
    monitoring: MonitoringSettings = MonitoringSettings()
    
    @validator('environment')
    def validate_environment(cls, v):
        valid_envs = ["development", "testing", "staging", "production"]
        if v.lower() not in valid_envs:
            raise ValueError(f'Environment must be one of: {valid_envs}')
        return v.lower()
    
    @root_validator
    def validate_production_settings(cls, values):
        """Validate settings for production environment"""
        env = values.get('environment', '').lower()
        debug = values.get('debug', False)
        
        if env == 'production':
            if debug:
                raise ValueError('Debug mode must be disabled in production')
            
            # Validate docs URLs for production
            if values.get('docs_url') or values.get('redoc_url'):
                values['docs_url'] = None
                values['redoc_url'] = None
                values['openapi_url'] = None
        
        return values
    
    @property
    def is_development(self) -> bool:
        return self.environment == "development"
    
    @property
    def is_production(self) -> bool:
        return self.environment == "production"
    
    @property
    def is_testing(self) -> bool:
        return self.environment == "testing" or self.testing
    
    class Config:
        # Environment file configuration
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
        # Custom settings source order
        @classmethod
        def customise_sources(
            cls,
            init_settings: SettingsSourceCallable,
            env_settings: SettingsSourceCallable,
            file_secret_settings: SettingsSourceCallable,
        ) -> tuple[SettingsSourceCallable, ...]:
            return (
                init_settings,
                env_settings,
                file_secret_settings,
            )


@lru_cache()
def get_settings() -> ApplicationSettings:
    """
    Get cached application settings.
    Uses lru_cache to ensure settings are loaded only once.
    """
    return ApplicationSettings()


# Global settings instance
settings = get_settings()


# Settings validation utility
def validate_settings() -> Dict[str, Any]:
    """Validate all settings and return validation report"""
    try:
        settings = get_settings()
        return {
            "status": "valid",
            "environment": settings.environment,
            "debug": settings.debug,
            "database_configured": bool(settings.database.postgres_password),
            "ai_providers": {
                "openai": settings.ai.use_openai,
                "huggingface": settings.ai.use_huggingface,
                "local": settings.ai.use_local_models
            },
            "security_level": "high" if settings.is_production else "medium",
            "cache_enabled": bool(settings.cache.redis_host),
            "monitoring_enabled": settings.monitoring.enable_metrics
        }
    except Exception as e:
        return {
            "status": "invalid",
            "error": str(e),
            "details": "Settings validation failed"
        }


# Configuration interface implementation
from core.interfaces.config_interface import IConfigurationService

class PydanticConfigurationService(IConfigurationService):
    """Pydantic-based configuration service implementation"""
    
    def __init__(self):
        self._settings = get_settings()
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot notation"""
        try:
            keys = key.split('.')
            value = self._settings
            
            for k in keys:
                if hasattr(value, k):
                    value = getattr(value, k)
                else:
                    return default
            
            return value
        except Exception:
            return default
    
    def get_string(self, key: str, default: str = "") -> str:
        value = self.get(key, default)
        return str(value) if value is not None else default
    
    def get_int(self, key: str, default: int = 0) -> int:
        value = self.get(key, default)
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        value = self.get(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "on")
        return bool(value) if value is not None else default
    
    def get_list(self, key: str, default: List[Any] = None) -> List[Any]:
        value = self.get(key, default or [])
        return value if isinstance(value, list) else default or []
    
    def validate_required_configs(self, required_keys: List[str]) -> Dict[str, bool]:
        """Validate required configuration keys"""
        result = {}
        for key in required_keys:
            value = self.get(key)
            result[key] = value is not None and value != ""
        return result
    
    def is_production(self) -> bool:
        return self._settings.is_production
    
    def is_development(self) -> bool:
        return self._settings.is_development
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration dictionary"""
        return {
            "host": self._settings.database.postgres_host,
            "port": self._settings.database.postgres_port,
            "user": self._settings.database.postgres_user,
            "password": self._settings.database.postgres_password,
            "database": self._settings.database.postgres_db,
            "min_connections": self._settings.database.min_connections,
            "max_connections": self._settings.database.max_connections,
            "url": self._settings.database.database_url,
            "async_url": self._settings.database.async_database_url
        }
    
    def get_security_config(self) -> Dict[str, Any]:
        """Get security configuration dictionary"""
        return {
            "secret_key": self._settings.security.secret_key,
            "algorithm": self._settings.security.algorithm,
            "access_token_expire_minutes": self._settings.security.access_token_expire_minutes,
            "allowed_hosts": self._settings.security.allowed_hosts,
            "secure_cookies": self._settings.security.secure_cookies
        }
    
    def get_cors_config(self) -> Dict[str, Any]:
        """Get CORS configuration dictionary"""
        return {
            "allowed_origins": self._settings.security.allowed_origins,
            "allowed_methods": self._settings.security.allowed_methods,
            "allowed_headers": self._settings.security.allowed_headers,
            "allow_credentials": self._settings.security.allow_credentials
        }
    
    def get_ai_config(self) -> Dict[str, Any]:
        """Get AI configuration dictionary"""
        return {
            "use_openai": self._settings.ai.use_openai,
            "use_huggingface": self._settings.ai.use_huggingface,
            "use_local_models": self._settings.ai.use_local_models,
            "openai_api_key": self._settings.ai.openai_api_key,
            "openai_model": self._settings.ai.openai_model,
            "hf_model_name": self._settings.ai.hf_model_name,
            "sentence_model": self._settings.ai.sentence_model
        }
    
    def get_cache_config(self) -> Dict[str, Any]:
        """Get cache configuration dictionary"""
        return {
            "type": "redis",
            "redis_url": self._settings.cache.redis_url,
            "default_ttl": self._settings.cache.default_ttl,
            "session_ttl": self._settings.cache.session_ttl,
            "response_ttl": self._settings.cache.response_ttl
        }
