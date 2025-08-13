"""
🚀 MEFAPEX PostgreSQL Database Manager
PostgreSQL-based database manager for production use
"""

import os
import uuid
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from database.interface import DatabaseInterface
import asyncpg
import psycopg2
from psycopg2.extras import RealDictCursor
import bcrypt

logger = logging.getLogger(__name__)

class PostgreSQLManager(DatabaseInterface):
    """PostgreSQL Database Manager for MEFAPEX Chat System"""
    
    def __init__(self):
        # Database configuration from environment
        self.host = os.getenv("POSTGRES_HOST", "localhost")
        self.port = int(os.getenv("POSTGRES_PORT", "5432"))
        self.database = os.getenv("POSTGRES_DB", "mefapex_chatbot")
        self.user = os.getenv("POSTGRES_USER", "mefapex")
        self.password = os.getenv("POSTGRES_PASSWORD", "mefapex")
        
        # Connection pool
        self.pool = None
        self.sync_connection = None
        
        logger.info(f"📊 PostgreSQL Manager initialized for {self.host}:{self.port}/{self.database}")

    async def initialize(self):
        """Initialize async connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                min_size=5,
                max_size=20,
                command_timeout=60
            )
            logger.info("✅ PostgreSQL async pool created")
            
            # Initialize sync connection for synchronous operations
            self._init_sync_connection()
            
            # Initialize database schema
            await self._init_schema()
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize PostgreSQL: {e}")
            raise

    def _init_sync_connection(self):
        """Initialize synchronous connection for simple operations"""
        try:
            self.sync_connection = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                cursor_factory=RealDictCursor
            )
            self.sync_connection.autocommit = True
            logger.info("✅ PostgreSQL sync connection established")
            
        except Exception as e:
            logger.error(f"❌ Failed to create sync connection: {e}")
            raise

    async def _init_schema(self):
        """Initialize database schema"""
        try:
            async with self.pool.acquire() as conn:
                # Enable extensions
                await conn.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")
                await conn.execute("CREATE EXTENSION IF NOT EXISTS \"pg_trgm\"")
                
                # Create users table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        user_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
                        username VARCHAR(255) UNIQUE NOT NULL,
                        email VARCHAR(255) UNIQUE NOT NULL,
                        hashed_password VARCHAR(255) NOT NULL,
                        full_name VARCHAR(255),
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        last_login TIMESTAMP WITH TIME ZONE,
                        is_active BOOLEAN DEFAULT TRUE,
                        failed_login_attempts INTEGER DEFAULT 0
                    )
                """)
                
                # Create chat_sessions table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS chat_sessions (
                        id SERIAL PRIMARY KEY,
                        session_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
                        user_id UUID NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT TRUE,
                        message_count INTEGER DEFAULT 0,
                        last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                    )
                """)
                
                # Create chat_messages table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS chat_messages (
                        id BIGSERIAL PRIMARY KEY,
                        session_id UUID NOT NULL,
                        user_id UUID NOT NULL,
                        timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        user_message TEXT,
                        bot_response TEXT,
                        source VARCHAR(100),
                        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                        FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE
                    )
                """)
                
                # Create indexes
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id)")
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON chat_sessions(user_id)")
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_session_id ON chat_sessions(session_id)")
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_user_id ON chat_messages(user_id)")
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_session_id ON chat_messages(session_id)")
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON chat_messages(timestamp)")
                
                logger.info("✅ Database schema initialized")
                
                # Create demo user if it doesn't exist
                await self._create_demo_user_if_not_exists(conn)
                
        except Exception as e:
            logger.error(f"❌ Schema initialization failed: {e}")
            raise

    async def _create_demo_user_if_not_exists(self, conn):
        """Create demo user if it doesn't exist"""
        try:
            # Check if demo user exists
            result = await conn.fetchrow("SELECT username FROM users WHERE username = $1", "demo")
            
            if not result:
                # Create demo user
                demo_password = "1234"
                hashed_password = bcrypt.hashpw(demo_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                demo_user_id = str(uuid.uuid4())
                
                await conn.execute("""
                    INSERT INTO users (user_id, username, email, hashed_password, full_name, is_active)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """, demo_user_id, "demo", "demo@mefapex.com", hashed_password, "Demo User", True)
                
                logger.info(f"✅ Demo user created with ID: {demo_user_id}")
            else:
                logger.info("✅ Demo user already exists")
                
        except Exception as e:
            logger.error(f"❌ Failed to create demo user: {e}")

    def authenticate_user(self, username: str) -> Optional[Dict]:
        """Authenticate user and return user data (synchronous)"""
        try:
            cursor = self.sync_connection.cursor()
            cursor.execute(
                "SELECT id, user_id, username, hashed_password, email, is_active, last_login FROM users WHERE username = %s",
                (username,)
            )
            result = cursor.fetchone()
            
            if result:
                return {
                    "id": str(result["user_id"]),  # Use UUID as string
                    "user_id": str(result["user_id"]),
                    "username": result["username"],
                    "password_hash": result["hashed_password"],
                    "hashed_password": result["hashed_password"],
                    "email": result["email"],
                    "is_active": bool(result["is_active"]),
                    "last_login": result["last_login"]
                }
            return None
            
        except Exception as e:
            logger.error(f"❌ Database authentication error: {e}")
            return None

    def update_last_login(self, username: str):
        """Update user's last login timestamp (synchronous)"""
        try:
            cursor = self.sync_connection.cursor()
            cursor.execute(
                "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE username = %s",
                (username,)
            )
        except Exception as e:
            logger.error(f"❌ Failed to update last login: {e}")

    def get_or_create_session(self, user_id: str, force_new: bool = False) -> str:
        """Get existing session or create new one (synchronous)"""
        try:
            cursor = self.sync_connection.cursor()
            
            if not force_new:
                # Try to get existing session
                cursor.execute(
                    "SELECT session_id FROM chat_sessions WHERE user_id = %s ORDER BY created_at DESC LIMIT 1",
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
            
            logger.info(f"📝 Created new session: {session_id} for user: {user_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"❌ Session creation error: {e}")
            # Return fallback session ID
            return f"fallback_{user_id}_{int(datetime.now().timestamp())}"

    def add_message(self, session_id: str, user_id: str, user_message: str, 
                   bot_response: str, source: str = "unknown"):
        """Add a chat message to the database (synchronous)"""
        try:
            cursor = self.sync_connection.cursor()
            
            # FIXED: First ensure the session exists, if not create it
            cursor.execute(
                "SELECT session_id FROM chat_sessions WHERE session_id = %s",
                (session_id,)
            )
            session_exists = cursor.fetchone()
            
            if not session_exists:
                # Create the session if it doesn't exist
                logger.info(f"Creating missing session: {session_id} for user: {user_id}")
                cursor.execute(
                    "INSERT INTO chat_sessions (session_id, user_id) VALUES (%s, %s)",
                    (session_id, user_id)
                )
            
            # Insert the message
            cursor.execute(
                """INSERT INTO chat_messages 
                   (session_id, user_id, user_message, bot_response, source) 
                   VALUES (%s, %s, %s, %s, %s)""",
                (session_id, user_id, user_message, bot_response, source)
            )
            
            # FIXED: Update the session's message count and last activity
            cursor.execute(
                """UPDATE chat_sessions 
                   SET message_count = message_count + 1, 
                       last_activity = CURRENT_TIMESTAMP,
                       updated_at = CURRENT_TIMESTAMP
                   WHERE session_id = %s""",
                (session_id,)
            )
            
            logger.debug(f"💬 Message saved: {len(user_message)} chars -> {len(bot_response)} chars, session updated")
            
        except Exception as e:
            logger.error(f"❌ Failed to save message: {e}")
            raise

    def get_chat_history(self, user_id: str, limit: int = 20) -> List[Dict]:
        """Get chat history for user (synchronous)"""
        try:
            cursor = self.sync_connection.cursor()
            cursor.execute(
                """SELECT user_message, bot_response, source, timestamp 
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
                    "created_at": row["timestamp"]  # For API compatibility
                }
                for row in results
            ]
            
        except Exception as e:
            logger.error(f"❌ Failed to get chat history: {e}")
            return []

    def get_user_sessions(self, user_id: str) -> List[Dict]:
        """Get user's chat sessions (synchronous)"""
        try:
            cursor = self.sync_connection.cursor()
            
            # FIXED: Get sessions with ACTUAL message counts from chat_messages table
            cursor.execute(
                """SELECT DISTINCT s.session_id, s.created_at, 
                          COALESCE(COUNT(m.id), 0) as actual_message_count,
                          MAX(m.timestamp) as last_message_time
                   FROM chat_sessions s
                   LEFT JOIN chat_messages m ON s.session_id = m.session_id
                   WHERE s.user_id = %s
                   GROUP BY s.session_id, s.created_at
                   HAVING COUNT(m.id) > 0
                   ORDER BY MAX(m.timestamp) DESC, s.created_at DESC
                   LIMIT 15""",
                (user_id,)
            )
            
            results = cursor.fetchall()
            sessions = []
            
            for row in results:
                session_id = str(row["session_id"])
                
                # Get first message for preview
                cursor.execute(
                    "SELECT user_message FROM chat_messages WHERE session_id = %s ORDER BY timestamp ASC LIMIT 1",
                    (session_id,)
                )
                first_msg = cursor.fetchone()
                preview = first_msg["user_message"] if first_msg else "Boş sohbet"
                
                sessions.append({
                    "sessionId": session_id,
                    "session_id": session_id,
                    "created_at": row["created_at"],
                    "startedAt": row["created_at"],
                    "messageCount": row["actual_message_count"],
                    "message_count": row["actual_message_count"],
                    "lastMessageTime": row["last_message_time"],
                    "preview": preview[:50] + "..." if len(preview) > 50 else preview
                })
            
            logger.info(f"📚 Retrieved {len(sessions)} sessions with messages for user {user_id}")
            return sessions
            
        except Exception as e:
            logger.error(f"❌ Failed to get user sessions: {e}")
            return []

    def get_session_messages(self, session_id: str) -> List[Dict]:
        """Get all messages from a specific session (synchronous)"""
        try:
            cursor = self.sync_connection.cursor()
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

    def clear_chat_history(self, user_id: str):
        """Clear all chat history for user (synchronous)"""
        try:
            cursor = self.sync_connection.cursor()
            cursor.execute("DELETE FROM chat_messages WHERE user_id = %s", (user_id,))
            cursor.execute("DELETE FROM chat_sessions WHERE user_id = %s", (user_id,))
            logger.info(f"🗑️ Cleared chat history for user: {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to clear chat history: {e}")
            raise

    def get_stats(self) -> Dict:
        """Get database statistics (synchronous)"""
        try:
            cursor = self.sync_connection.cursor()
            
            # Get counts
            cursor.execute("SELECT COUNT(*) as count FROM users")
            user_count = cursor.fetchone()["count"]
            
            cursor.execute("SELECT COUNT(*) as count FROM chat_sessions")
            session_count = cursor.fetchone()["count"]
            
            cursor.execute("SELECT COUNT(*) as count FROM chat_messages")
            message_count = cursor.fetchone()["count"]
            
            return {
                "users": user_count,
                "sessions": session_count,
                "messages": message_count,
                "database_type": "PostgreSQL",
                "database_host": self.host,
                "database_name": self.database
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get stats: {e}")
            return {"error": str(e)}

    async def close(self):
        """Close database connections"""
        if self.pool:
            await self.pool.close()
        if self.sync_connection:
            self.sync_connection.close()
        logger.info("📊 PostgreSQL connections closed")

    # === Required Abstract Method Implementations ===
    
    def connect(self) -> bool:
        """Establish database connection"""
        return self.test_connection()
        
    def disconnect(self) -> None:
        """Close database connection"""
        self.close()
        
    def test_connection(self) -> bool:
        """Test if database connection is working"""
        try:
            cursor = self.sync_connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def create_user(self, username: str, email: str, password_hash: str) -> str:
        """Create new user and return user_id"""
        user_id = str(uuid.uuid4())
        try:
            cursor = self.sync_connection.cursor()
            cursor.execute(
                """INSERT INTO users (id, username, email, password_hash) 
                   VALUES (%s, %s, %s, %s)""",
                (user_id, username, email, password_hash)
            )
            return user_id
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            raise
    
    def get_user(self, username: str) -> Optional[Dict]:
        """Get user by username"""
        return self.get_user_by_username(username)
        
    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """Get user by user_id"""
        try:
            cursor = self.sync_connection.cursor(cursor_factory=RealDictCursor)
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            result = cursor.fetchone()
            return dict(result) if result else None
        except Exception as e:
            logger.error(f"Failed to get user by ID: {e}")
            return None
    
    def create_session(self, user_id: str, session_id: Optional[str] = None) -> str:
        """Create new chat session and return session_id"""
        return self.get_or_create_session(user_id, session_id)
        
    def get_user_sessions(self, user_id: str, limit: int = 15) -> List[Dict]:
        """Get all sessions for a user"""
        # Use the existing get_user_sessions method (line 319)
        # Note: limit parameter is not used in the existing implementation
        try:
            cursor = self.sync_connection.cursor()
            
            # FIXED: Get sessions with ACTUAL message counts from chat_messages table
            cursor.execute(
                """SELECT DISTINCT s.session_id, s.created_at, 
                          COALESCE(COUNT(m.id), 0) as actual_message_count,
                          MAX(m.timestamp) as last_message_time
                   FROM chat_sessions s
                   LEFT JOIN chat_messages m ON s.session_id = m.session_id
                   WHERE s.user_id = %s
                   GROUP BY s.session_id, s.created_at
                   HAVING COUNT(m.id) > 0
                   ORDER BY MAX(m.timestamp) DESC, s.created_at DESC
                   LIMIT %s""",
                (user_id, limit)
            )
            
            results = cursor.fetchall()
            sessions = []
            
            for row in results:
                session_id = str(row["session_id"])
                
                # Get first message for preview
                cursor.execute(
                    "SELECT user_message FROM chat_messages WHERE session_id = %s ORDER BY timestamp ASC LIMIT 1",
                    (session_id,)
                )
                first_msg = cursor.fetchone()
                preview = first_msg["user_message"] if first_msg else "Boş sohbet"
                
                sessions.append({
                    "sessionId": session_id,
                    "session_id": session_id,
                    "title": preview[:50] + "..." if len(preview) > 50 else preview,
                    "lastMessage": preview,
                    "timestamp": row["last_message_time"] or row["created_at"],
                    "messageCount": row["actual_message_count"]
                })
            
            return sessions
            
        except Exception as e:
            logger.error(f"❌ Failed to get user sessions: {e}")
            return []
        
    def get_session_messages(self, session_id: str) -> List[Dict]:
        """Get all messages in a session - delegates to the main implementation"""
        # Delegate to the existing get_session_messages method (line 371)
        try:
            cursor = self.sync_connection.cursor()
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
        
    def delete_old_sessions(self, user_id: str, keep_count: int = 15) -> int:
        """Delete old sessions keeping only specified count"""
        try:
            cursor = self.sync_connection.cursor()
            
            # Get sessions to delete (keep most recent ones)
            cursor.execute(
                """SELECT session_id FROM chat_sessions 
                   WHERE user_id = %s 
                   ORDER BY created_at DESC OFFSET %s""",
                (user_id, keep_count)
            )
            old_sessions = cursor.fetchall()
            
            if not old_sessions:
                return 0
            
            # Delete old sessions and their messages
            old_session_ids = [session[0] for session in old_sessions]
            cursor.execute(
                "DELETE FROM chat_messages WHERE session_id = ANY(%s)",
                (old_session_ids,)
            )
            cursor.execute(
                "DELETE FROM chat_sessions WHERE session_id = ANY(%s)",
                (old_session_ids,)
            )
            
            return len(old_session_ids)
            
        except Exception as e:
            logger.error(f"Failed to delete old sessions: {e}")
            return 0
    
    def save_session_bulk(self, session_data: Dict) -> bool:
        """Save multiple messages in a session at once"""
        try:
            session_id = session_data.get('sessionId')
            user_id = session_data.get('userId')
            messages = session_data.get('messages', [])
            
            if not session_id or not user_id or not messages:
                return False
            
            # Ensure session exists
            self.get_or_create_session(user_id, session_id)
            
            # Save all messages
            cursor = self.sync_connection.cursor()
            for msg in messages:
                cursor.execute(
                    """INSERT INTO chat_messages 
                       (session_id, user_id, user_message, bot_response, source) 
                       VALUES (%s, %s, %s, %s, %s)""",
                    (session_id, user_id, 
                     msg.get('user_message', ''), 
                     msg.get('bot_response', ''),
                     msg.get('source', 'bulk_save'))
                )
            
            # Update session message count
            cursor.execute(
                """UPDATE chat_sessions 
                   SET message_count = %s, last_activity = CURRENT_TIMESTAMP
                   WHERE session_id = %s""",
                (len(messages), session_id)
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save session bulk: {e}")
            return False
    
    def get_sessions(self, user_id: str) -> List[Dict]:
        """Alias for get_user_sessions for backward compatibility"""
        return self.get_user_sessions(user_id)

    def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check"""
        try:
            # Test connection
            connection_ok = self.test_connection()
            
            # Get basic stats
            cursor = self.sync_connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM chat_sessions")
            session_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM chat_messages")
            message_count = cursor.fetchone()[0]
            
            return {
                "status": "healthy" if connection_ok else "unhealthy",
                "database": "postgresql",
                "connection": connection_ok,
                "stats": {
                    "users": user_count,
                    "sessions": session_count,
                    "messages": message_count
                }
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "database": "postgresql", 
                "connection": False,
                "error": str(e)
            }


# Global instance
postgresql_manager = None

def get_postgresql_manager() -> PostgreSQLManager:
    """Get or create PostgreSQL manager instance"""
    global postgresql_manager
    if postgresql_manager is None:
        postgresql_manager = PostgreSQLManager()
    return postgresql_manager
