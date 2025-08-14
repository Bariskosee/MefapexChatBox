#!/usr/bin/env python3
"""
🧪 Test Conversation History Management
=====================================

Test script to verify that conversation history is properly limited to 15 conversations
and old conversations are deleted when new ones are saved.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.manager import db_manager
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_conversation_limit():
    """Test that conversation history is limited to 15 conversations"""
    
    test_user_id = "test_user_history_limit"
    
    print(f"🧪 Testing conversation history limit for user: {test_user_id}")
    
    # Clean up any existing test data
    print("🧹 Cleaning up existing test data...")
    db_manager.clear_chat_history(test_user_id)
    
    # Delete all sessions for test user
    try:
        with db_manager.connection_service.get_cursor() as cursor:
            cursor.execute("DELETE FROM chat_sessions WHERE user_id = %s", (test_user_id,))
    except Exception as e:
        logger.warning(f"Failed to clean sessions: {e}")
    
    # Create 20 test sessions (should trigger cleanup)
    print("📝 Creating 20 test sessions...")
    for i in range(1, 21):
        session_id = f"test_session_{i}"
        
        # Add messages to each session
        for j in range(1, 4):  # 3 messages per session
            db_manager.add_message(
                session_id=session_id,
                user_id=test_user_id,
                user_message=f"Test message {j} in session {i}",
                bot_response=f"Test response {j} for session {i}",
                source="test"
            )
        
        # Trigger session cleanup after saving each session
        if i > 15:  # Start cleanup after 15 sessions
            deleted_count = db_manager.delete_old_sessions(test_user_id, keep_count=15)
            if deleted_count > 0:
                print(f"🧹 Deleted {deleted_count} old sessions after creating session {i}")
    
    # Check final session count
    final_sessions = db_manager.get_user_sessions(test_user_id)
    print(f"📊 Final session count: {len(final_sessions)}")
    
    if len(final_sessions) <= 15:
        print("✅ PASS: Session count is within limit (≤15)")
    else:
        print(f"❌ FAIL: Session count ({len(final_sessions)}) exceeds limit (15)")
    
    # Verify which sessions remain (should be the most recent ones)
    print("\n📚 Remaining sessions:")
    for session in final_sessions[:5]:  # Show first 5
        session_id = session.get('session_id', session.get('sessionId'))
        message_count = session.get('message_count', session.get('messageCount', 0))
        print(f"  - Session: {session_id}, Messages: {message_count}")
    
    # Clean up test data
    print("\n🧹 Cleaning up test data...")
    db_manager.clear_chat_history(test_user_id)
    try:
        with db_manager.connection_service.get_cursor() as cursor:
            cursor.execute("DELETE FROM chat_sessions WHERE user_id = %s", (test_user_id,))
    except Exception as e:
        logger.warning(f"Failed to clean sessions: {e}")
    
    print("✅ Test completed!")

def test_active_session_saving():
    """Test that active sessions are properly saved on logout"""
    
    test_user_id = "test_user_active_session"
    
    print(f"\n🧪 Testing active session saving for user: {test_user_id}")
    
    # Clean up any existing test data
    print("🧹 Cleaning up existing test data...")
    db_manager.clear_chat_history(test_user_id)
    
    # Create an active session with messages
    session_id = "test_active_session_123"
    
    print("📝 Creating active session with messages...")
    for i in range(1, 4):
        db_manager.add_message(
            session_id=session_id,
            user_id=test_user_id,
            user_message=f"Active session message {i}",
            bot_response=f"Active session response {i}",
            source="active_test"
        )
    
    # Verify the session was saved
    sessions = db_manager.get_user_sessions(test_user_id)
    print(f"📊 Sessions found: {len(sessions)}")
    
    if len(sessions) > 0:
        session = sessions[0]
        message_count = session.get('message_count', session.get('messageCount', 0))
        print(f"✅ PASS: Active session saved with {message_count} messages")
    else:
        print("❌ FAIL: Active session was not saved")
    
    # Clean up test data
    print("🧹 Cleaning up test data...")
    db_manager.clear_chat_history(test_user_id)
    
    print("✅ Test completed!")

if __name__ == "__main__":
    print("🚀 Starting Conversation History Management Tests")
    print("=" * 60)
    
    try:
        test_conversation_limit()
        test_active_session_saving()
        
        print("\n🎉 All tests completed!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
