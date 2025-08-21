"""
🔍 MEFAPEX Cache Monitor & Test Suite
Advanced cache testing and monitoring utilities
"""
import asyncio
import time
import random
import logging
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class CacheTestResult:
    """Result of cache performance test"""
    test_name: str
    operations: int
    duration_seconds: float
    ops_per_second: float
    hit_rate: float
    memory_usage_mb: float
    success: bool
    error: Optional[str] = None

class CacheMonitor:
    """
    Cache monitoring and testing utilities
    """
    
    def __init__(self, cache_manager):
        self.cache_manager = cache_manager
        self.test_data = self._generate_test_data()
    
    def _generate_test_data(self) -> List[Dict[str, str]]:
        """Generate test data for cache operations"""
        test_messages = [
            "Mefapex hakkında bilgi verir misiniz?",
            "Şirketinizin iletişim bilgileri neler?",
            "Hangi sektorlerde hizmet veriyorsunuz?",
            "Müşteri hizmetleri nasıl ulaşabilirim?",
            "Ürün kataloğunuzu görebilir miyim?",
            "Fiyat listesi var mı?",
            "Toplu satış yapıyor musunuz?",
            "Kargo ücreti ne kadar?",
            "İade politikanız nedir?",
            "Garanti süresi ne kadar?",
            "Teknik destek var mı?",
            "Çalışma saatleriniz neler?",
            "Online sipariş verebilir miyim?",
            "Kredi kartı kabul ediyor musunuz?",
            "Taksit imkanı var mı?",
            "Showroom adresiniz nerede?",
            "Yeni ürünler ne zaman çıkıyor?",
            "Kampanyalarınız var mı?",
            "İndirim kodları nasıl kullanırım?",
            "Üyelik avantajları neler?"
        ]
        
        test_responses = [
            "Mefapex hakkında detaylı bilgi için web sitemizi ziyaret edebilirsiniz.",
            "İletişim bilgilerimiz: info@mefapex.com, +90 212 123 4567",
            "Otomotiv, elektronik ve endüstriyel sektörlerde hizmet veriyoruz.",
            "Müşteri hizmetleri: 444 6332, 7/24 hizmetinizdeyiz.",
            "Ürün kataloğumuz web sitemizde mevcuttur.",
            "Güncel fiyat listesi için bizimle iletişime geçin.",
            "Evet, toplu satış yapıyoruz. Özel fiyatlarımız var.",
            "Kargo ücreti sipariş tutarına göre belirlenir.",
            "30 gün içinde iade edebilirsiniz.",
            "Ürünlerimiz 2 yıl garantilidir.",
            "7/24 teknik destek hizmetimiz var.",
            "Hafta içi 09:00-18:00, Cumartesi 09:00-14:00",
            "Evet, online sipariş verebilirsiniz.",
            "Tüm kredi kartlarını kabul ediyoruz.",
            "2-12 taksit imkanı mevcuttur.",
            "Showroom: İstanbul Ümraniye'de bulunmaktadır.",
            "Yeni ürünler her ayın ilk haftası çıkar.",
            "Sürekli kampanyalarımız var, takip edin.",
            "İndirim kodları sepette uygulanır.",
            "Üyelere özel %10 indirim ve öncelikli destek."
        ]
        
        return [
            {"message": msg, "response": resp, "context": f"test_context_{i}"}
            for i, (msg, resp) in enumerate(zip(test_messages, test_responses))
        ]
    
    async def run_performance_test(self, 
                                 test_name: str,
                                 operations: int = 1000,
                                 cache_type: str = "response") -> CacheTestResult:
        """Run performance test on specified cache"""
        start_time = time.time()
        hit_count = 0
        
        try:
            cache = None
            if cache_type == "response":
                cache = self.cache_manager.get_response_cache()
            elif cache_type == "distributed":
                cache = self.cache_manager.get_distributed_cache()
            
            if not cache:
                return CacheTestResult(
                    test_name=test_name,
                    operations=0,
                    duration_seconds=0,
                    ops_per_second=0,
                    hit_rate=0,
                    memory_usage_mb=0,
                    success=False,
                    error=f"Cache type '{cache_type}' not available"
                )
            
            # Populate cache with test data
            logger.info(f"🔄 Populating {cache_type} cache with test data...")
            for i, data in enumerate(self.test_data[:min(100, len(self.test_data))]):
                if cache_type == "response":
                    cache.set(data["message"], data["response"], data["context"], "test")
                elif cache_type == "distributed":
                    await cache.set(data["message"], data["response"], data["context"], "test")
            
            # Run test operations
            logger.info(f"🚀 Running {operations} operations on {cache_type} cache...")
            
            for i in range(operations):
                # Mix of gets and sets (80% gets, 20% sets)
                if random.random() < 0.8:
                    # Get operation
                    test_data = random.choice(self.test_data)
                    if cache_type == "response":
                        result = cache.get(test_data["message"], test_data["context"])
                    elif cache_type == "distributed":
                        result = await cache.get(test_data["message"], test_data["context"])
                    
                    if result:
                        hit_count += 1
                else:
                    # Set operation
                    test_data = random.choice(self.test_data)
                    new_response = f"{test_data['response']} [Updated at {time.time()}]"
                    
                    if cache_type == "response":
                        cache.set(test_data["message"], new_response, test_data["context"], "test")
                    elif cache_type == "distributed":
                        await cache.set(test_data["message"], new_response, test_data["context"], "test")
            
            # Calculate metrics
            end_time = time.time()
            duration = end_time - start_time
            ops_per_second = operations / duration if duration > 0 else 0
            hit_rate = (hit_count / (operations * 0.8)) * 100 if operations > 0 else 0
            
            # Get memory usage
            memory_usage = 0
            if cache_type == "response" and hasattr(cache, 'get_stats'):
                stats = cache.get_stats()
                memory_usage = stats.get('memory_usage_mb', 0)
            elif cache_type == "distributed" and hasattr(cache, 'get_stats'):
                stats = await cache.get_stats()
                if 'local' in stats:
                    memory_usage = stats['local'].get('memory_usage_mb', 0)
            
            return CacheTestResult(
                test_name=test_name,
                operations=operations,
                duration_seconds=duration,
                ops_per_second=ops_per_second,
                hit_rate=hit_rate,
                memory_usage_mb=memory_usage,
                success=True
            )
        
        except Exception as e:
            logger.error(f"❌ Performance test failed: {e}")
            return CacheTestResult(
                test_name=test_name,
                operations=0,
                duration_seconds=0,
                ops_per_second=0,
                hit_rate=0,
                memory_usage_mb=0,
                success=False,
                error=str(e)
            )
    
    async def run_memory_stress_test(self, 
                                   cache_type: str = "response",
                                   target_memory_mb: int = 50) -> CacheTestResult:
        """Run memory stress test to verify size limits"""
        start_time = time.time()
        
        try:
            cache = None
            if cache_type == "response":
                cache = self.cache_manager.get_response_cache()
            elif cache_type == "distributed":
                cache = self.cache_manager.get_distributed_cache()
            
            if not cache:
                return CacheTestResult(
                    test_name=f"Memory Stress Test ({cache_type})",
                    operations=0,
                    duration_seconds=0,
                    ops_per_second=0,
                    hit_rate=0,
                    memory_usage_mb=0,
                    success=False,
                    error=f"Cache type '{cache_type}' not available"
                )
            
            operations = 0
            logger.info(f"🧠 Running memory stress test on {cache_type} cache (target: {target_memory_mb}MB)...")
            
            while True:
                # Generate large response data
                large_response = "A" * 10240  # 10KB response
                test_key = f"stress_test_key_{operations}_{time.time()}"
                
                if cache_type == "response":
                    cache.set(test_key, large_response, f"stress_context_{operations}", "stress_test")
                    
                    # Check memory usage
                    stats = cache.get_stats()
                    current_memory = stats.get('memory_usage_mb', 0)
                elif cache_type == "distributed":
                    await cache.set(test_key, large_response, f"stress_context_{operations}", "stress_test")
                    
                    # Check memory usage
                    stats = await cache.get_stats()
                    current_memory = stats.get('local', {}).get('memory_usage_mb', 0)
                
                operations += 1
                
                # Stop if we've reached target memory or after reasonable number of operations
                if current_memory >= target_memory_mb or operations >= 10000:
                    break
                
                # Add some delay to prevent overwhelming the system
                if operations % 100 == 0:
                    await asyncio.sleep(0.01)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Final memory check
            if cache_type == "response":
                final_stats = cache.get_stats()
                final_memory = final_stats.get('memory_usage_mb', 0)
            elif cache_type == "distributed":
                final_stats = await cache.get_stats()
                final_memory = final_stats.get('local', {}).get('memory_usage_mb', 0)
            
            logger.info(f"✅ Memory stress test completed: {operations} operations, {final_memory:.2f}MB used")
            
            return CacheTestResult(
                test_name=f"Memory Stress Test ({cache_type})",
                operations=operations,
                duration_seconds=duration,
                ops_per_second=operations / duration if duration > 0 else 0,
                hit_rate=0,  # Not applicable for this test
                memory_usage_mb=final_memory,
                success=True
            )
        
        except Exception as e:
            logger.error(f"❌ Memory stress test failed: {e}")
            return CacheTestResult(
                test_name=f"Memory Stress Test ({cache_type})",
                operations=0,
                duration_seconds=0,
                ops_per_second=0,
                hit_rate=0,
                memory_usage_mb=0,
                success=False,
                error=str(e)
            )
    
    async def run_ttl_test(self, cache_type: str = "response", ttl_seconds: int = 5) -> CacheTestResult:
        """Test TTL (Time To Live) functionality"""
        start_time = time.time()
        
        try:
            cache = None
            if cache_type == "response":
                cache = self.cache_manager.get_response_cache()
            elif cache_type == "distributed":
                cache = self.cache_manager.get_distributed_cache()
            
            if not cache:
                return CacheTestResult(
                    test_name=f"TTL Test ({cache_type})",
                    operations=0,
                    duration_seconds=0,
                    ops_per_second=0,
                    hit_rate=0,
                    memory_usage_mb=0,
                    success=False,
                    error=f"Cache type '{cache_type}' not available"
                )
            
            logger.info(f"⏰ Running TTL test on {cache_type} cache (TTL: {ttl_seconds}s)...")
            
            # Store test data
            test_key = f"ttl_test_{time.time()}"
            test_response = "This entry should expire"
            
            if cache_type == "response":
                cache.set(test_key, test_response, "ttl_context", "ttl_test")
                
                # Verify entry exists
                result1 = cache.get(test_key, "ttl_context")
                exists_initially = result1 is not None
                
                # Wait for TTL + buffer
                await asyncio.sleep(ttl_seconds + 1)
                
                # Check if entry has expired
                result2 = cache.get(test_key, "ttl_context")
                expired_correctly = result2 is None
                
            elif cache_type == "distributed":
                await cache.set(test_key, test_response, "ttl_context", "ttl_test")
                
                # Verify entry exists
                result1 = await cache.get(test_key, "ttl_context")
                exists_initially = result1 is not None
                
                # Wait for TTL + buffer
                await asyncio.sleep(ttl_seconds + 1)
                
                # Check if entry has expired
                result2 = await cache.get(test_key, "ttl_context")
                expired_correctly = result2 is None
            
            end_time = time.time()
            duration = end_time - start_time
            
            success = exists_initially and expired_correctly
            
            logger.info(f"✅ TTL test completed: exists_initially={exists_initially}, expired_correctly={expired_correctly}")
            
            return CacheTestResult(
                test_name=f"TTL Test ({cache_type})",
                operations=2,  # One set, one get
                duration_seconds=duration,
                ops_per_second=2 / duration if duration > 0 else 0,
                hit_rate=100 if exists_initially else 0,
                memory_usage_mb=0,  # Not measured in this test
                success=success,
                error=None if success else "TTL test failed: entry did not expire correctly"
            )
        
        except Exception as e:
            logger.error(f"❌ TTL test failed: {e}")
            return CacheTestResult(
                test_name=f"TTL Test ({cache_type})",
                operations=0,
                duration_seconds=0,
                ops_per_second=0,
                hit_rate=0,
                memory_usage_mb=0,
                success=False,
                error=str(e)
            )
    
    async def run_comprehensive_test_suite(self) -> Dict[str, List[CacheTestResult]]:
        """Run comprehensive test suite on all caches"""
        logger.info("🧪 Starting comprehensive cache test suite...")
        
        test_results = {
            "response_cache": [],
            "distributed_cache": []
        }
        
        # Response cache tests
        if self.cache_manager.get_response_cache():
            logger.info("📊 Testing Response Cache...")
            
            # Performance test
            result1 = await self.run_performance_test("Response Cache Performance", 1000, "response")
            test_results["response_cache"].append(result1)
            
            # Memory stress test
            result2 = await self.run_memory_stress_test("response", 20)
            test_results["response_cache"].append(result2)
            
            # TTL test
            result3 = await self.run_ttl_test("response", 3)
            test_results["response_cache"].append(result3)
        
        # Distributed cache tests
        if self.cache_manager.get_distributed_cache():
            logger.info("🌐 Testing Distributed Cache...")
            
            # Performance test
            result4 = await self.run_performance_test("Distributed Cache Performance", 500, "distributed")
            test_results["distributed_cache"].append(result4)
            
            # Memory stress test
            result5 = await self.run_memory_stress_test("distributed", 15)
            test_results["distributed_cache"].append(result5)
            
            # TTL test
            result6 = await self.run_ttl_test("distributed", 3)
            test_results["distributed_cache"].append(result6)
        
        logger.info("✅ Comprehensive test suite completed")
        return test_results
    
    def generate_test_report(self, test_results: Dict[str, List[CacheTestResult]]) -> str:
        """Generate comprehensive test report"""
        report_lines = [
            "🔍 MEFAPEX Cache Test Report",
            "=" * 50,
            f"Generated at: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            ""
        ]
        
        for cache_type, results in test_results.items():
            if not results:
                continue
                
            report_lines.extend([
                f"📊 {cache_type.replace('_', ' ').title()} Results:",
                "-" * 30
            ])
            
            for result in results:
                status = "✅ PASSED" if result.success else "❌ FAILED"
                report_lines.extend([
                    f"Test: {result.test_name}",
                    f"Status: {status}",
                    f"Operations: {result.operations:,}",
                    f"Duration: {result.duration_seconds:.2f}s",
                    f"Ops/sec: {result.ops_per_second:.2f}",
                    f"Hit Rate: {result.hit_rate:.1f}%",
                    f"Memory Usage: {result.memory_usage_mb:.2f}MB"
                ])
                
                if result.error:
                    report_lines.append(f"Error: {result.error}")
                
                report_lines.append("")
        
        return "\n".join(report_lines)

async def run_cache_tests():
    """Main function to run cache tests"""
    from cache_manager import get_cache_manager, initialize_cache_manager
    
    # Initialize cache manager
    await initialize_cache_manager()
    cache_manager = get_cache_manager()
    
    # Create monitor and run tests
    monitor = CacheMonitor(cache_manager)
    test_results = await monitor.run_comprehensive_test_suite()
    
    # Generate and print report
    report = monitor.generate_test_report(test_results)
    print(report)
    
    # Also save to file
    with open("cache_test_report.txt", "w") as f:
        f.write(report)
    
    print("\n📁 Report saved to cache_test_report.txt")

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Run tests
    asyncio.run(run_cache_tests())
