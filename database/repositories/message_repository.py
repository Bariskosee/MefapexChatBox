"""
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
