from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from sentence_transformers import SentenceTransformer
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
import torch
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
text_generator = None
if USE_HUGGINGFACE:
    try:
        sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("✅ Sentence transformer loaded")
        
        # Initialize text generation model
        device = "mps" if torch.backends.mps.is_available() else "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"🖥️ Using device: {device}")
        
        # Get model from environment or use default
        model_name = os.getenv("HUGGINGFACE_MODEL", "microsoft/DialoGPT-small")
        
        # Available free models (user can change in .env):
        # "microsoft/DialoGPT-small"       # 117M params - Fast, good for conversations
        # "microsoft/DialoGPT-medium"      # 354M params - Better quality, slower
        # "facebook/blenderbot_small-90M"  # 90M params - Good for chatbots
        # "gpt2"                          # 124M params - General text generation
        # "google/flan-t5-small"          # 80M params - Instruction following
        
        logger.info(f"🤖 Loading model: {model_name}")
        
        text_generator = pipeline(
            "text-generation",
            model=model_name,
            tokenizer=model_name,
            device=0 if device == "cuda" else -1,
            max_length=150,
            do_sample=True,
            temperature=0.7,
            pad_token_id=50256
        )
        logger.info(f"✅ Text generation model loaded: {model_name}")
        
    except Exception as e:
        logger.warning(f"⚠️ Advanced Hugging Face initialization failed: {e}")
        # Fallback to sentence transformer only
        try:
            sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("✅ Fallback: Sentence transformer only")
        except Exception as e2:
            logger.warning(f"⚠️ Sentence transformer also failed: {e2}")
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
        if context:
            # Use context from database
            system_prompt = """Sen MEFAPEX fabrikasının yardımcı asistanısın. 
            Verilen bilgileri kullanarak Türkçe, kısa ve net cevaplar ver.
            Bilgileri doğru bir şekilde kullan ve kullanıcıya yardımcı ol."""
            
            user_prompt = f"Bağlam: {context}\n\nSoru: {user_message}"
        else:
            # No context found - use general knowledge
            system_prompt = """Sen MEFAPEX fabrikasının AI asistanısın. Türkçe yanıt ver.
            
            Fabrika ile ilgili genel sorulara yardımcı ol. Eğer spesifik fabrika verisi gerekmiyorsa,
            genel bilginle yanıt verebilirsin. Yanıtını kısa ve yararlı tut.
            
            MEFAPEX hakkında genel bilgi: Türkiye'deki bir üretim fabrikası, çalışan hakları ve 
            güvenlik kurallarına önem verir.
            
            Eğer fabrika-spesifik veri gerekliyse, kullanıcıyı yönetime yönlendir."""
            
            user_prompt = f"Soru: {user_message}\n\nBu konuda fabrika veritabanında spesifik bilgi bulunamadı. Genel bilginle yardımcı olabilir misin?"
        
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=200,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"OpenAI response error: {e}")
        raise

def generate_response_huggingface(context: str, user_message: str) -> str:
    """Generate response using Hugging Face with AI capabilities"""
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
        # Try advanced AI generation first, then fallback to local AI
        try:
            if text_generator is not None:
                response = generate_advanced_ai_response(user_message)
                return f"🤖 {response}\n\n💡 Bu yanıt gelişmiş AI modeli tarafından üretilmiştir."
            else:
                response = generate_ai_response_local(user_message)
                return f"🤖 {response}\n\n💡 Bu yanıt AI tarafından üretilmiştir."
        except:
            # Final fallback to rule-based responses
            return generate_rule_based_response(user_message)

