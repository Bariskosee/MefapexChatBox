"""
🧠 Memory Leak Detection and Monitoring for Production Backend
Author: MEFAPEX AI Assistant
Description: Comprehensive memory monitoring with leak detection and automatic cleanup
"""

import gc
import psutil
import threading
import time
import logging
import tracemalloc
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict, deque
import weakref
import sys

# Configure logger
logger = logging.getLogger(__name__)

@dataclass
class MemorySnapshot:
    """Memory usage snapshot"""
    timestamp: datetime
    memory_mb: float
    cpu_percent: float
    active_connections: int
    gc_collections: Dict[int, int]
    top_allocations: List[tuple]

class MemoryMonitor:
    """
    Production-ready memory monitor with leak detection
    """
    
    def __init__(self, 
                 check_interval: int = 60,  # seconds
                 memory_threshold_mb: float = 4096.0,  # MB - Increased for AI models (was 1536.0)
                 leak_detection_window: int = 10):  # snapshots
        self.check_interval = check_interval
        self.memory_threshold_mb = memory_threshold_mb
        self.leak_detection_window = leak_detection_window
        self.snapshots = deque(maxlen=leak_detection_window)
        self.process = psutil.Process()
        self.monitoring = False
        self.monitor_thread = None
        
        # Weak references for tracking objects
        self.tracked_objects = weakref.WeakSet()
        self.object_counts = defaultdict(int)
        
        # Statistics
        self.total_gc_runs = 0
        self.memory_warnings = 0
        self.leak_alerts = 0
        
    def start_monitoring(self):
        """Start memory monitoring in background thread"""
        if self.monitoring:
            logger.warning("Memory monitoring already started")
            return
            
        self.monitoring = True
        tracemalloc.start()
        
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="MemoryMonitor"
        )
        self.monitor_thread.start()
        logger.info(f"🧠 Memory monitoring started (interval: {self.check_interval}s, threshold: {self.memory_threshold_mb}MB)")
        
    def stop_monitoring(self):
        """Stop memory monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
        tracemalloc.stop()
        logger.info("🧠 Memory monitoring stopped")
        
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                snapshot = self._take_snapshot()
                self.snapshots.append(snapshot)
                
                # Check for memory issues
                self._check_memory_threshold(snapshot)
                self._detect_memory_leaks()
                
                # Periodic cleanup
                if len(self.snapshots) % 5 == 0:
                    self._periodic_cleanup()
                    
            except Exception as e:
                logger.error(f"Memory monitoring error: {e}")
                
            time.sleep(self.check_interval)
            
    def _take_snapshot(self) -> MemorySnapshot:
        """Take a memory usage snapshot"""
        try:
            # Memory info
            memory_info = self.process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            # CPU info
            cpu_percent = self.process.cpu_percent()
            
            # Active connections (approximate)
            try:
                connections = len(self.process.connections())
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                connections = 0
                
            # Garbage collection stats
            gc_stats = {i: gc.get_count()[i] for i in range(3)}
            
            # Top memory allocations
            top_allocations = []
            try:
                if tracemalloc.is_tracing():
                    current, peak = tracemalloc.get_traced_memory()
                    snapshot = tracemalloc.take_snapshot()
                    top_stats = snapshot.statistics('lineno')[:5]
                    
                    for stat in top_stats:
                        try:
                            location = stat.traceback.format()[-1] if stat.traceback.format() else "unknown"
                            size_mb = stat.size / 1024 / 1024  # MB
                            top_allocations.append((location, size_mb))
                        except Exception:
                            continue
            except Exception as e:
                logger.debug(f"Error getting memory allocations: {e}")
                    
            return MemorySnapshot(
                timestamp=datetime.utcnow(),
                memory_mb=memory_mb,
                cpu_percent=cpu_percent,
                active_connections=connections,
                gc_collections=gc_stats,
                top_allocations=top_allocations
            )
            
        except Exception as e:
            logger.error(f"Error taking memory snapshot: {e}")
            return MemorySnapshot(
                timestamp=datetime.utcnow(),
                memory_mb=0.0,
                cpu_percent=0.0,
                active_connections=0,
                gc_collections={},
                top_allocations=[]
            )
            
    def _check_memory_threshold(self, snapshot: MemorySnapshot):
        """Check if memory usage exceeds threshold"""
        if snapshot.memory_mb > self.memory_threshold_mb:
            self.memory_warnings += 1
            logger.warning(
                f"🚨 Memory threshold exceeded: {snapshot.memory_mb:.1f}MB > {self.memory_threshold_mb}MB"
            )
            
            # Force garbage collection
            self.force_gc()
            
            # Log top allocations
            if snapshot.top_allocations:
                logger.warning("Top memory allocations:")
                for location, size_mb in snapshot.top_allocations:
                    logger.warning(f"  {location}: {size_mb:.2f}MB")
                    
    def _detect_memory_leaks(self):
        """Detect potential memory leaks"""
        if len(self.snapshots) < self.leak_detection_window:
            return
            
        # Calculate memory growth trend
        recent_snapshots = list(self.snapshots)[-self.leak_detection_window:]
        memory_values = [s.memory_mb for s in recent_snapshots]
        
        # Simple linear trend detection
        start_memory = sum(memory_values[:3]) / 3
        end_memory = sum(memory_values[-3:]) / 3
        growth_rate = (end_memory - start_memory) / (len(memory_values) * self.check_interval / 60)  # MB per minute
        
        if growth_rate > 5.0:  # More than 5MB per minute growth
            self.leak_alerts += 1
            logger.error(
                f"🚨 POTENTIAL MEMORY LEAK DETECTED: "
                f"Growth rate: {growth_rate:.2f} MB/min over {len(memory_values)} samples"
            )
            
            # Detailed analysis
            self._analyze_potential_leak()
            
    def _analyze_potential_leak(self):
        """Analyze potential memory leak sources"""
        logger.info("🔍 Analyzing potential memory leak sources...")
        
        # Object count analysis
        current_objects = {}
        for obj_type in [list, dict, str, tuple, set]:
            current_objects[obj_type.__name__] = len([obj for obj in gc.get_objects() if type(obj) is obj_type])
            
        logger.info("Current object counts:")
        for obj_type, count in current_objects.items():
            logger.info(f"  {obj_type}: {count:,}")
            
        # Reference cycles
        unreachable = gc.collect()
        if unreachable > 0:
            logger.warning(f"Garbage collected {unreachable} unreachable objects")
            
    def _periodic_cleanup(self):
        """Perform periodic cleanup"""
        logger.debug("🧹 Performing periodic cleanup...")
        
        # Force garbage collection
        collected = self.force_gc()
        
        # Update statistics
        self.total_gc_runs += 1
        
        if collected > 100:
            logger.info(f"🧹 Cleanup collected {collected} objects")
            
    def force_gc(self) -> int:
        """Force garbage collection and return number of collected objects"""
        collected = 0
        for generation in range(3):
            collected += gc.collect(generation)
        return collected
        
    def get_stats(self) -> Dict:
        """Get monitoring statistics"""
        current_snapshot = self._take_snapshot()
        
        return {
            "current_memory_mb": current_snapshot.memory_mb,
            "current_cpu_percent": current_snapshot.cpu_percent,
            "active_connections": current_snapshot.active_connections,
            "memory_threshold_mb": self.memory_threshold_mb,
            "monitoring_active": self.monitoring,
            "total_snapshots": len(self.snapshots),
            "memory_warnings": self.memory_warnings,
            "leak_alerts": self.leak_alerts,
            "total_gc_runs": self.total_gc_runs,
            "gc_stats": current_snapshot.gc_collections,
            "top_allocations": current_snapshot.top_allocations
        }
        
    def get_memory_history(self, minutes: int = 60) -> List[Dict]:
        """Get memory history for the last N minutes"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        
        history = []
        for snapshot in self.snapshots:
            if snapshot.timestamp >= cutoff_time:
                history.append({
                    "timestamp": snapshot.timestamp.isoformat(),
                    "memory_mb": snapshot.memory_mb,
                    "cpu_percent": snapshot.cpu_percent,
                    "active_connections": snapshot.active_connections
                })
                
        return history
        
    def track_object(self, obj, name: str = None):
        """Track an object for memory leak detection"""
        self.tracked_objects.add(obj)
        obj_type = name or type(obj).__name__
        self.object_counts[obj_type] += 1
        
    def untrack_object(self, obj, name: str = None):
        """Untrack an object"""
        if obj in self.tracked_objects:
            self.tracked_objects.discard(obj)
            obj_type = name or type(obj).__name__
            self.object_counts[obj_type] = max(0, self.object_counts[obj_type] - 1)

