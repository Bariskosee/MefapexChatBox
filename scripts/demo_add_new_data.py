#!/usr/bin/env python3
"""
Demo script showing how to add new FAQ data to the existing knowledge base.
This demonstrates how the dataset can grow over time.
"""

from embedding_loader import add_new_faq_item, test_search, generate_embeddings_free
from qdrant_client import QdrantClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Qdrant client
qdrant_client = QdrantClient(
    host=os.getenv("QDRANT_HOST", "localhost"),
    port=int(os.getenv("QDRANT_PORT", 6333))
)

def demo_add_new_data():
    """Demonstrate adding new FAQ items to expand the knowledge base"""
    
    print("🚀 Demo: Adding New Data to Existing Knowledge Base")
    print("=" * 60)
    
    # Example 1: Add overtime policy
    print("📝 Adding new FAQ item: Overtime Policy")
    add_new_faq_item(
        question="Fazla mesai politikası nedir?",
        answer="Fazla mesai günlük 8 saati aştığında başlar. Haftalık 45 saati geçen saatler %50 zamlı ödenir. Fazla mesai için önceden onay alınmalıdır.",
        keywords=["fazla mesai", "overtime", "zam", "extra pay", "45 saat", "8 saat"],
        variations=[
            "Overtime nasıl hesaplanır?",
            "Fazla mesai zamlı mı?",
            "Kaç saatten sonra fazla mesai?",
            "Extra work pay nedir?",
            "Mesai ücreti nasıl?",
            "Overtime policy nedir?"
        ]
    )
    
    # Example 2: Add vacation days policy
    print("📝 Adding new FAQ item: Annual Leave Policy")
    add_new_faq_item(
        question="Yıllık izin hakları nelerdir?",
        answer="1-5 yıl arası çalışanlar 14 gün, 5-15 yıl arası 20 gün, 15+ yıl çalışanlar 26 gün yıllık izin hakkına sahiptir. İzinler yıl içinde kullanılmalıdır.",
        keywords=["yıllık izin", "annual leave", "vacation days", "tatil hakları", "14 gün", "20 gün", "26 gün"],
        variations=[
            "Kaç gün tatil hakkım var?",
            "Annual leave days nedir?",
            "Vacation time ne kadar?",
            "Yıllık izin günleri",
            "Tatil günü sayısı",
            "Leave entitlement nedir?"
        ]
    )
    
    # Example 3: Add remote work policy
    print("📝 Adding new FAQ item: Remote Work Policy")
    add_new_faq_item(
        question="Uzaktan çalışma politikası nedir?",
        answer="Uzaktan çalışma haftada en fazla 2 gün olabilir. Önceden amir onayı gereklidir. Video konferans toplantılarına katılım zorunludur.",
        keywords=["uzaktan çalışma", "remote work", "home office", "evden çalışma", "2 gün", "video konferans"],
        variations=[
            "Home office yapabilir miyim?",
            "Remote work policy nedir?",
            "Evden çalışma kuralları",
            "WFH policy nedir?",
            "Uzaktan nasıl çalışırım?",
            "Work from home rules"
        ]
    )
    
    print("✅ Successfully added 3 new FAQ items!")
    print("\n🔍 Testing queries on the expanded knowledge base:")
    print("-" * 50)
    
    # Test the new data
    test_queries = [
        "Fazla mesai ne zaman başlar?",
        "Overtime policy nedir?", 
        "Kaç gün tatil hakkım var?",
        "Annual leave days nedir?",
        "Home office yapabilir miyim?",
        "Remote work rules nedir?"
    ]
    
    for query in test_queries:
        print(f"\n🔍 Query: '{query}'")
        try:
            # Generate embedding for query
            query_embedding = generate_embeddings_free([query])[0]
            
            # Search in Qdrant
            results = qdrant_client.search(
                collection_name="mefapex_faq",
                query_vector=query_embedding,
                limit=1,  # Just best match
                with_payload=True
            )
            
            if results:
                result = results[0]
                print(f"   ✅ Answer: {result.payload['answer']}")
                print(f"   📊 Confidence: {result.score:.4f}")
            else:
                print("   ❌ No results found")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 Demo completed! The knowledge base now has 13 FAQ items.")
    print("💡 The system automatically handles new data and maintains fuzzy matching capabilities.")

if __name__ == "__main__":
    demo_add_new_data()
