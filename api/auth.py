"""
🔐 Authentication API Routes
User registration, login, and authentication endpoints with secure cookie support
"""
from fastapi import APIRouter, HTTPException, Depends, status, Request, Response
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
from typing import Optional
import logging

from auth_service import get_auth_service, verify_token, verify_token_from_request
from database.manager import db_manager
from security_config import input_validator
from core.configuration import get_config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["authentication"])

# Rate limiter will be imported from main
rate_limiter = None

# Pydantic models
class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user_info: dict

class RefreshTokenRequest(BaseModel):
    pass  # Refresh token will come from HTTP-only cookie

def set_rate_limiter(limiter):
    """Set rate limiter from main app"""
    global rate_limiter
    rate_limiter = limiter

@router.post("/register", response_model=dict)
async def register_user(user: UserRegister, request: Request):
    """Register a new user with enhanced security"""
    try:
        client_ip = request.client.host
        
        # Check rate limiting for registration
        if rate_limiter and not rate_limiter.is_allowed(client_ip, "general"):
            logger.warning(f"Rate limit exceeded for registration from {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many registration attempts. Please try again later."
            )
        
        # Input validation
        if not user.username or len(user.username) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username must be at least 3 characters long"
            )
        
        if len(user.password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters long"
            )
        
        # Security validation
        is_xss, xss_pattern = input_validator.detect_xss_attempt(user.username)
        if is_xss:
            logger.warning(f"XSS attempt in username registration: {xss_pattern}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid characters in username"
            )
        
        # Register user through auth service
        auth_service = get_auth_service()
        result = await auth_service.register_user(
            username=user.username,
            email=user.email,
            password=user.password,
            full_name=user.full_name
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Registration failed")
            )
        
        logger.info(f"New user registered: {user.username}")
        return {
            "message": "User registered successfully",
            "user_id": result.get("user_id"),
            "username": user.username
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@router.post("/login", response_model=dict)
async def login_user(user: UserLogin, request: Request, response: Response):
    """User login with secure cookie-based authentication"""
    try:
        client_ip = request.client.host
        
        # Rate limiting
        if rate_limiter and not rate_limiter.is_allowed(client_ip, "general"):
            logger.warning(f"Rate limit exceeded for login from {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts. Please try again later."
            )
        
        # Authenticate user
        auth_service = get_auth_service()
        auth_result = await auth_service.authenticate_user(user.username, user.password)
        
        if not auth_result.get("success"):
            logger.warning(f"Failed login attempt for {user.username} from {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Create tokens
        token_data = {
            "sub": user.username,
            "user_id": auth_result["user_id"],
            "username": user.username
        }
        
        # Create access token (short-lived)
        access_token = auth_service.create_access_token(
            data=token_data,
            expires_delta=timedelta(minutes=15)  # 15 minutes
        )
        
        # Create refresh token (long-lived)
        refresh_token, family = auth_service.create_refresh_token(auth_result["user_id"])
        
        # Set secure HTTP-only cookies
        auth_service.set_auth_cookies(response, access_token, refresh_token)
        
        logger.info(f"Successful login: {user.username}")
        
        return {
            "success": True,
            "message": "Login successful",
            "user_info": {
                "user_id": auth_result["user_id"],
                "username": user.username,
                "email": auth_result.get("email"),
                "full_name": auth_result.get("full_name")
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@router.get("/me")
async def get_current_user_info(request: Request):
    """Get current user information from cookie or header"""
    current_user = verify_token_from_request(request)
    return {
        "user_id": current_user.get("user_id"),
        "username": current_user.get("username"),
        "email": current_user.get("email"),
        "full_name": current_user.get("full_name"),
        "is_active": current_user.get("is_active", True)
    }

@router.post("/refresh")
async def refresh_access_token(request: Request, response: Response):
    """Refresh access token using refresh token from HTTP-only cookie"""
    try:
        # Get refresh token from cookie
        refresh_token = request.cookies.get("refresh_token")
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No refresh token provided"
            )
        
        auth_service = get_auth_service()
        
        # Rotate refresh token (security best practice)
        new_refresh_token, family = auth_service.rotate_refresh_token(refresh_token)
        
        # Get user data from refresh token
        token_data = auth_service.verify_refresh_token(refresh_token)
        user_id = token_data["user_id"]
        
        # Get user info from database
        user_data = db_manager.get_user_by_id(user_id)
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        # Create new access token
        access_token_data = {
            "sub": user_data["username"],
            "user_id": user_id,
            "username": user_data["username"]
        }
        
        new_access_token = auth_service.create_access_token(
            data=access_token_data,
            expires_delta=timedelta(minutes=15)
        )
        
        # Set new cookies
        auth_service.set_auth_cookies(response, new_access_token, new_refresh_token)
        
        logger.info(f"Token refreshed for user: {user_data['username']}")
        
        return {
            "success": True,
            "message": "Token refreshed successfully",
            "user_info": {
                "user_id": user_id,
                "username": user_data["username"],
                "email": user_data.get("email"),
                "full_name": user_data.get("full_name")
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token refresh failed"
        )

@router.post("/logout")
async def logout_user(request: Request, response: Response):
    """User logout with token cleanup"""
    try:
        # Get refresh token to revoke it
        refresh_token = request.cookies.get("refresh_token")
        if refresh_token:
            auth_service = get_auth_service()
            auth_service.revoke_refresh_token(refresh_token)
        
        # Get user info if possible (for logging)
        try:
            current_user = verify_token_from_request(request)
            username = current_user.get("username", "unknown")
        except:
            username = "unknown"
        
        # Clear cookies
        auth_service = get_auth_service()
        auth_service.clear_auth_cookies(response)
        
        logger.info(f"User logged out: {username}")
        return {"success": True, "message": "Logged out successfully"}
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        # Still clear cookies even if other operations fail
        auth_service = get_auth_service()
        auth_service.clear_auth_cookies(response)
        return {"success": True, "message": "Logged out successfully"}
