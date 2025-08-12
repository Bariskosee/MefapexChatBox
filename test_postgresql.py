#!/usr/bin/env python3
"""
Enhanced PostgreSQL Connection Test Script for MEFAPEX ChatBox
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    print("� MEFAPEX ChatBox - PostgreSQL Test")
    print("=" * 50)
    
    try:
        from database_manager import db_manager
        from content_manager import content_manager
        
        # Test database connection
        print("\n📊 Database Connection Test:")
        try:
            db_info = db_manager.get_database_info()
            print(f"✅ PostgreSQL Connection: SUCCESS")
            print(f"📊 Database Info: {db_info}")
            
            # Test table creation
            print("\n📋 Testing table creation...")
            db_manager.create_tables()
            print("✅ Tables created successfully")
            
            # Test user operations
            print("\n👤 Testing user operations...")
            test_user_id = db_manager.create_user("test_user", "test@example.com", "test_password")
            if test_user_id:
                print(f"✅ Test user created with ID: {test_user_id}")
                
                # Clean up test user
                conn = db_manager._get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM users WHERE username = %s", ("test_user",))
                conn.commit()
                db_manager._put_connection(conn)
                print("🧹 Test user cleaned up")
            
        except Exception as e:
            print(f"❌ Database test failed: {e}")
            return False
        
        # Test content manager
        print("\n📝 Content Manager Test:")
        try:
            content_stats = content_manager.get_stats()
            print(f"✅ Content Manager: SUCCESS")
            print(f"📊 Content Stats: {content_stats}")
        except Exception as e:
            print(f"❌ Content Manager test failed: {e}")
        
        # Test model manager (optional)
        print("\n🤖 Model Manager Test (Optional):")
        try:
            from model_manager import model_manager
            model_info = model_manager.get_model_info()
            print(f"✅ Model Manager: SUCCESS")
            print(f"📊 Model Info: {model_info}")
        except Exception as e:
            print(f"⚠️ Model Manager test failed (this is optional): {e}")
        
        print("\n🎉 All core systems tested successfully!")
        print("\n� Ready to start the application:")
        print("   python main.py")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("📦 Please install required packages:")
        print("   pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
