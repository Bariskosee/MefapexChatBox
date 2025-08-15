#!/usr/bin/env python3
"""
🚀 MEFAPEX Server Runner
Direct server startup with environment configuration
"""

import os
import uvicorn

# Set environment variables
os.environ["POSTGRES_HOST"] = "localhost"
os.environ["POSTGRES_PORT"] = "5432"
os.environ["POSTGRES_USER"] = "mefapex"
os.environ["POSTGRES_PASSWORD"] = "mefapex"
os.environ["POSTGRES_DB"] = "mefapex_chatbot"
os.environ["SECRET_KEY"] = "mefapex-secret-key-change-in-production"
os.environ["DEBUG"] = "true"
os.environ["ENVIRONMENT"] = "development"

# Server settings for Safari compatibility
os.environ["HOST"] = "0.0.0.0"  # Accept connections from all interfaces
os.environ["PORT"] = "8000"
os.environ["ALLOWED_ORIGINS"] = "http://localhost:8000,http://127.0.0.1:8000,http://0.0.0.0:8000,*"

# Redis settings
os.environ["REDIS_HOST"] = "localhost"
os.environ["REDIS_PORT"] = "6379"

if __name__ == "__main__":
    print("🚀 Starting MEFAPEX Chatbot Server...")
    print("Environment variables configured:")
    print(f"  POSTGRES_HOST={os.environ['POSTGRES_HOST']}")
    print(f"  POSTGRES_PORT={os.environ['POSTGRES_PORT']}")
    print(f"  POSTGRES_USER={os.environ['POSTGRES_USER']}")
    print(f"  POSTGRES_DB={os.environ['POSTGRES_DB']}")
    print(f"  HOST={os.environ['HOST']}")
    print(f"  PORT={os.environ['PORT']}")
    print()
    
    # Start server with uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",  # Accept from all interfaces for Safari compatibility
        port=8000,
        reload=True,
        log_level="info"
    )