def generate_advanced_ai_response(user_message: str) -> str:
    """Generate response using advanced Hugging Face text generation model"""
    try:
        # Create a conversational prompt
        prompt = f"MEFAPEX fabrika asistanı olarak, kullanıcının sorusuna Türkçe ve yardımcı bir şekilde yanıt ver.\n\nKullanıcı: {user_message}\nAsistan:"
        
        # Generate response
        outputs = text_generator(
            prompt,
            max_length=len(prompt.split()) + 50,
            num_return_sequences=1,
            temperature=0.7,
            do_sample=True,
            pad_token_id=text_generator.tokenizer.eos_token_id
        )
        
        # Extract the generated text
        generated_text = outputs[0]['generated_text']
        
        # Extract only the assistant's response
        if "Asistan:" in generated_text:
            response = generated_text.split("Asistan:")[-1].strip()
        else:
            response = generated_text[len(prompt):].strip()
        
        # Clean up the response
        response = response.replace("\\n", " ").strip()
        
        # If response is too short or empty, fallback
        if len(response) < 10:
            raise Exception("Generated response too short")
        
        return response
        
    except Exception as e:
        logger.warning(f"Advanced AI generation failed: {e}")
        # Fallback to local AI
        return generate_ai_response_local(user_message)

def generate_ai_response_local(user_message: str) -> str:
    """Generate AI response using local models/logic"""
    # Convert to lowercase for analysis
    msg_lower = user_message.lower().strip()
    
    # Greetings - Check first for better matching
    greetings = ["merhaba", "selam", "hi", "hello", "hey", "nasılsın", "nasıl gidiyor"]
    if any(greeting in msg_lower for greeting in greetings) or len(msg_lower.split()) <= 2:
        if any(greeting in msg_lower for greeting in ["merhaba", "selam", "hi", "hello", "hey"]):
            return "👋 Merhaba! MEFAPEX fabrika asistanınızım. Size nasıl yardımcı olabilirim?"
    
    # Thank you responses
    if any(word in msg_lower for word in ["teşekkür", "thanks", "sağol", "eyvallah"]):
        return "Rica ederim! Başka sorularınız olursa çekinmeden sorabilirsiniz."
    
    # Who are you questions
    if any(word in msg_lower for word in ["kim", "who", "kimsin", "sen kim"]):
        return "Ben MEFAPEX fabrikasının AI asistanıyım. Fabrika çalışanlarına yardımcı olmak ve sorularını yanıtlamak için buradayım."
    
    # Factory-related intelligent responses
    if any(word in msg_lower for word in ["mefapex", "fabrika", "factory"]):
        return "MEFAPEX Türkiye'nin önde gelen üretim fabrikalarından biridir. Kaliteli ürünler ve modern teknoloji ile hizmet vermektedir."
    
    if any(word in msg_lower for word in ["nedir", "ne", "what", "hangi"]) and "mefapex" in msg_lower:
        return "MEFAPEX, endüstriyel üretim alanında faaliyet gösteren bir fabrikadır. Çalışan hakları, güvenlik protokolleri ve kaliteli üretim prensiplerine bağlı olarak çalışır."
    
    if any(word in msg_lower for word in ["yardım", "help", "nasıl yardımcı"]):
        return "Size yardımcı olmaktan mutluluk duyarım! Fabrika ile ilgili çalışma saatleri, güvenlik kuralları, izin prosedürleri, vardiya değişiklikleri gibi konularda sorularınızı sorabilirsiniz."
    
    # Time-related queries
    if any(word in msg_lower for word in ["saat", "zaman", "time", "ne zaman"]):
        return "Zaman ile ilgili sorularınız için, lütfen daha spesifik olun. Çalışma saatleri, mola saatleri veya vardiya saatleri hakkında sormak istiyorsanız belirtin."
    
    # General work-related queries
    if any(word in msg_lower for word in ["çalışma", "iş", "work", "job"]):
        return "Çalışma hayatı ile ilgili sorularınızı yanıtlamaya hazırım. İzinler, vardiyalar, güvenlik kuralları gibi konularda detaylı bilgi verebilirim."
    
    # Safety-related
    if any(word in msg_lower for word in ["güvenlik", "safety", "emniyet"]):
        return "Güvenlik fabrikamızın önceliğidir. Kask, güvenlik ayakkabısı ve koruyucu ekipman kullanımı zorunludur. Detaylı güvenlik kuralları için spesifik sorularınızı sorabilirsiniz."
    
    # Food/meal related
    if any(word in msg_lower for word in ["yemek", "food", "meal", "lunch", "öğle"]):
        return "Yemek ve mola saatleri ile ilgili sorularınız için 'yemek saatleri' şeklinde sorabilirsiniz. Genel olarak fabrikada yemek servisi ve mola düzenlemeleri mevcuttur."
    
    # Weather (unrelated to factory)
    if any(word in msg_lower for word in ["hava", "weather", "yağmur", "güneş"]):
        return "Hava durumu ile ilgili bilgilere fabrika sistemi üzerinden erişemem. Ancak fabrika ile ilgili diğer konularda size yardımcı olabilirim."
    
    # Default intelligent response
    return f"'{user_message}' konusunda size yardımcı olmaya çalışıyorum. Bu konuda fabrika veritabanımızda spesifik bilgi bulamadım, ancak genel olarak yardımcı olabilirim. Sorunuzu daha detaylandırabilir misiniz?"

