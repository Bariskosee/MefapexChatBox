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
    """Improved text-based similarity for demo purposes"""
    # Normalize text - lowercase and basic cleaning
    query_clean = query.lower().strip()
    question_clean = question.lower().strip()
    
    # Exact match gets highest score
    if query_clean == question_clean:
        return 1.0
    
    # Check if query is contained in question or vice versa
    if query_clean in question_clean or question_clean in query_clean:
        return 0.8
    
    # Word-based similarity
    query_words = set(query_clean.split())
    question_words = set(question_clean.split())
    
    # Remove common Turkish stopwords
    stopwords = {'ve', 'ile', 'için', 'nasıl', 'nedir', 'nelerdir', 'ne', 'bu', 'o', 'bir', 'olan', 'olur'}
    query_words = query_words - stopwords
    question_words = question_words - stopwords
    
    if not query_words or not question_words:
        return 0.0
    
    intersection = len(query_words.intersection(question_words))
    union = len(query_words.union(question_words))
    
    if union == 0:
        return 0.0
    
    jaccard_score = intersection / union
    
    # Give bonus for key matching words
    key_words = ['çalışma', 'saat', 'mesai', 'fabrika', 'personel', 'giriş', 'çıkış', 'stok', 
                 'logo', 'izin', 'başvuru', 'vardiya', 'değişim', 'güvenlik', 'kural', 
                 'yemek', 'mola', 'kalite', 'kontrol', 'makine', 'arıza', 'üretim', 'hedef']
    
    bonus = 0
    for word in key_words:
        if word in query_clean and word in question_clean:
            bonus += 0.2
    
    final_score = min(1.0, jaccard_score + bonus)
    return final_score

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

