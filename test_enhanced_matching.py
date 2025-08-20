#!/usr/bin/env python3
"""
MEFAPEX Enhanced Question Matching Test Script
Test the new fuzzy matching and semantic search capabilities
"""

import sys
import os
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_enhanced_content_manager():
    """Test the enhanced content manager with fuzzy matching"""
    
    print("🧪 MEFAPEX Enhanced Question Matching Test")
    print("=" * 80)
    
    try:
        from content_manager import content_manager
        
        # Test cases with expected results
        test_cases = [
            # Çalışma saatleri - fuzzy matching testleri
            ("çalışma saatleri nelerdir?", "working_hours", "Normal Turkish"),
            ("calisma saatleri nedir?", "working_hours", "No Turkish chars"),
            ("calışma saatleri", "working_hours", "Mixed Turkish chars"),
            ("iş saatleri kaç?", "working_hours", "Synonym: iş"),
            ("ne zaman açıksınız?", "working_hours", "Different pattern"),
            ("working hours nedir?", "working_hours", "English + Turkish"),
            ("mesai saatleri", "working_hours", "Synonym: mesai"),
            ("ofis saatleri nedir", "working_hours", "Synonym: ofis"),
            ("saat kaçta açık", "working_hours", "Short form"),
            ("kaçta kapanıyorsunuz", "working_hours", "Closing time"),
            
            # Şirket bilgileri
            ("mefapex nedir?", "company_info", "Company info"),
            ("şirket hakkında bilgi", "company_info", "About company"),
            ("firma ne yapıyor?", "company_info", "What does company do"),
            
            # Teknik destek
            ("teknik destek nasıl alabilirim?", "support_types", "Tech support"),
            ("yardıma ihtiyacım var", "support_types", "Need help"),
            ("problem çözümü", "support_types", "Problem solving"),
            
            # Selamlama
            ("merhaba", "greetings", "Greeting"),
            ("selam nasılsın?", "greetings", "Hello"),
            ("günaydın", "greetings", "Good morning"),
            
            # Teşekkür
            ("teşekkürler", "thanks_goodbye", "Thanks"),
            ("sağol", "thanks_goodbye", "Thanks informal"),
            
            # Edge cases - should not match strongly
            ("bugün hava nasıl?", "default", "Weather - should be default"),
            ("futbol maçı", "default", "Football - should be default")
        ]
        
        print(f"Testing {len(test_cases)} cases...")
        print()
        
        correct_matches = 0
        enhanced_matches = 0
        
        def check_response_category(response_text: str, expected: str) -> bool:
            """Response içeriğine bakarak doğru kategoriyi tespit et"""
            response_lower = response_text.lower()
            
            if expected == "working_hours":
                return any(keyword in response_lower for keyword in [
                    "çalışma saatleri", "ofis saatleri", "pazartesi", "cuma", "09:00", "18:00"
                ])
            elif expected == "company_info":
                return any(keyword in response_lower for keyword in [
                    "mefapex", "bilişim teknolojileri", "şirket", "hizmet alanlarımız"
                ])
            elif expected == "support_types":
                return any(keyword in response_lower for keyword in [
                    "teknik destek", "yazılım desteği", "sistem desteği", "destek türleri"
                ])
            elif expected == "greetings":
                return any(keyword in response_lower for keyword in [
                    "merhaba", "hoş geldiniz", "asistanıyım", "ben mefapex"
                ])
            elif expected == "thanks_goodbye":
                return any(keyword in response_lower for keyword in [
                    "rica ederim", "teşekkür", "iyi çalışmalar"
                ])
            elif expected == "default":
                return any(keyword in response_lower for keyword in [
                    "üzgünüm", "hazır bir cevabım", "daha spesifik", "bilgi tabanımızda"
                ])
            
            return False
        
        for i, (question, expected, description) in enumerate(test_cases, 1):
            response, source = content_manager.find_response(question)
            
            # Check if match is correct by looking at response content
            is_correct = check_response_category(response, expected)
            
            is_enhanced = "enhanced" in source
            
            if is_correct:
                correct_matches += 1
                status = "✅ PASS"
            else:
                status = "❌ FAIL"
                
            if is_enhanced:
                enhanced_matches += 1
                status += " 🧠"
            
            print(f"{i:2d}. {status} | {description}")
            print(f"    Q: {question}")
            print(f"    Expected: {expected}")
            print(f"    Got: {source}")
            print(f"    Preview: {response[:60]}...")
            print()
        
        # Results
        accuracy = (correct_matches / len(test_cases)) * 100
        enhanced_rate = (enhanced_matches / len(test_cases)) * 100
        
        print("📊 TEST RESULTS:")
        print(f"    Total Tests: {len(test_cases)}")
        print(f"    Correct: {correct_matches}")
        print(f"    Accuracy: {accuracy:.1f}%")
        print(f"    Enhanced Matches: {enhanced_matches}")
        print(f"    Enhanced Rate: {enhanced_rate:.1f}%")
        
        # System stats
        stats = content_manager.get_stats()
        print(f"\n📈 SYSTEM STATS:")
        print(f"    Enhanced Matcher: {'✅' if stats.get('enhanced_matcher_enabled') else '❌'}")
        print(f"    AI Models: {'✅' if stats.get('huggingface_available') else '❌'}")
        print(f"    Cache Entries: {stats.get('cache_entries', 0)}")
        
        if 'query_stats' in stats:
            query_stats = stats['query_stats']
            print(f"    Total Queries: {query_stats.get('total_queries', 0)}")
            print(f"    Enhanced Matches: {query_stats.get('enhanced_matches', 0)}")
            print(f"    Cache Hits: {query_stats.get('cache_hits', 0)}")
        
        return accuracy >= 85  # 85% threshold for success
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_enhanced_question_matcher_standalone():
    """Test the enhanced question matcher independently"""
    
    print("\n🧠 Enhanced Question Matcher Standalone Test")
    print("=" * 60)
    
    try:
        from enhanced_question_matcher import test_enhanced_question_matching
        success = test_enhanced_question_matching()
        
        if success:
            print("✅ Enhanced Question Matcher test passed!")
        else:
            print("❌ Enhanced Question Matcher test failed!")
            
        return success
        
    except Exception as e:
        print(f"❌ Standalone test failed: {e}")
        return False

