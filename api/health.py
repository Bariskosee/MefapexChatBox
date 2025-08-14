"""
🏥 Health Check API Routes
System health, monitoring, and diagnostics
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any
import logging
import time
import psutil
from datetime import datetime

from database_manager import db_manager
from model_manager import model_manager
from core.configuration import get_config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/health", tags=["health"])

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    environment: str
    uptime_seconds: float
    services: Dict[str, Any]

@router.get("/", response_model=HealthResponse)
async def health_check():
    """Comprehensive health check"""
    start_time = time.time()
    
    try:
        # Database health
        db_health = db_manager.health_check() if hasattr(db_manager, 'health_check') else {"status": "unknown"}
        
        # Model manager health
        model_health = {
            "status": "healthy" if model_manager else "unavailable",
            "models_loaded": getattr(model_manager, 'models_loaded', 0)
        }
        
        # System metrics
        system_metrics = {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent
        }
        
        # Overall status
        all_healthy = (
            db_health.get("status") == "healthy" and
            model_health.get("status") == "healthy" and
            system_metrics["memory_percent"] < 90 and
            system_metrics["cpu_percent"] < 90
        )
        
        overall_status = "healthy" if all_healthy else "degraded"
        
        response_time = (time.time() - start_time) * 1000
        
        return HealthResponse(
            status=overall_status,
            timestamp=datetime.utcnow().isoformat(),
            environment=get_config().environment.value,
            uptime_seconds=time.time(),  # This should be calculated from startup time
            services={
                "database": db_health,
                "models": model_health,
                "system": system_metrics,
                "response_time_ms": round(response_time, 2)
            }
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.utcnow().isoformat(),
            environment=get_config().environment.value,
            uptime_seconds=0,
            services={"error": str(e)}
        )

@router.get("/database")
async def database_health():
    """Database-specific health check"""
    try:
        if hasattr(db_manager, 'health_check'):
            health = db_manager.health_check()
        else:
            # Basic database test
            stats = db_manager.get_stats()
            health = {
                "status": "healthy",
                "stats": stats
            }
        
        return health
        
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Database health check failed: {str(e)}"
        )

@router.get("/stats")
async def get_system_stats():
    """Get detailed system statistics"""
    try:
        # Database stats
        db_stats = db_manager.get_stats()
        
        # System stats
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "database": db_stats,
            "system": {
                "cpu_percent": psutil.cpu_percent(),
                "memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2),
                    "percent": memory.percent
                },
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "percent": round((disk.used / disk.total) * 100, 2)
                }
            },
            "environment": get_config().environment.value,
            "debug_mode": get_config().server.debug
        }
        
    except Exception as e:
        logger.error(f"Stats retrieval failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve system stats"
        )
