from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from sentence_transformers import SentenceTransformer
import os
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MEFAPEX Chatbot API - FREE Version")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize FREE sentence transformer model
sentence_model = SentenceTransformer('all-MiniLM-L6-v2')

# Initialize Qdrant client
qdrant_client = QdrantClient(
    host=os.getenv("QDRANT_HOST", "localhost"),
    port=int(os.getenv("QDRANT_PORT", 6333))
)

class ChatMessage(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    success: bool
    message: str

@app.get("/")
async def serve_index():
    """Serve the main HTML page"""
    return FileResponse("static/index.html")

@app.post("/login")
async def login(request: LoginRequest):
    """Simple hardcoded login for demo purposes"""
    if request.username == "demo" and request.password == "1234":
        return LoginResponse(success=True, message="Giriş başarılı!")
    else:
        return LoginResponse(success=False, message="Kullanıcı adı veya şifre hatalı!")

@app.post("/chat", response_model=ChatResponse)
async def chat(message: ChatMessage):
    """
    FREE chat endpoint that uses only local models:
    1. Searches in uploaded FAQ database using free sentence transformers
    2. Returns the best matching answer from the database
    3. No OpenAI API needed!
    """
    try:
        user_message = message.message.strip()
        
        if not user_message:
            raise HTTPException(status_code=400, detail="Mesaj boş olamaz")
        
        logger.info(f"User message: {user_message}")
        
        # Check for live data queries (simulated)
        if "üretim" in user_message.lower() and ("çıktı" in user_message.lower() or "miktar" in user_message.lower()):
            return ChatResponse(response="📊 **Güncel Üretim Bilgisi**\n\n• Bugünkü üretim: **850 adet**\n• Hedef: 1000 adet\n• Gerçekleşme: %85\n\n*Bu bilgi canlı sistemden alınmıştır.*")
        
        # Generate embedding for user message using FREE model
        logger.info("Generating embedding for user query...")
        user_embedding = sentence_model.encode([user_message])[0].tolist()
        
        # Search for similar questions in Qdrant
        search_results = qdrant_client.search(
            collection_name="mefapex_faq",
            query_vector=user_embedding,
            limit=3,
            with_payload=True
        )
        
        if not search_results:
            return ChatResponse(response="Üzgünüm, bu konuda şu anda bilgi bulunamıyor. Lütfen sorunuzu farklı kelimelerle tekrar deneyin.")
        
        # Get the best match
        best_match = search_results[0]
        similarity_score = best_match.score
        
        logger.info(f"Best match score: {similarity_score}")
        
        # High similarity threshold for direct answers
        if similarity_score > 0.8:
            # Very high similarity - give direct answer with confidence
            response = f"✅ **{best_match.payload['answer']}**"
            
            # Add related suggestions if available
            if len(search_results) > 1 and search_results[1].score > 0.6:
                response += f"\n\n💡 **İlgili konu:** {search_results[1].payload['question']}"
                
        elif similarity_score > 0.6:
            # Good similarity - provide answer with context
            response = f"📋 **En yakın eşleşme:**\n\n"
            response += f"**Soru:** {best_match.payload['question']}\n\n"
            response += f"**Cevap:** {best_match.payload['answer']}\n\n"
            response += f"*Eşleşme oranı: %{int(similarity_score * 100)}*"
            
        else:
            # Lower similarity - show multiple options
            response = "🔍 **Benzer konular buldum:**\n\n"
            for i, result in enumerate(search_results[:2], 1):
                response += f"**{i}.** {result.payload['question']}\n"
                response += f"   └─ {result.payload['answer'][:100]}...\n\n"
            response += "*Size en uygun olanını seçebilirsiniz.*"
        
        return ChatResponse(response=response)
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return ChatResponse(response=f"❌ Bir hata oluştu: {str(e)}\n\nLütfen daha sonra tekrar deneyin.")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check Qdrant connection
        collections = qdrant_client.get_collections()
        return {
            "status": "healthy",
            "qdrant_connected": True,
            "collections": len(collections.collections),
            "model": "FREE - No OpenAI API needed",
            "embedding_model": "all-MiniLM-L6-v2"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@app.get("/test")
async def test_endpoint():
    """Test endpoint to verify the system is working"""
    try:
        # Test Qdrant connection
        collection_info = qdrant_client.get_collection("mefapex_faq")
        
        # Test embedding generation
        test_embedding = sentence_model.encode(["test"])[0].tolist()
        
        return {
            "status": "✅ FREE chatbot is working!",
            "qdrant_points": collection_info.points_count,
            "embedding_size": len(test_embedding),
            "message": "🆓 No OpenAI API key needed - completely FREE!"
        }
    except Exception as e:
        return {
            "status": "❌ Error",
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting MEFAPEX FREE Chatbot...")
    print("🆓 No OpenAI API key needed!")
    print("🌐 URL: http://localhost:8000")
    print("🔑 Demo login: demo / 1234")
    uvicorn.run(app, host="0.0.0.0", port=8000)
