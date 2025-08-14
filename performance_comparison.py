"""
🎯 Performance Comparison: Sync vs Async Database Operations
Test script to demonstrate the performance difference between sync and async database operations
"""

import asyncio
import time
import logging
from typing import List
import concurrent.futures

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test data
TEST_USERS = [f"test_user_{i}" for i in range(10)]
TEST_MESSAGES = [
    "Merhaba nasılsın?",
    "Bugün hava nasıl?", 
    "AI teknolojisi hakkında ne düşünüyorsun?",
    "Python programlama dili avantajları nelerdir?",
    "Veritabanı optimizasyonu nasıl yapılır?"
]

async def test_async_operations():
    """Test async database operations performance"""
    print("🚀 Testing ASYNC Database Operations")
    print("=" * 50)
    
    try:
        from async_postgresql_manager import get_async_postgresql_manager
        
        # Initialize async database manager
        start_time = time.time()
        async_db = await get_async_postgresql_manager()
        init_time = time.time() - start_time
        print(f"✅ Async DB initialization: {init_time:.3f}s")
        
        # Test concurrent user authentication (simulates high load)
        start_time = time.time()
        auth_tasks = []
        for username in TEST_USERS:
            task = async_db.authenticate_user(username)
            auth_tasks.append(task)
        
        # Execute all authentication requests concurrently
        auth_results = await asyncio.gather(*auth_tasks, return_exceptions=True)
        auth_time = time.time() - start_time
        
        successful_auths = sum(1 for result in auth_results if not isinstance(result, Exception))
        print(f"✅ Async auth operations: {len(TEST_USERS)} users in {auth_time:.3f}s")
        print(f"   Concurrent processing: {successful_auths} operations")
        print(f"   Average per operation: {auth_time/len(TEST_USERS):.3f}s")
        
        # Test concurrent message operations
        start_time = time.time()
        message_tasks = []
        
        for i, username in enumerate(TEST_USERS[:5]):  # Test with 5 users
            for j, message in enumerate(TEST_MESSAGES):
                session_id = f"test_session_{i}_{j}"
                user_id = f"user_id_{i}"
                
                task = async_db.add_message(
                    session_id=session_id,
                    user_id=user_id,
                    user_message=message,
                    bot_response=f"Response to: {message}",
                    source="performance_test"
                )
                message_tasks.append(task)
        
        # Execute all message operations concurrently
        message_results = await asyncio.gather(*message_tasks, return_exceptions=True)
        message_time = time.time() - start_time
        
        successful_messages = sum(1 for result in message_results if result is True)
        total_operations = len(message_tasks)
        
        print(f"✅ Async message operations: {total_operations} messages in {message_time:.3f}s")
        print(f"   Successful operations: {successful_messages}")
        print(f"   Throughput: {total_operations/message_time:.1f} ops/sec")
        
        # Test health check
        start_time = time.time()
        health = await async_db.health_check()
        health_time = time.time() - start_time
        print(f"✅ Async health check: {health_time:.3f}s - Status: {health.get('status')}")
        
        return {
            "type": "async",
            "init_time": init_time,
            "auth_time": auth_time,
            "auth_operations": len(TEST_USERS),
            "message_time": message_time,
            "message_operations": total_operations,
            "throughput": total_operations/message_time,
            "health_time": health_time
        }
        
    except Exception as e:
        logger.error(f"❌ Async test failed: {e}")
        return None

def test_sync_operations():
    """Test sync database operations performance"""
    print("\n🐌 Testing SYNC Database Operations")
    print("=" * 50)
    
    try:
        from postgresql_manager import get_postgresql_manager
        
        # Initialize sync database manager
        start_time = time.time()
        sync_db = get_postgresql_manager()
        init_time = time.time() - start_time
        print(f"✅ Sync DB initialization: {init_time:.3f}s")
        
        # Test sequential user authentication (sync operations block)
        start_time = time.time()
        successful_auths = 0
        
        for username in TEST_USERS:
            try:
                result = sync_db.authenticate_user(username)
                if result:
                    successful_auths += 1
            except Exception as e:
                logger.warning(f"Auth failed for {username}: {e}")
        
        auth_time = time.time() - start_time
        print(f"✅ Sync auth operations: {len(TEST_USERS)} users in {auth_time:.3f}s")
        print(f"   Sequential processing: {successful_auths} operations")
        print(f"   Average per operation: {auth_time/len(TEST_USERS):.3f}s")
        
        # Test sequential message operations
        start_time = time.time()
        successful_messages = 0
        total_operations = 0
        
        for i, username in enumerate(TEST_USERS[:5]):  # Test with 5 users
            for j, message in enumerate(TEST_MESSAGES):
                total_operations += 1
                session_id = f"test_session_{i}_{j}"
                user_id = f"user_id_{i}"
                
                try:
                    sync_db.add_message(
                        session_id=session_id,
                        user_id=user_id,
                        user_message=message,
                        bot_response=f"Response to: {message}",
                        source="performance_test"
                    )
                    successful_messages += 1
                except Exception as e:
                    logger.warning(f"Message save failed: {e}")
        
        message_time = time.time() - start_time
        print(f"✅ Sync message operations: {total_operations} messages in {message_time:.3f}s")
        print(f"   Successful operations: {successful_messages}")
        print(f"   Throughput: {total_operations/message_time:.1f} ops/sec")
        
        # Test health check
        start_time = time.time()
        health = sync_db.health_check()
        health_time = time.time() - start_time
        print(f"✅ Sync health check: {health_time:.3f}s - Status: {health.get('status')}")
        
        return {
            "type": "sync",
            "init_time": init_time,
            "auth_time": auth_time,
            "auth_operations": len(TEST_USERS),
            "message_time": message_time,
            "message_operations": total_operations,
            "throughput": total_operations/message_time,
            "health_time": health_time
        }
        
    except Exception as e:
        logger.error(f"❌ Sync test failed: {e}")
        return None

