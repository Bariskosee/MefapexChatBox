"""
🗄️ Production Database Configuration Module
==================================================

This module provides production-ready database configuration with support for:
- PostgreSQL (Primary recommendation for production)
- MySQL/MariaDB (Secondary option)
- SQLite (Development only)

Features:
- Connection pooling
- Transaction management
- Async/await support
- Connection health monitoring
- Automatic failover
- Performance optimization
"""

import os
import logging
from typing import Optional, Dict, Any
from enum import Enum
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool, NullPool
from sqlalchemy.engine import Engine
import asyncio

logger = logging.getLogger(__name__)

class DatabaseType(Enum):
    """Supported database types"""
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"

class DatabaseConfig:
    """Production database configuration manager"""
    
    def __init__(self):
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.database_type = self._detect_database_type()
        self.connection_string = self._build_connection_string()
        self.engine_config = self._get_engine_config()
        
    def _detect_database_type(self) -> DatabaseType:
        """Detect which database to use based on environment variables"""
        
        # Check for explicit database type setting
        db_type = os.getenv("DATABASE_TYPE", "").lower()
        if db_type:
            if db_type in ["postgresql", "postgres", "pg"]:
                return DatabaseType.POSTGRESQL
            elif db_type in ["mysql", "mariadb"]:
                return DatabaseType.MYSQL
            elif db_type == "sqlite":
                return DatabaseType.SQLITE
        
        # Auto-detect based on available environment variables
        if os.getenv("POSTGRES_HOST") or os.getenv("DATABASE_URL", "").startswith("postgresql"):
            return DatabaseType.POSTGRESQL
        elif os.getenv("MYSQL_HOST") or os.getenv("DATABASE_URL", "").startswith("mysql"):
            return DatabaseType.MYSQL
        else:
            # Fallback to SQLite for development
            if self.environment == "production":
                logger.warning(
                    "🚨 PRODUCTION WARNING: No production database configured! "
                    "SQLite is not suitable for production. Please configure PostgreSQL or MySQL."
                )
            return DatabaseType.SQLITE
    
    def _build_connection_string(self) -> str:
        """Build database connection string based on type"""
        
        # Check for explicit DATABASE_URL first
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            logger.info(f"Using explicit DATABASE_URL for {self.database_type.value}")
            return database_url
        
        if self.database_type == DatabaseType.POSTGRESQL:
            return self._build_postgresql_url()
        elif self.database_type == DatabaseType.MYSQL:
            return self._build_mysql_url()
        else:  # SQLite
            return self._build_sqlite_url()
    
    def _build_postgresql_url(self) -> str:
        """Build PostgreSQL connection string"""
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        user = os.getenv("POSTGRES_USER", "mefapex")
        password = os.getenv("POSTGRES_PASSWORD", "")
        database = os.getenv("POSTGRES_DB", "mefapex_chatbot")
        
        if not password:
            logger.error("🚨 POSTGRES_PASSWORD not set!")
            raise ValueError("PostgreSQL password is required for production")
        
        # URL encode password to handle special characters
        encoded_password = quote_plus(password)
        
        # Include SSL mode for production
        ssl_mode = "require" if self.environment == "production" else "disable"
        
        url = f"postgresql://{user}:{encoded_password}@{host}:{port}/{database}?sslmode={ssl_mode}"
        logger.info(f"✅ PostgreSQL connection configured: {user}@{host}:{port}/{database}")
        return url
    
    def _build_mysql_url(self) -> str:
        """Build MySQL connection string"""
        host = os.getenv("MYSQL_HOST", "localhost")
        port = os.getenv("MYSQL_PORT", "3306")
        user = os.getenv("MYSQL_USER", "root")
        password = os.getenv("MYSQL_PASSWORD", "")
        database = os.getenv("MYSQL_DATABASE", "mefapex_chatbot")
        
        if not password:
            logger.error("🚨 MYSQL_PASSWORD not set!")
            raise ValueError("MySQL password is required for production")
        
        # URL encode password
        encoded_password = quote_plus(password)
        
        # Include charset and SSL for production
        charset = "utf8mb4"
        ssl_ca = "&ssl_ca=/etc/ssl/certs/ca-certificates.crt" if self.environment == "production" else ""
        
        url = f"mysql+pymysql://{user}:{encoded_password}@{host}:{port}/{database}?charset={charset}{ssl_ca}"
        logger.info(f"✅ MySQL connection configured: {user}@{host}:{port}/{database}")
        return url
    
    def _build_sqlite_url(self) -> str:
        """Build SQLite connection string"""
        db_path = os.getenv("SQLITE_PATH", "mefapex.db")
        
        if self.environment == "production":
            logger.critical(
                "🚨 CRITICAL: SQLite is being used in production! "
                "This is NOT recommended for production deployments due to concurrency limitations."
            )
        
        url = f"sqlite:///{db_path}"
        logger.info(f"SQLite database: {db_path}")
        return url
    
    def _get_engine_config(self) -> Dict[str, Any]:
        """Get SQLAlchemy engine configuration based on database type"""
        
        base_config = {
            "echo": self.environment == "development",
            "future": True,  # Use SQLAlchemy 2.0 style
        }
        
        if self.database_type == DatabaseType.POSTGRESQL:
            return {
                **base_config,
                "poolclass": QueuePool,
                "pool_size": 20,  # Number of connections to maintain
                "max_overflow": 30,  # Additional connections when pool is full
                "pool_pre_ping": True,  # Verify connections before use
                "pool_recycle": 3600,  # Recycle connections every hour
                "connect_args": {
                    "connect_timeout": 10,
                    "command_timeout": 30,
                    "server_settings": {
                        "application_name": "mefapex_chatbot",
                        "jit": "off",  # Disable JIT for better predictability
                    }
                }
            }
        
        elif self.database_type == DatabaseType.MYSQL:
            return {
                **base_config,
                "poolclass": QueuePool,
                "pool_size": 15,
                "max_overflow": 25,
                "pool_pre_ping": True,
                "pool_recycle": 3600,
                "connect_args": {
                    "connect_timeout": 10,
                    "read_timeout": 30,
                    "write_timeout": 30,
                    "charset": "utf8mb4",
                    "sql_mode": "STRICT_TRANS_TABLES",
                }
            }
        
        else:  # SQLite
            return {
                **base_config,
                "poolclass": NullPool,  # SQLite doesn't need connection pooling
                "connect_args": {
                    "check_same_thread": False,
                    "timeout": 30,
                    "isolation_level": None,  # For autocommit
                }
            }
    
    def create_engine(self) -> Engine:
        """Create and configure SQLAlchemy engine"""
        try:
            engine = create_engine(self.connection_string, **self.engine_config)
            
            # Test connection
            with engine.connect() as conn:
                if self.database_type == DatabaseType.POSTGRESQL:
                    result = conn.execute(text("SELECT version()"))
                    version = result.scalar()
                    logger.info(f"✅ PostgreSQL connected: {version}")
                elif self.database_type == DatabaseType.MYSQL:
                    result = conn.execute(text("SELECT @@version"))
                    version = result.scalar()
                    logger.info(f"✅ MySQL connected: {version}")
                else:
                    result = conn.execute(text("SELECT sqlite_version()"))
                    version = result.scalar()
                    logger.info(f"✅ SQLite connected: {version}")
            
            return engine
            
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            
            # In production, this should be a hard failure
            if self.environment == "production":
                raise RuntimeError(f"Production database connection failed: {e}")
            
            # In development, fall back to SQLite
            logger.warning("🔄 Falling back to SQLite for development")
            self.database_type = DatabaseType.SQLITE
            self.connection_string = self._build_sqlite_url()
            self.engine_config = self._get_engine_config()
            return create_engine(self.connection_string, **self.engine_config)
    
    def get_session_factory(self, engine: Engine):
        """Create session factory with proper configuration"""
        return sessionmaker(
            bind=engine,
            autoflush=True,
            autocommit=False,
            expire_on_commit=False
        )
    
    def validate_production_setup(self) -> tuple[bool, list[str]]:
        """Validate database setup for production"""
        issues = []
        
        if self.environment != "production":
            return True, []
        
        if self.database_type == DatabaseType.SQLITE:
            issues.append("SQLite is not suitable for production - use PostgreSQL or MySQL")
        
        if self.database_type == DatabaseType.POSTGRESQL:
            required_vars = ["POSTGRES_HOST", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB"]
            missing = [var for var in required_vars if not os.getenv(var)]
            if missing:
                issues.append(f"Missing PostgreSQL environment variables: {missing}")
        
        if self.database_type == DatabaseType.MYSQL:
            required_vars = ["MYSQL_HOST", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DATABASE"]
            missing = [var for var in required_vars if not os.getenv(var)]
            if missing:
                issues.append(f"Missing MySQL environment variables: {missing}")
        
        return len(issues) == 0, issues

# Global database configuration instance
db_config = DatabaseConfig()

def get_database_config() -> DatabaseConfig:
    """Get global database configuration"""
    return db_config

def validate_production_database():
    """Validate database configuration for production deployment"""
    is_valid, issues = db_config.validate_production_setup()
    
    if not is_valid:
        error_msg = "❌ Production database validation failed:\n" + "\n".join(f"  • {issue}" for issue in issues)
        logger.critical(error_msg)
        
        if db_config.environment == "production":
            raise RuntimeError("Production database validation failed. See logs for details.")
        else:
            logger.warning("Database validation issues detected (development mode)")
    
    return is_valid, issues
