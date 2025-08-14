#!/usr/bin/env python3
"""
🧪 Test PostgreSQL User Creation - MEFAPEX ChatBox
Simple test script to create a new user and test login
"""

import os
import sys
import asyncio
import bcrypt
import uuid
from database.manager import db_manager
from auth_service import init_auth_service

async def test_create_user():
    """Test creating a new user and logging in"""
    
    print("🔍 Testing PostgreSQL user creation...")
    print("=" * 50)
    
    try:
        # Initialize database manager
        print("📊 Database manager is ready...")
        # db_manager is already available from import
        print("✅ Database manager ready")
        
        # Initialize auth service
        print("🔐 Initializing authentication service...")
        auth_service = init_auth_service(secret_key="test-secret", environment="development")
        print("✅ Auth service initialized")
        
        # Create a new test user
        print("\n👤 Creating new test user...")
        test_username = "testuser"
        test_password = "testpass123"
        test_email = "testuser@mefapex.com"
        
        # Check if user already exists
        existing_user = db_manager.authenticate_user(test_username)
        if existing_user:
            print(f"ℹ️  User {test_username} already exists, skipping creation")
        else:
            # Hash password
            hashed_password = bcrypt.hashpw(test_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            test_user_id = str(uuid.uuid4())
            
            # Insert user directly into database
            cursor = db_manager.sync_connection.cursor()
            cursor.execute("""
                INSERT INTO users (user_id, username, email, hashed_password, full_name, is_active)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (test_user_id, test_username, test_email, hashed_password, "Test User", True))
            
            print(f"✅ New user created: {test_username}")
        
        # Test login with new user
        print(f"\n🧪 Testing login with user: {test_username}")
        
        # Get user from database
        user_data = db_manager.authenticate_user(test_username)
        
        if user_data:
            print(f"✅ User found in database: {test_username}")
            print(f"   User ID: {user_data['user_id']}")
            print(f"   Email: {user_data['email']}")
            print(f"   Active: {user_data['is_active']}")
            
            # Test password verification
            password_valid = auth_service.verify_password(test_password, user_data['hashed_password'])
            
            if password_valid:
                print("✅ Password verification successful!")
                
                # Update last login
                db_manager.update_last_login(test_username)
                print("✅ Last login updated")
                
                # Create session
                session_id = db_manager.get_or_create_session(user_data['user_id'])
                print(f"✅ Session created: {session_id}")
                
                # Test adding a message
                db_manager.add_message(
                    session_id=session_id,
                    user_id=user_data['user_id'],
                    user_message="Hello from test user!",
                    bot_response="Hello! This is a test response.",
                    source="test"
                )
                print("✅ Test message added successfully")
                
                # Get chat history
                history = db_manager.get_chat_history(user_data['user_id'], limit=5)
                print(f"✅ Retrieved {len(history)} messages from history")
                
                # Test user sessions
                sessions = db_manager.get_user_sessions(user_data['user_id'])
                print(f"✅ Retrieved {len(sessions)} sessions for user")
                
                print(f"\n🎉 All tests passed! User {test_username} can login successfully.")
                
            else:
                print("❌ Password verification failed!")
                return False
                
        else:
            print("❌ User not found in database!")
            return False
            
        # Close database connection
        await db_manager.close()
        print("\n✅ User creation test completed successfully!")
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
    result = asyncio.run(test_create_user())
    
    if result:
        print("\n🎯 Result: PostgreSQL user creation test PASSED ✅")
        sys.exit(0)
    else:
        print("\n🎯 Result: PostgreSQL user creation test FAILED ❌")
        sys.exit(1)
