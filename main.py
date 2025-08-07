from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from sentence_transformers import SentenceTransformer
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
import torch
import openai
import os
from dotenv import load_dotenv
import logging
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt
import uuid
import json
from database_manager import DatabaseManager

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🔐 AUTHENTICATION CONFIGURATION
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# In-memory storage (replace with database in production)
users_db = {}
chat_sessions = {}

# Initialize database manager
db_manager = DatabaseManager()

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
        logger.info(f"🤖 Loading model: {model_name}")
        
        try:
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
        except OSError as e:
            logger.error(f"Model loading failed: {e}")
            USE_HUGGINGFACE = False
        except ImportError as e:
            logger.error(f"Missing dependencies: {e}")
            USE_HUGGINGFACE = False
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

#️ DATA MODELS
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

# 🆕 NEW MODELS FOR ENHANCED FEATURES
class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UserInDB(BaseModel):
    user_id: str
    username: str
    email: str
    hashed_password: str
    full_name: Optional[str] = None
    created_at: datetime
    is_active: bool = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class ChatSession(BaseModel):
    session_id: str
    user_id: str
    messages: List[Dict]
    created_at: datetime

class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: List[Dict]
    total_messages: int

# 🔐 AUTHENTICATION UTILITIES
def verify_password(plain_password, hashed_password):
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """Hash a password"""
    return pwd_context.hash(password)

def get_user(username: str):
    """Get user from database"""
    return users_db.get(username)

