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

# Enhanced Turkish FAQ data for MEFAPEX factory with question variations
turkish_faq_data = [
    {
        "question": "Fabrika çalışma saatleri nelerdir?",
        "answer": "Fabrikamız haftaiçi 08:00-18:00 saatleri arasında çalışmaktadır. Cumartesi günleri 08:00-13:00 arası yarım gün çalışılır.",
        "keywords": ["çalışma saatleri", "working hours", "fabrika açılış", "factory open", "iş saatleri", "work time", "kaçta açılıyor", "kaçta kapanıyor", "ne zaman açık"],
        "variations": [
            "Çalışma saatleri nedir?",
            "Fabrika kaçta açılıyor?",
            "Fabrika kaçta kapanıyor?",
            "İş saatleri nedir?",
            "Ne zaman çalışıyoruz?",
            "Fabrika ne zaman açık?",
            "Working hours nedir?",
            "Calışma saatlerim ne?",
            "is kaçta başlıyor?",
            "Kaç saat çalışıyoruz?"
        ]
    },
    {
        "question": "Personel giriş çıkış saatleri nedir?",
        "answer": "Personel giriş 08:00, çıkış 18:00'dedir. Geç kalanlar sistemde kayıt altına alınır. 15 dakika tolerans süresi vardır.",
        "keywords": ["giriş çıkış", "entry exit", "personel saatleri", "staff hours", "mesai", "work shift"],
        "variations": [
            "Giriş saati kaç?",
            "Çıkış saati kaç?",
            "Ne zaman işe gelmeliyim?",
            "Ne zaman evime gidebilirim?",
            "Mesai saatleri nedir?",
            "Hangi saatte fabrikadan ayrılırım?"
        ]
    },
    {
        "question": "Yemek saatleri nedir?",
        "answer": "Öğle yemeği molası 12:00-13:00 arasındadır. Çay molaları sabah 10:00 ve öğleden sonra 15:30'da verilir.",
        "keywords": ["yemek saatleri", "lunch time", "öğle arası", "lunch break", "mola", "break", "çay molası"],
        "variations": [
            "Öğle arası ne zaman?",
            "Yemek molası kaçta?",
            "Lunch break ne zaman?",
            "Çay molası ne zaman?",
            "Mola saatleri nedir?",
            "Ne zaman yemek yiyebilirim?",
            "Öğle arası kaçta başlıyor?",
            "Yemek ne zaman?",
            "öğle arası ne zaman?"
        ]
    },
    {
        "question": "Stok durumu nasıl görüntülenir?",
        "answer": "Stok durumu Logo sistemi üzerinden takip edilmektedir. Stok raporlarına ERP menüsünden erişilebilir.",
        "keywords": ["stok", "stock", "envanter", "inventory", "logo sistem", "erp"],
        "variations": [
            "Stok nasıl kontrol edilir?",
            "Envanter nerede görülür?",
            "Stock kontrolü nasıl yapılır?",
            "ERP'de stok nerede?",
            "Logo sisteminde stok"
        ]
    },
    {
        "question": "İzin başvurusu nasıl yapılır?",
        "answer": "İzin başvuruları İK departmanına yazılı olarak veya online sistem üzerinden yapılmalıdır. En az 3 gün önceden başvuru yapılması gerekmektedir.",
        "keywords": ["izin", "leave", "tatil", "vacation", "ik", "hr", "başvuru"],
        "variations": [
            "Nasıl izin alırım?",
            "Leave nasıl başvururum?",
            "Tatil izni nasıl alınır?",
            "İK'ya nasıl başvururum?",
            "Online izin sistemi nerede?"
        ]
    },
    {
        "question": "Vardiya değişiklikleri nasıl yapılır?",
        "answer": "Vardiya değişiklikleri vardiya amiri onayı ile yapılır. Değişiklik talepleri en az 1 gün önceden bildirilmelidir.",
        "keywords": ["vardiya", "shift", "değişiklik", "change", "amir", "supervisor"],
        "variations": [
            "Shift nasıl değiştirilir?",
            "Vardiya nasıl değişir?",
            "Mesai saati nasıl değişir?",
            "Amire nasıl başvururum?"
        ]
    },
    {
        "question": "Güvenlik kuralları nelerdir?",
        "answer": "Fabrikada kask, güvenlik ayakkabısı ve iş elbisesi zorunludur. Makinelere yaklaşırken dikkatli olunmalı ve güvenlik protokolleri takip edilmelidir.",
        "keywords": ["güvenlik", "safety", "kask", "helmet", "iş güvenliği", "work safety"],
        "variations": [
            "Safety kuralları nedir?",
            "İş güvenliği kuralları",
            "Fabrikada nelere dikkat etmeliyim?",
            "Hangi ekipmanları kullanmalıyım?"
        ]
    },
    {
        "question": "Kalite kontrol prosedürleri nelerdir?",
        "answer": "Her üretim hattında kalite kontrol noktaları bulunur. Ürünler ISO 9001 standartlarına göre test edilir ve raporlanır.",
        "keywords": ["kalite", "quality", "kontrol", "control", "iso", "test"],
        "variations": [
            "Quality control nasıl yapılır?",
            "Kalite nasıl kontrol edilir?",
            "ISO standartları nedir?",
            "Ürün kalitesi nasıl test edilir?"
        ]
    },
    {
        "question": "Makine arızaları nasıl bildirilir?",
        "answer": "Makine arızaları derhal vardiya amiri ve teknik servise bildirilmelidir. Arıza formu doldurularak kayıt altına alınmalıdır.",
        "keywords": ["makine", "machine", "arıza", "breakdown", "teknik servis", "technical service"],
        "variations": [
            "Machine breakdown nasıl bildirilir?",
            "Arıza nasıl rapor edilir?",
            "Teknik servise nasıl ulaşırım?",
            "Makine bozulduğunda ne yapmalıyım?"
        ]
    },
    {
        "question": "Üretim hedefleri nasıl takip edilir?",
        "answer": "Günlük üretim hedefleri vardiya başında belirlenir ve sistem üzerinden anlık olarak takip edilir. Raporlar saatlik güncellenir.",
        "keywords": ["üretim", "production", "hedef", "target", "takip", "tracking"],
        "variations": [
            "Production target nasıl görülür?",
            "Üretim rakamları nerede?",
            "Günlük hedefler nerede görülür?",
            "Production nasıl takip edilir?"
        ]
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

def prepare_enhanced_text_for_embedding(faq_item):
    """Prepare enhanced text that includes question, variations, and keywords for better matching"""
    base_text = faq_item["question"]
    
    # Add variations to improve matching
    if "variations" in faq_item:
        variations_text = " ".join(faq_item["variations"])
        base_text += " " + variations_text
    
    # Add keywords for better semantic understanding
    if "keywords" in faq_item:
        keywords_text = " ".join(faq_item["keywords"])
        base_text += " " + keywords_text
    
    return base_text

def load_faq_to_qdrant():
    """Load Turkish FAQ data with FREE embeddings to Qdrant - Enhanced version"""
    try:
        logger.info("Starting to load enhanced FAQ data to Qdrant with FREE embeddings...")
        
        # Create collection
        create_collection()
        
        # Prepare enhanced texts for embedding (includes variations and keywords)
        enhanced_texts = []
        for item in turkish_faq_data:
            enhanced_text = prepare_enhanced_text_for_embedding(item)
            enhanced_texts.append(enhanced_text)
        
        # Generate FREE embeddings
        logger.info("Generating FREE embeddings for enhanced question data...")
        embeddings = generate_embeddings_free(enhanced_texts)
        
        # Prepare points for Qdrant
        points = []
        for idx, (faq_item, embedding) in enumerate(zip(turkish_faq_data, embeddings)):
            point = PointStruct(
                id=idx,
                vector=embedding,
                payload={
                    "question": faq_item["question"],
                    "answer": faq_item["answer"],
                    "keywords": faq_item.get("keywords", []),
                    "variations": faq_item.get("variations", []),
                    "enhanced_text": enhanced_texts[idx]  # Store the enhanced text for debugging
                }
            )
            points.append(point)
        
        # Upload to Qdrant
        logger.info("Uploading enhanced points to Qdrant...")
        qdrant_client.upsert(
            collection_name="mefapex_faq",
            points=points
        )
        
        logger.info(f"Successfully loaded {len(points)} enhanced FAQ items to Qdrant")
        
        # Verify the upload
        collection_info = qdrant_client.get_collection("mefapex_faq")
        logger.info(f"Collection info: {collection_info}")
        
    except Exception as e:
        logger.error(f"Error loading enhanced FAQ to Qdrant: {e}")
        raise

def test_search(query="Çalışma saatleri nedir?"):
    """Test the enhanced search functionality with fuzzy matching"""
    try:
        logger.info(f"Testing enhanced search with query: {query}")
        
        # Generate embedding for test query (FREE)
        query_embedding = generate_embeddings_free([query])[0]
        
        # Search in Qdrant
        results = qdrant_client.search(
            collection_name="mefapex_faq",
            query_vector=query_embedding,
            limit=3,
            with_payload=True
        )
        
        logger.info("Enhanced search results:")
        for idx, result in enumerate(results):
            logger.info(f"{idx+1}. Score: {result.score:.4f}")
            logger.info(f"   Question: {result.payload['question']}")
            logger.info(f"   Answer: {result.payload['answer']}")
            if 'keywords' in result.payload:
                logger.info(f"   Keywords: {', '.join(result.payload['keywords'])}")
            logger.info("")
            
    except Exception as e:
        logger.error(f"Error during enhanced test search: {e}")
        raise

def add_new_faq_item(question, answer, keywords=None, variations=None):
    """
    Add a new FAQ item to the existing collection
    This function allows the dataset to grow over time
    
    Args:
        question (str): The main question
        answer (str): The answer to the question
        keywords (list): Optional list of keywords for better matching
        variations (list): Optional list of question variations
    """
    try:
        logger.info(f"Adding new FAQ item: {question}")
        
        # Prepare the new item
        new_item = {
            "question": question,
            "answer": answer,
            "keywords": keywords or [],
            "variations": variations or []
        }
        
        # Generate enhanced text for embedding
        enhanced_text = prepare_enhanced_text_for_embedding(new_item)
        
        # Generate embedding
        embedding = generate_embeddings_free([enhanced_text])[0]
        
        # Get current collection info to determine next ID
        collection_info = qdrant_client.get_collection("mefapex_faq")
        next_id = collection_info.points_count
        
        # Create new point
        new_point = PointStruct(
            id=next_id,
            vector=embedding,
            payload={
                "question": question,
                "answer": answer,
                "keywords": keywords or [],
                "variations": variations or [],
                "enhanced_text": enhanced_text
            }
        )
        
        # Add to Qdrant
        qdrant_client.upsert(
            collection_name="mefapex_faq",
            points=[new_point]
        )
        
        logger.info(f"Successfully added new FAQ item with ID: {next_id}")
        return next_id
        
    except Exception as e:
        logger.error(f"Error adding new FAQ item: {e}")
        raise

def update_existing_faq_item(item_id, question=None, answer=None, keywords=None, variations=None):
    """
    Update an existing FAQ item in the collection
    
    Args:
        item_id (int): The ID of the item to update
        question (str): New question (optional)
        answer (str): New answer (optional)  
        keywords (list): New keywords (optional)
        variations (list): New variations (optional)
    """
    try:
        logger.info(f"Updating FAQ item with ID: {item_id}")
        
        # Get current item
        current_points = qdrant_client.scroll(
            collection_name="mefapex_faq",
            with_payload=True,
            limit=1,
            filter={
                "must": [
                    {"key": "id", "match": {"value": item_id}}
                ]
            }
        )
        
        if not current_points[0]:
            raise ValueError(f"No item found with ID: {item_id}")
            
        current_payload = current_points[0][0].payload
        
        # Update fields
        updated_item = {
            "question": question or current_payload["question"],
            "answer": answer or current_payload["answer"],
            "keywords": keywords if keywords is not None else current_payload.get("keywords", []),
            "variations": variations if variations is not None else current_payload.get("variations", [])
        }
        
        # Generate new embedding
        enhanced_text = prepare_enhanced_text_for_embedding(updated_item)
        embedding = generate_embeddings_free([enhanced_text])[0]
        
        # Update point
        updated_point = PointStruct(
            id=item_id,
            vector=embedding,
            payload={
                "question": updated_item["question"],
                "answer": updated_item["answer"],
                "keywords": updated_item["keywords"],
                "variations": updated_item["variations"],
                "enhanced_text": enhanced_text
            }
        )
        
        # Update in Qdrant
        qdrant_client.upsert(
            collection_name="mefapex_faq",
            points=[updated_point]
        )
        
        logger.info(f"Successfully updated FAQ item with ID: {item_id}")
        
    except Exception as e:
        logger.error(f"Error updating FAQ item: {e}")
        raise

def test_multiple_queries():
    """Test various query types including misspelled and incomplete queries"""
    test_queries = [
        "Çalışma saatleri nedir?",  # Perfect Turkish
        "Calışma saatlerim ne?",    # Misspelled (missing ç)
        "is kaçta başlıyor?",       # Incomplete (missing İ)
        "Öğle arası ne zaman?",     # Perfect Turkish
        "öğle arası ne zaman?",     # Lowercase
        "lunch break ne zaman?",    # Mixed language
        "Working hours nedir?",     # Mixed language
        "Fabrika kaçta kapanıyor?", # Different phrasing
        "Ne zaman evime gidebilirim?", # Natural language
        "Mola saatleri",            # Very short query
        "break time",               # English
        "yemek ne zaman?"           # Informal
    ]
    
    print("\n" + "="*80)
    print("🔍 TESTING ENHANCED FUZZY SEARCH CAPABILITIES")
    print("="*80)
    
    for query in test_queries:
        print(f"\n📝 Query: '{query}'")
        print("-" * 50)
        
        try:
            # Generate embedding for query
            query_embedding = generate_embeddings_free([query])[0]
            
            # Search in Qdrant
            results = qdrant_client.search(
                collection_name="mefapex_faq",
                query_vector=query_embedding,
                limit=2,  # Top 2 results
                with_payload=True
            )
            
            for idx, result in enumerate(results):
                print(f"   {idx+1}. Score: {result.score:.4f}")
                print(f"      ❓ Question: {result.payload['question']}")
                print(f"      ✅ Answer: {result.payload['answer']}")
                if idx == 0:  # Only show best match answer
                    print(f"      🎯 Best Match!")
                print()
                
        except Exception as e:
            print(f"      ❌ Error: {e}")
            
    print("="*80)

if __name__ == "__main__":
    try:
        print("🆓 Using FREE embedding model - No OpenAI API key needed!")
        print("🚀 Enhanced version with fuzzy matching, misspelling tolerance, and multilingual support!")
        
        # Load enhanced FAQ data to Qdrant
        load_faq_to_qdrant()
        
        # Test the basic search
        test_search()
        
        # Test multiple query variations including misspelled and incomplete queries
        test_multiple_queries()
        
        print("✅ Enhanced FREE Embedding loader completed successfully!")
        print("📚 FAQ data with variations and keywords has been loaded to Qdrant!")
        print("🔍 The system now handles misspelled, incomplete, and mixed-language queries!")
        print("🌟 Ready for intelligent question-answering with fuzzy matching!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Please check your Qdrant connection.")
