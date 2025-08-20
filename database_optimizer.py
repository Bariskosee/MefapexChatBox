"""
🚀 MEFAPEX Database Optimization Manager
========================================
Advanced PostgreSQL optimization management for production performance
"""

import os
import logging
import asyncio
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import time

# Configure logger
logger = logging.getLogger(__name__)

@dataclass
class OptimizationResult:
    """Result of database optimization operation"""
    operation: str
    success: bool
    duration_seconds: float
    details: Dict[str, Any]
    timestamp: datetime

class DatabaseOptimizer:
    """
    Advanced PostgreSQL optimization manager for MEFAPEX ChatBox
    """
    
    def __init__(self):
        # Database configuration from environment
        self.host = os.getenv("POSTGRES_HOST", "localhost")
        self.port = int(os.getenv("POSTGRES_PORT", "5432"))
        self.database = os.getenv("POSTGRES_DB", "mefapex_chatbot")
        self.user = os.getenv("POSTGRES_USER", "mefapex")
        self.password = os.getenv("POSTGRES_PASSWORD", "mefapex")
        
        self.connection = None
        self.optimization_history = []
        
        logger.info(f"🔧 Database Optimizer initialized for {self.host}:{self.port}/{self.database}")

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
            logger.info("✅ Database connection established")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to database: {e}")
            raise

    def disconnect(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("📊 Database connection closed")

    def execute_sql_file(self, file_path: str) -> OptimizationResult:
        """Execute SQL file and return optimization result"""
        start_time = time.time()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                sql_content = file.read()
            
            # Split SQL into individual statements
            statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
            
            cursor = self.connection.cursor()
            executed_statements = 0
            failed_statements = 0
            
            for statement in statements:
                # Skip comments and empty statements
                if statement.startswith('--') or statement.startswith('/*') or not statement.strip():
                    continue
                    
                try:
                    cursor.execute(statement)
                    executed_statements += 1
                    logger.debug(f"✅ Executed: {statement[:50]}...")
                    
                except Exception as e:
                    failed_statements += 1
                    logger.warning(f"⚠️ Failed statement: {statement[:50]}... Error: {e}")
            
            duration = time.time() - start_time
            
            result = OptimizationResult(
                operation=f"execute_sql_file_{os.path.basename(file_path)}",
                success=failed_statements == 0,
                duration_seconds=duration,
                details={
                    "file_path": file_path,
                    "executed_statements": executed_statements,
                    "failed_statements": failed_statements,
                    "total_statements": len(statements)
                },
                timestamp=datetime.now()
            )
            
            self.optimization_history.append(result)
            logger.info(f"🚀 SQL file executed: {executed_statements} statements in {duration:.2f}s")
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ Failed to execute SQL file {file_path}: {e}")
            
            result = OptimizationResult(
                operation=f"execute_sql_file_{os.path.basename(file_path)}",
                success=False,
                duration_seconds=duration,
                details={"error": str(e), "file_path": file_path},
                timestamp=datetime.now()
            )
            
            self.optimization_history.append(result)
            return result

    def apply_optimizations(self) -> List[OptimizationResult]:
        """Apply all database optimizations"""
        results = []
        
        # 1. Apply main optimization script
        optimization_file = os.path.join(os.path.dirname(__file__), "optimizations.sql")
        if os.path.exists(optimization_file):
            result = self.execute_sql_file(optimization_file)
            results.append(result)
        else:
            logger.warning(f"⚠️ Optimization file not found: {optimization_file}")
        
        # 2. Create indexes concurrently
        results.append(self.create_performance_indexes())
        
        # 3. Update table statistics
        results.append(self.update_statistics())
        
        # 4. Configure autovacuum
        results.append(self.configure_autovacuum())
        
        return results

    def create_performance_indexes(self) -> OptimizationResult:
        """Create performance-optimized indexes"""
        start_time = time.time()
        
        indexes = [
            {
                "name": "idx_messages_user_timestamp_performance",
                "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_messages_user_timestamp_performance ON chat_messages(user_id, timestamp DESC)"
            },
            {
                "name": "idx_messages_session_timestamp_performance", 
                "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_messages_session_timestamp_performance ON chat_messages(session_id, timestamp ASC)"
            },
            {
                "name": "idx_sessions_active_performance",
                "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sessions_active_performance ON chat_sessions(user_id, last_activity DESC) WHERE is_active = true"
            },
            {
                "name": "idx_messages_search_turkish",
                "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_messages_search_turkish ON chat_messages USING gin(to_tsvector('turkish', COALESCE(user_message, '') || ' ' || COALESCE(bot_response, '')))"
            }
        ]
        
        cursor = self.connection.cursor()
        created_indexes = 0
        failed_indexes = 0
        
        for index in indexes:
            try:
                logger.info(f"🔨 Creating index: {index['name']}")
                cursor.execute(index['sql'])
                created_indexes += 1
                logger.info(f"✅ Created index: {index['name']}")
                
            except Exception as e:
                failed_indexes += 1
                logger.warning(f"⚠️ Failed to create index {index['name']}: {e}")
        
        duration = time.time() - start_time
        
        result = OptimizationResult(
            operation="create_performance_indexes",
            success=failed_indexes == 0,
            duration_seconds=duration,
            details={
                "created_indexes": created_indexes,
                "failed_indexes": failed_indexes,
                "total_indexes": len(indexes)
            },
            timestamp=datetime.now()
        )
        
        self.optimization_history.append(result)
        return result

    def update_statistics(self) -> OptimizationResult:
        """Update table statistics for better query planning"""
        start_time = time.time()
        
        tables = ["users", "chat_sessions", "chat_messages"]
        cursor = self.connection.cursor()
        
        try:
            for table in tables:
                logger.info(f"📊 Analyzing table: {table}")
                cursor.execute(f"ANALYZE {table}")
            
            duration = time.time() - start_time
            
            result = OptimizationResult(
                operation="update_statistics",
                success=True,
                duration_seconds=duration,
                details={"analyzed_tables": tables},
                timestamp=datetime.now()
            )
            
            logger.info(f"✅ Statistics updated for {len(tables)} tables in {duration:.2f}s")
            
        except Exception as e:
            duration = time.time() - start_time
            result = OptimizationResult(
                operation="update_statistics",
                success=False,
                duration_seconds=duration,
                details={"error": str(e)},
                timestamp=datetime.now()
            )
            
            logger.error(f"❌ Failed to update statistics: {e}")
        
        self.optimization_history.append(result)
        return result

    def configure_autovacuum(self) -> OptimizationResult:
        """Configure autovacuum settings for optimal performance"""
        start_time = time.time()
        
        autovacuum_settings = [
            "ALTER TABLE chat_messages SET (autovacuum_vacuum_scale_factor = 0.1)",
            "ALTER TABLE chat_messages SET (autovacuum_analyze_scale_factor = 0.05)",
            "ALTER TABLE chat_sessions SET (autovacuum_vacuum_scale_factor = 0.2)",
            "ALTER TABLE users SET (autovacuum_vacuum_scale_factor = 0.2)"
        ]
        
        cursor = self.connection.cursor()
        applied_settings = 0
        
        try:
            for setting in autovacuum_settings:
                cursor.execute(setting)
                applied_settings += 1
                logger.debug(f"✅ Applied: {setting}")
            
            duration = time.time() - start_time
            
            result = OptimizationResult(
                operation="configure_autovacuum",
                success=True,
                duration_seconds=duration,
                details={"applied_settings": applied_settings},
                timestamp=datetime.now()
            )
            
            logger.info(f"✅ Autovacuum configured: {applied_settings} settings applied")
            
        except Exception as e:
            duration = time.time() - start_time
            result = OptimizationResult(
                operation="configure_autovacuum",
                success=False,
                duration_seconds=duration,
                details={"error": str(e)},
                timestamp=datetime.now()
            )
            
            logger.error(f"❌ Failed to configure autovacuum: {e}")
        
        self.optimization_history.append(result)
        return result

    def cleanup_old_data(self, retention_months: int = 6) -> OptimizationResult:
        """Clean up old data using the optimized cleanup function"""
        start_time = time.time()
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT cleanup_old_data(%s)", (retention_months,))
            result_data = cursor.fetchone()[0]
            
            duration = time.time() - start_time
            
            result = OptimizationResult(
                operation="cleanup_old_data",
                success=True,
                duration_seconds=duration,
                details=result_data,
                timestamp=datetime.now()
            )
            
            logger.info(f"🧹 Data cleanup completed: {result_data}")
            
        except Exception as e:
            duration = time.time() - start_time
            result = OptimizationResult(
                operation="cleanup_old_data",
                success=False,
                duration_seconds=duration,
                details={"error": str(e)},
                timestamp=datetime.now()
            )
            
            logger.error(f"❌ Data cleanup failed: {e}")
        
        self.optimization_history.append(result)
        return result

    def run_maintenance(self) -> OptimizationResult:
        """Run maintenance tasks using the optimized maintenance function"""
        start_time = time.time()
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT maintenance_tasks()")
            result_data = cursor.fetchone()[0]
            
            duration = time.time() - start_time
            
            result = OptimizationResult(
                operation="run_maintenance",
                success=True,
                duration_seconds=duration,
                details=result_data,
                timestamp=datetime.now()
            )
            
            logger.info(f"🔧 Maintenance completed: {result_data}")
            
        except Exception as e:
            duration = time.time() - start_time
            result = OptimizationResult(
                operation="run_maintenance",
                success=False,
                duration_seconds=duration,
                details={"error": str(e)},
                timestamp=datetime.now()
            )
            
            logger.error(f"❌ Maintenance failed: {e}")
        
        self.optimization_history.append(result)
        return result

    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT generate_performance_report()")
            report = cursor.fetchone()[0]
            
            logger.info("📈 Performance report generated")
            return report
            
        except Exception as e:
            logger.error(f"❌ Failed to generate performance report: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}

    def get_database_health(self) -> Dict[str, Any]:
        """Get current database health status"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT database_health_check()")
            health = cursor.fetchone()[0]
            
            logger.info("💚 Database health check completed")
            return health
            
        except Exception as e:
            logger.error(f"❌ Failed to check database health: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}

    def get_optimization_history(self) -> List[Dict[str, Any]]:
        """Get history of optimization operations"""
        return [
            {
                "operation": result.operation,
                "success": result.success,
                "duration_seconds": result.duration_seconds,
                "details": result.details,
                "timestamp": result.timestamp.isoformat()
            }
            for result in self.optimization_history
        ]

    def run_full_optimization(self) -> Dict[str, Any]:
        """Run complete optimization suite"""
        logger.info("🚀 Starting full database optimization...")
        
        start_time = time.time()
        
        # Connect to database
        self.connect()
        
        try:
            # Run all optimizations
            optimization_results = self.apply_optimizations()
            
            # Run cleanup
            cleanup_result = self.cleanup_old_data()
            optimization_results.append(cleanup_result)
            
            # Run maintenance
            maintenance_result = self.run_maintenance()
            optimization_results.append(maintenance_result)
            
            # Generate final report
            performance_report = self.get_performance_report()
            health_report = self.get_database_health()
            
            total_duration = time.time() - start_time
            
            summary = {
                "optimization_completed": True,
                "total_duration_seconds": total_duration,
                "total_operations": len(optimization_results),
                "successful_operations": sum(1 for r in optimization_results if r.success),
                "failed_operations": sum(1 for r in optimization_results if not r.success),
                "performance_report": performance_report,
                "health_report": health_report,
                "optimization_history": self.get_optimization_history(),
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"🎉 Full optimization completed in {total_duration:.2f}s")
            return summary
            
        except Exception as e:
            logger.error(f"❌ Full optimization failed: {e}")
            return {
                "optimization_completed": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        
        finally:
            self.disconnect()

# CLI interface for running optimizations
def main():
    """Main CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="MEFAPEX Database Optimizer")
    parser.add_argument("--operation", choices=[
        "full", "indexes", "statistics", "cleanup", "maintenance", "health", "report"
    ], default="full", help="Operation to perform")
    parser.add_argument("--retention-months", type=int, default=6, 
                       help="Data retention period in months for cleanup")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    optimizer = DatabaseOptimizer()
    
    try:
        if args.operation == "full":
            result = optimizer.run_full_optimization()
            print("🚀 Full Optimization Results:")
            print(json.dumps(result, indent=2, default=str))
            
        elif args.operation == "indexes":
            optimizer.connect()
            result = optimizer.create_performance_indexes()
            optimizer.disconnect()
            print(f"🔨 Index Creation Result: {result.success}")
            
        elif args.operation == "statistics":
            optimizer.connect()
            result = optimizer.update_statistics()
            optimizer.disconnect()
            print(f"📊 Statistics Update Result: {result.success}")
            
        elif args.operation == "cleanup":
            optimizer.connect()
            result = optimizer.cleanup_old_data(args.retention_months)
            optimizer.disconnect()
            print(f"🧹 Cleanup Result: {result.details}")
            
        elif args.operation == "maintenance":
            optimizer.connect()
            result = optimizer.run_maintenance()
            optimizer.disconnect()
            print(f"🔧 Maintenance Result: {result.details}")
            
        elif args.operation == "health":
            optimizer.connect()
            health = optimizer.get_database_health()
            optimizer.disconnect()
            print("💚 Database Health:")
            print(json.dumps(health, indent=2, default=str))
            
        elif args.operation == "report":
            optimizer.connect()
            report = optimizer.get_performance_report()
            optimizer.disconnect()
            print("📈 Performance Report:")
            print(json.dumps(report, indent=2, default=str))
            
    except Exception as e:
        logger.error(f"❌ Operation failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
