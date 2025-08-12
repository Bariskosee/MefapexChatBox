"""
🚀 MEFAPEX PostgreSQL Database Manager
=====================================
Production-ready PostgreSQL database manager for MEFAPEX Chat System
"""

import os
import uuid
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool
import time

logger = logging.getLogger(__name__)

class PostgreSQLDatabaseManager:
    """PostgreSQL Database Manager for MEFAPEX Chat System"""
    
    def __init__(self):
        self.connection_pool = None
        self.host = os.getenv("POSTGRES_HOST", "localhost")
        self.port = int(os.getenv("POSTGRES_PORT", 5432))
        self.user = os.getenv("POSTGRES_USER", "mefapex")
        self.password = os.getenv("POSTGRES_PASSWORD")
        self.database = os.getenv("POSTGRES_DB", "mefapex_chatbot")
        
        if not self.password:
            raise ValueError("POSTGRES_PASSWORD environment variable is required")
        
        self._init_connection_pool()
        self._ensure_tables_exist()
        logger.info(f"📊 PostgreSQL Database Manager initialized: {self.host}:{self.port}/{self.database}")

    def _init_connection_pool(self):
        """Initialize PostgreSQL connection pool"""
        try:
            self.connection_pool = ThreadedConnectionPool(
                minconn=1,
                maxconn=20,
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                cursor_factory=RealDictCursor
            )
            logger.info("✅ PostgreSQL connection pool established")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize PostgreSQL connection pool: {e}")
            raise

    def _get_connection(self):
        """Get connection from pool"""
        return self.connection_pool.getconn()

    def _put_connection(self, conn):
        """Return connection to pool"""
        self.connection_pool.putconn(conn)

    def _ensure_tables_exist(self):
        """Create necessary tables if they don't exist"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Create users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    user_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
                    username VARCHAR(255) UNIQUE NOT NULL,
                    email VARCHAR(255) UNIQUE,
                    hashed_password VARCHAR(255) NOT NULL,
                    full_name VARCHAR(255),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP WITH TIME ZONE,
                    is_active BOOLEAN DEFAULT TRUE,
                    failed_login_attempts INTEGER DEFAULT 0
                )
            ''')
            
            # Create chat_sessions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id SERIAL PRIMARY KEY,
                    session_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
                    user_id VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    message_count INTEGER DEFAULT 0
                )
            ''')
            
            # Create chat_messages table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id SERIAL PRIMARY KEY,
                    session_id VARCHAR(255) NOT NULL,
                    user_id VARCHAR(255) NOT NULL,
                    user_message TEXT NOT NULL,
                    bot_response TEXT NOT NULL,
                    source VARCHAR(50) DEFAULT 'unknown',
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    metadata JSONB
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_chat_sessions_session_id ON chat_sessions(session_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages(session_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_chat_messages_user_id ON chat_messages(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_chat_messages_timestamp ON chat_messages(timestamp)')
            
            conn.commit()
            logger.info("✅ PostgreSQL tables and indexes created/verified")
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"❌ Failed to create tables: {e}")
            raise
        finally:
            if conn:
                self._put_connection(conn)

    def authenticate_user(self, username: str) -> Optional[Dict]:
        """Authenticate user and return user data"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT id, user_id, username, hashed_password, email, is_active, last_login FROM users WHERE username = %s",
                (username,)
            )
            result = cursor.fetchone()
            
            if result:
                return {
                    "id": result["id"],
                    "user_id": str(result["user_id"]),
                    "username": result["username"],
                    "password_hash": result["hashed_password"],
                    "hashed_password": result["hashed_password"],
                    "email": result["email"],
                    "is_active": result["is_active"],
                    "last_login": result["last_login"]
                }
            return None
            
        except Exception as e:
            logger.error(f"❌ Database authentication error: {e}")
            return None
        finally:
            if conn:
                self._put_connection(conn)

    def update_last_login(self, username: str):
        """Update user's last login timestamp"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                "UPDATE users SET last_login = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE username = %s",
                (username,)
            )
            conn.commit()
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"❌ Failed to update last login: {e}")
        finally:
            if conn:
                self._put_connection(conn)

    def get_or_create_session(self, user_id: str, force_new: bool = False) -> str:
        """Get existing session or create new one"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            if not force_new:
                # Try to get existing active session
                cursor.execute(
                    "SELECT session_id FROM chat_sessions WHERE user_id = %s AND is_active = TRUE ORDER BY created_at DESC LIMIT 1",
                    (user_id,)
                )
                result = cursor.fetchone()
                if result:
                    return str(result["session_id"])
            
            # Create new session
            session_id = str(uuid.uuid4())
            cursor.execute(
                "INSERT INTO chat_sessions (session_id, user_id) VALUES (%s, %s)",
                (session_id, user_id)
            )
            conn.commit()
            
            logger.info(f"📝 Created new session: {session_id} for user: {user_id}")
            return session_id
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"❌ Session creation error: {e}")
            # Return fallback session ID
            return f"fallback_{user_id}_{int(time.time())}"
        finally:
            if conn:
                self._put_connection(conn)

    def add_message(self, session_id: str, user_id: str, user_message: str, 
                   bot_response: str, source: str = "unknown"):
        """Add a chat message to the database"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                """INSERT INTO chat_messages 
                   (session_id, user_id, user_message, bot_response, source) 
                   VALUES (%s, %s, %s, %s, %s)""",
                (session_id, user_id, user_message, bot_response, source)
            )
            
            # Update session message count
            cursor.execute(
                "UPDATE chat_sessions SET message_count = message_count + 1, updated_at = CURRENT_TIMESTAMP WHERE session_id = %s",
                (session_id,)
            )
            
            conn.commit()
            logger.debug(f"💬 Message saved: {len(user_message)} chars -> {len(bot_response)} chars")
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"❌ Failed to save message: {e}")
            raise
        finally:
            if conn:
                self._put_connection(conn)

    def get_chat_history(self, user_id: str, limit: int = 20) -> List[Dict]:
        """Get chat history for user"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                """SELECT user_message, bot_response, source, timestamp, created_at 
                   FROM chat_messages 
                   WHERE user_id = %s 
                   ORDER BY timestamp DESC 
                   LIMIT %s""",
                (user_id, limit)
            )
            
            results = cursor.fetchall()
            return [
                {
                    "user_message": row["user_message"],
                    "bot_response": row["bot_response"],
                    "source": row["source"],
                    "timestamp": row["timestamp"],
                    "created_at": row["created_at"]
                }
                for row in results
            ]
            
        except Exception as e:
            logger.error(f"❌ Failed to get chat history: {e}")
            return []
        finally:
            if conn:
                self._put_connection(conn)

    def get_user_sessions(self, user_id: str) -> List[Dict]:
        """Get user's chat sessions"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Get sessions with message counts
            cursor.execute(
                """SELECT s.session_id, s.created_at, s.message_count, s.updated_at,
                          (SELECT user_message FROM chat_messages 
                           WHERE session_id = s.session_id 
                           ORDER BY timestamp ASC LIMIT 1) as first_message
                   FROM chat_sessions s
                   WHERE s.user_id = %s AND s.is_active = TRUE
                   ORDER BY s.created_at DESC""",
                (user_id,)
            )
            
            results = cursor.fetchall()
            sessions = []
            
            for row in results:
                preview = row["first_message"] if row["first_message"] else "Boş sohbet"
                
                sessions.append({
                    "sessionId": str(row["session_id"]),
                    "session_id": str(row["session_id"]),
                    "created_at": row["created_at"],
                    "startedAt": row["created_at"],
                    "messageCount": row["message_count"] or 0,
                    "message_count": row["message_count"] or 0,
                    "lastMessageTime": row["updated_at"],
                    "preview": preview[:50] + "..." if len(preview) > 50 else preview
                })
            
            return sessions
            
        except Exception as e:
            logger.error(f"❌ Failed to get user sessions: {e}")
            return []
        finally:
            if conn:
                self._put_connection(conn)

    def get_session_messages(self, session_id: str) -> List[Dict]:
        """Get all messages from a specific session"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                """SELECT user_message, bot_response, source, timestamp 
                   FROM chat_messages 
                   WHERE session_id = %s 
                   ORDER BY timestamp ASC""",
                (session_id,)
            )
            
            results = cursor.fetchall()
            messages = []
            
            for row in results:
                messages.append({
                    "user_message": row["user_message"],
                    "bot_response": row["bot_response"],
                    "source": row["source"],
                    "timestamp": row["timestamp"]
                })
            
            return messages
            
        except Exception as e:
            logger.error(f"❌ Failed to get session messages: {e}")
            return []
        finally:
            if conn:
                self._put_connection(conn)

    def clear_chat_history(self, user_id: str):
        """Clear all chat history for user"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM chat_messages WHERE user_id = %s", (user_id,))
            cursor.execute("DELETE FROM chat_sessions WHERE user_id = %s", (user_id,))
            conn.commit()
            
            logger.info(f"🗑️ Cleared chat history for user: {user_id}")
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"❌ Failed to clear chat history: {e}")
            raise
        finally:
            if conn:
                self._put_connection(conn)

    def get_stats(self) -> Dict:
        """Get database statistics"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Get counts
            cursor.execute("SELECT COUNT(*) as count FROM users")
            user_count = cursor.fetchone()["count"]
            
            cursor.execute("SELECT COUNT(*) as count FROM chat_sessions WHERE is_active = TRUE")
            session_count = cursor.fetchone()["count"]
            
            cursor.execute("SELECT COUNT(*) as count FROM chat_messages")
            message_count = cursor.fetchone()["count"]
            
            return {
                "users": user_count,
                "sessions": session_count,
                "messages": message_count,
                "database_type": "PostgreSQL",
                "database_host": f"{self.host}:{self.port}",
                "database_name": self.database
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get stats: {e}")
            return {"error": str(e)}
        finally:
            if conn:
                self._put_connection(conn)

    def close(self):
        """Close database connection pool"""
        if self.connection_pool:
            self.connection_pool.closeall()
            logger.info("📊 PostgreSQL connection pool closed")

    def health_check(self) -> Dict:
        """Check database health"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            
            return {
                "status": "healthy",
                "database": "PostgreSQL",
                "connection": "active",
                "test_query": "passed"
            }
            
        except Exception as e:
            logger.error(f"❌ Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "database": "PostgreSQL",
                "connection": "failed",
                "error": str(e)
            }
        finally:
            if conn:
                self._put_connection(conn)

# Global instance
db_manager = None

def get_database_manager() -> PostgreSQLDatabaseManager:
    """Get or create PostgreSQL database manager instance"""
    global db_manager
    if db_manager is None:
        db_manager = PostgreSQLDatabaseManager()
    return db_manager

# Initialize global instance
db_manager = get_database_manager()
