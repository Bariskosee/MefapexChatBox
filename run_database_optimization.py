#!/usr/bin/env python3
"""
🚀 MEFAPEX Database Optimization Runner
======================================
Complete database optimization deployment script
"""

import os
import sys
import logging
import argparse
import json
from datetime import datetime
from database_optimizer import DatabaseOptimizer
from database_performance_monitor import setup_database_monitoring, get_integrated_health_report
from memory_monitor import setup_memory_monitoring

# Configure logging
def setup_logging(verbose: bool = False):
    """Setup logging configuration"""
    log_level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('database_optimization.log')
        ]
    )

def print_banner():
    """Print optimization banner"""
    banner = """
    🚀 MEFAPEX Database Optimization Suite
    =====================================
    Advanced PostgreSQL Performance Optimization
    
    Features:
    ✅ Advanced indexing strategy
    ✅ Table partitioning support  
    ✅ Query optimization functions
    ✅ Automated cleanup procedures
    ✅ Performance monitoring
    ✅ Turkish full-text search
    ✅ Memory leak detection
    ✅ Real-time alerts
    
    """
    print(banner)

def check_database_connection() -> bool:
    """Check if database is accessible"""
    try:
        optimizer = DatabaseOptimizer()
        optimizer.connect()
        
        # Test basic query
        cursor = optimizer.connection.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        
        optimizer.disconnect()
        
        print(f"✅ Database connection successful")
        print(f"📊 PostgreSQL version: {version}")
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("   Please ensure PostgreSQL is running and accessible")
        return False

def run_optimization_suite():
    """Run complete optimization suite"""
    print("\n🔧 Starting Database Optimization Suite...\n")
    
    optimizer = DatabaseOptimizer()
    
    try:
        # Run full optimization
        result = optimizer.run_full_optimization()
        
        print("\n📊 Optimization Results Summary:")
        print("=" * 50)
        print(f"✅ Completed: {result['optimization_completed']}")
        print(f"⏱️  Duration: {result['total_duration_seconds']:.2f} seconds")
        print(f"🔧 Total Operations: {result['total_operations']}")
        print(f"✅ Successful: {result['successful_operations']}")
        print(f"❌ Failed: {result['failed_operations']}")
        
        # Show performance improvements
        if 'performance_report' in result:
            health = result.get('health_report', {})
            print(f"\n💚 Database Health:")
            print(f"   Status: {health.get('status', 'Unknown')}")
            print(f"   Cache Hit Ratio: {health.get('cache_hit_ratio_percent', 0):.1f}%")
            print(f"   Database Size: {health.get('database_size_mb', 0):.1f}MB")
            print(f"   Active Connections: {health.get('connection_count', 0)}")
        
        # Show recommendations
        perf_report = result.get('performance_report', {})
        recommendations = perf_report.get('recommendations', [])
        if recommendations:
            print(f"\n💡 Recommendations:")
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. {rec}")
        
        return result['optimization_completed']
        
    except Exception as e:
        print(f"❌ Optimization failed: {e}")
        return False

def setup_monitoring():
    """Setup integrated monitoring"""
    print("\n📊 Setting up Performance Monitoring...\n")
    
    try:
        # Setup memory monitoring
        setup_memory_monitoring()
        print("✅ Memory monitoring started")
        
        # Setup database monitoring  
        setup_database_monitoring()
        print("✅ Database performance monitoring started")
        
        print("\n🔍 Monitoring Features Enabled:")
        print("   • Real-time memory leak detection")
        print("   • Database performance tracking")
        print("   • Connection pool monitoring")
        print("   • Query performance analysis")
        print("   • Automated alert system")
        print("   • Turkish full-text search optimization")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to setup monitoring: {e}")
        return False

