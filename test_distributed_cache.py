"""
🧪 Distributed Cache Performance Tests
Test suite for evaluating distributed cache performance vs local cache
"""
import asyncio
import time
import random
import string
import logging
from typing import List, Dict
import statistics

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_random_text(length: int = 100) -> str:
    """Generate random text for testing"""
    return ''.join(random.choices(string.ascii_letters + string.digits + ' ', k=length))

async def test_cache_performance():
    """Test performance comparison between local and distributed cache"""
    
    # Import cache implementations
    try:
        from response_cache import SimpleResponseCache
        from distributed_cache import HybridDistributedCache, RedisDistributedCache
        
        # Test data
        test_messages = [generate_random_text() for _ in range(100)]
        test_responses = [generate_random_text(200) for _ in range(100)]
        
        # Initialize caches
        local_cache = SimpleResponseCache(max_size=200, ttl=3600)
        
        # Try to initialize distributed cache
        distributed_cache = None
        try:
            distributed_cache = HybridDistributedCache(
                redis_url="redis://localhost:6379",
                local_max_size=100,
                local_ttl=1800,
                redis_ttl=3600
            )
            await distributed_cache.initialize()
            logger.info("✅ Distributed cache initialized")
        except Exception as e:
            logger.warning(f"⚠️ Distributed cache unavailable: {e}")
        
        # Test scenarios
        results = {}
        
        # Test 1: Write Performance
        logger.info("🔄 Testing write performance...")
        
        # Local cache writes
        start_time = time.time()
        for i, (msg, resp) in enumerate(zip(test_messages, test_responses)):
            local_cache.set(msg, resp, source="test")
        local_write_time = (time.time() - start_time) * 1000
        
        # Distributed cache writes
        distributed_write_time = 0
        if distributed_cache:
            start_time = time.time()
            for i, (msg, resp) in enumerate(zip(test_messages, test_responses)):
                await distributed_cache.set(msg, resp, source="test")
            distributed_write_time = (time.time() - start_time) * 1000
        
        results['write'] = {
            'local_ms': round(local_write_time, 2),
            'distributed_ms': round(distributed_write_time, 2) if distributed_cache else "N/A"
        }
        
        # Test 2: Read Performance
        logger.info("🔄 Testing read performance...")
        
        # Local cache reads
        start_time = time.time()
        local_hits = 0
        for msg in test_messages:
            result = local_cache.get(msg)
            if result:
                local_hits += 1
        local_read_time = (time.time() - start_time) * 1000
        
        # Distributed cache reads
        distributed_read_time = 0
        distributed_hits = 0
        if distributed_cache:
            start_time = time.time()
            for msg in test_messages:
                result = await distributed_cache.get(msg)
                if result:
                    distributed_hits += 1
            distributed_read_time = (time.time() - start_time) * 1000
        
        results['read'] = {
            'local_ms': round(local_read_time, 2),
            'local_hits': local_hits,
            'distributed_ms': round(distributed_read_time, 2) if distributed_cache else "N/A",
            'distributed_hits': distributed_hits if distributed_cache else "N/A"
        }
        
        # Test 3: Mixed Operations
        logger.info("🔄 Testing mixed operations...")
        
        mixed_operations = []
        for _ in range(50):
            if random.choice([True, False]):
                # Read operation
                msg = random.choice(test_messages)
                mixed_operations.append(('read', msg, None))
            else:
                # Write operation
                msg = generate_random_text()
                resp = generate_random_text(200)
                mixed_operations.append(('write', msg, resp))
        
        # Local mixed operations
        start_time = time.time()
        for op_type, msg, resp in mixed_operations:
            if op_type == 'read':
                local_cache.get(msg)
            else:
                local_cache.set(msg, resp, source="mixed_test")
        local_mixed_time = (time.time() - start_time) * 1000
        
        # Distributed mixed operations
        distributed_mixed_time = 0
        if distributed_cache:
            start_time = time.time()
            for op_type, msg, resp in mixed_operations:
                if op_type == 'read':
                    await distributed_cache.get(msg)
                else:
                    await distributed_cache.set(msg, resp, source="mixed_test")
            distributed_mixed_time = (time.time() - start_time) * 1000
        
        results['mixed'] = {
            'local_ms': round(local_mixed_time, 2),
            'distributed_ms': round(distributed_mixed_time, 2) if distributed_cache else "N/A"
        }
        
        # Test 4: Cache Statistics
        logger.info("📊 Gathering cache statistics...")
        
        local_stats = local_cache.get_stats()
        distributed_stats = None
        if distributed_cache:
            distributed_stats = await distributed_cache.get_stats()
        
        results['stats'] = {
            'local': local_stats,
            'distributed': distributed_stats if distributed_cache else "N/A"
        }
        
        # Print Results
        print("\n" + "="*60)
        print("🧪 DISTRIBUTED CACHE PERFORMANCE TEST RESULTS")
        print("="*60)
        
        print(f"\n📝 WRITE PERFORMANCE:")
        print(f"   Local Cache:       {results['write']['local_ms']} ms")
        print(f"   Distributed Cache: {results['write']['distributed_ms']} ms")
        
        if results['write']['distributed_ms'] != "N/A":
            speedup = results['write']['local_ms'] / results['write']['distributed_ms']
            print(f"   Speed Ratio:       {speedup:.2f}x {'(Local faster)' if speedup > 1 else '(Distributed faster)'}")
        
        print(f"\n📖 READ PERFORMANCE:")
        print(f"   Local Cache:       {results['read']['local_ms']} ms ({results['read']['local_hits']} hits)")
        print(f"   Distributed Cache: {results['read']['distributed_ms']} ms ({results['read']['distributed_hits']} hits)")
        
        if results['read']['distributed_ms'] != "N/A":
            speedup = results['read']['local_ms'] / results['read']['distributed_ms']
            print(f"   Speed Ratio:       {speedup:.2f}x {'(Local faster)' if speedup > 1 else '(Distributed faster)'}")
        
        print(f"\n🔄 MIXED OPERATIONS:")
        print(f"   Local Cache:       {results['mixed']['local_ms']} ms")
        print(f"   Distributed Cache: {results['mixed']['distributed_ms']} ms")
        
        if results['mixed']['distributed_ms'] != "N/A":
            speedup = results['mixed']['local_ms'] / results['mixed']['distributed_ms']
            print(f"   Speed Ratio:       {speedup:.2f}x {'(Local faster)' if speedup > 1 else '(Distributed faster)'}")
        
        print(f"\n📊 CACHE STATISTICS:")
        print(f"   Local Cache:")
        print(f"     Size: {local_stats['size']}/{local_stats['max_size']}")
        print(f"     Hit Rate: {local_stats['hit_rate']}%")
        print(f"     Memory: {local_stats['memory_usage_mb']} MB")
        
        if distributed_stats != "N/A":
            print(f"   Distributed Cache:")
            print(f"     Type: {distributed_stats['type']}")
            print(f"     Local Size: {distributed_stats['local']['size']}/{distributed_stats['local']['max_size']}")
            print(f"     Local Hit Rate: {distributed_stats['local']['hit_rate']}%")
            print(f"     Redis Available: {distributed_stats['redis_available']}")
            if 'redis' in distributed_stats:
                print(f"     Redis Memory: {distributed_stats['redis'].get('memory_used_mb', 'N/A')} MB")
        
        # Cleanup
        if distributed_cache:
            await distributed_cache.shutdown()
        
        return results
        
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        print("Please ensure all required modules are installed:")
        print("pip install redis>=5.0.0")
        return None
    except Exception as e:
        logger.error(f"❌ Test error: {e}")
        return None

