#!/usr/bin/env python3
"""
🛠️ Database Refactoring Script
============================

This script creates the remaining database files for the modular architecture.
"""

import os

# Define the base directory
base_dir = "/Users/bariskose/Downloads/MefapexChatBox-main/database"

# Session Repository
session_repository_content = '''"""
💬 Session Repository for MEFAPEX Chat System
============================================

Data access layer for chat session management operations.
"""

import logging
from typing import List, Optional, Dict, Any
from ..models.session import ChatSession
from ..services.connection_service import connection_service

logger = logging.getLogger(__name__)


class SessionRepository:
    """Session data access repository"""

    def __init__(self):
        self.connection_service = connection_service

    def create_session(self, session: ChatSession) -> ChatSession:
        """Create a new chat session"""
        query = """
            INSERT INTO chat_sessions (session_id, user_id, is_active, message_count)
            VALUES (%s, %s, %s, %s)
            RETURNING id, created_at, updated_at
        """
        
        try:
            result = self.connection_service.execute_query(
                query,
                (session.session_id, session.user_id, session.is_active, session.message_count),
                fetch_one=True
            )
            
            if result:
                session.id = result['id']
                session.created_at = result['created_at']
                session.updated_at = result['updated_at']
                logger.info(f"✅ Session created: {session.session_id}")
                return session
            else:
                raise RuntimeError("Failed to create session")
                
        except Exception as e:
            logger.error(f"❌ Failed to create session: {e}")
            raise

    def get_session_by_id(self, session_id: str) -> Optional[ChatSession]:
        """Get session by ID"""
        query = """
            SELECT id, session_id, user_id, created_at, updated_at, is_active, message_count
            FROM chat_sessions 
            WHERE session_id = %s
        """
        
        try:
            result = self.connection_service.execute_query(query, (session_id,), fetch_one=True)
            if result:
                return ChatSession.from_dict(dict(result))
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get session {session_id}: {e}")
            return None

    def get_user_sessions(self, user_id: str) -> List[ChatSession]:
        """Get all sessions for a user"""
        query = """
            SELECT id, session_id, user_id, created_at, updated_at, is_active, message_count
            FROM chat_sessions 
            WHERE user_id = %s 
            ORDER BY updated_at DESC
        """
        
        try:
            results = self.connection_service.execute_query(query, (user_id,))
            return [ChatSession.from_dict(dict(row)) for row in results]
            
        except Exception as e:
            logger.error(f"❌ Failed to get sessions for user {user_id}: {e}")
            return []

    def update_session(self, session: ChatSession) -> bool:
        """Update session information"""
        query = """
            UPDATE chat_sessions 
            SET updated_at = CURRENT_TIMESTAMP, is_active = %s, message_count = %s
            WHERE session_id = %s
        """
        
        try:
            rows_affected = self.connection_service.execute_query(
                query, (session.is_active, session.message_count, session.session_id),
                fetch_all=False
            )
            return rows_affected > 0
            
        except Exception as e:
            logger.error(f"❌ Failed to update session {session.session_id}: {e}")
            return False


# Create singleton instance
session_repository = SessionRepository()
'''

