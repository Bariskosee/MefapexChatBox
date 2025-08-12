"""
🔐 Authentication Interface
===========================
Abstract base class for authentication operations following Single Responsibility Principle.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
from datetime import timedelta


class IAuthenticationService(ABC):
    """
    Interface for authentication operations.
    Single Responsibility: User authentication and authorization.
    """
    
    @abstractmethod
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user credentials"""
        pass
    
    @abstractmethod
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        pass
    
    @abstractmethod
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT token and return user data"""
        pass
    
    @abstractmethod
    def get_password_hash(self, password: str) -> str:
        """Hash a password"""
        pass
    
    @abstractmethod
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        pass
    
    @abstractmethod
    def validate_password_strength(self, password: str) -> Tuple[bool, str]:
        """Validate password strength"""
        pass


class IPasswordService(ABC):
    """
    Password management service.
    Single Responsibility: Password hashing and validation.
    """
    
    @abstractmethod
    def hash_password(self, password: str) -> str:
        pass
    
    @abstractmethod
    def verify_password(self, password: str, hash: str) -> bool:
        pass
    
    @abstractmethod
    def validate_strength(self, password: str) -> Tuple[bool, str]:
        pass


class ITokenService(ABC):
    """
    Token management service.
    Single Responsibility: JWT token operations.
    """
    
    @abstractmethod
    def create_token(self, payload: Dict[str, Any], expires_in: Optional[timedelta] = None) -> str:
        pass
    
    @abstractmethod
    def verify_token(self, token: str) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def decode_token(self, token: str) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def is_token_expired(self, token: str) -> bool:
        pass


class IBruteForceProtectionService(ABC):
    """
    Brute force protection service.
    Single Responsibility: Security attack prevention.
    """
    
    @abstractmethod
    def is_blocked(self, client_ip: str) -> bool:
        pass
    
    @abstractmethod
    def record_failed_attempt(self, client_ip: str) -> None:
        pass
    
    @abstractmethod
    def record_successful_login(self, client_ip: str) -> None:
        pass
    
    @abstractmethod
    def get_attempt_count(self, client_ip: str) -> int:
        pass
