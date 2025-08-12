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
            INSERT INTO chat_messages (message_id, session_id, user_id, message, response, metadata)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING message_id, timestamp
        """
        
        try:
            # Generate message_id if not provided
            if not message.message_id:
                import uuid
                message.message_id = str(uuid.uuid4())
            
            # Convert metadata to JSON if it's a dict
            metadata_json = message.metadata
            if isinstance(metadata_json, dict):
                import json
                metadata_json = json.dumps(metadata_json)
            
            result = self.connection_service.execute_query(
                query,
                (message.message_id, message.session_id, message.user_id, message.message, 
                 message.response, metadata_json),
                fetch_one=True
            )
            
            if result:
                message.message_id = result['message_id']
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
            SELECT message_id, session_id, user_id, message, response, message_type,
                   timestamp, metadata
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
            SELECT message_id, session_id, user_id, message, response, message_type,
                   timestamp, metadata
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

    def clear_user_messages(self, user_id: str) -> bool:
        """Clear all messages for a user"""
        query = "DELETE FROM chat_messages WHERE user_id = %s"
        
        try:
            self.connection_service.execute_query(query, (user_id,))
            logger.info(f"✅ Cleared messages for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to clear messages for user {user_id}: {e}")
            return False


# Create singleton instance
message_repository = MessageRepository()
