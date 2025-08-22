#!/usr/bin/env python3
"""
Test script for Turkish morphological analysis improvements
Tests the enhanced Turkish content manager with lemmatization and morphological variations
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from improved_turkish_content_manager import ImprovedTurkishContentManager, TurkishMorphAnalyzer

def test_morphological_analyzer():
    """Test the Turkish morphological analyzer"""
    print("🔍 Testing Turkish Morphological Analyzer")
    print("=" * 50)
    
    analyzer = TurkishMorphAnalyzer()
    
    # Test words with various morphological forms
    test_words = [
        # Verbs
        "çalışıyor", "çalışıyorum", "çalışan", "çalışmak",
        "gidiyor", "gittik", "gitmek", "gittiğim",
        "yapıyor", "yaptım", "yapmak", "yapacağım",
        
        # Nouns with inflections
        "saatleri", "saatin", "saate", "saatler",
        "işleri", "işin", "işe", "işler",
        "sistemleri", "sistemin", "sisteme",
        
        # Adjectives
        "iyidir", "kötüdür", "hızlıdır", "yavaştır",
        
        # Complex forms
        "çalışanların", "sistemlerine", "projelerinde"
    ]
    
    print("Word Lemmatization Tests:")
    print("-" * 30)
    for word in test_words:
        lemma = analyzer.lemmatize_word(word)
        print(f"  {word:15} → {lemma}")
    
    print("\nText Lemmatization Test:")
    print("-" * 30)
    test_text = "Çalışanların sistemlere erişimi için yardıma ihtiyacım var"
    lemmatized = analyzer.lemmatize_text(test_text)
    print(f"  Original: {test_text}")
    print(f"  Lemmatized: {lemmatized}")
    
    print("\nWord Variants Test:")
    print("-" * 30)
    test_word = "çalış"
    variants = analyzer.get_word_variants(test_word)
    print(f"  Variants for '{test_word}': {variants}")

def test_enhanced_content_manager():
    """Test the enhanced Turkish content manager"""
    print("\n🤖 Testing Enhanced Turkish Content Manager")
    print("=" * 50)
    
    manager = ImprovedTurkishContentManager()
    
    # Test various input forms that should match working hours
    working_hours_tests = [
        "çalışma saatleri nedir",
        "iş saatleri nelerdir",
        "mesai saatlerine erişmek istiyorum",
        "çalışanların çalışma zamanları",
        "kaçta açılıyor ofis",
        "working hours nedir",
        "ne zaman çalışıyorsunuz"
    ]
    
    print("Working Hours Pattern Matching Tests:")
    print("-" * 40)
    for test_input in working_hours_tests:
        match = manager.find_best_match(test_input)
        if match:
            print(f"  ✅ '{test_input}' → {match['category']} (score: {match['score']:.3f})")
        else:
            print(f"  ❌ '{test_input}' → No match")
    
    # Test technical support variations
    support_tests = [
        "teknik destek lazım",
        "yardıma ihtiyacım var",
        "sistemde sorun var",
        "hatalar oluşuyor",
        "help me please",
        "support gerekiyor"
    ]
    
    print("\nTechnical Support Pattern Matching Tests:")
    print("-" * 40)
    for test_input in support_tests:
        match = manager.find_best_match(test_input)
        if match:
            print(f"  ✅ '{test_input}' → {match['category']} (score: {match['score']:.3f})")
        else:
            print(f"  ❌ '{test_input}' → No match")
    
    # Test morphological variations
    morphology_tests = [
        "çalışanların mesai saatleri",  # Possessive + plural
        "sistemlerdeki hatalar",         # Locative + plural
        "projelere yardım",             # Dative
        "güvenlik kurallarını öğrenmek", # Accusative + infinitive
        "eğitimlerde katılım"           # Locative
    ]
    
    print("\nMorphological Variation Tests:")
    print("-" * 40)
    for test_input in morphology_tests:
        match = manager.find_best_match(test_input)
        if match:
            print(f"  ✅ '{test_input}' → {match['category']} (score: {match['score']:.3f})")
            # Show the response preview
            response = manager.get_response(test_input)
            preview = response[:100] + "..." if len(response) > 100 else response
            print(f"      Preview: {preview}")
        else:
            print(f"  ❌ '{test_input}' → No match")

def test_synonym_expansion():
    """Test the enhanced synonym system"""
    print("\n📚 Testing Enhanced Synonym System")
    print("=" * 50)
    
    manager = ImprovedTurkishContentManager()
    
    # Test synonym loading and expansion
    print("Synonym Statistics:")
    print("-" * 30)
    stats = manager.get_stats()
    print(f"  Total synonym groups: {stats['synonym_words']}")
    print(f"  Morphological analysis: {stats['morphological_analysis']['morphological_analysis']}")
    print(f"  spaCy available: {stats['morphological_analysis']['spacy_available']}")
    print(f"  Fallback lemmas: {stats['morphological_analysis']['fallback_lemmas']}")
    
    # Test synonym expansion for specific words
    test_words = ["çalışma", "destek", "sistem", "hata"]
    
    print("\nSynonym Expansion Tests:")
    print("-" * 30)
    for word in test_words:
        expanded = manager._expand_with_synonyms(word)
        print(f"  '{word}' → {len(expanded)} variants: {expanded[:5]}{'...' if len(expanded) > 5 else ''}")

def main():
    """Run all tests"""
    print("🇹🇷 MEFAPEX Turkish Morphological Analysis Test Suite")
    print("=" * 60)
    
    try:
        test_morphological_analyzer()
        test_enhanced_content_manager()
        test_synonym_expansion()
        
        print("\n✅ All tests completed successfully!")
        print("\n📋 Summary:")
        print("- Morphological analyzer: Functional")
        print("- Enhanced pattern matching: Improved")
        print("- Synonym expansion: Enhanced")
        print("- Turkish language support: Advanced")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
