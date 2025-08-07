# Demo version with pre-computed embeddings (no OpenAI API calls needed)
import json
import numpy as np
import pickle
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Turkish FAQ data with pre-computed embeddings (simulated for demo)
demo_faq_data = [
    {
        "id": 0,
        "question": "Fabrika çalışma saatleri nelerdir?",
        "answer": "Fabrikamız haftaiçi 08:00-18:00 saatleri arasında çalışmaktadır. Cumartesi günleri 08:00-13:00 arası yarım gün çalışılır.",
        "embedding": [0.1, -0.2, 0.3, 0.8, -0.1, 0.4, -0.3, 0.2] + [0.0] * 1528  # Simplified 1536-dim vector
    },
    {
        "id": 1,
        "question": "Personel giriş çıkış saatleri nedir?",
        "answer": "Personel giriş 08:00, çıkış 18:00'dedir. Geç kalanlar sistemde kayıt altına alınır. 15 dakika tolerans süresi vardır.",
        "embedding": [0.2, -0.1, 0.4, 0.7, -0.2, 0.3, -0.2, 0.1] + [0.0] * 1528
    },
    {
        "id": 2,
        "question": "Stok durumu nasıl görüntülenir?",
        "answer": "Stok durumu Logo sistemi üzerinden takip edilmektedir. Stok raporlarına ERP menüsünden erişilebilir.",
        "embedding": [-0.1, 0.3, -0.2, 0.1, 0.5, -0.4, 0.2, 0.6] + [0.0] * 1528
    },
    {
        "id": 3,
        "question": "İzin başvurusu nasıl yapılır?",
        "answer": "İzin başvuruları İK departmanına yazılı olarak veya online sistem üzerinden yapılmalıdır. En az 3 gün önceden başvuru yapılması gerekmektedir.",
        "embedding": [0.3, 0.1, -0.3, -0.1, 0.2, 0.5, -0.1, 0.4] + [0.0] * 1528
    },
    {
        "id": 4,
        "question": "Vardiya değişiklikleri nasıl yapılır?",
        "answer": "Vardiya değişiklikleri vardiya amiri onayı ile yapılır. Değişiklik talepleri en az 1 gün önceden bildirilmelidir.",
        "embedding": [-0.2, 0.4, 0.1, -0.3, 0.6, 0.2, -0.5, 0.1] + [0.0] * 1528
    },
    {
        "id": 5,
        "question": "Güvenlik kuralları nelerdir?",
        "answer": "Fabrikada kask, güvenlik ayakkabısı ve iş elbisesi zorunludur. Makinelere yaklaşırken dikkatli olunmalı ve güvenlik protokolleri takip edilmelidir.",
        "embedding": [0.4, -0.3, 0.2, 0.5, -0.4, 0.1, 0.6, -0.1] + [0.0] * 1528
    },
    {
        "id": 6,
        "question": "Yemek saatleri nedir?",
        "answer": "Öğle yemeği molası 12:00-13:00 arasındadır. Çay molaları sabah 10:00 ve öğleden sonra 15:30'da verilir.",
        "embedding": [0.1, 0.2, -0.1, 0.4, 0.3, -0.2, 0.1, 0.5] + [0.0] * 1528
    },
    {
        "id": 7,
        "question": "Kalite kontrol prosedürleri nelerdir?",
        "answer": "Her üretim hattında kalite kontrol noktaları bulunur. Ürünler ISO 9001 standartlarına göre test edilir ve raporlanır.",
        "embedding": [-0.3, 0.1, 0.4, -0.2, 0.1, 0.6, -0.1, 0.3] + [0.0] * 1528
    },
    {
        "id": 8,
        "question": "Makine arızaları nasıl bildirilir?",
        "answer": "Makine arızaları derhal vardiya amiri ve teknik servise bildirilmelidir. Arıza formu doldurularak kayıt altına alınmalıdır.",
        "embedding": [0.2, -0.4, 0.3, 0.1, -0.1, 0.4, 0.2, -0.3] + [0.0] * 1528
    },
    {
        "id": 9,
        "question": "Üretim hedefleri nasıl takip edilir?",
        "answer": "Günlük üretim hedefleri vardiya başında belirlenir ve sistem üzerinden anlık olarak takip edilir. Raporlar saatlik güncellenir.",
        "embedding": [0.5, 0.2, -0.2, 0.3, 0.1, -0.3, 0.4, 0.2] + [0.0] * 1528
    }
]

def cosine_similarity(a, b):
    """Calculate cosine similarity between two vectors"""
    a = np.array(a)
    b = np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def simple_text_similarity(query, question):
    """Simple text-based similarity for demo purposes"""
    query_words = set(query.lower().split())
    question_words = set(question.lower().split())
    
    intersection = len(query_words.intersection(question_words))
    union = len(query_words.union(question_words))
    
    if union == 0:
        return 0.0
    
    return intersection / union

def create_demo_vector_store():
    """Create demo vector store"""
    vector_store = {
        'embeddings': [item['embedding'] for item in demo_faq_data],
        'data': [{'question': item['question'], 'answer': item['answer']} for item in demo_faq_data]
    }
    
    # Save to file
    with open('demo_faq_embeddings.pkl', 'wb') as f:
        pickle.dump(vector_store, f)
    
    logger.info(f"Created demo vector store with {len(demo_faq_data)} items")
    return vector_store

def search_similar_demo(query, vector_store, top_k=1):
    """Search for similar questions using simple similarity"""
    results = []
    
    for i, data_item in enumerate(vector_store['data']):
        # Use simple text similarity for demo
        similarity = simple_text_similarity(query, data_item['question'])
        
        results.append({
            'score': similarity,
            'data': data_item
        })
    
    # Sort by similarity
    results.sort(key=lambda x: x['score'], reverse=True)
    
    return results[:top_k]

def test_search_demo(vector_store):
    """Test the demo search functionality"""
    test_queries = [
        "Çalışma saatleri nedir?",
        "İzin nasıl alınır?",
        "Güvenlik kuralları",
        "Vardiya değişimi",
        "Yemek molası"
    ]
    
    for query in test_queries:
        logger.info(f"Testing query: '{query}'")
        results = search_similar_demo(query, vector_store, top_k=2)
        
        for idx, result in enumerate(results):
            logger.info(f"  {idx+1}. Score: {result['score']:.3f}")
            logger.info(f"     Question: {result['data']['question']}")
            logger.info(f"     Answer: {result['data']['answer'][:50]}...")
        logger.info("")

if __name__ == "__main__":
    try:
        logger.info("Creating demo vector store (no OpenAI API required)...")
        
        # Create demo vector store
        vector_store = create_demo_vector_store()
        
        # Test the search
        test_search_demo(vector_store)
        
        print("✅ Demo embedding loader completed successfully!")
        print("Demo FAQ data is ready for use (no OpenAI API required).")
        print("This will work until you can fix your OpenAI API quota.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        logger.error(f"Demo loader error: {e}")
