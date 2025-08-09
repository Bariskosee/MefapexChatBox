"""
🐘 PostgreSQL Production Manager
Enterprise-grade PostgreSQL implementation with full connection pooling,
migrations, backup, and monitoring capabilities
"""

import asyncio
import asyncpg
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
import json
import uuid
import os
import subprocess
from pathlib import Path

from .base import DatabaseInterface, DatabaseConfig, ConnectionStats

logger = logging.getLogger(__name__)

class PostgreSQLManager(DatabaseInterface):
    """Production-grade PostgreSQL manager with enterprise features"""
    
    def __init__(self, config: DatabaseConfig):
        super().__init__(config)
        self.pool: Optional[asyncpg.Pool] = None
        self.connection_url = self._build_connection_url()
        self._transaction_context = None
        
    def _build_connection_url(self) -> str:
        """Build PostgreSQL connection URL"""
        return (
            f"postgresql://{self.config.username}:{self.config.password}"
            f"@{self.config.host}:{self.config.port}/{self.config.database}"
        )
    
    async def initialize(self) -> bool:
        """Initialize PostgreSQL connection pool and schema"""
        try:
            # Create connection pool
            self.pool = await asyncpg.create_pool(
                self.connection_url,
                min_size=self.config.pool_size // 2,
                max_size=self.config.pool_size,
                max_queries=50000,
                max_inactive_connection_lifetime=self.config.pool_recycle,
                timeout=self.config.pool_timeout,
                command_timeout=60
            )
            
            # Create schema if not exists
            await self._create_schema()
            
            # Run migrations
            await self._run_migrations()
            
            # Validate data integrity
            await self.validate_data_integrity()
            
            logger.info("✅ PostgreSQL database initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize PostgreSQL: {e}")
            return False
    
    async def _create_schema(self):
        """Create database schema with constraints and indexes"""
        schema_sql = """
        -- Users table with constraints
        CREATE TABLE IF NOT EXISTS users (
            user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            full_name VARCHAR(100),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP WITH TIME ZONE,
            is_active BOOLEAN DEFAULT true,
            login_attempts INTEGER DEFAULT 0,
            locked_until TIMESTAMP WITH TIME ZONE,
            CONSTRAINT valid_email CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
            CONSTRAINT valid_username CHECK (length(username) >= 3 AND username ~* '^[a-zA-Z0-9_]+$')
        );
        
        -- Chat sessions with proper relationships
        CREATE TABLE IF NOT EXISTS chat_sessions (
            session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL,
            session_type VARCHAR(20) DEFAULT 'chat',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT true,
            session_metadata JSONB DEFAULT '{}',
            message_count INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        );
        
        -- Chat messages with full-text search
        CREATE TABLE IF NOT EXISTS chat_messages (
            message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            session_id UUID NOT NULL,
            user_id UUID NOT NULL,
            message TEXT NOT NULL,
            response TEXT NOT NULL,
            source VARCHAR(20) DEFAULT 'ai',
            timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            response_time_ms INTEGER,
            message_metadata JSONB DEFAULT '{}',
            vector_embedding VECTOR(384), -- For semantic search
            FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            CONSTRAINT valid_source CHECK (source IN ('ai', 'human', 'system')),
            CONSTRAINT non_empty_message CHECK (length(trim(message)) > 0)
        );
        
        -- System logs for monitoring
        CREATE TABLE IF NOT EXISTS system_logs (
            log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            log_level VARCHAR(10) NOT NULL,
            logger_name VARCHAR(100) NOT NULL,
            message TEXT NOT NULL,
            timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            user_id UUID,
            session_id UUID,
            request_id UUID,
            metadata JSONB DEFAULT '{}'
        );
        
        -- Performance indexes
        CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        CREATE INDEX IF NOT EXISTS idx_users_last_login ON users(last_login);
        
        CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON chat_sessions(user_id);
        CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON chat_sessions(created_at);
        CREATE INDEX IF NOT EXISTS idx_sessions_active ON chat_sessions(is_active);
        
        CREATE INDEX IF NOT EXISTS idx_messages_session_id ON chat_messages(session_id);
        CREATE INDEX IF NOT EXISTS idx_messages_user_id ON chat_messages(user_id);
        CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON chat_messages(timestamp);
        CREATE INDEX IF NOT EXISTS idx_messages_source ON chat_messages(source);
        
        -- Full-text search index
        CREATE INDEX IF NOT EXISTS idx_messages_fts ON chat_messages 
        USING gin(to_tsvector('english', message || ' ' || response));
        
        CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON system_logs(timestamp);
        CREATE INDEX IF NOT EXISTS idx_logs_level ON system_logs(log_level);
        
        -- Update trigger for sessions
        CREATE OR REPLACE FUNCTION update_session_timestamp()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        
        CREATE TRIGGER update_session_timestamp_trigger
            BEFORE UPDATE ON chat_sessions
            FOR EACH ROW
            EXECUTE FUNCTION update_session_timestamp();
        
        -- Update message count trigger
        CREATE OR REPLACE FUNCTION update_message_count()
        RETURNS TRIGGER AS $$
        BEGIN
            IF TG_OP = 'INSERT' THEN
                UPDATE chat_sessions 
                SET message_count = message_count + 1 
                WHERE session_id = NEW.session_id;
                RETURN NEW;
            ELSIF TG_OP = 'DELETE' THEN
                UPDATE chat_sessions 
                SET message_count = message_count - 1 
                WHERE session_id = OLD.session_id;
                RETURN OLD;
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
        
        CREATE TRIGGER update_message_count_trigger
            AFTER INSERT OR DELETE ON chat_messages
            FOR EACH ROW
            EXECUTE FUNCTION update_message_count();
        """
        
        async with self.pool.acquire() as conn:
            await conn.execute(schema_sql)
            logger.info("✅ PostgreSQL schema created/updated")
    
    async def _run_migrations(self):
        """Run database migrations"""
        migrations_dir = Path(__file__).parent / "migrations"
        migrations_dir.mkdir(exist_ok=True)
        
        # Create migrations table if not exists
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS migrations (
                    migration_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    migration_name VARCHAR(255) UNIQUE NOT NULL,
                    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    checksum VARCHAR(64) NOT NULL
                )
            """)
            
            # Get applied migrations
            applied = await conn.fetch("SELECT migration_name FROM migrations")
            applied_names = {row['migration_name'] for row in applied}
            
            # Run pending migrations
            migration_files = sorted(migrations_dir.glob("*.sql"))
            for migration_file in migration_files:
                migration_name = migration_file.stem
                if migration_name not in applied_names:
                    await self._apply_migration(conn, migration_file)
    
    async def _apply_migration(self, conn, migration_file: Path):
        """Apply a single migration"""
        migration_sql = migration_file.read_text()
        migration_name = migration_file.stem
        
        # Calculate checksum
        import hashlib
        checksum = hashlib.sha256(migration_sql.encode()).hexdigest()
        
        try:
            async with conn.transaction():
                await conn.execute(migration_sql)
                await conn.execute(
                    "INSERT INTO migrations (migration_name, checksum) VALUES ($1, $2)",
                    migration_name, checksum
                )
                logger.info(f"✅ Applied migration: {migration_name}")
        except Exception as e:
            logger.error(f"❌ Failed to apply migration {migration_name}: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check"""
        start_time = datetime.utcnow()
        
        try:
            async with self.pool.acquire() as conn:
                # Basic connectivity
                await conn.fetchval("SELECT 1")
                
                # Connection pool status
                pool_stats = {
                    "size": self.pool.get_size(),
                    "max_size": self.pool.get_max_size(),
                    "min_size": self.pool.get_min_size(),
                    "idle_size": self.pool.get_idle_size()
                }
                
                # Database stats
                db_stats = await conn.fetchrow("""
                    SELECT 
                        pg_database_size(current_database()) as db_size_bytes,
                        (SELECT count(*) FROM users) as user_count,
                        (SELECT count(*) FROM chat_sessions) as session_count,
                        (SELECT count(*) FROM chat_messages) as message_count
                """)
                
                response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                return {
                    "status": "healthy",
                    "database_type": "postgresql",
                    "response_time_ms": response_time,
                    "pool_stats": pool_stats,
                    "database_stats": dict(db_stats),
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def get_connection_stats(self) -> ConnectionStats:
        """Get real-time connection statistics"""
        if not self.pool:
            return self._connection_stats
        
        return ConnectionStats(
            active_connections=self.pool.get_size() - self.pool.get_idle_size(),
            idle_connections=self.pool.get_idle_size(),
            total_connections=self.pool.get_size(),
            pool_size=self.pool.get_max_size(),
            overflow_connections=max(0, self.pool.get_size() - self.pool.get_min_size()),
            connection_errors=0,  # Would need to track this
            avg_response_time_ms=0.0,  # Would need to track this
            last_health_check=datetime.utcnow()
        )
    
    # Session Management
    async def create_session(self, user_id: str, session_type: str = "chat") -> str:
        """Create new chat session"""
        session_id = str(uuid.uuid4())
        
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO chat_sessions (session_id, user_id, session_type)
                VALUES ($1, $2, $3)
            """, session_id, user_id, session_type)
        
        return session_id
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT session_id, user_id, session_type, created_at, 
                       updated_at, is_active, session_metadata, message_count
                FROM chat_sessions 
                WHERE session_id = $1
            """, session_id)
            
            return dict(row) if row else None
    
    async def get_user_sessions(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get user's sessions with pagination"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT session_id, session_type, created_at, updated_at, 
                       is_active, message_count
                FROM chat_sessions 
                WHERE user_id = $1 AND is_active = true
                ORDER BY updated_at DESC 
                LIMIT $2
            """, user_id, limit)
            
            return [dict(row) for row in rows]
    
    # Message Management
    async def add_message(
        self, 
        session_id: str, 
        user_id: str, 
        message: str, 
        response: str, 
        source: str = "ai"
    ) -> str:
        """Add message to session"""
        message_id = str(uuid.uuid4())
        
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO chat_messages 
                (message_id, session_id, user_id, message, response, source)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, message_id, session_id, user_id, message, response, source)
        
        return message_id
    
    async def get_session_messages(
        self, 
        session_id: str, 
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get session messages with pagination"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT message_id, message, response, source, timestamp, response_time_ms
                FROM chat_messages 
                WHERE session_id = $1
                ORDER BY timestamp ASC
                LIMIT $2 OFFSET $3
            """, session_id, limit, offset)
            
            return [dict(row) for row in rows]
    
    async def get_user_message_history(
        self, 
        user_id: str, 
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get user's complete message history"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT cm.message_id, cm.session_id, cm.message, cm.response, 
                       cm.source, cm.timestamp, cs.session_type
                FROM chat_messages cm
                JOIN chat_sessions cs ON cm.session_id = cs.session_id
                WHERE cm.user_id = $1
                ORDER BY cm.timestamp DESC
                LIMIT $2
            """, user_id, limit)
            
            return [dict(row) for row in rows]
    
    # User Management
    async def create_user(
        self, 
        username: str, 
        email: str, 
        hashed_password: str,
        full_name: Optional[str] = None
    ) -> str:
        """Create new user"""
        user_id = str(uuid.uuid4())
        
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO users (user_id, username, email, hashed_password, full_name)
                VALUES ($1, $2, $3, $4, $5)
            """, user_id, username, email, hashed_password, full_name)
        
        return user_id
    
    async def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT user_id, username, email, hashed_password, full_name, 
                       created_at, last_login, is_active, login_attempts, locked_until
                FROM users 
                WHERE username = $1
            """, username)
            
            return dict(row) if row else None
    
    async def update_user_last_login(self, user_id: str) -> bool:
        """Update user's last login timestamp"""
        async with self.pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE users 
                SET last_login = CURRENT_TIMESTAMP, login_attempts = 0
                WHERE user_id = $1
            """, user_id)
            
            return result.split()[-1] == "1"  # Check if one row was updated
    
    # Analytics & Reporting
    async def get_analytics_data(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get analytics data for date range"""
        async with self.pool.acquire() as conn:
            # User activity
            user_stats = await conn.fetchrow("""
                SELECT 
                    COUNT(DISTINCT user_id) as active_users,
                    COUNT(*) as total_messages,
                    AVG(response_time_ms) as avg_response_time
                FROM chat_messages 
                WHERE timestamp BETWEEN $1 AND $2
            """, start_date, end_date)
            
            # Daily message counts
            daily_stats = await conn.fetch("""
                SELECT 
                    DATE(timestamp) as date,
                    COUNT(*) as message_count,
                    COUNT(DISTINCT user_id) as unique_users
                FROM chat_messages 
                WHERE timestamp BETWEEN $1 AND $2
                GROUP BY DATE(timestamp)
                ORDER BY date
            """, start_date, end_date)
            
            return {
                "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
                "summary": dict(user_stats),
                "daily_stats": [dict(row) for row in daily_stats]
            }
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics"""
        async with self.pool.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT 
                    (SELECT COUNT(*) FROM users) as total_users,
                    (SELECT COUNT(*) FROM users WHERE last_login > CURRENT_TIMESTAMP - INTERVAL '24 hours') as active_users_24h,
                    (SELECT COUNT(*) FROM chat_sessions) as total_sessions,
                    (SELECT COUNT(*) FROM chat_sessions WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '24 hours') as sessions_24h,
                    (SELECT COUNT(*) FROM chat_messages) as total_messages,
                    (SELECT COUNT(*) FROM chat_messages WHERE timestamp > CURRENT_TIMESTAMP - INTERVAL '24 hours') as messages_24h,
                    (SELECT AVG(response_time_ms) FROM chat_messages WHERE response_time_ms IS NOT NULL) as avg_response_time,
                    pg_database_size(current_database()) as database_size_bytes
            """)
            
            return dict(stats)
    
    # Backup & Maintenance
    async def create_backup(self, backup_path: str) -> bool:
        """Create database backup using pg_dump"""
        try:
            backup_file = f"{backup_path}/mefapex_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.sql"
            
            cmd = [
                "pg_dump",
                "-h", self.config.host,
                "-p", str(self.config.port),
                "-U", self.config.username,
                "-d", self.config.database,
                "-f", backup_file,
                "--verbose"
            ]
            
            env = os.environ.copy()
            env["PGPASSWORD"] = self.config.password
            
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"✅ Database backup created: {backup_file}")
                return True
            else:
                logger.error(f"❌ Backup failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Backup error: {e}")
            return False
    
    async def restore_backup(self, backup_path: str) -> bool:
        """Restore database from backup"""
        try:
            cmd = [
                "psql",
                "-h", self.config.host,
                "-p", str(self.config.port),
                "-U", self.config.username,
                "-d", self.config.database,
                "-f", backup_path
            ]
            
            env = os.environ.copy()
            env["PGPASSWORD"] = self.config.password
            
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"✅ Database restored from: {backup_path}")
                return True
            else:
                logger.error(f"❌ Restore failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Restore error: {e}")
            return False
    
    async def optimize_database(self) -> Dict[str, Any]:
        """Run database optimization/maintenance tasks"""
        results = {}
        
        async with self.pool.acquire() as conn:
            # Analyze tables for query optimization
            await conn.execute("ANALYZE")
            results["analyze"] = "completed"
            
            # Update table statistics
            await conn.execute("VACUUM ANALYZE")
            results["vacuum_analyze"] = "completed"
            
            # Get database size after optimization
            size = await conn.fetchval("SELECT pg_database_size(current_database())")
            results["database_size_bytes"] = size
            
            # Check for bloated indexes
            bloated_indexes = await conn.fetch("""
                SELECT schemaname, tablename, indexname, 
                       pg_size_pretty(pg_relation_size(indexname::text)) as size
                FROM pg_indexes 
                WHERE schemaname = 'public'
                ORDER BY pg_relation_size(indexname::text) DESC
                LIMIT 10
            """)
            results["largest_indexes"] = [dict(row) for row in bloated_indexes]
        
        return results
    
    async def validate_data_integrity(self) -> Dict[str, Any]:
        """Validate database integrity and constraints"""
        results = {}
        
        async with self.pool.acquire() as conn:
            # Check foreign key constraints
            fk_violations = await conn.fetch("""
                SELECT 
                    tc.table_name,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name 
                FROM information_schema.table_constraints AS tc 
                JOIN information_schema.key_column_usage AS kcu
                  ON tc.constraint_name = kcu.constraint_name
                  AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                  ON ccu.constraint_name = tc.constraint_name
                  AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY'
                  AND tc.table_schema = 'public'
            """)
            results["foreign_key_constraints"] = len(fk_violations)
            
            # Check for orphaned records
            orphaned_messages = await conn.fetchval("""
                SELECT COUNT(*) FROM chat_messages cm
                LEFT JOIN chat_sessions cs ON cm.session_id = cs.session_id
                WHERE cs.session_id IS NULL
            """)
            results["orphaned_messages"] = orphaned_messages
            
            orphaned_sessions = await conn.fetchval("""
                SELECT COUNT(*) FROM chat_sessions cs
                LEFT JOIN users u ON cs.user_id = u.user_id
                WHERE u.user_id IS NULL
            """)
            results["orphaned_sessions"] = orphaned_sessions
            
            # Check data consistency
            message_count_mismatch = await conn.fetchval("""
                SELECT COUNT(*) FROM chat_sessions cs
                WHERE cs.message_count != (
                    SELECT COUNT(*) FROM chat_messages cm 
                    WHERE cm.session_id = cs.session_id
                )
            """)
            results["message_count_mismatches"] = message_count_mismatch
            
            results["validation_passed"] = (
                orphaned_messages == 0 and 
                orphaned_sessions == 0 and 
                message_count_mismatch == 0
            )
        
        return results
    
    async def cleanup_old_data(self, days_to_keep: int = 90) -> Dict[str, Any]:
        """Clean up old data based on retention policy"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        results = {}
        
        async with self.pool.acquire() as conn:
            # Delete old logs
            deleted_logs = await conn.fetchval("""
                DELETE FROM system_logs 
                WHERE timestamp < $1
                RETURNING COUNT(*)
            """, cutoff_date)
            results["deleted_logs"] = deleted_logs
            
            # Archive old inactive sessions
            archived_sessions = await conn.fetchval("""
                UPDATE chat_sessions 
                SET is_active = false 
                WHERE updated_at < $1 AND is_active = true
                RETURNING COUNT(*)
            """, cutoff_date)
            results["archived_sessions"] = archived_sessions
            
            # Clean up old temporary data (if any)
            results["cleanup_date"] = cutoff_date.isoformat()
        
        return results
    
    # Transaction Management
    async def begin_transaction(self):
        """Start database transaction"""
        if not self._transaction_context:
            conn = await self.pool.acquire()
            self._transaction_context = await conn.transaction()
            await self._transaction_context.start()
    
    async def commit_transaction(self):
        """Commit current transaction"""
        if self._transaction_context:
            await self._transaction_context.commit()
            await self._transaction_context.connection.close()
            self._transaction_context = None
    
    async def rollback_transaction(self):
        """Rollback current transaction"""
        if self._transaction_context:
            await self._transaction_context.rollback()
            await self._transaction_context.connection.close()
            self._transaction_context = None
    
    async def close(self):
        """Close database connections"""
        if self.pool:
            await self.pool.close()
            logger.info("✅ PostgreSQL connection pool closed")
