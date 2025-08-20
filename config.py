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
    MEMORY_THRESHOLD_MB = int(os.getenv("MEMORY_THRESHOLD_MB", 2048))  # 2GB for AI models (increased)
    MODEL_CACHE_SIZE = int(os.getenv("MODEL_CACHE_SIZE", 50))  # Dramatically reduced cache size
    FORCE_GC_INTERVAL = int(os.getenv("FORCE_GC_INTERVAL", 20))  # More frequent GC
    MEMORY_MONITOR_INTERVAL = int(os.getenv("MEMORY_MONITOR_INTERVAL", 30))  # More frequent monitoring
    
    # Emergency mode settings
    EMERGENCY_MODE = os.getenv("EMERGENCY_MODE", "false").lower() == "true"
    DISABLE_AI_MODELS = os.getenv("DISABLE_AI_MODELS", "false").lower() == "true"

# Global config instance
config = Config()



# 🚨 EMERGENCY MEMORY LEAK FIXES
# ==============================

# Memory thresholds (realistic for AI models)
MEMORY_THRESHOLD_MB = 2048  # Increased from 1536 (more realistic)
MODEL_CACHE_SIZE = 25       # Reduced from 100 (50% reduction)
FORCE_GC_INTERVAL = 15      # Reduced from 50 (more frequent cleanup)
EMERGENCY_MODE = False      # Enable to disable AI models
DISABLE_AI_MODELS = False   # Emergency AI model disabling

# Cache optimizations  
LRU_CACHE_SIZE = 50         # Reduced from 1000 (95% reduction)
SIMILARITY_CACHE_SIZE = 50  # New: limit similarity cache
TEXT_LENGTH_LIMIT = 500     # New: limit text processing length

# Garbage collection
AUTO_GC_ENABLED = True      # Enable automatic garbage collection
GC_THRESHOLD_FACTOR = 0.7   # GC when 70% of threshold reached
PERIODIC_GC_INTERVAL = 30   # GC every 30 operations

# Memory monitoring
MEMORY_MONITOR_INTERVAL = 30    # Monitor every 30 seconds
MEMORY_ALERT_THRESHOLD = 3072   # Alert at 3GB
MEMORY_EMERGENCY_THRESHOLD = 3584  # Emergency at 3.5GB

# Model optimization
MODEL_LAZY_LOADING = True       # Enable lazy loading
MODEL_AUTO_UNLOAD = True        # Auto-unload idle models
MODEL_IDLE_TIMEOUT = 600        # 10 minutes idle timeout


# 🚨 ULTRA MEMORY OPTIMIZATION SETTINGS
# ====================================
# Added by ultra memory optimization script

# Ultra-aggressive memory limits
MEMORY_THRESHOLD_MB=1024  # 1GB limit (was 2GB)
MAX_MODEL_MEMORY_MB=512   # 512MB per model max
EMERGENCY_MODE=true       # Force emergency mode

# Ultra-small cache sizes
MODEL_CACHE_SIZE=5        # Minimal model cache
LRU_CACHE_SIZE=5          # Minimal LRU cache
EMBEDDING_CACHE_SIZE=5    # Minimal embedding cache

# Aggressive cleanup
GC_FREQUENCY=5            # Garbage collect every 5 operations
AUTO_UNLOAD_TIMEOUT=120   # Auto-unload models after 2 minutes

# Text processing limits
MAX_TEXT_LENGTH=100       # Limit text to 100 chars
MAX_BATCH_SIZE=1          # Process one item at a time

# Disable heavy features in ultra mode
DISABLE_TEXT_GENERATION=true    # Disable text generation
DISABLE_LARGE_MODELS=true       # Disable large models
FORCE_CPU_ONLY=true             # Force CPU processing only

# Ultra-aggressive monitoring
MEMORY_CHECK_INTERVAL=30        # Check memory every 30 seconds
FORCE_CLEANUP_THRESHOLD=900     # Force cleanup at 900MB

export MEMORY_THRESHOLD_MB MODEL_CACHE_SIZE LRU_CACHE_SIZE EMERGENCY_MODE
export DISABLE_TEXT_GENERATION DISABLE_LARGE_MODELS FORCE_CPU_ONLY
export GC_FREQUENCY AUTO_UNLOAD_TIMEOUT MAX_TEXT_LENGTH MAX_BATCH_SIZE
