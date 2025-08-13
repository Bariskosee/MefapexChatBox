"""
🎯 MEFAPEX Database Utilities
Common database operations to eliminate code duplication
"""

import logging
from typing import Optional, Dict, Any
from database.interface import DatabaseInterface, DatabaseOperationsMixin

logger = logging.getLogger(__name__)

class DatabaseHelper(DatabaseOperationsMixin):
    """
    Helper class providing consolidated database operations
    Eliminates code duplication across handlers
    """
    
    def __init__(self, db_manager: DatabaseInterface):
        self.db_manager = db_manager
    
    def save_chat_interaction(self, user_id: str, message: str, response: str, 
                             source: str = "unknown", session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Complete chat interaction save with session management
        
        Returns:
            Dict with status, session_id, and any errors
        """
        try:
            # Get or create session
            if not session_id:
                session_id = self.get_or_create_user_session(user_id)
            
            # Save message
            success = self.save_chat_message(
                self.db_manager, session_id, user_id, message, response, source
            )
            
            return {
                "success": success,
                "session_id": session_id,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Failed to save chat interaction: {e}")
            return {
                "success": False, 
                "session_id": session_id,
                "error": str(e)
            }
    
    def get_or_create_user_session(self, user_id: str) -> str:
        """
        Get existing session or create new one for user
        """
        try:
            # Check if there's an active session
            sessions = self.db_manager.get_user_sessions(user_id, limit=1)
            if sessions:
                # Return most recent session
                return sessions[0].get('session_id', sessions[0].get('id'))
            
            # Create new session
            return self.create_user_session(self.db_manager, user_id)
            
        except Exception as e:
            logger.error(f"Failed to get/create session for user {user_id}: {e}")
            # Return fallback session ID
            import time
            return f"fallback_{user_id}_{int(time.time())}"

def get_database_helper(db_manager: DatabaseInterface) -> DatabaseHelper:
    """
    Factory function to get database helper instance
    """
    return DatabaseHelper(db_manager)
