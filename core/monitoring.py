"""
📊 MEFAPEX Advanced Monitoring System
===================================
Comprehensive monitoring with metrics collection, alerting,
and performance tracking.
"""

import time
import psutil
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import threading
from contextlib import contextmanager

from core.logging_config import get_structured_logger

logger = get_structured_logger(__name__)

@dataclass
class MetricDataPoint:
    """Single metric data point"""
    timestamp: datetime
    value: float
    labels: Dict[str, str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
            "labels": self.labels or {}
        }

@dataclass
class SystemMetrics:
    """System performance metrics"""
    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    memory_total_gb: float
    disk_percent: float
    disk_used_gb: float
    disk_total_gb: float
    network_io: Dict[str, int]
    active_connections: int
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class ApplicationMetrics:
    """Application-specific metrics"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time_ms: float
    active_users: int
    active_sessions: int
    ai_model_calls: int
    database_queries: int
    cache_hits: int
    cache_misses: int
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class MetricsCollector:
    """
    Advanced metrics collection system
    """
    
    def __init__(self, retention_hours: int = 24):
        self.retention_hours = retention_hours
        self.metrics_storage: Dict[str, deque] = defaultdict(lambda: deque())
        self.counters: Dict[str, int] = defaultdict(int)
        self.gauges: Dict[str, float] = defaultdict(float)
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        self.timers: Dict[str, List[float]] = defaultdict(list)
        
        # Request tracking
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0
        self.response_times = deque(maxlen=1000)
        
        # User tracking
        self.active_users = set()
        self.active_sessions = set()
        
        # Service tracking
        self.ai_model_calls = 0
        self.database_queries = 0
        self.cache_hits = 0
        self.cache_misses = 0
        
        self._lock = threading.Lock()
        self._collection_active = False
        
    def start_collection(self, interval_seconds: int = 30):
        """Start automatic metrics collection"""
        if self._collection_active:
            return
        
        self._collection_active = True
        
        def collect_loop():
            while self._collection_active:
                try:
                    self._collect_system_metrics()
                    self._cleanup_old_metrics()
                except Exception as e:
                    logger.error("Error in metrics collection", error=str(e))
                finally:
                    # Always sleep to prevent busy loop
                    time.sleep(interval_seconds)
        
        thread = threading.Thread(target=collect_loop, daemon=True)
        thread.start()
        logger.info("Metrics collection started", interval=interval_seconds)
    
    def stop_collection(self):
        """Stop metrics collection"""
        self._collection_active = False
        logger.info("Metrics collection stopped")
    
    def increment_counter(self, name: str, value: int = 1, labels: Dict[str, str] = None):
        """Increment a counter metric"""
        with self._lock:
            key = self._get_metric_key(name, labels)
            self.counters[key] += value
            self._store_metric(name, value, labels)
    
    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Set a gauge metric"""
        with self._lock:
            key = self._get_metric_key(name, labels)
            self.gauges[key] = value
            self._store_metric(name, value, labels)
    
    def record_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record a histogram value"""
        with self._lock:
            key = self._get_metric_key(name, labels)
            self.histograms[key].append(value)
            # Keep only last 1000 values
            if len(self.histograms[key]) > 1000:
                self.histograms[key] = self.histograms[key][-1000:]
            self._store_metric(name, value, labels)
    
    @contextmanager
    def timer(self, name: str, labels: Dict[str, str] = None):
        """Context manager for timing operations"""
        start_time = time.time()
        try:
            yield
        finally:
            duration = (time.time() - start_time) * 1000  # Convert to milliseconds
            self.record_histogram(f"{name}_duration_ms", duration, labels)
    
    def track_request(self, method: str, endpoint: str, status_code: int, duration_ms: float):
        """Track HTTP request metrics"""
        with self._lock:
            self.request_count += 1
            if 200 <= status_code < 400:
                self.success_count += 1
            else:
                self.error_count += 1
            
            self.response_times.append(duration_ms)
            
            # Track by endpoint
            labels = {"method": method, "endpoint": endpoint, "status": str(status_code)}
            self.increment_counter("http_requests_total", 1, labels)
            self.record_histogram("http_request_duration_ms", duration_ms, labels)
    
    def track_user_activity(self, user_id: str, session_id: str = None):
        """Track user activity"""
        with self._lock:
            self.active_users.add(user_id)
            if session_id:
                self.active_sessions.add(session_id)
    
    def track_ai_model_call(self, model_name: str, duration_ms: float, success: bool):
        """Track AI model usage"""
        with self._lock:
            self.ai_model_calls += 1
            labels = {"model": model_name, "success": str(success)}
            self.increment_counter("ai_model_calls_total", 1, labels)
            self.record_histogram("ai_model_duration_ms", duration_ms, labels)
    
    def track_database_query(self, operation: str, duration_ms: float, success: bool):
        """Track database queries"""
        with self._lock:
            self.database_queries += 1
            labels = {"operation": operation, "success": str(success)}
            self.increment_counter("database_queries_total", 1, labels)
            self.record_histogram("database_query_duration_ms", duration_ms, labels)
    
    def track_cache_operation(self, operation: str, hit: bool):
        """Track cache operations"""
        with self._lock:
            if hit:
                self.cache_hits += 1
            else:
                self.cache_misses += 1
            
            labels = {"operation": operation, "hit": str(hit)}
            self.increment_counter("cache_operations_total", 1, labels)
    
    def get_system_metrics(self) -> SystemMetrics:
        """Get current system metrics"""
        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Get CPU usage with timeout
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            try:
                network = psutil.net_io_counters()
                network_io = {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv
                }
            except Exception:
                network_io = {"bytes_sent": 0, "bytes_recv": 0}
            
            try:
                active_connections = len(psutil.net_connections())
            except (psutil.AccessDenied, OSError, Exception):
                active_connections = 0
            
            return SystemMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used_gb=round(memory.used / (1024**3), 2),
                memory_total_gb=round(memory.total / (1024**3), 2),
                disk_percent=round((disk.used / disk.total) * 100, 2),
                disk_used_gb=round(disk.used / (1024**3), 2),
                disk_total_gb=round(disk.total / (1024**3), 2),
                network_io=network_io,
                active_connections=active_connections
            )
        except Exception as e:
            logger.warning("Failed to get system metrics", error=str(e))
            # Return safe default values
            return SystemMetrics(
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_used_gb=0.0,
                memory_total_gb=1.0,
                disk_percent=0.0,
                disk_used_gb=0.0,
                disk_total_gb=1.0,
                network_io={"bytes_sent": 0, "bytes_recv": 0},
                active_connections=0
            )
    
    def get_application_metrics(self) -> ApplicationMetrics:
        """Get current application metrics"""
        with self._lock:
            avg_response_time = 0
            if self.response_times:
                avg_response_time = sum(self.response_times) / len(self.response_times)
            
            return ApplicationMetrics(
                total_requests=self.request_count,
                successful_requests=self.success_count,
                failed_requests=self.error_count,
                avg_response_time_ms=round(avg_response_time, 2),
                active_users=len(self.active_users),
                active_sessions=len(self.active_sessions),
                ai_model_calls=self.ai_model_calls,
                database_queries=self.database_queries,
                cache_hits=self.cache_hits,
                cache_misses=self.cache_misses
            )
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary"""
        system_metrics = self.get_system_metrics()
        app_metrics = self.get_application_metrics()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "system": system_metrics.to_dict(),
            "application": app_metrics.to_dict(),
            "health_status": self._calculate_health_status(system_metrics, app_metrics)
        }
    
    def get_prometheus_metrics(self) -> str:
        """Export metrics in Prometheus format"""
        lines = []
        
        # System metrics
        system = self.get_system_metrics()
        lines.append(f'# HELP system_cpu_percent CPU usage percentage')
        lines.append(f'# TYPE system_cpu_percent gauge')
        lines.append(f'system_cpu_percent {system.cpu_percent}')
        
        lines.append(f'# HELP system_memory_percent Memory usage percentage')
        lines.append(f'# TYPE system_memory_percent gauge')
        lines.append(f'system_memory_percent {system.memory_percent}')
        
        # Application metrics
        app = self.get_application_metrics()
        lines.append(f'# HELP http_requests_total Total HTTP requests')
        lines.append(f'# TYPE http_requests_total counter')
        lines.append(f'http_requests_total {app.total_requests}')
        
        lines.append(f'# HELP http_request_duration_ms_avg Average response time')
        lines.append(f'# TYPE http_request_duration_ms_avg gauge')
        lines.append(f'http_request_duration_ms_avg {app.avg_response_time_ms}')
        
        return '\n'.join(lines)
    
    def _collect_system_metrics(self):
        """Collect system metrics automatically"""
        metrics = self.get_system_metrics()
        timestamp = datetime.utcnow()
        
        # Store system metrics
        for key, value in metrics.to_dict().items():
            if isinstance(value, (int, float)):
                self._store_metric(f"system_{key}", value)
    
    def _store_metric(self, name: str, value: float, labels: Dict[str, str] = None):
        """Store metric data point"""
        key = self._get_metric_key(name, labels)
        data_point = MetricDataPoint(
            timestamp=datetime.utcnow(),
            value=value,
            labels=labels
        )
        self.metrics_storage[key].append(data_point)
    
    def _get_metric_key(self, name: str, labels: Dict[str, str] = None) -> str:
        """Generate metric key from name and labels"""
        if labels:
            label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
            return f"{name}{{{label_str}}}"
        return name
    
    def _cleanup_old_metrics(self):
        """Remove old metric data points"""
        cutoff_time = datetime.utcnow() - timedelta(hours=self.retention_hours)
        
        for key, deque_data in self.metrics_storage.items():
            # Remove old data points
            while deque_data and deque_data[0].timestamp < cutoff_time:
                deque_data.popleft()
    
    def _calculate_health_status(self, system: SystemMetrics, app: ApplicationMetrics) -> str:
        """Calculate overall health status"""
        if system.cpu_percent > 90 or system.memory_percent > 90:
            return "critical"
        elif system.cpu_percent > 70 or system.memory_percent > 70:
            return "warning"
        elif app.total_requests > 0 and (app.failed_requests / app.total_requests) > 0.1:
            return "warning"
        else:
            return "healthy"

# Global metrics collector instance
metrics_collector = MetricsCollector()

def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance"""
    return metrics_collector

# Monitoring decorator
def monitor_performance(operation_name: str):
    """Decorator to monitor function performance"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            with metrics_collector.timer(operation_name):
                try:
                    result = await func(*args, **kwargs)
                    metrics_collector.increment_counter(
                        f"{operation_name}_success_total"
                    )
                    return result
                except Exception as e:
                    metrics_collector.increment_counter(
                        f"{operation_name}_error_total",
                        labels={"error_type": type(e).__name__}
                    )
                    raise
        
        def sync_wrapper(*args, **kwargs):
            with metrics_collector.timer(operation_name):
                try:
                    result = func(*args, **kwargs)
                    metrics_collector.increment_counter(
                        f"{operation_name}_success_total"
                    )
                    return result
                except Exception as e:
                    metrics_collector.increment_counter(
                        f"{operation_name}_error_total",
                        labels={"error_type": type(e).__name__}
                    )
                    raise
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator
