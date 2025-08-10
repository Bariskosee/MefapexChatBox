"""
🏥 Health Check Router
System health monitoring and diagnostics
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)

# Router
router = APIRouter(prefix="/health", tags=["health"])

# Dependencies (will be injected from main)
db_manager = None
qdrant_client = None
websocket_manager = None
memory_monitor = None
ai_config = {}

def init_health_router(database_manager, qdrant, ws_manager, mem_monitor, config):
    """Initialize router with dependencies from main app"""
    global db_manager, qdrant_client, websocket_manager, memory_monitor, ai_config
    db_manager = database_manager
    qdrant_client = qdrant
    websocket_manager = ws_manager
    memory_monitor = mem_monitor
    ai_config = config

@router.get("/")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "MEFAPEX ChatBot",
        "version": "2.0.0"
    }

@router.get("/comprehensive")
async def comprehensive_health_check():
    """Comprehensive health check with all system components"""
    try:
        health_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "service": "MEFAPEX ChatBot",
            "version": "2.0.0",
            "environment": os.getenv("ENVIRONMENT", "development"),
            "status": "healthy",
            "checks": {}
        }
        
        # 1. 🗄️ Database Health Check
        try:
            stats = db_manager.get_stats()
            health_data["checks"]["database"] = {
                "status": "healthy" if stats["users"] >= 0 else "error",
                "users": stats["users"],
                "sessions": stats["sessions"], 
                "messages": stats["messages"],
                "messages_24h": stats["messages_24h"],
                "pool_connections": f"{stats['pool_active_connections']}/{stats['pool_max_connections']}"
            }
        except Exception as e:
            health_data["checks"]["database"] = {"status": "error", "error": str(e)}
        
        # 2. 🔍 Qdrant Vector Database Check
        try:
            collection_info = qdrant_client.get_collection("mefapex_faq")
            points_count = collection_info.points_count
            
            health_data["checks"]["qdrant"] = {
                "status": "healthy" if points_count > 0 else "warning",
                "points_count": points_count,
                "vectors_count": collection_info.vectors_count
            }
        except Exception as e:
            health_data["checks"]["qdrant"] = {"status": "error", "error": str(e)}
        
        # 3. 🤖 AI Services Check
        try:
            ai_status = {
                "openai": "configured" if ai_config.get('USE_OPENAI') and ai_config.get('OPENAI_API_KEY') else "disabled",
                "huggingface": "configured" if ai_config.get('USE_HUGGINGFACE') else "disabled"
            }
            
            health_data["checks"]["ai_services"] = {
                "status": "healthy" if any(status == "configured" for status in ai_status.values()) else "warning",
                "services": ai_status
            }
        except Exception as e:
            health_data["checks"]["ai_services"] = {"status": "error", "error": str(e)}
        
        # 4. 🧠 Memory Check
        try:
            if memory_monitor:
                memory_stats = memory_monitor.get_memory_stats()
                memory_usage = memory_stats.get("memory_percent", 0)
                
                health_data["checks"]["memory"] = {
                    "status": "healthy" if memory_usage < 80 else "warning" if memory_usage < 90 else "critical",
                    "usage_percent": memory_usage,
                    "available_gb": memory_stats.get("available_gb", 0)
                }
            else:
                health_data["checks"]["memory"] = {"status": "info", "message": "Memory monitoring not available"}
        except Exception as e:
            health_data["checks"]["memory"] = {"status": "error", "error": str(e)}
        
        # 5. 💾 Disk Space Check
        try:
            import shutil
            total, used, free = shutil.disk_usage("/")
            free_percent = (free / total) * 100
            
            health_data["checks"]["disk"] = {
                "status": "healthy" if free_percent > 20 else "warning" if free_percent > 10 else "critical",
                "free_percent": round(free_percent, 2),
                "free_gb": round(free / (1024**3), 2)
            }
        except Exception as e:
            health_data["checks"]["disk"] = {"status": "error", "error": str(e)}
        
        # 6. 🗂️ Cache Health Check (Response Cache)
        try:
            # Check if we have access to the AI generator cache
            from routers.chat import ai_generator
            cache_size = len(ai_generator._response_cache)
            
            health_data["checks"]["cache"] = {
                "status": "healthy",
                "size": cache_size,
                "max_size": ai_generator.cache_max_size
            }
        except Exception as e:
            health_data["checks"]["cache"] = {"status": "error", "error": str(e)}
        
        # 7. 🔌 WebSocket Connections Check
        try:
            if websocket_manager:
                ws_stats = websocket_manager.get_connection_stats()
                active_connections = ws_stats.get("active_connections", 0)
                
                health_data["checks"]["websockets"] = {
                    "status": "healthy" if active_connections < 100 else "warning",
                    "active_connections": active_connections,
                    "total_connections": ws_stats.get("total_connections", 0)
                }
            else:
                health_data["checks"]["websockets"] = {"status": "info", "message": "WebSocket manager not available"}
        except Exception as e:
            health_data["checks"]["websockets"] = {"status": "error", "error": str(e)}
        
        # 8. 🔐 Security Check
        try:
            DEBUG_MODE = os.getenv("DEBUG", "False").lower() == "true"
            SECRET_KEY = os.getenv("SECRET_KEY", "")
            ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
            
            cors_origins = os.getenv("CORS_ORIGINS", "").split(",") if os.getenv("CORS_ORIGINS") else []
            
            security_checks = {
                "debug_mode": not DEBUG_MODE,
                "secure_secret_key": SECRET_KEY != "your-secret-key-change-this-in-production",
                "environment": ENVIRONMENT,
                "cors_configured": len(cors_origins) > 0 and "*" not in cors_origins
            }
            
            security_issues = [k for k, v in security_checks.items() if not v]
            
            health_data["checks"]["security"] = {
                "status": "healthy" if not security_issues else "warning",
                "checks": security_checks,
                "issues": security_issues
            }
        except Exception as e:
            health_data["checks"]["security"] = {"status": "error", "error": str(e)}
        
        # Overall Status Calculation
        check_statuses = [check.get("status", "error") for check in health_data["checks"].values()]
        
        if "critical" in check_statuses:
            health_data["status"] = "critical"
        elif "error" in check_statuses:
            health_data["status"] = "error"  
        elif "warning" in check_statuses:
            health_data["status"] = "warning"
        else:
            health_data["status"] = "healthy"
        
        # Add summary metrics
        health_data["metrics"] = {
            "uptime_seconds": (datetime.utcnow() - db_manager.created_at).total_seconds() if hasattr(db_manager, 'created_at') else 0,
            "total_checks": len(health_data["checks"]),
            "healthy_checks": len([s for s in check_statuses if s == "healthy"]),
            "warning_checks": len([s for s in check_statuses if s == "warning"]),
            "critical_checks": len([s for s in check_statuses if s == "critical"]),
            "error_checks": len([s for s in check_statuses if s == "error"])
        }
        
        # Return appropriate HTTP status
        if health_data["status"] in ["critical", "error"]:
            return JSONResponse(
                status_code=503,  # Service Unavailable
                content=health_data
            )
        elif health_data["status"] == "warning":
            return JSONResponse(
                status_code=200,  # OK but with warnings
                content=health_data
            )
        else:
            return health_data
            
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "timestamp": datetime.utcnow().isoformat(),
                "status": "error",
                "error": str(e),
                "checks": {}
            }
        )
