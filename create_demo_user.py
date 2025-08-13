#!/usr/bin/env python3
"""
🔧 Create Demo User Script
Creates the demo user in the database if it doesn't exist
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
import bcrypt
import uuid

def create_demo_user():
    """Create demo user in the database"""
    try:
        # Database connection parameters
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='mefapex_chatbot',
            user='mefapex',
            password=os.getenv('POSTGRES_PASSWORD', 'mefapex'),
            cursor_factory=RealDictCursor
        )
        
        cursor = conn.cursor()
        
        # Check if demo user already exists
        cursor.execute("SELECT username FROM users WHERE username = %s", ('demo',))
        existing_user = cursor.fetchone()
        
        if existing_user:
            print("✅ Demo user already exists")
            cursor.close()
            conn.close()
            return
        
        # Create hashed password for demo user
        demo_password = '1234'
        hashed_password = bcrypt.hashpw(demo_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        demo_user_id = str(uuid.uuid4())
        
        # Insert demo user
        insert_query = """
            INSERT INTO users (user_id, username, email, hashed_password, full_name, is_active)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(insert_query, (
            demo_user_id,
            'demo',
            'demo@mefapex.com',
            hashed_password,
            'Demo User',
            True
        ))
        
        conn.commit()
        
        print(f"✅ Demo user created successfully!")
        print(f"   Username: demo")
        print(f"   Password: {demo_password}")
        print(f"   User ID: {demo_user_id}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error creating demo user: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("🔧 Creating demo user...")
    create_demo_user()
    print("✅ Done!")
