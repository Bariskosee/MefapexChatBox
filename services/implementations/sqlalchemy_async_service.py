"""
🗄️ SQLAlchemy Async Database Service
====================================
Modern async SQLAlchemy implementation with Pydantic models and FastAPI best practices.
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Union
from contextlib import asynccontextmanager

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, selectinload
from sqlalchemy import (
    Column, String, Integer, DateTime, Boolean, Text, JSON, 
    ForeignKey, Index, UniqueConstraint, CheckConstraint,
    select, update, delete, func, and_, or_
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from pydantic import BaseModel, Field, validator
from fastapi import HTTPException, status

from core.interfaces.database_interface import IDatabaseManager, IUserRepository, ISessionRepository
from core.interfaces.config_interface import IConfigurationService

logger = logging.getLogger(__name__)

# SQLAlchemy Base
Base = declarative_base()


# ================================
# SQLAlchemy Models
# ================================

class UserModel(Base):
    """SQLAlchemy User model with async support"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Status and Security
    is_active = Column(Boolean, default=True, nullable=False)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    sessions = relationship("SessionModel", back_populates="user", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('failed_login_attempts >= 0', name='check_failed_attempts_positive'),
        Index('idx_users_active_username', 'username', 'is_active'),
    )


class SessionModel(Base):
    """SQLAlchemy Session model with async support"""
    __tablename__ = "chat_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    user_id = Column(String(255), ForeignKey("users.user_id"), nullable=False, index=True)
    
    # Session metadata
    session_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    message_count = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_activity = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    user = relationship("UserModel", back_populates="sessions")
    messages = relationship("MessageModel", back_populates="session", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('message_count >= 0', name='check_message_count_positive'),
        Index('idx_sessions_user_active', 'user_id', 'is_active'),
        Index('idx_sessions_last_activity', 'last_activity'),
    )


class MessageModel(Base):
    """SQLAlchemy Message model with async support"""
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.session_id"), nullable=False, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    
    # Message content
    user_message = Column(Text, nullable=False)
    bot_response = Column(Text, nullable=False)
    source = Column(String(50), default="unknown", nullable=False)
    
    # Message metadata
    metadata = Column(JSONB, nullable=True)
    confidence_score = Column(String(10), nullable=True)  # For AI response confidence
    processing_time_ms = Column(Integer, nullable=True)
    
    # Timestamps
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    session = relationship("SessionModel", back_populates="messages")
    
    # Constraints
    __table_args__ = (
        Index('idx_messages_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_messages_session_timestamp', 'session_id', 'timestamp'),
        Index('idx_messages_source', 'source'),
    )


# ================================
# Pydantic Schemas
# ================================

class UserBase(BaseModel):
    """Base user schema"""
    username: str = Field(..., min_length=3, max_length=50, regex=r'^[a-zA-Z0-9_]+$')
    email: Optional[str] = Field(None, regex=r'^[^@]+@[^@]+\.[^@]+$')
    full_name: Optional[str] = Field(None, max_length=255)