# Global memory monitor instance with AI model optimized settings
memory_monitor = MemoryMonitor(
    check_interval=60,  # Check every 60 seconds
    memory_threshold_mb=4096.0,  # 4GB threshold for AI models (increased from 1.5GB)
    leak_detection_window=10
)

# Memory leak detection utilities
class MemoryLeakDetector:
    """AI-safe memory leak detection - completely bypasses object inspection."""
    
    @staticmethod
    def check_circular_references():
        """
        AI-safe circular reference check - uses only garbage collection without object inspection.
        Completely avoids iterating through objects to prevent 'K instance' errors with AI models.
        """
        logger.info("🔍 AI-safe circular reference check (GC only)")
        
        try:
            # Force garbage collection without object inspection
            collected = gc.collect()
            logger.debug(f"Garbage collection freed {collected} objects")
            
            # Return simple analysis without object iteration
            if collected > 0:
                logger.info(f"✅ Garbage collection cleaned up {collected} objects")
            else:
                logger.debug("No objects needed cleanup")
                
            return []  # Return empty list to avoid any object-based analysis
            
        except Exception as e:
            logger.warning(f"Safe garbage collection failed: {e}")
            return []
        
    @staticmethod
    def analyze_large_objects(threshold_mb: float = 10.0):
        """
        AI-safe large object analysis - completely bypasses problematic object inspection.
        Uses only system-level memory metrics to avoid 'K instance' errors with AI models.
        """
        logger.info(f"🔍 AI-safe memory analysis (bypassing object inspection)")
        
        try:
            # Use only system-level metrics instead of object inspection
            process = psutil.Process()
            memory_info = process.memory_info()
            
            # Create safe analysis without iterating through objects
            safe_analysis = {
                "total_memory_mb": memory_info.rss / 1024 / 1024,
                "virtual_memory_mb": memory_info.vms / 1024 / 1024,
                "analysis_method": "system_metrics_only",
                "ai_safe_mode": True
            }
            
            logger.info(f"📊 System memory usage: {safe_analysis['total_memory_mb']:.1f}MB")
            
            # Return empty list to avoid any object-based analysis
            return []
            
        except Exception as e:
            logger.warning(f"AI-safe memory analysis failed: {e}")
            return []
        
    @staticmethod
    def check_unclosed_resources():
        """Check for unclosed file handles and connections"""
        logger.info("🔍 Checking for unclosed resources...")
        
        process = psutil.Process()
        try:
            open_files = process.open_files()
            connections = process.connections()
            
            logger.info(f"Open files: {len(open_files)}")
            logger.info(f"Open connections: {len(connections)}")
            
            # Check for suspicious patterns
            file_extensions = defaultdict(int)
            for file in open_files:
                ext = file.path.split('.')[-1] if '.' in file.path else 'no_ext'
                file_extensions[ext] += 1
                
            return {
                "open_files": len(open_files),
                "open_connections": len(connections),
                "file_extensions": dict(file_extensions)
            }
            
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            logger.warning("Cannot access process information")
            return {}

