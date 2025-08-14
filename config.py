"""
🔧 Simple Configuration for MEFAPEX Chatbot
Simplified configuration without complex factory patterns
"""
import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
LOGS_DIR = BASE_DIR / "logs"

# Ensure directories exist
LOGS_DIR.mkdir(exist_ok=True)

class Config:
    """Simple configuration class"""
    
    # Server settings
    DEBUG_MODE = os.getenv("DEBUG_MODE", "true").lower() == "true"
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 8000))
    WORKERS = int(os.getenv("WORKERS", 1))
    
    # Security
    SECRET_KEY = os.getenv("SECRET_KEY", "mefapex-secret-key-change-in-production")
    ALLOWED_ORIGINS = [
        "http://localhost:8000", 
        "http://127.0.0.1:8000",
        "http://0.0.0.0:8000",
        "http://10.0.0.69:8000",
        "*"  # Geçici olarak tüm originlere izin ver - Safari için
    ]
    
    # PostgreSQL Database
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", 5432))
    POSTGRES_DB = os.getenv("POSTGRES_DB", "mefapex_chatbot")
    POSTGRES_USER = os.getenv("POSTGRES_USER", "mefapex")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "mefapex")
    
    # AI Settings
    USE_OPENAI = os.getenv("USE_OPENAI", "false").lower() == "true"
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    USE_HUGGINGFACE = os.getenv("USE_HUGGINGFACE", "true").lower() == "true"
    
    # Rate limiting
    RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", 100))
    RATE_LIMIT_CHAT = int(os.getenv("RATE_LIMIT_CHAT", 50))
    RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", 3600))
    
    # Environment
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    
    # Redis Cache Settings
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")  # Default to localhost for local development
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    REDIS_DB = int(os.getenv("REDIS_DB", 0))
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
    REDIS_URL = os.getenv("REDIS_URL", f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}")
    
    # Cache Configuration
    CACHE_TYPE = os.getenv("CACHE_TYPE", "hybrid")  # hybrid, redis, local
    CACHE_SIZE = int(os.getenv("CACHE_SIZE", 1000))  # For local cache
    CACHE_TTL = int(os.getenv("CACHE_TTL", 3600))  # 1 hour default TTL
    CACHE_LOCAL_SIZE = int(os.getenv("CACHE_LOCAL_SIZE", 500))  # Local cache in hybrid mode
    CACHE_LOCAL_TTL = int(os.getenv("CACHE_LOCAL_TTL", 1800))  # 30 minutes for local cache
    CACHE_REDIS_TTL = int(os.getenv("CACHE_REDIS_TTL", 3600))  # 1 hour for Redis cache
    NODE_ID = os.getenv("NODE_ID", f"node-{os.getpid()}")  # Unique node identifier
    
    # Brute force protection
    MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", 5))
    LOCKOUT_DURATION = int(os.getenv("LOCKOUT_DURATION", 900))  # 15 minutes
    
    # Demo user
    DEMO_USER_ENABLED = os.getenv("DEMO_USER_ENABLED", "true").lower() == "true"
    DEMO_USERNAME = os.getenv("DEMO_USERNAME", "demo")
    DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "1234")
    
    # Memory Management Settings for AI Models
    MEMORY_THRESHOLD_MB = int(os.getenv("MEMORY_THRESHOLD_MB", 1536))  # 1.5GB for AI models
    MODEL_CACHE_SIZE = int(os.getenv("MODEL_CACHE_SIZE", 100))  # Reduced cache size
    FORCE_GC_INTERVAL = int(os.getenv("FORCE_GC_INTERVAL", 50))  # Every N operations
    MEMORY_MONITOR_INTERVAL = int(os.getenv("MEMORY_MONITOR_INTERVAL", 60))  # seconds

# Global config instance
config = Config()
