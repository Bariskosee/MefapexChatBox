#!/usr/bin/env python3
"""
🚀 Simple Cache Test for MEFAPEX
===============================
Database bağımlılığı olmadan cache'i test eder.
"""

import time
import logging
import sys
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_cache_functionality():
    """Test basic cache functionality"""
    
    try:
        # Import only cache module
        from response_cache import response_cache
        
        logger.info("🧪 Cache Fonksiyonalite Testi Başlatılıyor...")
        
        # Clear cache
        response_cache.clear()
        logger.info("🗑️ Cache temizlendi")
        
        # Test 1: Basic set/get
        logger.info("📊 Test 1: Temel set/get işlemleri")
        
        test_message = "Merhaba test mesajı"
        test_response = "Bu bir test cevabıdır"
        test_source = "test_source"
        
        # Set cache
        response_cache.set(test_message, test_response, source=test_source)
        logger.info(f"✅ Cache set: {test_message[:20]}...")
        
        # Get cache
        cached_result = response_cache.get(test_message)
        
        # Verify result
        assert cached_result is not None, "Cache should return result"
        assert isinstance(cached_result, tuple), "Cache should return tuple"
        assert len(cached_result) == 2, "Cache should return (response, source) tuple"
        
        cached_response, cached_source = cached_result
        assert cached_response == test_response, f"Response mismatch: {cached_response} != {test_response}"
        assert cached_source == test_source, f"Source mismatch: {cached_source} != {test_source}"
        
        logger.info("✅ Temel set/get test passed")
        
        # Test 2: Cache miss
        logger.info("📊 Test 2: Cache miss testi")
        
        non_existent = response_cache.get("Non-existent message")
        assert non_existent is None, "Non-existent key should return None"
        
        logger.info("✅ Cache miss test passed")
        
        # Test 3: Multiple entries
        logger.info("📊 Test 3: Çoklu girişler testi")
        
        test_data = [
            ("Mesaj 1", "Cevap 1", "source1"),
            ("Mesaj 2", "Cevap 2", "source2"),
            ("Mesaj 3", "Cevap 3", "source3"),
            ("Türkçe mesaj", "Türkçe cevap", "turkish_source"),
        ]
        
        # Set multiple entries
        for message, response, source in test_data:
            response_cache.set(message, response, source=source)
        
        # Verify all entries
        for message, expected_response, expected_source in test_data:
            cached_result = response_cache.get(message)
            assert cached_result is not None, f"Cache miss for: {message}"
            
            cached_response, cached_source = cached_result
            assert cached_response == expected_response, f"Response mismatch for: {message}"
            assert cached_source == expected_source, f"Source mismatch for: {message}"
        
        logger.info("✅ Çoklu girişler test passed")
        
        # Test 4: Performance measurement
        logger.info("📊 Test 4: Performans ölçümü")
        
        # Measure cache hit time
        hit_times = []
        for _ in range(100):
            start_time = time.time()
            result = response_cache.get("Mesaj 1")
            end_time = time.time()
            
            assert result is not None, "Cache should hit"
            hit_times.append((end_time - start_time) * 1000)  # ms
        
        avg_hit_time = sum(hit_times) / len(hit_times)
        logger.info(f"⚡ Ortalama cache hit süresi: {avg_hit_time:.3f}ms")
        
        # Measure cache miss time
        miss_times = []
        for i in range(10):
            start_time = time.time()
            result = response_cache.get(f"Non-existent-{i}")
            end_time = time.time()
            
            assert result is None, "Should be cache miss"
            miss_times.append((end_time - start_time) * 1000)  # ms
        
        avg_miss_time = sum(miss_times) / len(miss_times)
        logger.info(f"❌ Ortalama cache miss süresi: {avg_miss_time:.3f}ms")
        
        # Test 5: Statistics
        logger.info("📊 Test 5: İstatistikler")
        
        stats = response_cache.get_stats()
        logger.info("Cache İstatistikleri:")
        for key, value in stats.items():
            logger.info(f"  {key}: {value}")
        
        # Verify stats make sense
        assert stats['size'] > 0, "Cache should have entries"
        assert stats['hits'] > 0, "Should have cache hits"
        assert stats['misses'] > 0, "Should have cache misses"
        
        # Test 6: Key normalization
        logger.info("📊 Test 6: Anahtar normalizasyon testi")
        
        # These should be treated as the same key due to normalization
        response_cache.set("  Test Message  ", "Normalized Response", source="normalize_test")
        
        variations = [
            "test message",
            "Test Message",
            "TEST MESSAGE",
            "  test message  ",
            "Test Message"
        ]
        
        for variation in variations:
            result = response_cache.get(variation)
            if result is not None:
                cached_response, cached_source = result
                logger.info(f"  '{variation}' -> Found: {cached_source}")
            else:
                logger.info(f"  '{variation}' -> Not found")
        
        logger.info("✅ Anahtar normalizasyon test completed")
        
        # Summary
        logger.info("=" * 50)
        logger.info("🎉 CACHE TEST SONUÇLARI")
        logger.info("=" * 50)
        logger.info(f"📦 Cache Boyutu: {stats['size']}")
        logger.info(f"🎯 Hit Rate: {stats['hit_rate']:.1f}%")
        logger.info(f"⚡ Cache Hit Ortalama: {avg_hit_time:.3f}ms")
        logger.info(f"❌ Cache Miss Ortalama: {avg_miss_time:.3f}ms")
        logger.info(f"💾 Bellek Kullanımı: {stats['memory_usage_mb']:.2f} MB")
        
        if avg_hit_time > 0:
            ratio = avg_miss_time / avg_hit_time
            logger.info(f"📈 Hit/Miss Ratio: {ratio:.1f}x")
        
        logger.info("=" * 50)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_corrected_api_usage():
    """Test the corrected API cache usage pattern"""
    
    logger.info("🔧 Düzeltilmiş API Kullanım Testi...")
    
    try:
        from response_cache import response_cache
        
        # Simulate old (wrong) usage
        logger.info("❌ Eski (yanlış) kullanım simülasyonu:")
        
        message = "Test mesajı"
        
        # Old way (double hashing - WRONG)
        old_cache_key = f"chat_{hash(message)}"
        logger.info(f"  Eski anahtar: {old_cache_key}")
        
        # Store with old way
        response_cache.set(old_cache_key, "Eski yanıt", source="old_way")
        
        # Try to retrieve with new way (should miss)
        new_result = response_cache.get(message)
        logger.info(f"  Yeni yöntemle getirme: {new_result}")
        
        # Try to retrieve with old way (should hit)
        old_result = response_cache.get(old_cache_key)
        logger.info(f"  Eski yöntemle getirme: {old_result}")
        
        # New way (correct)
        logger.info("✅ Yeni (doğru) kullanım:")
        
        # Store with new way
        response_cache.set(message, "Yeni yanıt", source="new_way")
        
        # Retrieve with new way (should hit)
        new_result2 = response_cache.get(message)
        if new_result2:
            response, source = new_result2
            logger.info(f"  Doğru getirme: response='{response}', source='{source}'")
        else:
            logger.error("  Yeni yöntem başarısız!")
            return False
        
        # Verify tuple unpacking works
        assert isinstance(new_result2, tuple), "Result should be tuple"
        assert len(new_result2) == 2, "Tuple should have 2 elements"
        
        response, source = new_result2
        assert response == "Yeni yanıt", "Response should match"
        assert source == "new_way", "Source should match"
        
        logger.info("✅ Düzeltilmiş API kullanım testi passed")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ API usage test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    logger.info("🧪 MEFAPEX Cache Test Suite (Standalone)")
    logger.info("=" * 60)
    
    tests_passed = 0
    total_tests = 2
    
    # Test 1: Basic functionality
    if test_cache_functionality():
        tests_passed += 1
        logger.info("✅ Cache Functionality Test: PASSED")
    else:
        logger.error("❌ Cache Functionality Test: FAILED")
    
    # Test 2: Corrected API usage
    if test_corrected_api_usage():
        tests_passed += 1
        logger.info("✅ Corrected API Usage Test: PASSED")
    else:
        logger.error("❌ Corrected API Usage Test: FAILED")
    
    # Summary
    logger.info("=" * 60)
    logger.info(f"🏁 TEST SONUÇLARI: {tests_passed}/{total_tests} test passed")
    
    if tests_passed == total_tests:
        logger.info("🎉 TÜM TESTLER BAŞARILI!")
        logger.info("💡 Cache düzeltmeleri çalışıyor!")
        return True
    else:
        logger.error("💥 BAZI TESTLER BAŞARISIZ!")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("⏹️ Test kullanıcı tarafından iptal edildi")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Beklenmeyen hata: {e}")
        sys.exit(1)
