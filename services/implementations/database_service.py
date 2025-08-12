"""
🗄️ Database Service Implementation
===================================
PostgreSQL database service implementing interface with dependency injection support.
"""

import os
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool

from core.interfaces.database_interface import IDatabaseManager, IUserRepository, ISessionRepository
from core.interfaces.config_interface import IDatabaseConfigurationService


logger = logging.getLogger(__name__)


class PostgreSQLDatabaseManager(IDatabaseManager):
    """
    PostgreSQL database manager implementing IDatabaseManager interface.
    Single Responsibility: Database connection and transaction management.
    """
    
    def __init__(self, config_service: IDatabaseConfigurationService):
        """Initialize with configuration service dependency injection"""
        self.config_service = config_service
        self.connection_pool: Optional[ThreadedConnectionPool] = None
        self._initialize_connection_pool()
        
        # Initialize repositories with dependency injection
        self.user_repository = UserRepository(self)
        self.session_repository = SessionRepository(self)
        
        logger.info("✅ PostgreSQL Database Manager initialized with DI")
    
    def _initialize_connection_pool(self):
        """Initialize PostgreSQL connection pool using configuration"""
        try:
            db_config = self.config_service.get_database_config()
            
            self.connection_pool = ThreadedConnectionPool(
                minconn=db_config.get('min_connections', 1),
                maxconn=db_config.get('max_connections', 20),
                host=db_config['host'],
                port=db_config['port'],
                user=db_config['user'],
                password=db_config['password'],
                database=db_config['database'],
                cursor_factory=RealDictCursor
            )
            
            # Ensure tables exist
            self._ensure_tables_exist()
            logger.info("✅ PostgreSQL connection pool established")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize PostgreSQL connection pool: {e}")
            raise
    
    def _get_connection(self):
        """Get connection from pool"""
        if not self.connection_pool:
            raise RuntimeError("Database connection pool not initialized")
        return self.connection_pool.getconn()
    
    def _put_connection(self, conn):
        """Return connection to pool"""
        if self.connection_pool:
            self.connection_pool.putconn(conn)
    
    async def initialize(self) -> bool:
        """Initialize database - already done in constructor"""
        return True
    
    def health_check(self) -> Dict[str, Any]:
        """Check database health"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            
            return {
                "status": "healthy",
                "database": "postgresql",
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        finally:
            if 'conn' in locals():
                self._put_connection(conn)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Get user count
            cursor.execute("SELECT COUNT(*) as count FROM users")
            user_count = cursor.fetchone()['count']
            
            # Get session count
            cursor.execute("SELECT COUNT(*) as count FROM chat_sessions")
            session_count = cursor.fetchone()['count']
            
            # Get message count
            cursor.execute("SELECT COUNT(*) as count FROM chat_messages")
            message_count = cursor.fetchone()['count']
            
            return {
                "total_users": user_count,
                "total_sessions": session_count,
                "total_messages": message_count,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {"error": str(e)}
        finally:
            if 'conn' in locals():
                self._put_connection(conn)
    
    # User Management Methods
    def authenticate_user(self, username: str) -> Optional[Dict[str, Any]]:
        """Delegate to user repository"""
        return self.user_repository.find_by_username(username)
    
    def create_user(self, username: str, email: str, hashed_password: str, **kwargs) -> str:
        """Delegate to user repository"""
        user_data = {
            'username': username,
            'email': email,
            'hashed_password': hashed_password,
            **kwargs
        }
        return self.user_repository.create(user_data)
    
    def update_last_login(self, username: str) -> bool:
        """Update user's last login timestamp"""
        return self.user_repository.update_last_login(username)
    
    # Session Management Methods
    def get_or_create_session(self, user_id: str, force_new: bool = False) -> str:
        """Delegate to session repository"""
        if force_new:
            return self.session_repository.create_session(user_id)
        
        # Get existing active session or create new one
        sessions = self.session_repository.find_by_user(user_id, limit=1)
        if sessions and not force_new:
            return sessions[0]['session_id']
        
        return self.session_repository.create_session(user_id)
    
    def get_user_sessions(self, user_id: str, limit: int = 15) -> List[Dict[str, Any]]:
        """Delegate to session repository"""
        return self.session_repository.find_by_user(user_id, limit)
    
    def get_session_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """Get messages from a specific session"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT user_message, bot_response, source, timestamp, created_at
                FROM chat_messages 
                WHERE session_id = %s 
                ORDER BY created_at ASC
            """, (session_id,))
            
            return cursor.fetchall()
            
        except Exception as e:
            logger.error(f"Failed to get session messages: {e}")
            return []
        finally:
            if 'conn' in locals():
                self._put_connection(conn)
    
    # Message Management Methods
    def add_message(self, session_id: str, user_id: str, user_message: str, 
                   bot_response: str, source: str = "unknown", **metadata) -> bool:
        """Add new message to database"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO chat_messages 
                (session_id, user_id, user_message, bot_response, source, metadata, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                session_id, user_id, user_message, bot_response, 
                source, metadata if metadata else {}, datetime.utcnow()
            ))
            
            # Update session message count
            cursor.execute("""
                UPDATE chat_sessions 
                SET message_count = message_count + 1, updated_at = %s 
                WHERE session_id = %s
            """, (datetime.utcnow(), session_id))
            
            conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to add message: {e}")
            if 'conn' in locals():
                conn.rollback()
            return False
        finally:
            if 'conn' in locals():
                self._put_connection(conn)
    
    def get_recent_messages(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent messages for user"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT session_id, user_message, bot_response, source, timestamp
                FROM chat_messages 
                WHERE user_id = %s 
                ORDER BY timestamp DESC 
                LIMIT %s
            """, (user_id, limit))
            
            return cursor.fetchall()
            
        except Exception as e:
            logger.error(f"Failed to get recent messages: {e}")
            return []
        finally:
            if 'conn' in locals():
                self._put_connection(conn)
    
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
            
            # Create indexes
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
    
    def close(self) -> None:
        """Close database connection pool"""
        if self.connection_pool:
            self.connection_pool.closeall()
            logger.info("🔒 Database connection pool closed")


