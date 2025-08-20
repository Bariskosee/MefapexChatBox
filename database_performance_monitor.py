"""
📊 MEFAPEX Database Performance Monitor
=====================================
Real-time database performance monitoring integrated with memory monitoring
"""

import os
import logging
import asyncio
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import json
import time
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from collections import deque
import weakref

# Import memory monitor
from memory_monitor import memory_monitor, MemoryTracker, track_memory

# Configure logger
logger = logging.getLogger(__name__)

@dataclass
class DatabaseMetrics:
    """Database performance metrics snapshot"""
    timestamp: datetime
    connection_count: int
    active_queries: int
    database_size_mb: float
    cache_hit_ratio: float
    table_stats: Dict[str, Any]
    index_stats: Dict[str, Any]
    slow_queries: List[Dict[str, Any]]
    memory_usage_mb: float
    cpu_usage_percent: float

class DatabasePerformanceMonitor:
    """
    Comprehensive database performance monitoring for MEFAPEX
    """
    
    def __init__(self, check_interval: int = 30):
        # Database configuration from environment
        self.host = os.getenv("POSTGRES_HOST", "localhost")
        self.port = int(os.getenv("POSTGRES_PORT", "5432"))
        self.database = os.getenv("POSTGRES_DB", "mefapex_chatbot")
        self.user = os.getenv("POSTGRES_USER", "mefapex")
        self.password = os.getenv("POSTGRES_PASSWORD", "mefapex")
        
        self.check_interval = check_interval
        self.connection = None
        self.monitoring = False
        self.monitor_thread = None
        
        # Metrics storage
        self.metrics_history = deque(maxlen=100)  # Keep last 100 snapshots
        self.alerts = []
        
        # Performance thresholds
        self.connection_threshold = 150
        self.cache_hit_threshold = 95.0
        self.slow_query_threshold = 1000  # ms
        
        logger.info(f"📊 Database Performance Monitor initialized for {self.host}:{self.port}/{self.database}")

    def connect(self):
        """Establish database connection"""
        try:
            self.connection = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                cursor_factory=RealDictCursor
            )
            self.connection.autocommit = True
            logger.info("✅ Database performance monitor connected")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to database for monitoring: {e}")
            raise

    def disconnect(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("📊 Database performance monitor disconnected")

    @track_memory("database_metrics_collection")
    def collect_metrics(self) -> DatabaseMetrics:
        """Collect comprehensive database metrics"""
        try:
            cursor = self.connection.cursor()
            
            # 1. Connection metrics
            cursor.execute("SELECT count(*) FROM pg_stat_activity")
            connection_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE state = 'active'")
            active_queries = cursor.fetchone()[0]
            
            # 2. Database size
            cursor.execute("SELECT pg_database_size(current_database()) / 1024 / 1024 as size_mb")
            database_size_mb = float(cursor.fetchone()['size_mb'])
            
            # 3. Cache hit ratio
            cursor.execute("""
                SELECT 
                    round(
                        100.0 * sum(blks_hit) / (sum(blks_hit) + sum(blks_read)), 2
                    ) as cache_hit_ratio
                FROM pg_stat_database 
                WHERE datname = current_database()
            """)
            cache_result = cursor.fetchone()
            cache_hit_ratio = float(cache_result['cache_hit_ratio']) if cache_result['cache_hit_ratio'] else 0.0
            
            # 4. Table statistics
            table_stats = self._get_table_stats(cursor)
            
            # 5. Index statistics  
            index_stats = self._get_index_stats(cursor)
            
            # 6. Slow queries (if pg_stat_statements is available)
            slow_queries = self._get_slow_queries(cursor)
            
            # 7. Memory usage from memory monitor
            memory_stats = memory_monitor.get_stats() if memory_monitor.monitoring else {}
            memory_usage_mb = memory_stats.get('current_memory_mb', 0.0)
            cpu_usage_percent = memory_stats.get('current_cpu_percent', 0.0)
            
            metrics = DatabaseMetrics(
                timestamp=datetime.now(),
                connection_count=connection_count,
                active_queries=active_queries,
                database_size_mb=database_size_mb,
                cache_hit_ratio=cache_hit_ratio,
                table_stats=table_stats,
                index_stats=index_stats,
                slow_queries=slow_queries,
                memory_usage_mb=memory_usage_mb,
                cpu_usage_percent=cpu_usage_percent
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"❌ Failed to collect database metrics: {e}")
            # Return empty metrics on error
            return DatabaseMetrics(
                timestamp=datetime.now(),
                connection_count=0,
                active_queries=0,
                database_size_mb=0.0,
                cache_hit_ratio=0.0,
                table_stats={},
                index_stats={},
                slow_queries=[],
                memory_usage_mb=0.0,
                cpu_usage_percent=0.0
            )

    def _get_table_stats(self, cursor) -> Dict[str, Any]:
        """Get table-level statistics"""
        try:
            cursor.execute("""
                SELECT 
                    tablename,
                    n_live_tup as live_tuples,
                    n_dead_tup as dead_tuples,
                    n_tup_ins as inserts,
                    n_tup_upd as updates,
                    n_tup_del as deletes,
                    last_vacuum,
                    last_autovacuum,
                    last_analyze,
                    vacuum_count,
                    autovacuum_count
                FROM pg_stat_user_tables
                WHERE schemaname = 'public'
                ORDER BY n_live_tup DESC
            """)
            
            results = cursor.fetchall()
            return {
                row['tablename']: {
                    'live_tuples': row['live_tuples'],
                    'dead_tuples': row['dead_tuples'],
                    'inserts': row['inserts'],
                    'updates': row['updates'],
                    'deletes': row['deletes'],
                    'last_vacuum': row['last_vacuum'],
                    'last_autovacuum': row['last_autovacuum'],
                    'last_analyze': row['last_analyze'],
                    'vacuum_count': row['vacuum_count'],
                    'autovacuum_count': row['autovacuum_count']
                }
                for row in results
            }
            
        except Exception as e:
            logger.warning(f"Failed to get table stats: {e}")
            return {}

    def _get_index_stats(self, cursor) -> Dict[str, Any]:
        """Get index usage statistics"""
        try:
            cursor.execute("""
                SELECT 
                    indexname,
                    tablename,
                    idx_scan as scans,
                    idx_tup_read as tuples_read,
                    idx_tup_fetch as tuples_fetched,
                    CASE 
                        WHEN idx_scan = 0 THEN 'UNUSED'
                        WHEN idx_scan < 100 THEN 'LOW'
                        WHEN idx_scan < 1000 THEN 'MEDIUM'
                        ELSE 'HIGH'
                    END as usage_level
                FROM pg_stat_user_indexes
                WHERE schemaname = 'public'
                ORDER BY idx_scan DESC
            """)
            
            results = cursor.fetchall()
            return {
                row['indexname']: {
                    'table': row['tablename'],
                    'scans': row['scans'],
                    'tuples_read': row['tuples_read'],
                    'tuples_fetched': row['tuples_fetched'],
                    'usage_level': row['usage_level']
                }
                for row in results
            }
            
        except Exception as e:
            logger.warning(f"Failed to get index stats: {e}")
            return {}

    def _get_slow_queries(self, cursor) -> List[Dict[str, Any]]:
        """Get slow query statistics"""
        try:
            # Check if pg_stat_statements extension is available
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'
                )
            """)
            
            has_pg_stat_statements = cursor.fetchone()[0]
            
            if not has_pg_stat_statements:
                return []
            
            cursor.execute("""
                SELECT 
                    query,
                    calls,
                    total_time,
                    mean_time,
                    max_time,
                    rows
                FROM pg_stat_statements
                WHERE mean_time > %s
                ORDER BY mean_time DESC
                LIMIT 10
            """, (self.slow_query_threshold,))
            
            results = cursor.fetchall()
            return [
                {
                    'query': row['query'][:100] + '...' if len(row['query']) > 100 else row['query'],
                    'calls': row['calls'],
                    'total_time': row['total_time'],
                    'mean_time': row['mean_time'],
                    'max_time': row['max_time'],
                    'rows': row['rows']
                }
                for row in results
            ]
            
        except Exception as e:
            logger.warning(f"Failed to get slow queries: {e}")
            return []

    def check_alerts(self, metrics: DatabaseMetrics):
        """Check for performance alerts"""
        alerts = []
        
        # Connection count alert
        if metrics.connection_count > self.connection_threshold:
            alerts.append({
                'type': 'HIGH_CONNECTIONS',
                'severity': 'WARNING',
                'message': f"High connection count: {metrics.connection_count} > {self.connection_threshold}",
                'timestamp': metrics.timestamp,
                'value': metrics.connection_count
            })
        
        # Cache hit ratio alert
        if metrics.cache_hit_ratio < self.cache_hit_threshold:
            alerts.append({
                'type': 'LOW_CACHE_HIT_RATIO',
                'severity': 'WARNING',
                'message': f"Low cache hit ratio: {metrics.cache_hit_ratio}% < {self.cache_hit_threshold}%",
                'timestamp': metrics.timestamp,
                'value': metrics.cache_hit_ratio
            })
        
        # Memory usage alert (integrate with memory monitor)
        if metrics.memory_usage_mb > 3072:  # 3GB threshold
            alerts.append({
                'type': 'HIGH_MEMORY_USAGE',
                'severity': 'WARNING',
                'message': f"High memory usage: {metrics.memory_usage_mb:.1f}MB",
                'timestamp': metrics.timestamp,
                'value': metrics.memory_usage_mb
            })
        
        # Dead tuple alert
        for table_name, stats in metrics.table_stats.items():
            dead_tuples = stats.get('dead_tuples', 0)
            live_tuples = stats.get('live_tuples', 1)
            dead_ratio = (dead_tuples / live_tuples) * 100 if live_tuples > 0 else 0
            
            if dead_ratio > 20:  # More than 20% dead tuples
                alerts.append({
                    'type': 'HIGH_DEAD_TUPLES',
                    'severity': 'WARNING',
                    'message': f"High dead tuple ratio in {table_name}: {dead_ratio:.1f}%",
                    'timestamp': metrics.timestamp,
                    'table': table_name,
                    'value': dead_ratio
                })
        
        # Add new alerts to history
        self.alerts.extend(alerts)
        
        # Keep only recent alerts (last 24 hours)
        cutoff_time = datetime.now() - timedelta(hours=24)
        self.alerts = [alert for alert in self.alerts if alert['timestamp'] > cutoff_time]
        
        # Log alerts
        for alert in alerts:
            if alert['severity'] == 'WARNING':
                logger.warning(f"🚨 {alert['message']}")
            else:
                logger.error(f"🚨 {alert['message']}")

    def start_monitoring(self):
        """Start database performance monitoring"""
        if self.monitoring:
            logger.warning("Database performance monitoring already started")
            return
        
        self.monitoring = True
        self.connect()
        
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="DatabasePerformanceMonitor"
        )
        self.monitor_thread.start()
        logger.info(f"📊 Database performance monitoring started (interval: {self.check_interval}s)")

    def stop_monitoring(self):
        """Stop database performance monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
        self.disconnect()
        logger.info("📊 Database performance monitoring stopped")

    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                # Collect metrics
                metrics = self.collect_metrics()
                self.metrics_history.append(metrics)
                
                # Check for alerts
                self.check_alerts(metrics)
                
                # Log key metrics periodically
                if len(self.metrics_history) % 10 == 0:  # Every 10 cycles
                    logger.info(
                        f"📊 DB Stats: {metrics.connection_count} conns, "
                        f"{metrics.cache_hit_ratio:.1f}% cache hit, "
                        f"{metrics.database_size_mb:.1f}MB size, "
                        f"{metrics.memory_usage_mb:.1f}MB memory"
                    )
                
            except Exception as e:
                logger.error(f"Database monitoring error: {e}")
                # Try to reconnect
                try:
                    self.disconnect()
                    time.sleep(5)
                    self.connect()
                except Exception as reconnect_error:
                    logger.error(f"Failed to reconnect: {reconnect_error}")
            
            time.sleep(self.check_interval)

    def get_current_stats(self) -> Dict[str, Any]:
        """Get current database statistics"""
        if not self.metrics_history:
            return {"error": "No metrics available"}
        
        latest_metrics = self.metrics_history[-1]
        
        return {
            "timestamp": latest_metrics.timestamp.isoformat(),
            "connection_count": latest_metrics.connection_count,
            "active_queries": latest_metrics.active_queries,
            "database_size_mb": latest_metrics.database_size_mb,
            "cache_hit_ratio": latest_metrics.cache_hit_ratio,
            "memory_usage_mb": latest_metrics.memory_usage_mb,
            "cpu_usage_percent": latest_metrics.cpu_usage_percent,
            "table_count": len(latest_metrics.table_stats),
            "index_count": len(latest_metrics.index_stats),
            "slow_query_count": len(latest_metrics.slow_queries),
            "alert_count": len([a for a in self.alerts if a['timestamp'] > datetime.now() - timedelta(hours=1)])
        }

    def get_performance_history(self, hours: int = 1) -> List[Dict[str, Any]]:
        """Get performance history for the last N hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        history = []
        for metrics in self.metrics_history:
            if metrics.timestamp >= cutoff_time:
                history.append({
                    "timestamp": metrics.timestamp.isoformat(),
                    "connection_count": metrics.connection_count,
                    "active_queries": metrics.active_queries,
                    "database_size_mb": metrics.database_size_mb,
                    "cache_hit_ratio": metrics.cache_hit_ratio,
                    "memory_usage_mb": metrics.memory_usage_mb,
                    "cpu_usage_percent": metrics.cpu_usage_percent
                })
        
        return history

    def get_table_health(self) -> Dict[str, Any]:
        """Get table health summary"""
        if not self.metrics_history:
            return {"error": "No metrics available"}
        
        latest_metrics = self.metrics_history[-1]
        table_health = {}
        
        for table_name, stats in latest_metrics.table_stats.items():
            dead_tuples = stats.get('dead_tuples', 0)
            live_tuples = stats.get('live_tuples', 1)
            dead_ratio = (dead_tuples / live_tuples) * 100 if live_tuples > 0 else 0
            
            # Determine health status
            if dead_ratio > 20:
                health_status = "POOR"
            elif dead_ratio > 10:
                health_status = "FAIR"
            else:
                health_status = "GOOD"
            
            table_health[table_name] = {
                "health_status": health_status,
                "live_tuples": live_tuples,
                "dead_tuples": dead_tuples,
                "dead_ratio_percent": round(dead_ratio, 2),
                "last_vacuum": stats.get('last_vacuum'),
                "last_analyze": stats.get('last_analyze')
            }
        
        return table_health

    def get_alerts(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent alerts"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_alerts = [
            {
                **alert,
                'timestamp': alert['timestamp'].isoformat()
            }
            for alert in self.alerts
            if alert['timestamp'] >= cutoff_time
        ]
        return recent_alerts

    def get_comprehensive_report(self) -> Dict[str, Any]:
        """Generate comprehensive database performance report"""
        current_stats = self.get_current_stats()
        table_health = self.get_table_health()
        recent_alerts = self.get_alerts(hours=1)
        performance_history = self.get_performance_history(hours=1)
        
        # Calculate performance trends
        if len(self.metrics_history) >= 2:
            recent_metrics = list(self.metrics_history)[-10:]  # Last 10 snapshots
            avg_connections = sum(m.connection_count for m in recent_metrics) / len(recent_metrics)
            avg_cache_hit = sum(m.cache_hit_ratio for m in recent_metrics) / len(recent_metrics)
            avg_memory = sum(m.memory_usage_mb for m in recent_metrics) / len(recent_metrics)
        else:
            avg_connections = avg_cache_hit = avg_memory = 0
        
        return {
            "generated_at": datetime.now().isoformat(),
            "database_info": {
                "host": self.host,
                "port": self.port,
                "database": self.database
            },
            "current_stats": current_stats,
            "performance_trends": {
                "avg_connections_10min": round(avg_connections, 1),
                "avg_cache_hit_ratio_10min": round(avg_cache_hit, 2),
                "avg_memory_usage_10min": round(avg_memory, 1)
            },
            "table_health": table_health,
            "recent_alerts": recent_alerts,
            "performance_history": performance_history[-20:],  # Last 20 snapshots
            "recommendations": self._generate_recommendations()
        }

    def _generate_recommendations(self) -> List[str]:
        """Generate performance recommendations based on current metrics"""
        recommendations = []
        
        if not self.metrics_history:
            return ["No data available for recommendations"]
        
        latest_metrics = self.metrics_history[-1]
        
        # Connection recommendations
        if latest_metrics.connection_count > 100:
            recommendations.append("Consider implementing connection pooling (PgBouncer)")
        
        # Cache hit ratio recommendations
        if latest_metrics.cache_hit_ratio < 95:
            recommendations.append("Increase shared_buffers or add more RAM for better cache performance")
        
        # Memory recommendations
        if latest_metrics.memory_usage_mb > 2048:
            recommendations.append("Monitor memory usage - consider increasing system RAM")
        
        # Table maintenance recommendations
        for table_name, stats in latest_metrics.table_stats.items():
            dead_tuples = stats.get('dead_tuples', 0)
            live_tuples = stats.get('live_tuples', 1)
            dead_ratio = (dead_tuples / live_tuples) * 100 if live_tuples > 0 else 0
            
            if dead_ratio > 15:
                recommendations.append(f"Run VACUUM on table '{table_name}' - {dead_ratio:.1f}% dead tuples")
        
        # Index recommendations
        unused_indexes = [
            name for name, stats in latest_metrics.index_stats.items()
            if stats.get('usage_level') == 'UNUSED'
        ]
        if unused_indexes:
            recommendations.append(f"Consider dropping unused indexes: {', '.join(unused_indexes[:3])}")
        
        # Slow query recommendations
        if len(latest_metrics.slow_queries) > 5:
            recommendations.append("Review and optimize slow queries - consider adding indexes")
        
        if not recommendations:
            recommendations.append("Database performance looks good! Continue monitoring.")
        
        return recommendations

# Global database monitor instance
db_performance_monitor = DatabasePerformanceMonitor(check_interval=30)

def setup_database_monitoring():
    """Setup integrated database and memory monitoring"""
    global db_performance_monitor
    
    # Start memory monitoring if not already started
    if not memory_monitor.monitoring:
        memory_monitor.start_monitoring()
        logger.info("🧠 Memory monitoring started for database integration")
    
    # Start database monitoring
    if not db_performance_monitor.monitoring:
        db_performance_monitor.start_monitoring()
        logger.info("📊 Database performance monitoring started")
    else:
        logger.info("📊 Database performance monitoring already active")

def get_integrated_health_report() -> Dict[str, Any]:
    """Get integrated health report combining database and memory metrics"""
    
    # Get database performance report
    db_report = db_performance_monitor.get_comprehensive_report()
    
    # Get memory monitoring stats
    memory_stats = memory_monitor.get_stats() if memory_monitor.monitoring else {}
    memory_history = memory_monitor.get_memory_history(minutes=30) if memory_monitor.monitoring else []
    
    # Combine reports
    integrated_report = {
        "timestamp": datetime.now().isoformat(),
        "system_health": {
            "database": db_report,
            "memory": {
                "current_stats": memory_stats,
                "memory_history": memory_history[-10:]  # Last 10 snapshots
            }
        },
        "overall_status": "HEALTHY",  # Will be determined by analysis
        "critical_alerts": [],
        "recommendations": []
    }
    
    # Analyze overall health
    critical_alerts = []
    recommendations = []
    
    # Check database health
    if db_report.get("current_stats", {}).get("connection_count", 0) > 150:
        critical_alerts.append("High database connection count")
        integrated_report["overall_status"] = "WARNING"
    
    if db_report.get("current_stats", {}).get("cache_hit_ratio", 100) < 90:
        critical_alerts.append("Low database cache hit ratio")
        integrated_report["overall_status"] = "WARNING"
    
    # Check memory health
    if memory_stats.get("current_memory_mb", 0) > 3072:
        critical_alerts.append("High memory usage detected")
        integrated_report["overall_status"] = "WARNING"
    
    if memory_stats.get("leak_alerts", 0) > 0:
        critical_alerts.append("Memory leak detected")
        integrated_report["overall_status"] = "CRITICAL"
    
    integrated_report["critical_alerts"] = critical_alerts
    integrated_report["recommendations"] = db_report.get("recommendations", [])
    
    return integrated_report

if __name__ == "__main__":
    # Test the database performance monitor
    setup_database_monitoring()
    
    try:
        # Let it run for a minute to collect some data
        import time
        time.sleep(60)
        
        # Generate and print report
        report = get_integrated_health_report()
        print("🔍 Integrated Health Report:")
        print(json.dumps(report, indent=2, default=str))
        
    finally:
        db_performance_monitor.stop_monitoring()
        memory_monitor.stop_monitoring()