async def test_cache_scalability():
    """Test cache behavior under different load scenarios"""
    
    try:
        from distributed_cache import HybridDistributedCache
        
        print("\n" + "="*60)
        print("📈 CACHE SCALABILITY TEST")
        print("="*60)
        
        # Test different cache sizes and loads
        test_cases = [
            {"cache_size": 100, "operations": 200, "name": "Small Cache, High Load"},
            {"cache_size": 500, "operations": 1000, "name": "Medium Cache, Medium Load"},
            {"cache_size": 1000, "operations": 500, "name": "Large Cache, Low Load"}
        ]
        
        for test_case in test_cases:
            print(f"\n🔄 Testing: {test_case['name']}")
            
            # Initialize cache
            cache = HybridDistributedCache(
                redis_url="redis://localhost:6379",
                local_max_size=test_case['cache_size'],
                local_ttl=1800,
                redis_ttl=3600
            )
            
            try:
                await cache.initialize()
                
                # Generate test data
                operations = []
                for i in range(test_case['operations']):
                    if i < test_case['cache_size']:
                        # Fill cache first
                        operations.append(('set', f"key_{i}", f"value_{i}"))
                    else:
                        # Mix of operations
                        if random.choice([True, False]):
                            # Read existing
                            key_id = random.randint(0, min(i-1, test_case['cache_size']-1))
                            operations.append(('get', f"key_{key_id}", None))
                        else:
                            # Write new
                            operations.append(('set', f"key_{i}", f"value_{i}"))
                
                # Execute operations
                start_time = time.time()
                hit_count = 0
                miss_count = 0
                
                for op_type, key, value in operations:
                    if op_type == 'get':
                        result = await cache.get(key)
                        if result:
                            hit_count += 1
                        else:
                            miss_count += 1
                    else:
                        await cache.set(key, value, source="scalability_test")
                
                total_time = (time.time() - start_time) * 1000
                
                # Get final stats
                stats = await cache.get_stats()
                
                print(f"   Operations: {test_case['operations']} in {total_time:.2f} ms")
                print(f"   Avg Time: {total_time/test_case['operations']:.2f} ms/op")
                print(f"   Cache Hits: {hit_count}")
                print(f"   Cache Misses: {miss_count}")
                print(f"   Hit Rate: {(hit_count/(hit_count+miss_count)*100):.1f}%" if (hit_count+miss_count) > 0 else "N/A")
                print(f"   Local Cache Size: {stats['local']['size']}/{stats['local']['max_size']}")
                
                await cache.shutdown()
                
            except Exception as e:
                print(f"   ❌ Test failed: {e}")
        
    except ImportError as e:
        print(f"❌ Scalability test unavailable: {e}")

async def main():
    """Run all cache tests"""
    print("🚀 Starting MEFAPEX Distributed Cache Tests...")
    
    # Performance test
    await test_cache_performance()
    
    # Scalability test
    await test_cache_scalability()
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    asyncio.run(main())
