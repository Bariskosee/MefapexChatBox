"""
📦 SQLite Manager (Development/Fallback)
SQLite implementation with improved connection handling and constraints
"""

import sqlite3
import asyncio
import logging
import json
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
from contextlib import asynccontextmanager
import threading
import queue

from .base import DatabaseInterface, DatabaseConfig, ConnectionStats

logger = logging.getLogger(__name__)

class SQLiteManager(DatabaseInterface):
    """
    Improved SQLite manager with better connection handling
    Suitable for development and small deployments
    """
    
    def __init__(self, config: DatabaseConfig):
        super().__init__(config)
        self.db_path = config.database
        self._connection_pool = queue.Queue(maxsize=5)
        self._lock = threading.Lock()
        self._executor = None
        
        # Ensure database directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
    
    async def initialize(self) -> bool:
        """Initialize SQLite database with optimizations"""
        try:
            # Create connection pool
            for _ in range(3):
                conn = self._create_connection()
                self._connection_pool.put(conn)
            
            # Create schema
            await self._create_schema()
            
            logger.info(f"✅ SQLite database initialized: {self.db_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize SQLite: {e}")
            return False
    
    def _create_connection(self) -> sqlite3.Connection:
        """Create optimized SQLite connection"""
        conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            timeout=30.0
        )
        
        # SQLite optimizations
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=10000")
        conn.execute("PRAGMA temp_store=memory")
        conn.execute("PRAGMA foreign_keys=ON")
        
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        return conn
    
    @asynccontextmanager
    async def _get_connection(self):
        """Get connection from pool with async wrapper"""
        loop = asyncio.get_event_loop()
        
        # Get connection from pool
        try:
            conn = self._connection_pool.get_nowait()
        except queue.Empty:
            conn = await loop.run_in_executor(None, self._create_connection)
        
        try:
            yield conn
        finally:
            # Return to pool if not full
            try:
                self._connection_pool.put_nowait(conn)
            except queue.Full:
                conn.close()
    
    async def _create_schema(self):
        """Create SQLite schema with constraints"""
        schema_sql = """
        -- Users table
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            full_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            login_attempts INTEGER DEFAULT 0,
            locked_until TIMESTAMP,
            CHECK (length(username) >= 3),
            CHECK (email LIKE '%@%.%')
        );
        
        -- Chat sessions
        CREATE TABLE IF NOT EXISTS chat_sessions (
            session_id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
            user_id TEXT NOT NULL,
            session_type TEXT DEFAULT 'chat',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            session_metadata TEXT DEFAULT '{}',
            message_count INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        );
        
        -- Chat messages
        CREATE TABLE IF NOT EXISTS chat_messages (
            message_id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
            session_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            message TEXT NOT NULL,
            response TEXT NOT NULL,
            source TEXT DEFAULT 'ai',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            response_time_ms INTEGER,
            message_metadata TEXT DEFAULT '{}',
            FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            CHECK (source IN ('ai', 'human', 'system')),
            CHECK (length(trim(message)) > 0)
        );
        
        -- System logs
        CREATE TABLE IF NOT EXISTS system_logs (
            log_id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
            log_level TEXT NOT NULL,
            logger_name TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            user_id TEXT,
            session_id TEXT,
            request_id TEXT,
            metadata TEXT DEFAULT '{}'
        );
        
        -- Indexes for performance
        CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        
        CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON chat_sessions(user_id);
        CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON chat_sessions(created_at);
        
        CREATE INDEX IF NOT EXISTS idx_messages_session_id ON chat_messages(session_id);
        CREATE INDEX IF NOT EXISTS idx_messages_user_id ON chat_messages(user_id);
        CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON chat_messages(timestamp);
        
        CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON system_logs(timestamp);
        
        -- Triggers for updated_at
        CREATE TRIGGER IF NOT EXISTS update_session_timestamp 
        AFTER UPDATE ON chat_sessions
        BEGIN
            UPDATE chat_sessions SET updated_at = CURRENT_TIMESTAMP 
            WHERE session_id = NEW.session_id;
        END;
        
        -- Trigger for message count
        CREATE TRIGGER IF NOT EXISTS update_message_count_insert
        AFTER INSERT ON chat_messages
        BEGIN
            UPDATE chat_sessions 
            SET message_count = message_count + 1 
            WHERE session_id = NEW.session_id;
        END;
        
        CREATE TRIGGER IF NOT EXISTS update_message_count_delete
        AFTER DELETE ON chat_messages
        BEGIN
            UPDATE chat_sessions 
            SET message_count = message_count - 1 
            WHERE session_id = OLD.session_id;
        END;
        """
        
        async with self._get_connection() as conn:
            await asyncio.get_event_loop().run_in_executor(None, conn.executescript, schema_sql)
            await asyncio.get_event_loop().run_in_executor(None, conn.commit)
    
    async def health_check(self) -> Dict[str, Any]:
        """SQLite health check"""
        start_time = datetime.utcnow()
        
        try:
            async with self._get_connection() as conn:
                # Basic connectivity
                await asyncio.get_event_loop().run_in_executor(
                    None, conn.execute, "SELECT 1"
                )
                
                # Database stats
                cursor = await asyncio.get_event_loop().run_in_executor(
                    None, conn.execute, """
                    SELECT 
                        (SELECT COUNT(*) FROM users) as user_count,
                        (SELECT COUNT(*) FROM chat_sessions) as session_count,
                        (SELECT COUNT(*) FROM chat_messages) as message_count
                """
                )
                stats = cursor.fetchone()
                
                response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                return {
                    "status": "healthy",
                    "database_type": "sqlite",
                    "database_path": self.db_path,
                    "response_time_ms": response_time,
                    "database_stats": dict(stats),
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def get_connection_stats(self) -> ConnectionStats:
        """Get SQLite connection statistics"""
        return ConnectionStats(
            active_connections=1,  # SQLite single connection
            idle_connections=self._connection_pool.qsize(),
            total_connections=1,
            pool_size=5,
            overflow_connections=0,
            connection_errors=0,
            avg_response_time_ms=0.0,
            last_health_check=datetime.utcnow()
        )
    
    # Session Management
    async def create_session(self, user_id: str, session_type: str = "chat") -> str:
        """Create new chat session"""
        session_id = str(uuid.uuid4())
        
        async with self._get_connection() as conn:
            await asyncio.get_event_loop().run_in_executor(
                None,
                conn.execute,
                "INSERT INTO chat_sessions (session_id, user_id, session_type) VALUES (?, ?, ?)",
                (session_id, user_id, session_type)
            )
            await asyncio.get_event_loop().run_in_executor(None, conn.commit)
        
        return session_id
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information"""
        async with self._get_connection() as conn:
            cursor = await asyncio.get_event_loop().run_in_executor(
                None,
                conn.execute,
                """SELECT session_id, user_id, session_type, created_at, 
                          updated_at, is_active, session_metadata, message_count
                   FROM chat_sessions WHERE session_id = ?""",
                (session_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    async def get_user_sessions(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get user's sessions"""
        async with self._get_connection() as conn:
            cursor = await asyncio.get_event_loop().run_in_executor(
                None,
                conn.execute,
                """SELECT session_id, session_type, created_at, updated_at, 
                          is_active, message_count
                   FROM chat_sessions 
                   WHERE user_id = ? AND is_active = 1
                   ORDER BY updated_at DESC LIMIT ?""",
                (user_id, limit)
            )
            return [dict(row) for row in cursor.fetchall()]
    
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
        
        async with self._get_connection() as conn:
            await asyncio.get_event_loop().run_in_executor(
                None,
                conn.execute,
                """INSERT INTO chat_messages 
                   (message_id, session_id, user_id, message, response, source)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (message_id, session_id, user_id, message, response, source)
            )
            await asyncio.get_event_loop().run_in_executor(None, conn.commit)
        
        return message_id
    
    async def get_session_messages(
        self, 
        session_id: str, 
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get session messages"""
        async with self._get_connection() as conn:
            cursor = await asyncio.get_event_loop().run_in_executor(
                None,
                conn.execute,
                """SELECT message_id, message, response, source, timestamp, response_time_ms
                   FROM chat_messages 
                   WHERE session_id = ?
                   ORDER BY timestamp ASC
                   LIMIT ? OFFSET ?""",
                (session_id, limit, offset)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    async def get_user_message_history(
        self, 
        user_id: str, 
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get user's message history"""
        async with self._get_connection() as conn:
            cursor = await asyncio.get_event_loop().run_in_executor(
                None,
                conn.execute,
                """SELECT cm.message_id, cm.session_id, cm.message, cm.response, 
                          cm.source, cm.timestamp, cs.session_type
                   FROM chat_messages cm
                   JOIN chat_sessions cs ON cm.session_id = cs.session_id
                   WHERE cm.user_id = ?
                   ORDER BY cm.timestamp DESC LIMIT ?""",
                (user_id, limit)
            )
            return [dict(row) for row in cursor.fetchall()]
    
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
        
        async with self._get_connection() as conn:
            await asyncio.get_event_loop().run_in_executor(
                None,
                conn.execute,
                """INSERT INTO users (user_id, username, email, hashed_password, full_name)
                   VALUES (?, ?, ?, ?, ?)""",
                (user_id, username, email, hashed_password, full_name)
            )
            await asyncio.get_event_loop().run_in_executor(None, conn.commit)
        
        return user_id
    
    async def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username"""
        async with self._get_connection() as conn:
            cursor = await asyncio.get_event_loop().run_in_executor(
                None,
                conn.execute,
                """SELECT user_id, username, email, hashed_password, full_name, 
                          created_at, last_login, is_active, login_attempts, locked_until
                   FROM users WHERE username = ?""",
                (username,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    async def update_user_last_login(self, user_id: str) -> bool:
        """Update user's last login"""
        async with self._get_connection() as conn:
            cursor = await asyncio.get_event_loop().run_in_executor(
                None,
                conn.execute,
                """UPDATE users 
                   SET last_login = CURRENT_TIMESTAMP, login_attempts = 0
                   WHERE user_id = ?""",
                (user_id,)
            )
            await asyncio.get_event_loop().run_in_executor(None, conn.commit)
            return cursor.rowcount == 1
    
    # Analytics & Reporting
    async def get_analytics_data(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get analytics data"""
        async with self._get_connection() as conn:
            # User stats
            cursor = await asyncio.get_event_loop().run_in_executor(
                None,
                conn.execute,
                """SELECT 
                    COUNT(DISTINCT user_id) as active_users,
                    COUNT(*) as total_messages,
                    AVG(response_time_ms) as avg_response_time
                   FROM chat_messages 
                   WHERE timestamp BETWEEN ? AND ?""",
                (start_date.isoformat(), end_date.isoformat())
            )
            stats = cursor.fetchone()
            
            return {
                "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
                "summary": dict(stats) if stats else {}
            }
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        async with self._get_connection() as conn:
            cursor = await asyncio.get_event_loop().run_in_executor(
                None,
                conn.execute,
                """SELECT 
                    (SELECT COUNT(*) FROM users) as total_users,
                    (SELECT COUNT(*) FROM chat_sessions) as total_sessions,
                    (SELECT COUNT(*) FROM chat_messages) as total_messages"""
            )
            stats = cursor.fetchone()
            
            # Get file size
            file_size = Path(self.db_path).stat().st_size if Path(self.db_path).exists() else 0
            
            result = dict(stats) if stats else {}
            result["database_size_bytes"] = file_size
            return result
    
    # Backup & Maintenance
    async def create_backup(self, backup_path: str) -> bool:
        """Create SQLite backup"""
        try:
            import shutil
            backup_file = f"{backup_path}/mefapex_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.db"
            await asyncio.get_event_loop().run_in_executor(
                None, shutil.copy2, self.db_path, backup_file
            )
            logger.info(f"✅ SQLite backup created: {backup_file}")
            return True
        except Exception as e:
            logger.error(f"❌ SQLite backup failed: {e}")
            return False
    
    async def restore_backup(self, backup_path: str) -> bool:
        """Restore SQLite backup"""
        try:
            import shutil
            await asyncio.get_event_loop().run_in_executor(
                None, shutil.copy2, backup_path, self.db_path
            )
            logger.info(f"✅ SQLite restored from: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"❌ SQLite restore failed: {e}")
            return False
    
    async def optimize_database(self) -> Dict[str, Any]:
        """Optimize SQLite database"""
        async with self._get_connection() as conn:
            await asyncio.get_event_loop().run_in_executor(None, conn.execute, "VACUUM")
            await asyncio.get_event_loop().run_in_executor(None, conn.execute, "ANALYZE")
            await asyncio.get_event_loop().run_in_executor(None, conn.commit)
            
            file_size = Path(self.db_path).stat().st_size
            return {
                "vacuum": "completed",
                "analyze": "completed",
                "database_size_bytes": file_size
            }
    
    async def validate_data_integrity(self) -> Dict[str, Any]:
        """Validate SQLite data integrity"""
        async with self._get_connection() as conn:
            cursor = await asyncio.get_event_loop().run_in_executor(
                None, conn.execute, "PRAGMA integrity_check"
            )
            integrity_result = cursor.fetchone()[0]
            
            return {
                "validation_passed": integrity_result == "ok",
                "integrity_check": integrity_result
            }
    
    async def cleanup_old_data(self, days_to_keep: int = 90) -> Dict[str, Any]:
        """Clean up old SQLite data"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        async with self._get_connection() as conn:
            cursor = await asyncio.get_event_loop().run_in_executor(
                None,
                conn.execute,
                "DELETE FROM system_logs WHERE timestamp < ?",
                (cutoff_date.isoformat(),)
            )
            deleted_logs = cursor.rowcount
            await asyncio.get_event_loop().run_in_executor(None, conn.commit)
            
            return {
                "deleted_logs": deleted_logs,
                "cleanup_date": cutoff_date.isoformat()
            }
    
    # Transaction Management
    async def begin_transaction(self):
        """Begin SQLite transaction"""
        # SQLite auto-commits, so we'd need to implement this differently
        pass
    
    async def commit_transaction(self):
        """Commit SQLite transaction"""
        pass
    
    async def rollback_transaction(self):
        """Rollback SQLite transaction"""
        pass
    
    async def close(self):
        """Close SQLite connections"""
        while not self._connection_pool.empty():
            try:
                conn = self._connection_pool.get_nowait()
                conn.close()
            except queue.Empty:
                break
        logger.info("✅ SQLite connections closed")
