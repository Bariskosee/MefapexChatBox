"""
🎯 Database Manager - Unified Interface (Facade Pattern)
======================================================

Unified interface that provides all database operations through a single entry point.
This maintains backward compatibility while using the new modular architecture.
"""

import logging
from datetime import datetime
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
                        last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT TRUE,
                        message_count INTEGER DEFAULT 0
                    )
                """)
                
                # Create chat_messages table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS chat_messages (
                        id SERIAL PRIMARY KEY,
                        message_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
                        session_id VARCHAR(255) NOT NULL,
                        user_id VARCHAR(255) NOT NULL,
                        user_message TEXT NOT NULL,
                        bot_response TEXT NOT NULL,
                        message_type VARCHAR(50) DEFAULT 'user',
                        source VARCHAR(50) DEFAULT 'unknown',
                        timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        metadata JSONB
                    )
                """)
                
                # Create indexes
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions(user_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_chat_sessions_session_id ON chat_sessions(session_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages(session_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_chat_messages_user_id ON chat_messages(user_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_chat_messages_message_id ON chat_messages(message_id)')
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

    def get_or_create_session_by_id(self, user_id: str, session_id: str) -> str:
        """Get existing session by ID or create new one with specific ID"""
        # Try to get existing session first
        existing_session = self.session_repo.get_session_by_id(session_id)
        if existing_session:
            return str(existing_session.session_id)
        
        # Create new session with the specified ID
        try:
            session = ChatSession(session_id=session_id, user_id=user_id)
            created_session = self.session_repo.create_session(session)
            return str(created_session.session_id)
        except Exception as e:
            logger.error(f"Failed to create session {session_id}: {e}")
            # Fallback to creating a session with auto-generated ID
            session = ChatSession(user_id=user_id)
            created_session = self.session_repo.create_session(session)
            return str(created_session.session_id)

    def get_user_sessions(self, user_id: str) -> List[Dict]:
        """Get user sessions (backward compatible)"""
        sessions = self.session_repo.get_user_sessions(user_id)
        enriched_sessions = []
        
        for session in sessions:
            session_dict = session.to_dict()
            
            # Get message count for this session
            session_messages = self.message_repo.get_session_messages(str(session.session_id))
            session_dict['message_count'] = len(session_messages)
            session_dict['messageCount'] = len(session_messages)  # Alternative field name
            
            # Add session ID in multiple formats for compatibility
            session_dict['sessionId'] = str(session.session_id)
            session_dict['session_id'] = str(session.session_id)
            
            # Add startedAt field for compatibility
            session_dict['startedAt'] = session.created_at
            
            # Generate a preview from the first message
            if session_messages:
                first_message = session_messages[0]
                preview_text = first_message.message[:50] + "..." if len(first_message.message) > 50 else first_message.message
                session_dict['preview'] = preview_text
            else:
                session_dict['preview'] = "Boş sohbet"
            
            # Add messages for compatibility
            session_dict['messages'] = [msg.to_dict() for msg in session_messages]
            
            enriched_sessions.append(session_dict)
        
        # Sort by creation date, newest first
        enriched_sessions.sort(key=lambda x: x.get('created_at', datetime.min), reverse=True)
        
        return enriched_sessions

    def get_session_messages(self, session_id: str) -> List[Dict]:
        """Get session messages (backward compatible)"""
        messages = self.message_repo.get_session_messages(session_id)
        return [message.to_dict() for message in messages]

    # === Message Management (Backward Compatible) ===
    
    def add_message(self, session_id: str, user_id: str, user_message: str, 
                   bot_response: str, source: str = "unknown") -> bool:
        """Add a chat message (backward compatible)"""
        try:
            # First ensure the session exists
            self.get_or_create_session_by_id(user_id, session_id)
            
            message = ChatMessage(
                session_id=session_id,
                user_id=user_id,
                message=user_message,  # Use new field name
                response=bot_response,  # Use new field name
                message_type="user",
                metadata={"source": source}  # Store source in metadata
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
            # Convert to backward compatible format
            chat_history = []
            for message in messages:
                chat_dict = {
                    "message_id": message.message_id,
                    "session_id": message.session_id,
                    "user_id": message.user_id,
                    "user_message": message.message,  # Convert message -> user_message
                    "bot_response": message.response,  # Convert response -> bot_response
                    "source": message.get_metadata("source", "unknown"),  # Extract source from metadata
                    "timestamp": message.timestamp,
                    "metadata": message.metadata
                }
                chat_history.append(chat_dict)
            return chat_history
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

    def delete_old_sessions(self, user_id: str, keep_count: int = 15) -> int:
        """Delete old sessions keeping only specified count"""
        try:
            with self.connection_service.get_cursor() as cursor:
                # Get sessions to delete (keep most recent ones)
                cursor.execute(
                    """SELECT session_id FROM chat_sessions 
                       WHERE user_id = %s 
                       ORDER BY created_at DESC OFFSET %s""",
                    (user_id, keep_count)
                )
                old_sessions = cursor.fetchall()
                
                if not old_sessions:
                    logger.info(f"No old sessions to delete for user {user_id}")
                    return 0
                
                # Delete old sessions and their messages
                old_session_ids = [str(session['session_id']) for session in old_sessions]
                
                # Delete messages first
                cursor.execute(
                    "DELETE FROM chat_messages WHERE session_id = ANY(%s)",
                    (old_session_ids,)
                )
                messages_deleted = cursor.rowcount
                
                # Delete sessions
                cursor.execute(
                    "DELETE FROM chat_sessions WHERE session_id = ANY(%s)",
                    (old_session_ids,)
                )
                sessions_deleted = cursor.rowcount
                
                logger.info(f"🧹 Deleted {sessions_deleted} old sessions and {messages_deleted} messages for user {user_id}")
                return sessions_deleted
                
        except Exception as e:
            logger.error(f"Failed to delete old sessions for user {user_id}: {e}")
            return 0


# Create singleton instance
db_manager = DatabaseManager()
