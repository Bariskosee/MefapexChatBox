"""
🏗️ Database Base Architecture
Production-grade database interface with multi-backend support
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class DatabaseConfig:
    """Database configuration with validation"""
    database_type: str
    host: str = "localhost"
    port: int = 5432
    database: str = "mefapex_chatbot"
    username: str = "mefapex"
    password: str = ""
    pool_size: int = 20
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 3600
    echo: bool = False
    
    def __post_init__(self):
        """Validate configuration"""
        if self.database_type not in ["postgresql", "mysql", "sqlite"]:
            raise ValueError(f"Unsupported database type: {self.database_type}")
        
        if self.database_type != "sqlite" and not self.password:
            logger.warning("⚠️ No password set for database connection")

@dataclass
class ConnectionStats:
    """Database connection statistics"""
    active_connections: int
    idle_connections: int
    total_connections: int
    pool_size: int
    overflow_connections: int
    connection_errors: int
    avg_response_time_ms: float
    last_health_check: datetime

class DatabaseInterface(ABC):
    """
    Abstract base class for all database backends
    Ensures consistent interface across SQLite, PostgreSQL, MySQL
    """
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.created_at = datetime.utcnow()
        self._connection_stats = ConnectionStats(
            active_connections=0,
            idle_connections=0,
            total_connections=0,
            pool_size=config.pool_size,
            overflow_connections=0,
            connection_errors=0,
            avg_response_time_ms=0.0,
            last_health_check=datetime.utcnow()
        )
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize database and create schema"""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check"""
        pass
    
    @abstractmethod
    async def get_connection_stats(self) -> ConnectionStats:
        """Get real-time connection statistics"""
        pass
    
    # Session Management
    @abstractmethod
    async def create_session(self, user_id: str, session_type: str = "chat") -> str:
        """Create new chat session"""
        pass
    
    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information"""
        pass
    
    @abstractmethod
    async def get_user_sessions(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get user's sessions with pagination"""
        pass
    
    # Message Management
    @abstractmethod
    async def add_message(
        self, 
        session_id: str, 
        user_id: str, 
        message: str, 
        response: str, 
        source: str = "ai"
    ) -> str:
        """Add message to session"""
        pass
    
    @abstractmethod
    async def get_session_messages(
        self, 
        session_id: str, 
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get session messages with pagination"""
        pass
    
    @abstractmethod
    async def get_user_message_history(
        self, 
        user_id: str, 
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get user's complete message history"""
        pass
    
    # User Management
    @abstractmethod
    async def create_user(
        self, 
        username: str, 
        email: str, 
        hashed_password: str,
        full_name: Optional[str] = None
    ) -> str:
        """Create new user"""
        pass
    
    @abstractmethod
    async def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username"""
        pass
    
    @abstractmethod
    async def update_user_last_login(self, user_id: str) -> bool:
        """Update user's last login timestamp"""
        pass
    
    # Analytics & Reporting
    @abstractmethod
    async def get_analytics_data(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get analytics data for date range"""
        pass
    
    @abstractmethod
    async def get_system_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics"""
        pass
    
    # Backup & Maintenance
    @abstractmethod
    async def create_backup(self, backup_path: str) -> bool:
        """Create database backup"""
        pass
    
    @abstractmethod
    async def restore_backup(self, backup_path: str) -> bool:
        """Restore database from backup"""
        pass
    
    @abstractmethod
    async def optimize_database(self) -> Dict[str, Any]:
        """Run database optimization/maintenance tasks"""
        pass
    
    # Data Validation & Constraints
    @abstractmethod
    async def validate_data_integrity(self) -> Dict[str, Any]:
        """Validate database integrity and constraints"""
        pass
    
    @abstractmethod
    async def cleanup_old_data(self, days_to_keep: int = 90) -> Dict[str, Any]:
        """Clean up old data based on retention policy"""
        pass
    
    # Transaction Management
    @abstractmethod
    async def begin_transaction(self):
        """Start database transaction"""
        pass
    
    @abstractmethod
    async def commit_transaction(self):
        """Commit current transaction"""
        pass
    
    @abstractmethod
    async def rollback_transaction(self):
        """Rollback current transaction"""
        pass
    
    async def close(self):
        """Close database connections"""
        pass

class DatabaseFactory:
    """Factory for creating database instances"""
    
    @staticmethod
    def create_database(config: DatabaseConfig) -> DatabaseInterface:
        """Create database instance based on configuration"""
        if config.database_type == "postgresql":
            from .postgresql_manager import PostgreSQLManager
            return PostgreSQLManager(config)
        elif config.database_type == "mysql":
            from .mysql_manager import MySQLManager
            return MySQLManager(config)
        elif config.database_type == "sqlite":
            from .sqlite_manager import SQLiteManager
            return SQLiteManager(config)
        else:
            raise ValueError(f"Unsupported database type: {config.database_type}")
    
    @staticmethod
    def create_from_env() -> DatabaseInterface:
        """Create database instance from environment variables"""
        import os
        
        database_type = os.getenv("DATABASE_TYPE", "sqlite")
        
        if database_type == "postgresql":
            config = DatabaseConfig(
                database_type="postgresql",
                host=os.getenv("POSTGRES_HOST", "localhost"),
                port=int(os.getenv("POSTGRES_PORT", "5432")),
                database=os.getenv("POSTGRES_DB", "mefapex_chatbot"),
                username=os.getenv("POSTGRES_USER", "mefapex"),
                password=os.getenv("POSTGRES_PASSWORD", ""),
                pool_size=int(os.getenv("DB_POOL_SIZE", "20")),
                max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
                pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "30")),
                pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "3600")),
                echo=os.getenv("DB_ECHO", "false").lower() == "true"
            )
        elif database_type == "mysql":
            config = DatabaseConfig(
                database_type="mysql",
                host=os.getenv("MYSQL_HOST", "localhost"),
                port=int(os.getenv("MYSQL_PORT", "3306")),
                database=os.getenv("MYSQL_DATABASE", "mefapex_chatbot"),
                username=os.getenv("MYSQL_USER", "mefapex"),
                password=os.getenv("MYSQL_PASSWORD", ""),
                pool_size=int(os.getenv("DB_POOL_SIZE", "20")),
                max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
                pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "30")),
                pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "3600"))
            )
        else:  # sqlite
            config = DatabaseConfig(
                database_type="sqlite",
                database=os.getenv("SQLITE_PATH", "./data/mefapex.db"),
                pool_size=1,  # SQLite doesn't support connection pooling
                max_overflow=0
            )
        
        return DatabaseFactory.create_database(config)