def generate_health_report():
    """Generate comprehensive health report"""
    print("\n📈 Generating Health Report...\n")
    
    try:
        report = get_integrated_health_report()
        
        print("🔍 Integrated System Health Report")
        print("=" * 50)
        print(f"Overall Status: {report['overall_status']}")
        print(f"Generated: {report['timestamp']}")
        
        # Database health
        db_stats = report['system_health']['database']['current_stats']
        print(f"\n📊 Database Metrics:")
        print(f"   Connections: {db_stats.get('connection_count', 0)}")
        print(f"   Cache Hit Ratio: {db_stats.get('cache_hit_ratio', 0):.1f}%")
        print(f"   Database Size: {db_stats.get('database_size_mb', 0):.1f}MB")
        print(f"   Active Queries: {db_stats.get('active_queries', 0)}")
        
        # Memory health
        memory_stats = report['system_health']['memory']['current_stats']
        if memory_stats:
            print(f"\n🧠 Memory Metrics:")
            print(f"   Current Usage: {memory_stats.get('current_memory_mb', 0):.1f}MB")
            print(f"   CPU Usage: {memory_stats.get('current_cpu_percent', 0):.1f}%")
            print(f"   Memory Warnings: {memory_stats.get('memory_warnings', 0)}")
            print(f"   Leak Alerts: {memory_stats.get('leak_alerts', 0)}")
        
        # Critical alerts
        if report['critical_alerts']:
            print(f"\n🚨 Critical Alerts:")
            for alert in report['critical_alerts']:
                print(f"   • {alert}")
        else:
            print(f"\n✅ No critical alerts")
        
        # Recommendations
        if report['recommendations']:
            print(f"\n💡 Recommendations:")
            for i, rec in enumerate(report['recommendations'][:5], 1):
                print(f"   {i}. {rec}")
        
        return report
        
    except Exception as e:
        print(f"❌ Failed to generate health report: {e}")
        return None

def validate_optimization():
    """Validate optimization results"""
    print("\n🔍 Validating Optimization Results...\n")
    
    try:
        optimizer = DatabaseOptimizer()
        optimizer.connect()
        
        cursor = optimizer.connection.cursor()
        
        # Check if optimization functions exist
        functions = [
            'cleanup_old_data',
            'maintenance_tasks', 
            'get_chat_history_optimized',
            'search_messages_turkish',
            'database_health_check'
        ]
        
        existing_functions = []
        for func in functions:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_proc p
                    JOIN pg_namespace n ON p.pronamespace = n.oid
                    WHERE n.nspname = 'public' AND p.proname = %s
                )
            """, (func,))
            
            if cursor.fetchone()[0]:
                existing_functions.append(func)
        
        # Check indexes
        cursor.execute("""
            SELECT indexname FROM pg_indexes 
            WHERE schemaname = 'public' 
            AND indexname LIKE 'idx_%'
            ORDER BY indexname
        """)
        indexes = [row[0] for row in cursor.fetchall()]
        
        # Check views
        cursor.execute("""
            SELECT viewname FROM pg_views 
            WHERE schemaname = 'public'
            ORDER BY viewname
        """)
        views = [row[0] for row in cursor.fetchall()]
        
        optimizer.disconnect()
        
        print("✅ Optimization Validation Results:")
        print(f"   Functions Created: {len(existing_functions)}/{len(functions)}")
        print(f"   Indexes Available: {len(indexes)}")
        print(f"   Views Created: {len(views)}")
        
        if len(existing_functions) == len(functions):
            print("   🎉 All optimization functions successfully created!")
        else:
            missing = set(functions) - set(existing_functions)
            print(f"   ⚠️  Missing functions: {', '.join(missing)}")
        
        return len(existing_functions) == len(functions)
        
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return False

def main():
    """Main optimization runner"""
    parser = argparse.ArgumentParser(description="MEFAPEX Database Optimization Runner")
    parser.add_argument("--action", choices=[
        "optimize", "monitor", "report", "validate", "full"
    ], default="full", help="Action to perform")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--output", "-o", help="Output file for reports")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Print banner
    print_banner()
    
    # Check database connection first
    if not check_database_connection():
        print("❌ Cannot proceed without database connection")
        return 1
    
    success = True
    
    if args.action in ["optimize", "full"]:
        success &= run_optimization_suite()
        if success:
            success &= validate_optimization()
    
    if args.action in ["monitor", "full"]:
        success &= setup_monitoring()
    
    if args.action in ["report", "full"]:
        report = generate_health_report()
        if report and args.output:
            try:
                with open(args.output, 'w') as f:
                    json.dump(report, f, indent=2, default=str)
                print(f"📄 Report saved to: {args.output}")
            except Exception as e:
                print(f"❌ Failed to save report: {e}")
    
    if args.action == "validate":
        success = validate_optimization()
    
    # Final status
    print("\n" + "=" * 60)
    if success:
        print("🎉 Database optimization completed successfully!")
        print("\nNext Steps:")
        print("1. Monitor performance metrics regularly")
        print("2. Review alerts and recommendations")
        print("3. Schedule automated cleanup tasks")
        print("4. Consider implementing connection pooling")
    else:
        print("❌ Database optimization completed with errors")
        print("Please check the logs for details")
    
    print("\nFor ongoing monitoring, the system will continue to:")
    print("• Track memory usage and detect leaks")
    print("• Monitor database performance metrics")
    print("• Generate alerts for performance issues")
    print("• Provide optimization recommendations")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
