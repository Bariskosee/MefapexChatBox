"""
🔌 Database Connection Service for MEFAPEX Chat System
=====================================================

Base connection management for PostgreSQL database.
Handles connection pooling, transactions, and low-level database operations.
"""

import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool
from typing import Optional
from contextlib import contextmanager
from core.configuration import get_config

logger = logging.getLogger(__name__)


class ConnectionService:
    """
    PostgreSQL Connection Service
    
    Manages database connections, connection pooling, and provides
    transaction management capabilities.
    """
    
    def __init__(self):
        """Initialize PostgreSQL Connection Service"""
        self.connection_pool = None
        self.host = get_config().database.host
        self.port = int(get_config().database.port)
        self.user = get_config().database.user
        self.password = get_config().database.password
        self.database = get_config().database.database
        
        # Validation
        if not self.password:
            raise ValueError("❌ POSTGRES_PASSWORD environment variable is required")
        
        # Initialize connection pool
        self._init_connection_pool()
        
        logger.info(f"✅ Connection Service initialized: {self.host}:{self.port}/{self.database}")

    def _init_connection_pool(self):
        """Initialize PostgreSQL connection pool"""
        try:
            self.connection_pool = ThreadedConnectionPool(
                minconn=1,
                maxconn=20,
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                cursor_factory=RealDictCursor
            )
            logger.info("✅ PostgreSQL connection pool established")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize PostgreSQL connection pool: {e}")
            raise

    def get_connection(self):
        """Get connection from pool"""
        if not self.connection_pool:
            raise RuntimeError("Connection pool not initialized")
        return self.connection_pool.getconn()

    def put_connection(self, conn):
        """Return connection to pool"""
        if self.connection_pool and conn:
            self.connection_pool.putconn(conn)

    @contextmanager
    def get_cursor(self, commit=True):
        """
        Context manager for database operations
        
        Args:
            commit: Whether to commit the transaction automatically
            
        Usage:
            with connection_service.get_cursor() as cursor:
                cursor.execute("SELECT * FROM users")
                result = cursor.fetchall()
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            yield cursor
            
            if commit:
                conn.commit()
                
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database operation error: {e}")
            raise
        finally:
            if conn:
                self.put_connection(conn)

    @contextmanager
    def get_transaction(self):
        """
        Context manager for explicit transaction control
        
        Usage:
            with connection_service.get_transaction() as (conn, cursor):
                cursor.execute("INSERT INTO users ...")
                cursor.execute("INSERT INTO sessions ...")
                # Will commit automatically if no exceptions
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            yield conn, cursor
            conn.commit()
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Transaction error: {e}")
            raise
        finally:
            if conn:
                self.put_connection(conn)

    def execute_query(self, query: str, params=None, fetch_one=False, fetch_all=True):
        """
        Execute a query and return results
        
        Args:
            query: SQL query to execute
            params: Query parameters
            fetch_one: Return single result
            fetch_all: Return all results
            
        Returns:
            Query results or None
        """
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            
            if fetch_one:
                return cursor.fetchone()
            elif fetch_all:
                return cursor.fetchall()
            else:
                return cursor.rowcount

    def execute_many(self, query: str, params_list):
        """
        Execute a query multiple times with different parameters
        
        Args:
            query: SQL query to execute
            params_list: List of parameter tuples
            
        Returns:
            Number of affected rows
        """
        with self.get_cursor() as cursor:
            cursor.executemany(query, params_list)
            return cursor.rowcount

    def health_check(self) -> dict:
        """
        Check database connection health
        
        Returns:
            Health status dictionary
        """
        try:
            result = self.execute_query("SELECT 1 as health_check", fetch_one=True)
            
            if result and result.get('health_check') == 1:
                return {
                    "status": "healthy",
                    "database": "postgresql",
                    "host": self.host,
                    "port": self.port,
                    "database_name": self.database
                }
            else:
                return {"status": "unhealthy", "error": "Invalid health check response"}
                
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}

    def get_database_info(self) -> dict:
        """
        Get database information and statistics
        
        Returns:
            Database information dictionary
        """
        try:
            with self.get_cursor() as cursor:
                # Get PostgreSQL version
                cursor.execute("SELECT version()")
                version_result = cursor.fetchone()
                
                # Get database size
                cursor.execute("""
                    SELECT pg_size_pretty(pg_database_size(%s)) as size
                """, (self.database,))
                size_result = cursor.fetchone()
                
                # Get connection count
                cursor.execute("""
                    SELECT count(*) as connections 
                    FROM pg_stat_activity 
                    WHERE datname = %s
                """, (self.database,))
                connections_result = cursor.fetchone()
                
                return {
                    "version": version_result.get('version') if version_result else 'unknown',
                    "size": size_result.get('size') if size_result else 'unknown',
                    "active_connections": connections_result.get('connections') if connections_result else 0,
                    "max_connections": 20,  # Our pool max
                    "host": self.host,
                    "port": self.port,
                    "database": self.database
                }
                
        except Exception as e:
            logger.error(f"Failed to get database info: {e}")
            return {"error": str(e)}

    def close_pool(self):
        """Close the connection pool"""
        if self.connection_pool:
            self.connection_pool.closeall()
            self.connection_pool = None
            logger.info("Connection pool closed")


# Create singleton instance
connection_service = ConnectionService()
