# Alternative embedding loader without requiring Qdrant
# Uses in-memory vector storage for development/testing

import json
import openai
import os
import numpy as np
from dotenv import load_dotenv
import pickle
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize OpenAI client
openai.api_key = os.getenv("OPENAI_API_KEY")

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

def generate_embeddings(texts):
    """Generate embeddings for a list of texts using OpenAI"""
    try:
        response = openai.embeddings.create(
            model="text-embedding-ada-002",
            input=texts
        )
        return [data.embedding for data in response.data]
    except Exception as e:
        logger.error(f"Error generating embeddings: {e}")
        raise

def cosine_similarity(a, b):
    """Calculate cosine similarity between two vectors"""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def load_faq_to_memory():
    """Load Turkish FAQ data with embeddings to memory"""
    try:
        logger.info("Starting to load FAQ data to memory...")
        
        # Prepare questions for embedding
        questions = [item["question"] for item in turkish_faq_data]
        
        # Generate embeddings
        logger.info("Generating embeddings for questions...")
        embeddings = generate_embeddings(questions)
        
        # Create in-memory vector store
        vector_store = {
            'embeddings': embeddings,
            'data': turkish_faq_data
        }
        
        # Save to file for persistence
        with open('faq_embeddings.pkl', 'wb') as f:
            pickle.dump(vector_store, f)
        
        logger.info(f"Successfully loaded {len(turkish_faq_data)} FAQ items to memory")
        
        return vector_store
        
    except Exception as e:
        logger.error(f"Error loading FAQ to memory: {e}")
        raise

def search_similar(query, vector_store, top_k=1):
    """Search for similar questions using cosine similarity"""
    try:
        # Generate embedding for query
        query_embedding = generate_embeddings([query])[0]
        
        # Calculate similarities
        similarities = []
        for i, embedding in enumerate(vector_store['embeddings']):
            similarity = cosine_similarity(query_embedding, embedding)
            similarities.append((similarity, i))
        
        # Sort by similarity and get top results
        similarities.sort(reverse=True)
        
        results = []
        for similarity, idx in similarities[:top_k]:
            results.append({
                'score': similarity,
                'data': vector_store['data'][idx]
            })
        
        return results
        
    except Exception as e:
        logger.error(f"Error during search: {e}")
        raise

def test_search(vector_store, query="Çalışma saatleri nedir?"):
    """Test the search functionality"""
    try:
        logger.info(f"Testing search with query: {query}")
        
        results = search_similar(query, vector_store, top_k=3)
        
        logger.info("Search results:")
        for idx, result in enumerate(results):
            logger.info(f"{idx+1}. Score: {result['score']:.4f}")
            logger.info(f"   Question: {result['data']['question']}")
            logger.info(f"   Answer: {result['data']['answer']}")
            logger.info("")
            
    except Exception as e:
        logger.error(f"Error during test search: {e}")
        raise

if __name__ == "__main__":
    try:
        # Load FAQ data to memory
        vector_store = load_faq_to_memory()
        
        # Test the search
        test_search(vector_store)
        
        print("✅ Memory-based embedding loader completed successfully!")
        print("FAQ data has been loaded to memory and is ready for use.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Please check your environment variables and API key.")
