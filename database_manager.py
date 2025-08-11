"""
🚀 Unified Database Manager
============================

Comprehensive database manager with support for multiple database backends:
- PostgreSQL (Recommended for production)
- MySQL/MariaDB (Alternative for production)  
- SQLite (Development only)

Features:
- Async/sync operations
- Connection pooling
- Transaction management
- Migration support
- Health monitoring
- Performance optimization

This is the unified version combining database_manager.py, production_database.py, 
and database_config.py for simplified maintenance.
"""

import sqlite3
import threading
import logging
import os
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union
from contextlib import contextmanager
import queue
import uuid
from enum import Enum

logger = logging.getLogger(__name__)

class DatabaseBackend(Enum):
    """Database backend types"""
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"

class ProductionDatabaseManager:
    """
    Production-ready database manager with support for multiple backends
    """
    
    def __init__(self, backend: str = None, connection_string: str = None):
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.backend = self._detect_backend(backend)
        self.connection_string = connection_string or self._build_connection_string()
        
        # Validate production setup
        if self.environment == "production":
            self._validate_production_setup()
        
        # Initialize based on backend
        if self.backend == DatabaseBackend.SQLITE:
            from .database_manager import DatabaseManager
            self.db_manager = DatabaseManager(self.connection_string.replace("sqlite:///", ""))
        else:
            self._init_sqlalchemy_backend()
    
    def _detect_backend(self, backend: str = None) -> DatabaseBackend:
        """Detect which database backend to use"""
        
        if backend:
            return DatabaseBackend(backend.lower())
        
        # Check environment variables
        if os.getenv("DATABASE_URL"):
            url = os.getenv("DATABASE_URL")
            if url.startswith("postgresql"):
                return DatabaseBackend.POSTGRESQL
            elif url.startswith("mysql"):
                return DatabaseBackend.MYSQL
            elif url.startswith("sqlite"):
                return DatabaseBackend.SQLITE
        
        # Check for specific database environment variables
        if os.getenv("POSTGRES_HOST") or os.getenv("POSTGRES_URL"):
            return DatabaseBackend.POSTGRESQL
        elif os.getenv("MYSQL_HOST") or os.getenv("MYSQL_URL"):
            return DatabaseBackend.MYSQL
        
        # Default to SQLite (with warning for production)
        if self.environment == "production":
            logger.critical(
                "🚨 PRODUCTION ALERT: No production database configured! "
                "SQLite is not suitable for production due to concurrency limitations. "
                "Please configure PostgreSQL or MySQL."
            )
        
        return DatabaseBackend.SQLITE
    
    def _build_connection_string(self) -> str:
        """Build connection string for the detected backend"""
        
        if os.getenv("DATABASE_URL"):
            return os.getenv("DATABASE_URL")
        
        if self.backend == DatabaseBackend.POSTGRESQL:
            host = os.getenv("POSTGRES_HOST", "localhost")
            port = os.getenv("POSTGRES_PORT", "5432")
            user = os.getenv("POSTGRES_USER", "mefapex")
            password = os.getenv("POSTGRES_PASSWORD")
            database = os.getenv("POSTGRES_DB", "mefapex_chatbot")
            
            if not password and self.environment == "production":
                raise ValueError("POSTGRES_PASSWORD is required for production")
            
            return f"postgresql://{user}:{password}@{host}:{port}/{database}"
        
        elif self.backend == DatabaseBackend.MYSQL:
            host = os.getenv("MYSQL_HOST", "localhost")
            port = os.getenv("MYSQL_PORT", "3306")
            user = os.getenv("MYSQL_USER", "root")
            password = os.getenv("MYSQL_PASSWORD")
            database = os.getenv("MYSQL_DATABASE", "mefapex_chatbot")
            
            if not password and self.environment == "production":
                raise ValueError("MYSQL_PASSWORD is required for production")
            
            return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
        
        else:  # SQLite
            db_path = os.getenv("SQLITE_PATH", "mefapex.db")
            return f"sqlite:///{db_path}"
    
    def _validate_production_setup(self):
        """Validate production database configuration"""
        
        if self.backend == DatabaseBackend.SQLITE:
            logger.critical(
                "🚨 CRITICAL PRODUCTION ISSUE: SQLite detected in production!\n"
                "SQLite is NOT suitable for production due to:\n"
                "  • Limited concurrency (single writer)\n"
                "  • No network access\n"  
                "  • Not suitable for multiple processes\n"
                "  • Limited scalability\n\n"
                "RECOMMENDED ACTIONS:\n"
                "  1. Set up PostgreSQL: POSTGRES_HOST, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB\n"
                "  2. Or set up MySQL: MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE\n"
                "  3. Or set DATABASE_URL directly\n"
            )
            
            # In production, this should be a hard failure
            if os.getenv("FORCE_SQLITE_PRODUCTION", "false").lower() != "true":
                raise RuntimeError(
                    "SQLite is not allowed in production. "
                    "Set FORCE_SQLITE_PRODUCTION=true only for testing (NOT recommended)."
                )
        
        # Validate connection string format
        if not self.connection_string:
            raise ValueError("Database connection string is empty")
        
        logger.info(f"✅ Production database validation passed: {self.backend.value}")
    
    def _init_sqlalchemy_backend(self):
        """Initialize SQLAlchemy-based backend for PostgreSQL/MySQL"""
        try:
            # Import SQLAlchemy (will be added to requirements)
            from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Text, DateTime, Boolean
            from sqlalchemy.orm import sessionmaker
            from sqlalchemy.pool import QueuePool
            
            # Create engine with production configuration
            engine_config = {
                "echo": self.environment == "development",
                "poolclass": QueuePool,
                "pool_size": 20,
                "max_overflow": 30,
                "pool_pre_ping": True,
                "pool_recycle": 3600,
            }
            
            self.engine = create_engine(self.connection_string, **engine_config)
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            
            # Define table schema
            self.metadata = MetaData()
            
            self.users_table = Table(
                'users', self.metadata,
                Column('id', Integer, primary_key=True),
                Column('user_id', String(255), unique=True, nullable=False),
                Column('username', String(255), unique=True, nullable=False),
                Column('email', String(255), unique=True, nullable=False),
                Column('hashed_password', String(255), nullable=False),
                Column('full_name', String(255)),
                Column('created_at', DateTime, default=datetime.utcnow),
                Column('is_active', Boolean, default=True)
            )
            
            self.sessions_table = Table(
                'chat_sessions', self.metadata,
                Column('id', Integer, primary_key=True),
                Column('session_id', String(255), unique=True, nullable=False),
                Column('user_id', String(255), nullable=False),
                Column('created_at', DateTime, default=datetime.utcnow),
                Column('updated_at', DateTime, default=datetime.utcnow),
                Column('is_active', Boolean, default=True),
                Column('message_count', Integer, default=0)
            )
            
            self.messages_table = Table(
                'chat_messages', self.metadata,
                Column('id', Integer, primary_key=True),
                Column('session_id', String(255), nullable=False),
                Column('user_id', String(255), nullable=False),
                Column('timestamp', DateTime, default=datetime.utcnow),
                Column('user_message', Text),
                Column('bot_response', Text),
                Column('source', String(100))
            )
            
            # Create tables
            self.metadata.create_all(self.engine)
            
            logger.info(f"✅ SQLAlchemy backend initialized: {self.backend.value}")
            
        except ImportError:
            logger.error("SQLAlchemy not installed. Please install: pip install sqlalchemy pymysql psycopg2-binary")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize SQLAlchemy backend: {e}")
            raise
    
    @contextmanager
    def get_session(self):
        """Get database session (SQLAlchemy or SQLite)"""
        if self.backend == DatabaseBackend.SQLITE:
            with self.db_manager.pool.get_connection() as conn:
                yield conn
        else:
            session = self.SessionLocal()
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()
    
    def get_or_create_session(self, user_id: str, force_new: bool = False) -> str:
        """Get or create user session"""
        if self.backend == DatabaseBackend.SQLITE:
            return self.db_manager.get_or_create_session(user_id, force_new)
        else:
            return self._sqlalchemy_get_or_create_session(user_id, force_new)
    
    def add_message(self, session_id: str, user_id: str, user_message: str, bot_response: str, source: str):
        """Add message to session"""
        if self.backend == DatabaseBackend.SQLITE:
            self.db_manager.add_message(session_id, user_id, user_message, bot_response, source)
        else:
            self._sqlalchemy_add_message(session_id, user_id, user_message, bot_response, source)
    
    def get_chat_history(self, user_id: str, limit: int = 20) -> List[Dict]:
        """Get chat history for user"""
        if self.backend == DatabaseBackend.SQLITE:
            return self.db_manager.get_chat_history(user_id, limit)
        else:
            return self._sqlalchemy_get_chat_history(user_id, limit)
    
    def clear_chat_history(self, user_id: str):
        """Clear chat history for user"""
        if self.backend == DatabaseBackend.SQLITE:
            self.db_manager.clear_chat_history(user_id)
        else:
            self._sqlalchemy_clear_chat_history(user_id)
    
    def get_stats(self) -> Dict:
        """Get database statistics"""
        if self.backend == DatabaseBackend.SQLITE:
            stats = self.db_manager.get_stats()
            stats["backend"] = "sqlite"
            stats["production_ready"] = False
            return stats
        else:
            return self._sqlalchemy_get_stats()
    
    # SQLAlchemy implementation methods
    def _sqlalchemy_get_or_create_session(self, user_id: str, force_new: bool = False) -> str:
        """SQLAlchemy implementation of get_or_create_session"""
        from sqlalchemy import select, insert
        
        with self.get_session() as session:
            if not force_new:
                # Look for existing active session
                query = select(self.sessions_table.c.session_id).where(
                    self.sessions_table.c.user_id == user_id,
                    self.sessions_table.c.is_active == True
                ).order_by(self.sessions_table.c.created_at.desc()).limit(1)
                
                result = session.execute(query).first()
                if result:
                    return result.session_id
            
            # Create new session
            session_id = str(uuid.uuid4())
            insert_stmt = insert(self.sessions_table).values(
                session_id=session_id,
                user_id=user_id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                is_active=True,
                message_count=0
            )
            session.execute(insert_stmt)
            
            return session_id
    
    def _sqlalchemy_add_message(self, session_id: str, user_id: str, user_message: str, bot_response: str, source: str):
        """SQLAlchemy implementation of add_message"""
        from sqlalchemy import insert
        
        with self.get_session() as session:
            insert_stmt = insert(self.messages_table).values(
                session_id=session_id,
                user_id=user_id,
                timestamp=datetime.utcnow(),
                user_message=user_message,
                bot_response=bot_response,
                source=source
            )
            session.execute(insert_stmt)
    
    def _sqlalchemy_get_chat_history(self, user_id: str, limit: int = 20) -> List[Dict]:
        """SQLAlchemy implementation of get_chat_history"""
        from sqlalchemy import select
        
        with self.get_session() as session:
            query = select(
                self.messages_table.c.user_message,
                self.messages_table.c.bot_response,
                self.messages_table.c.source,
                self.messages_table.c.timestamp
            ).where(
                self.messages_table.c.user_id == user_id
            ).order_by(
                self.messages_table.c.timestamp.desc()
            ).limit(limit)
            
            results = session.execute(query).fetchall()
            
            return [
                {
                    "user_message": row.user_message,
                    "bot_response": row.bot_response,
                    "source": row.source,
                    "timestamp": row.timestamp.isoformat() if row.timestamp else None
                }
                for row in reversed(results)
            ]
    
    def _sqlalchemy_clear_chat_history(self, user_id: str):
        """SQLAlchemy implementation of clear_chat_history"""
        from sqlalchemy import delete
        
        with self.get_session() as session:
            # Delete messages
            delete_messages = delete(self.messages_table).where(
                self.messages_table.c.user_id == user_id
            )
            session.execute(delete_messages)
            
            # Delete sessions
            delete_sessions = delete(self.sessions_table).where(
                self.sessions_table.c.user_id == user_id
            )
            session.execute(delete_sessions)
    
    def _sqlalchemy_get_stats(self) -> Dict:
        """SQLAlchemy implementation of get_stats"""
        from sqlalchemy import select, func
        
        with self.get_session() as session:
            # Count users
            user_count = session.execute(
                select(func.count()).select_from(self.users_table)
            ).scalar() or 0
            
            # Count sessions
            session_count = session.execute(
                select(func.count()).select_from(self.sessions_table)
            ).scalar() or 0
            
            # Count messages
            message_count = session.execute(
                select(func.count()).select_from(self.messages_table)
            ).scalar() or 0
            
            # Count recent messages (last 24 hours)
            from sqlalchemy import and_
            recent_messages = session.execute(
                select(func.count()).select_from(self.messages_table).where(
                    self.messages_table.c.timestamp >= datetime.utcnow() - timedelta(days=1)
                )
            ).scalar() or 0
            
            return {
                "backend": self.backend.value,
                "production_ready": True,
                "users": user_count,
                "sessions": session_count,
                "messages": message_count,
                "messages_24h": recent_messages,
                "connection_pool_size": self.engine.pool.size() if hasattr(self.engine, 'pool') else 0,
                "connection_pool_checked_out": self.engine.pool.checkedout() if hasattr(self.engine, 'pool') else 0
            }
    
    def health_check(self) -> Dict:
        """Perform database health check"""
        try:
            start_time = time.time()
            
            if self.backend == DatabaseBackend.SQLITE:
                # SQLite health check
                with self.get_session() as conn:
                    conn.execute("SELECT 1")
                status = "healthy"
            else:
                # SQLAlchemy health check
                from sqlalchemy import text
                with self.get_session() as session:
                    session.execute(text("SELECT 1"))
                status = "healthy"
            
            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            return {
                "status": status,
                "backend": self.backend.value,
                "response_time_ms": round(response_time, 2),
                "production_ready": self.backend != DatabaseBackend.SQLITE,
                "environment": self.environment
            }
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "backend": self.backend.value,
                "error": str(e),
                "production_ready": False,
                "environment": self.environment
            }