class UserCreate(UserBase):
    """User creation schema"""
    password: str = Field(..., min_length=8, max_length=128)
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength"""
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in v):
            raise ValueError('Password must contain at least one special character')
        return v


class UserUpdate(BaseModel):
    """User update schema"""
    email: Optional[str] = Field(None, regex=r'^[^@]+@[^@]+\.[^@]+$')
    full_name: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    """User response schema"""
    user_id: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime]
    
    class Config:
        from_attributes = True


class SessionBase(BaseModel):
    """Base session schema"""
    session_name: Optional[str] = Field(None, max_length=255)


class SessionCreate(SessionBase):
    """Session creation schema"""
    user_id: str


class SessionResponse(SessionBase):
    """Session response schema"""
    session_id: str
    user_id: str
    is_active: bool
    message_count: int
    created_at: datetime
    updated_at: datetime
    last_activity: datetime
    
    class Config:
        from_attributes = True


class MessageBase(BaseModel):
    """Base message schema"""
    user_message: str = Field(..., min_length=1, max_length=4000)
    source: str = Field(default="user", max_length=50)


class MessageCreate(MessageBase):
    """Message creation schema"""
    session_id: str
    user_id: str
    bot_response: str = Field(..., min_length=1, max_length=4000)
    metadata: Optional[Dict[str, Any]] = None
    confidence_score: Optional[str] = None
    processing_time_ms: Optional[int] = None


class MessageResponse(MessageBase):
    """Message response schema"""
    id: int
    session_id: str
    user_id: str
    bot_response: str
    metadata: Optional[Dict[str, Any]]
    confidence_score: Optional[str]
    processing_time_ms: Optional[int]
    timestamp: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True


# ================================
# Database Connection Manager
# ================================

class AsyncDatabaseManager:
    """Async database connection manager"""
    
    def __init__(self, config_service: IConfigurationService):
        self.config_service = config_service
        self.engine = None
        self.async_session_maker = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize async database connection"""
        if self._initialized:
            return
        
        try:
            db_config = self.config_service.get_database_config()
            
            # Create async engine
            self.engine = create_async_engine(
                db_config["async_url"],
                echo=self.config_service.is_development(),
                pool_size=db_config.get("max_connections", 20),
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=3600,
                pool_pre_ping=True
            )
            
            # Create session maker
            self.async_session_maker = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Create tables
            await self.create_tables()
            
            self._initialized = True
            logger.info("✅ Async database manager initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize async database: {e}")
            raise
    
    async def create_tables(self):
        """Create database tables"""
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("✅ Database tables created/verified")
        except Exception as e:
            logger.error(f"❌ Failed to create tables: {e}")
            raise
    
    @asynccontextmanager
    async def get_session(self):
        """Get async database session"""
        if not self._initialized:
            await self.initialize()
        
        async with self.async_session_maker() as session:
            try:
                yield session
            except Exception as e:
                await session.rollback()
                logger.error(f"Database session error: {e}")
                raise
            finally:
                await session.close()
    
    async def health_check(self) -> Dict[str, Any]:
        """Async health check"""
        try:
            async with self.get_session() as session:
                result = await session.execute(select(func.now()))
                db_time = result.scalar()
                
                # Get database stats
                user_count = await session.scalar(select(func.count(UserModel.id)))
                session_count = await session.scalar(select(func.count(SessionModel.id)))
                message_count = await session.scalar(select(func.count(MessageModel.id)))
                
                return {
                    "status": "healthy",
                    "database": "postgresql",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "db_time": db_time.isoformat() if db_time else None,
                    "stats": {
                        "users": user_count,
                        "sessions": session_count,
                        "messages": message_count
                    }
                }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def close(self):
        """Close database connections"""
        if self.engine:
            await self.engine.dispose()
            logger.info("🔒 Database connections closed")


# ================================
# Repository Implementations
# ================================

class AsyncUserRepository(IUserRepository):
    """Async user repository implementation"""
    
    def __init__(self, db_manager: AsyncDatabaseManager):
        self.db_manager = db_manager
    
    async def find_by_username(self, username: str) -> Optional[UserResponse]:
        """Find user by username"""
        try:
            async with self.db_manager.get_session() as session:
                stmt = select(UserModel).where(
                    and_(UserModel.username == username, UserModel.is_active == True)
                )
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()
                
                if user:
                    return UserResponse.from_orm(user)
                return None
                
        except Exception as e:
            logger.error(f"Failed to find user by username: {e}")
            return None
    
    async def find_by_email(self, email: str) -> Optional[UserResponse]:
        """Find user by email"""
        try:
            async with self.db_manager.get_session() as session:
                stmt = select(UserModel).where(
                    and_(UserModel.email == email, UserModel.is_active == True)
                )
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()
                
                if user:
                    return UserResponse.from_orm(user)
                return None
                
        except Exception as e:
            logger.error(f"Failed to find user by email: {e}")
            return None
    
    async def create(self, user_data: UserCreate, hashed_password: str) -> UserResponse:
        """Create new user"""
        try:
            async with self.db_manager.get_session() as session:
                db_user = UserModel(
                    username=user_data.username,
                    email=user_data.email,
                    full_name=user_data.full_name,
                    hashed_password=hashed_password
                )
                
                session.add(db_user)
                await session.commit()
                await session.refresh(db_user)
                
                logger.info(f"✅ User created: {user_data.username}")
                return UserResponse.from_orm(db_user)
                
        except IntegrityError as e:
            logger.error(f"User creation failed - integrity error: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username or email already exists"
            )
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User creation failed"
            )
    
    async def update(self, user_id: str, user_data: UserUpdate) -> Optional[UserResponse]:
        """Update user"""
        try:
            async with self.db_manager.get_session() as session:
                stmt = select(UserModel).where(UserModel.user_id == user_id)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()
                
                if not user:
                    return None
                
                # Update fields
                update_data = user_data.dict(exclude_unset=True)
                for field, value in update_data.items():
                    setattr(user, field, value)
                
                user.updated_at = datetime.now(timezone.utc)
                
                await session.commit()
                await session.refresh(user)
                
                logger.info(f"✅ User updated: {user.username}")
                return UserResponse.from_orm(user)
                
        except Exception as e:
            logger.error(f"Failed to update user: {e}")
            return None
    
    async def update_last_login(self, username: str) -> bool:
        """Update user's last login timestamp"""
        try:
            async with self.db_manager.get_session() as session:
                stmt = (
                    update(UserModel)
                    .where(UserModel.username == username)
                    .values(last_login=datetime.now(timezone.utc))
                )
                result = await session.execute(stmt)
                await session.commit()
                
                return result.rowcount > 0
                
        except Exception as e:
            logger.error(f"Failed to update last login: {e}")
            return False
    
    async def delete(self, user_id: str) -> bool:
        """Soft delete user"""
        return await self.update(user_id, UserUpdate(is_active=False)) is not None


