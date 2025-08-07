from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from sentence_transformers import SentenceTransformer
import openai
import os
from dotenv import load_dotenv
import logging
from typing import Optional

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MEFAPEX Hybrid Chatbot API")

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

# 🎯 HYBRID CONFIGURATION
USE_OPENAI = os.getenv("USE_OPENAI", "false").lower() == "true"
USE_HUGGINGFACE = os.getenv("USE_HUGGINGFACE", "true").lower() == "true"

logger.info(f"🤖 OpenAI enabled: {USE_OPENAI}")
logger.info(f"🆓 Hugging Face enabled: {USE_HUGGINGFACE}")

# Initialize OpenAI client (if enabled)
if USE_OPENAI:
    try:
        openai.api_key = os.getenv("OPENAI_API_KEY")
        logger.info("✅ OpenAI initialized")
    except Exception as e:
        logger.warning(f"⚠️ OpenAI initialization failed: {e}")
        USE_OPENAI = False

# Initialize Hugging Face model (if enabled)
if USE_HUGGINGFACE:
    try:
        sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("✅ Hugging Face model loaded")
    except Exception as e:
        logger.warning(f"⚠️ Hugging Face initialization failed: {e}")
        USE_HUGGINGFACE = False

# Initialize Qdrant client
qdrant_client = QdrantClient(
    host=os.getenv("QDRANT_HOST", "localhost"),
    port=int(os.getenv("QDRANT_PORT", 6333))
)

class ChatMessage(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    source: str  # "openai", "huggingface", or "database"

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    success: bool
    message: str

@app.get("/")
async def read_root():
    return FileResponse("static/index.html")

@app.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    # Simple authentication
    if request.username == "demo" and request.password == "1234":
        return LoginResponse(success=True, message="Giriş başarılı")
    else:
        return LoginResponse(success=False, message="Kullanıcı adı veya şifre hatalı")

@app.get("/health")
async def health_check():
    try:
        # Check Qdrant connection
        collections = qdrant_client.get_collections()
        return {
            "status": "healthy",
            "qdrant": "connected",
            "openai_enabled": USE_OPENAI,
            "huggingface_enabled": USE_HUGGINGFACE,
            "collections": len(collections.collections)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

def generate_embedding(text: str) -> list:
    """Generate embedding using available method"""
    if USE_HUGGINGFACE:
        try:
            return sentence_model.encode([text])[0].tolist()
        except Exception as e:
            logger.error(f"Hugging Face embedding error: {e}")
    
    if USE_OPENAI:
        try:
            response = openai.embeddings.create(
                model="text-embedding-ada-002",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"OpenAI embedding error: {e}")
    
    raise HTTPException(status_code=500, detail="No embedding service available")

def generate_response_openai(context: str, user_message: str) -> str:
    """Generate response using OpenAI"""
    try:
        system_prompt = """Sen MEFAPEX fabrikasının yardımcı asistanısın. 
        Verilen bilgileri kullanarak Türkçe, kısa ve net cevaplar ver.
        Bilgi bulamazsan 'Bu konuda bilgim yok' de."""
        
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Bağlam: {context}\n\nSoru: {user_message}"}
            ],
            max_tokens=150,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"OpenAI response error: {e}")
        raise

def generate_response_huggingface(context: str, user_message: str) -> str:
    """Generate response using Hugging Face (template-based)"""
    if context:
        # Extract answer from context
        lines = context.split('\n')
        for line in lines:
            if 'Answer:' in line or 'answer' in line.lower():
                answer = line.split(':', 1)[-1].strip()
                if answer:
                    return f"📋 {answer}\n\n💡 Bu bilgi MEFAPEX fabrika veritabanından alınmıştır."
        
        # If no clear answer found, return the context
        return f"📋 {context.strip()}\n\n💡 Bu bilgi MEFAPEX fabrika veritabanından alınmıştır."
    else:
        # General responses for common queries
        greetings = ["merhaba", "selam", "hi", "hello"]
        if any(greeting in user_message.lower() for greeting in greetings):
            return "👋 Merhaba! MEFAPEX fabrika asistanınızım. Size nasıl yardımcı olabilirim?"
        
        return "🤖 Bu konuda detaylı bilgim bulunmuyor. Lütfen daha spesifik bir soru sorun veya yöneticinizle iletişime geçin."

