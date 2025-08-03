import json
import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Qdrant client
qdrant_client = QdrantClient(
    host=os.getenv("QDRANT_HOST", "localhost"),
    port=int(os.getenv("QDRANT_PORT", 6333))
)

# Initialize FREE sentence transformer model
model = SentenceTransformer('all-MiniLM-L6-v2')  # Free, no API key needed!

# Turkish FAQ data for MEFAPEX factory
turkish_faq_data = [
    {
        "question": "Fabrika çalışma saatleri nelerdir?",
        "answer": "Fabrikamız haftaiçi 08:00-18:00 saatleri arasında çalışmaktadır. Cumartesi günleri 08:00-13:00 arası yarım gün çalışılır."
    },
    {
        "question": "Personel giriş çıkış saatleri nedir?",
        "answer": "Personel giriş 08:00, çıkış 18:00'dedir. Geç kalanlar sistemde kayıt altına alınır. 15 dakika tolerans süresi vardır."
    },
    {
        "question": "Stok durumu nasıl görüntülenir?",
        "answer": "Stok durumu Logo sistemi üzerinden takip edilmektedir. Stok raporlarına ERP menüsünden erişilebilir."
    },
    {
        "question": "İzin başvurusu nasıl yapılır?",
        "answer": "İzin başvuruları İK departmanına yazılı olarak veya online sistem üzerinden yapılmalıdır. En az 3 gün önceden başvuru yapılması gerekmektedir."
    },
    {
        "question": "Vardiya değişiklikleri nasıl yapılır?",
        "answer": "Vardiya değişiklikleri vardiya amiri onayı ile yapılır. Değişiklik talepleri en az 1 gün önceden bildirilmelidir."
    },
    {
        "question": "Güvenlik kuralları nelerdir?",
        "answer": "Fabrikada kask, güvenlik ayakkabısı ve iş elbisesi zorunludur. Makinelere yaklaşırken dikkatli olunmalı ve güvenlik protokolleri takip edilmelidir."
    },
    {
        "question": "Yemek saatleri nedir?",
        "answer": "Öğle yemeği molası 12:00-13:00 arasındadır. Çay molaları sabah 10:00 ve öğleden sonra 15:30'da verilir."
    },
    {
        "question": "Kalite kontrol prosedürleri nelerdir?",
        "answer": "Her üretim hattında kalite kontrol noktaları bulunur. Ürünler ISO 9001 standartlarına göre test edilir ve raporlanır."
    },
    {
        "question": "Makine arızaları nasıl bildirilir?",
        "answer": "Makine arızaları derhal vardiya amiri ve teknik servise bildirilmelidir. Arıza formu doldurularak kayıt altına alınmalıdır."
    },
    {
        "question": "Üretim hedefleri nasıl takip edilir?",
        "answer": "Günlük üretim hedefleri vardiya başında belirlenir ve sistem üzerinden anlık olarak takip edilir. Raporlar saatlik güncellenir."
    }
]

def create_collection():
    """Create Qdrant collection for FAQ embeddings"""
    try:
        # Delete collection if exists
        try:
            qdrant_client.delete_collection("mefapex_faq")
            logger.info("Existing collection deleted")
        except:
            pass
        
        # Create new collection (384 dimensions for all-MiniLM-L6-v2)
        qdrant_client.create_collection(
            collection_name="mefapex_faq",
            vectors_config=VectorParams(size=384, distance=Distance.COSINE)
        )
        logger.info("Collection 'mefapex_faq' created successfully")
        
    except Exception as e:
        logger.error(f"Error creating collection: {e}")
        raise

def generate_embeddings_free(texts):
    """Generate embeddings using FREE sentence-transformers model"""
    try:
        logger.info("Generating FREE embeddings (no OpenAI API needed)...")
        embeddings = model.encode(texts)
        return embeddings.tolist()
    except Exception as e:
        logger.error(f"Error generating embeddings: {e}")
        raise

def load_faq_to_qdrant():
    """Load Turkish FAQ data with FREE embeddings to Qdrant"""
    try:
        logger.info("Starting to load FAQ data to Qdrant with FREE embeddings...")
        
        # Create collection
        create_collection()
        
        # Prepare questions for embedding
        questions = [item["question"] for item in turkish_faq_data]
        
        # Generate FREE embeddings
        logger.info("Generating FREE embeddings for questions...")
        embeddings = generate_embeddings_free(questions)
        
        # Prepare points for Qdrant
        points = []
        for idx, (faq_item, embedding) in enumerate(zip(turkish_faq_data, embeddings)):
            point = PointStruct(
                id=idx,
                vector=embedding,
                payload={
                    "question": faq_item["question"],
                    "answer": faq_item["answer"]
                }
            )
            points.append(point)
        
        # Upload to Qdrant
        logger.info("Uploading points to Qdrant...")
        qdrant_client.upsert(
            collection_name="mefapex_faq",
            points=points
        )
        
        logger.info(f"Successfully loaded {len(points)} FAQ items to Qdrant")
        
        # Verify the upload
        collection_info = qdrant_client.get_collection("mefapex_faq")
        logger.info(f"Collection info: {collection_info}")
        
    except Exception as e:
        logger.error(f"Error loading FAQ to Qdrant: {e}")
        raise

def test_search(query="Çalışma saatleri nedir?"):
    """Test the search functionality"""
    try:
        logger.info(f"Testing search with query: {query}")
        
        # Generate embedding for test query (FREE)
        query_embedding = generate_embeddings_free([query])[0]
        
        # Search in Qdrant
        results = qdrant_client.search(
            collection_name="mefapex_faq",
            query_vector=query_embedding,
            limit=3,
            with_payload=True
        )
        
        logger.info("Search results:")
        for idx, result in enumerate(results):
            logger.info(f"{idx+1}. Score: {result.score:.4f}")
            logger.info(f"   Question: {result.payload['question']}")
            logger.info(f"   Answer: {result.payload['answer']}")
            logger.info("")
            
    except Exception as e:
        logger.error(f"Error during test search: {e}")
        raise

if __name__ == "__main__":
    try:
        print("🆓 Using FREE embedding model - No OpenAI API key needed!")
        
        # Load FAQ data to Qdrant
        load_faq_to_qdrant()
        
        # Test the search
        test_search()
        
        print("✅ FREE Embedding loader completed successfully!")
        print("FAQ data has been loaded to Qdrant using FREE embeddings!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Please check your Qdrant connection.")
