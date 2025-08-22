#!/usr/bin/env python3
"""
Simple test to verify inverted index functionality
"""

import json
import os
import sys
import time

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_inverted_index_basic():
    """Test basic inverted index functionality"""
    print("=" * 60)
    print("🔍 INVERTED INDEX BASIC FUNCTIONALITY TEST")
    print("=" * 60)
    
    # Create a simple content manager for testing
    from content_manager import ContentManager
    
    # Initialize content manager
    cm = ContentManager()
    
    # Test that index was built
    print(f"\n📊 Index Status:")
    print(f"   Index built: {cm._index_built}")
    print(f"   Keywords indexed: {len(cm._keyword_index)}")
    print(f"   Phrases indexed: {len(cm._phrase_index)}")
    
    if cm._index_built:
        print(f"\n🔍 Sample Keywords in Index:")
        sample_keywords = list(cm._keyword_index.keys())[:10]
        for keyword in sample_keywords:
            categories = cm._keyword_index[keyword]
            print(f"   '{keyword}' -> {list(categories)}")
    
    # Test sample queries
    test_queries = [
        "merhaba",
        "çalışma saatleri",
        "teknoloji",
        "destek",
        "mefapex"
    ]
    
    print(f"\n📝 Testing Sample Queries:")
    for query in test_queries:
        start_time = time.perf_counter()
        response, source = cm._find_static_response_direct(query.lower())
        end_time = time.perf_counter()
        
        time_ms = (end_time - start_time) * 1000
        found = "✅" if response else "❌"
        
        print(f"   {found} '{query}' -> {source} ({time_ms:.4f}ms)")
    
    # Show stats
    stats = cm.get_stats()
    print(f"\n📈 Stats:")
    index_info = stats.get("inverted_index", {})
    print(f"   Enabled: {index_info.get('enabled', False)}")
    print(f"   Keywords: {index_info.get('keywords', 0)}")
    print(f"   Phrases: {index_info.get('phrases', 0)}")
    print(f"   Avg categories per keyword: {index_info.get('avg_categories_per_keyword', 0):.2f}")
    
    print(f"\n✅ Basic functionality test completed!")

if __name__ == "__main__":
    test_inverted_index_basic()
