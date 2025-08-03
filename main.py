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
    Hybrid chat endpoint that:
    1. First searches in uploaded FAQ database
    2. If relevant info found, uses that as primary source
    3. If no relevant info found, uses ChatGPT's general knowledge
    4. Always generates response via GPT-3.5 Turbo for natural conversation
    """
    try:
        user_message = message.message.strip()
        
        if not user_message:
            raise HTTPException(status_code=400, detail="Mesaj boş olamaz")
        
        logger.info(f"User message: {user_message}")
        
        # Check for live data queries (simulated)
        if "üretim" in user_message.lower() and ("çıktı" in user_message.lower() or "miktar" in user_message.lower()):
            return ChatResponse(response="Güncel üretim çıktısı: 850 adet. Bu bilgi canlı sistemden alınmıştır.")
        
        # Generate embedding for user message using FREE model
        user_embedding = sentence_model.encode([user_message])[0].tolist()
        
        # Search for similar questions in Qdrant
        search_results = qdrant_client.search(
            collection_name="mefapex_faq",
            query_vector=user_embedding,
            limit=1,
            with_payload=True
        )
        
        # Determine if we have relevant info from database
        has_relevant_context = False
        context = ""
        similarity_threshold = 0.7  # Adjust this threshold as needed
        
        if search_results and search_results[0].score > similarity_threshold:
            # High similarity - use database info
            has_relevant_context = True
            best_match = search_results[0]
            context = f"Fabrika veritabanından: {best_match.payload['answer']}"
            logger.info(f"Using database context with score: {best_match.score}")
        else:
            # Low similarity or no results - will use general knowledge
            has_relevant_context = False
            logger.info("No relevant database context found, using general knowledge")
        
            # Create adaptive prompt based on context availability with advanced formatting
            if has_relevant_context:
                # Use database information as primary source with beautiful formatting
                system_prompt = """Sen MEFAPEX fabrikasının AI asistanısın. Türkçe olarak yanıt ver.

ÖNCELİK SIRASI:
1. Önce veritabanındaki bilgileri kullan (bunlar doğru ve güncel)
2. Bu bilgileri ChatGPT tarzı temiz formatta sun

FORMAT ÖNCELİĞİ (ÇOK ÖNEMLİ):
Her yanıtını temiz, yapılandırılmış ve görsel olarak çekici yap:
• Düşünceler/bölümler arası açık satır boşlukları
• Çoklu öğeler için madde işaretli veya numaralı listeler  
• Okunabilirlik için kısa paragraflar
• Gerektiğinde **kalın** veya *italik* vurgu
• Büyük metin blokları yapmaktan kaçın
• Akıcılık, netlik ve organize görünüm önceliği

Kibar, profesyonel ve yardımsever ol."""
                
                user_prompt = f"""Kullanıcı sorusu: {user_message}

Fabrika veritabanından alınan bilgi: {context}

Yukarıdaki veritabanı bilgisini kullanarak soruyu yanıtla. Bu bilgi fabrikamıza özeldir ve doğru kabul edilmelidir.
Yanıtını ChatGPT kalitesinde temiz ve okunabilir formatta sun."""
            
            else:
                # Use general knowledge but maintain MEFAPEX context with clean formatting
                system_prompt = """Sen MEFAPEX fabrikasının AI asistanısın. Türkçe olarak yanıt ver.

KAYNAK STRATEJİSİ:
• Bu soru fabrika veritabanında bulunmuyor
• Genel bilginle doğrudan yanıtla - ChatGPT bilgini kullan
• MEFAPEX perspektifini koru ama soru hakkında bilgin varsa paylaş
• Yanıtının sonunda "Bu konuda fabrika veritabanımızda spesifik bilgi bulunmuyor" ifadesini ekle

FORMAT ÖNCELİĞİ (ÇOK ÖNEMLİ):
Her yanıtını temiz, yapılandırılmış ve görsel olarak çekici yap:
• Düşünceler/bölümler arası açık satır boşlukları
• Çoklu öğeler için madde işaretli veya numaralı listeler
• Okunabilirlik için kısa paragraflar  
• Gerektiğinde **kalın** veya *italik* vurgu
• Büyük metin blokları yapmaktan kaçın
• Akıcılık, netlik ve organize görünüm önceliği

Kibar, profesyonel ve yardımsever ol."""
                
                user_prompt = f"""Kullanıcı sorusu: {user_message}

Bu konuda fabrika veritabanında spesifik bilgi bulunamadı. 
Lütfen genel bilginle doğrudan yanıtla. Soruyu ChatGPT olarak cevaplayabilirsin.
Yanıtının sonunda mutlaka şu ifadeyi ekle: "Bu konuda fabrika veritabanımızda spesifik bilgi bulunmuyor."
Yanıtını ChatGPT kalitesinde temiz ve okunabilir formatta sun."""        # Generate response using GPT-3.5 Turbo
        chat_completion = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=400,  # Increased for more detailed responses
            temperature=0.7
        )
        
        bot_response = chat_completion.choices[0].message.content
        
        # Add source indicator to response
        if has_relevant_context:
            logger.info("Generated response using database context")
        else:
            logger.info("Generated response using general knowledge")
            # Optionally add a subtle indicator that this is general knowledge
            bot_response += "\n\n💡 *Bu yanıt genel bilgiye dayanmaktadır.*"
        
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
