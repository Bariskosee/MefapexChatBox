"""
📊 Performance Monitoring Service
Real-time performance tracking, metrics collection, and alerting
"""

import time
import psutil
import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from threading import Thread, Lock
import queue
import json

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetric:
    """Single performance metric"""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags or {}
        }

@dataclass
class SystemMetrics:
    """System resource metrics"""
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_percent: float
    network_sent_mb: float
    network_recv_mb: float
    process_count: int
    load_average: List[float]
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class PerformanceMonitor:
    """Advanced performance monitoring service"""
    
    def __init__(self, collection_interval: int = 10, retention_hours: int = 24):
        self.collection_interval = collection_interval
        self.retention_hours = retention_hours
        
        # Storage
        self._metrics = []
        self._system_metrics = []
        self._custom_metrics = {}
        self._lock = Lock()
        
        # Background collection
        self._running = False
        self._collector_thread = None
        
        # Performance tracking
        self._request_times = queue.Queue(maxsize=10000)
        self._error_counts = {}
        self._endpoint_stats = {}
        
        # Baseline metrics
        self._baseline_cpu = 0
        self._baseline_memory = 0
        self._last_network_stats = None
        
        logger.info(f"📊 PerformanceMonitor initialized (interval={collection_interval}s)")
    
    def start_monitoring(self):
        """Start background metrics collection"""
        if self._running:
            return
        
        self._running = True
        self._collector_thread = Thread(target=self._collect_metrics_loop, daemon=True)
        self._collector_thread.start()
        
        logger.info("🚀 Performance monitoring started")
    
    def stop_monitoring(self):
        """Stop background metrics collection"""
        self._running = False
        if self._collector_thread:
            self._collector_thread.join(timeout=5)
        
        logger.info("🛑 Performance monitoring stopped")
    
    def _collect_metrics_loop(self):
        """Background metrics collection loop"""
        while self._running:
            try:
                self._collect_system_metrics()
                self._cleanup_old_metrics()
                time.sleep(self.collection_interval)
            except Exception as e:
                logger.error(f"Metrics collection error: {e}")
                time.sleep(self.collection_interval)
    
    def _collect_system_metrics(self):
        """Collect system performance metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory metrics
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_mb = memory.used / (1024 * 1024)
            memory_available_mb = memory.available / (1024 * 1024)
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            # Network metrics
            network = psutil.net_io_counters()
            network_sent_mb = network.bytes_sent / (1024 * 1024)
            network_recv_mb = network.bytes_recv / (1024 * 1024)
            
            # Process metrics
            process_count = len(psutil.pids())
            
            # Load average (Unix-like systems)
            try:
                load_average = list(psutil.getloadavg())
            except AttributeError:
                load_average = [0.0, 0.0, 0.0]
            
            # Create metrics object
            metrics = SystemMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_used_mb=memory_used_mb,
                memory_available_mb=memory_available_mb,
                disk_percent=disk_percent,
                network_sent_mb=network_sent_mb,
                network_recv_mb=network_recv_mb,
                process_count=process_count,
                load_average=load_average,
                timestamp=datetime.now()
            )
            
            with self._lock:
                self._system_metrics.append(metrics)
            
        except Exception as e:
            logger.error(f"System metrics collection failed: {e}")
    
    def _cleanup_old_metrics(self):
        """Remove old metrics beyond retention period"""
        cutoff_time = datetime.now() - timedelta(hours=self.retention_hours)
        
        with self._lock:
            # Clean system metrics
            self._system_metrics = [
                m for m in self._system_metrics 
                if m.timestamp > cutoff_time
            ]
            
            # Clean custom metrics
            self._metrics = [
                m for m in self._metrics 
                if m.timestamp > cutoff_time
            ]
    
    def record_metric(self, name: str, value: float, tags: Dict[str, str] = None):
        """Record a custom performance metric"""
        metric = PerformanceMetric(
            name=name,
            value=value,
            timestamp=datetime.now(),
            tags=tags
        )
        
        with self._lock:
            self._metrics.append(metric)
            
            # Also store in custom metrics for quick access
            if name not in self._custom_metrics:
                self._custom_metrics[name] = []
            self._custom_metrics[name].append(value)
            
            # Keep only recent values (last 100)
            if len(self._custom_metrics[name]) > 100:
                self._custom_metrics[name] = self._custom_metrics[name][-100:]
    
    def record_request_time(self, endpoint: str, duration: float, status_code: int = 200):
        """Record API request performance"""
        # Add to request times queue
        try:
            self._request_times.put_nowait({
                'endpoint': endpoint,
                'duration': duration,
                'status_code': status_code,
                'timestamp': datetime.now()
            })
        except queue.Full:
            # Remove oldest item if queue is full
            try:
                self._request_times.get_nowait()
                self._request_times.put_nowait({
                    'endpoint': endpoint,
                    'duration': duration,
                    'status_code': status_code,
                    'timestamp': datetime.now()
                })
            except queue.Empty:
                pass
        
        # Update endpoint statistics
        with self._lock:
            if endpoint not in self._endpoint_stats:
                self._endpoint_stats[endpoint] = {
                    'count': 0,
                    'total_time': 0,
                    'min_time': float('inf'),
                    'max_time': 0,
                    'errors': 0
                }
            
            stats = self._endpoint_stats[endpoint]
            stats['count'] += 1
            stats['total_time'] += duration
            stats['min_time'] = min(stats['min_time'], duration)
            stats['max_time'] = max(stats['max_time'], duration)
            
            if status_code >= 400:
                stats['errors'] += 1
        
        # Record as metric
        self.record_metric(f"request_time.{endpoint}", duration, {
            'endpoint': endpoint,
            'status_code': str(status_code)
        })
    
    def get_current_system_metrics(self) -> Optional[SystemMetrics]:
        """Get most recent system metrics"""
        with self._lock:
            if self._system_metrics:
                return self._system_metrics[-1]
            return None
    
    def get_system_metrics_history(self, hours: int = 1) -> List[SystemMetrics]:
        """Get system metrics history"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            return [
                m for m in self._system_metrics 
                if m.timestamp > cutoff_time
            ]
    
    def get_endpoint_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get endpoint performance statistics"""
        with self._lock:
            stats = {}
            for endpoint, data in self._endpoint_stats.items():
                if data['count'] > 0:
                    stats[endpoint] = {
                        'count': data['count'],
                        'avg_time': round(data['total_time'] / data['count'], 3),
                        'min_time': round(data['min_time'], 3),
                        'max_time': round(data['max_time'], 3),
                        'error_rate': round(data['errors'] / data['count'] * 100, 2),
                        'total_errors': data['errors']
                    }
            
            return stats
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        current_metrics = self.get_current_system_metrics()
        endpoint_stats = self.get_endpoint_stats()
        
        # Recent request times
        recent_requests = []
        try:
            while not self._request_times.empty():
                req = self._request_times.get_nowait()
                # Only keep requests from last hour
                if datetime.now() - req['timestamp'] <= timedelta(hours=1):
                    recent_requests.append(req)
        except queue.Empty:
            pass
        
        # Put back recent requests
        for req in recent_requests:
            try:
                self._request_times.put_nowait(req)
            except queue.Full:
                break
        
        # Calculate averages
        avg_response_time = 0
        total_requests = len(recent_requests)
        error_count = 0
        
        if recent_requests:
            avg_response_time = sum(r['duration'] for r in recent_requests) / len(recent_requests)
            error_count = sum(1 for r in recent_requests if r['status_code'] >= 400)
        
        summary = {
            "timestamp": datetime.now().isoformat(),
            "system": current_metrics.to_dict() if current_metrics else None,
            "requests": {
                "total_count": total_requests,
                "avg_response_time": round(avg_response_time, 3),
                "error_count": error_count,
                "error_rate": round(error_count / total_requests * 100, 2) if total_requests > 0 else 0
            },
            "endpoints": endpoint_stats,
            "custom_metrics": self._get_custom_metrics_summary()
        }
        
        return summary
    
    def _get_custom_metrics_summary(self) -> Dict[str, Dict[str, float]]:
        """Get summary of custom metrics"""
        summary = {}
        
        with self._lock:
            for name, values in self._custom_metrics.items():
                if values:
                    summary[name] = {
                        "count": len(values),
                        "avg": round(sum(values) / len(values), 3),
                        "min": round(min(values), 3),
                        "max": round(max(values), 3),
                        "latest": round(values[-1], 3)
                    }
        
        return summary
    
    def check_performance_alerts(self) -> List[Dict[str, Any]]:
        """Check for performance issues and return alerts"""
        alerts = []
        current_metrics = self.get_current_system_metrics()
        
        if not current_metrics:
            return alerts
        
        # CPU alert
        if current_metrics.cpu_percent > 80:
            alerts.append({
                "type": "HIGH_CPU",
                "severity": "warning" if current_metrics.cpu_percent < 90 else "critical",
                "message": f"High CPU usage: {current_metrics.cpu_percent}%",
                "value": current_metrics.cpu_percent
            })
        
        # Memory alert
        if current_metrics.memory_percent > 85:
            alerts.append({
                "type": "HIGH_MEMORY",
                "severity": "warning" if current_metrics.memory_percent < 95 else "critical",
                "message": f"High memory usage: {current_metrics.memory_percent}%",
                "value": current_metrics.memory_percent
            })
        
        # Disk alert
        if current_metrics.disk_percent > 90:
            alerts.append({
                "type": "HIGH_DISK",
                "severity": "warning" if current_metrics.disk_percent < 95 else "critical",
                "message": f"High disk usage: {current_metrics.disk_percent}%",
                "value": current_metrics.disk_percent
            })
        
        # Response time alerts
        endpoint_stats = self.get_endpoint_stats()
        for endpoint, stats in endpoint_stats.items():
            if stats['avg_time'] > 5.0:  # 5 seconds
                alerts.append({
                    "type": "SLOW_ENDPOINT",
                    "severity": "warning",
                    "message": f"Slow endpoint {endpoint}: {stats['avg_time']}s average",
                    "value": stats['avg_time'],
                    "endpoint": endpoint
                })
            
            if stats['error_rate'] > 10:  # 10% error rate
                alerts.append({
                    "type": "HIGH_ERROR_RATE",
                    "severity": "critical" if stats['error_rate'] > 25 else "warning",
                    "message": f"High error rate for {endpoint}: {stats['error_rate']}%",
                    "value": stats['error_rate'],
                    "endpoint": endpoint
                })
        
        return alerts
    
    def export_metrics(self, format: str = "json") -> str:
        """Export metrics in specified format"""
        if format.lower() == "json":
            return json.dumps(self.get_performance_summary(), indent=2, default=str)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def reset_stats(self):
        """Reset all statistics"""
        with self._lock:
            self._metrics.clear()
            self._system_metrics.clear()
            self._custom_metrics.clear()
            self._endpoint_stats.clear()
            
            # Clear request times queue
            while not self._request_times.empty():
                try:
                    self._request_times.get_nowait()
                except queue.Empty:
                    break
        
        logger.info("📊 Performance statistics reset")

# Global performance monitor instance
performance_monitor = None

def init_performance_monitor(collection_interval: int = 10, retention_hours: int = 24):
    """Initialize global performance monitor"""
    global performance_monitor
    performance_monitor = PerformanceMonitor(collection_interval, retention_hours)
    return performance_monitor

def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance"""
    global performance_monitor
    if performance_monitor is None:
        performance_monitor = PerformanceMonitor()
    return performance_monitor
