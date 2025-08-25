#!/usr/bin/env python3
"""
🧪 Simple Test Server
Minimal FastAPI server to test basic functionality
"""
import logging
from fastapi import FastAPI
import uvicorn

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create simple FastAPI app
app = FastAPI(title="MEFAPEX Test Server")

@app.get("/")
async def root():
    return {"message": "Hello from MEFAPEX Test Server", "status": "OK"}

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": "now"}

@app.get("/test")
async def test():
    logger.info("Test endpoint called")
    return {"test": "success", "message": "Server is working!"}

if __name__ == "__main__":
    print("🚀 Starting simple test server...")
    print("📍 http://localhost:8000")
    print("🔍 http://localhost:8000/docs")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