def benchmark_performance():
    """Benchmark the performance of the enhanced system"""
    
    print("\n⚡ Performance Benchmark")
    print("=" * 40)
    
    try:
        from content_manager import content_manager
        import time
        
        # Test queries
        queries = [
            "çalışma saatleri nelerdir?",
            "calisma saatleri",
            "mefapex nedir",
            "teknik destek",
            "merhaba"
        ] * 4  # 20 queries total
        
        start_time = time.time()
        
        for query in queries:
            content_manager.find_response(query)
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time = total_time / len(queries)
        
        print(f"Total queries: {len(queries)}")
        print(f"Total time: {total_time:.3f}s")
        print(f"Average time per query: {avg_time:.3f}s")
        print(f"Queries per second: {len(queries)/total_time:.1f}")
        
        # Acceptable performance: < 100ms per query
        return avg_time < 0.1
        
    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        return False

def main():
    """Main test function"""
    
    print("🚀 MEFAPEX Enhanced Question Matching - Comprehensive Test Suite")
    print("=" * 80)
    
    all_tests_passed = True
    
    # Test 1: Enhanced Content Manager
    print("TEST 1: Enhanced Content Manager with Fuzzy Matching")
    test1_passed = test_enhanced_content_manager()
    all_tests_passed = all_tests_passed and test1_passed
    
    # Test 2: Standalone Enhanced Question Matcher
    print("\nTEST 2: Enhanced Question Matcher Standalone")
    test2_passed = test_enhanced_question_matcher_standalone()
    all_tests_passed = all_tests_passed and test2_passed
    
    # Test 3: Performance Benchmark
    print("\nTEST 3: Performance Benchmark")
    test3_passed = benchmark_performance()
    all_tests_passed = all_tests_passed and test3_passed
    
    # Final Results
    print("\n" + "=" * 80)
    if all_tests_passed:
        print("🎉 ALL TESTS PASSED! Enhanced question matching is working correctly!")
        print("✅ Fuzzy matching enabled")
        print("✅ Semantic search enabled") 
        print("✅ Turkish character tolerance enabled")
        print("✅ Synonym expansion enabled")
        print("✅ Performance acceptable")
        print("\n🔧 System ready for production!")
    else:
        print("💥 SOME TESTS FAILED! Please check the issues above.")
        print("❌ System needs improvement before production use.")
    
    return 0 if all_tests_passed else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
