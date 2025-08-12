"""
🚀 MEFAPEX Database Manager (Fixed Version)
Simple SQLite-based database manager for chat history functionality
"""

import os
import sqlite3
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Simplified Database Manager for MEFAPEX Chat System"""
    
    def __init__(self):
        self.db_path = os.path.join(os.getcwd(), "mefapex.db")
        self.connection = None
        self._init_connection()
        logger.info(f"📊 Database Manager initialized with SQLite: {self.db_path}")

    def _init_connection(self):
        """Initialize SQLite connection"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else '.', exist_ok=True)
            
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row  # Enable column access by name
            logger.info("✅ SQLite connection established")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize database: {e}")
            raise

    def authenticate_user(self, username: str) -> Optional[Dict]:
        """Authenticate user and return user data"""
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                "SELECT id, username, hashed_password, email, is_active, last_login FROM users WHERE username = ?",
                (username,)
            )
            result = cursor.fetchone()
            
            if result:
                return {
                    "id": result[0],
                    "username": result[1],
                    "password_hash": result[2],  # Map to password_hash for compatibility
                    "hashed_password": result[2],  # Keep original field name
                    "email": result[3],
                    "is_active": bool(result[4]),
                    "last_login": result[5]
                }
            return None
            
        except Exception as e:
            logger.error(f"❌ Database authentication error: {e}")
            return None

    def update_last_login(self, username: str):
        """Update user's last login timestamp"""
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE username = ?",
                (username,)
            )
            self.connection.commit()
        except Exception as e:
            logger.error(f"❌ Failed to update last login: {e}")

    def get_or_create_session(self, user_id: str, force_new: bool = False) -> str:
        """Get existing session or create new one"""
        try:
            cursor = self.connection.cursor()
            
            if not force_new:
                # Try to get existing session
                cursor.execute(
                    "SELECT session_id FROM chat_sessions WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
                    (user_id,)
                )
                result = cursor.fetchone()
                if result:
                    return result[0]
            
            # Create new session
            session_id = str(uuid.uuid4())
            cursor.execute(
                "INSERT INTO chat_sessions (session_id, user_id) VALUES (?, ?)",
                (session_id, user_id)
            )
            self.connection.commit()
            
            logger.info(f"📝 Created new session: {session_id} for user: {user_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"❌ Session creation error: {e}")
            # Return fallback session ID
            return f"fallback_{user_id}_{int(datetime.now().timestamp())}"

    def add_message(self, session_id: str, user_id: str, user_message: str, 
                   bot_response: str, source: str = "unknown"):
        """Add a chat message to the database"""
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                """INSERT INTO chat_messages 
                   (session_id, user_id, user_message, bot_response, source) 
                   VALUES (?, ?, ?, ?, ?)""",
                (session_id, user_id, user_message, bot_response, source)
            )
            self.connection.commit()
            logger.debug(f"💬 Message saved: {len(user_message)} chars -> {len(bot_response)} chars")
            
        except Exception as e:
            logger.error(f"❌ Failed to save message: {e}")
            raise

    def get_chat_history(self, user_id: str, limit: int = 20) -> List[Dict]:
        """Get chat history for user"""
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                """SELECT user_message, bot_response, source, timestamp 
                   FROM chat_messages 
                   WHERE user_id = ? 
                   ORDER BY timestamp DESC 
                   LIMIT ?""",
                (user_id, limit)
            )
            
            results = cursor.fetchall()
            return [
                {
                    "user_message": row[0],
                    "bot_response": row[1],
                    "source": row[2],
                    "timestamp": row[3],
                    "created_at": row[3]  # For API compatibility
                }
                for row in results
            ]
            
        except Exception as e:
            logger.error(f"❌ Failed to get chat history: {e}")
            return []

    def get_user_sessions(self, user_id: str) -> List[Dict]:
        """Get user's chat sessions"""
        try:
            cursor = self.connection.cursor()
            
            # Get sessions with message counts
            cursor.execute(
                """SELECT s.session_id, s.created_at, COUNT(m.id) as message_count,
                          MAX(m.timestamp) as last_message_time
                   FROM chat_sessions s
                   LEFT JOIN chat_messages m ON s.session_id = m.session_id
                   WHERE s.user_id = ?
                   GROUP BY s.session_id, s.created_at
                   ORDER BY s.created_at DESC""",
                (user_id,)
            )
            
            results = cursor.fetchall()
            sessions = []
            
            for row in results:
                # Get first message for preview
                cursor.execute(
                    "SELECT user_message FROM chat_messages WHERE session_id = ? ORDER BY timestamp ASC LIMIT 1",
                    (row[0],)
                )
                first_msg = cursor.fetchone()
                preview = first_msg[0] if first_msg else "Boş sohbet"
                
                sessions.append({
                    "sessionId": row[0],
                    "session_id": row[0],
                    "created_at": row[1],
                    "startedAt": row[1],
                    "messageCount": row[2],
                    "message_count": row[2],
                    "lastMessageTime": row[3],
                    "preview": preview[:50] + "..." if len(preview) > 50 else preview
                })
            
            return sessions
            
        except Exception as e:
            logger.error(f"❌ Failed to get user sessions: {e}")
            return []

    def get_session_messages(self, session_id: str) -> List[Dict]:
        """Get all messages from a specific session"""
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                """SELECT user_message, bot_response, source, timestamp 
                   FROM chat_messages 
                   WHERE session_id = ? 
                   ORDER BY timestamp ASC""",
                (session_id,)
            )
            
            results = cursor.fetchall()
            messages = []
            
            for row in results:
                messages.append({
                    "user_message": row[0],
                    "bot_response": row[1],
                    "source": row[2],
                    "timestamp": row[3]
                })
            
            return messages
            
        except Exception as e:
            logger.error(f"❌ Failed to get session messages: {e}")
            return []

    def clear_chat_history(self, user_id: str):
        """Clear all chat history for user"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM chat_messages WHERE user_id = ?", (user_id,))
            cursor.execute("DELETE FROM chat_sessions WHERE user_id = ?", (user_id,))
            self.connection.commit()
            logger.info(f"🗑️ Cleared chat history for user: {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to clear chat history: {e}")
            raise

    def get_stats(self) -> Dict:
        """Get database statistics"""
        try:
            cursor = self.connection.cursor()
            
            # Get counts
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM chat_sessions")
            session_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM chat_messages")
            message_count = cursor.fetchone()[0]
            
            return {
                "users": user_count,
                "sessions": session_count,
                "messages": message_count,
                "database_path": self.db_path
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get stats: {e}")
            return {"error": str(e)}

    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("📊 Database connection closed")

# Global instance
db_manager = None

def get_database_manager() -> DatabaseManager:
    """Get or create database manager instance"""
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager()
    return db_manager

# Initialize global instance
db_manager = get_database_manager()