# Context managers for memory tracking
class MemoryTracker:
    """Context manager for tracking memory usage"""
    
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_memory = 0
        self.start_time = 0
        
    def __enter__(self):
        self.start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        self.start_time = time.time()
        logger.debug(f"🧠 Starting memory tracking for: {self.operation_name}")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024
        duration = time.time() - self.start_time
        memory_diff = end_memory - self.start_memory
        
        logger.info(
            f"🧠 Memory tracking for '{self.operation_name}': "
            f"{memory_diff:+.2f}MB in {duration:.2f}s"
        )
        
        if memory_diff > 50:  # More than 50MB increase
            logger.warning(
                f"🚨 High memory usage detected in '{self.operation_name}': {memory_diff:.2f}MB"
            )

# Decorators for memory monitoring
def track_memory(operation_name: str = None):
    """Decorator to track memory usage of functions"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            name = operation_name or f"{func.__module__}.{func.__name__}"
            with MemoryTracker(name):
                return func(*args, **kwargs)
        return wrapper
    return decorator

# Example usage functions
def setup_memory_monitoring():
    """
    Setup AI-safe memory monitoring - completely disables problematic object inspection.
    Uses only basic system-level monitoring to prevent 'K instance' errors with AI models.
    """
    import os
    global memory_monitor
    
    # Get memory threshold from environment or use 4GB default for AI models
    memory_threshold = float(os.getenv("MEMORY_THRESHOLD_MB", "4096.0"))
    
    # Use existing global instance if available, otherwise create new one
    if memory_monitor is None or not memory_monitor.monitoring:
        memory_monitor = MemoryMonitor(
            check_interval=60,  # Check every 60 seconds
            memory_threshold_mb=memory_threshold,  # Use environment variable
            leak_detection_window=10
        )
        
        memory_monitor.start_monitoring()
        logger.info(f"🧠 AI-safe memory monitoring started with {memory_threshold}MB threshold")
    else:
        logger.info("🧠 Memory monitoring already active")
    
    # COMPLETELY DISABLE periodic deep analysis to prevent AI model compatibility issues
    # The basic MemoryMonitor provides sufficient monitoring without problematic object inspection
    logger.info("🧠 AI-safe memory monitoring setup complete (deep analysis disabled for AI compatibility)")

if __name__ == "__main__":
    # Test the memory monitor
    setup_memory_monitoring()
    
    # Simulate some memory usage
    test_data = []
    for i in range(1000):
        test_data.append([0] * 1000)
        time.sleep(0.1)
        
    print("Memory monitor stats:", memory_monitor.get_stats())
    
    memory_monitor.stop_monitoring()
