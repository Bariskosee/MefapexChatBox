from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
import openai
import os
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MEFAPEX Chatbot API")

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

# Initialize OpenAI client
openai.api_key = os.getenv("OPENAI_API_KEY")

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
    Main chat endpoint that:
    1. Performs vector search in Qdrant
    2. Uses OpenAI GPT-3.5 Turbo to generate response
    """
    try:
        user_message = message.message.strip()
        
        if not user_message:
            raise HTTPException(status_code=400, detail="Mesaj boş olamaz")
        
        logger.info(f"User message: {user_message}")
        
        # Check for live data queries (simulated)
        if "üretim" in user_message.lower() and ("çıktı" in user_message.lower() or "miktar" in user_message.lower()):
            return ChatResponse(response="Güncel üretim çıktısı: 850 adet. Bu bilgi canlı sistemden alınmıştır.")
        
        # Generate embedding for user message
        embedding_response = openai.embeddings.create(
            model="text-embedding-ada-002",
            input=user_message
        )
        user_embedding = embedding_response.data[0].embedding
        
        # Search for similar questions in Qdrant
        search_results = qdrant_client.search(
            collection_name="mefapex_faq",
            query_vector=user_embedding,
            limit=1,
            with_payload=True
        )
        
        if not search_results:
            context = "Maalesef bu konuda spesifik bilgim yok."
        else:
            best_match = search_results[0]
            context = f"Soru: {best_match.payload['question']}\nCevap: {best_match.payload['answer']}"
            logger.info(f"Found context with score: {best_match.score}")
        
        # Create prompt for GPT-3.5 Turbo
        system_prompt = """Sen MEFAPEX fabrikasının AI asistanısın. Türkçe olarak yanıt ver. 
        Çalışanlara yardımcı olmak için tasarlandın. Kibar, profesyonel ve yardımsever ol.
        Eğer bir sorunun cevabını bilmiyorsan, bunu açıkça belirt ve kime başvurabileceklerini söyle."""
        
        user_prompt = f"""Kullanıcı sorusu: {user_message}

İlgili bilgi: {context}

Lütfen yukarıdaki bilgiyi kullanarak kullanıcının sorusuna Türkçe olarak yanıt ver. 
Eğer sağlanan bilgi soruyla tam olarak ilgili değilse, genel yardımcı bir yanıt ver."""
        
        # Generate response using GPT-3.5 Turbo
        chat_completion = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=300,
            temperature=0.7
        )
        
        bot_response = chat_completion.choices[0].message.content
        logger.info(f"Generated response: {bot_response}")
        
        return ChatResponse(response=bot_response)
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Bir hata oluştu: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check Qdrant connection
        collections = qdrant_client.get_collections()
        return {
            "status": "healthy",
            "qdrant_connected": True,
            "collections": len(collections.collections)
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
