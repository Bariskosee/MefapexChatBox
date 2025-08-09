#!/usr/bin/env python3
"""
🔄 MEFAPEX Database Migration Tool
================================

This script helps migrate data from SQLite to PostgreSQL/MySQL for production deployment.

Features:
- Automatic data migration from SQLite to PostgreSQL/MySQL
- Data validation and integrity checks
- Backup creation before migration
- Progress tracking
- Rollback capabilities
- Performance optimization during migration

Usage:
    python migrate_database.py --from sqlite --to postgresql
    python migrate_database.py --from sqlite --to mysql
    python migrate_database.py --validate-only
"""

import os
import sys
import sqlite3
import argparse
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import json
import shutil

# Add the project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'migration_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DatabaseMigrator:
    """Database migration utility"""
    
    def __init__(self, source_type: str, target_type: str):
        self.source_type = source_type.lower()
        self.target_type = target_type.lower()
        self.source_conn = None
        self.target_conn = None
        self.migration_stats = {
            'start_time': None,
            'end_time': None,
            'users_migrated': 0,
            'sessions_migrated': 0,
            'messages_migrated': 0,
            'errors': []
        }
    
    def connect_source_database(self) -> bool:
        """Connect to source database (SQLite)"""
        try:
            if self.source_type == "sqlite":
                db_path = os.getenv("SQLITE_PATH", "mefapex.db")
                if not os.path.exists(db_path):
                    logger.error(f"SQLite database not found: {db_path}")
                    return False
                
                self.source_conn = sqlite3.connect(db_path)
                self.source_conn.row_factory = sqlite3.Row  # For dict-like access
                logger.info(f"✅ Connected to SQLite database: {db_path}")
                return True
            else:
                logger.error(f"Unsupported source database type: {self.source_type}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to connect to source database: {e}")
            return False
    
    def connect_target_database(self) -> bool:
        """Connect to target database (PostgreSQL/MySQL)"""
        try:
            if self.target_type == "postgresql":
                import psycopg2
                from psycopg2.extras import RealDictCursor
                
                conn_params = {
                    'host': os.getenv('POSTGRES_HOST', 'localhost'),
                    'port': os.getenv('POSTGRES_PORT', 5432),
                    'user': os.getenv('POSTGRES_USER', 'mefapex'),
                    'password': os.getenv('POSTGRES_PASSWORD'),
                    'database': os.getenv('POSTGRES_DB', 'mefapex_chatbot')
                }
                
                if not conn_params['password']:
                    logger.error("POSTGRES_PASSWORD environment variable is required")
                    return False
                
                self.target_conn = psycopg2.connect(**conn_params)
                self.target_conn.autocommit = False  # We'll manage transactions
                logger.info(f"✅ Connected to PostgreSQL: {conn_params['host']}:{conn_params['port']}")
                return True
                
            elif self.target_type == "mysql":
                import pymysql
                
                conn_params = {
                    'host': os.getenv('MYSQL_HOST', 'localhost'),
                    'port': int(os.getenv('MYSQL_PORT', 3306)),
                    'user': os.getenv('MYSQL_USER', 'root'),
                    'password': os.getenv('MYSQL_PASSWORD'),
                    'database': os.getenv('MYSQL_DATABASE', 'mefapex_chatbot'),
                    'charset': 'utf8mb4',
                    'autocommit': False
                }
                
                if not conn_params['password']:
                    logger.error("MYSQL_PASSWORD environment variable is required")
                    return False
                
                self.target_conn = pymysql.connect(**conn_params)
                logger.info(f"✅ Connected to MySQL: {conn_params['host']}:{conn_params['port']}")
                return True
            else:
                logger.error(f"Unsupported target database type: {self.target_type}")
                return False
                
        except ImportError as e:
            logger.error(f"Required database driver not installed: {e}")
            logger.info("Install with: pip install psycopg2-binary (PostgreSQL) or pip install PyMySQL (MySQL)")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to target database: {e}")
            return False
    
    def create_backup(self) -> str:
        """Create backup of source database"""
        try:
            if self.source_type == "sqlite":
                db_path = os.getenv("SQLITE_PATH", "mefapex.db")
                backup_path = f"mefapex_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                shutil.copy2(db_path, backup_path)
                logger.info(f"📦 Backup created: {backup_path}")
                return backup_path
            else:
                logger.warning("Backup not implemented for non-SQLite sources")
                return ""
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return ""
    
    def validate_source_data(self) -> bool:
        """Validate source database structure and data"""
        try:
            cursor = self.source_conn.cursor()
            
            # Check if required tables exist
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN ('users', 'chat_sessions', 'chat_messages')
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            required_tables = ['users', 'chat_sessions', 'chat_messages']
            missing_tables = [table for table in required_tables if table not in tables]
            
            if missing_tables:
                logger.error(f"Missing required tables: {missing_tables}")
                return False
            
            # Count records
            for table in required_tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                logger.info(f"📊 {table}: {count} records")
                
                if table == 'users':
                    self.migration_stats['users_to_migrate'] = count
                elif table == 'chat_sessions':
                    self.migration_stats['sessions_to_migrate'] = count
                elif table == 'chat_messages':
                    self.migration_stats['messages_to_migrate'] = count
            
            return True
            
        except Exception as e:
            logger.error(f"Source data validation failed: {e}")
            return False
    
    def prepare_target_database(self) -> bool:
        """Prepare target database (create tables, indexes)"""
        try:
            cursor = self.target_conn.cursor()
            
            if self.target_type == "postgresql":
                # PostgreSQL table creation
                sql_commands = [
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        user_id VARCHAR(255) UNIQUE NOT NULL,
                        username VARCHAR(255) UNIQUE NOT NULL,
                        email VARCHAR(255) UNIQUE NOT NULL,
                        hashed_password VARCHAR(255) NOT NULL,
                        full_name VARCHAR(255),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT TRUE
                    )
                    """,
                    """
                    CREATE TABLE IF NOT EXISTS chat_sessions (
                        id SERIAL PRIMARY KEY,
                        session_id VARCHAR(255) UNIQUE NOT NULL,
                        user_id VARCHAR(255) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT TRUE,
                        message_count INTEGER DEFAULT 0
                    )
                    """,
                    """
                    CREATE TABLE IF NOT EXISTS chat_messages (
                        id BIGSERIAL PRIMARY KEY,
                        session_id VARCHAR(255) NOT NULL,
                        user_id VARCHAR(255) NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        user_message TEXT,
                        bot_response TEXT,
                        source VARCHAR(100)
                    )
                    """
                ]
                
            elif self.target_type == "mysql":
                # MySQL table creation
                sql_commands = [
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id VARCHAR(255) UNIQUE NOT NULL,
                        username VARCHAR(255) UNIQUE NOT NULL,
                        email VARCHAR(255) UNIQUE NOT NULL,
                        hashed_password VARCHAR(255) NOT NULL,
                        full_name VARCHAR(255),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT TRUE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    """,
                    """
                    CREATE TABLE IF NOT EXISTS chat_sessions (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        session_id VARCHAR(255) UNIQUE NOT NULL,
                        user_id VARCHAR(255) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT TRUE,
                        message_count INT DEFAULT 0
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    """,
                    """
                    CREATE TABLE IF NOT EXISTS chat_messages (
                        id BIGINT AUTO_INCREMENT PRIMARY KEY,
                        session_id VARCHAR(255) NOT NULL,
                        user_id VARCHAR(255) NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        user_message TEXT,
                        bot_response TEXT,
                        source VARCHAR(100)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    """
                ]
            
            # Execute table creation commands
            for sql in sql_commands:
                cursor.execute(sql)
            
            self.target_conn.commit()
            logger.info("✅ Target database tables prepared")
            return True
            
        except Exception as e:
            logger.error(f"Failed to prepare target database: {e}")
            self.target_conn.rollback()
            return False
    
    def migrate_users(self) -> bool:
        """Migrate users table"""
        try:
            # Get data from source
            source_cursor = self.source_conn.cursor()
            source_cursor.execute("SELECT * FROM users")
            users = source_cursor.fetchall()
            
            if not users:
                logger.info("📤 No users to migrate")
                return True
            
            # Insert into target
            target_cursor = self.target_conn.cursor()
            
            for user in users:
                if self.target_type == "postgresql":
                    sql = """
                        INSERT INTO users (user_id, username, email, hashed_password, full_name, created_at, is_active)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (user_id) DO NOTHING
                    """
                elif self.target_type == "mysql":
                    sql = """
                        INSERT IGNORE INTO users (user_id, username, email, hashed_password, full_name, created_at, is_active)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """
                
                values = (
                    user['user_id'],
                    user['username'],
                    user['email'],
                    user['hashed_password'],
                    user['full_name'] if 'full_name' in user.keys() else None,
                    user['created_at'],
                    bool(user['is_active']) if 'is_active' in user.keys() else True
                )
                
                target_cursor.execute(sql, values)
                self.migration_stats['users_migrated'] += 1
            
            self.target_conn.commit()
            logger.info(f"✅ Migrated {len(users)} users")
            return True
            
        except Exception as e:
            logger.error(f"User migration failed: {e}")
            self.target_conn.rollback()
            self.migration_stats['errors'].append(f"User migration: {str(e)}")
            return False
    
    def migrate_sessions(self) -> bool:
        """Migrate chat_sessions table"""
        try:
            # Get data from source
            source_cursor = self.source_conn.cursor()
            source_cursor.execute("SELECT * FROM chat_sessions")
            sessions = source_cursor.fetchall()
            
            if not sessions:
                logger.info("📤 No sessions to migrate")
                return True
            
            # Insert into target
            target_cursor = self.target_conn.cursor()
            
            for session in sessions:
                if self.target_type == "postgresql":
                    sql = """
                        INSERT INTO chat_sessions (session_id, user_id, created_at, updated_at, is_active, message_count)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (session_id) DO NOTHING
                    """
                elif self.target_type == "mysql":
                    sql = """
                        INSERT IGNORE INTO chat_sessions (session_id, user_id, created_at, updated_at, is_active, message_count)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """
                
                values = (
                    session['session_id'],
                    session['user_id'],
                    session['created_at'],
                    session['updated_at'] if 'updated_at' in session.keys() else session['created_at'],
                    bool(session['is_active']) if 'is_active' in session.keys() else True,
                    session['message_count'] if 'message_count' in session.keys() else 0
                )
                
                target_cursor.execute(sql, values)
                self.migration_stats['sessions_migrated'] += 1
            
            self.target_conn.commit()
            logger.info(f"✅ Migrated {len(sessions)} sessions")
            return True
            
        except Exception as e:
            logger.error(f"Session migration failed: {e}")
            self.target_conn.rollback()
            self.migration_stats['errors'].append(f"Session migration: {str(e)}")
            return False
    
    def migrate_messages(self) -> bool:
        """Migrate chat_messages table"""
        try:
            # Get data from source
            source_cursor = self.source_conn.cursor()
            source_cursor.execute("SELECT * FROM chat_messages ORDER BY timestamp")
            messages = source_cursor.fetchall()
            
            if not messages:
                logger.info("📤 No messages to migrate")
                return True
            
            # Insert into target in batches for better performance
            target_cursor = self.target_conn.cursor()
            batch_size = 1000
            
            for i in range(0, len(messages), batch_size):
                batch = messages[i:i + batch_size]
                
                if self.target_type == "postgresql":
                    sql = """
                        INSERT INTO chat_messages (session_id, user_id, timestamp, user_message, bot_response, source)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """
                elif self.target_type == "mysql":
                    sql = """
                        INSERT INTO chat_messages (session_id, user_id, timestamp, user_message, bot_response, source)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """
                
                batch_values = []
                for message in batch:
                    values = (
                        message['session_id'],
                        message['user_id'],
                        message['timestamp'],
                        message['user_message'] if 'user_message' in message.keys() else None,
                        message['bot_response'] if 'bot_response' in message.keys() else None,
                        message['source'] if 'source' in message.keys() else 'migrated'
                    )
                    batch_values.append(values)
                
                target_cursor.executemany(sql, batch_values)
                self.migration_stats['messages_migrated'] += len(batch)
                
                # Commit each batch
                self.target_conn.commit()
                
                if i % (batch_size * 10) == 0:  # Progress update every 10 batches
                    logger.info(f"📤 Migrated {self.migration_stats['messages_migrated']}/{len(messages)} messages")
            
            logger.info(f"✅ Migrated {len(messages)} messages")
            return True
            
        except Exception as e:
            logger.error(f"Message migration failed: {e}")
            self.target_conn.rollback()
            self.migration_stats['errors'].append(f"Message migration: {str(e)}")
            return False
    
    def create_indexes(self) -> bool:
        """Create indexes for optimal performance"""
        try:
            target_cursor = self.target_conn.cursor()
            
            if self.target_type == "postgresql":
                index_commands = [
                    "CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id)",
                    "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)",
                    "CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON chat_sessions(user_id)",
                    "CREATE INDEX IF NOT EXISTS idx_sessions_session_id ON chat_sessions(session_id)",
                    "CREATE INDEX IF NOT EXISTS idx_messages_user_id ON chat_messages(user_id)",
                    "CREATE INDEX IF NOT EXISTS idx_messages_session_id ON chat_messages(session_id)",
                    "CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON chat_messages(timestamp)"
                ]
            elif self.target_type == "mysql":
                index_commands = [
                    "CREATE INDEX idx_users_user_id ON users(user_id)",
                    "CREATE INDEX idx_users_username ON users(username)",
                    "CREATE INDEX idx_sessions_user_id ON chat_sessions(user_id)",
                    "CREATE INDEX idx_sessions_session_id ON chat_sessions(session_id)",
                    "CREATE INDEX idx_messages_user_id ON chat_messages(user_id)",
                    "CREATE INDEX idx_messages_session_id ON chat_messages(session_id)",
                    "CREATE INDEX idx_messages_timestamp ON chat_messages(timestamp)"
                ]
            
            for sql in index_commands:
                try:
                    target_cursor.execute(sql)
                except Exception as e:
                    # Index might already exist
                    if "already exists" not in str(e).lower() and "duplicate" not in str(e).lower():
                        logger.warning(f"Index creation warning: {e}")
            
            self.target_conn.commit()
            logger.info("✅ Database indexes created")
            return True
            
        except Exception as e:
            logger.error(f"Index creation failed: {e}")
            return False
    
    def validate_migration(self) -> bool:
        """Validate that migration was successful"""
        try:
            source_cursor = self.source_conn.cursor()
            target_cursor = self.target_conn.cursor()
            
            # Count records in both databases
            tables = ['users', 'chat_sessions', 'chat_messages']
            
            for table in tables:
                # Source count
                source_cursor.execute(f"SELECT COUNT(*) FROM {table}")
                source_count = source_cursor.fetchone()[0]
                
                # Target count
                target_cursor.execute(f"SELECT COUNT(*) FROM {table}")
                target_count = target_cursor.fetchone()[0]
                
                if source_count != target_count:
                    logger.error(f"❌ Count mismatch in {table}: source={source_count}, target={target_count}")
                    return False
                else:
                    logger.info(f"✅ {table}: {source_count} records migrated successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"Migration validation failed: {e}")
            return False
    
    def run_migration(self) -> bool:
        """Run the complete migration process"""
        logger.info("🚀 Starting database migration")
        self.migration_stats['start_time'] = datetime.now()
        
        try:
            # Step 1: Connect to databases
            if not self.connect_source_database():
                return False
            
            if not self.connect_target_database():
                return False
            
            # Step 2: Create backup
            backup_path = self.create_backup()
            
            # Step 3: Validate source data
            if not self.validate_source_data():
                return False
            
            # Step 4: Prepare target database
            if not self.prepare_target_database():
                return False
            
            # Step 5: Migrate data
            steps = [
                ("users", self.migrate_users),
                ("sessions", self.migrate_sessions),
                ("messages", self.migrate_messages)
            ]
            
            for step_name, step_func in steps:
                logger.info(f"📤 Migrating {step_name}...")
                if not step_func():
                    logger.error(f"❌ Migration failed at step: {step_name}")
                    return False
            
            # Step 6: Create indexes
            self.create_indexes()
            
            # Step 7: Validate migration
            if not self.validate_migration():
                return False
            
            self.migration_stats['end_time'] = datetime.now()
            duration = self.migration_stats['end_time'] - self.migration_stats['start_time']
            
            logger.info("🎉 Migration completed successfully!")
            logger.info(f"⏱️  Duration: {duration}")
            logger.info(f"📊 Users: {self.migration_stats['users_migrated']}")
            logger.info(f"📊 Sessions: {self.migration_stats['sessions_migrated']}")
            logger.info(f"📊 Messages: {self.migration_stats['messages_migrated']}")
            
            if backup_path:
                logger.info(f"💾 Backup saved at: {backup_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            return False
        
        finally:
            # Close connections
            if self.source_conn:
                self.source_conn.close()
            if self.target_conn:
                self.target_conn.close()

def main():
    parser = argparse.ArgumentParser(description='MEFAPEX Database Migration Tool')
    parser.add_argument('--from', dest='source', required=True, 
                       choices=['sqlite'], help='Source database type')
    parser.add_argument('--to', dest='target', required=True,
                       choices=['postgresql', 'mysql'], help='Target database type')
    parser.add_argument('--validate-only', action='store_true',
                       help='Only validate source data without migrating')
    parser.add_argument('--backup-only', action='store_true',
                       help='Only create backup without migrating')
    
    args = parser.parse_args()
    
    migrator = DatabaseMigrator(args.source, args.target)
    
    if args.validate_only:
        logger.info("🔍 Validation mode - checking source data only")
        if migrator.connect_source_database():
            valid = migrator.validate_source_data()
            sys.exit(0 if valid else 1)
    
    elif args.backup_only:
        logger.info("💾 Backup mode - creating backup only")
        if migrator.connect_source_database():
            backup_path = migrator.create_backup()
            if backup_path:
                logger.info(f"✅ Backup created: {backup_path}")
                sys.exit(0)
            else:
                sys.exit(1)
    
    else:
        # Full migration
        success = migrator.run_migration()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
