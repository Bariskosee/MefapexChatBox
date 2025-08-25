#!/usr/bin/env python3
"""
Debug script to isolate startup issues
"""
import sys
import time

print("🔍 Debug: Python interpreter started")

try:
    print("🔍 Debug: Testing basic imports...")
    import logging
    print("✅ logging imported")
    
    import asyncio
    print("✅ asyncio imported")
    
    from contextlib import asynccontextmanager
    print("✅ contextlib imported")
    
    from fastapi import FastAPI
    print("✅ FastAPI imported")
    
    print("🔍 Debug: Testing configuration import...")
    from core.configuration import get_config
    print("✅ core.configuration imported")
    
    print("🔍 Debug: Getting config...")
    main_config = get_config()
    print("✅ Configuration loaded")
    
    print("🔍 Debug: Testing startup manager import...")
    from startup import StartupManager
    print("✅ StartupManager imported")
    
    print("🔍 Debug: Testing database manager import...")
    from database.manager import db_manager
    print("✅ Database manager imported")
    
    print("🔍 Debug: Testing database health check...")
    health = db_manager.health_check()
    print(f"✅ Database health: {health}")
    
    print("🔍 Debug: Testing Turkish content import...")
    from improved_turkish_content_manager import improved_turkish_content
    print("✅ Turkish content manager imported")
    
    print("🔍 Debug: Testing unified microservice import...")
    from unified_microservice_architecture import initialize_unified_architecture
    print("✅ Unified microservice imported")
    
    print("🔍 Debug: All imports successful!")
    
except Exception as e:
    print(f"❌ Debug: Error at import: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("🔍 Debug: Script completed successfully")
