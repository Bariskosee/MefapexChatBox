import sqlite3
from datetime import datetime
from typing import List, Dict, Optional

class DatabaseManager:
    def __init__(self, db_path="mefapex.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    user_id TEXT UNIQUE NOT NULL,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    hashed_password TEXT NOT NULL,
                    full_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id INTEGER PRIMARY KEY,
                    session_id TEXT UNIQUE NOT NULL,
                    user_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_message TEXT,
                    bot_response TEXT,
                    source TEXT
                )
            """)
    
    def get_or_create_session(self, user_id: str) -> str:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("SELECT session_id FROM chat_sessions WHERE user_id = ?", (user_id,))
            row = cur.fetchone()
            if row:
                return row[0]
            # Create new session
            import uuid
            session_id = str(uuid.uuid4())
            cur.execute("INSERT INTO chat_sessions (session_id, user_id) VALUES (?, ?)", (session_id, user_id))
            conn.commit()
            return session_id
    
    def add_message(self, session_id: str, user_id: str, user_message: str, bot_response: str, source: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO chat_messages (session_id, user_id, user_message, bot_response, source) VALUES (?, ?, ?, ?, ?)",
                (session_id, user_id, user_message, bot_response, source)
            )
            conn.commit()
    
    def get_chat_history(self, user_id: str, limit: int = 20) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT user_message, bot_response, source, timestamp FROM chat_messages WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
                (user_id, limit)
            )
            rows = cur.fetchall()
            # Return in chronological order
            return [
                {
                    "user_message": row[0],
                    "bot_response": row[1],
                    "source": row[2],
                    "timestamp": row[3]
                }
                for row in reversed(rows)
            ]
    
    def clear_chat_history(self, user_id: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM chat_messages WHERE user_id = ?", (user_id,))
            conn.commit() 