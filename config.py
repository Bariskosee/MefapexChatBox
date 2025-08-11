"""
🔧 MEFAPEX Configuration Manager
Centralized configuration for the entire application
"""
import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Base configuration class"""
    
    # Environment
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    DEBUG_MODE = os.getenv("DEBUG", "False").lower() == "true"
    
    # Security
    SECRET_KEY = os.getenv("SECRET_KEY")
    
    # AI Configuration
    USE_OPENAI = os.getenv("USE_OPENAI", "false").lower() == "true"
    USE_HUGGINGFACE = os.getenv("USE_HUGGINGFACE", "true").lower() == "true"
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL")
    POSTGRES_HOST = os.getenv("POSTGRES_HOST")
    POSTGRES_USER = os.getenv("POSTGRES_USER")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
    POSTGRES_DB = os.getenv("POSTGRES_DB")
    
    # Qdrant
    QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "200"))
    RATE_LIMIT_CHAT = int(os.getenv("RATE_LIMIT_CHAT", "100"))
    
    # CORS Settings
    ALLOWED_ORIGINS = [
        "http://localhost:3000",
        "http://localhost:8000",
        "https://mefapex.com",
        "https://www.mefapex.com"
    ]
    
    @classmethod
    def validate_production_config(cls):
        """Validate configuration for production environment"""
        if cls.ENVIRONMENT == "production":
            if cls.DEBUG_MODE:
                raise RuntimeError("DEBUG mode must be disabled in production")
            
            if not cls.SECRET_KEY:
                raise RuntimeError("SECRET_KEY is required in production")
            
            if cls.USE_OPENAI and not cls.OPENAI_API_KEY:
                raise RuntimeError("OPENAI_API_KEY is required when USE_OPENAI is enabled")

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG_MODE = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG_MODE = False

# Configuration factory
def get_config() -> Config:
    """Get configuration based on environment"""
    env = os.getenv("ENVIRONMENT", "development")
    
    if env == "production":
        config = ProductionConfig()
    else:
        config = DevelopmentConfig()
    
    # Validate configuration
    if env == "production":
        config.validate_production_config()
    
    return config

# Global config instance
config = get_config()
