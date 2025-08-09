#!/usr/bin/env python3
"""
🔍 MEFAPEX Database Status Checker
=================================

This script analyzes the current database setup and provides recommendations
for production deployment.
"""

import os
import sys
import logging
from pathlib import Path
import subprocess

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def check_environment():
    """Check current environment and configuration"""
    print("🔍 MEFAPEX Database Status Analysis")
    print("=" * 50)
    
    # Check environment
    environment = os.getenv("ENVIRONMENT", "development")
    print(f"📍 Environment: {environment}")
    
    # Check if SQLite database exists
    sqlite_files = [
        "mefapex.db",
        "chatbot.db",
        "./data/mefapex.db"
    ]
    
    current_sqlite = None
    for db_file in sqlite_files:
        if os.path.exists(db_file):
            current_sqlite = db_file
            size = os.path.getsize(db_file) / 1024 / 1024  # MB
            print(f"📁 Found SQLite database: {db_file} ({size:.2f} MB)")
            break
    
    if not current_sqlite:
        print("❌ No SQLite database found")
        return
    
    # Analyze SQLite content
    try:
        import sqlite3
        conn = sqlite3.connect(current_sqlite)
        cursor = conn.cursor()
        
        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"📊 Tables found: {', '.join(tables)}")
        
        # Count records
        total_records = 0
        for table in ['users', 'chat_sessions', 'chat_messages']:
            if table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"   📈 {table}: {count:,} records")
                total_records += count
        
        conn.close()
        
        # Production readiness assessment
        print(f"\n🎯 Total records: {total_records:,}")
        
        if environment == "production":
            print("🚨 CRITICAL PRODUCTION ISSUE DETECTED!")
            print("   SQLite is being used in production environment")
            print("   This will cause serious concurrency and performance problems")
            recommend_migration()
        elif total_records > 1000:
            print("⚠️  WARNING: Large dataset detected")
            print("   Consider migrating to PostgreSQL for better performance")
            recommend_migration()
        elif total_records > 100:
            print("💡 RECOMMENDATION: Consider production database")
            print("   Your application is growing - plan for PostgreSQL migration")
        else:
            print("✅ Development setup looks good")
            print("   Consider PostgreSQL for production deployment")
            
    except ImportError:
        print("❌ Cannot analyze SQLite database (sqlite3 not available)")
    except Exception as e:
        print(f"❌ Error analyzing database: {e}")

def check_production_requirements():
    """Check if production database requirements are available"""
    print("\n🔧 Production Database Requirements Check")
    print("-" * 45)
    
    # Check environment variables
    postgres_vars = {
        'POSTGRES_HOST': os.getenv('POSTGRES_HOST'),
        'POSTGRES_USER': os.getenv('POSTGRES_USER'),
        'POSTGRES_PASSWORD': os.getenv('POSTGRES_PASSWORD'),
        'POSTGRES_DB': os.getenv('POSTGRES_DB'),
    }
    
    mysql_vars = {
        'MYSQL_HOST': os.getenv('MYSQL_HOST'),
        'MYSQL_USER': os.getenv('MYSQL_USER'),
        'MYSQL_PASSWORD': os.getenv('MYSQL_PASSWORD'),
        'MYSQL_DATABASE': os.getenv('MYSQL_DATABASE'),
    }
    
    database_url = os.getenv('DATABASE_URL')
    
    if database_url:
        print(f"✅ DATABASE_URL configured: {database_url[:20]}...")
        if database_url.startswith("postgresql"):
            print("   🐘 PostgreSQL URL detected")
        elif database_url.startswith("mysql"):
            print("   🐬 MySQL URL detected")
    
    postgres_configured = all(postgres_vars.values())
    mysql_configured = all(mysql_vars.values())
    
    if postgres_configured:
        print("✅ PostgreSQL configuration found:")
        for key, value in postgres_vars.items():
            display_value = "***" if "PASSWORD" in key and value else value
            print(f"   {key}: {display_value}")
    
    if mysql_configured:
        print("✅ MySQL configuration found:")
        for key, value in mysql_vars.items():
            display_value = "***" if "PASSWORD" in key and value else value
            print(f"   {key}: {display_value}")
    
    if not postgres_configured and not mysql_configured and not database_url:
        print("❌ No production database configured")
        print("   Set up PostgreSQL or MySQL environment variables")

def check_dependencies():
    """Check if required dependencies are installed"""
    print("\n📦 Dependency Check")
    print("-" * 20)
    
    dependencies = {
        'sqlalchemy': 'SQLAlchemy ORM',
        'psycopg2': 'PostgreSQL driver',
        'pymysql': 'MySQL driver',
    }
    
    for package, description in dependencies.items():
        try:
            __import__(package)
            print(f"✅ {package}: {description}")
        except ImportError:
            print(f"❌ {package}: {description} (not installed)")

def recommend_migration():
    """Provide migration recommendations"""
    print("\n🚀 Migration Recommendations")
    print("-" * 30)
    
    print("1. 📦 Install production database:")
    print("   # PostgreSQL (recommended)")
    print("   docker run -d --name postgres \\")
    print("     -e POSTGRES_DB=mefapex_chatbot \\")
    print("     -e POSTGRES_USER=mefapex \\")
    print("     -e POSTGRES_PASSWORD=secure_password \\")
    print("     -p 5432:5432 postgres:15-alpine")
    
    print("\n2. 🔧 Configure environment:")
    print("   cp .env.production .env")
    print("   # Edit .env with your database settings")
    
    print("\n3. 📥 Install dependencies:")
    print("   pip install psycopg2-binary  # PostgreSQL")
    print("   pip install pymysql          # MySQL")
    
    print("\n4. 🔄 Run migration:")
    print("   python migrate_database.py --from sqlite --to postgresql")
    
    print("\n5. ✅ Test production setup:")
    print("   python main.py")
    print("   curl http://localhost:8000/health")

def check_docker_setup():
    """Check Docker setup for production deployment"""
    print("\n🐳 Docker Setup Check")
    print("-" * 20)
    
    docker_files = [
        'docker-compose.yml',
        'docker-compose.production.yml',
        'Dockerfile'
    ]
    
    for file in docker_files:
        if os.path.exists(file):
            print(f"✅ {file}")
        else:
            print(f"❌ {file} (missing)")
    
    # Check if Docker is running
    try:
        result = subprocess.run(['docker', '--version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"✅ Docker: {result.stdout.strip()}")
        else:
            print("❌ Docker not available")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("❌ Docker not available")

def main():
    """Main analysis function"""
    try:
        check_environment()
        check_production_requirements()
        check_dependencies()
        check_docker_setup()
        
        print("\n" + "=" * 50)
        print("📋 SUMMARY")
        print("=" * 50)
        
        environment = os.getenv("ENVIRONMENT", "development")
        
        if environment == "production":
            print("🚨 URGENT ACTION REQUIRED:")
            print("   Your application is configured for production but using SQLite")
            print("   This will cause serious problems under load")
            print("   Migrate to PostgreSQL immediately!")
        else:
            print("💡 DEVELOPMENT SETUP:")
            print("   Current setup is suitable for development")
            print("   Plan PostgreSQL migration before production deployment")
        
        print("\n📖 Next Steps:")
        print("   1. Read: PRODUCTION_DATABASE_MIGRATION.md")
        print("   2. Configure: .env.production")
        print("   3. Migrate: python migrate_database.py")
        print("   4. Deploy: docker-compose -f docker-compose.production.yml up")
        
    except KeyboardInterrupt:
        print("\n⚠️  Analysis interrupted")
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
