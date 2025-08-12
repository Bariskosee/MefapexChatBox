"""
🎯 Database Manager - Unified Interface (Facade Pattern)
======================================================

Unified interface that provides all database operations through a single entry point.
This maintains backward compatibility while using the new modular architecture.
"""

import logging
from typing import Dict, List, Optional, Any
from .services.connection_service import connection_service
from .repositories.user_repository import user_repository
from .repositories.session_repository import session_repository
from .repositories.message_repository import message_repository
from .models.user import User
from .models.session import ChatSession
from .models.message import ChatMessage

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Unified Database Manager (Facade Pattern)
    
    Provides a single interface for all database operations while delegating
    to specialized repositories. Maintains backward compatibility with the
    original monolithic database manager.
    """
    
    def __init__(self):
        """Initialize Database Manager"""
        self.connection_service = connection_service
        self.user_repo = user_repository
        self.session_repo = session_repository
        self.message_repo = message_repository
        
        # Initialize database tables
        self._ensure_tables_exist()
        
        logger.info("✅ Modular Database Manager initialized")

    def _ensure_tables_exist(self):
        """Create necessary tables if they don't exist"""
        try:
            with self.connection_service.get_cursor() as cursor:
                # Create users table
                cursor.execute("""
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
                """)
                
                # Create chat_sessions table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS chat_sessions (
                        id SERIAL PRIMARY KEY,
                        session_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
                        user_id VARCHAR(255) NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT TRUE,
                        message_count INTEGER DEFAULT 0
                    )
                """)
                
                # Create chat_messages table
                cursor.execute("""
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
                """)
                
                # Create indexes
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions(user_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_chat_sessions_session_id ON chat_sessions(session_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages(session_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_chat_messages_user_id ON chat_messages(user_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_chat_messages_timestamp ON chat_messages(timestamp)')
                
                logger.info("✅ Database tables and indexes created/verified")
                
        except Exception as e:
            logger.error(f"❌ Failed to create tables: {e}")
            raise

    # === User Management (Backward Compatible) ===
    
    def authenticate_user(self, username: str) -> Optional[Dict]:
        """Authenticate user and return user data (backward compatible)"""
        user = self.user_repo.get_user_by_username(username)
        if user:
            return {
                "user_id": str(user.user_id),  # Primary key is now user_id
                "username": user.username,
                "password_hash": user.password_hash,  # New column name
                "hashed_password": user.password_hash,  # Backward compatibility
                "email": user.email,
                "is_active": user.is_active,
                "last_login": user.last_login
            }
        return None

    def create_user(self, username: str, password_hash: str, email: str = None) -> bool:
        """Create a new user (backward compatible)"""
        try:
            user = User(
                username=username,
                password_hash=password_hash,  # Use new column name
                email=email
            )
            created_user = self.user_repo.create_user(user)
            return created_user is not None
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            return False

    def update_last_login(self, username: str) -> bool:
        """Update user's last login timestamp (backward compatible)"""
        try:
            # First get the user to find their user_id
            user = self.user_repo.get_user_by_username(username)
            if user:
                return self.user_repo.update_last_login(str(user.user_id))
            return False
        except Exception as e:
            logger.error(f"Failed to update last login for {username}: {e}")
            return False

    # === Session Management (Backward Compatible) ===
    
    def get_or_create_session(self, user_id: str) -> str:
        """Get existing session or create new one (backward compatible)"""
        # Try to get existing active session
        sessions = self.session_repo.get_user_sessions(user_id)
        active_sessions = [s for s in sessions if s.is_active]
        
        if active_sessions:
            return str(active_sessions[0].session_id)  # Convert UUID to string
        
        # Create new session
        session = ChatSession(user_id=user_id)
        created_session = self.session_repo.create_session(session)
        return str(created_session.session_id)  # Convert UUID to string

    def get_user_sessions(self, user_id: str) -> List[Dict]:
        """Get user sessions (backward compatible)"""
        sessions = self.session_repo.get_user_sessions(user_id)
        return [session.to_dict() for session in sessions]

    def get_session_messages(self, session_id: str) -> List[Dict]:
        """Get session messages (backward compatible)"""
        messages = self.message_repo.get_session_messages(session_id)
        return [message.to_dict() for message in messages]

    # === Message Management (Backward Compatible) ===
    
    def add_message(self, session_id: str, user_id: str, user_message: str, 
                   bot_response: str, source: str = "unknown") -> bool:
        """Add a chat message (backward compatible)"""
        try:
            message = ChatMessage(
                session_id=session_id,
                user_id=user_id,
                message=user_message,  # Use new field name
                response=bot_response,  # Use new field name
                message_type="user"
            )
            created_message = self.message_repo.create_message(message)
            
            return created_message is not None
        except Exception as e:
            logger.error(f"Failed to add message: {e}")
            return False

    # === Health and Statistics ===
    
    def health_check(self) -> Dict:
        """Database health check"""
        return self.connection_service.health_check()

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        user_stats = self.user_repo.get_user_stats()
        db_info = self.connection_service.get_database_info()
        
        return {
            **user_stats,
            "database_info": db_info,
            "architecture": "modular"
        }

    # === New Methods (Enhanced Functionality) ===
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username (returns User object)"""
        return self.user_repo.get_user_by_username(username)

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID (returns User object)"""
        return self.user_repo.get_user_by_id(user_id)

    def update_user_last_login(self, user_id: str) -> bool:
        """Update user's last login timestamp"""
        return self.user_repo.update_last_login(user_id)

    def get_recent_messages(self, user_id: str, limit: int = 50) -> List[ChatMessage]:
        """Get recent messages for a user"""
        return self.message_repo.get_user_messages(user_id, limit)

    def get_chat_history(self, user_id: str, limit: int = 20) -> List[Dict]:
        """Get chat history for a user (backward compatible)"""
        try:
            messages = self.message_repo.get_user_messages(user_id, limit)
            return [message.to_dict() for message in messages]
        except Exception as e:
            logger.error(f"Failed to get chat history: {e}")
            return []

    def clear_chat_history(self, user_id: str) -> bool:
        """Clear chat history for a user"""
        try:
            return self.message_repo.clear_user_messages(user_id)
        except Exception as e:
            logger.error(f"Failed to clear chat history: {e}")
            return False


# Create singleton instance
db_manager = DatabaseManager()
