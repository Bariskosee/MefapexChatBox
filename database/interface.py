"""
🎯 MEFAPEX Database Interface - Unified Database Operations
Eliminates code duplication across different database managers
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class DatabaseInterface(ABC):
    """
    Abstract interface for all database operations
    Provides unified API across SQLite and PostgreSQL implementations
    """
    
    # === Connection Management ===
    @abstractmethod
    def connect(self) -> bool:
        """Establish database connection"""
        pass
        
    @abstractmethod
    def disconnect(self) -> None:
        """Close database connection"""
        pass
        
    @abstractmethod
    def test_connection(self) -> bool:
        """Test if database connection is working"""
        pass
    
    # === User Management ===
    @abstractmethod
    def create_user(self, username: str, email: str, password_hash: str) -> str:
        """Create new user and return user_id"""
        pass
        
    @abstractmethod
    def get_user(self, username: str) -> Optional[Dict]:
        """Get user by username"""
        pass
        
    @abstractmethod
    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """Get user by user_id"""
        pass
    
    # === Session Management ===
    @abstractmethod
    def create_session(self, user_id: str, session_id: Optional[str] = None) -> str:
        """Create new chat session and return session_id"""
        pass
        
    @abstractmethod
    def get_user_sessions(self, user_id: str, limit: int = 15) -> List[Dict]:
        """Get all sessions for a user"""
        pass
        
    @abstractmethod
    def get_session_messages(self, session_id: str) -> List[Dict]:
        """Get all messages in a session"""
        pass
        
    @abstractmethod
    def delete_old_sessions(self, user_id: str, keep_count: int = 15) -> int:
        """Delete old sessions keeping only specified count"""
        pass
    
    # === Message Management ===
    @abstractmethod
    def add_message(self, session_id: str, user_id: str, user_message: str, 
                   bot_response: str, source: str = "unknown") -> bool:
        """
        Add a chat message to database
        
        Args:
            session_id: Session identifier
            user_id: User identifier  
            user_message: User's message
            bot_response: AI response
            source: Message source (web, api, etc.)
            
        Returns:
            bool: Success status
        """
        pass
        
    @abstractmethod
    def get_chat_history(self, user_id: str, limit: int = 20) -> List[Dict]:
        """Get recent chat history for user"""
        pass
        
    @abstractmethod
    def save_session_bulk(self, session_data: Dict) -> bool:
        """Save multiple messages in a session at once"""
        pass
    
    # === Health Check ===
    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check"""
        pass

class DatabaseFactory:
    """
    Factory class to create appropriate database manager
    Eliminates direct instantiation of specific managers
    """
    
    @staticmethod
    def create_manager(db_type: str, config: Dict) -> DatabaseInterface:
        """
        Create database manager based on type
        
        Args:
            db_type: 'postgresql' or 'sqlite'
            config: Database configuration
            
        Returns:
            DatabaseInterface: Appropriate manager instance
        """
        if db_type.lower() == 'postgresql':
            from postgresql_manager import PostgreSQLManager
            return PostgreSQLManager(config)
        elif db_type.lower() == 'sqlite':
            from database.manager import DatabaseManager
            return DatabaseManager(config)
        else:
            raise ValueError(f"Unsupported database type: {db_type}")

class DatabaseOperationsMixin:
    """
    Mixin class providing common database operations
    Eliminates code duplication in handlers
    """
    
    def save_chat_message(self, db_manager: DatabaseInterface, session_id: str, 
                         user_id: str, user_message: str, bot_response: str, 
                         source: str = "unknown") -> bool:
        """
        Unified method to save chat message
        
        Usage:
            # Instead of duplicating this logic everywhere:
            try:
                db_manager.add_message(session_id, user_id, message, response, source)
                logger.info("Message saved")
            except Exception as e:
                logger.error(f"Save failed: {e}")
                
            # Use this:
            self.save_chat_message(db_manager, session_id, user_id, message, response, source)
        """
        try:
            success = db_manager.add_message(
                session_id=session_id,
                user_id=user_id, 
                user_message=user_message,
                bot_response=bot_response,
                source=source
            )
            
            if success:
                logger.info(f"Chat message saved for user {user_id} in session {session_id}")
                return True
            else:
                logger.warning(f"Failed to save message for user {user_id}")
                return False
                
        except Exception as db_error:
            logger.error(f"Database error while saving message: {db_error}")
            return False
    
    def create_user_session(self, db_manager: DatabaseInterface, user_id: str, 
                           session_id: Optional[str] = None) -> Optional[str]:
        """
        Unified method to create user session
        """
        try:
            created_session_id = db_manager.create_session(user_id, session_id)
            logger.info(f"Session created: {created_session_id} for user {user_id}")
            return created_session_id
        except Exception as e:
            logger.error(f"Failed to create session for user {user_id}: {e}")
            return None
    
    def get_user_chat_history(self, db_manager: DatabaseInterface, user_id: str, 
                             limit: int = 20) -> List[Dict]:
        """
        Unified method to get user chat history
        """
        try:
            history = db_manager.get_chat_history(user_id, limit)
            logger.debug(f"Retrieved {len(history)} chat history items for user {user_id}")
            return history
        except Exception as e:
            logger.error(f"Failed to get chat history for user {user_id}: {e}")
            return []

# Utility functions for common operations
def ensure_session_exists(db_manager: DatabaseInterface, session_id: str, user_id: str) -> bool:
    """
    Ensure session exists, create if missing
    Common pattern used across multiple files
    """
    try:
        # Try to get session info first
        sessions = db_manager.get_user_sessions(user_id, limit=1)
        for session in sessions:
            if session.get('session_id') == session_id:
                return True
        
        # Session doesn't exist, create it
        created_session = db_manager.create_session(user_id, session_id)
        return created_session == session_id
        
    except Exception as e:
        logger.error(f"Failed to ensure session exists: {e}")
        return False

def cleanup_old_sessions(db_manager: DatabaseInterface, user_id: str, max_sessions: int = 15) -> int:
    """
    Clean up old sessions for user
    Common maintenance operation
    """
    try:
        deleted_count = db_manager.delete_old_sessions(user_id, max_sessions)
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old sessions for user {user_id}")
        return deleted_count
    except Exception as e:
        logger.error(f"Failed to cleanup sessions for user {user_id}: {e}")
        return 0
