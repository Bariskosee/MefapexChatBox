#!/usr/bin/env python3
"""
Simple MEFAPEX Server for Login Testing
This is a minimal server to test the login functionality
"""

from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import uvicorn
import os
import json
import time
from datetime import datetime, timedelta
from typing import Optional

# Create FastAPI app
app = FastAPI(
    title="MEFAPEX Simple ChatBox",
    description="Simplified MEFAPEX ChatBox for testing login functionality",
    version="1.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Security
security = HTTPBearer()

# Data Models
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    success: bool
    message: str

class Token(BaseModel):
    access_token: str
    token_type: str

class ChatMessage(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    source: str

# Demo user credentials (hardcoded for testing)
DEMO_USERS = {
    "demo": {
        "password": "1234",
        "user_id": "demo-user-id",
        "username": "demo",
        "email": "demo@mefapex.com",
        "full_name": "Demo User"
    }
}

# Simple token storage (in production, use proper JWT with secret)
active_tokens = {}

def create_simple_token(username: str) -> str:
    """Create a simple token for demo purposes"""
    token = f"demo-token-{username}-{int(time.time())}"
    active_tokens[token] = {
        "username": username,
        "created_at": datetime.now(),
        "expires_at": datetime.now() + timedelta(hours=24)
    }
    return token

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify token"""
    token = credentials.credentials
    if token not in active_tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    token_data = active_tokens[token]
    if datetime.now() > token_data["expires_at"]:
        del active_tokens[token]
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
    
    return token_data

# Routes
@app.get("/")
async def read_root():
    """Serve the main page"""
    if os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    else:
        return {"message": "MEFAPEX Simple ChatBox API", "status": "running"}

@app.post("/login", response_model=Token)
async def login_jwt(request: LoginRequest):
    """JWT Login endpoint"""
    print(f"🔐 JWT Login attempt: {request.username}")
    
    if request.username in DEMO_USERS:
        user = DEMO_USERS[request.username]
        if user["password"] == request.password:
            token = create_simple_token(request.username)
            print(f"✅ JWT Login successful for: {request.username}")
            return Token(access_token=token, token_type="bearer")
    
    print(f"❌ JWT Login failed for: {request.username}")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials"
    )

@app.post("/login-legacy", response_model=LoginResponse)
async def login_legacy(request: LoginRequest):
    """Legacy login endpoint"""
    print(f"🔐 Legacy Login attempt: {request.username}")
    
    if request.username in DEMO_USERS:
        user = DEMO_USERS[request.username]
        if user["password"] == request.password:
            print(f"✅ Legacy Login successful for: {request.username}")
            return LoginResponse(success=True, message="Giriş başarılı")
    
    print(f"❌ Legacy Login failed for: {request.username}")
    return LoginResponse(success=False, message="Kullanıcı adı veya şifre hatalı")

@app.get("/me")
async def get_current_user(token_data: dict = Depends(verify_token)):
    """Get current user info"""
    username = token_data["username"]
    if username in DEMO_USERS:
        user = DEMO_USERS[username].copy()
        user.pop("password", None)  # Don't return password
        return user
    raise HTTPException(status_code=404, detail="User not found")

@app.post("/chat", response_model=ChatResponse)
async def chat_anonymous(message: ChatMessage):
    """Anonymous chat endpoint"""
    print(f"💬 Anonymous chat message: {message.message}")
    
    # Simple response logic
    user_msg = message.message.lower().strip()
    
    if any(word in user_msg for word in ["merhaba", "selam", "hello", "hi"]):
        response = "👋 Merhaba! MEFAPEX AI asistanına hoş geldiniz. Size nasıl yardımcı olabilirim?"
    elif any(word in user_msg for word in ["teşekkür", "sağol", "thanks"]):
        response = "🙏 Rica ederim! Başka sorularınız varsa yardımcı olmaktan mutluluk duyarım."
    elif "mefapex" in user_msg:
        response = """🏭 **MEFAPEX Fabrikası Hakkında**

MEFAPEX, Türkiye'de faaliyet gösteren modern bir üretim fabrikasıdır.

**Özellikler:**
• Modern üretim tesisleri
• Güvenlik odaklı çalışma ortamı
• Kaliteli ürün üretimi
• Deneyimli çalışan kadrosu

Size başka nasıl yardımcı olabilirim?"""
    else:
        response = f"🤖 '{message.message}' konusunda size yardımcı olmaya çalışıyorum. Bu konuda daha spesifik bir soru sorabilir misiniz?"
    
    return ChatResponse(response=response, source="simple_ai")

@app.post("/chat/authenticated", response_model=ChatResponse)
async def chat_authenticated(message: ChatMessage, token_data: dict = Depends(verify_token)):
    """Authenticated chat endpoint"""
    username = token_data["username"]
    print(f"💬 Authenticated chat from {username}: {message.message}")
    
    # Enhanced response for authenticated users
    user_msg = message.message.lower().strip()
    
    if any(word in user_msg for word in ["merhaba", "selam", "hello", "hi"]):
        response = f"👋 Merhaba {username}! MEFAPEX AI asistanınızım. Size nasıl yardımcı olabilirim?"
    elif any(word in user_msg for word in ["profil", "hesap", "account"]):
        user = DEMO_USERS.get(username, {})
        response = f"""👤 **Profil Bilgileri**

• Kullanıcı: {user.get('username', 'N/A')}
• Ad: {user.get('full_name', 'N/A')}
• E-posta: {user.get('email', 'N/A')}
• Durum: Aktif

Başka bir konuda yardıma ihtiyacınız var mı?"""
    elif "çıkış" in user_msg or "logout" in user_msg:
        response = "🚪 Çıkış yapmak için sağ üstteki 'Çıkış' butonunu kullanabilirsiniz. İyi günler!"
    else:
        # Use the same logic as anonymous but with personalization
        anonymous_response = await chat_anonymous(message)
        response = f"👤 {username}: {anonymous_response.response}"
    
    return ChatResponse(response=response, source="authenticated_ai")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_sessions": len(active_tokens),
        "services": {
            "api": "running",
            "authentication": "available",
            "chat": "available"
        }
    }

@app.get("/debug/tokens")
async def debug_tokens():
    """Debug endpoint to see active tokens (remove in production!)"""
    return {
        "active_tokens": len(active_tokens),
        "tokens": {
            token: {
                "username": data["username"],
                "created_at": data["created_at"].isoformat(),
                "expires_at": data["expires_at"].isoformat()
            }
            for token, data in active_tokens.items()
        }
    }

# Chat session endpoints (simplified)
@app.post("/chat/sessions/save")
async def save_chat_session(session_data: dict, token_data: dict = Depends(verify_token)):
    """Save chat session (simplified)"""
    print(f"💾 Saving session for {token_data['username']}")
    return {"success": True, "message": "Session saved (demo mode)"}

@app.get("/chat/session/current")
async def get_current_session(token_data: dict = Depends(verify_token)):
    """Get current session info"""
    return {
        "success": True,
        "session_id": f"demo-session-{int(time.time())}",
        "user_id": token_data["username"],
        "session_ready": True
    }

@app.post("/chat/sessions/{user_id}/new")
async def start_new_session(user_id: str, token_data: dict = Depends(verify_token)):
    """Start new session"""
    return {
        "success": True,
        "session_id": f"demo-session-{int(time.time())}",
        "message": "New session started"
    }

@app.post("/chat/sessions/save-beacon")
async def save_session_beacon(request: Request):
    """Handle session save beacon (for page unload)"""
    try:
        # Read the raw body data
        body = await request.body()
        data = json.loads(body.decode()) if body else {}
        print(f"💾 Session save beacon: {data}")
        return {"success": True, "message": "Beacon received"}
    except Exception as e:
        print(f"❌ Beacon error: {e}")
        return {"success": False, "error": str(e)}

@app.get("/chat/sessions/{user_id}")
async def get_user_sessions(user_id: str):
    """Get user sessions (demo implementation)"""
    print(f"📋 Getting sessions for user: {user_id}")
    return {
        "user_id": user_id,
        "sessions": [],
        "total_sessions": 0,
        "current_session_id": f"demo-session-{int(time.time())}",
        "session_ready": True
    }

if __name__ == "__main__":
    print("🚀 Starting MEFAPEX Simple Server...")
    print("📍 Demo credentials: username='demo', password='1234'")
    print("🌐 Access the application at: http://localhost:8000")
    
    uvicorn.run(
        "simple_server:app", 
        host="127.0.0.1", 
        port=8000, 
        reload=True,
        log_level="info"
    )
