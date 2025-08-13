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
    
    # Brute force protection
    MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", 5))
    LOCKOUT_DURATION = int(os.getenv("LOCKOUT_DURATION", 900))  # 15 minutes
    
    # Demo user
    DEMO_USER_ENABLED = os.getenv("DEMO_USER_ENABLED", "true").lower() == "true"
    DEMO_USERNAME = os.getenv("DEMO_USERNAME", "demo")
    DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "1234")

# Global config instance
config = Config()