def generate_rule_based_response(user_message: str) -> str:
    """Fallback rule-based responses"""
    msg_lower = user_message.lower()
    
    # Greetings
    greetings = ["merhaba", "selam", "hi", "hello", "hey"]
    if any(greeting in msg_lower for greeting in greetings):
        return "👋 Merhaba! MEFAPEX fabrika asistanınızım. Size nasıl yardımcı olabilirim?"
    
    # Goodbyes
    goodbyes = ["görüşürüz", "bye", "hoşça kal", "iyi günler"]
    if any(goodbye in msg_lower for goodbye in goodbyes):
        return "👋 İyi günler! Başka sorularınız olduğunda yardımcı olmaktan mutluluk duyarım."
    
    # Default response
    return "🤖 Bu konuda detaylı bilgim bulunmuyor, ancak size yardımcı olmaya çalışabilirim. Sorunuzu biraz daha detaylandırabilir misiniz? Veya fabrika ile ilgili spesifik bir konu hakkında soru sorabilirsiniz."

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
                
                if best_score > 0.75:  # Higher confidence threshold for exact matches
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
        "text_generator_loaded": text_generator is not None,
        "current_model": os.getenv("HUGGINGFACE_MODEL", "microsoft/DialoGPT-small"),
        "version": "hybrid_v2.0_enhanced"
    }

@app.get("/ai/models")
async def available_models():
    """Get available AI models information"""
    return {
        "current_model": os.getenv("HUGGINGFACE_MODEL", "microsoft/DialoGPT-small"),
        "text_generator_loaded": text_generator is not None,
        "available_models": {
            "microsoft/DialoGPT-small": {
                "size": "117M parameters",
                "description": "Fast, good conversations",
                "download_size": "~351MB",
                "speed": "Fast"
            },
            "microsoft/DialoGPT-medium": {
                "size": "354M parameters", 
                "description": "Better quality conversations",
                "download_size": "~2GB",
                "speed": "Medium"
            },
            "facebook/blenderbot_small-90M": {
                "size": "90M parameters",
                "description": "Chatbot optimized",
                "download_size": "~400MB", 
                "speed": "Very Fast"
            },
            "google/flan-t5-small": {
                "size": "80M parameters",
                "description": "Instruction following",
                "download_size": "~300MB",
                "speed": "Fast"
            },
            "gpt2": {
                "size": "124M parameters",
                "description": "General text generation", 
                "download_size": "~500MB",
                "speed": "Fast"
            }
        },
        "instructions": "Change model in .env file: HUGGINGFACE_MODEL=model_name"
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting MEFAPEX Chatbot")
    print(f"🤖 OpenAI: {'✅ Enabled' if USE_OPENAI else '❌ Disabled'}")
    print(f"🆓 Hugging Face: {'✅ Enabled' if USE_HUGGINGFACE else '❌ Disabled'}")
    print("🌐 Visit: http://localhost:8000")
    print("🔑 Login: demo / 1234")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