# Message Repository
message_repository_content = '''"""
💬 Message Repository for MEFAPEX Chat System
============================================

Data access layer for chat message operations.
"""

import logging
from typing import List, Optional, Dict, Any
from ..models.message import ChatMessage
from ..services.connection_service import connection_service

logger = logging.getLogger(__name__)


class MessageRepository:
    """Message data access repository"""

    def __init__(self):
        self.connection_service = connection_service

    def create_message(self, message: ChatMessage) -> ChatMessage:
        """Create a new chat message"""
        query = """
            INSERT INTO chat_messages (session_id, user_id, user_message, bot_response, source, metadata)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, timestamp, created_at
        """
        
        try:
            result = self.connection_service.execute_query(
                query,
                (message.session_id, message.user_id, message.user_message, 
                 message.bot_response, message.source, message.metadata),
                fetch_one=True
            )
            
            if result:
                message.id = result['id']
                message.timestamp = result['timestamp']
                message.created_at = result['created_at']
                logger.info(f"✅ Message created: {message.id}")
                return message
            else:
                raise RuntimeError("Failed to create message")
                
        except Exception as e:
            logger.error(f"❌ Failed to create message: {e}")
            raise

    def get_session_messages(self, session_id: str) -> List[ChatMessage]:
        """Get all messages for a session"""
        query = """
            SELECT id, session_id, user_id, user_message, bot_response, source, 
                   timestamp, created_at, metadata
            FROM chat_messages 
            WHERE session_id = %s 
            ORDER BY timestamp ASC
        """
        
        try:
            results = self.connection_service.execute_query(query, (session_id,))
            return [ChatMessage.from_dict(dict(row)) for row in results]
            
        except Exception as e:
            logger.error(f"❌ Failed to get messages for session {session_id}: {e}")
            return []

    def get_user_messages(self, user_id: str, limit: int = 100) -> List[ChatMessage]:
        """Get recent messages for a user"""
        query = """
            SELECT id, session_id, user_id, user_message, bot_response, source, 
                   timestamp, created_at, metadata
            FROM chat_messages 
            WHERE user_id = %s 
            ORDER BY timestamp DESC 
            LIMIT %s
        """
        
        try:
            results = self.connection_service.execute_query(query, (user_id, limit))
            return [ChatMessage.from_dict(dict(row)) for row in results]
            
        except Exception as e:
            logger.error(f"❌ Failed to get messages for user {user_id}: {e}")
            return []


# Create singleton instance
message_repository = MessageRepository()
'''

# Repositories __init__.py
repositories_init_content = '''"""
Database repositories package
"""

from .user_repository import UserRepository, user_repository
from .session_repository import SessionRepository, session_repository
from .message_repository import MessageRepository, message_repository

__all__ = [
    'UserRepository', 'user_repository',
    'SessionRepository', 'session_repository', 
    'MessageRepository', 'message_repository'
]
'''

# Database Manager (Facade)
manager_content = '''"""
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
                "id": user.id,
                "user_id": user.user_id,
                "username": user.username,
                "password_hash": user.hashed_password,
                "hashed_password": user.hashed_password,
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
                hashed_password=password_hash,
                email=email
            )
            created_user = self.user_repo.create_user(user)
            return created_user is not None
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            return False

    # === Session Management (Backward Compatible) ===
    
    def get_or_create_session(self, user_id: str) -> str:
        """Get existing session or create new one (backward compatible)"""
        # Try to get existing active session
        sessions = self.session_repo.get_user_sessions(user_id)
        active_sessions = [s for s in sessions if s.is_active]
        
        if active_sessions:
            return active_sessions[0].session_id
        
        # Create new session
        session = ChatSession(user_id=user_id)
        created_session = self.session_repo.create_session(session)
        return created_session.session_id

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
                user_message=user_message,
                bot_response=bot_response,
                source=source
            )
            created_message = self.message_repo.create_message(message)
            
            # Update session message count
            session = self.session_repo.get_session_by_id(session_id)
            if session:
                session.increment_message_count()
                self.session_repo.update_session(session)
            
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


# Create singleton instance
db_manager = DatabaseManager()
'''

# Write all files
files_to_create = [
    ("repositories/session_repository.py", session_repository_content),
    ("repositories/message_repository.py", message_repository_content),
    ("repositories/__init__.py", repositories_init_content),
    ("manager.py", manager_content),
]

print("🛠️ Creating database files...")

for file_path, content in files_to_create:
    full_path = os.path.join(base_dir, file_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Created: {file_path}")

# Update database/__init__.py
init_content = '''"""
Database package for MEFAPEX Chat System
"""

from .manager import DatabaseManager, db_manager

__all__ = ['DatabaseManager', 'db_manager']
'''

with open(os.path.join(base_dir, "__init__.py"), 'w', encoding='utf-8') as f:
    f.write(init_content)

print("✅ Updated: __init__.py")
print("🎉 Database refactoring completed!")
print()
print("📊 File structure created:")
print(f"📁 {base_dir}/")
print("  ├── __init__.py")
print("  ├── manager.py (Unified interface)")
print("  ├── models/")
print("  │   ├── user.py")
print("  │   ├── session.py") 
print("  │   ├── message.py")
print("  │   └── __init__.py")
print("  ├── repositories/")
print("  │   ├── user_repository.py")
print("  │   ├── session_repository.py")
print("  │   ├── message_repository.py")
print("  │   └── __init__.py")
print("  └── services/")
print("      ├── connection_service.py")
print("      └── __init__.py")
