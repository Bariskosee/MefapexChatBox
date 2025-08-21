#!/usr/bin/env python3
"""
🎯 MEFAPEX Rate Limiter Demo
Quick demonstration of the Redis-based distributed rate limiter
"""

import asyncio
import time
import os
from core.configuration import get_config, RateLimitConfig
from core.rate_limiter import DistributedRateLimiter, get_rate_limiter

def print_banner():
    print("🚦 MEFAPEX Distributed Rate Limiter Demo")
    print("=" * 50)

async def demo_basic_functionality():
    """Demo basic rate limiting functionality"""
    print("\n📋 Demo 1: Basic Rate Limiting")
    print("-" * 30)
    
    # Create a demo config with low limits for quick testing
    config = RateLimitConfig()
    config.requests_per_minute = 3  # Low limit for demo
    config.chat_requests_per_minute = 2
    config.window_size_seconds = 10  # Short window for demo
    config.use_redis = False  # Use memory for demo simplicity
    
    rate_limiter = DistributedRateLimiter(config)
    
    try:
        test_ip = "demo.user.ip"
        
        print(f"🔧 Testing with IP: {test_ip}")
        print(f"📊 Limit: {config.requests_per_minute} requests per {config.window_size_seconds} seconds")
        print()
        
        # Test requests
        for i in range(5):
            allowed = await rate_limiter.is_allowed(test_ip, "general")
            count = await rate_limiter.get_current_count(test_ip, "general")
            
            status = "✅ ALLOWED" if allowed else "❌ BLOCKED"
            print(f"Request {i+1}: {status} (Current count: {count})")
            
            await asyncio.sleep(0.5)  # Small delay between requests
        
        print(f"\n⏰ Waiting for window reset ({config.window_size_seconds} seconds)...")
        await asyncio.sleep(config.window_size_seconds + 1)
        
        # Test after reset
        allowed = await rate_limiter.is_allowed(test_ip, "general")
        count = await rate_limiter.get_current_count(test_ip, "general")
        status = "✅ ALLOWED" if allowed else "❌ BLOCKED"
        print(f"After reset: {status} (Current count: {count})")
        
    finally:
        await rate_limiter.close()

async def demo_different_endpoints():
    """Demo different limits for different endpoint types"""
    print("\n📋 Demo 2: Different Endpoint Types")
    print("-" * 30)
    
    config = RateLimitConfig()
    config.requests_per_minute = 5  # General limit
    config.chat_requests_per_minute = 2  # Lower chat limit
    config.window_size_seconds = 8
    config.use_redis = False
    
    rate_limiter = DistributedRateLimiter(config)
    
    try:
        test_ip = "demo.endpoint.test"
        
        print(f"🔧 Testing different endpoint types")
        print(f"📊 General limit: {config.requests_per_minute}")
        print(f"💬 Chat limit: {config.chat_requests_per_minute}")
        print()
        
        # Test general endpoints
        print("General endpoints:")
        for i in range(3):
            allowed = await rate_limiter.is_allowed(test_ip, "general")
            status = "✅ ALLOWED" if allowed else "❌ BLOCKED"
            print(f"  Request {i+1}: {status}")
        
        print("\nChat endpoints:")
        for i in range(3):
            allowed = await rate_limiter.is_allowed(test_ip, "chat")
            status = "✅ ALLOWED" if allowed else "❌ BLOCKED"
            print(f"  Request {i+1}: {status}")
        
    finally:
        await rate_limiter.close()

async def demo_statistics():
    """Demo rate limiter statistics and monitoring"""
    print("\n📋 Demo 3: Statistics and Monitoring")
    print("-" * 30)
    
    rate_limiter = await get_rate_limiter()
    
    try:
        # Get and display stats
        stats = await rate_limiter.get_stats()
        
        print("📊 Rate Limiter Statistics:")
        print(f"  Enabled: {stats['enabled']}")
        print(f"  Backend: {stats['backend']}")
        print(f"  Redis Available: {stats['redis_available']}")
        print(f"  Fallback Enabled: {stats['fallback_enabled']}")
        print()
        
        print("📈 Limits:")
        limits = stats['limits']
        print(f"  General: {limits['general_requests_per_minute']}/min")
        print(f"  Chat: {limits['chat_requests_per_minute']}/min")
        print()
        
        print("⚙️ Configuration:")
        config = stats['config']
        print(f"  Window Size: {config['window_size_seconds']} seconds")
        print(f"  Cleanup Interval: {config['cleanup_interval_seconds']} seconds")
        
    finally:
        await rate_limiter.close()

async def demo_redis_vs_memory():
    """Demo Redis vs Memory backend performance"""
    print("\n📋 Demo 4: Backend Performance Comparison")
    print("-" * 30)
    
    # Test Redis backend
    redis_config = RateLimitConfig()
    redis_config.use_redis = True
    redis_config.requests_per_minute = 100
    
    # Test Memory backend
    memory_config = RateLimitConfig()
    memory_config.use_redis = False
    memory_config.requests_per_minute = 100
    
    backends_to_test = [
        ("Redis", redis_config),
        ("Memory", memory_config)
    ]
    
    for backend_name, config in backends_to_test:
        print(f"\n🧪 Testing {backend_name} Backend:")
        
        rate_limiter = DistributedRateLimiter(config)
        
        try:
            test_ip = f"perf.test.{backend_name.lower()}"
            num_requests = 10
            
            start_time = time.time()
            
            # Test multiple requests
            results = []
            for i in range(num_requests):
                request_start = time.time()
                allowed = await rate_limiter.is_allowed(test_ip, "general")
                request_time = (time.time() - request_start) * 1000  # ms
                results.append(request_time)
            
            total_time = (time.time() - start_time) * 1000  # ms
            avg_time = sum(results) / len(results)
            
            print(f"  Requests: {num_requests}")
            print(f"  Total Time: {total_time:.2f}ms")
            print(f"  Average Time: {avg_time:.2f}ms per request")
            print(f"  Throughput: {(num_requests / total_time * 1000):.1f} req/sec")
            
        except Exception as e:
            print(f"  ⚠️  Backend unavailable: {e}")
        finally:
            await rate_limiter.close()

async def main():
    """Run all demos"""
    print_banner()
    
    try:
        await demo_basic_functionality()
        await demo_different_endpoints()
        await demo_statistics()
        await demo_redis_vs_memory()
        
        print("\n🎉 Demo completed successfully!")
        print("\n💡 Next Steps:")
        print("  1. Review the RATE_LIMITER_GUIDE.md for detailed documentation")
        print("  2. Configure Redis settings in your .env file")
        print("  3. Test with your application using /api/health/rate-limiter")
        print("  4. Monitor rate limiting with the health endpoints")
        
    except KeyboardInterrupt:
        print("\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
