"""
🏭 Production Database Manager Factory
Creates appropriate database manager based on environment configuration
"""

import os
import logging
from typing import Optional, Dict, Any
from .base import DatabaseInterface, DatabaseConfig, DatabaseFactory

logger = logging.getLogger(__name__)

class ProductionDatabaseManager:
    """
    Production-grade database manager with automatic failover,
    health monitoring, and performance optimization
    """
    
    def __init__(self):
        self.db: Optional[DatabaseInterface] = None
        self.config: Optional[DatabaseConfig] = None
        self._initialized = False
        self._health_status = "unknown"
        
    async def initialize(self) -> bool:
        """Initialize database with production configuration"""
        try:
            # Create database configuration from environment
            self.config = self._create_config_from_env()
            
            # Create database instance
            self.db = DatabaseFactory.create_database(self.config)
            
            # Initialize database
            success = await self.db.initialize()
            
            if success:
                self._initialized = True
                self._health_status = "healthy"
                logger.info(f"✅ Production database initialized: {self.config.database_type}")
                
                # Log configuration (without sensitive data)
                logger.info(f"🔧 Database: {self.config.host}:{self.config.port}/{self.config.database}")
                logger.info(f"🔧 Pool size: {self.config.pool_size} (max overflow: {self.config.max_overflow})")
                
                return True
            else:
                self._health_status = "failed"
                logger.error("❌ Failed to initialize database")
                return False
                
        except Exception as e:
            self._health_status = "error"
            logger.error(f"❌ Database initialization error: {e}")
            return False
    
    def _create_config_from_env(self) -> DatabaseConfig:
        """Create database configuration from environment variables"""
        database_type = os.getenv("DATABASE_TYPE", "sqlite").lower()
        
        # Validate production requirements
        environment = os.getenv("ENVIRONMENT", "development")
        if environment == "production" and database_type == "sqlite":
            force_sqlite = os.getenv("FORCE_SQLITE_PRODUCTION", "false").lower() == "true"
            if not force_sqlite:
                logger.error("🚨 SQLite not recommended for production! Use PostgreSQL or MySQL.")
                logger.error("Set FORCE_SQLITE_PRODUCTION=true to override (NOT recommended)")
                raise ValueError("SQLite not suitable for production without explicit override")
        
        if database_type == "postgresql":
            return DatabaseConfig(
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
            return DatabaseConfig(
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
            if environment == "production":
                logger.warning("⚠️ Using SQLite in production mode (override enabled)")
            
            return DatabaseConfig(
                database_type="sqlite",
                database=os.getenv("SQLITE_PATH", "./data/mefapex.db"),
                pool_size=1,  # SQLite doesn't support real pooling
                max_overflow=0
            )
    
    # Proxy methods to underlying database
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check with fallback handling"""
        if not self._initialized or not self.db:
            return {
                "status": "not_initialized",
                "database_type": "unknown",
                "error": "Database not initialized"
            }
        
        try:
            health = await self.db.health_check()
            self._health_status = health.get("status", "unknown")
            return health
        except Exception as e:
            self._health_status = "error"
            logger.error(f"❌ Health check failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "database_type": self.config.database_type if self.config else "unknown"
            }
    
    async def get_connection_stats(self):
        """Get connection pool statistics"""
        if not self.db:
            return None
        return await self.db.get_connection_stats()
    
    # Session Management
    async def create_session(self, user_id: str, session_type: str = "chat") -> str:
        """Create new chat session"""
        if not self.db:
            raise RuntimeError("Database not initialized")
        return await self.db.create_session(user_id, session_type)
    
    async def get_session(self, session_id: str):
        """Get session information"""
        if not self.db:
            raise RuntimeError("Database not initialized")
        return await self.db.get_session(session_id)
    
    async def get_user_sessions(self, user_id: str, limit: int = 20):
        """Get user's sessions"""
        if not self.db:
            raise RuntimeError("Database not initialized")
        return await self.db.get_user_sessions(user_id, limit)
    
    # Message Management
    async def add_message(self, session_id: str, user_id: str, message: str, response: str, source: str = "ai") -> str:
        """Add message to session"""
        if not self.db:
            raise RuntimeError("Database not initialized")
        return await self.db.add_message(session_id, user_id, message, response, source)
    
    async def get_session_messages(self, session_id: str, limit: int = 50, offset: int = 0):
        """Get session messages"""
        if not self.db:
            raise RuntimeError("Database not initialized")
        return await self.db.get_session_messages(session_id, limit, offset)
    
    async def get_user_message_history(self, user_id: str, limit: int = 100):
        """Get user's message history"""
        if not self.db:
            raise RuntimeError("Database not initialized")
        return await self.db.get_user_message_history(user_id, limit)
    
    # User Management
    async def create_user(self, username: str, email: str, hashed_password: str, full_name: Optional[str] = None) -> str:
        """Create new user"""
        if not self.db:
            raise RuntimeError("Database not initialized")
        return await self.db.create_user(username, email, hashed_password, full_name)
    
    async def get_user(self, username: str):
        """Get user by username"""
        if not self.db:
            raise RuntimeError("Database not initialized")
        return await self.db.get_user(username)
    
    async def update_user_last_login(self, user_id: str) -> bool:
        """Update user's last login"""
        if not self.db:
            raise RuntimeError("Database not initialized")
        return await self.db.update_user_last_login(user_id)
    
    # Analytics & System Stats
    async def get_analytics_data(self, start_date, end_date):
        """Get analytics data"""
        if not self.db:
            raise RuntimeError("Database not initialized")
        return await self.db.get_analytics_data(start_date, end_date)
    
    async def get_system_stats(self):
        """Get system statistics"""
        if not self.db:
            raise RuntimeError("Database not initialized")
        return await self.db.get_system_stats()
    
    # Backup & Maintenance
    async def create_backup(self, backup_path: str) -> bool:
        """Create database backup"""
        if not self.db:
            raise RuntimeError("Database not initialized")
        return await self.db.create_backup(backup_path)
    
    async def restore_backup(self, backup_path: str) -> bool:
        """Restore from backup"""
        if not self.db:
            raise RuntimeError("Database not initialized")
        return await self.db.restore_backup(backup_path)
    
    async def optimize_database(self):
        """Optimize database performance"""
        if not self.db:
            raise RuntimeError("Database not initialized")
        return await self.db.optimize_database()
    
    async def validate_data_integrity(self):
        """Validate data integrity"""
        if not self.db:
            raise RuntimeError("Database not initialized")
        return await self.db.validate_data_integrity()
    
    async def cleanup_old_data(self, days_to_keep: int = 90):
        """Clean up old data"""
        if not self.db:
            raise RuntimeError("Database not initialized")
        return await self.db.cleanup_old_data(days_to_keep)
    
    # Legacy compatibility methods (for gradual migration)
    def get_or_create_session(self, user_id: str, force_new: bool = False) -> str:
        """Legacy method - synchronous wrapper"""
        import asyncio
        
        if force_new:
            return asyncio.run(self.create_session(user_id))
        else:
            # Get existing session or create new
            sessions = asyncio.run(self.get_user_sessions(user_id, limit=1))
            if sessions:
                return sessions[0]['session_id']
            else:
                return asyncio.run(self.create_session(user_id))
    
    def get_current_session(self, user_id: str):
        """Legacy method - get current session"""
        import asyncio
        sessions = asyncio.run(self.get_user_sessions(user_id, limit=1))
        return sessions[0] if sessions else None
    
    def add_message_sync(self, session_id: str, user_id: str, message: str, response: str, source: str = "ai"):
        """Legacy synchronous add message"""
        import asyncio
        return asyncio.run(self.add_message(session_id, user_id, message, response, source))
    
    def get_chat_history(self, user_id: str, limit: int = 20):
        """Legacy method - get chat history"""
        import asyncio
        return asyncio.run(self.get_user_message_history(user_id, limit))
    
    def get_stats(self):
        """Legacy method - get statistics"""
        import asyncio
        try:
            return asyncio.run(self.get_system_stats())
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {
                "error": str(e),
                "status": self._health_status,
                "database_type": self.config.database_type if self.config else "unknown"
            }
    
    # Properties for compatibility
    @property
    def db_path(self):
        """Legacy property for SQLite compatibility"""
        if self.config and self.config.database_type == "sqlite":
            return self.config.database
        return None
    
    @property
    def created_at(self):
        """Legacy property"""
        return self.db.created_at if self.db else None
    
    async def close(self):
        """Close database connections"""
        if self.db:
            await self.db.close()
            self._initialized = False
            self._health_status = "closed"

# Global instance for backward compatibility
_global_db_manager: Optional[ProductionDatabaseManager] = None

async def get_database_manager() -> ProductionDatabaseManager:
    """Get or create global database manager instance"""
    global _global_db_manager
    
    if _global_db_manager is None:
        _global_db_manager = ProductionDatabaseManager()
        await _global_db_manager.initialize()
    
    return _global_db_manager

def get_database_manager_sync() -> ProductionDatabaseManager:
    """Synchronous wrapper for getting database manager"""
    import asyncio
    return asyncio.run(get_database_manager())

# Factory function for easy instantiation
def create_production_database_manager():
    """Create a new production database manager instance"""
    return ProductionDatabaseManager()
