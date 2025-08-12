"""
🗄️ Database Interface
====================
Abstract base class for database operations following Single Responsibility Principle.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime


class IDatabaseManager(ABC):
    """
    Interface for database operations.
    Single Responsibility: Database data access and persistence.
    """
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize database connection and setup"""
        pass
    
    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Check database health status"""
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        pass
    
    # User Management
    @abstractmethod
    def authenticate_user(self, username: str) -> Optional[Dict[str, Any]]:
        """Authenticate user and return user data"""
        pass
    
    @abstractmethod
    def create_user(self, username: str, email: str, hashed_password: str, **kwargs) -> str:
        """Create new user and return user ID"""
        pass
    
    @abstractmethod
    def update_last_login(self, username: str) -> bool:
        """Update user's last login timestamp"""
        pass
    
    # Session Management
    @abstractmethod
    def get_or_create_session(self, user_id: str, force_new: bool = False) -> str:
        """Get existing session or create new one"""
        pass
    
    @abstractmethod
    def get_user_sessions(self, user_id: str, limit: int = 15) -> List[Dict[str, Any]]:
        """Get user's chat sessions"""
        pass
    
    @abstractmethod
    def get_session_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """Get messages from a specific session"""
        pass
    
    # Message Management
    @abstractmethod
    def add_message(self, session_id: str, user_id: str, user_message: str, 
                   bot_response: str, source: str = "unknown", **metadata) -> bool:
        """Add new message to database"""
        pass
    
    @abstractmethod
    def get_recent_messages(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent messages for user"""
        pass
    
    # Cleanup
    @abstractmethod
    def close(self) -> None:
        """Close database connections"""
        pass


class IUserRepository(ABC):
    """
    User-specific database operations.
    Single Responsibility: User data management.
    """
    
    @abstractmethod
    def find_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        pass
    
    @abstractmethod
    def find_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        pass
    
    @abstractmethod
    def create(self, user_data: Dict[str, Any]) -> str:
        pass
    
    @abstractmethod
    def update(self, user_id: str, user_data: Dict[str, Any]) -> bool:
        pass
    
    @abstractmethod
    def delete(self, user_id: str) -> bool:
        pass


class ISessionRepository(ABC):
    """
    Session-specific database operations.
    Single Responsibility: Session data management.
    """
    
    @abstractmethod
    def create_session(self, user_id: str) -> str:
        pass
    
    @abstractmethod
    def find_by_user(self, user_id: str, limit: int = 15) -> List[Dict[str, Any]]:
        pass
    
    @abstractmethod
    def find_by_id(self, session_id: str) -> Optional[Dict[str, Any]]:
        pass
    
    @abstractmethod
    def update_session(self, session_id: str, data: Dict[str, Any]) -> bool:
        pass