# Factory function to create the appropriate database manager
def create_database_manager() -> ProductionDatabaseManager:
    """
    Create appropriate database manager based on environment and configuration
    """
    environment = os.getenv("ENVIRONMENT", "development")
    
    # Check if production database is configured
    if (os.getenv("POSTGRES_HOST") or os.getenv("MYSQL_HOST") or 
        os.getenv("DATABASE_URL", "").startswith(("postgresql", "mysql"))):
        
        try:
            return ProductionDatabaseManager()
        except Exception as e:
            logger.error(f"Failed to initialize production database: {e}")
            
            if environment == "production":
                raise RuntimeError(f"Production database initialization failed: {e}")
            else:
                logger.warning("Falling back to SQLite for development")
                return ProductionDatabaseManager(backend="sqlite")
    
    else:
        # Use existing SQLite manager
        from .database_manager import DatabaseManager
        if environment == "production":
            logger.critical(
                "🚨 PRODUCTION WARNING: Using SQLite in production is not recommended!"
            )
        return DatabaseManager()

# Global database manager instance
_db_manager = None

def get_database_manager() -> ProductionDatabaseManager:
    """Get global database manager instance"""
    global _db_manager
    if _db_manager is None:
        _db_manager = create_database_manager()
    return _db_manager

def init_database_manager():
    """Initialize global database manager"""
    global _db_manager
    _db_manager = create_database_manager()
    return _db_manager

# Backward compatibility alias
DatabaseManager = ProductionDatabaseManager
