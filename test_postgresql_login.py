#!/usr/bin/env python3
"""
🧪 Test PostgreSQL Login - MEFAPEX ChatBox
Simple test script to verify login functionality with PostgreSQL
"""

import os
import sys
import asyncio
from postgresql_manager import get_postgresql_manager
from auth_service import init_auth_service

async def test_login():
    """Test login functionality"""
    
    print("🔍 Testing PostgreSQL login functionality...")
    print("=" * 50)
    
    try:
        # Initialize database manager
        print("📊 Initializing PostgreSQL manager...")
        db_manager = get_postgresql_manager()
        await db_manager.initialize()
        print("✅ Database initialized successfully")
        
        # Initialize auth service
        print("🔐 Initializing authentication service...")
        auth_service = init_auth_service(secret_key="test-secret", environment="development")
        print("✅ Auth service initialized")
        
        # Test demo user login
        print("\n🧪 Testing demo user login...")
        username = "demo"
        password = "1234"
        
        # Get user from database
        user_data = db_manager.authenticate_user(username)
        
        if user_data:
            print(f"✅ User found in database: {username}")
            print(f"   User ID: {user_data['user_id']}")
            print(f"   Email: {user_data['email']}")
            print(f"   Active: {user_data['is_active']}")
            
            # Test password verification
            password_valid = auth_service.verify_password(password, user_data['hashed_password'])
            
            if password_valid:
                print("✅ Password verification successful!")
                
                # Update last login
                db_manager.update_last_login(username)
                print("✅ Last login updated")
                
                # Create session
                session_id = db_manager.get_or_create_session(user_data['user_id'])
                print(f"✅ Session created: {session_id}")
                
                # Test adding a message
                db_manager.add_message(
                    session_id=session_id,
                    user_id=user_data['user_id'],
                    user_message="Test message",
                    bot_response="Test response",
                    source="test"
                )
                print("✅ Test message added successfully")
                
                # Get chat history
                history = db_manager.get_chat_history(user_data['user_id'], limit=5)
                print(f"✅ Retrieved {len(history)} messages from history")
                
                print("\n🎉 All tests passed! Login functionality is working.")
                
            else:
                print("❌ Password verification failed!")
                return False
                
        else:
            print("❌ User not found in database!")
            return False
            
        # Test database stats
        print("\n📊 Database statistics:")
        stats = db_manager.get_stats()
        for key, value in stats.items():
            print(f"   {key}: {value}")
            
        # Close database connection
        await db_manager.close()
        print("\n✅ Test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Set environment variables
    os.environ["POSTGRES_HOST"] = "localhost"
    os.environ["POSTGRES_PORT"] = "5432"
    os.environ["POSTGRES_DB"] = "mefapex_chatbot"
    os.environ["POSTGRES_USER"] = "mefapex"
    os.environ["POSTGRES_PASSWORD"] = "mefapex"
    
    # Run the test
    result = asyncio.run(test_login())
    
    if result:
        print("\n🎯 Result: PostgreSQL login test PASSED ✅")
        sys.exit(0)
    else:
        print("\n🎯 Result: PostgreSQL login test FAILED ❌")
        sys.exit(1)
