"""
🚨 Ultra-Aggressive Memory Monitor
================================
Near-zero memory leak target monitoring
"""

import gc
import os
import time
import threading
import logging
import psutil
from typing import List

logger = logging.getLogger(__name__)

class UltraMemoryMonitor:
    """Ultra-aggressive memory monitoring for near-zero leaks"""
    
    def __init__(self):
        self.memory_samples = []
        self.max_samples = 20
        self.check_interval = 15  # Check every 15 seconds
        self.force_cleanup_threshold = 900  # 900MB force cleanup
        self.emergency_threshold = 1200     # 1.2GB emergency mode
        self.running = False
        self.thread = None
        
    def start(self):
        """Start ultra-aggressive monitoring"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.thread.start()
            logger.warning("🚨 Ultra-aggressive memory monitor started")
    
    def stop(self):
        """Stop monitoring"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
    
    def _get_memory_mb(self) -> float:
        """Get current memory usage in MB"""
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except:
            return 0.0
    
    def _force_cleanup(self):
        """Force aggressive cleanup"""
        try:
            # Ultra-aggressive garbage collection
            for _ in range(10):
                gc.collect()
            
            # Clear all possible caches
            import sys
            if hasattr(sys, '_clear_type_cache'):
                sys._clear_type_cache()
            
            # Force torch cleanup if available
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize()
            except:
                pass
            
            logger.warning("🧹 Ultra-aggressive cleanup executed")
            
        except Exception as e:
            logger.error(f"Ultra cleanup failed: {e}")
    
    def _monitor_loop(self):
        """Ultra-aggressive monitoring loop"""
        while self.running:
            try:
                current_memory = self._get_memory_mb()
                self.memory_samples.append(current_memory)
                
                # Keep only recent samples
                if len(self.memory_samples) > self.max_samples:
                    self.memory_samples.pop(0)
                
                # Emergency cleanup trigger
                if current_memory > self.emergency_threshold:
                    logger.error(f"🚨 EMERGENCY: Memory {current_memory:.1f}MB > {self.emergency_threshold}MB")
                    self._force_cleanup()
                    
                    # Enable emergency mode
                    os.environ['EMERGENCY_MODE'] = 'true'
                    os.environ['DISABLE_AI_MODELS'] = 'true'
                
                # Force cleanup trigger
                elif current_memory > self.force_cleanup_threshold:
                    logger.warning(f"🚨 Force cleanup: Memory {current_memory:.1f}MB > {self.force_cleanup_threshold}MB")
                    self._force_cleanup()
                
                # Calculate leak rate
                if len(self.memory_samples) >= 10:
                    time_span = (len(self.memory_samples) - 1) * self.check_interval / 60  # minutes
                    memory_growth = self.memory_samples[-1] - self.memory_samples[0]
                    leak_rate = memory_growth / time_span if time_span > 0 else 0
                    
                    if leak_rate > 1.0:  # > 1 MB/min
                        logger.error(f"🚨 ULTRA LEAK DETECTED: {leak_rate:.2f} MB/min")
                        self._force_cleanup()
                        
                        # If still leaking, enable emergency mode
                        if leak_rate > 3.0:
                            os.environ['EMERGENCY_MODE'] = 'true'
                            logger.error("🚨 Emergency mode activated due to severe leak")
                
                # Periodic cleanup regardless
                if len(self.memory_samples) % 4 == 0:  # Every 4 checks (1 minute)
                    self._force_cleanup()
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Ultra monitor error: {e}")
                time.sleep(5)

# Global ultra monitor
ultra_monitor = UltraMemoryMonitor()

def start_ultra_monitoring():
    """Start ultra-aggressive memory monitoring"""
    ultra_monitor.start()

def stop_ultra_monitoring():
    """Stop ultra monitoring"""
    ultra_monitor.stop()

# Auto-start on import
start_ultra_monitoring()