@app.post("/chat", response_model=ChatResponse)
async def chat(message: ChatMessage):
    """
    Hybrid chat endpoint:
    1. Search in Qdrant database using available embedding method
    2. Generate response using OpenAI or Hugging Face
    3. Fallback mechanism for reliability
    """
    try:
        user_message = message.message.strip()
        
        if not user_message:
            raise HTTPException(status_code=400, detail="Mesaj boş olamaz")
        
        logger.info(f"User message: {user_message}")
        
        # Generate embedding for search
        try:
            user_embedding = generate_embedding(user_message)
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return ChatResponse(
                response="🤖 Sistem geçici olarak kullanılamıyor. Lütfen daha sonra tekrar deneyin.",
                source="error"
            )
        
        # Search in Qdrant
        try:
            search_results = qdrant_client.search(
                collection_name="mefapex_faq",
                query_vector=user_embedding,
                limit=3,
                with_payload=True
            )
            
            # Process search results
            best_match = None
            if search_results and len(search_results) > 0:
                best_score = search_results[0].score
                logger.info(f"Best match score: {best_score}")
                
                if best_score > 0.6:  # High confidence threshold
                    best_match = search_results[0].payload
                    context = f"Question: {best_match['question']}\nAnswer: {best_match['answer']}"
                    logger.info(f"Using database context with score: {best_score}")
                else:
                    context = ""
                    logger.info("No relevant database context found")
            else:
                context = ""
                logger.info("No search results found")
                
        except Exception as e:
            logger.error(f"Qdrant search error: {e}")
            context = ""
        
        # Generate response using available method
        try:
            if USE_OPENAI:
                response_text = generate_response_openai(context, user_message)
                source = "openai"
                logger.info("Response generated using OpenAI")
            elif USE_HUGGINGFACE:
                response_text = generate_response_huggingface(context, user_message)
                source = "huggingface"
                logger.info("Response generated using Hugging Face")
            else:
                response_text = "🤖 Sistem geçici olarak kullanılamıyor. Lütfen daha sonra tekrar deneyin."
                source = "error"
                
        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            # Fallback to alternative method
            try:
                if USE_HUGGINGFACE and source != "huggingface":
                    response_text = generate_response_huggingface(context, user_message)
                    source = "huggingface_fallback"
                    logger.info("Using Hugging Face as fallback")
                else:
                    response_text = "🤖 Üzgünüm, bir hata oluştu. Lütfen tekrar deneyin."
                    source = "error"
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {fallback_error}")
                response_text = "🤖 Sistem geçici olarak kullanılamıyor. Lütfen daha sonra tekrar deneyin."
                source = "error"
        
        return ChatResponse(response=response_text, source=source)
        
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        return ChatResponse(
            response="🤖 Bir hata oluştu. Lütfen tekrar deneyin.",
            source="error"
        )

@app.get("/system/status")
async def system_status():
    """Get current system configuration"""
    return {
        "openai_enabled": USE_OPENAI,
        "huggingface_enabled": USE_HUGGINGFACE,
        "embedding_method": "huggingface" if USE_HUGGINGFACE else "openai",
        "response_method": "openai" if USE_OPENAI else "huggingface",
        "version": "hybrid_v1.0"
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting MEFAPEX Hybrid Chatbot")
    print(f"🤖 OpenAI: {'✅ Enabled' if USE_OPENAI else '❌ Disabled'}")
    print(f"🆓 Hugging Face: {'✅ Enabled' if USE_HUGGINGFACE else '❌ Disabled'}")
    print("🌐 Visit: http://localhost:8000")
    print("🔑 Login: demo / 1234")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
