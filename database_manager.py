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
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    message_count INTEGER DEFAULT 0
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
    
    def get_current_session(self, user_id: str) -> Optional[str]:
        """Get current active session without creating a new one"""
        with self.pool.get_connection() as conn:
            cur = conn.cursor()
            
            # Get the most recent session that has recent activity (last 30 minutes)
            cur.execute("""
                SELECT s.session_id 
                FROM chat_sessions s
                LEFT JOIN chat_messages m ON s.session_id = m.session_id
                WHERE s.user_id = ? 
                AND (m.timestamp IS NULL OR m.timestamp >= datetime('now', '-30 minutes'))
                ORDER BY s.created_at DESC 
                LIMIT 1
            """, (user_id,))
            
            row = cur.fetchone()
            return row[0] if row else None
    
    def get_or_create_session(self, user_id: str, force_new: bool = False) -> str:
        """Get existing session or create new one with enhanced session management"""
        with self.pool.get_connection() as conn:
            cur = conn.cursor()
            
            if not force_new:
                # Use the get_current_session method for consistency
                existing_session = self.get_current_session(user_id)
                if existing_session:
                    logger.debug(f"Using existing session {existing_session} for user {user_id}")
                    return existing_session
            
            # Create new session with enhanced logging
            import uuid
            session_id = str(uuid.uuid4())
            
            # Before creating, check if we need to clean up old sessions
            # Limit to 15 sessions per user (keep most recent 15)
            cur.execute("""
                SELECT COUNT(*) FROM chat_sessions WHERE user_id = ?
            """, (user_id,))
            
            session_count = cur.fetchone()[0]
            
            if session_count >= 15:
                # Delete oldest sessions and their messages to maintain limit
                cur.execute("""
                    DELETE FROM chat_messages WHERE session_id IN (
                        SELECT session_id FROM chat_sessions 
                        WHERE user_id = ? 
                        ORDER BY created_at ASC 
                        LIMIT ?
                    )
                """, (user_id, session_count - 14))  # Keep 14, add 1 new = 15 total
                
                cur.execute("""
                    DELETE FROM chat_sessions WHERE session_id IN (
                        SELECT session_id FROM chat_sessions 
                        WHERE user_id = ? 
                        ORDER BY created_at ASC 
                        LIMIT ?
                    )
                """, (user_id, session_count - 14))
                
                logger.debug(f"Cleaned up old sessions for user {user_id}, keeping limit at 15")
            
            # Create the new session
            try:
                cur.execute(
                    "INSERT INTO chat_sessions (session_id, user_id) VALUES (?, ?)", 
                    (session_id, user_id)
                )
                conn.commit()
                logger.info(f"✅ Created new session {session_id} for user {user_id}")
                return session_id
            except Exception as e:
                logger.error(f"Failed to create session for user {user_id}: {e}")
                conn.rollback()
                raise
    
    def add_message(self, session_id: str, user_id: str, user_message: str, bot_response: str, source: str):
        """Add message with enhanced error handling and validation"""
        try:
            # Validate inputs
            if not session_id or not user_message or not bot_response:
                raise ValueError("session_id, user_message, and bot_response are required")
            
            with self.pool.get_connection() as conn:
                # Verify session exists
                cur = conn.cursor()
                cur.execute("SELECT 1 FROM chat_sessions WHERE session_id = ?", (session_id,))
                if not cur.fetchone():
                    logger.warning(f"Session {session_id} not found, creating it for user {user_id}")
                    # Auto-create session if it doesn't exist
                    if user_id:
                        cur.execute(
                            "INSERT OR IGNORE INTO chat_sessions (session_id, user_id) VALUES (?, ?)", 
                            (session_id, user_id)
                        )
                
                # Insert message
                conn.execute(
                    """INSERT INTO chat_messages 
                       (session_id, user_id, user_message, bot_response, source) 
                       VALUES (?, ?, ?, ?, ?)""",
                    (session_id, user_id, user_message, bot_response, source)
                )
                conn.commit()
                logger.debug(f"Message added to session {session_id}")
                
        except Exception as e:
            logger.error(f"Failed to add message to session {session_id}: {e}")
            raise
    
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
    
    def get_chat_sessions_with_history(self, user_id: str, limit: int = 15) -> List[Dict]:
        """Get chat sessions with their messages (session-based history)"""
        with self.pool.get_connection() as conn:
            cur = conn.cursor()
            
            # Get sessions ordered by most recent activity
            cur.execute("""
                SELECT DISTINCT s.session_id, s.created_at,
                       COUNT(m.id) as message_count,
                       MAX(m.timestamp) as last_message_time,
                       MIN(m.timestamp) as first_message_time
                FROM chat_sessions s
                LEFT JOIN chat_messages m ON s.session_id = m.session_id
                WHERE s.user_id = ?
                GROUP BY s.session_id, s.created_at
                HAVING message_count > 0
                ORDER BY COALESCE(last_message_time, s.created_at) DESC
                LIMIT ?
            """, (user_id, limit))
            
            sessions = cur.fetchall()
            result = []
            
            for session in sessions:
                session_id, created_at, message_count, last_message_time, first_message_time = session
                
                # Get messages for this session
                cur.execute("""
                    SELECT user_message, bot_response, source, timestamp
                    FROM chat_messages
                    WHERE session_id = ?
                    ORDER BY timestamp ASC
                """, (session_id,))
                
                messages = [
                    {
                        "user_message": row[0],
                        "bot_response": row[1],
                        "source": row[2],
                        "timestamp": row[3]
                    }
                    for row in cur.fetchall()
                ]
                
                # Create session summary with first message as preview
                session_summary = {
                    "session_id": session_id,
                    "created_at": created_at,
                    "message_count": message_count,
                    "last_message_time": last_message_time,
                    "first_message_time": first_message_time,
                    "messages": messages,
                    "preview": messages[0]["user_message"] if messages else "Empty session"
                }
                
                result.append(session_summary)
            
            return result

    def get_chat_messages(self, session_id: str) -> List[Dict]:
        """Get all messages for a specific session with optimization"""
        try:
            with self.pool.get_connection() as conn:
                cur = conn.cursor()
                
                # Optimized query with LIMIT to prevent large result sets
                cur.execute("""
                    SELECT user_message, bot_response, source, timestamp
                    FROM chat_messages
                    WHERE session_id = ?
                    ORDER BY timestamp ASC
                    LIMIT 1000
                """, (session_id,))
                
                return [
                    {
                        "user_message": row[0],
                        "bot_response": row[1],
                        "source": row[2],
                        "timestamp": row[3]
                    }
                    for row in cur.fetchall()
                ]
                
        except Exception as e:
            logger.error(f"Error getting chat messages: {e}")
            return [] 

    def save_chat_session_emergency(self, user_id: str, session_id: str):
        """Emergency save for session during page unload"""
        try:
            with self.pool.get_connection() as conn:
                cur = conn.cursor()
                
                # Check if session exists first
                cur.execute("SELECT 1 FROM chat_sessions WHERE session_id = ?", (session_id,))
                if not cur.fetchone():
                    logger.warning(f"Session {session_id} not found during emergency save")
                    return
                
                # Update session as saved
                cur.execute("""
                    UPDATE chat_sessions 
                    SET updated_at = ?, is_active = 0
                    WHERE session_id = ? AND user_id = ?
                """, (datetime.now().isoformat(), session_id, user_id))
                
                conn.commit()
                logger.info(f"🚨 Emergency session save completed for {session_id[:8]}...")
                
        except Exception as e:
            logger.error(f"Emergency session save failed: {e}")
    
    def start_new_session(self, user_id: str) -> str:
        """Force creation of a new session for the user"""
        return self.get_or_create_session(user_id, force_new=True)
    
    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """Get information about a specific session"""
        with self.pool.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT s.session_id, s.user_id, s.created_at,
                       COUNT(m.id) as message_count,
                       MIN(m.timestamp) as first_message_time,
                       MAX(m.timestamp) as last_message_time
                FROM chat_sessions s
                LEFT JOIN chat_messages m ON s.session_id = m.session_id
                WHERE s.session_id = ?
                GROUP BY s.session_id, s.user_id, s.created_at
            """, (session_id,))
            
            row = cur.fetchone()
            if row:
                return {
                    "session_id": row[0],
                    "user_id": row[1],
                    "created_at": row[2],
                    "message_count": row[3],
                    "first_message_time": row[4],
                    "last_message_time": row[5]
                }
            return None
    
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
    def save_chat_session(self, user_id: str, session_id: str, started_at: str, message_count: int):
        """Save a chat session record with optimization"""
        try:
            with self.pool.get_connection() as conn:
                cur = conn.cursor()
                
                # Use pool connection instead of creating new one
                cur.execute("""
                    INSERT OR REPLACE INTO chat_sessions 
                    (session_id, user_id, created_at, updated_at, message_count, is_active)
                    VALUES (?, ?, ?, ?, ?, 0)
                """, (session_id, user_id, started_at, datetime.now().isoformat(), message_count))
                
                conn.commit()
                logger.info(f"💾 Session record saved: {session_id} ({message_count} messages)")
                
        except Exception as e:
            logger.error(f"Failed to save session record: {e}")
            raise
    
    def trim_user_sessions(self, user_id: str, max_sessions: int = 15):
        """Keep only the most recent max_sessions for a user with optimization"""
        try:
            with self.pool.get_connection() as conn:
                cur = conn.cursor()
                
                # Use connection pool and optimize query
                cur.execute("""
                    SELECT session_id FROM chat_sessions 
                    WHERE user_id = ? 
                    ORDER BY created_at DESC
                    LIMIT -1 OFFSET ?
                """, (user_id, max_sessions))
                
                old_sessions = cur.fetchall()
                
                if old_sessions:
                    old_session_ids = [row[0] for row in old_sessions]
                    
                    # Use batch delete for better performance
                    placeholders = ','.join(['?' for _ in old_session_ids])
                    
                    # Delete associated messages first (referential integrity)
                    cur.execute(f"""
                        DELETE FROM chat_messages 
                        WHERE session_id IN ({placeholders})
                    """, old_session_ids)
                    
                    # Delete old session records
                    cur.execute(f"""
                        DELETE FROM chat_sessions 
                        WHERE session_id IN ({placeholders})
                    """, old_session_ids)
                    
                    conn.commit()
                    
                    logger.info(f"🗑️ Trimmed {len(old_session_ids)} old sessions for user {user_id}")
                
        except Exception as e:
            logger.error(f"Failed to trim user sessions: {e}")

# Global database manager instance
db_manager = None

def init_database_manager():
    """Initialize global database manager"""
    global db_manager
    db_manager = DatabaseManager()
    return db_manager

def get_database_manager() -> DatabaseManager:
    """Get global database manager instance"""
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager()
    return db_manager
