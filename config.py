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
    
    # Distributed WebSocket Settings
    DISTRIBUTED_WEBSOCKET_ENABLED = os.getenv("DISTRIBUTED_WEBSOCKET_ENABLED", "true").lower() == "true"
    WEBSOCKET_SESSION_TTL = int(os.getenv("WEBSOCKET_SESSION_TTL", 3600))  # 1 hour
    WORKER_ID = os.getenv("WORKER_ID", None)  # Auto-generated if not set
    NODE_ID = os.getenv("NODE_ID", f"node-{os.getpid()}")  # Unique node identifier
    
    # Cache Configuration with size limits and eviction policies
    CACHE_TYPE = os.getenv("CACHE_TYPE", "hybrid")  # hybrid, redis, local
    
    # Response Cache Settings
    RESPONSE_CACHE_ENABLED = os.getenv("RESPONSE_CACHE_ENABLED", "true").lower() == "true"
    RESPONSE_CACHE_MAX_SIZE = int(os.getenv("RESPONSE_CACHE_MAX_SIZE", "1000"))
    RESPONSE_CACHE_TTL = int(os.getenv("RESPONSE_CACHE_TTL", "3600"))  # 1 hour default TTL
    RESPONSE_CACHE_EVICTION_POLICY = os.getenv("RESPONSE_CACHE_EVICTION_POLICY", "lru")  # lru, fifo, lfu, random, ttl_aware
    
    # Distributed Cache Settings
    DISTRIBUTED_CACHE_ENABLED = os.getenv("DISTRIBUTED_CACHE_ENABLED", "true").lower() == "true"
    LOCAL_CACHE_MAX_SIZE = int(os.getenv("LOCAL_CACHE_MAX_SIZE", "500"))  # Local cache in hybrid mode
    LOCAL_CACHE_TTL = int(os.getenv("LOCAL_CACHE_TTL", "1800"))  # 30 minutes for local cache
    REDIS_CACHE_TTL = int(os.getenv("REDIS_CACHE_TTL", "3600"))  # 1 hour for Redis cache
    REDIS_MAX_ENTRIES = int(os.getenv("REDIS_MAX_ENTRIES", "10000"))  # Maximum Redis entries
    
    # Cache Memory Management
    CACHE_MAX_MEMORY_MB = int(os.getenv("CACHE_MAX_MEMORY_MB", "100"))  # Maximum cache memory usage
    CACHE_CLEANUP_INTERVAL = int(os.getenv("CACHE_CLEANUP_INTERVAL", "300"))  # 5 minutes cleanup interval
    CACHE_MEMORY_CHECK_INTERVAL = int(os.getenv("CACHE_MEMORY_CHECK_INTERVAL", "60"))  # Memory check interval
    
    # Cache Auto-scaling
    CACHE_AUTO_SCALE_ENABLED = os.getenv("CACHE_AUTO_SCALE_ENABLED", "true").lower() == "true"
    CACHE_SCALE_DOWN_THRESHOLD = float(os.getenv("CACHE_SCALE_DOWN_THRESHOLD", "0.5"))  # Scale down when usage < 50%
    CACHE_SCALE_UP_THRESHOLD = float(os.getenv("CACHE_SCALE_UP_THRESHOLD", "0.9"))    # Scale up when usage > 90%
    CACHE_MIN_SIZE = int(os.getenv("CACHE_MIN_SIZE", "100"))
    CACHE_MAX_SIZE = int(os.getenv("CACHE_MAX_SIZE", "10000"))
    
    # Legacy cache settings (for backward compatibility)
    CACHE_SIZE = RESPONSE_CACHE_MAX_SIZE  # Backward compatibility
    CACHE_TTL = RESPONSE_CACHE_TTL       # Backward compatibility
    CACHE_LOCAL_SIZE = LOCAL_CACHE_MAX_SIZE  # Backward compatibility
    
    # Brute force protection
    MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", 5))
    LOCKOUT_DURATION = int(os.getenv("LOCKOUT_DURATION", 900))  # 15 minutes
    
    # Demo user
    DEMO_USER_ENABLED = os.getenv("DEMO_USER_ENABLED", "true").lower() == "true"
    DEMO_USERNAME = os.getenv("DEMO_USERNAME", "demo")
    DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "1234")
    
    # Memory Management Settings for AI Models
    MEMORY_THRESHOLD_MB = int(os.getenv("MEMORY_THRESHOLD_MB", 6144))  # AI MODEL FIX: 6GB realistic for AI models
    MODEL_CACHE_SIZE = int(os.getenv("MODEL_CACHE_SIZE", 100))  # AI MODEL FIX: Realistic cache size for AI models
    FORCE_GC_INTERVAL = int(os.getenv("FORCE_GC_INTERVAL", 50))  # AI MODEL FIX: Balanced GC frequency
    MEMORY_MONITOR_INTERVAL = int(os.getenv("MEMORY_MONITOR_INTERVAL", 45))  # AI MODEL FIX: Balanced monitoring
    
    # Emergency mode settings
    EMERGENCY_MODE = os.getenv("EMERGENCY_MODE", "false").lower() == "true"
    DISABLE_AI_MODELS = os.getenv("DISABLE_AI_MODELS", "false").lower() == "true"

