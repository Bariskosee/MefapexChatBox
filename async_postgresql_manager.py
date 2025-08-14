"""
🚀 MEFAPEX Async PostgreSQL Database Manager
Full async/await support for FastAPI performance optimization
Replaces sync psycopg2 with asyncpg for true async operations
"""

import os
import uuid
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from contextlib import asynccontextmanager
import asyncpg
import bcrypt
from database.interface import DatabaseInterface

logger = logging.getLogger(__name__)

class AsyncPostgreSQLManager(DatabaseInterface):
    """
    Fully Asynchronous PostgreSQL Database Manager for MEFAPEX Chat System
    
    Key Improvements:
    - 100% async/await operations using asyncpg
    - Connection pooling for high performance
    - No thread blocking in FastAPI
    - Proper resource management
    - Better error handling and recovery
    """
    
    def __init__(self):
        """Initialize async PostgreSQL manager"""
        # Database configuration from environment
        self.host = os.getenv("POSTGRES_HOST", "localhost")
        self.port = int(os.getenv("POSTGRES_PORT", "5432"))
        self.database = os.getenv("POSTGRES_DB", "mefapex_chatbot")
        self.user = os.getenv("POSTGRES_USER", "mefapex")
        self.password = os.getenv("POSTGRES_PASSWORD", "mefapex")
        
        # Connection pool (will be initialized in initialize())
        self.pool: Optional[asyncpg.Pool] = None
        self._initialized = False
        
        logger.info(f"🔄 Async PostgreSQL Manager created for {self.host}:{self.port}/{self.database}")

    async def initialize(self) -> bool:
        """Initialize async connection pool and database schema"""
        try:
            # Create connection pool with optimized settings
            self.pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                min_size=5,          # Minimum connections in pool
                max_size=25,         # Maximum connections in pool
                max_queries=50000,   # Max queries per connection
                max_inactive_connection_lifetime=300.0,  # 5 minutes
                command_timeout=60,  # Command timeout in seconds
                server_settings={
                    'application_name': 'mefapex_chatbot',
                    'tcp_keepalives_idle': '600',
                    'tcp_keepalives_interval': '30',
                    'tcp_keepalives_count': '3',
                }
            )
            
            logger.info("✅ Async PostgreSQL connection pool created")
            
            # Initialize database schema
            await self._init_schema()
            
            self._initialized = True
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize async PostgreSQL: {e}")
            return False

    @asynccontextmanager
    async def get_connection(self):
        """Get connection from pool with proper resource management"""
        if not self.pool:
            raise RuntimeError("Database pool not initialized. Call initialize() first.")
        
        conn = await self.pool.acquire()
        try:
            yield conn
        finally:
            await self.pool.release(conn)

    async def _init_schema(self):
        """Initialize database schema with all necessary tables and indexes"""
        try:
            async with self.get_connection() as conn:
                # Enable UUID extension
                await conn.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")
                await conn.execute("CREATE EXTENSION IF NOT EXISTS \"pg_trgm\"")
                
                # Create users table with optimized structure
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
                        session_title VARCHAR(200),
                        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                    )
                """)
                
                # Create chat_messages table with better indexing
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS chat_messages (
                        id BIGSERIAL PRIMARY KEY,
                        message_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
                        session_id UUID NOT NULL,
                        user_id UUID NOT NULL,
                        timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        user_message TEXT,
                        bot_response TEXT,
                        source VARCHAR(100) DEFAULT 'unknown',
                        message_type VARCHAR(50) DEFAULT 'user',
                        tokens_used INTEGER DEFAULT 0,
                        processing_time_ms INTEGER DEFAULT 0,
                        metadata JSONB,
                        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                        FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE
                    )
                """)
                
                # Create optimized indexes for performance
                indexes = [
                    "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)",
                    "CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id)",
                    "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
                    "CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON chat_sessions(user_id)",
                    "CREATE INDEX IF NOT EXISTS idx_sessions_session_id ON chat_sessions(session_id)",
                    "CREATE INDEX IF NOT EXISTS idx_sessions_last_activity ON chat_sessions(last_activity DESC)",
                    "CREATE INDEX IF NOT EXISTS idx_messages_user_id ON chat_messages(user_id)",
                    "CREATE INDEX IF NOT EXISTS idx_messages_session_id ON chat_messages(session_id)",
                    "CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON chat_messages(timestamp DESC)",
                    "CREATE INDEX IF NOT EXISTS idx_messages_message_id ON chat_messages(message_id)",
                    "CREATE INDEX IF NOT EXISTS idx_messages_user_session ON chat_messages(user_id, session_id)",
                ]
                
                for index_sql in indexes:
                    await conn.execute(index_sql)
                
                logger.info("✅ Async database schema initialized with optimized indexes")
                
                # Create demo user if it doesn't exist
                await self._create_demo_user_if_not_exists(conn)
                
        except Exception as e:
            logger.error(f"❌ Schema initialization failed: {e}")
            raise

    async def _create_demo_user_if_not_exists(self, conn):
        """Create demo user if it doesn't exist"""
        try:
            # Check if demo user exists
            result = await conn.fetchrow("SELECT user_id FROM users WHERE username = $1", "demo")
            
            if not result:
                # Create demo user
                demo_password = "1234"
                hashed_password = bcrypt.hashpw(demo_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                demo_user_id = uuid.uuid4()
                
                await conn.execute("""
                    INSERT INTO users (user_id, username, email, hashed_password, full_name, is_active)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """, demo_user_id, "demo", "demo@mefapex.com", hashed_password, "Demo User", True)
                
                logger.info(f"✅ Demo user created with ID: {demo_user_id}")
            else:
                logger.info("✅ Demo user already exists")
                
        except Exception as e:
            logger.error(f"❌ Failed to create demo user: {e}")

    # === Async User Management ===
    
    async def authenticate_user(self, username: str) -> Optional[Dict]:
        """Authenticate user and return user data (async)"""
        try:
            async with self.get_connection() as conn:
                result = await conn.fetchrow("""
                    SELECT user_id, username, hashed_password, email, is_active, last_login, full_name
                    FROM users WHERE username = $1 AND is_active = true
                """, username)
                
                if result:
                    return {
                        "id": str(result["user_id"]),
                        "user_id": str(result["user_id"]),
                        "username": result["username"],
                        "password_hash": result["hashed_password"],
                        "hashed_password": result["hashed_password"],
                        "email": result["email"],
                        "full_name": result["full_name"],
                        "is_active": bool(result["is_active"]),
                        "last_login": result["last_login"]
                    }
                return None
                
        except Exception as e:
            logger.error(f"❌ Database authentication error: {e}")
            return None

    async def update_last_login(self, username: str) -> bool:
        """Update user's last login timestamp (async)"""
        try:
            async with self.get_connection() as conn:
                result = await conn.execute("""
                    UPDATE users 
                    SET last_login = CURRENT_TIMESTAMP, 
                        updated_at = CURRENT_TIMESTAMP,
                        failed_login_attempts = 0
                    WHERE username = $1
                """, username)
                return result == "UPDATE 1"
                
        except Exception as e:
            logger.error(f"❌ Failed to update last login: {e}")
            return False

    async def create_user(self, username: str, email: str, password_hash: str, full_name: str = None) -> str:
        """Create new user and return user_id (async)"""
        try:
            user_id = uuid.uuid4()
            async with self.get_connection() as conn:
                await conn.execute("""
                    INSERT INTO users (user_id, username, email, hashed_password, full_name)
                    VALUES ($1, $2, $3, $4, $5)
                """, user_id, username, email, password_hash, full_name)
                
                logger.info(f"✅ User created: {username} with ID: {user_id}")
                return str(user_id)
                
        except Exception as e:
            logger.error(f"❌ Failed to create user: {e}")
            raise

    async def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """Get user by user_id (async)"""
        try:
            async with self.get_connection() as conn:
                result = await conn.fetchrow("""
                    SELECT user_id, username, email, full_name, is_active, created_at, last_login
                    FROM users WHERE user_id = $1
                """, uuid.UUID(user_id))
                
                if result:
                    return {
                        "id": str(result["user_id"]),
                        "user_id": str(result["user_id"]),
                        "username": result["username"],
                        "email": result["email"],
                        "full_name": result["full_name"],
                        "is_active": result["is_active"],
                        "created_at": result["created_at"],
                        "last_login": result["last_login"]
                    }
                return None
                
        except Exception as e:
            logger.error(f"❌ Failed to get user by ID: {e}")
            return None

    # === Async Session Management ===
    
    async def get_or_create_session(self, user_id: str, force_new: bool = False) -> str:
        """Get existing session or create new one (async)"""
        try:
            async with self.get_connection() as conn:
                if not force_new:
                    # Try to get existing active session
                    result = await conn.fetchrow("""
                        SELECT session_id FROM chat_sessions 
                        WHERE user_id = $1 AND is_active = true
                        ORDER BY last_activity DESC LIMIT 1
                    """, uuid.UUID(user_id))
                    
                    if result:
                        return str(result["session_id"])
                
                # Create new session
                session_id = uuid.uuid4()
                await conn.execute("""
                    INSERT INTO chat_sessions (session_id, user_id, session_title)
                    VALUES ($1, $2, $3)
                """, session_id, uuid.UUID(user_id), "New Chat")
                
                logger.info(f"📝 Created new session: {session_id} for user: {user_id}")
                return str(session_id)
                
        except Exception as e:
            logger.error(f"❌ Session creation error: {e}")
            # Return fallback session ID
            return f"fallback_{user_id}_{int(datetime.now().timestamp())}"

    async def create_session(self, user_id: str, session_id: Optional[str] = None) -> str:
        """Create new chat session and return session_id (async)"""
        try:
            if session_id:
                new_session_id = uuid.UUID(session_id)
            else:
                new_session_id = uuid.uuid4()
                
            async with self.get_connection() as conn:
                await conn.execute("""
                    INSERT INTO chat_sessions (session_id, user_id, session_title)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (session_id) DO NOTHING
                """, new_session_id, uuid.UUID(user_id), "New Chat")
                
                return str(new_session_id)
                
        except Exception as e:
            logger.error(f"❌ Failed to create session: {e}")
            raise

    async def get_user_sessions(self, user_id: str, limit: int = 15) -> List[Dict]:
        """Get user's chat sessions (async)"""
        try:
            async with self.get_connection() as conn:
                results = await conn.fetch("""
                    SELECT DISTINCT s.session_id, s.created_at, s.session_title, s.last_activity,
                           COALESCE(COUNT(m.id), 0) as actual_message_count,
                           MAX(m.timestamp) as last_message_time
                    FROM chat_sessions s
                    LEFT JOIN chat_messages m ON s.session_id = m.session_id
                    WHERE s.user_id = $1 AND s.is_active = true
                    GROUP BY s.session_id, s.created_at, s.session_title, s.last_activity
                    HAVING COUNT(m.id) > 0
                    ORDER BY MAX(m.timestamp) DESC, s.created_at DESC
                    LIMIT $2
                """, uuid.UUID(user_id), limit)
                
                sessions = []
                for row in results:
                    session_id = str(row["session_id"])
                    
                    # Get first message for preview
                    first_msg = await conn.fetchrow("""
                        SELECT user_message FROM chat_messages 
                        WHERE session_id = $1 
                        ORDER BY timestamp ASC LIMIT 1
                    """, row["session_id"])
                    
                    preview = first_msg["user_message"] if first_msg and first_msg["user_message"] else "Boş sohbet"
                    
                    sessions.append({
                        "sessionId": session_id,
                        "session_id": session_id,
                        "title": row["session_title"] or (preview[:50] + "..." if len(preview) > 50 else preview),
                        "created_at": row["created_at"],
                        "startedAt": row["created_at"],
                        "messageCount": row["actual_message_count"],
                        "message_count": row["actual_message_count"],
                        "lastMessageTime": row["last_message_time"],
                        "lastActivity": row["last_activity"],
                        "preview": preview[:50] + "..." if len(preview) > 50 else preview
                    })
                
                logger.info(f"📚 Retrieved {len(sessions)} sessions for user {user_id}")
                return sessions
                
        except Exception as e:
            logger.error(f"❌ Failed to get user sessions: {e}")
            return []

    async def get_session_messages(self, session_id: str) -> List[Dict]:
        """Get all messages from a specific session (async)"""
        try:
            async with self.get_connection() as conn:
                results = await conn.fetch("""
                    SELECT message_id, user_message, bot_response, source, timestamp, 
                           tokens_used, processing_time_ms, metadata
                    FROM chat_messages 
                    WHERE session_id = $1 
                    ORDER BY timestamp ASC
                """, uuid.UUID(session_id))
                
                messages = []
                for row in results:
                    messages.append({
                        "message_id": str(row["message_id"]),
                        "user_message": row["user_message"],
                        "bot_response": row["bot_response"],
                        "source": row["source"],
                        "timestamp": row["timestamp"],
                        "tokens_used": row["tokens_used"],
                        "processing_time_ms": row["processing_time_ms"],
                        "metadata": row["metadata"]
                    })
                
                return messages
                
        except Exception as e:
            logger.error(f"❌ Failed to get session messages: {e}")
            return []

    # === Async Message Management ===
    
    async def add_message(self, session_id: str, user_id: str, user_message: str, 
                         bot_response: str, source: str = "unknown", 
                         tokens_used: int = 0, processing_time_ms: int = 0) -> bool:
        """Add a chat message to the database (async)"""
        try:
            async with self.get_connection() as conn:
                # Ensure session exists
                session_exists = await conn.fetchrow("""
                    SELECT session_id FROM chat_sessions WHERE session_id = $1
                """, uuid.UUID(session_id))
                
                if not session_exists:
                    # Create the session if it doesn't exist
                    logger.info(f"Creating missing session: {session_id} for user: {user_id}")
                    await conn.execute("""
                        INSERT INTO chat_sessions (session_id, user_id, session_title)
                        VALUES ($1, $2, $3)
                    """, uuid.UUID(session_id), uuid.UUID(user_id), "Chat Session")
                
                # Insert the message
                message_id = uuid.uuid4()
                await conn.execute("""
                    INSERT INTO chat_messages 
                    (message_id, session_id, user_id, user_message, bot_response, source, 
                     tokens_used, processing_time_ms) 
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """, message_id, uuid.UUID(session_id), uuid.UUID(user_id), 
                    user_message, bot_response, source, tokens_used, processing_time_ms)
                
                # Update session statistics
                await conn.execute("""
                    UPDATE chat_sessions 
                    SET message_count = message_count + 1, 
                        last_activity = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE session_id = $1
                """, uuid.UUID(session_id))
                
                logger.debug(f"💬 Message saved: {len(user_message)} chars -> {len(bot_response)} chars")
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to save message: {e}")
            return False

    async def get_chat_history(self, user_id: str, limit: int = 20) -> List[Dict]:
        """Get chat history for user (async)"""
        try:
            async with self.get_connection() as conn:
                results = await conn.fetch("""
                    SELECT user_message, bot_response, source, timestamp, tokens_used
                    FROM chat_messages 
                    WHERE user_id = $1 
                    ORDER BY timestamp DESC 
                    LIMIT $2
                """, uuid.UUID(user_id), limit)
                
                return [
                    {
                        "user_message": row["user_message"],
                        "bot_response": row["bot_response"],
                        "source": row["source"],
                        "timestamp": row["timestamp"],
                        "created_at": row["timestamp"],  # API compatibility
                        "tokens_used": row["tokens_used"]
                    }
                    for row in results
                ]
                
        except Exception as e:
            logger.error(f"❌ Failed to get chat history: {e}")
            return []

    async def clear_chat_history(self, user_id: str) -> bool:
        """Clear all chat history for user (async)"""
        try:
            async with self.get_connection() as conn:
                # Delete messages first (due to foreign key constraints)
                await conn.execute("DELETE FROM chat_messages WHERE user_id = $1", uuid.UUID(user_id))
                # Then delete sessions
                await conn.execute("DELETE FROM chat_sessions WHERE user_id = $1", uuid.UUID(user_id))
                
                logger.info(f"🗑️ Cleared chat history for user: {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to clear chat history: {e}")
            return False

    async def delete_old_sessions(self, user_id: str, keep_count: int = 15) -> int:
        """Delete old sessions keeping only specified count (async)"""
        try:
            async with self.get_connection() as conn:
                # Get sessions to delete (keep most recent ones)
                old_sessions = await conn.fetch("""
                    SELECT session_id FROM chat_sessions 
                    WHERE user_id = $1 
                    ORDER BY created_at DESC OFFSET $2
                """, uuid.UUID(user_id), keep_count)
                
                if not old_sessions:
                    return 0
                
                # Delete old sessions and their messages
                old_session_ids = [session["session_id"] for session in old_sessions]
                
                # Delete messages first
                await conn.execute("""
                    DELETE FROM chat_messages WHERE session_id = ANY($1::uuid[])
                """, old_session_ids)
                
                # Delete sessions
                result = await conn.execute("""
                    DELETE FROM chat_sessions WHERE session_id = ANY($1::uuid[])
                """, old_session_ids)
                
                deleted_count = len(old_session_ids)
                logger.info(f"🧹 Deleted {deleted_count} old sessions for user {user_id}")
                return deleted_count
                
        except Exception as e:
            logger.error(f"❌ Failed to delete old sessions: {e}")
            return 0

    # === Bulk Operations ===
    
    async def save_session_bulk(self, session_data: Dict) -> bool:
        """Save multiple messages in a session at once (async)"""
        try:
            session_id = session_data.get('sessionId')
            user_id = session_data.get('userId')
            messages = session_data.get('messages', [])
            
            if not session_id or not user_id or not messages:
                return False
            
            async with self.get_connection() as conn:
                # Ensure session exists
                await self.create_session(user_id, session_id)
                
                # Save all messages in a transaction
                async with conn.transaction():
                    for msg in messages:
                        message_id = uuid.uuid4()
                        await conn.execute("""
                            INSERT INTO chat_messages 
                            (message_id, session_id, user_id, user_message, bot_response, source) 
                            VALUES ($1, $2, $3, $4, $5, $6)
                        """, message_id, uuid.UUID(session_id), uuid.UUID(user_id),
                            msg.get('user_message', ''), 
                            msg.get('bot_response', ''),
                            msg.get('source', 'bulk_save'))
                    
                    # Update session message count
                    await conn.execute("""
                        UPDATE chat_sessions 
                        SET message_count = $1, last_activity = CURRENT_TIMESTAMP
                        WHERE session_id = $2
                    """, len(messages), uuid.UUID(session_id))
                
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to save session bulk: {e}")
            return False

    # === Health Check and Statistics ===
    
    async def get_stats(self) -> Dict:
        """Get database statistics (async)"""
        try:
            async with self.get_connection() as conn:
                user_count = await conn.fetchval("SELECT COUNT(*) FROM users")
                session_count = await conn.fetchval("SELECT COUNT(*) FROM chat_sessions")
                message_count = await conn.fetchval("SELECT COUNT(*) FROM chat_messages")
                
                return {
                    "users": user_count,
                    "sessions": session_count,
                    "messages": message_count,
                    "database_type": "Async PostgreSQL",
                    "database_host": self.host,
                    "database_name": self.database,
                    "pool_size": self.pool.get_size() if self.pool else 0,
                    "pool_idle": self.pool.get_idle_size() if self.pool else 0,
                }
                
        except Exception as e:
            logger.error(f"❌ Failed to get stats: {e}")
            return {"error": str(e)}

    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check (async)"""
        try:
            # Test connection with a simple query
            async with self.get_connection() as conn:
                await conn.fetchval("SELECT 1")
                
                # Get basic stats
                user_count = await conn.fetchval("SELECT COUNT(*) FROM users")
                session_count = await conn.fetchval("SELECT COUNT(*) FROM chat_sessions")
                message_count = await conn.fetchval("SELECT COUNT(*) FROM chat_messages")
                
                return {
                    "status": "healthy",
                    "database": "async_postgresql",
                    "connection": True,
                    "pool_status": {
                        "size": self.pool.get_size() if self.pool else 0,
                        "idle": self.pool.get_idle_size() if self.pool else 0,
                    },
                    "stats": {
                        "users": user_count,
                        "sessions": session_count,
                        "messages": message_count
                    }
                }
                
        except Exception as e:
            logger.error(f"❌ Health check failed: {e}")
            return {
                "status": "unhealthy",
                "database": "async_postgresql", 
                "connection": False,
                "error": str(e)
            }

    # === Required Abstract Method Implementations ===
    
    def connect(self) -> bool:
        """Establish database connection (not used in async version)"""
        return asyncio.run(self.test_connection())
        
    def disconnect(self) -> None:
        """Close database connection"""
        if self.pool:
            asyncio.run(self.pool.close())
        
    async def test_connection(self) -> bool:
        """Test if database connection is working (async)"""
        try:
            if not self.pool:
                return False
                
            async with self.get_connection() as conn:
                await conn.fetchval("SELECT 1")
                return True
                
        except Exception as e:
            logger.error(f"❌ Connection test failed: {e}")
            return False

    def get_user(self, username: str) -> Optional[Dict]:
        """Get user by username (sync wrapper for async method)"""
        return asyncio.run(self.authenticate_user(username))

    async def close(self):
        """Close database connections and cleanup"""
        if self.pool:
            await self.pool.close()
            logger.info("📊 Async PostgreSQL connections closed")

    def get_sessions(self, user_id: str) -> List[Dict]:
        """Alias for get_user_sessions for backward compatibility"""
        return asyncio.run(self.get_user_sessions(user_id))


# Global instance
async_postgresql_manager = None

async def get_async_postgresql_manager() -> AsyncPostgreSQLManager:
    """Get or create async PostgreSQL manager instance"""
    global async_postgresql_manager
    if async_postgresql_manager is None:
        async_postgresql_manager = AsyncPostgreSQLManager()
        await async_postgresql_manager.initialize()
    return async_postgresql_manager

async def initialize_async_db():
    """Initialize the async database manager"""
    return await get_async_postgresql_manager()
