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

from database.manager import db_manager
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
        
        # Model manager health with lazy loading info
        model_health = {
            "status": "healthy" if model_manager else "unavailable",
            "models_loaded": getattr(model_manager, 'models_loaded', 0)
        }
        
        # Add lazy loading stats if available
        if model_manager and hasattr(model_manager, 'get_lazy_loading_statistics'):
            try:
                lazy_stats = model_manager.get_lazy_loading_statistics()
                model_health["lazy_loading"] = {
                    "enabled": True,
                    "models_currently_loaded": sum(lazy_stats["current_state"]["models_loaded"].values()),
                    "memory_usage_mb": lazy_stats["current_state"]["memory_usage_mb"],
                    "auto_cleanup": lazy_stats["config"]["auto_cleanup"]
                }
            except Exception as e:
                logger.warning(f"Failed to get lazy loading stats: {e}")
                model_health["lazy_loading"] = {"enabled": False, "error": str(e)}
        
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

@router.get("/ai")
async def ai_health():
    """
    🤖 Get detailed AI model health and lazy loading performance
    """
    try:
        if not model_manager:
            return {
                "status": "unavailable",
                "error": "Model manager not initialized"
            }
        
        # Get comprehensive model information
        model_info = model_manager.get_model_info()
        
        # Get lazy loading statistics if available
        lazy_stats = None
        if hasattr(model_manager, 'get_lazy_loading_statistics'):
            lazy_stats = model_manager.get_lazy_loading_statistics()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "models": model_info,
            "lazy_loading": lazy_stats,
            "optimization": {
                "lazy_loading_enabled": lazy_stats is not None,
                "memory_efficient_caching": True,
                "auto_cleanup": lazy_stats["config"]["auto_cleanup"] if lazy_stats else False,
                "turkish_language_optimization": model_info.get("prefer_turkish_models", False)
            }
        }
        
    except Exception as e:
        logger.error(f"AI health check failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@router.get("/ai/models")
async def models_status():
    """
    📊 Get current model loading status and performance metrics
    """
    try:
        if not model_manager:
            return {
                "status": "unavailable",
                "error": "Model manager not initialized"
            }
        
        lazy_stats = None
        if hasattr(model_manager, 'get_lazy_loading_statistics'):
            lazy_stats = model_manager.get_lazy_loading_statistics()
        
        return {
            "status": "healthy",
            "lazy_loading_enabled": lazy_stats is not None,
            "lazy_loading_stats": lazy_stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Model status check failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@router.get("/cache")
async def cache_health():
    """
    🗄️ Get cache health status and metrics
    """
    try:
        # Try to import cache manager
        try:
            from cache_manager import get_cache_manager, get_cache_health, get_cache_metrics
            cache_health_data = await get_cache_health()
            cache_metrics = await get_cache_metrics()
            
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "health": cache_health_data,
                "metrics": cache_metrics
            }
        except ImportError:
            # Fallback to basic cache info
            return {
                "status": "basic",
                "timestamp": datetime.utcnow().isoformat(),
                "message": "Using basic cache implementation",
                "cache_manager_available": False
            }
        
    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@router.get("/cache/stats")
async def cache_stats():
    """
    📊 Get detailed cache statistics and performance metrics
    """
    try:
        try:
            from cache_manager import get_cache_metrics, get_cache_manager
            cache_manager = get_cache_manager()
            
            if not cache_manager.initialized:
                return {
                    "status": "not_initialized",
                    "message": "Cache manager not initialized"
                }
            
            metrics = await get_cache_metrics()
            
            # Add performance analysis
            analysis = {}
            if 'response_cache' in metrics:
                rc_stats = metrics['response_cache']
                hit_rate = rc_stats.get('hit_rate', 0)
                
                if hit_rate > 80:
                    analysis['response_cache'] = "excellent"
                elif hit_rate > 60:
                    analysis['response_cache'] = "good"
                elif hit_rate > 40:
                    analysis['response_cache'] = "fair"
                else:
                    analysis['response_cache'] = "poor"
            
            if 'distributed_cache' in metrics:
                dc_stats = metrics['distributed_cache']
                redis_available = dc_stats.get('redis_available', False)
                analysis['distributed_cache'] = "redis_enabled" if redis_available else "local_only"
            
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "metrics": metrics,
                "performance_analysis": analysis
            }
            
        except ImportError:
            return {
                "status": "basic",
                "timestamp": datetime.utcnow().isoformat(),
                "message": "Advanced cache statistics not available"
            }
        
    except Exception as e:
        logger.error(f"Cache stats retrieval failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@router.post("/cache/optimize")
async def optimize_caches():
    """
    🔧 Manually optimize all cache instances
    """
    try:
        try:
            from cache_manager import optimize_all_caches
            await optimize_all_caches()
            
            return {
                "status": "success",
                "message": "Cache optimization completed",
                "timestamp": datetime.utcnow().isoformat()
            }
        except ImportError:
            return {
                "status": "unavailable",
                "message": "Cache optimization not available in basic mode"
            }
        
    except Exception as e:
        logger.error(f"Cache optimization failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@router.post("/cache/clear")
async def clear_caches():
    """
    🗑️ Clear all cache instances (use with caution)
    """
    try:
        try:
            from cache_manager import clear_all_caches
            await clear_all_caches()
            
            return {
                "status": "success",
                "message": "All caches cleared",
                "timestamp": datetime.utcnow().isoformat()
            }
        except ImportError:
            return {
                "status": "unavailable",
                "message": "Cache clearing not available in basic mode"
            }
        
    except Exception as e:
        logger.error(f"Cache clearing failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
