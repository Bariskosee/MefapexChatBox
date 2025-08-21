#!/usr/bin/env python3
"""
🧪 Redis Rate Limiter Test Script
Test the distributed rate limiter functionality
"""

import asyncio
import time
import logging
from core.configuration import get_config, RateLimitConfig
from core.rate_limiter import DistributedRateLimiter, get_rate_limiter

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_redis_connection():
    """Test Redis connection"""
    try:
        import redis.asyncio as redis
        config = get_config()
        
        # Test Redis connection
        redis_client = redis.from_url(config.rate_limit.redis_url, decode_responses=True)
        await redis_client.ping()
        logger.info("✅ Redis connection successful")
        await redis_client.close()
        return True
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        return False

async def test_rate_limiter_basic():
    """Test basic rate limiter functionality"""
    logger.info("🧪 Testing basic rate limiter functionality...")
    
    # Create test configuration
    config = RateLimitConfig()
    config.requests_per_minute = 5  # Low limit for testing
    config.chat_requests_per_minute = 3
    config.window_size_seconds = 10  # Short window for testing
    
    rate_limiter = DistributedRateLimiter(config)
    
    try:
        test_ip = "192.168.1.100"
        
        # Test general endpoint
        logger.info("Testing general endpoint limits...")
        for i in range(7):  # Exceed the limit of 5
            allowed = await rate_limiter.is_allowed(test_ip, "general")
            count = await rate_limiter.get_current_count(test_ip, "general")
            logger.info(f"Request {i+1}: Allowed={allowed}, Count={count}")
            
            if i < 5:
                assert allowed == True, f"Request {i+1} should be allowed"
            else:
                assert allowed == False, f"Request {i+1} should be blocked"
        
        # Test chat endpoint
        logger.info("Testing chat endpoint limits...")
        test_ip_2 = "192.168.1.101"
        for i in range(5):  # Exceed the limit of 3
            allowed = await rate_limiter.is_allowed(test_ip_2, "chat")
            count = await rate_limiter.get_current_count(test_ip_2, "chat")
            logger.info(f"Chat request {i+1}: Allowed={allowed}, Count={count}")
            
            if i < 3:
                assert allowed == True, f"Chat request {i+1} should be allowed"
            else:
                assert allowed == False, f"Chat request {i+1} should be blocked"
        
        # Test window reset
        logger.info("Waiting for window reset...")
        await asyncio.sleep(11)  # Wait longer than window
        
        allowed = await rate_limiter.is_allowed(test_ip, "general")
        logger.info(f"After window reset: Allowed={allowed}")
        assert allowed == True, "Request should be allowed after window reset"
        
        logger.info("✅ Basic rate limiter tests passed")
        
    finally:
        await rate_limiter.close()

async def test_fallback_to_memory():
    """Test fallback to memory when Redis is unavailable"""
    logger.info("🧪 Testing fallback to memory functionality...")
    
    # Create config with invalid Redis settings
    config = RateLimitConfig()
    config.redis_host = "invalid-host"
    config.redis_port = 9999
    config.fallback_to_memory = True
    config.requests_per_minute = 3
    
    rate_limiter = DistributedRateLimiter(config)
    
    try:
        test_ip = "192.168.1.200"
        
        # Should fallback to memory
        for i in range(5):
            allowed = await rate_limiter.is_allowed(test_ip, "general")
            count = await rate_limiter.get_current_count(test_ip, "general")
            logger.info(f"Fallback request {i+1}: Allowed={allowed}, Count={count}")
            
            if i < 3:
                assert allowed == True, f"Fallback request {i+1} should be allowed"
            else:
                assert allowed == False, f"Fallback request {i+1} should be blocked"
        
        logger.info("✅ Fallback to memory tests passed")
        
    finally:
        await rate_limiter.close()

async def test_multiple_instances():
    """Test multiple rate limiter instances (simulating multiple app instances)"""
    logger.info("🧪 Testing multiple instances...")
    
    config = RateLimitConfig()
    config.requests_per_minute = 5
    config.window_size_seconds = 10
    
    # Create two instances (simulating different app instances)
    rate_limiter_1 = DistributedRateLimiter(config)
    rate_limiter_2 = DistributedRateLimiter(config)
    
    try:
        test_ip = "192.168.1.300"
        
        # Alternate requests between instances
        for i in range(7):
            if i % 2 == 0:
                allowed = await rate_limiter_1.is_allowed(test_ip, "general")
                source = "Instance 1"
            else:
                allowed = await rate_limiter_2.is_allowed(test_ip, "general")
                source = "Instance 2"
            
            count_1 = await rate_limiter_1.get_current_count(test_ip, "general")
            count_2 = await rate_limiter_2.get_current_count(test_ip, "general")
            
            logger.info(f"Request {i+1} from {source}: Allowed={allowed}, Count1={count_1}, Count2={count_2}")
            
            # Both instances should see the same count
            assert count_1 == count_2, f"Counts should be synchronized: {count_1} != {count_2}"
            
            if i < 5:
                assert allowed == True, f"Request {i+1} should be allowed"
            else:
                assert allowed == False, f"Request {i+1} should be blocked"
        
        logger.info("✅ Multiple instances tests passed")
        
    finally:
        await rate_limiter_1.close()
        await rate_limiter_2.close()

async def test_stats():
    """Test rate limiter statistics"""
    logger.info("🧪 Testing statistics...")
    
    rate_limiter = await get_rate_limiter()
    
    try:
        stats = await rate_limiter.get_stats()
        logger.info(f"Rate limiter stats: {stats}")
        
        assert "enabled" in stats
        assert "backend" in stats
        assert "limits" in stats
        assert "config" in stats
        
        logger.info("✅ Statistics tests passed")
        
    finally:
        await rate_limiter.close()

async def main():
    """Run all tests"""
    logger.info("🚀 Starting Redis Rate Limiter Tests")
    
    try:
        # Test Redis connection first
        redis_available = await test_redis_connection()
        
        if redis_available:
            logger.info("📡 Redis is available - running Redis tests")
            await test_rate_limiter_basic()
            await test_multiple_instances()
        else:
            logger.warning("⚠️ Redis not available - skipping Redis-specific tests")
        
        # Test fallback functionality
        await test_fallback_to_memory()
        
        # Test stats
        await test_stats()
        
        logger.info("🎉 All tests completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
