#!/usr/bin/env python3
"""
Docker PostgreSQL Database Migration Script
Runs inside Docker environment to setup database
"""

import os
import sys
import json
from datetime import datetime

# Use localhost for external setup
os.environ['POSTGRES_HOST'] = 'localhost'
os.environ['POSTGRES_PORT'] = '5432'
os.environ['POSTGRES_USER'] = 'mefapex'
os.environ['POSTGRES_PASSWORD'] = 'mefapex_docker_secure_2025'
os.environ['POSTGRES_DB'] = 'mefapex_chatbot'

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def setup_docker_database():
    """Setup Docker PostgreSQL database"""
    
    try:
        from database_manager import db_manager
        
        print("🐳 Docker PostgreSQL Database Setup")
        print("=" * 40)
        
        # Test connection
        health = db_manager.health_check()
        if health.get('status') != 'healthy':
            print("❌ Database connection failed!")
            return False
        
        print("✅ Docker PostgreSQL connection successful")
        
        # Get stats
        stats = db_manager.get_stats()
        print(f"📊 Current stats: {stats}")
        
        # Load and migrate content
        print("\n📝 Loading static content...")
        
        json_path = "content/static_responses.json"
        if not os.path.exists(json_path):
            print(f"❌ {json_path} not found!")
            return False
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        responses = data.get("responses", {})
        
        # Clear existing system responses
        conn = db_manager._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM dynamic_responses WHERE created_by = 'system'")
        print("🧹 Cleared existing system responses")
        
        # Add all responses
        successful_imports = 0
        
        for category_key, response_data in responses.items():
            try:
                message = response_data.get("message", "")
                keywords = response_data.get("keywords", [])
                
                cursor.execute("""
                    INSERT INTO dynamic_responses 
                    (category, keywords, response_text, created_by, is_active, created_at) 
                    VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                """, (
                    category_key,
                    json.dumps(keywords, ensure_ascii=False),
                    message,
                    'system',
                    True
                ))
                
                successful_imports += 1
                print(f"✅ {category_key}: {len(keywords)} keywords imported")
                
            except Exception as e:
                print(f"❌ {category_key} failed: {e}")
                continue
        
        conn.commit()
        db_manager._put_connection(conn)
        
        print(f"\n🎉 Migration completed: {successful_imports}/{len(responses)} responses imported")
        
        # Final stats
        final_stats = db_manager.get_stats()
        print(f"📊 Final stats: {final_stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ Docker database setup failed: {e}")
        return False

if __name__ == "__main__":
    if setup_docker_database():
        print("\n✅ Docker database setup completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Docker database setup failed!")
        sys.exit(1)
