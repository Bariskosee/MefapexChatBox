"""
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
            INSERT INTO chat_sessions (session_id, user_id, session_name, is_active, metadata)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING session_id, created_at, updated_at
        """
        
        try:
            # Convert metadata to JSON
            import json
            metadata_json = json.dumps(session.metadata) if session.metadata else '{}'
            
            result = self.connection_service.execute_query(
                query,
                (session.session_id, session.user_id, session.session_name, session.is_active, metadata_json),
                fetch_one=True
            )
            
            if result:
                session.session_id = result['session_id']
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
            SELECT session_id, user_id, session_name, created_at, updated_at, is_active, metadata
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
            SELECT session_id, user_id, session_name, created_at, updated_at, is_active, metadata
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
            SET updated_at = CURRENT_TIMESTAMP, session_name = %s, is_active = %s, metadata = %s
            WHERE session_id = %s
        """
        
        try:
            # Convert metadata to JSON
            import json
            metadata_json = json.dumps(session.metadata) if session.metadata else '{}'
            
            rows_affected = self.connection_service.execute_query(
                query, (session.session_name, session.is_active, metadata_json, session.session_id),
                fetch_all=False
            )
            return rows_affected > 0
            
        except Exception as e:
            logger.error(f"❌ Failed to update session {session.session_id}: {e}")
            return False


# Create singleton instance
session_repository = SessionRepository()