class UserRepository(IUserRepository):
    """
    User repository implementing IUserRepository interface.
    Single Responsibility: User data access operations.
    """
    
    def __init__(self, db_manager: PostgreSQLDatabaseManager):
        self.db_manager = db_manager
    
    def find_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Find user by username"""
        try:
            conn = self.db_manager._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, user_id, username, email, hashed_password, 
                       full_name, created_at, last_login, is_active, failed_login_attempts
                FROM users WHERE username = %s AND is_active = TRUE
            """, (username,))
            
            result = cursor.fetchone()
            return dict(result) if result else None
            
        except Exception as e:
            logger.error(f"Failed to find user by username: {e}")
            return None
        finally:
            if 'conn' in locals():
                self.db_manager._put_connection(conn)
    
    def find_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Find user by email"""
        try:
            conn = self.db_manager._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, user_id, username, email, hashed_password, 
                       full_name, created_at, last_login, is_active, failed_login_attempts
                FROM users WHERE email = %s AND is_active = TRUE
            """, (email,))
            
            result = cursor.fetchone()
            return dict(result) if result else None
            
        except Exception as e:
            logger.error(f"Failed to find user by email: {e}")
            return None
        finally:
            if 'conn' in locals():
                self.db_manager._put_connection(conn)
    
    def create(self, user_data: Dict[str, Any]) -> str:
        """Create new user"""
        try:
            conn = self.db_manager._get_connection()
            cursor = conn.cursor()
            
            user_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO users (user_id, username, email, hashed_password, full_name)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING user_id
            """, (
                user_id,
                user_data['username'],
                user_data.get('email'),
                user_data['hashed_password'],
                user_data.get('full_name')
            ))
            
            result = cursor.fetchone()
            conn.commit()
            
            logger.info(f"✅ User created: {user_data['username']}")
            return result['user_id']
            
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            if 'conn' in locals():
                conn.rollback()
            raise
        finally:
            if 'conn' in locals():
                self.db_manager._put_connection(conn)
    
    def update(self, user_id: str, user_data: Dict[str, Any]) -> bool:
        """Update user data"""
        try:
            conn = self.db_manager._get_connection()
            cursor = conn.cursor()
            
            # Build dynamic update query
            update_fields = []
            values = []
            
            for field, value in user_data.items():
                if field in ['email', 'full_name', 'hashed_password', 'is_active']:
                    update_fields.append(f"{field} = %s")
                    values.append(value)
            
            if not update_fields:
                return True
            
            values.append(datetime.utcnow())  # updated_at
            values.append(user_id)
            
            query = f"""
                UPDATE users 
                SET {', '.join(update_fields)}, updated_at = %s
                WHERE user_id = %s
            """
            
            cursor.execute(query, values)
            conn.commit()
            
            return cursor.rowcount > 0
            
        except Exception as e:
            logger.error(f"Failed to update user: {e}")
            if 'conn' in locals():
                conn.rollback()
            return False
        finally:
            if 'conn' in locals():
                self.db_manager._put_connection(conn)
    
    def update_last_login(self, username: str) -> bool:
        """Update user's last login timestamp"""
        try:
            conn = self.db_manager._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE users 
                SET last_login = %s, updated_at = %s
                WHERE username = %s
            """, (datetime.utcnow(), datetime.utcnow(), username))
            
            conn.commit()
            return cursor.rowcount > 0
            
        except Exception as e:
            logger.error(f"Failed to update last login: {e}")
            if 'conn' in locals():
                conn.rollback()
            return False
        finally:
            if 'conn' in locals():
                self.db_manager._put_connection(conn)
    
    def delete(self, user_id: str) -> bool:
        """Soft delete user (set is_active = FALSE)"""
        return self.update(user_id, {'is_active': False})


class SessionRepository(ISessionRepository):
    """
    Session repository implementing ISessionRepository interface.
    Single Responsibility: Session data access operations.
    """
    
    def __init__(self, db_manager: PostgreSQLDatabaseManager):
        self.db_manager = db_manager
    
    def create_session(self, user_id: str) -> str:
        """Create new session"""
        try:
            conn = self.db_manager._get_connection()
            cursor = conn.cursor()
            
            session_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO chat_sessions (session_id, user_id)
                VALUES (%s, %s)
                RETURNING session_id
            """, (session_id, user_id))
            
            result = cursor.fetchone()
            conn.commit()
            
            logger.info(f"✅ Session created: {session_id} for user {user_id}")
            return result['session_id']
            
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            if 'conn' in locals():
                conn.rollback()
            # Return fallback session ID
            return f"fallback_{user_id}_{int(datetime.utcnow().timestamp())}"
        finally:
            if 'conn' in locals():
                self.db_manager._put_connection(conn)
    
    def find_by_user(self, user_id: str, limit: int = 15) -> List[Dict[str, Any]]:
        """Find sessions by user ID"""
        try:
            conn = self.db_manager._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT session_id, user_id, created_at, updated_at, message_count
                FROM chat_sessions 
                WHERE user_id = %s AND is_active = TRUE
                ORDER BY updated_at DESC 
                LIMIT %s
            """, (user_id, limit))
            
            return cursor.fetchall()
            
        except Exception as e:
            logger.error(f"Failed to find sessions by user: {e}")
            return []
        finally:
            if 'conn' in locals():
                self.db_manager._put_connection(conn)
    
    def find_by_id(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Find session by ID"""
        try:
            conn = self.db_manager._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT session_id, user_id, created_at, updated_at, message_count, is_active
                FROM chat_sessions 
                WHERE session_id = %s
            """, (session_id,))
            
            result = cursor.fetchone()
            return dict(result) if result else None
            
        except Exception as e:
            logger.error(f"Failed to find session by ID: {e}")
            return None
        finally:
            if 'conn' in locals():
                self.db_manager._put_connection(conn)
    
    def update_session(self, session_id: str, data: Dict[str, Any]) -> bool:
        """Update session data"""
        try:
            conn = self.db_manager._get_connection()
            cursor = conn.cursor()
            
            # Build dynamic update query
            update_fields = []
            values = []
            
            for field, value in data.items():
                if field in ['message_count', 'is_active']:
                    update_fields.append(f"{field} = %s")
                    values.append(value)
            
            if not update_fields:
                return True
            
            values.append(datetime.utcnow())  # updated_at
            values.append(session_id)
            
            query = f"""
                UPDATE chat_sessions 
                SET {', '.join(update_fields)}, updated_at = %s
                WHERE session_id = %s
            """
            
            cursor.execute(query, values)
            conn.commit()
            
            return cursor.rowcount > 0
            
        except Exception as e:
            logger.error(f"Failed to update session: {e}")
            if 'conn' in locals():
                conn.rollback()
            return False
        finally:
            if 'conn' in locals():
                self.db_manager._put_connection(conn)
