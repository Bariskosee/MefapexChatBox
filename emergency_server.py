#!/usr/bin/env python3
"""
🚑 MEFAPEX Emergency Server
Minimal FastAPI server for emergency situations
"""

import os
import sys
import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create minimal FastAPI app
app = FastAPI(
    title="MEFAPEX Emergency Server",
    description="Minimal emergency server for MEFAPEX",
    version="1.0.0-emergency",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Static files
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
    logger.info("✅ Static files mounted")
except Exception as e:
    logger.warning(f"⚠️ Static files not available: {e}")

# Models
class LoginRequest(BaseModel):
    username: str
    password: str

class ChatMessage(BaseModel):
    message: str

# Main page
@app.get("/", response_class=HTMLResponse)
async def home():
    """Main page"""
    try:
        return FileResponse("static/index.html", media_type="text/html; charset=utf-8")
    except:
        return HTMLResponse("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>MEFAPEX Emergency Server</title>
            <meta charset="utf-8">
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
                .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                h1 { color: #2c3e50; text-align: center; }
                .status { background: #e8f5e8; border: 1px solid #4caf50; padding: 15px; border-radius: 5px; margin: 20px 0; }
                .links { display: flex; gap: 20px; justify-content: center; margin: 20px 0; }
                .link { background: #3498db; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; }
                .link:hover { background: #2980b9; }
                .chat-box { border: 1px solid #ddd; border-radius: 5px; padding: 20px; margin: 20px 0; background: #fafafa; }
                input, button { padding: 10px; margin: 5px; border: 1px solid #ddd; border-radius: 3px; }
                button { background: #3498db; color: white; cursor: pointer; }
                button:hover { background: #2980b9; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🚑 MEFAPEX Emergency Server</h1>
                
                <div class="status">
                    <strong>✅ Emergency Server Aktif</strong><br>
                    Ana server çalışmadığında bu minimal server devreye girer.
                </div>
                
                <div class="links">
                    <a href="/docs" class="link">📚 API Docs</a>
                    <a href="/health" class="link">🩺 Health Check</a>
                    <a href="/test" class="link">🧪 Test Page</a>
                </div>
                
                <div class="chat-box">
                    <h3>💬 Emergency Chat</h3>
                    <input type="text" id="chatInput" placeholder="Mesajınızı yazın..." style="width: 60%;">
                    <button onclick="sendMessage()">Gönder</button>
                    <div id="chatResponse" style="margin-top: 10px; padding: 10px; background: white; border-radius: 3px;"></div>
                </div>
                
                <script>
                    async function sendMessage() {
                        const input = document.getElementById('chatInput');
                        const response = document.getElementById('chatResponse');
                        const message = input.value.trim();
                        
                        if (!message) return;
                        
                        try {
                            const result = await fetch('/chat', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ message: message })
                            });
                            
                            const data = await result.json();
                            response.innerHTML = '<strong>Bot:</strong> ' + data.response;
                            input.value = '';
                        } catch (error) {
                            response.innerHTML = '<strong>Hata:</strong> ' + error.message;
                        }
                    }
                    
                    document.getElementById('chatInput').addEventListener('keypress', function(e) {
                        if (e.key === 'Enter') sendMessage();
                    });
                </script>
            </div>
        </body>
        </html>
        """)

# Health check
@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "Emergency server running",
        "version": "1.0.0-emergency",
        "server_type": "emergency"
    }

# Test endpoint
@app.get("/test", response_class=HTMLResponse)
async def test_page():
    """Test page"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>MEFAPEX Test</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }
            .test-item { margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
            .success { background: #e8f5e8; border-color: #4caf50; }
            .error { background: #fee; border-color: #f44336; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🧪 MEFAPEX Test Sayfası</h1>
            <div class="test-item success">✅ Emergency Server Çalışıyor</div>
            <div class="test-item success">✅ FastAPI Yüklü</div>
            <div class="test-item success">✅ CORS Aktif</div>
            <div class="test-item success">✅ API Endpoints Aktif</div>
            <div class="test-item">📝 Main server debug için bu sayfayı kullanın</div>
            <a href="/">← Ana Sayfaya Dön</a>
        </div>
    </body>
    </html>
    """)

# Simple login (demo)
@app.post("/login")
async def login(login_data: LoginRequest):
    """Simple demo login"""
    if login_data.username == "demo" and login_data.password == "1234":
        return {
            "success": True,
            "message": "Emergency login başarılı!",
            "access_token": "emergency-demo-token",
            "token_type": "bearer"
        }
    return {"success": False, "message": "Demo kullanıcı: demo/1234"}

# Simple chat
@app.post("/chat")
async def chat(chat_msg: ChatMessage):
    """Simple chat endpoint"""
    message = chat_msg.message.lower()
    
    # Simple responses
    if "merhaba" in message or "selam" in message:
        response = "Merhaba! Emergency server'dan size yardımcı oluyorum."
    elif "nasıl" in message and "sin" in message:
        response = "İyiyim, teşekkürler! Bu emergency server çalışıyor."
    elif "test" in message:
        response = "Test başarılı! Emergency server aktif."
    elif "help" in message or "yardım" in message:
        response = "Emergency server komutları: test, status, help"
    elif "status" in message:
        response = "Emergency server durumu: Aktif ve çalışıyor"
    else:
        response = f"Emergency server'dan yanıt: '{message}' mesajınızı aldım."
    
    return {"response": response}

# Status endpoint
@app.get("/status")
async def status():
    """Server status"""
    return {
        "server": "emergency",
        "status": "running",
        "endpoints": ["/", "/health", "/test", "/login", "/chat", "/docs"],
        "message": "Emergency server successfully running"
    }

# Error handler
@app.exception_handler(404)
async def not_found_handler(request, exc):
    """404 handler"""
    return {"error": "Not found", "message": "Emergency server - endpoint bulunamadı"}

@app.exception_handler(500)
async def server_error_handler(request, exc):
    """500 handler"""
    logger.error(f"Emergency server error: {exc}")
    return {"error": "Server error", "message": "Emergency server hatası"}

def main():
    """Main function"""
    print("🚑 MEFAPEX Emergency Server Starting...")
    print("=" * 50)
    print("✅ Minimal dependencies")
    print("✅ No database required")
    print("✅ No AI models required")
    print("✅ Simple FastAPI only")
    print("=" * 50)
    
    # Check if port is available
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "127.0.0.1")
    
    print(f"🌐 Starting on http://{host}:{port}")
    print(f"📚 API Docs: http://{host}:{port}/docs")
    print(f"🧪 Test Page: http://{host}:{port}/test")
    print("=" * 50)
    
    try:
        uvicorn.run(
            "emergency_server:app",
            host=host,
            port=port,
            reload=False,
            log_level="info"
        )
    except Exception as e:
        print(f"❌ Emergency server failed to start: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
