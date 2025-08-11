"""
🔐 Authentication Router
User registration, login, and JWT token management
🚨 DEPRECATED: This router is being migrated to unified auth_service.py
Use main auth endpoints or the new auth_service for consistency.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from datetime import datetime, timedelta
from typing import Optional
import logging

# Import unified authentication service
from auth_service import get_auth_service, verify_token

logger = logging.getLogger(__name__)

# Models
from pydantic import BaseModel, EmailStr

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

# Global database manager reference
db_manager = None

def init_auth_router(database_manager):
    """Initialize router with dependencies from main app"""
    global db_manager
    db_manager = database_manager

@router.post("/register", response_model=dict)
async def register_user(user: UserRegister, request: Request):
    """Register a new user with enhanced security"""
    try:
        auth_service = get_auth_service()
        
        # Enhanced password validation
        is_valid, message = auth_service.validate_password_strength(user.password)
        if not is_valid:
            raise HTTPException(status_code=400, detail=message)
        
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
                hashed_password = auth_service.get_password_hash(user.password)
                
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
        auth_service = get_auth_service()
        
        # Demo user support
        if auth_service.authenticate_demo_user(form_data.username, form_data.password):
            access_token_expires = timedelta(minutes=auth_service.access_token_expire_minutes)
            access_token = auth_service.create_access_token(
                data={"sub": "demo", "user_id": "demo_user_id"}, 
                expires_delta=access_token_expires
            )
            logger.info("✅ Demo user authenticated")
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": auth_service.access_token_expire_minutes * 60
            }
        
        # Regular user authentication
        import sqlite3
        with sqlite3.connect(db_manager.db_path) as conn:
            cur = conn.cursor()
            cur.execute("SELECT user_id, hashed_password FROM users WHERE username = ?", 
                       (form_data.username,))
            user_record = cur.fetchone()
            
            if not user_record or not auth_service.verify_password(form_data.password, user_record[1]):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Kullanıcı adı veya şifre hatalı",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            user_id = user_record[0]
            access_token_expires = timedelta(minutes=auth_service.access_token_expire_minutes)
            access_token = auth_service.create_access_token(
                data={"sub": form_data.username, "user_id": user_id}, 
                expires_delta=access_token_expires
            )
            
            logger.info(f"✅ User authenticated: {form_data.username}")
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": auth_service.access_token_expire_minutes * 60
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
        auth_service = get_auth_service()
        
        if auth_service.authenticate_demo_user(request.username, request.password):
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
