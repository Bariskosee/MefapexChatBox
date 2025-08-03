from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import openai
import os
from dotenv import load_dotenv
import pickle
import logging
import numpy as np

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MEFAPEX Chatbot API (Demo Mode)")

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

# Load demo vector store
demo_vector_store = None
try:
    with open('demo_faq_embeddings.pkl', 'rb') as f:
        demo_vector_store = pickle.load(f)
    logger.info("Demo vector store loaded successfully")
except FileNotFoundError:
    logger.warning("Demo vector store not found. Run embedding_loader_demo.py first.")

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

def simple_text_similarity(query, question):
    """Simple text-based similarity for demo purposes"""
    query_words = set(query.lower().split())
    question_words = set(question.lower().split())
    
    intersection = len(query_words.intersection(question_words))
    union = len(query_words.union(question_words))
    
    if union == 0:
        return 0.0
    
    return intersection / union

def search_similar_demo(query, top_k=1):
    """Search for similar questions using demo data"""
    if not demo_vector_store:
        return []
    
    results = []
    for i, data_item in enumerate(demo_vector_store['data']):
        similarity = simple_text_similarity(query, data_item['question'])
        results.append({
            'score': similarity,
            'data': data_item
        })
    
    results.sort(key=lambda x: x['score'], reverse=True)
    return results[:top_k]

def generate_demo_response(user_message, context):
    """Generate a demo response when OpenAI API is not available"""
    
    # Simple rule-based responses for common queries
    user_lower = user_message.lower()
    
    if any(word in user_lower for word in ['çalışma', 'saat', 'mesai']):
        return f"Çalışma saatleri ile ilgili sorunuzu yanıtlayayım: {context}"
    
    elif any(word in user_lower for word in ['izin', 'tatil']):
        return f"İzin başvuruları hakkında bilgi: {context}"
    
    elif any(word in user_lower for word in ['güvenlik', 'kural']):
        return f"Güvenlik kurallarımız şunlardır: {context}"
    
    elif any(word in user_lower for word in ['vardiya', 'değişim']):
        return f"Vardiya değişiklikleri için: {context}"
    
    elif any(word in user_lower for word in ['yemek', 'mola']):
        return f"Yemek ve mola saatleri: {context}"
    
    elif any(word in user_lower for word in ['stok', 'logo']):
        return f"Stok durumu kontrolü: {context}"
    
    elif any(word in user_lower for word in ['kalite', 'kontrol']):
        return f"Kalite kontrol prosedürlerimiz: {context}"
    
    elif any(word in user_lower for word in ['makine', 'arıza']):
        return f"Makine arızası bildirimi: {context}"
    
    elif any(word in user_lower for word in ['üretim', 'hedef']):
        return f"Üretim hedeflerimiz: {context}"
    
    else:
        return f"Sorunuzla ilgili bulduğum bilgi: {context}. Daha detaylı bilgi için lütfen yöneticinize başvurun."

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
    Main chat endpoint that works in demo mode
    """
    try:
        user_message = message.message.strip()
        
        if not user_message:
            raise HTTPException(status_code=400, detail="Mesaj boş olamaz")
        
        logger.info(f"User message: {user_message}")
        
        # Check for live data queries (simulated)
        if "üretim" in user_message.lower() and ("çıktı" in user_message.lower() or "miktar" in user_message.lower()):
            return ChatResponse(response="Güncel üretim çıktısı: 850 adet. Bu bilgi canlı sistemden alınmıştır. (Demo Mode)")
        
        # Search for similar questions in demo data
        search_results = search_similar_demo(user_message, top_k=1)
        
        if not search_results or search_results[0]['score'] < 0.1:
            context = "Bu konuda spesifik bilgim bulunmuyor."
        else:
            best_match = search_results[0]
            context = f"{best_match['data']['answer']}"
            logger.info(f"Found context with score: {best_match['score']:.3f}")
        
        # Try to use OpenAI API, fallback to demo response
        try:
            # Create prompt for GPT-3.5 Turbo
            system_prompt = """Sen MEFAPEX fabrikasının AI asistanısın. Türkçe olarak yanıt ver. 
            Çalışanlara yardımcı olmak için tasarlandın. Kibar, profesyonel ve yardımsever ol."""
            
            user_prompt = f"""Kullanıcı sorusu: {user_message}

İlgili bilgi: {context}

Lütfen yukarıdaki bilgiyi kullanarak kullanıcının sorusuna Türkçe olarak yanıt ver."""
            
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
            logger.info("Generated response using OpenAI API")
            
        except Exception as openai_error:
            logger.warning(f"OpenAI API error: {openai_error}")
            # Fallback to demo response
            bot_response = generate_demo_response(user_message, context)
            bot_response += "\n\n(Not: Bu yanıt demo modunda oluşturulmuştur. Tam özellikler için OpenAI API kotanızı kontrol edin.)"
            logger.info("Generated response using demo mode")
        
        return ChatResponse(response=bot_response)
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Bir hata oluştu: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        return {
            "status": "healthy",
            "mode": "demo" if not demo_vector_store else "demo with data",
            "demo_vector_store": demo_vector_store is not None,
            "openai_configured": bool(os.getenv("OPENAI_API_KEY"))
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting MEFAPEX Chatbot in Demo Mode")
    print("📝 Note: This version works without Qdrant and handles OpenAI API quota issues")
    print("🌐 Visit: http://localhost:8000")
    print("🔑 Login: demo / 1234")
    uvicorn.run(app, host="0.0.0.0", port=8000)
