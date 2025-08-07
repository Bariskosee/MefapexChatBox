"""
🚀 Async Database Pool for High Performance SQLite Operations
Replaces blocking sqlite3 with aiosqlite for proper async support
"""

import aiosqlite
import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
import os
import uuid
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class PoolStats:
    """Database pool statistics"""
    active_connections: int = 0
    total_queries: int = 0
    average_query_time: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0

class AsyncDatabasePool:
    """
    🏊‍♂️ High-performance async database pool for SQLite
    - Non-blocking async operations
    - Connection pooling and reuse
    - Query result caching
    - Performance monitoring
    """
    
    def __init__(self, db_path: str = "mefapex_chat.db", max_connections: int = 10):
        self.db_path = db_path
        self.max_connections = max_connections
        self._connection_pool = asyncio.Queue(maxsize=max_connections)
        self._pool_initialized = False
        self._stats = PoolStats()
        self._query_cache = {}  # Simple query result cache
        self._cache_ttl = timedelta(minutes=5)
        self._lock = asyncio.Lock()
        self.created_at = datetime.utcnow()
        
    async def initialize_pool(self):
        """Initialize the connection pool with pre-created connections"""
        if self._pool_initialized:
            return
            
        logger.info(f"🔧 Initializing async database pool with {self.max_connections} connections")
        
        # Create database file and tables if not exists
        await self._create_tables()
        
        # Pre-populate connection pool
        for _ in range(self.max_connections):
            conn = await aiosqlite.connect(
                self.db_path,
                timeout=30.0,
                isolation_level=None  # Autocommit mode for better performance
            )
            # Enable WAL mode for better concurrent access
            await conn.execute("PRAGMA journal_mode=WAL")
            await conn.execute("PRAGMA synchronous=NORMAL")
            await conn.execute("PRAGMA cache_size=10000")
            await conn.execute("PRAGMA temp_store=MEMORY")
            
            await self._connection_pool.put(conn)
            
        self._pool_initialized = True
        logger.info("✅ Async database pool initialized successfully")
    
    async def _create_tables(self):
        """Create necessary tables if they don't exist"""
        async with aiosqlite.connect(self.db_path) as db:
            # Chat sessions table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            """)
            
            # Chat messages table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    user_message TEXT NOT NULL,
                    bot_response TEXT NOT NULL,
                    source TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    response_time_ms REAL,
                    FOREIGN KEY (session_id) REFERENCES chat_sessions (session_id)
                )
            """)
            
            # Create indexes for better performance
            await db.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON chat_sessions(user_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_messages_session_id ON chat_messages(session_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_messages_user_id ON chat_messages(user_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON chat_messages(timestamp)")
            
            await db.commit()
    
    @asynccontextmanager
    async def get_connection(self):
        """
        🔌 Get a connection from the pool
        Automatically handles connection lifecycle
        """
        if not self._pool_initialized:
            await self.initialize_pool()
            
        # Get connection from pool
        conn = await self._connection_pool.get()
        self._stats.active_connections += 1
        
        try:
            yield conn
        finally:
            # Return connection to pool
            await self._connection_pool.put(conn)
            self._stats.active_connections -= 1
    
    async def execute_query(
        self, 
        query: str, 
        params: tuple = (),
        cache_key: Optional[str] = None,
        cache_result: bool = False
    ) -> List[Dict[str, Any]]:
        """
        ⚡ Execute a SELECT query with optional caching
        """
        start_time = asyncio.get_event_loop().time()
        
        # Check cache first
        if cache_key and cache_result:
            cached = await self._get_cached_result(cache_key)
            if cached:
                self._stats.cache_hits += 1
                return cached
            self._stats.cache_misses += 1
        
        async with self.get_connection() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                result = [dict(row) for row in rows]
        
        # Cache result if requested
        if cache_key and cache_result and result:
            await self._cache_result(cache_key, result)
        
        # Update stats
        query_time = (asyncio.get_event_loop().time() - start_time) * 1000
        self._stats.total_queries += 1
        self._stats.average_query_time = (
            (self._stats.average_query_time * (self._stats.total_queries - 1) + query_time) 
            / self._stats.total_queries
        )
        
        return result
    
    async def execute_write(
        self, 
        query: str, 
        params: tuple = (),
        return_id: bool = False
    ) -> Optional[int]:
        """
        ✍️ Execute an INSERT/UPDATE/DELETE query
        """
        start_time = asyncio.get_event_loop().time()
        
        async with self.get_connection() as db:
            cursor = await db.execute(query, params)
            await db.commit()
            
            result = cursor.lastrowid if return_id else None
        
        # Update stats
        query_time = (asyncio.get_event_loop().time() - start_time) * 1000
        self._stats.total_queries += 1
        self._stats.average_query_time = (
            (self._stats.average_query_time * (self._stats.total_queries - 1) + query_time) 
            / self._stats.total_queries
        )
        
        return result
    
    async def execute_many(
        self, 
        query: str, 
        params_list: List[tuple]
    ) -> int:
        """
        📦 Execute multiple queries in a single transaction
        """
        start_time = asyncio.get_event_loop().time()
        
        async with self.get_connection() as db:
            await db.executemany(query, params_list)
            await db.commit()
            affected_rows = db.total_changes
        
        # Update stats
        query_time = (asyncio.get_event_loop().time() - start_time) * 1000
        self._stats.total_queries += len(params_list)
        self._stats.average_query_time = (
            (self._stats.average_query_time * (self._stats.total_queries - len(params_list)) + query_time) 
            / self._stats.total_queries
        )
        
        return affected_rows
    
    async def _get_cached_result(self, cache_key: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached query result if not expired"""
        async with self._lock:
            if cache_key in self._query_cache:
                cached_data, timestamp = self._query_cache[cache_key]
                if datetime.utcnow() - timestamp < self._cache_ttl:
                    return cached_data
                else:
                    # Remove expired cache
                    del self._query_cache[cache_key]
        return None
    
    async def _cache_result(self, cache_key: str, result: List[Dict[str, Any]]):
        """Cache query result with timestamp"""
        async with self._lock:
            self._query_cache[cache_key] = (result, datetime.utcnow())
            
            # Simple cache cleanup - remove oldest entries if cache is too large
            if len(self._query_cache) > 100:
                oldest_key = min(self._query_cache.keys(), 
                               key=lambda k: self._query_cache[k][1])
                del self._query_cache[oldest_key]
    
    async def get_or_create_session(self, user_id: str, force_new: bool = False) -> str:
        """
        🆔 Get existing session or create new one for user
        """
        if not force_new:
            # Try to get existing active session
            existing_sessions = await self.execute_query(
                "SELECT session_id FROM chat_sessions WHERE user_id = ? AND is_active = 1 ORDER BY updated_at DESC LIMIT 1",
                (user_id,),
                cache_key=f"active_session_{user_id}",
                cache_result=True
            )
            
            if existing_sessions:
                session_id = existing_sessions[0]["session_id"]
                # Update session timestamp
                await self.execute_write(
                    "UPDATE chat_sessions SET updated_at = CURRENT_TIMESTAMP WHERE session_id = ?",
                    (session_id,)
                )
                return session_id
        
        # Create new session
        session_id = str(uuid.uuid4())
        await self.execute_write(
            "INSERT INTO chat_sessions (session_id, user_id, created_at, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            (session_id, user_id)
        )
        
        logger.info(f"🆕 Created new session {session_id} for user {user_id}")
        return session_id
    
    async def add_message(
        self, 
        session_id: str, 
        user_id: str, 
        user_message: str, 
        bot_response: str, 
        source: str,
        response_time_ms: Optional[float] = None
    ):
        """
        💬 Add message to chat session
        """
        await self.execute_write(
            """INSERT INTO chat_messages 
               (session_id, user_id, user_message, bot_response, source, timestamp, response_time_ms) 
               VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)""",
            (session_id, user_id, user_message, bot_response, source, response_time_ms)
        )
        
        # Update session timestamp
        await self.execute_write(
            "UPDATE chat_sessions SET updated_at = CURRENT_TIMESTAMP WHERE session_id = ?",
            (session_id,)
        )
    
    async def get_chat_history(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        📜 Get chat history for user
        """
        return await self.execute_query(
            """SELECT user_message, bot_response, source, timestamp, response_time_ms
               FROM chat_messages 
               WHERE user_id = ? 
               ORDER BY timestamp DESC 
               LIMIT ?""",
            (user_id, limit),
            cache_key=f"history_{user_id}_{limit}",
            cache_result=True
        )
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        📊 Get database and pool statistics
        """
        # Get database stats
        db_stats = await self.execute_query(
            """SELECT 
                (SELECT COUNT(*) FROM chat_sessions) as total_sessions,
                (SELECT COUNT(*) FROM chat_messages) as total_messages,
                (SELECT COUNT(DISTINCT user_id) FROM chat_sessions) as unique_users
            """,
            cache_key="db_stats",
            cache_result=True
        )
        
        stats = db_stats[0] if db_stats else {}
        
        # Add pool stats
        stats.update({
            "pool_stats": {
                "max_connections": self.max_connections,
                "active_connections": self._stats.active_connections,
                "total_queries": self._stats.total_queries,
                "average_query_time_ms": round(self._stats.average_query_time, 2),
                "cache_hit_rate": (
                    self._stats.cache_hits / max(self._stats.cache_hits + self._stats.cache_misses, 1) * 100
                ),
                "cached_queries": len(self._query_cache)
            },
            "uptime_seconds": (datetime.utcnow() - self.created_at).total_seconds()
        })
        
        return stats
    
    async def clear_chat_history(self, user_id: str):
        """
        🗑️ Clear chat history for user
        """
        await self.execute_write(
            "DELETE FROM chat_messages WHERE user_id = ?",
            (user_id,)
        )
        await self.execute_write(
            "UPDATE chat_sessions SET is_active = 0 WHERE user_id = ?",
            (user_id,)
        )
        
        # Clear related cache entries
        async with self._lock:
            keys_to_remove = [k for k in self._query_cache.keys() if user_id in k]
            for key in keys_to_remove:
                del self._query_cache[key]
    
    async def cleanup_old_sessions(self, days: int = 30):
        """
        🧹 Clean up old inactive sessions
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Mark old sessions as inactive
        affected = await self.execute_write(
            "UPDATE chat_sessions SET is_active = 0 WHERE updated_at < ? AND is_active = 1",
            (cutoff_date,)
        )
        
        logger.info(f"🧹 Marked {affected} old sessions as inactive")
        return affected
    
    async def close_pool(self):
        """
        🔐 Close all connections in the pool
        """
        logger.info("🔐 Closing async database pool...")
        
        while not self._connection_pool.empty():
            try:
                conn = self._connection_pool.get_nowait()
                await conn.close()
            except asyncio.QueueEmpty:
                break
                
        self._pool_initialized = False
        logger.info("✅ Async database pool closed")

# Global instance
async_db_pool = AsyncDatabasePool()

# Compatibility function for existing code
async def get_database_pool() -> AsyncDatabasePool:
    """Get the global async database pool instance"""
    if not async_db_pool._pool_initialized:
        await async_db_pool.initialize_pool()
    return async_db_pool
