#!/usr/bin/env python3
"""
Database Manager Compatibility Test
Tests if database/manager.py has all required methods for unification
"""

from database.manager import db_manager
import sys

def test_compatibility():
    """Test if database/manager.py has all required features"""
    
    required_methods = [
        'authenticate_user',
        'update_last_login', 
        'get_or_create_session',
        'add_message',
        'get_chat_history',
        'get_user_sessions',
        'get_session_messages',
        'clear_chat_history',
        'get_stats',
        'health_check'
    ]
    
    print("🧪 Testing database manager compatibility...")
    print("=" * 40)
    
    missing_methods = []
    
    for method in required_methods:
        if hasattr(db_manager, method):
            print(f"✅ {method} - Available")
        else:
            print(f"❌ {method} - Missing")
            missing_methods.append(method)
    
    if missing_methods:
        print(f"\n❌ Missing methods: {missing_methods}")
        return False
    
    # Test basic functionality
    try:
        # Test connection
        stats = db_manager.get_stats()
        print(f"✅ Database connection: {len(stats) if isinstance(stats, dict) else 'available'}")
        
        # Test health check
        health = db_manager.health_check()
        print(f"✅ Health check: {health.get('status', 'unknown')}")
        
        print("\n🎉 Compatibility test PASSED!")
        return True
        
    except Exception as e:
        print(f"\n❌ Compatibility test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if test_compatibility():
        print("✅ Database manager is ready for unification!")
        sys.exit(0)
    else:
        print("❌ Database manager needs fixes before unification!")
        sys.exit(1)