class AsyncSessionRepository(ISessionRepository):
    """Async session repository implementation"""
    
    def __init__(self, db_manager: AsyncDatabaseManager):
        self.db_manager = db_manager
    
    async def create_session(self, user_id: str, session_name: Optional[str] = None) -> SessionResponse:
        """Create new session"""
        try:
            async with self.db_manager.get_session() as session:
                db_session = SessionModel(
                    user_id=user_id,
                    session_name=session_name
                )
                
                session.add(db_session)
                await session.commit()
                await session.refresh(db_session)
                
                logger.info(f"✅ Session created: {db_session.session_id} for user {user_id}")
                return SessionResponse.from_orm(db_session)
                
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Session creation failed"
            )
    
    async def find_by_user(self, user_id: str, limit: int = 15) -> List[SessionResponse]:
        """Find sessions by user ID"""
        try:
            async with self.db_manager.get_session() as session:
                stmt = (
                    select(SessionModel)
                    .where(and_(SessionModel.user_id == user_id, SessionModel.is_active == True))
                    .order_by(SessionModel.last_activity.desc())
                    .limit(limit)
                )
                result = await session.execute(stmt)
                sessions = result.scalars().all()
                
                return [SessionResponse.from_orm(s) for s in sessions]
                
        except Exception as e:
            logger.error(f"Failed to find sessions by user: {e}")
            return []
    
    async def find_by_id(self, session_id: str) -> Optional[SessionResponse]:
        """Find session by ID"""
        try:
            async with self.db_manager.get_session() as session:
                stmt = select(SessionModel).where(SessionModel.session_id == session_id)
                result = await session.execute(stmt)
                session_obj = result.scalar_one_or_none()
                
                if session_obj:
                    return SessionResponse.from_orm(session_obj)
                return None
                
        except Exception as e:
            logger.error(f"Failed to find session by ID: {e}")
            return None
    
    async def update_session(self, session_id: str, data: Dict[str, Any]) -> bool:
        """Update session data"""
        try:
            async with self.db_manager.get_session() as session:
                stmt = (
                    update(SessionModel)
                    .where(SessionModel.session_id == session_id)
                    .values(**data, updated_at=datetime.now(timezone.utc))
                )
                result = await session.execute(stmt)
                await session.commit()
                
                return result.rowcount > 0
                
        except Exception as e:
            logger.error(f"Failed to update session: {e}")
            return False


# ================================
# Main Database Service
# ================================