def generate_demo_response(user_message, context, has_relevant_data=False):
    """Generate a well-formatted demo response when OpenAI API is not available"""
    
    user_lower = user_message.lower()
    
    # If we have relevant data from database, use it with clean formatting
    if has_relevant_data and context != "Bu konuda spesifik bilgim bulunmuyor.":
        if any(word in user_lower for word in ['çalışma', 'saat', 'mesai']):
            return f"""**Çalışma Saatleri**

{context}

📋 *Bu bilgi fabrika veritabanımızdan alınmıştır.*"""
            
        elif any(word in user_lower for word in ['izin', 'tatil']):
            return f"""**İzin Başvuruları**

{context}

📋 *Bu bilgi fabrika veritabanımızdan alınmıştır.*"""
            
        elif any(word in user_lower for word in ['güvenlik', 'kural']):
            return f"""**Güvenlik Kuralları**

{context}

🛡️ *Bu bilgi fabrika veritabanımızdan alınmıştır.*"""
            
        elif any(word in user_lower for word in ['vardiya', 'değişim']):
            return f"""**Vardiya Değişiklikleri**

{context}

🔄 *Bu bilgi fabrika veritabanımızdan alınmıştır.*"""
            
        elif any(word in user_lower for word in ['yemek', 'mola']):
            return f"""**Yemek ve Mola Saatleri**

{context}

🍽️ *Bu bilgi fabrika veritabanımızdan alınmıştır.*"""
            
        elif any(word in user_lower for word in ['stok', 'logo']):
            return f"""**Stok Durumu**

{context}

📦 *Bu bilgi fabrika veritabanımızdan alınmıştır.*"""
            
        elif any(word in user_lower for word in ['kalite', 'kontrol']):
            return f"""**Kalite Kontrol**

{context}

✅ *Bu bilgi fabrika veritabanımızdan alınmıştır.*"""
            
        elif any(word in user_lower for word in ['makine', 'arıza']):
            return f"""**Makine Arızası**

{context}

🔧 *Bu bilgi fabrika veritabanımızdan alınmıştır.*"""
            
        elif any(word in user_lower for word in ['üretim', 'hedef']):
            return f"""**Üretim Hedefleri**

{context}

🎯 *Bu bilgi fabrika veritabanımızdan alınmıştır.*"""
            
        else:
            return f"""**Fabrika Bilgisi**

{context}

📋 *Bu bilgi fabrika veritabanımızdan alınmıştır.*"""
    
    # If no relevant data, provide general knowledge responses with clean formatting
    else:
        if any(word in user_lower for word in ['mefapex', 'bilişim', 'şirket', 'teknoloji']):
            return """**MEFAPEX Bilişim Hakkında**

MEFAPEX, Türkiye'de faaliyet gösteren bir teknoloji şirketidir. Şirket, yazılım geliştirme, sistem entegrasyonu ve bilişim danışmanlığı alanlarında hizmet vermektedir.

**Başlıca Hizmet Alanları:**
• Yazılım geliştirme ve özelleştirme
• Sistem entegrasyonu  
• Veritabanı yönetimi
• Bilişim danışmanlığı
• Dijital dönüşüm projeleri

**Bu Chatbot Teknolojileri:**
• Python - Programlama dili
• FastAPI - Web framework
• OpenAI GPT-3.5 - AI modeli
• Qdrant - Vector veritabanı
• HTML/CSS/JavaScript - Web arayüzü

� *Bu konuda fabrika veritabanımızda spesifik bilgi bulunmuyor.*"""

        elif any(word in user_lower for word in ['ai', 'yapay', 'zeka', 'chatbot', 'chatgpt']):
            return """**ChatGPT ve Yapay Zeka Hakkında**

**ChatGPT Nedir?**
ChatGPT, OpenAI tarafından geliştirilen büyük dil modelidir (LLM). Doğal dil işleme teknolojisini kullanarak insanlarla anlık sohbet edebilir.

**ChatGPT'nin Özellikleri:**
• Geniş bilgi birikimi ve anlayış
• Çok dilli destek (Türkçe dahil)
• Yaratıcı yazma ve analiz yetenekleri
• Kod yazma ve debugging
• Sorulara detaylı yanıtlar

**Yapay Zeka Teknolojileri:**
• Makine öğrenmesi ve derin öğrenme
• Doğal dil işleme (NLP)
• Bilgisayarlı görü
• Otomasyon ve karar verme sistemleri

Bu chatbot da ChatGPT benzeri teknolojiler kullanarak size yardımcı olmaktadır.

📋 *Bu konuda fabrika veritabanımızda spesifik bilgi bulunmuyor.*"""

        elif any(word in user_lower for word in ['merhaba', 'selam', 'hello', 'hi']):
            return """**Merhaba! 👋**

Ben MEFAPEX fabrikasının AI asistanıyım. Size yardımcı olmaktan mutluluk duyarım.

**Size nasıl yardımcı olabilirim?**

🏭 **Fabrika konularında:**
• Çalışma saatleri ve vardiya bilgileri
• Güvenlik kuralları ve prosedürler
• İzin başvuruları ve tatil planları
• Yemek saatleri ve sosyal olanaklar

💬 **Genel konularda:**
• Şirket hakkında bilgiler
• Teknoloji ve AI konuları
• Günlük sorular ve merak ettikleriniz

Sorunuzu Türkçe olarak yazabilirsiniz. Size en iyi şekilde yardımcı olmaya çalışacağım! ✨"""

        else:
            return """**Genel Bilgi** �

Bu konu hakkında genel bilgi verebilirim, ancak spesifik detaylar için uygun kaynaklara başvurmanızı öneririm.

**Yardım alabileceğiniz yerler:**
• Yöneticinize başvurabilirsiniz
• İnsan Kaynakları departmanından bilgi alabilirsiniz  
• Teknik konular için IT desteği ile iletişime geçebilirsiniz

**Size yardımcı olabileceğim konular:**
• Fabrika ile ilgili genel sorular
• Çalışma düzeni ve kurallar
• Şirket hakkında bilgiler
• Teknoloji ve AI konuları

📋 *Bu konuda fabrika veritabanımızda spesifik bilgi bulunmuyor.*

Başka bir sorunuz var mı? Size yardımcı olmaktan memnuniyet duyarım! 💫"""

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
            return ChatResponse(response="Güncel üretim çıktısı: 850 adet. Bu bilgi canlı sistemden alınmıştır. (Demo Mode)")
        
        # Search for similar questions in demo data
        search_results = search_similar_demo(user_message, top_k=1)
        
        # Log search results for debugging
        if search_results:
            logger.info(f"Search results - Top match score: {search_results[0]['score']:.3f}")
            logger.info(f"Top match question: {search_results[0]['data']['question']}")
        else:
            logger.info("No search results found")
        
        # Determine if we have relevant info from database
        has_relevant_context = False
        context = ""
        similarity_threshold = 0.1  # Lowered threshold even more for demo similarity
        
        if search_results and search_results[0]['score'] > similarity_threshold:
            # Found relevant info in database
            has_relevant_context = True
            best_match = search_results[0]
            context = f"{best_match['data']['answer']}"
            logger.info(f"Using database context with score: {best_match['score']:.3f}")
        else:
            # No relevant info in database
            has_relevant_context = False
            context = "Bu konuda spesifik bilgim bulunmuyor."
            logger.info("No relevant database context found, will use general knowledge")
        
        # Try to use OpenAI API, fallback to demo response
        try:
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
Eğer soruyla ilgili bir şey bilmiyorsan, bunu açıkça belirt.
Yanıtını ChatGPT kalitesinde temiz ve okunabilir formatta sun."""
            
            # Generate response using GPT-3.5 Turbo
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
            
        except Exception as openai_error:
            logger.warning(f"OpenAI API error: {openai_error}")
            # Fallback to demo response
            bot_response = generate_demo_response(user_message, context, has_relevant_context)
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
