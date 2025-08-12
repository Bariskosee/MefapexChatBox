"""
🔐 MEFAPEX Authentication Service
Unified authentication system consolidating all auth-related functionality

Features:
- JWT token creation and verification
- Password hashing and verification  
- User authentication
- Demo user handling
- Brute force protection
- Security validation
"""

import os
import secrets
import hashlib
import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from collections import defaultdict

from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from jose import JWTError, jwt

# Initialize logger
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()

class AuthenticationService:
    """Unified Authentication Service"""
    
    def __init__(self, secret_key: str = None, environment: str = "development"):
        """Initialize authentication service with configuration"""
        
        # Environment setup
        self.environment = environment
        
        # JWT Configuration
        self.secret_key = secret_key or self._generate_secret_key()
        self.algorithm = "HS256"
        self.access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
        
        # Password hashing
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        # Demo user configuration
        self.demo_user_enabled = os.getenv("DEMO_USER_ENABLED", "true").lower() == "true"
        self.demo_password = os.getenv("DEMO_PASSWORD", "1234")
        
        # Security settings
        self.min_password_length = int(os.getenv("MIN_PASSWORD_LENGTH", "4"))
        self.max_password_length = int(os.getenv("MAX_PASSWORD_LENGTH", "128"))
        
        # Brute force protection
        self.brute_force_protection = BruteForceProtection()
        
        # Production security checks
        self._validate_production_security()
        
        logger.info(f"🔐 Authentication service initialized for {environment} environment")
    
    def _generate_secret_key(self) -> str:
        """Generate secure SECRET_KEY if not provided"""
        if self.environment == "production":
            logger.error("🚨 SECURITY ALERT: SECRET_KEY not set in production!")
            raise RuntimeError("SECRET_KEY must be set in production environment variables.")
        else:
            secret_key = secrets.token_urlsafe(32)
            logger.warning("⚠️ Using auto-generated SECRET_KEY for development")
            return secret_key
    
    def _validate_production_security(self):
        """Validate security settings for production"""
        if self.environment == "production":
            # Check demo user in production
            if self.demo_user_enabled:
                logger.error("🚨 CRITICAL SECURITY ALERT: Demo user is enabled in production!")
                if not os.getenv("FORCE_DEMO_IN_PRODUCTION", "false").lower() == "true":
                    self.demo_user_enabled = False
                    logger.warning("🔒 Demo user automatically disabled for production security")
            
            # Check weak demo password
            if self.demo_password == "1234" and self.demo_user_enabled:
                logger.critical("🚨 SECURITY ALERT: Demo user using default weak password in production!")
                if not os.getenv("ACCEPT_WEAK_DEMO_PASSWORD", "false").lower() == "true":
                    self.demo_user_enabled = False
                    logger.warning("🔒 Demo user disabled due to weak password")
    
    # 🔒 PASSWORD MANAGEMENT
    def validate_password_strength(self, password: str) -> Tuple[bool, str]:
        """Validate password strength"""
        if len(password) < self.min_password_length:
            return False, f"Şifre en az {self.min_password_length} karakter olmalıdır"
        
        if len(password) > self.max_password_length:
            return False, f"Şifre en fazla {self.max_password_length} karakter olabilir"
        
        return True, "Password is valid"
    
    def get_password_hash(self, password: str) -> str:
        """Hash a password with enhanced security"""
        try:
            # Validate password first
            is_valid, message = self.validate_password_strength(password)
            if not is_valid:
                raise HTTPException(status_code=400, detail=message)
            
            return self.pwd_context.hash(password)
        except Exception as e:
            logger.error(f"Password hashing error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Password processing failed"
            )
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        try:
            # Support both bcrypt (new) and legacy hash format
            if ":" in hashed_password:
                # Legacy hash format (hash:salt)
                return self._verify_legacy_password(plain_password, hashed_password)
            else:
                # New bcrypt format
                return self.pwd_context.verify(plain_password, hashed_password)
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False
    
    def _verify_legacy_password(self, password: str, hashed: str) -> bool:
        """Verify legacy password format (hash:salt)"""
        try:
            hash_part, salt = hashed.split(":")
            return hashlib.sha256((password + salt).encode()).hexdigest() == hash_part
        except ValueError:
            return False
    
    def hash_password_legacy(self, password: str) -> str:
        """Hash password with legacy salt format (for compatibility)"""
        salt = secrets.token_hex(16)
        return hashlib.sha256((password + salt).encode()).hexdigest() + ":" + salt
    
    # 🎫 JWT TOKEN MANAGEMENT
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token with enhanced security"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        # Add security claims
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": str(uuid.uuid4()),  # Unique token ID
            "iss": "mefapex-api",  # Issuer
        })
        
        try:
            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
            return encoded_jwt
        except Exception as e:
            logger.error(f"Token creation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Token creation failed"
            )
    
    def verify_token(self, credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
        """Verify JWT token and return user data"""
        try:
            payload = jwt.decode(credentials.credentials, self.secret_key, algorithms=[self.algorithm])
            username: str = payload.get("sub")
            user_id: str = payload.get("user_id")
            
            if username is None or user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            return {"username": username, "user_id": user_id, "payload": payload}
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.JWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    # 👤 USER AUTHENTICATION
    def authenticate_user(self, username: str, password: str, users_db: dict = None) -> dict:
        """Authenticate user credentials"""
        try:
            # Demo user support
            if self.demo_user_enabled and username == "demo" and password == self.demo_password:
                logger.info("✅ Demo user authenticated")
                return {
                    "username": "demo", 
                    "user_id": "demo_user_id",
                    "hashed_password": self.get_password_hash(self.demo_password),
                    "is_demo": True
                }
            
            # Database user authentication
            from database_manager import db_manager
            user_data = db_manager.authenticate_user(username)
            
            if user_data and self.verify_password(password, user_data["password_hash"]):
                # Update last login
                db_manager.update_last_login(username)
                logger.info(f"✅ User authenticated: {username}")
                return {
                    "username": username,
                    "user_id": str(user_data["id"]),
                    "email": user_data.get("email"),
                    "is_active": user_data.get("is_active", True),
                    "hashed_password": user_data["password_hash"],
                    "is_demo": False
                }
            
            # Fallback to provided users_db for compatibility
            if users_db and username in users_db:
                user = users_db[username]
                if self.verify_password(password, user["hashed_password"]):
                    logger.info(f"✅ User authenticated: {username}")
                    return user
            
            logger.warning(f"❌ Authentication failed for user: {username}")
            return False
            
        except Exception as e:
            logger.error(f"Database authentication error: {e}")
            logger.warning(f"❌ Authentication failed for user: {username}")
            return False
    
    def authenticate_demo_user(self, username: str, password: str) -> bool:
        """Specific demo user authentication"""
        return (self.demo_user_enabled and 
                username == "demo" and 
                password == self.demo_password)
    
    # 🛡️ SECURITY UTILITIES
    def get_client_ip(self, request) -> str:
        """Extract client IP address from request"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        return request.client.host if request.client else "unknown"
    
    def check_brute_force(self, client_ip: str) -> bool:
        """Check if IP is blocked due to brute force attempts"""
        return self.brute_force_protection.is_blocked(client_ip)
    
    def record_failed_attempt(self, client_ip: str):
        """Record failed login attempt"""
        self.brute_force_protection.record_failed_attempt(client_ip)
    
    def record_successful_login(self, client_ip: str):
        """Record successful login (reset failed attempts)"""
        self.brute_force_protection.reset_failed_attempts(client_ip)


class BruteForceProtection:
    """Brute force protection system"""
    
    def __init__(self):
        self.failed_attempts = defaultdict(list)
        self.blocked_ips = defaultdict(datetime)
        self.max_attempts = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
        self.block_duration = int(os.getenv("BLOCK_DURATION_MINUTES", "15"))
        
    def is_blocked(self, client_ip: str) -> bool:
        """Check if IP is currently blocked"""
        if client_ip in self.blocked_ips:
            if datetime.utcnow() < self.blocked_ips[client_ip]:
                return True
            else:
                # Unblock expired blocks
                del self.blocked_ips[client_ip]
                return False
        return False
    
    def record_failed_attempt(self, client_ip: str):
        """Record a failed login attempt"""
        now = datetime.utcnow()
        
        # Clean old attempts (older than 1 hour)
        self.failed_attempts[client_ip] = [
            attempt for attempt in self.failed_attempts[client_ip]
            if now - attempt < timedelta(hours=1)
        ]
        
        # Add new attempt
        self.failed_attempts[client_ip].append(now)
        
        # Check if should block
        if len(self.failed_attempts[client_ip]) >= self.max_attempts:
            self.blocked_ips[client_ip] = now + timedelta(minutes=self.block_duration)
            logger.warning(f"🚨 IP blocked due to brute force: {client_ip}")
    
    def reset_failed_attempts(self, client_ip: str):
        """Reset failed attempts for successful login"""
        if client_ip in self.failed_attempts:
            del self.failed_attempts[client_ip]
        if client_ip in self.blocked_ips:
            del self.blocked_ips[client_ip]


# 🌍 GLOBAL AUTHENTICATION INSTANCE
# Will be initialized by main application
auth_service: Optional[AuthenticationService] = None

def get_auth_service() -> AuthenticationService:
    """Get global authentication service instance"""
    if auth_service is None:
        raise RuntimeError("Authentication service not initialized. Call init_auth_service() first.")
    return auth_service

def init_auth_service(secret_key: str = None, environment: str = "development") -> AuthenticationService:
    """Initialize global authentication service"""
    global auth_service
    auth_service = AuthenticationService(secret_key=secret_key, environment=environment)
    return auth_service

# 🎯 CONVENIENCE FUNCTIONS
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Convenience function for token creation"""
    return get_auth_service().create_access_token(data, expires_delta)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Convenience function for password verification"""
    return get_auth_service().verify_password(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Convenience function for password hashing"""
    return get_auth_service().get_password_hash(password)

def authenticate_user(username: str, password: str, users_db: dict = None) -> dict:
    """Convenience function for user authentication"""
    return get_auth_service().authenticate_user(username, password, users_db)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Convenience function for token verification"""
    return get_auth_service().verify_token(credentials)

def validate_password_strength(password: str) -> Tuple[bool, str]:
    """Convenience function for password validation"""
    return get_auth_service().validate_password_strength(password)
