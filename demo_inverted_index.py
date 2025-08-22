#!/usr/bin/env python3
"""
Inverted Index Performance Demo
Shows the performance improvement visually with real examples
"""

import time
import sys
import os

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def demo_performance_improvement():
    """Demonstrate the performance improvement with visual comparison"""
    print("=" * 70)
    print("🚀 INVERTED INDEX vs LINEAR SEARCH PERFORMANCE DEMO")
    print("=" * 70)
    
    from content_manager import ContentManager
    
    # Initialize content manager
    cm = ContentManager()
    
    # Test queries that should show good performance differences
    demo_queries = [
        "merhaba nasılsınız",
        "çalışma saatleri nedir", 
        "mefapex teknoloji firma",
        "teknik destek yardım",
        "yazılım geliştirme programming",
        "teşekkür ederim sağol",
        "bilinmeyen rastgele soru"
    ]
    
    print(f"\n🔍 Index Information:")
    print(f"   Keywords indexed: {len(cm._keyword_index)}")
    print(f"   Phrases indexed: {len(cm._phrase_index)}")
    print(f"   Categories: {len(cm.static_responses)}")
    
    print(f"\n📊 Performance Comparison:")
    print(f"{'Query':<35} {'Inverted (ms)':<12} {'Linear (ms)':<12} {'Speedup':<10} {'Match'}")
    print("-" * 80)
    
    total_inverted_time = 0
    total_linear_time = 0
    
    for query in demo_queries:
        # Test with inverted index
        cm._index_built = True
        start = time.perf_counter()
        response1, source1 = cm._find_static_response_direct(query.lower())
        inverted_time = time.perf_counter() - start
        total_inverted_time += inverted_time
        
        # Test with linear search
        cm._index_built = False
        start = time.perf_counter()
        response2, source2 = cm._find_static_response_direct(query.lower())
        linear_time = time.perf_counter() - start
        total_linear_time += linear_time
        
        # Calculate speedup
        speedup = linear_time / inverted_time if inverted_time > 0 else float('inf')
        match_result = "✅" if response1 else "❌"
        
        # Display results
        query_short = query[:30] + "..." if len(query) > 30 else query
        print(f"{query_short:<35} {inverted_time*1000:<12.4f} {linear_time*1000:<12.4f} {speedup:<10.1f}x {match_result}")
    
    # Restore inverted index
    cm._index_built = True
    
    # Summary
    total_speedup = total_linear_time / total_inverted_time if total_inverted_time > 0 else float('inf')
    improvement = ((total_linear_time - total_inverted_time) / total_linear_time) * 100
    
    print("-" * 80)
    print(f"{'TOTAL':<35} {total_inverted_time*1000:<12.4f} {total_linear_time*1000:<12.4f} {total_speedup:<10.1f}x")
    print(f"\n✨ Overall Performance Improvement: {improvement:.1f}%")
    print(f"⚡ Average Speedup: {total_speedup:.1f}x faster")
    
    # Show some index details
    print(f"\n🔍 Index Details:")
    print(f"   Most common words in index:")
    word_counts = {}
    for word, categories in cm._keyword_index.items():
        word_counts[word] = len(categories)
    
    # Show top 10 words by category count
    top_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    for word, count in top_words:
        print(f"   '{word}' appears in {count} categories")
    
    # Test specific lookup scenarios
    print(f"\n🧪 Testing Specific Scenarios:")
    
    scenarios = [
        ("Single word match", "merhaba"),
        ("Multi-word phrase", "çalışma saatleri"),
        ("Partial match", "mefapex bilişim"),
        ("No match", "random xyz 123"),
        ("Category name", "technology_info")
    ]
    
    for scenario_name, test_query in scenarios:
        response, source = cm._find_static_response_direct(test_query.lower())
        result = "Found" if response else "Not found"
        print(f"   {scenario_name}: '{test_query}' -> {result} ({source})")

def show_index_structure():
    """Show the structure of the inverted index"""
    print(f"\n" + "=" * 70)
    print("📚 INVERTED INDEX STRUCTURE")
    print("=" * 70)
    
    from content_manager import ContentManager
    cm = ContentManager()
    
    print(f"\n🔤 Keyword Index Structure:")
    print(f"   Total keywords: {len(cm._keyword_index)}")
    
    # Group by category
    category_keywords = {}
    for word, categories in cm._keyword_index.items():
        for category in categories:
            if category not in category_keywords:
                category_keywords[category] = []
            category_keywords[category].append(word)
    
    for category, words in category_keywords.items():
        print(f"\n   📁 {category}:")
        # Show first 15 words for each category
        words_to_show = words[:15]
        remaining = len(words) - len(words_to_show)
        print(f"      {', '.join(words_to_show)}")
        if remaining > 0:
            print(f"      ... and {remaining} more words")
    
    print(f"\n📝 Phrase Index Structure:")
    print(f"   Total phrases: {len(cm._phrase_index)}")
    
    # Group phrases by category
    category_phrases = {}
    for phrase, categories in cm._phrase_index.items():
        for category in categories:
            if category not in category_phrases:
                category_phrases[category] = []
            category_phrases[category].append(phrase)
    
    for category, phrases in category_phrases.items():
        print(f"\n   📁 {category}:")
        # Show first 10 phrases for each category
        phrases_to_show = phrases[:10]
        remaining = len(phrases) - len(phrases_to_show)
        for phrase in phrases_to_show:
            print(f"      '{phrase}'")
        if remaining > 0:
            print(f"      ... and {remaining} more phrases")

if __name__ == "__main__":
    demo_performance_improvement()
    show_index_structure()
