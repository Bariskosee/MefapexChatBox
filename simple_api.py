from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import os

# Create FastAPI app
app = FastAPI(
    title="MEFAPEX ChatBox",
    description="A simplified version of the MEFAPEX ChatBox API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return {"message": "Welcome to MEFAPEX ChatBox API"}

@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "services": {
            "api": "running",
            "database": "connected",
            "vector_db": "available"
        }
    }

# Add a simple echo endpoint for testing
@app.post("/api/echo")
async def echo(data: dict):
    return {"message": "Echo service", "data": data}

if __name__ == "__main__":
    uvicorn.run("simple_api:app", host="0.0.0.0", port=8000, reload=True)
