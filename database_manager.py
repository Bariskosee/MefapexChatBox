import sqlite3
import threading
import logging
from datetime import datetime
from typing import List, Dict, Optional
from contextlib import contextmanager
import queue
import time

logger = logging.getLogger(__name__)

class DatabaseConnectionPool:
    """
    Thread-safe SQLite connection pool for better performance
    """
    
    def __init__(self, db_path: str, max_connections: int = 10):
        self.db_path = db_path
        self.max_connections = max_connections
        self._pool = queue.Queue(maxsize=max_connections)
        self._active_connections = 0
        self._lock = threading.Lock()
        
        # Initialize pool with some connections
        for _ in range(min(3, max_connections)):
            self._create_connection()
    
    def _create_connection(self) -> sqlite3.Connection:
        """Create a new database connection with optimizations"""
        conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,  # Allow sharing between threads
            timeout=30.0  # 30 second timeout
        )
        
        # SQLite optimizations
        conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
        conn.execute("PRAGMA synchronous=NORMAL")  # Balance safety and speed
        conn.execute("PRAGMA cache_size=10000")  # Larger cache
        conn.execute("PRAGMA temp_store=memory")  # Use memory for temp tables
        conn.execute("PRAGMA mmap_size=268435456")  # 256MB memory-mapped I/O
        
        return conn
    
    @contextmanager
    def get_connection(self):
        """Get a connection from pool with automatic cleanup"""
        conn = None
        try:
            # Try to get from pool
            try:
                conn = self._pool.get_nowait()
            except queue.Empty:
                # Create new connection if pool is empty and under limit
                with self._lock:
                    if self._active_connections < self.max_connections:
                        conn = self._create_connection()
                        self._active_connections += 1
                    else:
                        # Wait for connection to become available
                        conn = self._pool.get(timeout=10)
            
            yield conn
            
        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
            raise e
        finally:
            if conn:
                try:
                    # Return connection to pool
                    self._pool.put_nowait(conn)
                except queue.Full:
                    # Pool is full, close connection
                    conn.close()
                    with self._lock:
                        self._active_connections -= 1

class DatabaseManager:
    def __init__(self, db_path="mefapex.db"):
        self.db_path = db_path
        self.pool = DatabaseConnectionPool(db_path, max_connections=10)
        self.init_database()
    
    
    def init_database(self):
        """Initialize database with optimized schema and indexes"""
        with self.pool.get_connection() as conn:
            # Create tables
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    user_id TEXT UNIQUE NOT NULL,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    hashed_password TEXT NOT NULL,
                    full_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id INTEGER PRIMARY KEY,
                    session_id TEXT UNIQUE NOT NULL,
                    user_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_message TEXT,
                    bot_response TEXT,
                    source TEXT
                )
            """)
            
            # Create indexes for better performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON chat_sessions(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_user_id ON chat_messages(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_session_id ON chat_messages(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON chat_messages(timestamp)")
            
            conn.commit()
            logger.info("✅ Database initialized with optimizations")
    
    def get_or_create_session(self, user_id: str) -> str:
        """Get existing session or create new one with optimized query"""
        with self.pool.get_connection() as conn:
            cur = conn.cursor()
            
            # Try to get existing session (most recent)
            cur.execute("""
                SELECT session_id FROM chat_sessions 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT 1
            """, (user_id,))
            
            row = cur.fetchone()
            if row:
                return row[0]
            
            # Create new session
            import uuid
            session_id = str(uuid.uuid4())
            cur.execute(
                "INSERT INTO chat_sessions (session_id, user_id) VALUES (?, ?)", 
                (session_id, user_id)
            )
            conn.commit()
            return session_id
    
    def add_message(self, session_id: str, user_id: str, user_message: str, bot_response: str, source: str):
        """Add message with optimized insert"""
        with self.pool.get_connection() as conn:
            conn.execute(
                """INSERT INTO chat_messages 
                   (session_id, user_id, user_message, bot_response, source) 
                   VALUES (?, ?, ?, ?, ?)""",
                (session_id, user_id, user_message, bot_response, source)
            )
            conn.commit()
    
    def get_chat_history(self, user_id: str, limit: int = 20) -> List[Dict]:
        """Get chat history with optimized query and pagination"""
        with self.pool.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT user_message, bot_response, source, timestamp 
                FROM chat_messages 
                WHERE user_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (user_id, limit))
            
            rows = cur.fetchall()
            
            # Return in chronological order with better structure
            return [
                {
                    "user_message": row[0],
                    "bot_response": row[1],
                    "source": row[2],
                    "timestamp": row[3]
                }
                for row in reversed(rows)
            ]
    
    def get_chat_sessions(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Get recent chat sessions for user"""
        with self.pool.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT s.session_id, s.created_at, COUNT(m.id) as message_count,
                       MAX(m.timestamp) as last_message_time
                FROM chat_sessions s
                LEFT JOIN chat_messages m ON s.session_id = m.session_id
                WHERE s.user_id = ?
                GROUP BY s.session_id, s.created_at
                ORDER BY last_message_time DESC
                LIMIT ?
            """, (user_id, limit))
            
            rows = cur.fetchall()
            return [
                {
                    "session_id": row[0],
                    "created_at": row[1],
                    "message_count": row[2],
                    "last_message_time": row[3]
                }
                for row in rows
            ]
    
    def clear_chat_history(self, user_id: str):
        """Clear chat history with optimized delete"""
        with self.pool.get_connection() as conn:
            # Delete in order to maintain referential integrity
            conn.execute("DELETE FROM chat_messages WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM chat_sessions WHERE user_id = ?", (user_id,))
            conn.commit()
    
    def get_stats(self) -> Dict:
        """Get database statistics"""
        with self.pool.get_connection() as conn:
            cur = conn.cursor()
            
            # Get table sizes
            cur.execute("SELECT COUNT(*) FROM users")
            user_count = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM chat_sessions")
            session_count = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM chat_messages")
            message_count = cur.fetchone()[0]
            
            # Get recent activity
            cur.execute("""
                SELECT COUNT(*) FROM chat_messages 
                WHERE timestamp >= datetime('now', '-24 hours')
            """)
            messages_24h = cur.fetchone()[0]
            
            return {
                "users": user_count,
                "sessions": session_count,
                "messages": message_count,
                "messages_24h": messages_24h,
                "pool_active_connections": self.pool._active_connections,
                "pool_max_connections": self.pool.max_connections
            } 