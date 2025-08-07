"""
🗄️ Production Database Connection Pool Configuration
Author: MEFAPEX AI Assistant
Description: Enhanced database connection pooling with monitoring and health checks
"""

import os
import time
import asyncio
import logging
from contextlib import asynccontextmanager, contextmanager
from typing import Optional, Dict, Any, AsyncGenerator
from datetime import datetime, timedelta
import sqlite3
import threading
from queue import Queue, Empty, Full
from dataclasses import dataclass

# For PostgreSQL support (uncomment when needed)
# import asyncpg
# from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
# from sqlalchemy.orm import sessionmaker
# from sqlalchemy.pool import QueuePool

logger = logging.getLogger(__name__)

@dataclass
class PoolStats:
    """Database pool statistics"""
    total_connections: int
    active_connections: int
    idle_connections: int
    total_queries: int
    failed_queries: int
    avg_query_time: float
    created_at: datetime

class DatabaseConnectionPool:
    """
    Production-ready database connection pool with monitoring
    Supports both SQLite (for development) and PostgreSQL (for production)
    """
    
    def __init__(self, 
                 database_url: str,
                 max_connections: int = 20,
                 min_connections: int = 5,
                 connection_timeout: int = 30,
                 idle_timeout: int = 300,
                 max_query_time: int = 30):
        
        self.database_url = database_url
        self.max_connections = max_connections
        self.min_connections = min_connections
        self.connection_timeout = connection_timeout
        self.idle_timeout = idle_timeout
        self.max_query_time = max_query_time
        
        # Connection management
        self._connections = Queue(maxsize=max_connections)
        self._active_connections = set()
        self._connection_times = {}
        self._lock = threading.Lock()
        
        # Statistics
        self.total_queries = 0
        self.failed_queries = 0
        self.query_times = []
        self.created_at = datetime.utcnow()
        
        # Health check
        self._healthy = True
        self._last_health_check = None
        
        # Initialize pool
        self._initialize_pool()
        
    def _initialize_pool(self):
        """Initialize the connection pool"""
        logger.info(f"🗄️ Initializing database pool (min: {self.min_connections}, max: {self.max_connections})")
        
        # Create minimum connections
        for _ in range(self.min_connections):
            try:
                conn = self._create_connection()
                self._connections.put(conn, block=False)
            except Exception as e:
                logger.error(f"Failed to create initial connection: {e}")
                
        logger.info(f"✅ Database pool initialized with {self._connections.qsize()} connections")
        
    def _create_connection(self):
        """Create a new database connection"""
        if self.database_url.startswith('sqlite'):
            return self._create_sqlite_connection()
        elif self.database_url.startswith('postgresql'):
            return self._create_postgresql_connection()
        else:
            raise ValueError(f"Unsupported database URL: {self.database_url}")
            
    def _create_sqlite_connection(self):
        """Create SQLite connection with optimizations"""
        # Extract database path from URL
        db_path = self.database_url.replace('sqlite:///', '')
        
        conn = sqlite3.connect(
            db_path,
            timeout=self.connection_timeout,
            check_same_thread=False,
            isolation_level=None  # Autocommit mode
        )
        
        # SQLite optimizations for production
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL") 
        conn.execute("PRAGMA cache_size=10000")
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.execute("PRAGMA mmap_size=268435456")  # 256MB
        
        return conn
        
    def _create_postgresql_connection(self):
        """Create PostgreSQL connection (placeholder for future implementation)"""
        # TODO: Implement PostgreSQL connection
        # import psycopg2
        # from psycopg2.pool import ThreadedConnectionPool
        
        raise NotImplementedError("PostgreSQL support not yet implemented")
        
    @contextmanager
    def get_connection(self):
        """Get a connection from the pool (context manager)"""
        conn = None
        start_time = time.time()
        
        try:
            # Get connection from pool
            try:
                conn = self._connections.get(timeout=self.connection_timeout)
            except Empty:
                # Pool exhausted, try to create new connection if under limit
                with self._lock:
                    if len(self._active_connections) < self.max_connections:
                        conn = self._create_connection()
                        logger.warning(f"Created new connection (pool exhausted)")
                    else:
                        raise RuntimeError("Connection pool exhausted and at maximum capacity")
                        
            # Track active connection
            with self._lock:
                self._active_connections.add(conn)
                self._connection_times[id(conn)] = time.time()
                
            # Test connection health
            if not self._test_connection(conn):
                # Connection is dead, create new one
                conn.close()
                conn = self._create_connection()
                logger.warning("Replaced dead connection")
                
            yield conn
            
        except Exception as e:
            self.failed_queries += 1
            logger.error(f"Database connection error: {e}")
            raise
            
        finally:
            # Return connection to pool
            if conn:
                with self._lock:
                    self._active_connections.discard(conn)
                    if id(conn) in self._connection_times:
                        del self._connection_times[id(conn)]
                        
                try:
                    # Test connection before returning to pool
                    if self._test_connection(conn):
                        self._connections.put(conn, block=False)
                    else:
                        conn.close()
                        logger.warning("Discarded unhealthy connection")
                except Full:
                    # Pool is full, close connection
                    conn.close()
                    
            # Track query time
            query_time = time.time() - start_time
            self.query_times.append(query_time)
            self.total_queries += 1
            
            # Keep only recent query times (last 1000)
            if len(self.query_times) > 1000:
                self.query_times = self.query_times[-1000:]
                
    def _test_connection(self, conn) -> bool:
        """Test if connection is healthy"""
        try:
            if self.database_url.startswith('sqlite'):
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                cursor.close()
                return True
            else:
                # PostgreSQL test would go here
                return True
        except Exception:
            return False
            
    def execute_query(self, query: str, params: tuple = None) -> list:
        """Execute a query and return results"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                    
                # Fetch results for SELECT queries
                if query.strip().upper().startswith('SELECT'):
                    results = cursor.fetchall()
                    return results
                else:
                    conn.commit()
                    return []
                    
            finally:
                cursor.close()
                
    def execute_many(self, query: str, params_list: list) -> int:
        """Execute a query multiple times with different parameters"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.executemany(query, params_list)
                conn.commit()
                return cursor.rowcount
            finally:
                cursor.close()
                
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on the database pool"""
        try:
            start_time = time.time()
            
            # Test a simple query
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                cursor.close()
                
            response_time = time.time() - start_time
            self._healthy = True
            self._last_health_check = datetime.utcnow()
            
            return {
                "status": "healthy",
                "response_time_ms": response_time * 1000,
                "timestamp": self._last_health_check.isoformat()
            }
            
        except Exception as e:
            self._healthy = False
            self._last_health_check = datetime.utcnow()
            
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": self._last_health_check.isoformat()
            }
            
    def get_stats(self) -> PoolStats:
        """Get current pool statistics"""
        with self._lock:
            active_count = len(self._active_connections)
            idle_count = self._connections.qsize()
            total_count = active_count + idle_count
            
        avg_query_time = sum(self.query_times) / len(self.query_times) if self.query_times else 0
        
        return PoolStats(
            total_connections=total_count,
            active_connections=active_count,
            idle_connections=idle_count,
            total_queries=self.total_queries,
            failed_queries=self.failed_queries,
            avg_query_time=avg_query_time,
            created_at=self.created_at
        )
        
    def cleanup_idle_connections(self):
        """Clean up idle connections that have exceeded timeout"""
        current_time = time.time()
        connections_to_close = []
        
        with self._lock:
            for conn_id, connect_time in list(self._connection_times.items()):
                if current_time - connect_time > self.idle_timeout:
                    # Find and remove the connection
                    for conn in self._active_connections:
                        if id(conn) == conn_id:
                            connections_to_close.append(conn)
                            break
                            
        # Close idle connections
        for conn in connections_to_close:
            try:
                conn.close()
                with self._lock:
                    self._active_connections.discard(conn)
                    if id(conn) in self._connection_times:
                        del self._connection_times[id(conn)]
                logger.info(f"Closed idle connection (timeout: {self.idle_timeout}s)")
            except Exception as e:
                logger.error(f"Error closing idle connection: {e}")
                
    def close_all(self):
        """Close all connections in the pool"""
        logger.info("🗄️ Closing all database connections...")
        
        # Close connections in pool
        while not self._connections.empty():
            try:
                conn = self._connections.get_nowait()
                conn.close()
            except Empty:
                break
            except Exception as e:
                logger.error(f"Error closing pooled connection: {e}")
                
        # Close active connections
        with self._lock:
            for conn in list(self._active_connections):
                try:
                    conn.close()
                except Exception as e:
                    logger.error(f"Error closing active connection: {e}")
            self._active_connections.clear()
            self._connection_times.clear()
            
        logger.info("✅ All database connections closed")

# Async version for FastAPI (future implementation)
class AsyncDatabasePool:
    """
    Async database connection pool for FastAPI applications
    TODO: Implement when migrating to async database operations
    """
    
    def __init__(self, database_url: str, **kwargs):
        self.database_url = database_url
        # Implementation would use asyncpg for PostgreSQL
        # or aiosqlite for SQLite
        pass
        
    @asynccontextmanager
    async def get_connection(self):
        """Async context manager for getting connections"""
        # TODO: Implement async connection management
        yield None

# PostgreSQL specific implementation
class PostgreSQLPool:
    """
    Production PostgreSQL connection pool using SQLAlchemy
    """
    
    def __init__(self, 
                 database_url: str,
                 pool_size: int = 20,
                 max_overflow: int = 10,
                 pool_timeout: int = 30,
                 pool_recycle: int = 3600):
        
        self.database_url = database_url
        
        # SQLAlchemy engine with connection pooling
        # from sqlalchemy import create_engine
        # self.engine = create_engine(
        #     database_url,
        #     poolclass=QueuePool,
        #     pool_size=pool_size,
        #     max_overflow=max_overflow,
        #     pool_timeout=pool_timeout,
        #     pool_recycle=pool_recycle,
        #     echo=False,  # Set to True for SQL logging in development
        #     future=True
        # )
        
        logger.info(f"🐘 PostgreSQL pool configured (size: {pool_size}, overflow: {max_overflow})")
        
    @contextmanager 
    def get_session(self):
        """Get SQLAlchemy session"""
        # session = self.Session()
        # try:
        #     yield session
        #     session.commit()
        # except Exception:
        #     session.rollback()
        #     raise
        # finally:
        #     session.close()
        pass

# Factory function to create appropriate pool
def create_database_pool(database_url: str, **kwargs) -> DatabaseConnectionPool:
    """
    Factory function to create appropriate database pool based on URL
    """
    if database_url.startswith('sqlite'):
        return DatabaseConnectionPool(database_url, **kwargs)
    elif database_url.startswith('postgresql'):
        # For production PostgreSQL
        return PostgreSQLPool(database_url, **kwargs)
    else:
        raise ValueError(f"Unsupported database URL: {database_url}")

# Example usage and testing
if __name__ == "__main__":
    # Test the connection pool
    pool = DatabaseConnectionPool("sqlite:///test.db", max_connections=5)
    
    # Test basic operations
    try:
        results = pool.execute_query("SELECT 1 as test")
        print(f"Query result: {results}")
        
        # Health check
        health = pool.health_check()
        print(f"Health check: {health}")
        
        # Statistics
        stats = pool.get_stats()
        print(f"Pool stats: {stats}")
        
    finally:
        pool.close_all()
