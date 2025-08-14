#!/usr/bin/env python3
"""
🔍 Debug Session Cleanup
======================

Debug script to understand why session cleanup is not working.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.manager import db_manager
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_session_cleanup():
    """Debug the session cleanup functionality"""
    
    test_user_id = "debug_user"
    
    print(f"🔍 Debugging session cleanup for user: {test_user_id}")
    
    # Clean up any existing test data
    print("🧹 Cleaning up existing test data...")
    try:
        with db_manager.connection_service.get_cursor() as cursor:
            cursor.execute("DELETE FROM chat_messages WHERE user_id = %s", (test_user_id,))
            cursor.execute("DELETE FROM chat_sessions WHERE user_id = %s", (test_user_id,))
    except Exception as e:
        logger.warning(f"Failed to clean test data: {e}")
    
    # Create 5 test sessions
    print("📝 Creating 5 test sessions...")
    for i in range(1, 6):
        session_id = f"debug_session_{i}"
        db_manager.add_message(
            session_id=session_id,
            user_id=test_user_id,
            user_message=f"Test message in session {i}",
            bot_response=f"Test response for session {i}",
            source="debug"
        )
    
    # Check how many sessions exist
    sessions = db_manager.get_user_sessions(test_user_id)
    print(f"📊 Created sessions: {len(sessions)}")
    
    # Manually test the cleanup query
    print("\n🔍 Testing cleanup query manually...")
    try:
        with db_manager.connection_service.get_cursor() as cursor:
            # Test the SELECT query
            cursor.execute(
                """SELECT session_id FROM chat_sessions 
                   WHERE user_id = %s 
                   ORDER BY created_at DESC OFFSET %s""",
                (test_user_id, 3)  # Keep 3, should find 2 to delete
            )
            old_sessions = cursor.fetchall()
            print(f"🔍 Found {len(old_sessions)} sessions to delete")
            
            if old_sessions:
                print(f"🔍 Session structure: {type(old_sessions[0])} - {old_sessions[0]}")
                for session in old_sessions:
                    print(f"  - Session data: {session}")
                    print(f"  - Keys: {session.keys() if hasattr(session, 'keys') else 'No keys method'}")
                
                # Test deletion
                old_session_ids = [str(session['session_id']) for session in old_sessions]
                print(f"🔍 Deleting session IDs: {old_session_ids}")
                
                # Delete messages first
                cursor.execute(
                    "DELETE FROM chat_messages WHERE session_id = ANY(%s)",
                    (old_session_ids,)
                )
                messages_deleted = cursor.rowcount
                print(f"🔍 Messages deleted: {messages_deleted}")
                
                # Delete sessions
                cursor.execute(
                    "DELETE FROM chat_sessions WHERE session_id = ANY(%s)",
                    (old_session_ids,)
                )
                sessions_deleted = cursor.rowcount
                print(f"🔍 Sessions deleted: {sessions_deleted}")
            else:
                print("🔍 No sessions found to delete")
    
    except Exception as e:
        print(f"❌ Manual test failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Check final session count
    final_sessions = db_manager.get_user_sessions(test_user_id)
    print(f"📊 Final session count: {len(final_sessions)}")
    
    # Clean up
    print("🧹 Cleaning up...")
    try:
        with db_manager.connection_service.get_cursor() as cursor:
            cursor.execute("DELETE FROM chat_messages WHERE user_id = %s", (test_user_id,))
            cursor.execute("DELETE FROM chat_sessions WHERE user_id = %s", (test_user_id,))
    except Exception as e:
        logger.warning(f"Failed to clean test data: {e}")

if __name__ == "__main__":
    debug_session_cleanup()
