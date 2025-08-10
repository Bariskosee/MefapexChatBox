"""
🔐 Authentication Router
User registration, login, and JWT token management
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt, JWTError
import hashlib
import secrets
import logging
import os

from pydantic import BaseModel, EmailStr

logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()

# Models
class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

class LoginResponse(BaseModel):
    success: bool
    message: str
    token: Optional[str] = None

# Router
router = APIRouter(prefix="/auth", tags=["authentication"])

# Configuration (will be injected from main)
SECRET_KEY = None
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
db_manager = None

def init_auth_router(secret_key: str, database_manager):
    """Initialize router with dependencies from main app"""
    global SECRET_KEY, db_manager
    SECRET_KEY = secret_key
    db_manager = database_manager

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token and return user data"""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: str = payload.get("user_id")
        
        if username is None or user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return {"username": username, "user_id": user_id}
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def hash_password(password: str) -> str:
    """Hash password with salt"""
    salt = secrets.token_hex(16)
    return hashlib.sha256((password + salt).encode()).hexdigest() + ":" + salt

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    try:
        hash_part, salt = hashed.split(":")
        return hashlib.sha256((password + salt).encode()).hexdigest() == hash_part
    except ValueError:
        return False

@router.post("/register", response_model=dict)
async def register_user(user: UserRegister, request: Request):
    """Register a new user with enhanced security"""
    try:
        # Enhanced password validation
        if len(user.password) < 4:
            raise HTTPException(status_code=400, detail="Şifre en az 4 karakter olmalıdır")
        
        # Check if user already exists
        import sqlite3
        try:
            with sqlite3.connect(db_manager.db_path) as conn:
                cur = conn.cursor()
                cur.execute("SELECT username FROM users WHERE username = ? OR email = ?", 
                           (user.username, user.email))
                if cur.fetchone():
                    raise HTTPException(status_code=400, detail="Kullanıcı adı veya email zaten kullanımda")
                
                # Create user
                import uuid
                user_id = str(uuid.uuid4())
                hashed_password = hash_password(user.password)
                
                cur.execute("""
                    INSERT INTO users (user_id, username, email, hashed_password, full_name)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_id, user.username, user.email, hashed_password, user.full_name))
                
                conn.commit()
                logger.info(f"✅ New user registered: {user.username}")
                
                return {"success": True, "message": "Kullanıcı başarıyla oluşturuldu", "user_id": user_id}
                
        except sqlite3.Error as e:
            logger.error(f"Database error during registration: {e}")
            raise HTTPException(status_code=500, detail="Veritabanı hatası")
            
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="Kayıt işlemi başarısız")

@router.post("/login", response_model=Token)
async def login_for_access_token(form_data: LoginRequest, request: Request):
    """Authenticate user and return access token"""
    try:
        import sqlite3
        
        # Demo user support
        if form_data.username == "demo" and form_data.password == "1234":
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                data={"sub": "demo", "user_id": "demo_user_id"}, 
                expires_delta=access_token_expires
            )
            logger.info("✅ Demo user authenticated")
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
            }
        
        # Regular user authentication
        with sqlite3.connect(db_manager.db_path) as conn:
            cur = conn.cursor()
            cur.execute("SELECT user_id, hashed_password FROM users WHERE username = ?", 
                       (form_data.username,))
            user_record = cur.fetchone()
            
            if not user_record or not verify_password(form_data.password, user_record[1]):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Kullanıcı adı veya şifre hatalı",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            user_id = user_record[0]
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                data={"sub": form_data.username, "user_id": user_id}, 
                expires_delta=access_token_expires
            )
            
            logger.info(f"✅ User authenticated: {form_data.username}")
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Giriş işlemi başarısız")

@router.post("/login-legacy", response_model=LoginResponse)
async def login_legacy(request: LoginRequest):
    """Legacy login endpoint for demo purposes"""
    try:
        if request.username == "demo" and request.password == "1234":
            logger.info("✅ Legacy demo login successful")
            return LoginResponse(
                success=True,
                message="Giriş başarılı",
                token="legacy_demo_token"
            )
        else:
            return LoginResponse(
                success=False,
                message="Kullanıcı adı veya şifre hatalı"
            )
    except Exception as e:
        logger.error(f"Legacy login error: {e}")
        return LoginResponse(
            success=False,
            message="Giriş işlemi başarısız"
        )

@router.get("/me")
async def get_current_user(current_user: dict = Depends(verify_token)):
    """Get current user information"""
    return current_user
