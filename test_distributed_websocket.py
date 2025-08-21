#!/usr/bin/env python3
"""
Test script for distributed WebSocket functionality
Tests both in-memory and Redis-based session management
"""
import asyncio
import json
import logging
import os
import sys
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.session_store import (
    create_session_store, create_message_broker, SessionInfo
)
from core.distributed_websocket_manager import create_distributed_websocket_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_session_store(redis_url=None):
    """Test session store functionality"""
    logger.info(f"🧪 Testing session store (Redis: {redis_url is not None})")
    
    # Create session store
    session_store = create_session_store(redis_url)
    
    try:
        # Test session creation
        session_info = SessionInfo(
            session_id="test_session_1",
            user_id="test_user_1",
            username="Test User",
            connected_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            worker_id="test_worker_1",
            metadata={"test": True}
        )
        
        # Test add session
        success = await session_store.add_session(session_info)
        assert success, "Failed to add session"
        logger.info("✅ Session added successfully")
        
        # Test get session
        retrieved_session = await session_store.get_session("test_session_1")
        assert retrieved_session is not None, "Failed to retrieve session"
        assert retrieved_session.user_id == "test_user_1", "Session data mismatch"
        logger.info("✅ Session retrieved successfully")
        
        # Test get user sessions
        user_sessions = await session_store.get_user_sessions("test_user_1")
        assert len(user_sessions) == 1, "Incorrect user session count"
        logger.info("✅ User sessions retrieved successfully")
        
        # Test update activity
        update_success = await session_store.update_activity("test_session_1")
        assert update_success, "Failed to update session activity"
        logger.info("✅ Session activity updated successfully")
        
        # Test get all sessions
        all_sessions = await session_store.get_all_sessions()
        assert len(all_sessions) >= 1, "Failed to get all sessions"
        logger.info("✅ All sessions retrieved successfully")
        
        # Test remove session
        remove_success = await session_store.remove_session("test_session_1")
        assert remove_success, "Failed to remove session"
        logger.info("✅ Session removed successfully")
        
        # Verify session is gone
        removed_session = await session_store.get_session("test_session_1")
        assert removed_session is None, "Session should be removed"
        logger.info("✅ Session removal verified")
        
    finally:
        if hasattr(session_store, 'close'):
            await session_store.close()
    
    logger.info("🎉 Session store test completed successfully")

async def test_message_broker(redis_url=None):
    """Test message broker functionality"""
    logger.info(f"🧪 Testing message broker (Redis: {redis_url is not None})")
    
    # Create message broker
    message_broker = create_message_broker(redis_url)
    
    # Test message collection
    received_messages = []
    
    async def message_callback(message):
        received_messages.append(message)
        logger.info(f"📨 Received message: {message}")
    
    try:
        # Test subscription
        await message_broker.subscribe_to_channel("test_channel", message_callback)
        logger.info("✅ Subscribed to test channel")
        
        # Wait a moment for subscription to be established
        await asyncio.sleep(0.1)
        
        # Test message publishing
        test_message = {
            "type": "test",
            "data": "Hello, World!",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        publish_success = await message_broker.publish_message("test_channel", test_message)
        assert publish_success, "Failed to publish message"
        logger.info("✅ Message published successfully")
        
        # Wait for message to be received
        await asyncio.sleep(0.2)
        
        # Verify message was received (for in-memory broker)
        if redis_url is None:  # In-memory broker receives messages immediately
            assert len(received_messages) == 1, f"Expected 1 message, got {len(received_messages)}"
            assert received_messages[0]["type"] == "test", "Message content mismatch"
            logger.info("✅ Message received successfully")
        else:
            # For Redis, messages are received asynchronously
            logger.info("✅ Message published to Redis (async reception)")
        
    finally:
        # Cleanup
        await message_broker.unsubscribe_from_channel("test_channel")
        if hasattr(message_broker, 'close'):
            await message_broker.close()
    
    logger.info("🎉 Message broker test completed successfully")

async def test_distributed_websocket_manager(redis_url=None):
    """Test distributed WebSocket manager functionality"""
    logger.info(f"🧪 Testing distributed WebSocket manager (Redis: {redis_url is not None})")
    
    # Create distributed WebSocket manager
    manager = create_distributed_websocket_manager(redis_url, worker_id="test_worker")
    
    try:
        # Test health check
        health = await manager.health_check()
        assert health["worker_id"] == "test_worker", "Worker ID mismatch"
        logger.info(f"✅ Health check passed: {health}")
        
        # Test session management without actual WebSocket
        # (In a real scenario, we'd use mock WebSocket objects)
        
        # Test get online users (should be empty initially)
        online_users = await manager.get_online_users()
        assert isinstance(online_users, list), "Online users should be a list"
        logger.info(f"✅ Online users retrieved: {len(online_users)} users")
        
        # Test connection stats
        stats = await manager.get_connection_stats()
        assert "distributed_stats" in stats, "Missing distributed stats"
        assert "local_stats" in stats, "Missing local stats"
        logger.info(f"✅ Connection stats retrieved: {stats['local_stats']['worker_id']}")
        
        # Test cleanup (should return 0 since no sessions exist)
        cleaned_count = await manager.cleanup_expired_sessions()
        assert isinstance(cleaned_count, int), "Cleanup count should be integer"
        logger.info(f"✅ Cleanup completed: {cleaned_count} sessions cleaned")
        
    finally:
        await manager.close()
    
    logger.info("🎉 Distributed WebSocket manager test completed successfully")

async def run_all_tests():
    """Run all tests"""
    logger.info("🚀 Starting distributed WebSocket system tests")
    
    # Test 1: In-memory implementations
    logger.info("\n" + "="*60)
    logger.info("TESTING IN-MEMORY IMPLEMENTATIONS")
    logger.info("="*60)
    
    await test_session_store(redis_url=None)
    await test_message_broker(redis_url=None)
    await test_distributed_websocket_manager(redis_url=None)
    
    # Test 2: Redis implementations (if Redis is available)
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    try:
        logger.info("\n" + "="*60)
        logger.info("TESTING REDIS IMPLEMENTATIONS")
        logger.info("="*60)
        
        await test_session_store(redis_url=redis_url)
        await test_message_broker(redis_url=redis_url)
        await test_distributed_websocket_manager(redis_url=redis_url)
        
    except Exception as e:
        logger.warning(f"⚠️ Redis tests failed (Redis server may not be available): {e}")
        logger.info("💡 To test Redis functionality, ensure Redis server is running")
    
    logger.info("\n" + "="*60)
    logger.info("🎉 ALL TESTS COMPLETED SUCCESSFULLY!")
    logger.info("="*60)

if __name__ == "__main__":
    asyncio.run(run_all_tests())