# Global config instance
config = Config()



# AI MODEL FIX: Realistic memory thresholds for production AI systems
# ==============================

# Memory thresholds (realistic for AI models in production)
MEMORY_THRESHOLD_MB = 6144  # AI MODEL FIX: 6GB realistic for AI models (was 1536/2048)
MODEL_CACHE_SIZE = 100       # AI MODEL FIX: Realistic cache size (was 25/100)
FORCE_GC_INTERVAL = 50      # AI MODEL FIX: Balanced cleanup frequency (was 15)
EMERGENCY_MODE = False      # AI MODEL FIX: Disable for normal operations
DISABLE_AI_MODELS = False   # AI MODEL FIX: Enable AI models for production

# Cache optimizations balanced for AI performance
LRU_CACHE_SIZE = 100         # AI MODEL FIX: Realistic cache size (was 50)
SIMILARITY_CACHE_SIZE = 100  # AI MODEL FIX: Realistic similarity cache (was 50)
TEXT_LENGTH_LIMIT = 800     # AI MODEL FIX: Reasonable text length (was 500)

# Balanced garbage collection for AI workloads
AUTO_GC_ENABLED = True      # Enable automatic garbage collection
GC_THRESHOLD_FACTOR = 0.8   # AI MODEL FIX: Less aggressive - GC at 80% (was 70%)
PERIODIC_GC_INTERVAL = 50   # AI MODEL FIX: GC every 50 operations (was 30)

# Balanced memory monitoring for AI systems
MEMORY_MONITOR_INTERVAL = 45    # AI MODEL FIX: Monitor every 45 seconds (was 30)
MEMORY_ALERT_THRESHOLD = 5120   # AI MODEL FIX: Alert at 5GB (was 3GB)
MEMORY_EMERGENCY_THRESHOLD = 5632  # AI MODEL FIX: Emergency at 5.5GB (was 3.5GB)

# AI Model optimization settings
MODEL_LAZY_LOADING = True       # Enable lazy loading
MODEL_AUTO_UNLOAD = True        # Auto-unload idle models
MODEL_IDLE_TIMEOUT = 900        # AI MODEL FIX: 15 minutes idle timeout (was 10 minutes)


# AI MODEL FIX: Realistic memory optimization settings for production AI models
# ====================================

# Realistic memory limits for AI models
MEMORY_THRESHOLD_MB = 6144  # AI MODEL FIX: 6GB realistic for AI models (was 1GB/2GB)
MAX_MODEL_MEMORY_MB = 2048   # AI MODEL FIX: 2GB per model reasonable (was 512MB)
EMERGENCY_MODE = False       # AI MODEL FIX: Disable emergency mode for normal operation

# Balanced cache sizes for AI performance
MODEL_CACHE_SIZE = 100        # AI MODEL FIX: Realistic model cache (was 5)
LRU_CACHE_SIZE = 100          # AI MODEL FIX: Realistic LRU cache (was 5)
EMBEDDING_CACHE_SIZE = 100    # AI MODEL FIX: Realistic embedding cache (was 5)

# Balanced cleanup for AI models
GC_FREQUENCY = 50            # AI MODEL FIX: Balanced garbage collection (was 5)
AUTO_UNLOAD_TIMEOUT = 900    # AI MODEL FIX: 15 minutes idle timeout (was 2 minutes)

# Reasonable text processing limits
MAX_TEXT_LENGTH = 800       # AI MODEL FIX: Reasonable text length (was 100 chars)
MAX_BATCH_SIZE = 4          # AI MODEL FIX: Small but workable batch size (was 1)

# Enable all AI features for production use
DISABLE_TEXT_GENERATION = False    # AI MODEL FIX: Enable text generation
DISABLE_LARGE_MODELS = False       # AI MODEL FIX: Enable large models
FORCE_CPU_ONLY = False             # AI MODEL FIX: Allow GPU acceleration

# Balanced monitoring for AI models
MEMORY_CHECK_INTERVAL = 45        # AI MODEL FIX: Check memory every 45 seconds (was 30)
FORCE_CLEANUP_THRESHOLD = 5500     # AI MODEL FIX: Cleanup at 5.5GB (was 900MB)