def print_performance_comparison(async_results, sync_results):
    """Print detailed performance comparison"""
    print("\n📊 PERFORMANCE COMPARISON RESULTS")
    print("=" * 60)
    
    if not async_results or not sync_results:
        print("❌ Unable to compare - one or both tests failed")
        return
    
    print(f"{'Metric':<25} {'Async':<15} {'Sync':<15} {'Improvement':<15}")
    print("-" * 70)
    
    # Initialization time
    async_init = async_results["init_time"]
    sync_init = sync_results["init_time"]
    init_improvement = f"{(sync_init/async_init):.1f}x" if async_init > 0 else "N/A"
    print(f"{'Initialization':<25} {async_init:.3f}s{'':<8} {sync_init:.3f}s{'':<8} {init_improvement:<15}")
    
    # Authentication time
    async_auth = async_results["auth_time"]
    sync_auth = sync_results["auth_time"]
    auth_improvement = f"{(sync_auth/async_auth):.1f}x" if async_auth > 0 else "N/A"
    print(f"{'Auth Operations':<25} {async_auth:.3f}s{'':<8} {sync_auth:.3f}s{'':<8} {auth_improvement:<15}")
    
    # Message operations time
    async_msg = async_results["message_time"]
    sync_msg = sync_results["message_time"]
    msg_improvement = f"{(sync_msg/async_msg):.1f}x" if async_msg > 0 else "N/A"
    print(f"{'Message Operations':<25} {async_msg:.3f}s{'':<8} {sync_msg:.3f}s{'':<8} {msg_improvement:<15}")
    
    # Throughput
    async_throughput = async_results["throughput"]
    sync_throughput = sync_results["throughput"]
    throughput_improvement = f"{(async_throughput/sync_throughput):.1f}x" if sync_throughput > 0 else "N/A"
    print(f"{'Throughput':<25} {async_throughput:.1f} ops/s{'':<5} {sync_throughput:.1f} ops/s{'':<5} {throughput_improvement:<15}")
    
    # Health check
    async_health = async_results["health_time"]
    sync_health = sync_results["health_time"]
    health_improvement = f"{(sync_health/async_health):.1f}x" if async_health > 0 else "N/A"
    print(f"{'Health Check':<25} {async_health:.3f}s{'':<8} {sync_health:.3f}s{'':<8} {health_improvement:<15}")
    
    print("\n🎯 KEY BENEFITS OF ASYNC APPROACH:")
    print("─" * 50)
    print("✅ Non-blocking operations - FastAPI can handle other requests")
    print("✅ Better resource utilization - connection pooling")
    print("✅ Higher concurrency - multiple DB operations in parallel")
    print("✅ Improved user experience - faster response times")
    print("✅ Better scalability - handles more concurrent users")
    
    print(f"\n🚀 OVERALL PERFORMANCE GAIN:")
    if async_throughput > sync_throughput:
        overall_gain = (async_throughput / sync_throughput)
        print(f"   Async approach is {overall_gain:.1f}x FASTER than sync approach!")
    else:
        print("   Results may vary depending on system load and database configuration")

async def main():
    """Main performance test runner"""
    print("🎯 MEFAPEX Database Performance Analysis")
    print("Testing sync vs async PostgreSQL operations")
    print("=" * 60)
    
    # Test async operations
    async_results = await test_async_operations()
    
    # Test sync operations
    sync_results = test_sync_operations()
    
    # Compare results
    print_performance_comparison(async_results, sync_results)
    
    print(f"\n✅ Performance analysis completed!")
    print("💡 Consider migrating all database operations to async for production use.")

if __name__ == "__main__":
    asyncio.run(main())