def authenticate_user(username: str, password: str):
    """Authenticate user credentials"""
    user = get_user(username)
    if not user:
        return False
    if not verify_password(password, user["hashed_password"]):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    # Handle demo user
    if token_data.username == "demo":
        return {
            "user_id": "demo-user-id",
            "username": "demo",
            "email": "demo@mefapex.com",
            "full_name": "Demo User",
            "created_at": datetime.utcnow(),
            "is_active": True,
            "is_demo": True
        }
    
    # Handle regular users
    user = get_user(username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

def get_user_session(user_id: str) -> str:
    """Get or create user session ID (persistent)"""
    return db_manager.get_or_create_session(user_id)

def add_message_to_session(session_id: str, user_message: str, bot_response: str, source: str, user_id: str = None):
    """Add message to chat session (persistent)"""
    if user_id is None:
        # Try to infer user_id from session (legacy fallback)
        user_id = None
    db_manager.add_message(session_id, user_id, user_message, bot_response, source)

@app.get("/")
async def read_root():
    return FileResponse("static/index.html")

# 🆕 USER REGISTRATION
@app.post("/register", response_model=dict)
async def register_user(user: UserRegister):
    """Register a new user"""
    try:
        # Check if user already exists
        if user.username in users_db:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        
        # Check if email already exists
        for existing_user in users_db.values():
            if existing_user["email"] == user.email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
        
        # Create new user
        user_id = str(uuid.uuid4())
        hashed_password = get_password_hash(user.password)
        
        users_db[user.username] = {
            "user_id": user_id,
            "username": user.username,
            "email": user.email,
            "hashed_password": hashed_password,
            "full_name": user.full_name,
            "created_at": datetime.utcnow(),
            "is_active": True
        }
        
        logger.info(f"✅ New user registered: {user.username}")
        
        return {
            "success": True,
            "message": "User registered successfully",
            "user_id": user_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

# 🆕 USER LOGIN WITH JWT (supports demo user)
@app.post("/login", response_model=Token)
async def login_for_access_token(form_data: LoginRequest):
    """Authenticate user and return access token"""
    # Check for demo user first
    if form_data.username == "demo" and form_data.password == "1234":
        # Create a temporary demo user entry for JWT
        demo_user = {
            "user_id": "demo-user-id",
            "username": "demo",
            "email": "demo@mefapex.com",
            "is_demo": True
        }
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": "demo"}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}
    
    # Check regular users
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# 🆕 LEGACY LOGIN (for backward compatibility)
@app.post("/login-legacy", response_model=LoginResponse)
async def login_legacy(request: LoginRequest):
    """Legacy login endpoint for demo purposes"""
    # Keep demo login for testing
    if request.username == "demo" and request.password == "1234":
        return LoginResponse(success=True, message="Giriş başarılı")
    
    # Check real users
    user = authenticate_user(request.username, request.password)
    if user:
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
    """Generate response using Hugging Face with improved AI capabilities"""
    
    # Eğer veritabanında context varsa kullan
    if context and "Answer:" in context:
        lines = context.split('\n')
        for line in lines:
            if 'Answer:' in line:
                answer = line.split(':', 1)[-1].strip()
                if answer:
                    return f"📋 {answer}\n\n💡 Bu bilgi MEFAPEX fabrika veritabanından alınmıştır."
    
    # Veritabanında bilgi yoksa, genel AI yanıtı üret
    user_lower = user_message.lower().strip()
    
    # MEFAPEX soruları için öncelikli kontrol
    if any(word in user_lower for word in ["mefapex", "nedir", "ne", "what"]) and "mefapex" in user_lower:
        return """🏭 **MEFAPEX Fabrikası Hakkında**

MEFAPEX, Türkiye'de faaliyet gösteren modern bir üretim fabrikasıdır.

**Fabrika Özellikleri:**
• 🏗️ **Modern Üretim**: En son teknoloji ile donatılmış tesisler
• 🛡️ **Güvenlik Odaklı**: Çalışan güvenliği birinci öncelik
• 🌟 **Kalite**: Uluslararası standartlarda üretim
• 👥 **İnsan Kaynakları**: Deneyimli ve eğitimli çalışan kadrosu
• 🌱 **Sürdürülebilirlik**: Çevre dostu üretim süreçleri

**Faaliyet Alanları:**
• Endüstriyel üretim ve imalat
• Kalite kontrol ve test süreçleri
• Ar-Ge ve inovasyon çalışmaları
• İş güvenliği ve çalışan eğitimleri

**Misyonumuz:**
Yüksek kaliteli ürünlerle hem yerel hem de global pazarda güvenilir bir üretici olmak.

Size MEFAPEX hakkında başka hangi konularda bilgi verebilirim? 🤝"""
    
    # AI/IA hakkında sorular
    if any(word in user_lower for word in ["ia", "ai", "yapay zeka", "artificial intelligence", "IA nedir"]):
        return """🤖 **IA (Intelligence Artificielle) / Yapay Zeka Nedir?**

IA veya AI (Artificial Intelligence), makinelerin insan benzeri zeka göstermesini sağlayan teknolojilerin genel adıdır.

**Temel Özellikler:**
• Öğrenme ve adaptasyon yeteneği
• Problem çözme ve karar verme
• Doğal dil işleme ve anlama
• Görüntü ve ses tanıma
• Otonom hareket ve planlama

**Kullanım Alanları:**
• Sağlık: Hastalık teşhisi, ilaç keşfi
• Finans: Risk analizi, dolandırıcılık tespiti
• Üretim: Kalite kontrol, tahmine dayalı bakım
• Eğitim: Kişiselleştirilmiş öğrenme
• Günlük hayat: Sesli asistanlar, öneri sistemleri

Ben de bir AI asistanıyım ve size MEFAPEX fabrikası hakkında yardımcı olmak için buradayım! 🎯"""

    # ChatGPT hakkında sorular
    elif any(word in user_lower for word in ["chatgpt", "gpt", "openai"]):
        return """💬 **ChatGPT Nedir?**

ChatGPT, OpenAI tarafından geliştirilen gelişmiş bir dil modelidir. GPT (Generative Pre-trained Transformer) teknolojisini kullanır.

**Yetenekleri:**
• Doğal dil anlama ve üretme
• Çok dilli destek (100+ dil)
• Kod yazma ve debugging
• Yaratıcı içerik üretimi
• Analiz ve problem çözme

**Nasıl Çalışır:**
• Milyarlarca parametreli sinir ağı
• Transformer mimarisi
• Bağlamsal anlama ve tahmin
• Sürekli öğrenme ve gelişme

Ben de benzer teknolojiler kullanıyorum! Size nasıl yardımcı olabilirim? 🚀"""

    # Python hakkında sorular
    elif any(word in user_lower for word in ["python", "programlama", "kod", "yazılım"]):
        return """🐍 **Python Programlama Dili**

Python, yüksek seviyeli, yorumlanabilir ve çok amaçlı bir programlama dilidir.

**Özellikleri:**
• Kolay ve okunabilir sözdizimi
• Geniş kütüphane desteği
• Platform bağımsız
• Açık kaynak ve ücretsiz
• Dinamik tip sistemi

**Kullanım Alanları:**
• Web geliştirme (Django, Flask)
• Veri bilimi (Pandas, NumPy)
• Yapay zeka (TensorFlow, PyTorch)
• Otomasyon ve scripting
• Oyun geliştirme

Bu chatbot da Python ile geliştirilmiştir! 🎯"""

    # Teknoloji genel soruları
    elif any(word in user_lower for word in ["teknoloji", "bilgisayar", "internet", "dijital"]):
        return """💻 **Teknoloji ve Dijital Dönüşüm**

Modern teknoloji, hayatımızın her alanını dönüştürüyor.

**Önemli Teknoloji Trendleri:**
• Yapay Zeka ve Makine Öğrenmesi
• Bulut Bilişim (Cloud Computing)
• Nesnelerin İnterneti (IoT)
• Blockchain ve Kripto
• 5G ve Bağlantı Teknolojileri
• Sanal ve Artırılmış Gerçeklik

**Fabrikada Teknoloji:**
MEFAPEX fabrikamız da modern teknolojileri kullanarak üretim verimliliğini artırıyor.

Teknoloji hakkında spesifik sorularınız varsa, sormaktan çekinmeyin! 🚀"""

    # Matematik/Hesaplama soruları
    elif any(word in user_lower for word in ["hesapla", "matematik", "toplam", "çarp", "böl", "eksi", "artı"]):
        return """🔢 **Matematik ve Hesaplama**

Matematik sorunuz için size yardımcı olmaya çalışayım!

Basit hesaplamalar yapabilirim:
• Toplama, çıkarma, çarpma, bölme
• Yüzde hesaplamaları
• Oran ve orantı
• Basit denklemler

Lütfen hesaplamanızı net bir şekilde yazın. Örnek:
- "15 + 27 kaç eder?"
- "120'nin %15'i nedir?"
- "8 x 12 = ?"

Not: Karmaşık hesaplamalar için hesap makinesi kullanmanızı öneririm. 📊"""

    # Genel selamlama
    elif any(word in user_lower for word in ["merhaba", "selam", "günaydın", "iyi günler", "hey", "hello"]):
        return """👋 **Merhaba! Hoş geldiniz!**

Ben MEFAPEX fabrikasının AI asistanıyım. Size yardımcı olmaktan mutluluk duyarım!

**Size yardımcı olabileceğim konular:**
• Fabrika ile ilgili sorular (çalışma saatleri, kurallar vb.)
• Genel bilgi soruları
• Teknoloji ve AI konuları
• Basit hesaplamalar
• Ve daha fazlası...

Nasıl yardımcı olabilirim? 😊"""

    # Teşekkür mesajları
    elif any(word in user_lower for word in ["teşekkür", "sağol", "eyvallah", "thanks"]):
        return """� **Rica ederim!**

Yardımcı olabildiysem ne mutlu bana! 

Başka sorularınız olursa her zaman buradayım. Size yardımcı olmak benim için bir zevk.

İyi günler dilerim! 🌟"""

    # Veda mesajları
    elif any(word in user_lower for word in ["görüşürüz", "hoşçakal", "bye", "iyi akşamlar", "iyi geceler"]):
        return """👋 **Görüşmek üzere!**

Size yardımcı olabildiğim için mutluyum. 

Tekrar görüşmek üzere! Başka sorularınız olduğunda ben burada olacağım.

İyi günler dilerim! 🌟"""

    # Fabrika dışı genel sorular için
    else:
        # Önce gelişmiş AI response'u dene
        if text_generator is not None:
            try:
                ai_response = generate_advanced_ai_response(user_message)
                if ai_response and len(ai_response) > 20:
                    return f"🤖 {ai_response}\n\n💡 Bu yanıt AI tarafından üretilmiştir."
            except Exception as e:
                logger.warning(f"Advanced AI response failed: {e}")
        
        # Fallback: Basit text generation
        if text_generator is not None:
            try:
                # Türkçe prompt
                prompt = f"Soru: {user_message}\nYanıt:"
                
                # Model ile yanıt üret - eski API uyumlu
                result = text_generator(
                    prompt,
                    max_length=min(len(prompt) + 80, 200),
                    num_return_sequences=1,
                    temperature=0.7,
                    do_sample=True,
                    pad_token_id=text_generator.tokenizer.eos_token_id
                )
                
                generated = result[0]['generated_text']
                # Sadece yanıt kısmını al
                if "Yanıt:" in generated:
                    response = generated.split("Yanıt:")[-1].strip()
                else:
                    response = generated[len(prompt):].strip()
                
                # Response'u temizle
                response = response.split('\n')[0].strip()
                response = response.split('Soru:')[0].strip()
                
                if len(response) > 15:  # Yeterince uzun bir cevap üretildiyse
                    return f"🤖 {response}\n\n💡 Bu yanıt AI tarafından üretilmiştir."
            except Exception as e:
                logger.warning(f"Basic text generation failed: {e}")
        
        # Fallback: Genel yardımcı yanıt
        return f"""🤖 **'{user_message}' hakkında:**

Bu konu hakkında size yardımcı olmaya çalışıyorum. 

Sorunuz fabrika veritabanımızda bulunmamakla birlikte, genel bilgilerimle yanıt vermeye çalışabilirim.

**Daha iyi yardım için:**
• Sorunuzu daha detaylı yazabilirsiniz
• Fabrika ile ilgili konularda daha spesifik sorular sorabilirsiniz
• Veya farklı bir konu hakkında soru sorabilirsiniz

Size başka nasıl yardımcı olabilirim? 💭"""

def generate_advanced_ai_response(user_message: str) -> str:
    """Generate response using advanced Hugging Face text generation model"""
    try:
        if text_generator is None:
            raise Exception("Text generator not loaded")
        
        # DialoGPT için konuşma formatında prompt
        # Model konuşma tarzında eğitilmiş, bu yüzden diyalog formatı kullanmalıyız
        conversation_prompt = f"Kullanıcı: {user_message}\nAsistan:"
        
        # Generate response - DialoGPT için optimize edilmiş
        outputs = text_generator(
            conversation_prompt,
            max_length=min(len(conversation_prompt) + 80, 200),
            num_return_sequences=1,
            temperature=0.8,
            do_sample=True,
            top_p=0.9,
            top_k=50,
            pad_token_id=text_generator.tokenizer.eos_token_id,
            eos_token_id=text_generator.tokenizer.eos_token_id,
            no_repeat_ngram_size=2,
            repetition_penalty=1.2
        )
        
        # Extract the generated text
        generated_text = outputs[0]['generated_text']
        
        # Extract only the assistant's response
        if "Asistan:" in generated_text:
            response = generated_text.split("Asistan:")[-1].strip()
        else:
            response = generated_text[len(conversation_prompt):].strip()
        
        # Clean up the response
        response = response.replace("\\n", " ").strip()
        response = response.replace("  ", " ").strip()
        
        # Remove unwanted patterns
        response = response.split("Kullanıcı:")[0].strip()  # Stop at next user input
        response = response.split("\n")[0].strip()  # Take first line
        
        # DialoGPT sometimes generates very short responses, which is normal
        # But we want at least some meaningful content
        if len(response) < 5:
            raise Exception(f"Generated response too short: '{response}'")
        
        # Check for garbled/meaningless output (common with DialoGPT)
        # Look for repetitive patterns or non-Turkish characters
        words = response.split()
        if len(words) > 0:
            # Check for too much repetition
            unique_words = set(words)
            if len(unique_words) < len(words) / 2 and len(words) > 3:
                raise Exception(f"Generated response too repetitive: '{response}'")
            
            # Check for meaningless patterns
            meaningless_patterns = ['malaziz', 'nazir', 'aksine', 'kelar', 'bajkim']
            if any(pattern in response.lower() for pattern in meaningless_patterns):
                raise Exception(f"Generated response contains meaningless patterns: '{response}'")
        
        # Limit response length
        if len(response) > 150:
            # Find last complete word or sentence
            response = response[:150]
            last_space = response.rfind(' ')
            if last_space > 100:
                response = response[:last_space]
        
        # Post-process for better Turkish responses
        if response and len(response) >= 5:
            # Add contextual enhancement for Turkish
            if any(word in user_message.lower() for word in ['nedir', 'ne', 'nasıl', 'neden']):
                if not any(char in response for char in '.!?'):
                    response += "."
            return response
        else:
            raise Exception("Generated response not meaningful")
        
    except Exception as e:
        logger.warning(f"Advanced AI generation failed: {e}")
        # Fallback to local AI with more intelligent responses
        return generate_ai_response_local(user_message)

def generate_ai_response_local(user_message: str) -> str:
    """Generate AI response using enhanced local intelligence"""
    # Convert to lowercase for analysis
    msg_lower = user_message.lower().strip()
    
    # Python ve Programlama Soruları
    if any(word in msg_lower for word in ["python", "programlama", "kod", "yazılım", "programming"]):
        return """🐍 **Python ve Programlama Hakkında**

Python, öğrenmesi kolay ve güçlü bir programlama dilidir.

**Başlangıç için öneriler:**
• Python.org'dan ücretsiz indirebilirsiniz
• Online kurslar: Codecademy, Python.org tutorials
• Temel konular: değişkenler, döngüler, fonksiyonlar
• Pratik projeler yaparak öğrenin

**Kullanım alanları:**
• Web geliştirme (Django, Flask)
• Veri analizi (Pandas, NumPy)
• Yapay zeka (TensorFlow, scikit-learn)
• Otomasyon ve scripting

Hangi alanda odaklanmak istiyorsunuz? 🚀"""

    # Yapay Zeka Soruları
    elif any(word in msg_lower for word in ["yapay zeka", "ai", "artificial intelligence", "makine öğrenmesi", "machine learning"]):
        return """🤖 **Yapay Zeka Hakkında**

Yapay zeka, makinelerin insan benzeri zeka göstermesini sağlar.

**Temel Kavramlar:**
• **Makine Öğrenmesi**: Verilerden öğrenme
• **Derin Öğrenme**: Sinir ağları ile karmaşık pattern'ler
• **Doğal Dil İşleme**: Metinleri anlama ve üretme
• **Bilgisayarla Görme**: Görüntü tanıma ve analiz

**Günlük Hayatta AI:**
• Sesli asistanlar (Siri, Alexa)
• Öneri sistemleri (Netflix, YouTube)
• Çeviri servisleri (Google Translate)
• Otomatik araçlar

Ben de bir AI asistanıyım! Spesifik bir AI konusu merak ediyor musunuz? 🎯"""

    # Teknoloji Genel
    elif any(word in msg_lower for word in ["teknoloji", "bilgisayar", "internet", "dijital", "technology"]):
        return """💻 **Modern Teknoloji**

Teknoloji hayatımızı sürekli şekillendiriyor.

**Güncel Trendler:**
• **Bulut Bilişim**: Her yerden erişilebilir veriler
• **Mobil Teknolojiler**: Akıllı telefonlar ve uygulamalar
• **Nesnelerin İnterneti (IoT)**: Bağlı cihazlar
• **Siber Güvenlik**: Dijital koruma
• **Blockchain**: Güvenli veri paylaşımı

**Öğrenme Kaynakları:**
• Online platformlar (Coursera, Udemy)
• YouTube eğitim kanalları
• Teknoloji blogları ve podcastler

Hangi teknoloji alanı sizi ilgilendiriyor? 🌐"""

    # Öğrenme ve Eğitim
    elif any(word in msg_lower for word in ["öğren", "eğitim", "ders", "kurs", "learn", "study"]):
        return """📚 **Öğrenme ve Gelişim**

Sürekli öğrenmek modern dünyanın anahtarıdır.

**Etkili Öğrenme Yöntemleri:**
• **Aktif Öğrenme**: Sadece okumak değil, pratik yapmak
• **Proje Tabanlı**: Gerçek projelerle öğrenmek
• **Topluluk**: Online forumlar ve gruplar
• **Düzenli Tekrar**: Spaced repetition tekniği

**Ücretsiz Kaynaklar:**
• Khan Academy, Coursera (audit)
• YouTube eğitim kanalları
• GitHub açık kaynak projeleri
• Stack Overflow (programlama)

Hangi konuda gelişmek istiyorsunuz? 🎓"""

    # İş ve Kariyer
    elif any(word in msg_lower for word in ["iş", "kariyer", "job", "career", "work", "meslek"]):
        return """💼 **Kariyer ve İş Dünyası**

Modern iş dünyası sürekli değişiyor.

**Gelecekteki Beceriler:**
• **Dijital Okuryazarlık**: Teknoloji kullanımı
• **Problem Çözme**: Analitik düşünme
• **İletişim**: Hem yazılı hem sözlü
• **Uyum Yeteneği**: Değişime açık olma
• **İşbirliği**: Takım çalışması

**Kariyer Tavsiyeleri:**
• LinkedIn profilinizi güncel tutun
• Sürekli yeni beceriler edinin
• Network oluşturun ve güçlendirin
• Kişisel projeler geliştirin

Hangi sektörde çalışmayı hedefliyorsunuz? 🚀"""

    # Sağlık ve Yaşam
    elif any(word in msg_lower for word in ["sağlık", "health", "yaşam", "life", "beslenme", "spor"]):
        return """🏥 **Sağlık ve Yaşam Kalitesi**

Sağlıklı yaşam, hem fiziksel hem mental iyilik hali gerektirir.

**Temel Prensipler:**
• **Dengeli Beslenme**: Çeşitli besin grupları
• **Düzenli Egzersiz**: Haftada en az 150 dakika
• **Yeterli Uyku**: 7-9 saat kaliteli uyku
• **Stres Yönetimi**: Meditasyon, hobi aktiviteleri
• **Sosyal Bağlantılar**: Aile ve arkadaş ilişkileri

**Dijital Sağlık:**
• Sağlık uygulamaları kullanın
• Düzenli kontroller yaptırın
• Güvenilir kaynaklardan bilgi alın

Not: Sağlık konularında mutlaka uzman görüşü alın! 🌟"""

    # Genel selamlama ve tanışma
    elif any(word in msg_lower for word in ["merhaba", "selam", "hi", "hello", "hey", "nasılsın", "kimsin", "sen kim"]):
        return """👋 **Merhaba! Tanışmak güzel!**

Ben MEFAPEX fabrikasının AI asistanıyım. Size yardımcı olmak için buradayım!

**Size yardımcı olabileceğim konular:**
• 🏭 Fabrika ile ilgili sorular
• 💻 Teknoloji ve programlama
• 🤖 Yapay zeka ve AI
• 📚 Öğrenme ve gelişim tavsiyeleri
• 💼 Kariyer ve iş dünyası
• 🔢 Basit matematik hesaplamaları

**Nasıl çalışırım:**
• Sorularınızı anlayıp uygun yanıtlar vermeye çalışırım
• Fabrika veritabanını tarayabilir, genel bilgilerimi kullanabilirim
• Sürekli öğrenmeye ve gelişmeye odaklıyım

Hangi konuda size yardımcı olabilirim? 😊"""

    # Teşekkür ve veda
    elif any(word in msg_lower for word in ["teşekkür", "thanks", "sağol", "görüşürüz", "bye", "hoşça kal"]):
        return """🙏 **Rica ederim!**

Size yardımcı olabildiysem ne mutlu bana! 

**Unutmayın:**
• Her zaman burada olmaya devam edeceğim
• Yeni sorularınız için sormaktan çekinmeyin
• Sürekli öğrenmeye devam edin

İyi günler dilerim! Tekrar görüşmek üzere! 🌟"""

    # Fabrika ve MEFAPEX
    elif any(word in msg_lower for word in ["mefapex", "fabrika", "factory", "üretim", "işçi", "çalışan"]):
        return """🏭 **MEFAPEX Fabrikası**

MEFAPEX, modern üretim teknolojileri ile kaliteli ürünler üreten bir fabrikadır.

**Fabrika Değerleri:**
• 🛡️ **Güvenlik**: Çalışan güvenliği öncelik
• 🌟 **Kalite**: Yüksek standartlarda üretim
• 🌱 **Sürdürülebilirlik**: Çevreye duyarlı üretim
• 👥 **İnsan Odaklı**: Çalışan refahı önemli
• 🔧 **İnovasyon**: Sürekli gelişim ve teknoloji

**Size yardımcı olabileceğim fabrika konuları:**
• Çalışma saatleri ve vardiyalar
• Güvenlik kuralları ve prosedürler
• İzin ve tatil prosedürleri
• Genel fabrika bilgileri

Spesifik bir konu hakkında soru sormak ister misiniz? 🤝"""

    # Zamana dayalı sorular
    elif any(word in msg_lower for word in ["saat", "zaman", "time", "ne zaman", "when"]):
        return """⏰ **Zaman ve Zamanlama**

Zamanlama konularında size yardımcı olmaya çalışayım.

**Genel Zaman Bilgileri:**
• Standart çalışma saatleri: Genellikle 08:00-17:00
• Mola saatleri: Öğle arası ve çay molaları
• Vardiya sistemleri: Bazı bölümlerde 24 saat üretim

**Daha spesifik bilgi için şunları sorabilirsiniz:**
• "Çalışma saatleri nedir?"
• "Mola saatleri ne zaman?"
• "Vardiya değişim saatleri nedir?"
• "Fabrika ne zaman açık?"

Hangi zaman konusunda bilgi almak istiyorsunuz? 📅"""

    # Matematiksel sorular
    elif any(word in msg_lower for word in ["hesapla", "matematik", "math", "sayı", "number", "hesap"]):
        return """🔢 **Matematik ve Hesaplama**

Basit matematik işlemlerinde size yardımcı olabilirim!

**Yapabileceğim hesaplamalar:**
• ➕ Toplama: "15 + 27"
• ➖ Çıkarma: "100 - 35" 
• ✖️ Çarpma: "8 × 12" veya "8 x 12"
• ➗ Bölme: "144 ÷ 12"
• 📊 Yüzde: "200'nin %15'i"

**Örnek kullanım:**
• "25 + 17 kaç eder?"
• "120'nin %20'si nedir?"
• "15 x 8 = ?"

Hesaplamanızı yukarıdaki formatlardan birinde yazabilir misiniz? 📱"""

    # Yardım ve rehberlik
    elif any(word in msg_lower for word in ["yardım", "help", "nasıl", "how", "rehber"]):
        return """🆘 **Yardım ve Rehberlik**

Size en iyi şekilde yardımcı olmak istiyorum!

**Bana şunları sorabilirsiniz:**
• 🏭 **Fabrika konuları**: Çalışma saatleri, kurallar, prosedürler
• 💻 **Teknoloji**: Python, AI, programlama, bilgisayar
• 📚 **Öğrenme**: Eğitim kaynakları, beceri geliştirme
• 🔢 **Hesaplama**: Basit matematik işlemleri
• 💼 **Kariyer**: İş dünyası, beceriler, tavsiyelr

**Daha iyi yanıt almak için:**
• Sorularınızı net ve açık yazın
• Spesifik konular belirtin
• Örnek vererek detaylandırın

Hangi konuda yardıma ihtiyacınız var? 💪"""

    # Default: Akıllı genel yanıt
    else:
        # Soru tipini analiz et
        question_words = ["ne", "nedir", "nasıl", "neden", "niçin", "hangi", "kim", "where", "what", "how", "why", "which", "who"]
        is_question = any(word in msg_lower for word in question_words) or "?" in user_message
        
        if is_question:
            return f"""🤔 **'{user_message}' hakkında...**

Bu konuda size yardımcı olmaya çalışıyorum. Fabrika veritabanımızda spesifik bilgi bulamadım, ancak genel bilgilerimle destekleyebilirim.

**Daha iyi yardım için şunları deneyebilirsiniz:**
• Soruyu daha detaylandırın
• Hangi alanda bilgi istediğinizi belirtin
• Fabrika ile ilgili sorular için spesifik konular sorun

**Popüler konularım:**
• 🏭 Fabrika operasyonları • 💻 Teknoloji ve AI • 📚 Öğrenme tavsiyeleri
• 🔢 Matematik hesaplamaları • 💼 Kariyer rehberliği

Size başka nasıl yardımcı olabilirim? 💭"""
        else:
            return f"""💬 **'{user_message}' konusunda...**

Bu konuyu anlıyorum ve size yardımcı olmaya çalışıyorum. 

**Size şunları önerebilirim:**
• Bu konuda daha spesifik sorular sorabilirsiniz
• Hangi açıdan yaklaşmak istediğinizi belirtebilirsiniz
• İlgili diğer konular hakkında soru sorabilirsiniz

**Ben şu konularda uzmanım:**
• 🏭 MEFAPEX fabrika bilgileri • 💻 Teknoloji ve programlama 
• 🤖 Yapay zeka • 📚 Eğitim ve öğrenme • 🔢 Matematik

Hangi açıdan size yardımcı olabilirim? 🎯"""

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

# 🆕 CHAT HISTORY ENDPOINTS
@app.get("/chat/history/{user_id}", response_model=ChatHistoryResponse)
async def get_chat_history(user_id: str, current_user: dict = Depends(get_current_user)):
    """Get chat history for a user (last 20 messages, persistent)"""
    try:
        if current_user["user_id"] != user_id and not current_user.get("is_admin", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        session_id = db_manager.get_or_create_session(user_id)
        messages = db_manager.get_chat_history(user_id, limit=20)
        return ChatHistoryResponse(
            session_id=session_id,
            messages=messages,
            total_messages=len(messages)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching chat history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch chat history"
        )

@app.delete("/chat/history/{user_id}")
async def clear_chat_history(user_id: str, current_user: dict = Depends(get_current_user)):
    """Clear chat history for a user (persistent)"""
    try:
        if current_user["user_id"] != user_id and not current_user.get("is_admin", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        db_manager.clear_chat_history(user_id)
        return {"success": True, "message": "Chat history cleared"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing chat history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear chat history"
        )

@app.get("/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user information"""
    return {
        "user_id": current_user["user_id"],
        "username": current_user["username"],
        "email": current_user["email"],
        "full_name": current_user.get("full_name"),
        "created_at": current_user["created_at"].isoformat() if isinstance(current_user["created_at"], datetime) else current_user["created_at"]
    }

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

# 🆕 AUTHENTICATED CHAT WITH SESSION MANAGEMENT
@app.post("/chat/authenticated", response_model=ChatResponse)
async def chat_authenticated(message: ChatMessage, current_user: dict = Depends(get_current_user)):
    """
    Authenticated chat endpoint with session management:
    1. Search in Qdrant database using available embedding method
    2. Generate response using OpenAI or Hugging Face
    3. Save to user's chat session
    4. Fallback mechanism for reliability
    """
    try:
        user_message = message.message.strip()
        
        if not user_message:
            raise HTTPException(status_code=400, detail="Mesaj boş olamaz")
        
        logger.info(f"User {current_user['username']} message: {user_message}")
        
        # Get or create user session
        session_id = get_user_session(current_user["user_id"])
        
        # Generate embedding for search
        try:
            user_embedding = generate_embedding(user_message)
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            response_text = "🤖 Sistem geçici olarak kullanılamıyor. Lütfen daha sonra tekrar deneyin."
            source = "error"
            add_message_to_session(session_id, user_message, response_text, source, user_id=current_user["user_id"])
            return ChatResponse(response=response_text, source=source)
        
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
        
        # Save to session
        add_message_to_session(session_id, user_message, response_text, source, user_id=current_user["user_id"])
        
        return ChatResponse(response=response_text, source=source)
        
    except Exception as e:
        logger.error(f"Authenticated chat endpoint error: {e}")
        response_text = "🤖 Bir hata oluştu. Lütfen tekrar deneyin."
        source = "error"
        
        # Try to save to session even on error
        try:
            session_id = get_user_session(current_user["user_id"])
            add_message_to_session(session_id, user_message, response_text, source, user_id=current_user["user_id"])
        except:
            pass
            
        return ChatResponse(response=response_text, source=source)

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
