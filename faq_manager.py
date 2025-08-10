#!/usr/bin/env python3
"""
Interactive FAQ Management Tool
Allows easy addition and testing of FAQ items for the MEFAPEX ChatBox knowledge base.
"""

import sys
from embedding_loader import (
    add_new_faq_item, 
    test_search, 
    generate_embeddings_free,
    qdrant_client
)
import json

def interactive_add_faq():
    """Interactive tool to add new FAQ items"""
    print("\n🆕 ADD NEW FAQ ITEM")
    print("=" * 40)
    
    question = input("📝 Enter the main question: ").strip()
    if not question:
        print("❌ Question cannot be empty!")
        return
    
    answer = input("✅ Enter the answer: ").strip()
    if not answer:
        print("❌ Answer cannot be empty!")
        return
    
    print("\n🏷️  Enter keywords (separated by commas, press Enter to skip):")
    keywords_input = input("Keywords: ").strip()
    keywords = [k.strip() for k in keywords_input.split(",") if k.strip()] if keywords_input else []
    
    print("\n🔄 Enter question variations (one per line, press Enter twice to finish):")
    variations = []
    while True:
        variation = input("Variation: ").strip()
        if not variation:
            break
        variations.append(variation)
    
    try:
        item_id = add_new_faq_item(question, answer, keywords, variations)
        print(f"\n✅ Successfully added FAQ item with ID: {item_id}")
        
        # Test the new item
        print(f"\n🔍 Testing search with your question...")
        test_search(question)
        
    except Exception as e:
        print(f"\n❌ Error adding FAQ item: {e}")

def interactive_search():
    """Interactive search tool"""
    print("\n🔍 SEARCH FAQ DATABASE")
    print("=" * 40)
    
    while True:
        query = input("\n🔍 Enter your question (or 'back' to return): ").strip()
        if query.lower() in ['back', 'b', 'exit', 'quit']:
            break
        
        if not query:
            print("❌ Please enter a question!")
            continue
            
        try:
            # Generate embedding for query
            query_embedding = generate_embeddings_free([query])[0]
            
            # Search in Qdrant
            results = qdrant_client.search(
                collection_name="mefapex_faq",
                query_vector=query_embedding,
                limit=3,
                with_payload=True
            )
            
            print(f"\n📊 Search Results for: '{query}'")
            print("-" * 50)
            
            if results:
                for idx, result in enumerate(results, 1):
                    print(f"\n{idx}. 📊 Confidence: {result.score:.4f}")
                    print(f"   ❓ Question: {result.payload['question']}")
                    print(f"   ✅ Answer: {result.payload['answer']}")
                    if idx == 1:
                        print("   🎯 BEST MATCH")
            else:
                print("❌ No results found!")
                
        except Exception as e:
            print(f"❌ Search error: {e}")

def show_database_stats():
    """Show current database statistics"""
    try:
        collection_info = qdrant_client.get_collection("mefapex_faq")
        print(f"\n📊 DATABASE STATISTICS")
        print("=" * 40)
        print(f"📚 Total FAQ Items: {collection_info.points_count}")
        print(f"🔧 Collection Status: {collection_info.status}")
        print(f"🎯 Vector Dimensions: 384 (sentence-transformers)")
        print(f"📈 Distance Metric: Cosine Similarity")
        
    except Exception as e:
        print(f"❌ Error getting database stats: {e}")

def export_database():
    """Export current FAQ database to JSON"""
    try:
        # Get all points from collection
        all_points = qdrant_client.scroll(
            collection_name="mefapex_faq",
            with_payload=True,
            limit=1000  # Adjust if you have more items
        )
        
        export_data = []
        for point in all_points[0]:
            export_data.append({
                "id": point.id,
                "question": point.payload["question"],
                "answer": point.payload["answer"],
                "keywords": point.payload.get("keywords", []),
                "variations": point.payload.get("variations", [])
            })
        
        filename = "mefapex_faq_export.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ Database exported to {filename}")
        print(f"📊 Exported {len(export_data)} FAQ items")
        
    except Exception as e:
        print(f"❌ Export error: {e}")

def main_menu():
    """Main interactive menu"""
    while True:
        print("\n" + "="*60)
        print("🤖 MEFAPEX FAQ MANAGEMENT TOOL")
        print("="*60)
        print("1. 🆕 Add New FAQ Item")
        print("2. 🔍 Search FAQ Database") 
        print("3. 📊 Show Database Statistics")
        print("4. 💾 Export Database to JSON")
        print("5. 🧪 Run Test Queries")
        print("6. ❌ Exit")
        print("-"*60)
        
        choice = input("Choose an option (1-6): ").strip()
        
        if choice == "1":
            interactive_add_faq()
        elif choice == "2":
            interactive_search()
        elif choice == "3":
            show_database_stats()
        elif choice == "4":
            export_database()
        elif choice == "5":
            print("\n🧪 Running test queries...")
            from embedding_loader import test_multiple_queries
            test_multiple_queries()
        elif choice == "6":
            print("\n👋 Goodbye! FAQ management tool closing...")
            break
        else:
            print("\n❌ Invalid choice! Please select 1-6.")

if __name__ == "__main__":
    try:
        print("🚀 Starting MEFAPEX FAQ Management Tool...")
        print("🔗 Connecting to Qdrant database...")
        
        # Test connection
        collection_info = qdrant_client.get_collection("mefapex_faq")
        print(f"✅ Connected! Found {collection_info.points_count} FAQ items.")
        
        main_menu()
        
    except Exception as e:
        print(f"❌ Failed to connect to Qdrant database: {e}")
        print("💡 Make sure Qdrant is running and the FAQ data is loaded.")
        print("💡 Run 'python embedding_loader.py' first to initialize the database.")
        sys.exit(1)
