#!/usr/bin/env python3
"""
🚨 MEFAPEX Emergency Memory Manager
==================================
Emergency memory leak mitigation and monitoring
"""

import os
import gc
import time
import logging
import psutil
from typing import Dict, Any

logger = logging.getLogger(__name__)

class EmergencyMemoryManager:
    """Emergency memory management for critical situations"""
    
    def __init__(self):
        self.emergency_threshold_mb = 3584  # 3.5GB
        self.critical_threshold_mb = 4096   # 4GB  
        self.monitoring = False
        
    def get_memory_status(self) -> Dict[str, Any]:
        """Get current memory status"""
        try:
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            memory_percent = process.memory_percent()
            
            status = "NORMAL"
            if memory_mb > self.critical_threshold_mb:
                status = "CRITICAL"
            elif memory_mb > self.emergency_threshold_mb:
                status = "EMERGENCY"
            
            return {
                "memory_mb": memory_mb,
                "memory_percent": memory_percent,
                "status": status,
                "emergency": memory_mb > self.emergency_threshold_mb,
                "critical": memory_mb > self.critical_threshold_mb
            }
        except:
            return {"error": "Cannot get memory status"}
    
    def emergency_cleanup(self):
        """Emergency memory cleanup"""
        logger.warning("🚨 EMERGENCY MEMORY CLEANUP INITIATED")
        
        try:
            # Clear all possible caches
            gc.collect()
            
            # Try to clear model caches if available
            try:
                from model_manager import model_manager
                if hasattr(model_manager, 'clear_caches'):
                    model_manager.clear_caches()
                    logger.info("   ✅ Model caches cleared")
            except:
                pass
            
            # Try to clear question matcher caches
            try:
                from enhanced_question_matcher import enhanced_question_matcher
                if hasattr(enhanced_question_matcher, 'clear_all_caches'):
                    enhanced_question_matcher.clear_all_caches()
                    logger.info("   ✅ Question matcher caches cleared")
            except:
                pass
            
            # Force garbage collection multiple times
            for i in range(3):
                collected = gc.collect()
                logger.info(f"   🧹 GC run {i+1}: {collected} objects collected")
            
            # Check memory after cleanup
            status = self.get_memory_status()
            logger.info(f"   📊 Memory after cleanup: {status.get('memory_mb', 0):.1f}MB")
            
            return status
            
        except Exception as e:
            logger.error(f"Emergency cleanup failed: {e}")
            return {"error": str(e)}
    
    def enable_emergency_mode(self):
        """Enable emergency mode - disable AI models"""
        logger.warning("🚨 ENABLING EMERGENCY MODE - AI MODELS DISABLED")
        
        try:
            # Set environment variables
            os.environ['EMERGENCY_MODE'] = 'true'
            os.environ['DISABLE_AI_MODELS'] = 'true'
            
            # Try to unload models
            try:
                from model_manager import model_manager
                if hasattr(model_manager, 'unload_all_models'):
                    model_manager.unload_all_models()
                    logger.info("   ✅ All AI models unloaded")
            except:
                logger.warning("   ⚠️ Could not unload AI models")
            
            # Emergency cleanup
            self.emergency_cleanup()
            
            logger.warning("🚨 Emergency mode enabled - system running in safe mode")
            
        except Exception as e:
            logger.error(f"Failed to enable emergency mode: {e}")

# Global emergency manager
emergency_manager = EmergencyMemoryManager()

def emergency_memory_check():
    """Quick emergency memory check"""
    status = emergency_manager.get_memory_status()
    
    if status.get("critical"):
        print("🚨 CRITICAL MEMORY USAGE - ENABLING EMERGENCY MODE")
        emergency_manager.enable_emergency_mode()
    elif status.get("emergency"):
        print("⚠️ HIGH MEMORY USAGE - RUNNING EMERGENCY CLEANUP")
        emergency_manager.emergency_cleanup()
    else:
        print(f"✅ Memory status OK: {status.get('memory_mb', 0):.1f}MB")
    
    return status

if __name__ == "__main__":
    emergency_memory_check()