class AsyncSQLAlchemyDatabaseService(IDatabaseManager):
    """Main async SQLAlchemy database service implementing IDatabaseManager"""
    
    def __init__(self, config_service: IConfigurationService):
        self.config_service = config_service
        self.db_manager = AsyncDatabaseManager(config_service)
        self.user_repository = AsyncUserRepository(self.db_manager)
        self.session_repository = AsyncSessionRepository(self.db_manager)
    
    async def initialize(self) -> bool:
        """Initialize database service"""
        try:
            await self.db_manager.initialize()
            return True
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """Sync health check wrapper"""
        # For compatibility with sync interface, run async health check
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.db_manager.health_check())
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        return asyncio.run(self.db_manager.health_check()).get("stats", {})
    
    # User Management (async wrappers for compatibility)
    def authenticate_user(self, username: str) -> Optional[Dict[str, Any]]:
        """Authenticate user - sync wrapper"""
        async def _authenticate():
            user = await self.user_repository.find_by_username(username)
            return user.dict() if user else None
        
        return asyncio.run(_authenticate())
    
    def create_user(self, username: str, email: str, hashed_password: str, **kwargs) -> str:
        """Create user - sync wrapper"""
        async def _create():
            user_data = UserCreate(
                username=username,
                email=email,
                password="dummy",  # Not used, hashed_password provided
                **kwargs
            )
            user = await self.user_repository.create(user_data, hashed_password)
            return str(user.user_id)
        
        return asyncio.run(_create())
    
    def update_last_login(self, username: str) -> bool:
        """Update last login - sync wrapper"""
        return asyncio.run(self.user_repository.update_last_login(username))
    
    # Session Management (async wrappers for compatibility)
    def get_or_create_session(self, user_id: str, force_new: bool = False) -> str:
        """Get or create session - sync wrapper"""
        async def _get_or_create():
            if not force_new:
                sessions = await self.session_repository.find_by_user(user_id, limit=1)
                if sessions:
                    return str(sessions[0].session_id)
            
            session = await self.session_repository.create_session(user_id)
            return str(session.session_id)
        
        return asyncio.run(_get_or_create())
    
    def get_user_sessions(self, user_id: str, limit: int = 15) -> List[Dict[str, Any]]:
        """Get user sessions - sync wrapper"""
        async def _get_sessions():
            sessions = await self.session_repository.find_by_user(user_id, limit)
            return [session.dict() for session in sessions]
        
        return asyncio.run(_get_sessions())
    
    def get_session_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """Get session messages - sync wrapper"""
        async def _get_messages():
            async with self.db_manager.get_session() as session:
                stmt = (
                    select(MessageModel)
                    .where(MessageModel.session_id == session_id)
                    .order_by(MessageModel.created_at.asc())
                )
                result = await session.execute(stmt)
                messages = result.scalars().all()
                
                return [MessageResponse.from_orm(msg).dict() for msg in messages]
        
        return asyncio.run(_get_messages())
    
    def add_message(self, session_id: str, user_id: str, user_message: str, 
                   bot_response: str, source: str = "unknown", **metadata) -> bool:
        """Add message - sync wrapper"""
        async def _add_message():
            try:
                async with self.db_manager.get_session() as session:
                    message = MessageModel(
                        session_id=session_id,
                        user_id=user_id,
                        user_message=user_message,
                        bot_response=bot_response,
                        source=source,
                        metadata=metadata
                    )
                    
                    session.add(message)
                    
                    # Update session message count
                    stmt = (
                        update(SessionModel)
                        .where(SessionModel.session_id == session_id)
                        .values(
                            message_count=SessionModel.message_count + 1,
                            last_activity=datetime.now(timezone.utc),
                            updated_at=datetime.now(timezone.utc)
                        )
                    )
                    await session.execute(stmt)
                    
                    await session.commit()
                    return True
                    
            except Exception as e:
                logger.error(f"Failed to add message: {e}")
                return False
        
        return asyncio.run(_add_message())
    
    def get_recent_messages(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent messages - sync wrapper"""
        async def _get_recent():
            async with self.db_manager.get_session() as session:
                stmt = (
                    select(MessageModel)
                    .where(MessageModel.user_id == user_id)
                    .order_by(MessageModel.timestamp.desc())
                    .limit(limit)
                )
                result = await session.execute(stmt)
                messages = result.scalars().all()
                
                return [MessageResponse.from_orm(msg).dict() for msg in messages]
        
        return asyncio.run(_get_recent())
    
    def close(self) -> None:
        """Close database connections"""
        asyncio.run(self.db_manager.close())
